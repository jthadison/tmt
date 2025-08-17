"""
Data Retention System
Story 8.8 - Task 6: Implement data retention
"""
import logging
import asyncio
import gzip
import json
import os
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timedelta, date
from pathlib import Path
from dataclasses import dataclass, asdict
import shutil
import sqlite3
from concurrent.futures import ThreadPoolExecutor

try:
    from .transaction_manager import TransactionRecord
    from .audit_trail import AuditRecord
except ImportError:
    from transaction_manager import TransactionRecord
    from audit_trail import AuditRecord

logger = logging.getLogger(__name__)


@dataclass
class RetentionPolicy:
    """Data retention policy configuration"""
    data_type: str
    retention_years: int
    archive_after_months: int
    compression_enabled: bool
    backup_enabled: bool
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ArchiveMetadata:
    """Metadata for archived data"""
    archive_id: str
    data_type: str
    period_start: date
    period_end: date
    record_count: int
    compressed_size_bytes: int
    archive_path: str
    created_at: datetime
    checksum: str
    
    def to_dict(self) -> Dict:
        result = asdict(self)
        result['period_start'] = self.period_start.isoformat()
        result['period_end'] = self.period_end.isoformat()
        result['created_at'] = self.created_at.isoformat()
        return result


@dataclass
class RetentionReport:
    """Report on data retention operations"""
    operation_id: str
    operation_type: str  # 'archive', 'purge', 'restore'
    started_at: datetime
    completed_at: datetime
    records_processed: int
    success_count: int
    failure_count: int
    space_saved_bytes: int
    errors: List[str]
    
    def to_dict(self) -> Dict:
        result = asdict(self)
        result['started_at'] = self.started_at.isoformat()
        result['completed_at'] = self.completed_at.isoformat()
        return result


class DataRetentionManager:
    """Manages 7-year data retention for transactions and audit records"""
    
    def __init__(self, base_storage_path: str = "./data_retention"):
        self.base_storage_path = Path(base_storage_path)
        self.active_storage_path = self.base_storage_path / "active"
        self.archive_storage_path = self.base_storage_path / "archive"
        self.backup_storage_path = self.base_storage_path / "backup"
        
        # Create storage directories
        for path in [self.active_storage_path, self.archive_storage_path, self.backup_storage_path]:
            path.mkdir(parents=True, exist_ok=True)
            
        # Default retention policies
        self.retention_policies = {
            'transactions': RetentionPolicy(
                data_type='transactions',
                retention_years=7,
                archive_after_months=12,
                compression_enabled=True,
                backup_enabled=True
            ),
            'audit_records': RetentionPolicy(
                data_type='audit_records',
                retention_years=7,
                archive_after_months=6,
                compression_enabled=True,
                backup_enabled=True
            )
        }
        
        # Initialize metadata database
        self.metadata_db_path = self.base_storage_path / "retention_metadata.db"
        self._init_metadata_db()
        
        # Thread executor for I/O operations
        self.executor = ThreadPoolExecutor(max_workers=4)
        
    def _init_metadata_db(self):
        """Initialize SQLite database for retention metadata"""
        conn = sqlite3.connect(str(self.metadata_db_path))
        
        # Create tables
        conn.execute('''
            CREATE TABLE IF NOT EXISTS archives (
                archive_id TEXT PRIMARY KEY,
                data_type TEXT NOT NULL,
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                record_count INTEGER NOT NULL,
                compressed_size_bytes INTEGER NOT NULL,
                archive_path TEXT NOT NULL,
                created_at TEXT NOT NULL,
                checksum TEXT NOT NULL
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS retention_operations (
                operation_id TEXT PRIMARY KEY,
                operation_type TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                records_processed INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                space_saved_bytes INTEGER DEFAULT 0,
                errors TEXT
            )
        ''')
        
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_archives_data_type_period 
            ON archives(data_type, period_start, period_end)
        ''')
        
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_operations_type_date 
            ON retention_operations(operation_type, started_at)
        ''')
        
        conn.commit()
        conn.close()
        
    async def archive_old_transactions(self, 
                                     transactions: List[TransactionRecord],
                                     cutoff_date: date) -> ArchiveMetadata:
        """
        Archive old transactions to compressed storage
        
        Args:
            transactions: List of transactions to archive
            cutoff_date: Archive transactions older than this date
            
        Returns:
            ArchiveMetadata for the created archive
        """
        # Filter transactions to archive
        old_transactions = [
            t for t in transactions 
            if t.timestamp.date() < cutoff_date
        ]
        
        if not old_transactions:
            logger.info("No transactions to archive")
            return None
            
        # Create archive
        archive_id = f"transactions_{cutoff_date.isoformat()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        period_start = min(t.timestamp.date() for t in old_transactions)
        period_end = max(t.timestamp.date() for t in old_transactions)
        
        # Prepare data for archiving
        archive_data = {
            'metadata': {
                'archive_id': archive_id,
                'data_type': 'transactions',
                'period_start': period_start.isoformat(),
                'period_end': period_end.isoformat(),
                'record_count': len(old_transactions),
                'created_at': datetime.now().isoformat()
            },
            'transactions': [t.to_dict() for t in old_transactions]
        }
        
        # Write to compressed file
        archive_filename = f"{archive_id}.json.gz"
        archive_path = self.archive_storage_path / archive_filename
        
        await self._write_compressed_archive(archive_data, archive_path)
        
        # Calculate checksum and size
        checksum = await self._calculate_file_checksum(archive_path)
        compressed_size = archive_path.stat().st_size
        
        # Create metadata
        metadata = ArchiveMetadata(
            archive_id=archive_id,
            data_type='transactions',
            period_start=period_start,
            period_end=period_end,
            record_count=len(old_transactions),
            compressed_size_bytes=compressed_size,
            archive_path=str(archive_path),
            created_at=datetime.now(),
            checksum=checksum
        )
        
        # Store metadata in database
        await self._store_archive_metadata(metadata)
        
        # Create backup if enabled
        policy = self.retention_policies['transactions']
        if policy.backup_enabled:
            await self._create_backup(archive_path)
            
        logger.info(f"Archived {len(old_transactions)} transactions to {archive_filename}")
        return metadata
        
    async def archive_old_audit_records(self,
                                      audit_records: List[AuditRecord],
                                      cutoff_date: date) -> ArchiveMetadata:
        """
        Archive old audit records to compressed storage
        
        Args:
            audit_records: List of audit records to archive
            cutoff_date: Archive records older than this date
            
        Returns:
            ArchiveMetadata for the created archive
        """
        # Filter records to archive
        old_records = [
            r for r in audit_records 
            if r.timestamp.date() < cutoff_date
        ]
        
        if not old_records:
            logger.info("No audit records to archive")
            return None
            
        # Create archive
        archive_id = f"audit_records_{cutoff_date.isoformat()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        period_start = min(r.timestamp.date() for r in old_records)
        period_end = max(r.timestamp.date() for r in old_records)
        
        # Prepare data for archiving
        archive_data = {
            'metadata': {
                'archive_id': archive_id,
                'data_type': 'audit_records',
                'period_start': period_start.isoformat(),
                'period_end': period_end.isoformat(),
                'record_count': len(old_records),
                'created_at': datetime.now().isoformat()
            },
            'audit_records': [r.to_dict() for r in old_records]
        }
        
        # Write to compressed file
        archive_filename = f"{archive_id}.json.gz"
        archive_path = self.archive_storage_path / archive_filename
        
        await self._write_compressed_archive(archive_data, archive_path)
        
        # Calculate checksum and size
        checksum = await self._calculate_file_checksum(archive_path)
        compressed_size = archive_path.stat().st_size
        
        # Create metadata
        metadata = ArchiveMetadata(
            archive_id=archive_id,
            data_type='audit_records',
            period_start=period_start,
            period_end=period_end,
            record_count=len(old_records),
            compressed_size_bytes=compressed_size,
            archive_path=str(archive_path),
            created_at=datetime.now(),
            checksum=checksum
        )
        
        # Store metadata in database
        await self._store_archive_metadata(metadata)
        
        # Create backup if enabled
        policy = self.retention_policies['audit_records']
        if policy.backup_enabled:
            await self._create_backup(archive_path)
            
        logger.info(f"Archived {len(old_records)} audit records to {archive_filename}")
        return metadata
        
    async def restore_from_archive(self, archive_id: str) -> Dict[str, Any]:
        """
        Restore data from archive
        
        Args:
            archive_id: ID of archive to restore
            
        Returns:
            Restored data
        """
        # Get archive metadata
        metadata = await self._get_archive_metadata(archive_id)
        if not metadata:
            raise ValueError(f"Archive {archive_id} not found")
            
        archive_path = Path(metadata.archive_path)
        if not archive_path.exists():
            raise FileNotFoundError(f"Archive file not found: {archive_path}")
            
        # Verify checksum
        current_checksum = await self._calculate_file_checksum(archive_path)
        if current_checksum != metadata.checksum:
            raise ValueError(f"Archive checksum mismatch: {archive_id}")
            
        # Read and decompress data
        restored_data = await self._read_compressed_archive(archive_path)
        
        logger.info(f"Restored archive {archive_id} with {metadata.record_count} records")
        return restored_data
        
    async def purge_expired_data(self) -> RetentionReport:
        """
        Purge data that has exceeded retention period
        
        Returns:
            RetentionReport with operation details
        """
        operation_id = f"purge_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        started_at = datetime.now()
        
        # Find expired archives
        expired_archives = await self._find_expired_archives()
        
        success_count = 0
        failure_count = 0
        space_saved = 0
        errors = []
        
        for metadata in expired_archives:
            try:
                archive_path = Path(metadata.archive_path)
                
                # Calculate space savings
                if archive_path.exists():
                    space_saved += archive_path.stat().st_size
                    
                # Remove archive file
                if archive_path.exists():
                    archive_path.unlink()
                    
                # Remove backup if exists
                backup_path = self.backup_storage_path / archive_path.name
                if backup_path.exists():
                    backup_path.unlink()
                    
                # Remove metadata
                await self._remove_archive_metadata(metadata.archive_id)
                
                success_count += 1
                logger.info(f"Purged expired archive: {metadata.archive_id}")
                
            except Exception as e:
                failure_count += 1
                error_msg = f"Failed to purge archive {metadata.archive_id}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
                
        completed_at = datetime.now()
        
        # Create retention report
        report = RetentionReport(
            operation_id=operation_id,
            operation_type='purge',
            started_at=started_at,
            completed_at=completed_at,
            records_processed=len(expired_archives),
            success_count=success_count,
            failure_count=failure_count,
            space_saved_bytes=space_saved,
            errors=errors
        )
        
        # Store operation record
        await self._store_retention_operation(report)
        
        logger.info(f"Purge operation completed: {success_count} success, {failure_count} failures")
        return report
        
    async def run_retention_maintenance(self) -> List[RetentionReport]:
        """
        Run complete retention maintenance cycle
        
        Returns:
            List of RetentionReport objects for each operation
        """
        reports = []
        
        logger.info("Starting retention maintenance cycle")
        
        # Archive old data (simplified - would integrate with actual data sources)
        # This would typically be called with actual transaction and audit data
        
        # Purge expired archives
        purge_report = await self.purge_expired_data()
        reports.append(purge_report)
        
        # Verify archive integrity
        verification_report = await self._verify_archive_integrity()
        reports.append(verification_report)
        
        logger.info(f"Retention maintenance completed with {len(reports)} operations")
        return reports
        
    async def get_retention_statistics(self) -> Dict[str, Any]:
        """Get retention system statistics"""
        conn = sqlite3.connect(str(self.metadata_db_path))
        
        # Archive statistics
        cursor = conn.execute('''
            SELECT data_type, COUNT(*), SUM(record_count), SUM(compressed_size_bytes)
            FROM archives
            GROUP BY data_type
        ''')
        
        archive_stats = {}
        for row in cursor.fetchall():
            data_type, count, total_records, total_size = row
            archive_stats[data_type] = {
                'archive_count': count,
                'total_records': total_records or 0,
                'total_size_bytes': total_size or 0,
                'total_size_mb': (total_size or 0) / (1024 * 1024)
            }
            
        # Recent operations
        cursor = conn.execute('''
            SELECT operation_type, COUNT(*)
            FROM retention_operations
            WHERE started_at > date('now', '-30 days')
            GROUP BY operation_type
        ''')
        
        recent_operations = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            'archive_statistics': archive_stats,
            'recent_operations': recent_operations,
            'retention_policies': {k: v.to_dict() for k, v in self.retention_policies.items()},
            'storage_paths': {
                'active': str(self.active_storage_path),
                'archive': str(self.archive_storage_path),
                'backup': str(self.backup_storage_path)
            }
        }
        
    async def _write_compressed_archive(self, data: Dict, archive_path: Path):
        """Write data to compressed archive file"""
        def _write_file():
            with gzip.open(archive_path, 'wt', encoding='utf-8') as f:
                json.dump(data, f, indent=1, default=str)
                
        await asyncio.get_event_loop().run_in_executor(self.executor, _write_file)
        
    async def _read_compressed_archive(self, archive_path: Path) -> Dict:
        """Read data from compressed archive file"""
        def _read_file():
            with gzip.open(archive_path, 'rt', encoding='utf-8') as f:
                return json.load(f)
                
        return await asyncio.get_event_loop().run_in_executor(self.executor, _read_file)
        
    async def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of file"""
        import hashlib
        
        def _calculate():
            hash_sha256 = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
            
        return await asyncio.get_event_loop().run_in_executor(self.executor, _calculate)
        
    async def _create_backup(self, archive_path: Path):
        """Create backup copy of archive"""
        backup_path = self.backup_storage_path / archive_path.name
        
        def _copy_file():
            shutil.copy2(archive_path, backup_path)
            
        await asyncio.get_event_loop().run_in_executor(self.executor, _copy_file)
        logger.info(f"Created backup: {backup_path}")
        
    async def _store_archive_metadata(self, metadata: ArchiveMetadata):
        """Store archive metadata in database"""
        conn = sqlite3.connect(str(self.metadata_db_path))
        
        conn.execute('''
            INSERT INTO archives 
            (archive_id, data_type, period_start, period_end, record_count, 
             compressed_size_bytes, archive_path, created_at, checksum)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            metadata.archive_id,
            metadata.data_type,
            metadata.period_start.isoformat(),
            metadata.period_end.isoformat(),
            metadata.record_count,
            metadata.compressed_size_bytes,
            metadata.archive_path,
            metadata.created_at.isoformat(),
            metadata.checksum
        ))
        
        conn.commit()
        conn.close()
        
    async def _get_archive_metadata(self, archive_id: str) -> Optional[ArchiveMetadata]:
        """Get archive metadata from database"""
        conn = sqlite3.connect(str(self.metadata_db_path))
        
        cursor = conn.execute('''
            SELECT * FROM archives WHERE archive_id = ?
        ''', (archive_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
            
        return ArchiveMetadata(
            archive_id=row[0],
            data_type=row[1],
            period_start=date.fromisoformat(row[2]),
            period_end=date.fromisoformat(row[3]),
            record_count=row[4],
            compressed_size_bytes=row[5],
            archive_path=row[6],
            created_at=datetime.fromisoformat(row[7]),
            checksum=row[8]
        )
        
    async def _find_expired_archives(self) -> List[ArchiveMetadata]:
        """Find archives that have exceeded retention period"""
        expired_archives = []
        
        for data_type, policy in self.retention_policies.items():
            cutoff_date = datetime.now() - timedelta(days=policy.retention_years * 365)
            
            conn = sqlite3.connect(str(self.metadata_db_path))
            
            cursor = conn.execute('''
                SELECT * FROM archives 
                WHERE data_type = ? AND created_at < ?
            ''', (data_type, cutoff_date.isoformat()))
            
            for row in cursor.fetchall():
                metadata = ArchiveMetadata(
                    archive_id=row[0],
                    data_type=row[1],
                    period_start=date.fromisoformat(row[2]),
                    period_end=date.fromisoformat(row[3]),
                    record_count=row[4],
                    compressed_size_bytes=row[5],
                    archive_path=row[6],
                    created_at=datetime.fromisoformat(row[7]),
                    checksum=row[8]
                )
                expired_archives.append(metadata)
                
            conn.close()
            
        return expired_archives
        
    async def _remove_archive_metadata(self, archive_id: str):
        """Remove archive metadata from database"""
        conn = sqlite3.connect(str(self.metadata_db_path))
        
        conn.execute('''
            DELETE FROM archives WHERE archive_id = ?
        ''', (archive_id,))
        
        conn.commit()
        conn.close()
        
    async def _store_retention_operation(self, report: RetentionReport):
        """Store retention operation record"""
        conn = sqlite3.connect(str(self.metadata_db_path))
        
        conn.execute('''
            INSERT INTO retention_operations
            (operation_id, operation_type, started_at, completed_at, records_processed,
             success_count, failure_count, space_saved_bytes, errors)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            report.operation_id,
            report.operation_type,
            report.started_at.isoformat(),
            report.completed_at.isoformat(),
            report.records_processed,
            report.success_count,
            report.failure_count,
            report.space_saved_bytes,
            json.dumps(report.errors)
        ))
        
        conn.commit()
        conn.close()
        
    async def _verify_archive_integrity(self) -> RetentionReport:
        """Verify integrity of all archives"""
        operation_id = f"verify_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        started_at = datetime.now()
        
        # Get all archives
        conn = sqlite3.connect(str(self.metadata_db_path))
        cursor = conn.execute('SELECT archive_id, archive_path, checksum FROM archives')
        archives = cursor.fetchall()
        conn.close()
        
        success_count = 0
        failure_count = 0
        errors = []
        
        for archive_id, archive_path, stored_checksum in archives:
            try:
                path = Path(archive_path)
                if not path.exists():
                    errors.append(f"Archive file missing: {archive_id}")
                    failure_count += 1
                    continue
                    
                current_checksum = await self._calculate_file_checksum(path)
                if current_checksum != stored_checksum:
                    errors.append(f"Checksum mismatch: {archive_id}")
                    failure_count += 1
                else:
                    success_count += 1
                    
            except Exception as e:
                errors.append(f"Verification failed for {archive_id}: {str(e)}")
                failure_count += 1
                
        completed_at = datetime.now()
        
        report = RetentionReport(
            operation_id=operation_id,
            operation_type='verify',
            started_at=started_at,
            completed_at=completed_at,
            records_processed=len(archives),
            success_count=success_count,
            failure_count=failure_count,
            space_saved_bytes=0,
            errors=errors
        )
        
        await self._store_retention_operation(report)
        
        logger.info(f"Archive verification completed: {success_count} success, {failure_count} failures")
        return report