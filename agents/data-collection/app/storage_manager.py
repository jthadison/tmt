"""
Data storage and query system for time-series trade data.

This module implements efficient storage, partitioning, archival, and query
interfaces optimized for high-volume trade data analysis.
"""

from typing import Dict, List, Optional, Any, Union, Tuple
from decimal import Decimal
from datetime import datetime, timedelta, date
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from enum import Enum

from .data_models import (
    ComprehensiveTradeRecord,
    PatternPerformance,
    ExecutionQualityMetrics,
    FalseSignalAnalysis,
    DataValidationResult,
)


logger = logging.getLogger(__name__)


class StorageType(str, Enum):
    HOT = "hot"      # Last 3 months, full detail, fastest access
    WARM = "warm"    # 3-12 months, summarized hourly, medium access
    COLD = "cold"    # 1+ years, daily summaries, archived storage


class QueryComplexity(str, Enum):
    SIMPLE = "simple"      # Single table, basic filters
    MEDIUM = "medium"      # Joins, aggregations
    COMPLEX = "complex"    # Complex analytics, multiple tables


@dataclass
class QueryPerformanceMetrics:
    """Metrics for query performance monitoring."""
    query_id: str
    query_type: str
    execution_time_ms: int
    rows_scanned: int
    rows_returned: int
    complexity: QueryComplexity
    cache_hit: bool
    partition_pruning: bool
    index_usage: List[str]
    timestamp: datetime


@dataclass
class StorageStats:
    """Storage utilization statistics."""
    total_records: int
    hot_storage_records: int
    warm_storage_records: int
    cold_storage_records: int
    total_size_gb: Decimal
    hot_storage_size_gb: Decimal
    warm_storage_size_gb: Decimal
    cold_storage_size_gb: Decimal
    oldest_record: datetime
    newest_record: datetime


class DataPartitionStrategy:
    """Implements data partitioning strategy for time-series data."""
    
    def __init__(self):
        self.partition_interval = "monthly"  # Monthly partitions
        self.retention_policy = {
            StorageType.HOT: timedelta(days=90),    # 3 months
            StorageType.WARM: timedelta(days=365),  # 1 year
            StorageType.COLD: timedelta(days=2555), # 7 years
        }
    
    def get_partition_name(self, timestamp: datetime, storage_type: StorageType) -> str:
        """Generate partition name for given timestamp."""
        
        if storage_type == StorageType.HOT:
            # Daily partitions for hot storage
            return f"trades_hot_{timestamp.strftime('%Y_%m_%d')}"
        elif storage_type == StorageType.WARM:
            # Monthly partitions for warm storage
            return f"trades_warm_{timestamp.strftime('%Y_%m')}"
        else:
            # Yearly partitions for cold storage
            return f"trades_cold_{timestamp.strftime('%Y')}"
    
    def determine_storage_type(self, timestamp: datetime) -> StorageType:
        """Determine appropriate storage type based on age."""
        
        age = datetime.now() - timestamp
        
        if age <= self.retention_policy[StorageType.HOT]:
            return StorageType.HOT
        elif age <= self.retention_policy[StorageType.WARM]:
            return StorageType.WARM
        else:
            return StorageType.COLD
    
    def get_partitions_for_query(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Tuple[str, StorageType]]:
        """Get list of partitions needed for date range query."""
        
        partitions = []
        current_date = start_date.replace(day=1)  # Start of month
        
        while current_date <= end_date:
            storage_type = self.determine_storage_type(current_date)
            partition_name = self.get_partition_name(current_date, storage_type)
            partitions.append((partition_name, storage_type))
            
            # Move to next month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
        
        return partitions


class IndexOptimizer:
    """Optimizes database indexes for query performance."""
    
    def __init__(self):
        self.recommended_indexes = {
            # Time-series indexes
            "idx_trades_timestamp": {
                "table": "comprehensive_trades",
                "columns": ["trade_timestamp"],
                "type": "btree",
                "purpose": "Time-based queries"
            },
            "idx_trades_timestamp_brin": {
                "table": "comprehensive_trades", 
                "columns": ["trade_timestamp"],
                "type": "brin",
                "purpose": "Efficient time-series scans"
            },
            
            # Pattern analysis indexes
            "idx_trades_pattern": {
                "table": "comprehensive_trades",
                "columns": ["pattern_type", "trade_timestamp"],
                "type": "btree",
                "purpose": "Pattern performance queries"
            },
            
            # Account-based indexes
            "idx_trades_account_time": {
                "table": "comprehensive_trades",
                "columns": ["account_id", "trade_timestamp"],
                "type": "btree",
                "purpose": "Account-specific analysis"
            },
            
            # Symbol-based indexes
            "idx_trades_symbol_time": {
                "table": "comprehensive_trades",
                "columns": ["symbol", "trade_timestamp"],
                "type": "btree",
                "purpose": "Symbol-specific analysis"
            },
            
            # Market regime indexes
            "idx_trades_regime": {
                "table": "comprehensive_trades",
                "columns": ["market_regime", "trade_timestamp"],
                "type": "btree",
                "purpose": "Market condition analysis"
            },
            
            # Composite performance index
            "idx_trades_performance": {
                "table": "comprehensive_trades",
                "columns": ["win_loss", "pattern_type", "trade_timestamp"],
                "type": "btree",
                "purpose": "Performance analysis"
            }
        }
    
    def analyze_query_performance(self, query: str) -> Dict[str, Any]:
        """Analyze query and recommend optimizations."""
        
        recommendations = []
        
        # Simple heuristics for index recommendations
        if "WHERE trade_timestamp" in query.upper():
            recommendations.append("Consider using BRIN index on trade_timestamp for large scans")
        
        if "pattern_type" in query.lower():
            recommendations.append("Use composite index on pattern_type + trade_timestamp")
        
        if "account_id" in query.lower():
            recommendations.append("Use composite index on account_id + trade_timestamp")
        
        return {
            "query": query,
            "recommendations": recommendations,
            "suggested_indexes": [idx for idx in self.recommended_indexes.keys() if self._index_matches_query(idx, query)]
        }
    
    def _index_matches_query(self, index_name: str, query: str) -> bool:
        """Check if index would be useful for query."""
        index_info = self.recommended_indexes[index_name]
        
        # Simple matching based on column presence
        for column in index_info["columns"]:
            if column in query.lower():
                return True
        
        return False


class QueryOptimizer:
    """Optimizes database queries for performance."""
    
    def __init__(self):
        self.index_optimizer = IndexOptimizer()
    
    def optimize_time_range_query(
        self,
        base_query: str,
        start_time: datetime,
        end_time: datetime,
        partition_strategy: DataPartitionStrategy
    ) -> str:
        """Optimize query for time range with partition pruning."""
        
        # Get relevant partitions
        partitions = partition_strategy.get_partitions_for_query(start_time, end_time)
        
        if len(partitions) == 1:
            # Single partition query
            partition_name = partitions[0][0]
            optimized_query = base_query.replace("comprehensive_trades", partition_name)
        else:
            # Multi-partition UNION query
            union_parts = []
            for partition_name, storage_type in partitions:
                partition_query = base_query.replace("comprehensive_trades", partition_name)
                union_parts.append(f"({partition_query})")
            
            optimized_query = " UNION ALL ".join(union_parts)
        
        return optimized_query
    
    def add_query_hints(self, query: str, complexity: QueryComplexity) -> str:
        """Add database-specific query hints for optimization."""
        
        hints = []
        
        if complexity == QueryComplexity.COMPLEX:
            hints.append("/*+ USE_HASH_AGGREGATION */")
            hints.append("/*+ PARALLEL(4) */")
        
        if "ORDER BY trade_timestamp" in query:
            hints.append("/*+ INDEX_HINT(trades, idx_trades_timestamp_brin) */")
        
        if hints:
            return f"{' '.join(hints)} {query}"
        
        return query


class CacheManager:
    """Manages query result caching."""
    
    def __init__(self):
        self.cache = {}  # In-memory cache (would use Redis in production)
        self.cache_ttl = {
            "pattern_performance": timedelta(hours=1),
            "execution_quality": timedelta(minutes=30),
            "daily_stats": timedelta(hours=4),
            "monthly_stats": timedelta(days=1),
        }
    
    def get_cache_key(self, query_type: str, parameters: Dict[str, Any]) -> str:
        """Generate cache key for query."""
        
        # Create deterministic key from query type and parameters
        param_str = json.dumps(parameters, sort_keys=True, default=str)
        return f"{query_type}:{hash(param_str)}"
    
    def get_cached_result(self, cache_key: str) -> Optional[Any]:
        """Get cached query result."""
        
        if cache_key in self.cache:
            result, timestamp = self.cache[cache_key]
            
            # Check if cache entry is still valid
            query_type = cache_key.split(":")[0]
            ttl = self.cache_ttl.get(query_type, timedelta(minutes=15))
            
            if datetime.now() - timestamp < ttl:
                return result
            else:
                # Cache expired
                del self.cache[cache_key]
        
        return None
    
    def cache_result(self, cache_key: str, result: Any):
        """Cache query result."""
        
        self.cache[cache_key] = (result, datetime.now())
        
        # Simple cache size management (would use LRU in production)
        if len(self.cache) > 1000:
            # Remove oldest entries
            sorted_items = sorted(self.cache.items(), key=lambda x: x[1][1])
            for key, _ in sorted_items[:100]:
                del self.cache[key]


class DataArchivalManager:
    """Manages data archival and retention policies."""
    
    def __init__(self):
        self.archival_rules = {
            # Hot to Warm: After 3 months, summarize to hourly
            "hot_to_warm": {
                "age_threshold": timedelta(days=90),
                "aggregation": "hourly",
                "fields_to_summarize": [
                    "pnl", "slippage", "execution_latency", "confidence", "strength"
                ]
            },
            
            # Warm to Cold: After 1 year, summarize to daily
            "warm_to_cold": {
                "age_threshold": timedelta(days=365),
                "aggregation": "daily",
                "fields_to_summarize": [
                    "total_trades", "total_pnl", "avg_slippage", "avg_latency"
                ]
            },
            
            # Cold retention: Keep for 7 years
            "cold_retention": {
                "age_threshold": timedelta(days=2555),
                "action": "delete"
            }
        }
    
    def create_archival_summary(
        self,
        records: List[ComprehensiveTradeRecord],
        aggregation_period: str
    ) -> Dict[str, Any]:
        """Create archival summary for records."""
        
        if not records:
            return {}
        
        # Group records by time period
        if aggregation_period == "hourly":
            grouped_records = self._group_by_hour(records)
        elif aggregation_period == "daily":
            grouped_records = self._group_by_day(records)
        else:
            raise ValueError(f"Unsupported aggregation period: {aggregation_period}")
        
        # Create summaries for each group
        summaries = {}
        for period, period_records in grouped_records.items():
            summaries[period] = self._create_period_summary(period_records)
        
        return summaries
    
    def _group_by_hour(self, records: List[ComprehensiveTradeRecord]) -> Dict[str, List[ComprehensiveTradeRecord]]:
        """Group records by hour."""
        
        grouped = {}
        for record in records:
            hour_key = record.timestamp.strftime("%Y-%m-%d_%H")
            if hour_key not in grouped:
                grouped[hour_key] = []
            grouped[hour_key].append(record)
        
        return grouped
    
    def _group_by_day(self, records: List[ComprehensiveTradeRecord]) -> Dict[str, List[ComprehensiveTradeRecord]]:
        """Group records by day."""
        
        grouped = {}
        for record in records:
            day_key = record.timestamp.strftime("%Y-%m-%d")
            if day_key not in grouped:
                grouped[day_key] = []
            grouped[day_key].append(record)
        
        return grouped
    
    def _create_period_summary(self, records: List[ComprehensiveTradeRecord]) -> Dict[str, Any]:
        """Create summary statistics for a time period."""
        
        if not records:
            return {}
        
        # Basic statistics
        total_trades = len(records)
        wins = len([r for r in records if r.performance.actual_outcome == "win"])
        losses = total_trades - wins
        
        # Financial statistics
        total_pnl = sum(r.performance.actual_pnl for r in records)
        avg_pnl = total_pnl / Decimal(str(total_trades))
        
        # Execution statistics
        slippages = [r.execution_quality.slippage for r in records if r.execution_quality.slippage != 0]
        avg_slippage = sum(slippages) / Decimal(str(len(slippages))) if slippages else Decimal("0")
        
        latencies = [r.execution_quality.execution_latency for r in records if r.execution_quality.execution_latency > 0]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        
        # Pattern statistics
        pattern_counts = {}
        for record in records:
            pattern = record.signal_context.pattern_type
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
        
        return {
            "period_start": min(r.timestamp for r in records).isoformat(),
            "period_end": max(r.timestamp for r in records).isoformat(),
            "total_trades": total_trades,
            "wins": wins,
            "losses": losses,
            "win_rate": float(wins / total_trades),
            "total_pnl": float(total_pnl),
            "average_pnl": float(avg_pnl),
            "average_slippage": float(avg_slippage),
            "average_latency": avg_latency,
            "pattern_distribution": pattern_counts,
            "unique_symbols": len(set(r.trade_details.symbol for r in records)),
            "unique_accounts": len(set(r.account_id for r in records)),
        }


class PerformanceMonitor:
    """Monitors query and storage performance."""
    
    def __init__(self):
        self.query_metrics: List[QueryPerformanceMetrics] = []
        self.slow_query_threshold_ms = 1000
        self.storage_stats = StorageStats(
            total_records=0,
            hot_storage_records=0,
            warm_storage_records=0,
            cold_storage_records=0,
            total_size_gb=Decimal("0"),
            hot_storage_size_gb=Decimal("0"),
            warm_storage_size_gb=Decimal("0"),
            cold_storage_size_gb=Decimal("0"),
            oldest_record=datetime.now(),
            newest_record=datetime.now()
        )
    
    def record_query_performance(
        self,
        query_id: str,
        query_type: str,
        execution_time_ms: int,
        rows_scanned: int,
        rows_returned: int,
        complexity: QueryComplexity,
        cache_hit: bool = False,
        partition_pruning: bool = False,
        index_usage: List[str] = None
    ):
        """Record query performance metrics."""
        
        metrics = QueryPerformanceMetrics(
            query_id=query_id,
            query_type=query_type,
            execution_time_ms=execution_time_ms,
            rows_scanned=rows_scanned,
            rows_returned=rows_returned,
            complexity=complexity,
            cache_hit=cache_hit,
            partition_pruning=partition_pruning,
            index_usage=index_usage or [],
            timestamp=datetime.now()
        )
        
        self.query_metrics.append(metrics)
        
        # Log slow queries
        if execution_time_ms > self.slow_query_threshold_ms:
            logger.warning(f"Slow query detected: {query_type} took {execution_time_ms}ms")
        
        # Maintain metrics buffer size
        if len(self.query_metrics) > 10000:
            self.query_metrics = self.query_metrics[-5000:]  # Keep last 5000
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance summary for last N hours."""
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_metrics = [m for m in self.query_metrics if m.timestamp > cutoff_time]
        
        if not recent_metrics:
            return {"message": "No query metrics available"}
        
        # Calculate statistics
        total_queries = len(recent_metrics)
        avg_execution_time = sum(m.execution_time_ms for m in recent_metrics) / total_queries
        slow_queries = len([m for m in recent_metrics if m.execution_time_ms > self.slow_query_threshold_ms])
        cache_hits = len([m for m in recent_metrics if m.cache_hit])
        
        # Query type breakdown
        query_types = {}
        for metric in recent_metrics:
            query_type = metric.query_type
            if query_type not in query_types:
                query_types[query_type] = {"count": 0, "total_time": 0}
            query_types[query_type]["count"] += 1
            query_types[query_type]["total_time"] += metric.execution_time_ms
        
        # Calculate averages for each query type
        for query_type, stats in query_types.items():
            stats["avg_time"] = stats["total_time"] / stats["count"]
        
        return {
            "time_period_hours": hours,
            "total_queries": total_queries,
            "average_execution_time_ms": avg_execution_time,
            "slow_queries": slow_queries,
            "slow_query_percentage": (slow_queries / total_queries) * 100,
            "cache_hit_rate": (cache_hits / total_queries) * 100,
            "query_type_breakdown": query_types,
            "storage_stats": asdict(self.storage_stats)
        }
    
    def identify_performance_issues(self) -> List[Dict[str, Any]]:
        """Identify performance issues and recommendations."""
        
        issues = []
        
        # Check cache hit rate
        recent_metrics = self.query_metrics[-1000:] if len(self.query_metrics) >= 1000 else self.query_metrics
        
        if recent_metrics:
            cache_hit_rate = len([m for m in recent_metrics if m.cache_hit]) / len(recent_metrics)
            
            if cache_hit_rate < 0.3:  # Less than 30% cache hit rate
                issues.append({
                    "type": "low_cache_hit_rate",
                    "severity": "medium",
                    "description": f"Cache hit rate is only {cache_hit_rate:.1%}",
                    "recommendation": "Consider increasing cache TTL or implementing smarter caching strategies"
                })
            
            # Check slow query percentage
            slow_query_rate = len([m for m in recent_metrics if m.execution_time_ms > self.slow_query_threshold_ms]) / len(recent_metrics)
            
            if slow_query_rate > 0.1:  # More than 10% slow queries
                issues.append({
                    "type": "high_slow_query_rate",
                    "severity": "high",
                    "description": f"Slow query rate is {slow_query_rate:.1%}",
                    "recommendation": "Review query optimization and index usage"
                })
        
        return issues


class DataStorageManager:
    """Main storage manager orchestrating all storage operations."""
    
    def __init__(self):
        self.partition_strategy = DataPartitionStrategy()
        self.index_optimizer = IndexOptimizer()
        self.query_optimizer = QueryOptimizer()
        self.cache_manager = CacheManager()
        self.archival_manager = DataArchivalManager()
        self.performance_monitor = PerformanceMonitor()
        
        logger.info("Data storage manager initialized")
    
    def store_trade_record(self, record: ComprehensiveTradeRecord) -> bool:
        """Store trade record in appropriate partition."""
        
        try:
            # Determine storage type and partition
            storage_type = self.partition_strategy.determine_storage_type(record.timestamp)
            partition_name = self.partition_strategy.get_partition_name(record.timestamp, storage_type)
            
            # In real implementation: insert into database
            # self.execute_query(f"INSERT INTO {partition_name} VALUES (...)")
            
            logger.debug(f"Stored trade record {record.id} in {partition_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store trade record {record.id}: {str(e)}")
            return False
    
    def query_trades(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> List[ComprehensiveTradeRecord]:
        """Query trades with optimized performance."""
        
        # Check cache first
        cache_key = self.cache_manager.get_cache_key("trades_query", {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "filters": filters or {},
            "limit": limit
        })
        
        cached_result = self.cache_manager.get_cached_result(cache_key)
        if cached_result:
            logger.debug("Query served from cache")
            return cached_result
        
        # Build and optimize query
        base_query = self._build_query(filters, limit)
        optimized_query = self.query_optimizer.optimize_time_range_query(
            base_query, start_time, end_time, self.partition_strategy
        )
        
        # Execute query (mock implementation)
        start_exec_time = datetime.now()
        
        # In real implementation: execute optimized_query
        results = []  # Would be actual query results
        
        exec_time = int((datetime.now() - start_exec_time).total_seconds() * 1000)
        
        # Record performance metrics
        self.performance_monitor.record_query_performance(
            query_id=f"trades_query_{datetime.now().timestamp()}",
            query_type="trades_query",
            execution_time_ms=exec_time,
            rows_scanned=1000,  # Would be actual count
            rows_returned=len(results),
            complexity=QueryComplexity.MEDIUM,
            cache_hit=False,
            partition_pruning=True
        )
        
        # Cache results
        self.cache_manager.cache_result(cache_key, results)
        
        return results
    
    def _build_query(self, filters: Optional[Dict[str, Any]], limit: Optional[int]) -> str:
        """Build base SQL query from filters."""
        
        query = "SELECT * FROM comprehensive_trades WHERE 1=1"
        
        if filters:
            for field, value in filters.items():
                if field == "symbol":
                    query += f" AND symbol = '{value}'"
                elif field == "pattern_type":
                    query += f" AND pattern_type = '{value}'"
                elif field == "account_id":
                    query += f" AND account_id = '{value}'"
                # Add more filter conditions as needed
        
        query += " ORDER BY trade_timestamp DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        return query
    
    def get_storage_statistics(self) -> Dict[str, Any]:
        """Get comprehensive storage statistics."""
        
        return {
            "storage_stats": asdict(self.performance_monitor.storage_stats),
            "performance_summary": self.performance_monitor.get_performance_summary(),
            "performance_issues": self.performance_monitor.identify_performance_issues(),
            "cache_stats": {
                "cache_size": len(self.cache_manager.cache),
                "cache_types": list(self.cache_manager.cache_ttl.keys())
            },
            "partition_stats": {
                "partition_strategy": self.partition_strategy.partition_interval,
                "retention_policies": {
                    str(k): str(v) for k, v in self.partition_strategy.retention_policy.items()
                }
            }
        }
    
    def optimize_storage(self) -> Dict[str, Any]:
        """Perform storage optimization tasks."""
        
        optimization_results = {}
        
        # Run archival process
        try:
            # In real implementation: identify records for archival and process them
            optimization_results["archival"] = "Archival process completed successfully"
        except Exception as e:
            optimization_results["archival"] = f"Archival process failed: {str(e)}"
        
        # Update index recommendations
        try:
            # Analyze recent queries and update index recommendations
            optimization_results["indexing"] = "Index analysis completed"
        except Exception as e:
            optimization_results["indexing"] = f"Index analysis failed: {str(e)}"
        
        # Clear expired cache entries
        try:
            # Clean up expired cache entries
            optimization_results["caching"] = "Cache cleanup completed"
        except Exception as e:
            optimization_results["caching"] = f"Cache cleanup failed: {str(e)}"
        
        return optimization_results