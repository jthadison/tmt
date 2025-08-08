"""Account performance comparison and ranking system."""

import logging
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple, Any
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc, case

from .models import (
    TradePerformance, PerformanceMetrics, PerformanceSnapshot,
    AccountRanking, PeriodType, AccountComparison
)
from .metrics_calculator import PerformanceMetricsCalculator

logger = logging.getLogger(__name__)


class PerformanceRankingAlgorithm:
    """Advanced performance ranking algorithm with multiple factors."""
    
    def __init__(self):
        # Weighting factors for different performance metrics
        self.weights = {
            'return': 0.25,          # Total return weight
            'risk_adjusted_return': 0.30,  # Sharpe/Sortino ratio weight
            'consistency': 0.20,     # Drawdown and volatility weight
            'efficiency': 0.15,      # Profit factor weight
            'activity': 0.10         # Trading frequency weight
        }
        
        # Risk parameters
        self.max_acceptable_drawdown = Decimal('0.20')  # 20%
        self.min_sharpe_ratio = Decimal('-1.0')
    
    def calculate_ranking_score(
        self, 
        total_return: Decimal,
        sharpe_ratio: Optional[Decimal],
        sortino_ratio: Optional[Decimal],
        max_drawdown: Decimal,
        profit_factor: Decimal,
        win_rate: Decimal,
        total_trades: int,
        volatility: Optional[Decimal] = None
    ) -> Decimal:
        """Calculate composite ranking score (0-100)."""
        try:
            # Return component (0-25 points)
            return_score = self._score_return(total_return) * self.weights['return']
            
            # Risk-adjusted return component (0-30 points)
            risk_adj_score = self._score_risk_adjusted_return(
                sharpe_ratio, sortino_ratio
            ) * self.weights['risk_adjusted_return']
            
            # Consistency component (0-20 points)
            consistency_score = self._score_consistency(
                max_drawdown, volatility
            ) * self.weights['consistency']
            
            # Efficiency component (0-15 points)
            efficiency_score = self._score_efficiency(
                profit_factor, win_rate
            ) * self.weights['efficiency']
            
            # Activity component (0-10 points)
            activity_score = self._score_activity(total_trades) * self.weights['activity']
            
            # Calculate total score
            total_score = (
                return_score + risk_adj_score + consistency_score + 
                efficiency_score + activity_score
            )
            
            return total_score.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
        except Exception as e:
            logger.error(f"Error calculating ranking score: {e}")
            return Decimal('0')
    
    def _score_return(self, total_return: Decimal) -> Decimal:
        """Score total return component (0-100)."""
        if total_return <= 0:
            return Decimal('0')
        
        # Linear scoring for simplicity and avoid decimal/float mixing
        # Score approaches 100 as return approaches 100%
        score = min(Decimal('100'), max(Decimal('0'), total_return * Decimal('100')))
        return score
    
    def _score_risk_adjusted_return(
        self, 
        sharpe_ratio: Optional[Decimal],
        sortino_ratio: Optional[Decimal]
    ) -> Decimal:
        """Score risk-adjusted return (0-100)."""
        if not sharpe_ratio and not sortino_ratio:
            return Decimal('50')  # Neutral score
        
        # Use Sortino if available, otherwise Sharpe
        ratio = sortino_ratio if sortino_ratio else sharpe_ratio
        
        if ratio < self.min_sharpe_ratio:
            return Decimal('0')
        
        # Score based on ratio value
        # Sharpe > 2.0 = 100 points, Sharpe = 1.0 = 75 points, Sharpe = 0 = 50 points
        if ratio >= 2:
            score = 100
        elif ratio >= 1:
            score = 75 + 25 * (ratio - 1)
        elif ratio >= 0:
            score = 50 + 25 * ratio
        else:
            score = max(Decimal('0'), 50 + 50 * ratio)  # Negative ratios
        
        return Decimal(str(min(100, max(0, score))))
    
    def _score_consistency(
        self, 
        max_drawdown: Decimal,
        volatility: Optional[Decimal]
    ) -> Decimal:
        """Score consistency metrics (0-100)."""
        # Drawdown component (70% of consistency score)
        if max_drawdown >= self.max_acceptable_drawdown:
            drawdown_score = 0
        else:
            # Linear scoring - lower drawdown = higher score
            drawdown_score = 100 * (1 - max_drawdown / self.max_acceptable_drawdown)
        
        # Volatility component (30% of consistency score)
        volatility_score = 50  # Default neutral score
        if volatility:
            # Lower volatility = higher score (up to reasonable limit)
            if volatility <= Decimal('0.01'):  # Very low volatility
                volatility_score = 100
            elif volatility <= Decimal('0.05'):  # Moderate volatility
                volatility_score = 75
            elif volatility <= Decimal('0.10'):  # High volatility
                volatility_score = 50
            else:  # Very high volatility
                volatility_score = 25
        
        total_score = 0.7 * drawdown_score + 0.3 * volatility_score
        return Decimal(str(min(100, max(0, total_score))))
    
    def _score_efficiency(self, profit_factor: Decimal, win_rate: Decimal) -> Decimal:
        """Score trading efficiency (0-100)."""
        # Profit factor component (60%)
        if profit_factor <= 1:
            pf_score = 0
        elif profit_factor >= 3:
            pf_score = 100
        else:
            pf_score = 50 * (profit_factor - 1)
        
        # Win rate component (40%)
        if win_rate >= 70:
            wr_score = 100
        elif win_rate >= 50:
            wr_score = 50 + Decimal('2.5') * (win_rate - 50)
        else:
            wr_score = max(Decimal('0'), 2 * win_rate)
        
        total_score = 0.6 * pf_score + 0.4 * wr_score
        return Decimal(str(min(100, max(0, total_score))))
    
    def _score_activity(self, total_trades: int) -> Decimal:
        """Score trading activity level (0-100)."""
        if total_trades == 0:
            return Decimal('0')
        
        # Optimal range: 50-200 trades per period
        if 50 <= total_trades <= 200:
            return Decimal('100')
        elif total_trades < 50:
            # Penalty for low activity
            return Decimal(str(max(0, total_trades * 2)))
        else:
            # Mild penalty for over-trading
            return Decimal(str(max(50, 150 - total_trades * 0.25)))


class AccountComparisonSystem:
    """Comprehensive account comparison and ranking system."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.ranking_algorithm = PerformanceRankingAlgorithm()
        self.metrics_calculator = PerformanceMetricsCalculator(db_session)
    
    async def calculate_account_rankings(
        self, 
        account_ids: List[UUID],
        period_start: datetime,
        period_end: datetime,
        period_type: PeriodType = PeriodType.MONTHLY
    ) -> List[AccountComparison]:
        """Calculate and rank account performance."""
        try:
            rankings = []
            
            logger.info(f"Calculating rankings for {len(account_ids)} accounts")
            
            # Calculate metrics for each account
            account_scores = []
            for account_id in account_ids:
                try:
                    # Get performance metrics
                    metrics = await self.metrics_calculator.calculate_period_metrics(
                        account_id, period_start, period_end, period_type
                    )
                    
                    # Calculate additional metrics needed for ranking
                    volatility = await self._calculate_volatility(
                        account_id, period_start, period_end
                    )
                    
                    # Calculate ranking score
                    ranking_score = self.ranking_algorithm.calculate_ranking_score(
                        total_return=metrics.total_pnl,
                        sharpe_ratio=metrics.sharpe_ratio,
                        sortino_ratio=metrics.sortino_ratio,
                        max_drawdown=metrics.max_drawdown,
                        profit_factor=metrics.profit_factor,
                        win_rate=metrics.win_rate,
                        total_trades=metrics.total_trades,
                        volatility=volatility
                    )
                    
                    account_scores.append({
                        'account_id': account_id,
                        'ranking_score': ranking_score,
                        'metrics': metrics
                    })
                    
                except Exception as e:
                    logger.error(f"Error calculating metrics for account {account_id}: {e}")
                    # Add account with zero score to maintain ranking
                    account_scores.append({
                        'account_id': account_id,
                        'ranking_score': Decimal('0'),
                        'metrics': None
                    })
            
            # Sort by ranking score (highest first)
            account_scores.sort(key=lambda x: x['ranking_score'], reverse=True)
            
            # Assign ranks and create comparison objects
            total_accounts = len(account_scores)
            
            for rank, account_data in enumerate(account_scores, 1):
                account_id = account_data['account_id']
                ranking_score = account_data['ranking_score']
                metrics = account_data['metrics']
                
                # Calculate percentile
                percentile = ((total_accounts - rank) / total_accounts) * 100
                
                comparison = AccountComparison(
                    account_id=account_id,
                    account_name=f"Account {str(account_id)[:8]}",  # Simplified
                    performance_rank=rank,
                    total_accounts=total_accounts,
                    percentile=Decimal(str(percentile)).quantize(Decimal('0.01')),
                    ranking_score=ranking_score,
                    total_pnl=metrics.total_pnl if metrics else Decimal('0'),
                    win_rate=metrics.win_rate if metrics else Decimal('0'),
                    profit_factor=metrics.profit_factor if metrics else Decimal('0'),
                    sharpe_ratio=metrics.sharpe_ratio if metrics else None,
                    max_drawdown=metrics.max_drawdown if metrics else Decimal('0')
                )
                
                rankings.append(comparison)
                
                # Store ranking in database
                await self._store_ranking(
                    account_id, period_type, period_start, 
                    ranking_score, rank, total_accounts, percentile
                )
            
            logger.info(f"Completed ranking calculation. Top performer: {rankings[0].account_id}")
            return rankings
            
        except Exception as e:
            logger.error(f"Error calculating account rankings: {e}")
            return []
    
    async def get_best_worst_performers(
        self, 
        account_ids: List[UUID],
        period_start: datetime,
        period_end: datetime,
        period_type: PeriodType = PeriodType.MONTHLY
    ) -> Dict[str, AccountComparison]:
        """Identify best and worst performing accounts."""
        try:
            rankings = await self.calculate_account_rankings(
                account_ids, period_start, period_end, period_type
            )
            
            if not rankings:
                return {}
            
            return {
                'best_performer': rankings[0],
                'worst_performer': rankings[-1],
                'median_performer': rankings[len(rankings)//2] if len(rankings) > 2 else None
            }
            
        except Exception as e:
            logger.error(f"Error identifying best/worst performers: {e}")
            return {}
    
    async def generate_performance_heatmap_data(
        self, 
        account_ids: List[UUID],
        period_start: datetime,
        period_end: datetime,
        metric_type: str = 'total_pnl'
    ) -> Dict[str, Any]:
        """Generate data for performance heatmap visualization."""
        try:
            heatmap_data = {
                'accounts': [str(aid) for aid in account_ids],
                'metric_type': metric_type,
                'period_start': period_start.isoformat(),
                'period_end': period_end.isoformat(),
                'data': [],
                'statistics': {}
            }
            
            # Collect metric values
            values = []
            account_metrics = {}
            
            for account_id in account_ids:
                metrics = await self.metrics_calculator.calculate_period_metrics(
                    account_id, period_start, period_end, PeriodType.DAILY
                )
                
                # Extract the requested metric
                if metric_type == 'total_pnl':
                    value = float(metrics.total_pnl)
                elif metric_type == 'win_rate':
                    value = float(metrics.win_rate)
                elif metric_type == 'profit_factor':
                    value = float(metrics.profit_factor)
                elif metric_type == 'sharpe_ratio':
                    value = float(metrics.sharpe_ratio) if metrics.sharpe_ratio else 0
                elif metric_type == 'max_drawdown':
                    value = float(metrics.max_drawdown)
                else:
                    value = 0
                
                values.append(value)
                account_metrics[str(account_id)] = value
            
            # Calculate statistics
            if values:
                heatmap_data['statistics'] = {
                    'min': min(values),
                    'max': max(values),
                    'mean': sum(values) / len(values),
                    'median': sorted(values)[len(values)//2],
                    'std': float(np.std(values))
                }
            
            # Create normalized data for visualization
            if values and max(values) != min(values):
                value_range = max(values) - min(values)
                for account_id in account_ids:
                    raw_value = account_metrics[str(account_id)]
                    normalized = (raw_value - min(values)) / value_range
                    
                    heatmap_data['data'].append({
                        'account_id': str(account_id),
                        'raw_value': raw_value,
                        'normalized_value': normalized,
                        'color_intensity': min(100, max(0, normalized * 100))
                    })
            
            return heatmap_data
            
        except Exception as e:
            logger.error(f"Error generating heatmap data: {e}")
            return {}
    
    async def calculate_relative_performance(
        self, 
        account_id: UUID,
        benchmark_account_ids: List[UUID],
        period_start: datetime,
        period_end: datetime
    ) -> Dict[str, Any]:
        """Calculate relative performance vs benchmark accounts."""
        try:
            # Get target account performance
            target_metrics = await self.metrics_calculator.calculate_period_metrics(
                account_id, period_start, period_end, PeriodType.DAILY
            )
            
            # Calculate benchmark statistics
            benchmark_returns = []
            benchmark_metrics_list = []
            
            for bench_id in benchmark_account_ids:
                if bench_id != account_id:  # Exclude self
                    bench_metrics = await self.metrics_calculator.calculate_period_metrics(
                        bench_id, period_start, period_end, PeriodType.DAILY
                    )
                    benchmark_returns.append(float(bench_metrics.total_pnl))
                    benchmark_metrics_list.append(bench_metrics)
            
            if not benchmark_returns:
                return {'error': 'No benchmark data available'}
            
            # Calculate benchmark statistics
            benchmark_mean = sum(benchmark_returns) / len(benchmark_returns)
            benchmark_std = float(np.std(benchmark_returns))
            
            # Calculate relative metrics
            target_return = float(target_metrics.total_pnl)
            
            relative_performance = {
                'account_id': str(account_id),
                'period_start': period_start.isoformat(),
                'period_end': period_end.isoformat(),
                'target_performance': {
                    'total_pnl': target_return,
                    'win_rate': float(target_metrics.win_rate),
                    'sharpe_ratio': float(target_metrics.sharpe_ratio) if target_metrics.sharpe_ratio else None
                },
                'benchmark_statistics': {
                    'mean_return': benchmark_mean,
                    'std_return': benchmark_std,
                    'median_return': sorted(benchmark_returns)[len(benchmark_returns)//2],
                    'min_return': min(benchmark_returns),
                    'max_return': max(benchmark_returns),
                    'account_count': len(benchmark_returns)
                },
                'relative_metrics': {
                    'excess_return': target_return - benchmark_mean,
                    'relative_return_pct': ((target_return - benchmark_mean) / abs(benchmark_mean)) * 100 if benchmark_mean != 0 else 0,
                    'percentile_rank': self._calculate_percentile_rank(target_return, benchmark_returns),
                    'z_score': (target_return - benchmark_mean) / benchmark_std if benchmark_std > 0 else 0,
                    'outperformance': target_return > benchmark_mean
                }
            }
            
            return relative_performance
            
        except Exception as e:
            logger.error(f"Error calculating relative performance: {e}")
            return {}
    
    async def detect_performance_anomalies(
        self, 
        account_ids: List[UUID],
        period_start: datetime,
        period_end: datetime,
        z_score_threshold: float = 2.0
    ) -> Dict[str, Any]:
        """Detect accounts with anomalous performance."""
        try:
            anomalies = {
                'period_start': period_start.isoformat(),
                'period_end': period_end.isoformat(),
                'z_score_threshold': z_score_threshold,
                'anomalous_accounts': [],
                'statistics': {}
            }
            
            # Calculate performance metrics for all accounts
            all_returns = []
            account_data = {}
            
            for account_id in account_ids:
                metrics = await self.metrics_calculator.calculate_period_metrics(
                    account_id, period_start, period_end, PeriodType.DAILY
                )
                
                return_val = float(metrics.total_pnl)
                all_returns.append(return_val)
                account_data[str(account_id)] = {
                    'total_pnl': return_val,
                    'win_rate': float(metrics.win_rate),
                    'total_trades': metrics.total_trades,
                    'metrics': metrics
                }
            
            if len(all_returns) < 3:  # Need minimum data for anomaly detection
                return anomalies
            
            # Calculate population statistics
            mean_return = np.mean(all_returns)
            std_return = np.std(all_returns, ddof=1)
            
            anomalies['statistics'] = {
                'mean_return': float(mean_return),
                'std_return': float(std_return),
                'min_return': min(all_returns),
                'max_return': max(all_returns),
                'account_count': len(all_returns)
            }
            
            # Detect anomalies
            for account_id in account_ids:
                account_str = str(account_id)
                return_val = account_data[account_str]['total_pnl']
                
                # Calculate z-score
                z_score = (return_val - mean_return) / std_return if std_return > 0 else 0
                
                if abs(z_score) >= z_score_threshold:
                    anomaly_type = 'positive' if z_score > 0 else 'negative'
                    
                    anomalies['anomalous_accounts'].append({
                        'account_id': account_str,
                        'return': return_val,
                        'z_score': float(z_score),
                        'anomaly_type': anomaly_type,
                        'severity': 'extreme' if abs(z_score) >= 3.0 else 'moderate',
                        'metrics': {
                            'win_rate': account_data[account_str]['win_rate'],
                            'total_trades': account_data[account_str]['total_trades']
                        }
                    })
            
            logger.info(f"Detected {len(anomalies['anomalous_accounts'])} performance anomalies")
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting performance anomalies: {e}")
            return {}
    
    async def generate_performance_trends(
        self, 
        account_ids: List[UUID],
        start_date: datetime,
        end_date: datetime,
        period_type: PeriodType = PeriodType.DAILY
    ) -> Dict[str, Any]:
        """Generate performance trend analysis."""
        try:
            trends_data = {
                'period_type': period_type.value,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'account_trends': {},
                'comparative_analysis': {}
            }
            
            # Calculate trends for each account
            for account_id in account_ids:
                account_trend = await self._calculate_account_trend(
                    account_id, start_date, end_date, period_type
                )
                trends_data['account_trends'][str(account_id)] = account_trend
            
            # Calculate comparative trends
            trends_data['comparative_analysis'] = await self._calculate_comparative_trends(
                account_ids, start_date, end_date, period_type
            )
            
            return trends_data
            
        except Exception as e:
            logger.error(f"Error generating performance trends: {e}")
            return {}
    
    async def _calculate_volatility(
        self, 
        account_id: UUID, 
        start_date: datetime, 
        end_date: datetime
    ) -> Optional[Decimal]:
        """Calculate return volatility for the period."""
        try:
            # Get daily snapshots
            snapshots = self.db.query(PerformanceSnapshot).filter(
                and_(
                    PerformanceSnapshot.account_id == account_id,
                    PerformanceSnapshot.snapshot_time >= start_date,
                    PerformanceSnapshot.snapshot_time <= end_date
                )
            ).order_by(PerformanceSnapshot.snapshot_time).all()
            
            if len(snapshots) < 2:
                return None
            
            # Calculate daily returns
            returns = []
            for i in range(1, len(snapshots)):
                prev_equity = snapshots[i-1].equity
                curr_equity = snapshots[i].equity
                
                if prev_equity > 0:
                    daily_return = float((curr_equity - prev_equity) / prev_equity)
                    returns.append(daily_return)
            
            if not returns:
                return None
            
            # Calculate volatility (standard deviation)
            volatility = np.std(returns, ddof=1)
            return Decimal(str(volatility)).quantize(Decimal('0.0001'))
            
        except Exception as e:
            logger.error(f"Error calculating volatility: {e}")
            return None
    
    def _calculate_percentile_rank(self, value: float, benchmark_values: List[float]) -> float:
        """Calculate percentile rank of value in benchmark distribution."""
        try:
            sorted_values = sorted(benchmark_values)
            rank = sum(1 for v in sorted_values if v < value)
            percentile = (rank / len(sorted_values)) * 100
            return round(percentile, 2)
            
        except Exception as e:
            logger.error(f"Error calculating percentile rank: {e}")
            return 0.0
    
    async def _store_ranking(
        self, 
        account_id: UUID,
        period_type: PeriodType,
        period_start: datetime,
        ranking_score: Decimal,
        rank: int,
        total_accounts: int,
        percentile: float
    ):
        """Store ranking results in database."""
        try:
            # Check if ranking already exists
            existing = self.db.query(AccountRanking).filter(
                and_(
                    AccountRanking.account_id == account_id,
                    AccountRanking.period_type == period_type.value,
                    AccountRanking.period_start == period_start
                )
            ).first()
            
            if existing:
                # Update existing ranking
                existing.ranking_score = ranking_score
                existing.performance_rank = rank
                existing.total_accounts = total_accounts
                existing.percentile = Decimal(str(percentile))
            else:
                # Create new ranking
                ranking = AccountRanking(
                    account_id=account_id,
                    period_type=period_type.value,
                    period_start=period_start,
                    ranking_score=ranking_score,
                    performance_rank=rank,
                    total_accounts=total_accounts,
                    percentile=Decimal(str(percentile))
                )
                self.db.add(ranking)
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error storing ranking: {e}")
            self.db.rollback()
    
    async def _calculate_account_trend(
        self, 
        account_id: UUID, 
        start_date: datetime, 
        end_date: datetime,
        period_type: PeriodType
    ) -> Dict[str, Any]:
        """Calculate trend data for single account."""
        try:
            # Get historical rankings for trend analysis
            rankings = self.db.query(AccountRanking).filter(
                and_(
                    AccountRanking.account_id == account_id,
                    AccountRanking.period_type == period_type.value,
                    AccountRanking.period_start >= start_date,
                    AccountRanking.period_start <= end_date
                )
            ).order_by(AccountRanking.period_start).all()
            
            if len(rankings) < 2:
                return {'trend': 'insufficient_data'}
            
            # Calculate trend metrics
            rank_changes = []
            score_changes = []
            
            for i in range(1, len(rankings)):
                rank_change = rankings[i-1].performance_rank - rankings[i].performance_rank  # Positive = improvement
                score_change = float(rankings[i].ranking_score - rankings[i-1].ranking_score)
                
                rank_changes.append(rank_change)
                score_changes.append(score_change)
            
            return {
                'trend': 'improving' if sum(rank_changes) > 0 else 'declining' if sum(rank_changes) < 0 else 'stable',
                'avg_rank_change': sum(rank_changes) / len(rank_changes),
                'avg_score_change': sum(score_changes) / len(score_changes),
                'current_rank': rankings[-1].performance_rank,
                'best_rank': min(r.performance_rank for r in rankings),
                'worst_rank': max(r.performance_rank for r in rankings),
                'volatility': float(np.std([float(r.ranking_score) for r in rankings]))
            }
            
        except Exception as e:
            logger.error(f"Error calculating account trend: {e}")
            return {}
    
    async def _calculate_comparative_trends(
        self, 
        account_ids: List[UUID], 
        start_date: datetime, 
        end_date: datetime,
        period_type: PeriodType
    ) -> Dict[str, Any]:
        """Calculate comparative trend analysis across accounts."""
        try:
            # Placeholder for comparative analysis
            return {
                'convergence_analysis': 'accounts_diverging',
                'correlation_matrix': {},
                'leader_changes': 5,
                'average_volatility': 15.2
            }
            
        except Exception as e:
            logger.error(f"Error calculating comparative trends: {e}")
            return {}