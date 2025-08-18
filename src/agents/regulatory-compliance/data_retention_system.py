"""
Data Retention System - Story 8.15

Manages regulatory data retention requirements including:
- 7-year data retention for financial records
- Automated archival and purging
- Data lifecycle management
- Compliance audit trails
- Secure data storage and retrieval
"""

import asyncio
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import structlog
import json
import hashlib
import gzip
import os
from pathlib import Path
import sqlite3
from collections import defaultdict

logger = structlog.get_logger(__name__)


class RetentionPolicy(Enum):
    """Data retention policies"""
    SEVEN_YEARS = "seven_years"  # 7 years for financial records
    THREE_YEARS = "three_years"  # 3 years for customer communications
    ONE_YEAR = "one_year"  # 1 year for operational logs
    INDEFINITE = "indefinite"  # Keep indefinitely
    CUSTOM = "custom"  # Custom retention period


class DataCategory(Enum):
    """Categories of data for retention"""
    TRADING_RECORDS = "trading_records"
    CUSTOMER_DATA = "customer_data"
    FINANCIAL_STATEMENTS = "financial_statements"
    TAX_DOCUMENTS = "tax_documents"
    REGULATORY_FILINGS = "regulatory_filings"
    AUDIT_TRAILS = "audit_trails"
    COMMUNICATIONS = "communications"
    SYSTEM_LOGS = "system_logs"
    COMPLIANCE_RECORDS = "compliance_records"


class DataStatus(Enum):
    """Status of retained data"""
    ACTIVE = "active"  # Currently active data
    ARCHIVED = "archived"  # Archived but accessible
    DEEP_ARCHIVE = "deep_archive"  # Long-term storage
    PENDING_DELETION = "pending_deletion"  # Marked for deletion
    DELETED = "deleted"  # Permanently deleted
    ENCRYPTED = "encrypted"  # Encrypted storage


class ArchivalMethod(Enum):
    """Methods for data archival"""
    COMPRESS = "compress"  # Compress and store locally
    CLOUD_STORAGE = "cloud_storage"  # Move to cloud storage
    TAPE_BACKUP = "tape_backup"  # Store on tape backup
    HYBRID = "hybrid"  # Combination of methods


@dataclass
class RetentionRule:
    """Data retention rule definition"""
    rule_id: str
    data_category: DataCategory
    retention_policy: RetentionPolicy
    retention_period_days: int
    archival_method: ArchivalMethod
    encryption_required: bool
    description: str
    effective_date: datetime
    created_by: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataRecord:
    """Record of data subject to retention"""
    record_id: str
    data_category: DataCategory
    record_type: str
    creation_date: datetime
    last_modified: datetime
    data_size_bytes: int
    retention_rule_id: str
    deletion_date: Optional[datetime]
    current_status: DataStatus
    storage_location: str
    checksum: str
    encrypted: bool = False
    compression_ratio: Optional[float] = None
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ArchivalJob:
    """Archival job for data retention"""
    job_id: str
    job_type: str  # 'archive', 'delete', 'migrate'
    data_records: List[str]  # Record IDs
    scheduled_date: datetime
    started_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    status: str = "pending"  # pending, running, completed, failed
    error_message: Optional[str] = None
    bytes_processed: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComplianceReport:
    """Compliance report for data retention"""
    report_id: str
    report_date: datetime
    reporting_period_start: date
    reporting_period_end: date
    total_records: int
    records_by_category: Dict[str, int]
    records_by_status: Dict[str, int]
    total_storage_bytes: int
    compliance_issues: List[str]
    archival_jobs_completed: int
    deletion_jobs_completed: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class DataRetentionSystem:
    """Main data retention management system"""
    
    # Standard retention periods (in days)
    RETENTION_PERIODS = {
        RetentionPolicy.SEVEN_YEARS: 7 * 365,  # 7 years
        RetentionPolicy.THREE_YEARS: 3 * 365,  # 3 years
        RetentionPolicy.ONE_YEAR: 365,  # 1 year
        RetentionPolicy.INDEFINITE: None  # Never delete
    }
    
    def __init__(self, storage_base_path: Path):
        self.storage_base_path = storage_base_path
        self.retention_rules: Dict[str, RetentionRule] = {}
        self.data_records: Dict[str, DataRecord] = {}
        self.archival_jobs: List[ArchivalJob] = []
        self.compliance_reports: List[ComplianceReport] = []
        self.storage_manager = StorageManager(storage_base_path)
        self.archival_engine = ArchivalEngine()
        self.compliance_monitor = ComplianceMonitor()
        self.db_path = storage_base_path / "retention.db"
        
    async def initialize(self):
        """Initialize data retention system"""
        logger.info("Initializing data retention system")
        
        # Create storage directories
        self.storage_base_path.mkdir(parents=True, exist_ok=True)
        (self.storage_base_path / "active").mkdir(exist_ok=True)
        (self.storage_base_path / "archived").mkdir(exist_ok=True)
        (self.storage_base_path / "deep_archive").mkdir(exist_ok=True)
        
        # Initialize database
        await self._initialize_database()
        
        # Load default retention rules
        await self._load_default_retention_rules()
        
        await self.storage_manager.initialize()
        await self.archival_engine.initialize()
        await self.compliance_monitor.initialize()
        
    async def _initialize_database(self):
        """Initialize SQLite database for retention tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS retention_rules (
                rule_id TEXT PRIMARY KEY,
                data_category TEXT,
                retention_policy TEXT,
                retention_period_days INTEGER,
                archival_method TEXT,
                encryption_required BOOLEAN,
                description TEXT,
                effective_date TIMESTAMP,
                created_by TEXT,
                metadata TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS data_records (
                record_id TEXT PRIMARY KEY,
                data_category TEXT,
                record_type TEXT,
                creation_date TIMESTAMP,
                last_modified TIMESTAMP,
                data_size_bytes INTEGER,
                retention_rule_id TEXT,
                deletion_date TIMESTAMP,
                current_status TEXT,
                storage_location TEXT,
                checksum TEXT,
                encrypted BOOLEAN,
                compression_ratio REAL,
                access_count INTEGER,
                last_accessed TIMESTAMP,
                metadata TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS archival_jobs (
                job_id TEXT PRIMARY KEY,
                job_type TEXT,
                data_records TEXT,
                scheduled_date TIMESTAMP,
                started_date TIMESTAMP,
                completed_date TIMESTAMP,
                status TEXT,
                error_message TEXT,
                bytes_processed INTEGER,
                metadata TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        
    async def _load_default_retention_rules(self):
        """Load default retention rules"""
        default_rules = [
            RetentionRule(
                rule_id="trading_records_7yr",
                data_category=DataCategory.TRADING_RECORDS,
                retention_policy=RetentionPolicy.SEVEN_YEARS,
                retention_period_days=self.RETENTION_PERIODS[RetentionPolicy.SEVEN_YEARS],
                archival_method=ArchivalMethod.HYBRID,
                encryption_required=True,
                description="Trading records - 7 year retention",
                effective_date=datetime.now(),
                created_by="system"
            ),
            RetentionRule(
                rule_id="tax_docs_7yr",
                data_category=DataCategory.TAX_DOCUMENTS,
                retention_policy=RetentionPolicy.SEVEN_YEARS,
                retention_period_days=self.RETENTION_PERIODS[RetentionPolicy.SEVEN_YEARS],
                archival_method=ArchivalMethod.COMPRESS,
                encryption_required=True,
                description="Tax documents - 7 year retention",
                effective_date=datetime.now(),
                created_by="system"
            ),
            RetentionRule(
                rule_id="customer_data_7yr",
                data_category=DataCategory.CUSTOMER_DATA,
                retention_policy=RetentionPolicy.SEVEN_YEARS,
                retention_period_days=self.RETENTION_PERIODS[RetentionPolicy.SEVEN_YEARS],
                archival_method=ArchivalMethod.CLOUD_STORAGE,
                encryption_required=True,
                description="Customer data - 7 year retention",
                effective_date=datetime.now(),
                created_by="system"
            ),
            RetentionRule(
                rule_id="audit_trails_indefinite",
                data_category=DataCategory.AUDIT_TRAILS,
                retention_policy=RetentionPolicy.INDEFINITE,
                retention_period_days=0,  # Indefinite
                archival_method=ArchivalMethod.HYBRID,
                encryption_required=True,
                description="Audit trails - indefinite retention",
                effective_date=datetime.now(),
                created_by="system"
            )
        ]
        
        for rule in default_rules:
            self.retention_rules[rule.rule_id] = rule
            await self._save_retention_rule(rule)
            
    async def _save_retention_rule(self, rule: RetentionRule):
        """Save retention rule to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO retention_rules VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            rule.rule_id, rule.data_category.value, rule.retention_policy.value,
            rule.retention_period_days, rule.archival_method.value,
            rule.encryption_required, rule.description,
            rule.effective_date, rule.created_by, json.dumps(rule.metadata)
        ))
        
        conn.commit()
        conn.close()
        
    async def register_data_record(self, record_type: str, data_category: DataCategory,
                                  data_content: bytes, metadata: Dict[str, Any] = None) -> DataRecord:
        """Register data for retention management"""
        # Find applicable retention rule
        retention_rule = await self._find_retention_rule(data_category)
        
        if not retention_rule:
            raise ValueError(f"No retention rule found for category: {data_category}")
        
        # Calculate checksum
        checksum = hashlib.sha256(data_content).hexdigest()
        
        # Determine deletion date
        deletion_date = None
        if retention_rule.retention_period_days > 0:
            deletion_date = datetime.now() + timedelta(days=retention_rule.retention_period_days)
        
        # Create data record
        record = DataRecord(
            record_id=f"rec_{datetime.now().timestamp()}_{checksum[:8]}",
            data_category=data_category,
            record_type=record_type,
            creation_date=datetime.now(),
            last_modified=datetime.now(),
            data_size_bytes=len(data_content),
            retention_rule_id=retention_rule.rule_id,
            deletion_date=deletion_date,
            current_status=DataStatus.ACTIVE,
            storage_location="",  # Will be set by storage manager
            checksum=checksum,
            encrypted=retention_rule.encryption_required,
            metadata=metadata or {}
        )
        
        # Store the data
        storage_location = await self.storage_manager.store_data(
            record.record_id, data_content, record.encrypted
        )
        record.storage_location = storage_location
        
        # Save record
        self.data_records[record.record_id] = record
        await self._save_data_record(record)
        
        logger.info(f"Registered data record: {record.record_id}")
        return record
        
    async def _find_retention_rule(self, data_category: DataCategory) -> Optional[RetentionRule]:
        """Find applicable retention rule for data category"""
        for rule in self.retention_rules.values():
            if rule.data_category == data_category:
                return rule
        return None
        
    async def _save_data_record(self, record: DataRecord):
        """Save data record to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO data_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            record.record_id, record.data_category.value, record.record_type,
            record.creation_date, record.last_modified, record.data_size_bytes,
            record.retention_rule_id, record.deletion_date, record.current_status.value,
            record.storage_location, record.checksum, record.encrypted,
            record.compression_ratio, record.access_count, record.last_accessed,
            json.dumps(record.metadata)
        ))
        
        conn.commit()
        conn.close()
        
    async def retrieve_data_record(self, record_id: str) -> Optional[bytes]:
        """Retrieve data record by ID"""
        if record_id not in self.data_records:
            return None
        
        record = self.data_records[record_id]
        
        # Update access tracking
        record.access_count += 1
        record.last_accessed = datetime.now()
        await self._save_data_record(record)
        
        # Retrieve from storage
        data = await self.storage_manager.retrieve_data(record.storage_location, record.encrypted)
        
        logger.info(f"Retrieved data record: {record_id}")
        return data
        
    async def schedule_archival_jobs(self):
        """Schedule archival jobs for data due for archival"""
        current_time = datetime.now()
        
        # Find records due for archival (active records older than 1 year)
        archival_candidates = []
        for record in self.data_records.values():
            if (record.current_status == DataStatus.ACTIVE and
                (current_time - record.creation_date).days > 365):
                archival_candidates.append(record.record_id)
        
        if archival_candidates:
            job = ArchivalJob(
                job_id=f"archive_{current_time.timestamp()}",
                job_type="archive",
                data_records=archival_candidates,
                scheduled_date=current_time
            )
            
            self.archival_jobs.append(job)
            await self._save_archival_job(job)
            
            logger.info(f"Scheduled archival job: {job.job_id} for {len(archival_candidates)} records")
        
        # Find records due for deletion
        deletion_candidates = []
        for record in self.data_records.values():
            if (record.deletion_date and
                record.deletion_date <= current_time and
                record.current_status != DataStatus.PENDING_DELETION):
                deletion_candidates.append(record.record_id)
        
        if deletion_candidates:
            job = ArchivalJob(
                job_id=f"delete_{current_time.timestamp()}",
                job_type="delete",
                data_records=deletion_candidates,
                scheduled_date=current_time
            )
            
            self.archival_jobs.append(job)
            await self._save_archival_job(job)
            
            logger.info(f"Scheduled deletion job: {job.job_id} for {len(deletion_candidates)} records")
            
    async def _save_archival_job(self, job: ArchivalJob):
        """Save archival job to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO archival_jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            job.job_id, job.job_type, json.dumps(job.data_records),
            job.scheduled_date, job.started_date, job.completed_date,
            job.status, job.error_message, job.bytes_processed,
            json.dumps(job.metadata)
        ))
        
        conn.commit()
        conn.close()
        
    async def execute_archival_jobs(self):
        """Execute pending archival jobs"""
        pending_jobs = [job for job in self.archival_jobs if job.status == "pending"]
        
        for job in pending_jobs:
            try:
                job.status = "running"
                job.started_date = datetime.now()
                await self._save_archival_job(job)
                
                if job.job_type == "archive":
                    await self._execute_archive_job(job)
                elif job.job_type == "delete":
                    await self._execute_delete_job(job)
                
                job.status = "completed"
                job.completed_date = datetime.now()
                
            except Exception as e:
                job.status = "failed"
                job.error_message = str(e)
                logger.error(f"Archival job failed: {job.job_id} - {e}")
            
            await self._save_archival_job(job)
            
    async def _execute_archive_job(self, job: ArchivalJob):
        """Execute archive job"""
        bytes_processed = 0
        
        for record_id in job.data_records:
            if record_id in self.data_records:
                record = self.data_records[record_id]
                
                # Archive the data
                await self.archival_engine.archive_record(record)
                
                # Update record status
                record.current_status = DataStatus.ARCHIVED
                await self._save_data_record(record)
                
                bytes_processed += record.data_size_bytes
        
        job.bytes_processed = bytes_processed
        logger.info(f"Archived {len(job.data_records)} records, {bytes_processed} bytes")
        
    async def _execute_delete_job(self, job: ArchivalJob):
        """Execute delete job"""
        bytes_processed = 0
        
        for record_id in job.data_records:
            if record_id in self.data_records:
                record = self.data_records[record_id]
                
                # Delete the data
                await self.storage_manager.delete_data(record.storage_location)
                
                # Update record status
                record.current_status = DataStatus.DELETED
                await self._save_data_record(record)
                
                bytes_processed += record.data_size_bytes
        
        job.bytes_processed = bytes_processed
        logger.info(f"Deleted {len(job.data_records)} records, {bytes_processed} bytes")
        
    async def generate_compliance_report(self, period_start: date, period_end: date) -> ComplianceReport:
        """Generate compliance report for data retention"""
        # Count records by category and status
        records_by_category = defaultdict(int)
        records_by_status = defaultdict(int)
        total_storage_bytes = 0
        compliance_issues = []
        
        for record in self.data_records.values():
            if period_start <= record.creation_date.date() <= period_end:
                records_by_category[record.data_category.value] += 1
                records_by_status[record.current_status.value] += 1
                total_storage_bytes += record.data_size_bytes
                
                # Check for compliance issues
                if record.deletion_date and record.deletion_date < datetime.now():
                    if record.current_status != DataStatus.DELETED:
                        compliance_issues.append(f"Record {record.record_id} past deletion date but not deleted")
        
        # Count completed archival jobs
        archival_jobs_completed = len([
            job for job in self.archival_jobs
            if job.job_type == "archive" and job.status == "completed"
            and period_start <= job.completed_date.date() <= period_end
        ])
        
        deletion_jobs_completed = len([
            job for job in self.archival_jobs
            if job.job_type == "delete" and job.status == "completed"
            and period_start <= job.completed_date.date() <= period_end
        ])
        
        report = ComplianceReport(
            report_id=f"compliance_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            report_date=datetime.now(),
            reporting_period_start=period_start,
            reporting_period_end=period_end,
            total_records=len(self.data_records),
            records_by_category=dict(records_by_category),
            records_by_status=dict(records_by_status),
            total_storage_bytes=total_storage_bytes,
            compliance_issues=compliance_issues,
            archival_jobs_completed=archival_jobs_completed,
            deletion_jobs_completed=deletion_jobs_completed
        )
        
        self.compliance_reports.append(report)
        logger.info(f"Generated compliance report: {report.report_id}")
        
        return report
        
    async def get_retention_summary(self) -> Dict[str, Any]:
        """Get summary of data retention system"""
        total_records = len(self.data_records)
        total_storage = sum(record.data_size_bytes for record in self.data_records.values())
        
        status_counts = defaultdict(int)
        category_counts = defaultdict(int)
        
        for record in self.data_records.values():
            status_counts[record.current_status.value] += 1
            category_counts[record.data_category.value] += 1
        
        pending_jobs = len([job for job in self.archival_jobs if job.status == "pending"])
        
        return {
            'total_records': total_records,
            'total_storage_bytes': total_storage,
            'total_storage_mb': round(total_storage / (1024 * 1024), 2),
            'records_by_status': dict(status_counts),
            'records_by_category': dict(category_counts),
            'retention_rules_count': len(self.retention_rules),
            'pending_archival_jobs': pending_jobs,
            'total_archival_jobs': len(self.archival_jobs)
        }


class StorageManager:
    """Manages data storage and retrieval"""
    
    def __init__(self, base_path: Path):
        self.base_path = base_path
        
    async def initialize(self):
        """Initialize storage manager"""
        logger.info("Initialized storage manager")
        
    async def store_data(self, record_id: str, data: bytes, encrypt: bool = False) -> str:
        """Store data and return storage location"""
        storage_dir = self.base_path / "active"
        storage_file = storage_dir / f"{record_id}.dat"
        
        if encrypt:
            # Simple encryption (in production, use proper encryption)
            data = self._encrypt_data(data)
            storage_file = storage_dir / f"{record_id}.enc"
        
        with open(storage_file, 'wb') as f:
            f.write(data)
        
        return str(storage_file)
        
    async def retrieve_data(self, storage_location: str, encrypted: bool = False) -> bytes:
        """Retrieve data from storage location"""
        with open(storage_location, 'rb') as f:
            data = f.read()
        
        if encrypted:
            data = self._decrypt_data(data)
        
        return data
        
    async def delete_data(self, storage_location: str):
        """Delete data from storage"""
        if os.path.exists(storage_location):
            os.remove(storage_location)
            
    def _encrypt_data(self, data: bytes) -> bytes:
        """Simple encryption (use proper encryption in production)"""
        # This is a placeholder - use proper encryption like AES
        return data  # For now, just return original data
        
    def _decrypt_data(self, data: bytes) -> bytes:
        """Simple decryption (use proper decryption in production)"""
        # This is a placeholder - use proper decryption
        return data  # For now, just return original data


class ArchivalEngine:
    """Handles data archival operations"""
    
    def __init__(self):
        pass
        
    async def initialize(self):
        """Initialize archival engine"""
        logger.info("Initialized archival engine")
        
    async def archive_record(self, record: DataRecord):
        """Archive a data record"""
        # Move from active to archived storage
        # Implement compression, cloud storage, etc.
        
        logger.info(f"Archived record: {record.record_id}")
        
    async def compress_data(self, data: bytes) -> Tuple[bytes, float]:
        """Compress data and return compressed data with ratio"""
        compressed_data = gzip.compress(data)
        compression_ratio = len(compressed_data) / len(data)
        
        return compressed_data, compression_ratio


class ComplianceMonitor:
    """Monitors compliance with retention policies"""
    
    def __init__(self):
        pass
        
    async def initialize(self):
        """Initialize compliance monitor"""
        logger.info("Initialized compliance monitor")
        
    async def check_compliance(self, data_records: Dict[str, DataRecord]) -> List[str]:
        """Check compliance issues"""
        issues = []
        current_time = datetime.now()
        
        for record in data_records.values():
            # Check if record is past deletion date
            if (record.deletion_date and
                record.deletion_date < current_time and
                record.current_status != DataStatus.DELETED):
                issues.append(f"Record {record.record_id} past deletion date")
        
        return issues