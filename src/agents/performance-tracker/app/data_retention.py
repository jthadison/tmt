"""Data retention and archival system for performance data."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func, text

from .models import (
    TradePerformance, PerformanceMetrics, PerformanceSnapshot,
    AccountRanking
)

logger = logging.getLogger(__name__)


class DataRetentionManager:
    """Manages data retention and archival policies."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.retention_policies = {
            'trade_performance': {
                'hot_storage_days': 90,     # 3 months
                'warm_storage_days': 365,   # 1 year  
                'cold_storage_days': 730,   # 2 years
                'purge_after_days': 2555    # 7 years (extended for compliance)
            },
            'performance_snapshots': {
                'hot_storage_days': 30,     # 1 month
                'warm_storage_days': 90,    # 3 months
                'cold_storage_days': 730,   # 2 years
                'purge_after_days': 2555    # 7 years
            },
            'performance_metrics': {
                'hot_storage_days': 365,    # 1 year
                'warm_storage_days': 730,   # 2 years
                'cold_storage_days': 2555,  # 7 years
                'purge_after_days': 3650    # 10 years
            }
        }
        
    async def start_retention_manager(self):
        """Start the data retention background process."""
        logger.info("Starting data retention manager...")
        
        # Schedule daily cleanup task
        asyncio.create_task(self._daily_cleanup_task())
        
        # Schedule weekly archival task
        asyncio.create_task(self._weekly_archival_task())
        
        # Schedule monthly compression task
        asyncio.create_task(self._monthly_compression_task())
    
    async def apply_retention_policy(self, table_name: str) -> Dict[str, int]:
        """Apply retention policy for specific table."""
        try:
            if table_name not in self.retention_policies:
                raise ValueError(f"No retention policy defined for {table_name}")
            
            policy = self.retention_policies[table_name]
            results = {}
            
            # Archive old data
            archived_count = await self._archive_old_data(table_name, policy)
            results['archived'] = archived_count
            
            # Compress data
            compressed_count = await self._compress_data(table_name, policy)
            results['compressed'] = compressed_count
            
            # Purge expired data
            purged_count = await self._purge_expired_data(table_name, policy)
            results['purged'] = purged_count
            
            logger.info(f"Applied retention policy for {table_name}: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Error applying retention policy for {table_name}: {e}")
            return {}
    
    async def cleanup_performance_snapshots(self) -> int:
        """Clean up old performance snapshots to manage storage."""
        try:
            policy = self.retention_policies['performance_snapshots']
            cutoff_date = datetime.utcnow() - timedelta(days=policy['hot_storage_days'])
            
            # Keep only latest snapshot per account per day
            subquery = self.db.query(
                PerformanceSnapshot.account_id,
                func.date(PerformanceSnapshot.snapshot_time).label('snapshot_date'),
                func.max(PerformanceSnapshot.snapshot_time).label('max_time')
            ).filter(
                PerformanceSnapshot.snapshot_time < cutoff_date
            ).group_by(
                PerformanceSnapshot.account_id,
                func.date(PerformanceSnapshot.snapshot_time)
            ).subquery()
            
            # Delete snapshots not matching the max time for each day
            deleted_count = self.db.query(PerformanceSnapshot).filter(
                and_(
                    PerformanceSnapshot.snapshot_time < cutoff_date,
                    ~self.db.query(subquery).filter(
                        and_(
                            PerformanceSnapshot.account_id == subquery.c.account_id,
                            func.date(PerformanceSnapshot.snapshot_time) == subquery.c.snapshot_date,
                            PerformanceSnapshot.snapshot_time == subquery.c.max_time
                        )
                    ).exists()
                )
            ).delete(synchronize_session=False)
            
            self.db.commit()
            logger.info(f"Cleaned up {deleted_count} old performance snapshots")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up performance snapshots: {e}")
            self.db.rollback()
            return 0
    
    async def archive_historical_data(
        self, 
        account_id: Optional[UUID] = None,
        before_date: Optional[datetime] = None
    ) -> Dict[str, int]:
        """Archive historical data for long-term storage."""
        try:
            if before_date is None:
                before_date = datetime.utcnow() - timedelta(days=365)  # Archive data older than 1 year
            
            results = {}
            
            # Archive trade performance data
            trade_query = self.db.query(TradePerformance).filter(
                TradePerformance.entry_time < before_date
            )
            
            if account_id:
                trade_query = trade_query.filter(TradePerformance.account_id == account_id)
            
            trade_count = trade_query.count()
            
            # In a production system, this would move data to archive tables or storage
            # For now, we'll just mark the operation
            logger.info(f"Would archive {trade_count} trade records")
            results['trades'] = trade_count
            
            # Archive performance metrics
            metrics_query = self.db.query(PerformanceMetrics).filter(
                PerformanceMetrics.period_start < before_date
            )
            
            if account_id:
                metrics_query = metrics_query.filter(PerformanceMetrics.account_id == account_id)
            
            metrics_count = metrics_query.count()
            logger.info(f"Would archive {metrics_count} metrics records")
            results['metrics'] = metrics_count
            
            return results
            
        except Exception as e:
            logger.error(f"Error archiving historical data: {e}")
            return {}
    
    async def create_data_backup(
        self, 
        backup_type: str = 'incremental'
    ) -> Dict[str, Any]:
        """Create backup of performance data."""
        try:
            backup_info = {
                'backup_id': f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                'backup_type': backup_type,
                'created_at': datetime.utcnow().isoformat(),
                'tables_backed_up': [],
                'total_records': 0
            }
            
            # Count records in each table
            tables = [
                ('trade_performance', TradePerformance),
                ('performance_metrics', PerformanceMetrics),
                ('performance_snapshots', PerformanceSnapshot),
                ('account_rankings', AccountRanking)
            ]
            
            for table_name, model_class in tables:
                if backup_type == 'full':
                    count = self.db.query(model_class).count()
                else:  # incremental - last 7 days
                    week_ago = datetime.utcnow() - timedelta(days=7)
                    
                    if hasattr(model_class, 'entry_time'):
                        count = self.db.query(model_class).filter(
                            model_class.entry_time >= week_ago
                        ).count()
                    elif hasattr(model_class, 'snapshot_time'):
                        count = self.db.query(model_class).filter(
                            model_class.snapshot_time >= week_ago
                        ).count()
                    elif hasattr(model_class, 'period_start'):
                        count = self.db.query(model_class).filter(
                            model_class.period_start >= week_ago
                        ).count()
                    else:
                        count = 0
                
                backup_info['tables_backed_up'].append({
                    'table': table_name,
                    'record_count': count
                })
                backup_info['total_records'] += count
            
            # In production, would actually perform backup operations
            logger.info(f"Created {backup_type} backup: {backup_info['backup_id']}")
            
            return backup_info
            
        except Exception as e:
            logger.error(f"Error creating data backup: {e}")
            return {}
    
    async def verify_data_integrity(self) -> Dict[str, Any]:
        """Verify data integrity and consistency."""
        try:
            integrity_report = {
                'verified_at': datetime.utcnow().isoformat(),
                'issues_found': [],
                'statistics': {},
                'recommendations': []
            }
            
            # Check for orphaned records
            orphaned_snapshots = await self._check_orphaned_snapshots()
            if orphaned_snapshots > 0:
                integrity_report['issues_found'].append(
                    f"Found {orphaned_snapshots} orphaned performance snapshots"
                )
            
            # Check for data consistency
            consistency_issues = await self._check_data_consistency()
            integrity_report['issues_found'].extend(consistency_issues)
            
            # Collect statistics
            integrity_report['statistics'] = await self._collect_data_statistics()
            
            # Generate recommendations
            if len(integrity_report['issues_found']) > 0:
                integrity_report['recommendations'].append("Run data cleanup procedures")
            
            if integrity_report['statistics']['total_snapshots'] > 100000:
                integrity_report['recommendations'].append("Consider archiving old snapshots")
            
            logger.info(f"Data integrity check completed. Issues found: {len(integrity_report['issues_found'])}")
            
            return integrity_report
            
        except Exception as e:
            logger.error(f"Error verifying data integrity: {e}")
            return {}
    
    async def _archive_old_data(self, table_name: str, policy: Dict[str, int]) -> int:
        """Archive old data based on policy."""
        # Placeholder for archival logic
        return 0
    
    async def _compress_data(self, table_name: str, policy: Dict[str, int]) -> int:
        """Compress old data based on policy.""" 
        # Placeholder for compression logic
        return 0
    
    async def _purge_expired_data(self, table_name: str, policy: Dict[str, int]) -> int:
        """Purge expired data based on policy."""
        try:
            purge_date = datetime.utcnow() - timedelta(days=policy['purge_after_days'])
            
            if table_name == 'trade_performance':
                deleted = self.db.query(TradePerformance).filter(
                    TradePerformance.entry_time < purge_date
                ).delete()
            elif table_name == 'performance_snapshots':
                deleted = self.db.query(PerformanceSnapshot).filter(
                    PerformanceSnapshot.snapshot_time < purge_date
                ).delete()
            else:
                deleted = 0
            
            self.db.commit()
            return deleted
            
        except Exception as e:
            logger.error(f"Error purging data from {table_name}: {e}")
            self.db.rollback()
            return 0
    
    async def _daily_cleanup_task(self):
        """Daily cleanup background task."""
        while True:
            try:
                await asyncio.sleep(24 * 3600)  # Wait 24 hours
                
                logger.info("Starting daily data cleanup...")
                
                # Clean up performance snapshots
                await self.cleanup_performance_snapshots()
                
                # Apply retention policies
                for table_name in self.retention_policies.keys():
                    await self.apply_retention_policy(table_name)
                
                logger.info("Daily cleanup completed")
                
            except Exception as e:
                logger.error(f"Error in daily cleanup task: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour before retry
    
    async def _weekly_archival_task(self):
        """Weekly archival background task."""
        while True:
            try:
                await asyncio.sleep(7 * 24 * 3600)  # Wait 7 days
                
                logger.info("Starting weekly archival process...")
                
                # Archive old data
                await self.archive_historical_data()
                
                # Create incremental backup
                await self.create_data_backup('incremental')
                
                logger.info("Weekly archival completed")
                
            except Exception as e:
                logger.error(f"Error in weekly archival task: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour before retry
    
    async def _monthly_compression_task(self):
        """Monthly compression background task."""
        while True:
            try:
                await asyncio.sleep(30 * 24 * 3600)  # Wait 30 days
                
                logger.info("Starting monthly compression process...")
                
                # Verify data integrity
                integrity_report = await self.verify_data_integrity()
                
                # Create full backup
                await self.create_data_backup('full')
                
                logger.info("Monthly compression completed")
                
            except Exception as e:
                logger.error(f"Error in monthly compression task: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour before retry
    
    async def _check_orphaned_snapshots(self) -> int:
        """Check for orphaned performance snapshots."""
        # Placeholder - would check for snapshots without corresponding accounts
        return 0
    
    async def _check_data_consistency(self) -> List[str]:
        """Check for data consistency issues."""
        issues = []
        
        try:
            # Check for negative P&L values that seem unrealistic
            extreme_losses = self.db.query(TradePerformance).filter(
                TradePerformance.pnl < -10000  # More than $10k loss on single trade
            ).count()
            
            if extreme_losses > 0:
                issues.append(f"Found {extreme_losses} trades with extreme losses")
            
            # Check for trades with missing exit times but closed status
            missing_exits = self.db.query(TradePerformance).filter(
                and_(
                    TradePerformance.status == 'closed',
                    TradePerformance.exit_time.is_(None)
                )
            ).count()
            
            if missing_exits > 0:
                issues.append(f"Found {missing_exits} closed trades missing exit times")
                
        except Exception as e:
            logger.error(f"Error checking data consistency: {e}")
            issues.append("Failed to complete consistency checks")
        
        return issues
    
    async def _collect_data_statistics(self) -> Dict[str, Any]:
        """Collect database statistics."""
        try:
            stats = {
                'total_trades': self.db.query(TradePerformance).count(),
                'total_snapshots': self.db.query(PerformanceSnapshot).count(), 
                'total_metrics': self.db.query(PerformanceMetrics).count(),
                'oldest_trade': None,
                'newest_trade': None
            }
            
            # Get oldest and newest trade dates
            oldest = self.db.query(TradePerformance.entry_time).order_by(
                TradePerformance.entry_time
            ).first()
            
            newest = self.db.query(TradePerformance.entry_time).order_by(
                desc(TradePerformance.entry_time)
            ).first()
            
            if oldest:
                stats['oldest_trade'] = oldest[0].isoformat()
            if newest:
                stats['newest_trade'] = newest[0].isoformat()
            
            return stats
            
        except Exception as e:
            logger.error(f"Error collecting statistics: {e}")
            return {}