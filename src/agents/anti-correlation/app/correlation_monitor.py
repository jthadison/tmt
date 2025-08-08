"""Real-time correlation monitoring system."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from uuid import UUID
import numpy as np
from scipy.stats import pearsonr
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc

from .models import (
    CorrelationMetric, CorrelationAlert, PositionData,
    CorrelationSeverity, CorrelationMatrixResponse
)

logger = logging.getLogger(__name__)


class CorrelationMonitor:
    """Monitors correlation between trading accounts in real-time."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.correlation_matrix = {}
        self.time_windows = [300, 3600, 86400]  # 5min, 1hr, 1day
        self.thresholds = {
            CorrelationSeverity.INFO: 0.5,
            CorrelationSeverity.WARNING: 0.7,
            CorrelationSeverity.CRITICAL: 0.9
        }
        self.position_cache = {}
        self.last_update = datetime.utcnow()
    
    async def calculate_correlation(
        self,
        account1_id: UUID,
        account2_id: UUID,
        time_window: int = 3600,
        include_components: bool = True
    ) -> Tuple[float, float, Optional[Dict[str, float]]]:
        """Calculate correlation between two accounts."""
        try:
            # Get position data for both accounts
            positions1 = await self._get_position_vector(account1_id, time_window)
            positions2 = await self._get_position_vector(account2_id, time_window)
            
            if len(positions1) < 2 or len(positions2) < 2:
                logger.warning(f"Insufficient data for correlation between {account1_id} and {account2_id}")
                return 0.0, 1.0, None
            
            # Calculate main correlation coefficient
            correlation, p_value = pearsonr(positions1, positions2)
            
            # Calculate component correlations if requested
            components = None
            if include_components:
                components = await self._calculate_component_correlations(
                    account1_id, account2_id, time_window
                )
            
            return float(correlation), float(p_value), components
            
        except Exception as e:
            logger.error(f"Error calculating correlation: {e}")
            return 0.0, 1.0, None
    
    async def update_correlation_matrix(
        self,
        account_ids: List[UUID],
        time_window: int = 3600
    ) -> CorrelationMatrixResponse:
        """Update correlation matrix for all account pairs."""
        n_accounts = len(account_ids)
        correlation_matrix = np.zeros((n_accounts, n_accounts))
        
        # Calculate pairwise correlations
        for i, account1_id in enumerate(account_ids):
            for j, account2_id in enumerate(account_ids):
                if i == j:
                    correlation_matrix[i][j] = 1.0
                elif i < j:  # Calculate only upper triangle
                    corr, p_val, components = await self.calculate_correlation(
                        account1_id, account2_id, time_window, include_components=True
                    )
                    correlation_matrix[i][j] = corr
                    correlation_matrix[j][i] = corr  # Symmetric
                    
                    # Store in database
                    await self._store_correlation_metric(
                        account1_id, account2_id, corr, p_val, 
                        time_window, components
                    )
                    
                    # Check for threshold violations
                    await self._check_correlation_threshold(
                        account1_id, account2_id, corr
                    )
        
        # Calculate summary statistics
        upper_triangle = correlation_matrix[np.triu_indices(n_accounts, k=1)]
        summary_stats = {
            "mean_correlation": float(np.mean(upper_triangle)),
            "max_correlation": float(np.max(upper_triangle)),
            "min_correlation": float(np.min(upper_triangle)),
            "std_correlation": float(np.std(upper_triangle)),
            "high_correlation_pairs": int(np.sum(upper_triangle > self.thresholds[CorrelationSeverity.WARNING]))
        }
        
        return CorrelationMatrixResponse(
            accounts=account_ids,
            correlation_matrix=correlation_matrix.tolist(),
            calculation_time=datetime.utcnow(),
            time_window=time_window,
            summary_stats=summary_stats
        )
    
    async def monitor_real_time(self, account_ids: List[UUID]):
        """Continuous real-time monitoring of correlations."""
        while True:
            try:
                # Update correlations every 60 seconds
                logger.info(f"Updating correlations for {len(account_ids)} accounts")
                
                # Update for all time windows
                for time_window in self.time_windows:
                    matrix_result = await self.update_correlation_matrix(
                        account_ids, time_window
                    )
                    
                    # Update cache
                    self.correlation_matrix[time_window] = matrix_result
                
                self.last_update = datetime.utcnow()
                
                # Publish WebSocket updates
                await self._publish_correlation_updates(account_ids)
                
                # Wait before next update
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in real-time monitoring: {e}")
                await asyncio.sleep(10)  # Shorter retry interval on error
    
    async def get_correlation_history(
        self,
        account1_id: UUID,
        account2_id: UUID,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get historical correlation data."""
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        metrics = self.db.query(CorrelationMetric).filter(
            and_(
                or_(
                    and_(
                        CorrelationMetric.account_1_id == account1_id,
                        CorrelationMetric.account_2_id == account2_id
                    ),
                    and_(
                        CorrelationMetric.account_1_id == account2_id,
                        CorrelationMetric.account_2_id == account1_id
                    )
                ),
                CorrelationMetric.calculation_time >= start_time
            )
        ).order_by(CorrelationMetric.calculation_time.asc()).all()
        
        return [
            {
                "time": metric.calculation_time.isoformat(),
                "correlation": float(metric.correlation_coefficient),
                "p_value": float(metric.p_value) if metric.p_value else None,
                "time_window": metric.time_window
            }
            for metric in metrics
        ]
    
    async def get_high_correlation_pairs(
        self,
        threshold: float = 0.7,
        time_window: int = 3600
    ) -> List[Dict[str, Any]]:
        """Get account pairs with correlation above threshold."""
        recent_time = datetime.utcnow() - timedelta(seconds=time_window * 2)
        
        high_correlations = self.db.query(CorrelationMetric).filter(
            and_(
                CorrelationMetric.correlation_coefficient >= threshold,
                CorrelationMetric.time_window == time_window,
                CorrelationMetric.calculation_time >= recent_time
            )
        ).order_by(desc(CorrelationMetric.correlation_coefficient)).all()
        
        return [
            {
                "account_1_id": str(metric.account_1_id),
                "account_2_id": str(metric.account_2_id),
                "correlation": float(metric.correlation_coefficient),
                "calculation_time": metric.calculation_time.isoformat(),
                "components": {
                    "position": float(metric.position_correlation) if metric.position_correlation else None,
                    "timing": float(metric.timing_correlation) if metric.timing_correlation else None,
                    "size": float(metric.size_correlation) if metric.size_correlation else None,
                    "pnl": float(metric.pnl_correlation) if metric.pnl_correlation else None
                }
            }
            for metric in high_correlations
        ]
    
    async def _get_position_vector(
        self,
        account_id: UUID,
        time_window: int
    ) -> List[float]:
        """Get position vector for correlation calculation."""
        # This would integrate with the trading system to get actual positions
        # For now, using simulated position data
        
        # In production, this would query the trading database
        # positions = get_account_positions(account_id, time_window)
        
        # Simulated position data for major currency pairs
        instruments = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCHF", "USDCAD", "NZDUSD"]
        
        # Generate realistic position vector (this would come from actual data)
        positions = []
        for instrument in instruments:
            # This would be actual position size from database
            position_size = np.random.normal(0, 0.5)  # Simulated
            positions.append(position_size)
        
        return positions
    
    async def _calculate_component_correlations(
        self,
        account1_id: UUID,
        account2_id: UUID,
        time_window: int
    ) -> Dict[str, float]:
        """Calculate component-wise correlations."""
        components = {}
        
        try:
            # Position correlation (instruments and directions)
            pos1 = await self._get_position_vector(account1_id, time_window)
            pos2 = await self._get_position_vector(account2_id, time_window)
            components["position"] = float(pearsonr(pos1, pos2)[0])
            
            # Timing correlation (entry/exit timing patterns)
            timing1 = await self._get_timing_vector(account1_id, time_window)
            timing2 = await self._get_timing_vector(account2_id, time_window)
            if len(timing1) >= 2 and len(timing2) >= 2:
                components["timing"] = float(pearsonr(timing1, timing2)[0])
            
            # Size correlation (position size patterns)
            sizes1 = await self._get_size_vector(account1_id, time_window)
            sizes2 = await self._get_size_vector(account2_id, time_window)
            if len(sizes1) >= 2 and len(sizes2) >= 2:
                components["size"] = float(pearsonr(sizes1, sizes2)[0])
            
            # P&L correlation (profit/loss patterns)
            pnl1 = await self._get_pnl_vector(account1_id, time_window)
            pnl2 = await self._get_pnl_vector(account2_id, time_window)
            if len(pnl1) >= 2 and len(pnl2) >= 2:
                components["pnl"] = float(pearsonr(pnl1, pnl2)[0])
                
        except Exception as e:
            logger.warning(f"Error calculating component correlations: {e}")
        
        return components
    
    async def _get_timing_vector(self, account_id: UUID, time_window: int) -> List[float]:
        """Get timing pattern vector for account."""
        # Simulated timing data - in production, get from trade execution logs
        return np.random.normal(0, 1, 10).tolist()
    
    async def _get_size_vector(self, account_id: UUID, time_window: int) -> List[float]:
        """Get position size pattern vector for account."""
        # Simulated size data - in production, get from position history
        return np.random.normal(1.0, 0.3, 10).tolist()
    
    async def _get_pnl_vector(self, account_id: UUID, time_window: int) -> List[float]:
        """Get P&L pattern vector for account."""
        # Simulated P&L data - in production, get from account performance
        return np.random.normal(0, 100, 10).tolist()
    
    async def _store_correlation_metric(
        self,
        account1_id: UUID,
        account2_id: UUID,
        correlation: float,
        p_value: float,
        time_window: int,
        components: Optional[Dict[str, float]]
    ):
        """Store correlation metric in database."""
        metric = CorrelationMetric(
            account_1_id=account1_id,
            account_2_id=account2_id,
            correlation_coefficient=correlation,
            p_value=p_value,
            time_window=time_window,
            position_correlation=components.get("position") if components else None,
            timing_correlation=components.get("timing") if components else None,
            size_correlation=components.get("size") if components else None,
            pnl_correlation=components.get("pnl") if components else None
        )
        
        self.db.add(metric)
        self.db.commit()
    
    async def _check_correlation_threshold(
        self,
        account1_id: UUID,
        account2_id: UUID,
        correlation: float
    ):
        """Check if correlation exceeds thresholds and trigger alerts."""
        severity = None
        
        if correlation >= self.thresholds[CorrelationSeverity.CRITICAL]:
            severity = CorrelationSeverity.CRITICAL
        elif correlation >= self.thresholds[CorrelationSeverity.WARNING]:
            severity = CorrelationSeverity.WARNING
        elif correlation >= self.thresholds[CorrelationSeverity.INFO]:
            severity = CorrelationSeverity.INFO
        
        if severity:
            # Check if this is a new alert (not duplicate)
            recent_alert = self.db.query(CorrelationAlert).filter(
                and_(
                    or_(
                        and_(
                            CorrelationAlert.account_1_id == account1_id,
                            CorrelationAlert.account_2_id == account2_id
                        ),
                        and_(
                            CorrelationAlert.account_1_id == account2_id,
                            CorrelationAlert.account_2_id == account1_id
                        )
                    ),
                    CorrelationAlert.resolved_time.is_(None),
                    CorrelationAlert.alert_time >= datetime.utcnow() - timedelta(hours=1)
                )
            ).first()
            
            if not recent_alert:
                alert = CorrelationAlert(
                    account_1_id=account1_id,
                    account_2_id=account2_id,
                    correlation_coefficient=correlation,
                    severity=severity.value
                )
                
                self.db.add(alert)
                self.db.commit()
                
                logger.warning(
                    f"Correlation alert: {account1_id} <-> {account2_id} "
                    f"correlation={correlation:.3f} severity={severity.value}"
                )
    
    async def _publish_correlation_updates(self, account_ids: List[UUID]):
        """Publish correlation updates via WebSocket."""
        # This would integrate with WebSocket system
        # For now, just log the update
        logger.info(f"Publishing correlation updates for {len(account_ids)} accounts")


from sqlalchemy import or_  # Add missing import