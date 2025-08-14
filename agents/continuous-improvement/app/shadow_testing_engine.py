"""
Shadow Testing Engine

Implements risk-free testing of new strategies and improvements by running them
in parallel with live trading without executing actual trades. This allows
comprehensive validation of improvements before real money deployment.

Key Features:
- Paper trading simulation with real market conditions
- Performance comparison against live trading
- Risk assessment and validation
- Signal generation and trade simulation
- Comprehensive performance analytics
"""

import logging
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Any, Tuple
import numpy as np
from dataclasses import asdict

from .models import (
    ImprovementTest, ShadowTestResults, PerformanceMetrics, PerformanceComparison,
    StatisticalAnalysis, TestGroup, Change
)

# Import data interfaces
from ...src.shared.python_utils.data_interfaces import (
    MarketDataInterface, MockMarketDataProvider,
    TradeDataInterface, MockTradeDataProvider,
    PerformanceDataInterface, MockPerformanceDataProvider
)

logger = logging.getLogger(__name__)


class ShadowTestingEngine:
    """
    Shadow testing engine for risk-free validation of trading improvements.
    
    This engine runs improvements in a simulated environment that mirrors
    live trading conditions but without executing real trades. It provides
    comprehensive performance analysis and risk assessment.
    """
    
    def __init__(self,
                 market_data_provider: Optional[MarketDataInterface] = None,
                 trade_data_provider: Optional[TradeDataInterface] = None,
                 performance_data_provider: Optional[PerformanceDataInterface] = None):
        
        # Data providers
        self.market_data_provider = market_data_provider or MockMarketDataProvider()
        self.trade_data_provider = trade_data_provider or MockTradeDataProvider()
        self.performance_data_provider = performance_data_provider or MockPerformanceDataProvider()
        
        # Shadow testing configuration
        self.config = {
            'min_shadow_duration': timedelta(days=7),  # Minimum shadow testing period
            'min_signals_required': 50,  # Minimum signals for validation
            'min_trades_simulated': 25,  # Minimum simulated trades
            'max_drawdown_threshold': Decimal('0.15'),  # 15% max drawdown
            'min_improvement_threshold': Decimal('0.02'),  # 2% minimum improvement
            'confidence_level': 0.95,  # 95% confidence for validation
            'risk_tolerance': Decimal('0.10')  # 10% additional risk tolerance
        }
        
        # Internal state
        self._active_shadow_tests: Dict[str, Dict] = {}
        self._shadow_results_cache: Dict[str, ShadowTestResults] = {}
        
        logger.info("Shadow Testing Engine initialized")
    
    async def start_shadow_test(self, test: ImprovementTest) -> bool:
        """
        Start shadow testing for an improvement test.
        
        Args:
            test: ImprovementTest to run in shadow mode
            
        Returns:
            bool: True if shadow test started successfully
        """
        try:
            logger.info(f"Starting shadow test for {test.test_id}")
            
            # Validate test configuration
            if not await self._validate_shadow_test_config(test):
                logger.error(f"Shadow test configuration invalid for {test.test_id}")
                return False
            
            # Initialize shadow environment
            shadow_env = await self._create_shadow_environment(test)
            
            # Start shadow execution
            self._active_shadow_tests[test.test_id] = {
                'test': test,
                'environment': shadow_env,
                'start_time': datetime.utcnow(),
                'signals_generated': 0,
                'trades_simulated': 0,
                'performance_tracking': {},
                'risk_metrics': {},
                'validation_status': 'running'
            }
            
            logger.info(f"Shadow test started for {test.test_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start shadow test for {test.test_id}: {e}")
            return False
    
    async def update_shadow_test(self, test_id: str) -> Optional[Dict]:
        """
        Update a running shadow test with latest market conditions.
        
        Args:
            test_id: ID of the test to update
            
        Returns:
            Dict with update results or None if test not found
        """
        if test_id not in self._active_shadow_tests:
            return None
        
        try:
            shadow_test = self._active_shadow_tests[test_id]
            test = shadow_test['test']
            
            # Get latest market data
            market_data = await self._get_current_market_state()
            
            # Generate signals using shadow strategy
            signals = await self._generate_shadow_signals(test, market_data)
            
            # Simulate trades based on signals
            simulated_trades = await self._simulate_trades(signals, market_data)
            
            # Update performance tracking
            await self._update_shadow_performance(test_id, simulated_trades)
            
            # Update counters
            shadow_test['signals_generated'] += len(signals)
            shadow_test['trades_simulated'] += len(simulated_trades)
            
            # Check completion criteria
            completion_status = await self._check_shadow_completion(test_id)
            
            return {
                'test_id': test_id,
                'signals_generated': len(signals),
                'trades_simulated': len(simulated_trades),
                'total_signals': shadow_test['signals_generated'],
                'total_trades': shadow_test['trades_simulated'],
                'completion_status': completion_status,
                'last_updated': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Failed to update shadow test {test_id}: {e}")
            return {'error': str(e)}
    
    async def evaluate_shadow_test(self, test: ImprovementTest) -> ShadowTestResults:
        """
        Evaluate completed shadow test and generate results.
        
        Args:
            test: ImprovementTest that completed shadow testing
            
        Returns:
            ShadowTestResults with comprehensive analysis
        """
        try:
            logger.info(f"Evaluating shadow test results for {test.test_id}")
            
            # Get shadow test data
            shadow_data = self._active_shadow_tests.get(test.test_id)
            if not shadow_data:
                # Try to load from cache
                cached_results = self._shadow_results_cache.get(test.test_id)
                if cached_results:
                    return cached_results
                raise ValueError(f"No shadow test data found for {test.test_id}")
            
            # Calculate shadow performance metrics
            shadow_performance = await self._calculate_shadow_performance(test.test_id)
            
            # Get live performance for comparison
            live_performance = await self._get_live_performance_baseline(test)
            
            # Perform statistical comparison
            comparison_results = await self._compare_shadow_vs_live(
                shadow_performance, live_performance
            )
            
            # Conduct risk analysis
            risk_analysis = await self._analyze_shadow_risks(test.test_id)
            
            # Generate validation results
            validation = await self._validate_shadow_results(
                shadow_performance, comparison_results, risk_analysis
            )
            
            # Create comprehensive results
            results = ShadowTestResults(
                test_id=test.test_id,
                start_date=shadow_data['start_time'],
                end_date=datetime.utcnow(),
                duration=datetime.utcnow() - shadow_data['start_time'],
                total_signals=shadow_data['signals_generated'],
                trades_executed=shadow_data['trades_simulated'],
                simulated_performance=shadow_performance,
                comparison_to_live=comparison_results,
                max_simulated_drawdown=risk_analysis['max_drawdown'],
                volatility_increase=risk_analysis['volatility_increase'],
                correlation_impact=risk_analysis['correlation_impact'],
                risk_score=risk_analysis['overall_risk_score'],
                validation_passed=validation['passed'],
                validation_issues=validation['issues'],
                performance_gain=comparison_results.relative_improvement if comparison_results else Decimal('0'),
                significance_level=validation['significance_level'],
                recommendation=validation['recommendation']
            )
            
            # Cache results
            self._shadow_results_cache[test.test_id] = results
            
            # Cleanup active test
            if test.test_id in self._active_shadow_tests:
                del self._active_shadow_tests[test.test_id]
            
            logger.info(f"Shadow test evaluation completed for {test.test_id}: {results.recommendation}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to evaluate shadow test for {test.test_id}: {e}")
            # Return failed results
            return ShadowTestResults(
                test_id=test.test_id,
                start_date=datetime.utcnow(),
                end_date=datetime.utcnow(),
                duration=timedelta(0),
                validation_passed=False,
                validation_issues=[f"Evaluation failed: {e}"],
                recommendation="reject"
            )
    
    async def _validate_shadow_test_config(self, test: ImprovementTest) -> bool:
        """Validate shadow test configuration"""
        
        # Check if test has required components
        if not test.treatment_group or not test.treatment_group.changes:
            logger.error(f"Test {test.test_id} missing treatment group or changes")
            return False
        
        # Validate changes can be shadow tested
        for change in test.treatment_group.changes:
            if not await self._can_shadow_test_change(change):
                logger.error(f"Change {change.change_id} cannot be shadow tested")
                return False
        
        # Check account allocation
        if not test.treatment_group.accounts:
            logger.error(f"Test {test.test_id} has no accounts assigned")
            return False
        
        return True
    
    async def _can_shadow_test_change(self, change: Change) -> bool:
        """Check if a specific change can be shadow tested"""
        
        # Changes that can be shadow tested
        shadowable_types = [
            'parameter', 'algorithm', 'strategy', 'feature'
        ]
        
        if change.change_type not in shadowable_types:
            return False
        
        # Check if change requires external systems
        if change.system_impact and 'external_api' in change.system_impact.lower():
            return False  # Cannot shadow test external API changes
        
        return True
    
    async def _create_shadow_environment(self, test: ImprovementTest) -> Dict:
        """Create isolated shadow testing environment"""
        
        environment = {
            'test_id': test.test_id,
            'accounts': test.treatment_group.accounts.copy(),
            'changes_applied': [],
            'strategy_config': {},
            'risk_parameters': {},
            'performance_tracking': {
                'trades': [],
                'signals': [],
                'pnl_history': [],
                'drawdown_history': [],
                'daily_returns': {}
            },
            'market_state': {},
            'simulation_parameters': {
                'execution_delay_ms': 100,  # Simulated execution delay
                'slippage_bps': 0.5,  # 0.5 basis points slippage
                'commission_per_lot': Decimal('7.00')  # $7 per lot
            }
        }
        
        # Apply changes to shadow environment
        for change in test.treatment_group.changes:
            shadow_change = await self._apply_shadow_change(change, environment)
            environment['changes_applied'].append(shadow_change)
        
        return environment
    
    async def _apply_shadow_change(self, change: Change, environment: Dict) -> Dict:
        """Apply a change to the shadow environment"""
        
        shadow_change = {
            'change_id': change.change_id,
            'type': change.change_type,
            'component': change.component,
            'old_value': change.old_value,
            'new_value': change.new_value,
            'applied_at': datetime.utcnow(),
            'shadow_config': {}
        }
        
        # Apply change based on type
        if change.change_type == 'parameter':
            await self._apply_parameter_change(change, environment)
        elif change.change_type == 'algorithm':
            await self._apply_algorithm_change(change, environment)
        elif change.change_type == 'strategy':
            await self._apply_strategy_change(change, environment)
        elif change.change_type == 'feature':
            await self._apply_feature_change(change, environment)
        
        return shadow_change
    
    async def _apply_parameter_change(self, change: Change, environment: Dict):
        """Apply parameter change to shadow environment"""
        
        # Update strategy configuration
        component = change.component
        if component not in environment['strategy_config']:
            environment['strategy_config'][component] = {}
        
        # Apply configuration changes
        for key, value in change.configuration_changes.items():
            environment['strategy_config'][component][key] = value
        
        logger.debug(f"Applied parameter change for {component}: {change.configuration_changes}")
    
    async def _apply_algorithm_change(self, change: Change, environment: Dict):
        """Apply algorithm change to shadow environment"""
        
        # For shadow testing, we simulate algorithm changes through parameter modifications
        # Real implementation would load different algorithm versions
        
        algorithm_config = {
            'algorithm_version': change.new_value,
            'algorithm_parameters': change.configuration_changes,
            'simulation_mode': True
        }
        
        environment['strategy_config'][change.component] = algorithm_config
        logger.debug(f"Applied algorithm change for {change.component}")
    
    async def _apply_strategy_change(self, change: Change, environment: Dict):
        """Apply strategy change to shadow environment"""
        
        strategy_config = {
            'strategy_type': change.new_value,
            'strategy_parameters': change.configuration_changes,
            'enabled': True,
            'shadow_mode': True
        }
        
        environment['strategy_config'][change.component] = strategy_config
        logger.debug(f"Applied strategy change for {change.component}")
    
    async def _apply_feature_change(self, change: Change, environment: Dict):
        """Apply feature change to shadow environment"""
        
        feature_config = {
            'feature_enabled': True,
            'feature_parameters': change.configuration_changes,
            'testing_mode': True
        }
        
        environment['strategy_config'][change.component] = feature_config
        logger.debug(f"Applied feature change for {change.component}")
    
    async def _get_current_market_state(self) -> Dict:
        """Get current market state for signal generation"""
        
        # Get market data for major pairs
        symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF']
        market_state = {}
        
        for symbol in symbols:
            market_data = await self.market_data_provider.get_market_data_point(symbol)
            regime_data = await self.market_data_provider.get_regime_analysis(symbol)
            
            market_state[symbol] = {
                'price': market_data.price,
                'volume': market_data.volume,
                'volatility': market_data.volatility,
                'trend_strength': market_data.trend_strength,
                'regime_type': regime_data.regime_type,
                'regime_confidence': regime_data.confidence,
                'timestamp': market_data.timestamp
            }
        
        return market_state
    
    async def _generate_shadow_signals(self, test: ImprovementTest, market_data: Dict) -> List[Dict]:
        """Generate trading signals using shadow strategy"""
        
        signals = []
        environment = self._active_shadow_tests[test.test_id]['environment']
        
        # Simulate signal generation based on changes
        for symbol, data in market_data.items():
            
            # Check if strategy would generate signal
            signal_probability = await self._calculate_signal_probability(
                test, symbol, data, environment
            )
            
            # Generate signal based on probability and market conditions
            if signal_probability > 0.6:  # 60% threshold for signal generation
                signal = {
                    'signal_id': f"SIG_{test.test_id}_{symbol}_{datetime.utcnow().timestamp()}",
                    'test_id': test.test_id,
                    'symbol': symbol,
                    'signal_type': self._determine_signal_type(data, environment),
                    'direction': 'buy' if data['trend_strength'] > 0 else 'sell',
                    'strength': float(signal_probability),
                    'price': data['price'],
                    'timestamp': datetime.utcnow(),
                    'market_conditions': {
                        'volatility': float(data['volatility']),
                        'regime': data['regime_type'],
                        'trend_strength': float(data['trend_strength'])
                    }
                }
                signals.append(signal)
        
        logger.debug(f"Generated {len(signals)} shadow signals for {test.test_id}")
        return signals
    
    async def _calculate_signal_probability(self, test: ImprovementTest, symbol: str, 
                                         market_data: Dict, environment: Dict) -> float:
        """Calculate probability of signal generation based on changes and market conditions"""
        
        base_probability = 0.3  # Base 30% chance
        
        # Adjust based on market conditions
        volatility_factor = min(float(market_data['volatility']) * 10, 1.0)  # Higher volatility = more signals
        trend_factor = abs(float(market_data['trend_strength'])) * 2  # Stronger trends = more signals
        regime_factor = 0.8 if market_data['regime_type'] == 'trending' else 0.5  # Trending markets favored
        
        # Adjust based on strategy changes
        strategy_factor = 1.0
        for change in test.treatment_group.changes:
            if change.change_type == 'strategy':
                strategy_factor *= 1.2  # New strategies may generate more signals
            elif change.change_type == 'parameter':
                strategy_factor *= 1.1  # Parameter changes may increase sensitivity
        
        # Calculate final probability
        probability = base_probability * volatility_factor * trend_factor * regime_factor * strategy_factor
        return min(probability, 1.0)  # Cap at 100%
    
    def _determine_signal_type(self, market_data: Dict, environment: Dict) -> str:
        """Determine the type of signal to generate"""
        
        # Simple signal type determination based on market conditions
        volatility = float(market_data['volatility'])
        trend_strength = abs(float(market_data['trend_strength']))
        
        if trend_strength > 0.015:  # Strong trend
            return 'trend_following'
        elif volatility > 0.02:  # High volatility
            return 'volatility_breakout'
        elif market_data['regime_type'] == 'ranging':
            return 'mean_reversion'
        else:
            return 'momentum'
    
    async def _simulate_trades(self, signals: List[Dict], market_data: Dict) -> List[Dict]:
        """Simulate trade execution based on generated signals"""
        
        simulated_trades = []
        
        for signal in signals:
            # Simulate trade execution
            trade = await self._simulate_single_trade(signal, market_data)
            if trade:
                simulated_trades.append(trade)
        
        return simulated_trades
    
    async def _simulate_single_trade(self, signal: Dict, market_data: Dict) -> Optional[Dict]:
        """Simulate execution of a single trade"""
        
        symbol = signal['symbol']
        symbol_data = market_data.get(symbol)
        
        if not symbol_data:
            return None
        
        # Simulate execution parameters
        entry_price = symbol_data['price']
        size = Decimal('1.0')  # 1 lot
        direction = signal['direction']
        
        # Add slippage and execution delay effects
        slippage = Decimal('0.00005')  # 0.5 pips
        if direction == 'buy':
            actual_entry_price = entry_price + slippage
        else:
            actual_entry_price = entry_price - slippage
        
        # Simulate trade outcome (simplified)
        trade_duration = timedelta(minutes=np.random.randint(30, 480))  # 30min to 8hrs
        exit_time = datetime.utcnow() + trade_duration
        
        # Simple P&L simulation based on market volatility
        volatility = symbol_data['volatility']
        random_return = np.random.normal(0, float(volatility))
        
        if direction == 'buy':
            exit_price = actual_entry_price * (1 + Decimal(str(random_return)))
            pnl = (exit_price - actual_entry_price) * size
        else:
            exit_price = actual_entry_price * (1 - Decimal(str(random_return)))
            pnl = (actual_entry_price - exit_price) * size
        
        # Apply commission
        commission = Decimal('7.00')  # $7 per lot
        net_pnl = pnl - commission
        
        trade = {
            'trade_id': f"TRADE_{signal['test_id']}_{signal['signal_id']}",
            'test_id': signal['test_id'],
            'signal_id': signal['signal_id'],
            'symbol': symbol,
            'direction': direction,
            'size': float(size),
            'entry_price': float(actual_entry_price),
            'exit_price': float(exit_price),
            'entry_time': datetime.utcnow(),
            'exit_time': exit_time,
            'pnl': float(net_pnl),
            'commission': float(commission),
            'duration_minutes': trade_duration.total_seconds() / 60,
            'market_conditions_at_entry': signal['market_conditions']
        }
        
        return trade
    
    async def _update_shadow_performance(self, test_id: str, simulated_trades: List[Dict]):
        """Update performance tracking for shadow test"""
        
        shadow_test = self._active_shadow_tests[test_id]
        performance_tracking = shadow_test['environment']['performance_tracking']
        
        # Add new trades
        performance_tracking['trades'].extend(simulated_trades)
        
        # Update PnL history
        for trade in simulated_trades:
            performance_tracking['pnl_history'].append({
                'timestamp': trade['entry_time'],
                'pnl': trade['pnl'],
                'cumulative_pnl': sum(t['pnl'] for t in performance_tracking['trades'])
            })
        
        # Update daily returns
        today = datetime.utcnow().date()
        if today not in performance_tracking['daily_returns']:
            performance_tracking['daily_returns'][today] = 0.0
        
        for trade in simulated_trades:
            performance_tracking['daily_returns'][today] += trade['pnl']
    
    async def _check_shadow_completion(self, test_id: str) -> str:
        """Check if shadow test meets completion criteria"""
        
        shadow_test = self._active_shadow_tests[test_id]
        start_time = shadow_test['start_time']
        
        # Check duration
        duration = datetime.utcnow() - start_time
        if duration < self.config['min_shadow_duration']:
            return 'insufficient_duration'
        
        # Check signal count
        if shadow_test['signals_generated'] < self.config['min_signals_required']:
            return 'insufficient_signals'
        
        # Check trade count
        if shadow_test['trades_simulated'] < self.config['min_trades_simulated']:
            return 'insufficient_trades'
        
        return 'complete'
    
    async def _calculate_shadow_performance(self, test_id: str) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics for shadow test"""
        
        shadow_test = self._active_shadow_tests[test_id]
        trades = shadow_test['environment']['performance_tracking']['trades']
        
        if not trades:
            return PerformanceMetrics()
        
        # Calculate basic metrics
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t['pnl'] > 0])
        losing_trades = len([t for t in trades if t['pnl'] < 0])
        
        win_rate = Decimal(str(winning_trades / total_trades)) if total_trades > 0 else Decimal('0')
        
        # PnL calculations
        total_pnl = sum(Decimal(str(t['pnl'])) for t in trades)
        winning_pnl = sum(Decimal(str(t['pnl'])) for t in trades if t['pnl'] > 0)
        losing_pnl = sum(Decimal(str(abs(t['pnl']))) for t in trades if t['pnl'] < 0)
        
        average_win = winning_pnl / winning_trades if winning_trades > 0 else Decimal('0')
        average_loss = losing_pnl / losing_trades if losing_trades > 0 else Decimal('0')
        
        profit_factor = winning_pnl / losing_pnl if losing_pnl > 0 else Decimal('1000')
        expectancy = (win_rate * average_win) - ((Decimal('1') - win_rate) * average_loss)
        
        # Calculate drawdown
        cumulative_pnl = Decimal('0')
        peak = Decimal('0')
        max_drawdown = Decimal('0')
        
        for trade in trades:
            cumulative_pnl += Decimal(str(trade['pnl']))
            peak = max(peak, cumulative_pnl)
            drawdown = peak - cumulative_pnl
            max_drawdown = max(max_drawdown, drawdown)
        
        # Calculate Sharpe ratio (simplified)
        daily_returns = list(shadow_test['environment']['performance_tracking']['daily_returns'].values())
        if len(daily_returns) > 1:
            returns_array = np.array(daily_returns)
            mean_return = np.mean(returns_array)
            std_return = np.std(returns_array)
            sharpe_ratio = Decimal(str(mean_return / std_return)) if std_return > 0 else Decimal('0')
        else:
            sharpe_ratio = Decimal('0')
        
        # Calculate volatility
        if len(daily_returns) > 1:
            volatility = Decimal(str(np.std(daily_returns)))
        else:
            volatility = Decimal('0')
        
        return PerformanceMetrics(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            profit_factor=profit_factor,
            expectancy=expectancy,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            total_return=total_pnl,
            average_win=average_win,
            average_loss=average_loss,
            volatility=volatility
        )
    
    async def _get_live_performance_baseline(self, test: ImprovementTest) -> PerformanceMetrics:
        """Get baseline live performance for comparison"""
        
        # Get performance data for control group accounts
        if not test.control_group or not test.control_group.accounts:
            # Return mock baseline if no control group
            return PerformanceMetrics(
                total_trades=100,
                win_rate=Decimal('0.55'),
                profit_factor=Decimal('1.2'),
                sharpe_ratio=Decimal('0.8'),
                max_drawdown=Decimal('0.08'),
                total_return=Decimal('0.05'),
                expectancy=Decimal('0.001')
            )
        
        # Aggregate performance across control accounts
        total_performance = PerformanceMetrics()
        
        for account_id in test.control_group.accounts:
            account_perf = await self.performance_data_provider.get_account_performance(
                account_id, 'monthly'
            )
            if account_perf:
                # Aggregate metrics (simplified)
                total_performance.total_trades += account_perf.total_trades
                total_performance.total_return += account_perf.total_return
                # ... aggregate other metrics
        
        return total_performance
    
    async def _compare_shadow_vs_live(self, shadow_perf: PerformanceMetrics, 
                                    live_perf: PerformanceMetrics) -> PerformanceComparison:
        """Compare shadow performance against live baseline"""
        
        # Calculate relative improvement
        if live_perf.expectancy != 0:
            relative_improvement = (shadow_perf.expectancy - live_perf.expectancy) / abs(live_perf.expectancy)
        else:
            relative_improvement = shadow_perf.expectancy
        
        # Calculate absolute difference
        absolute_difference = shadow_perf.expectancy - live_perf.expectancy
        
        # Calculate percentage improvement
        if live_perf.total_return != 0:
            percentage_improvement = (shadow_perf.total_return - live_perf.total_return) / abs(live_perf.total_return) * 100
        else:
            percentage_improvement = shadow_perf.total_return * 100
        
        # Perform statistical analysis (simplified)
        statistical_analysis = StatisticalAnalysis(
            sample_size=shadow_perf.total_trades,
            power_analysis=0.8,
            p_value=0.05,  # Placeholder
            confidence_interval=(float(relative_improvement) - 0.02, float(relative_improvement) + 0.02),
            effect_size=float(abs(relative_improvement)),
            statistically_significant=abs(relative_improvement) > Decimal('0.02')
        )
        
        return PerformanceComparison(
            control_performance=live_perf,
            treatment_performance=shadow_perf,
            relative_improvement=relative_improvement,
            absolute_difference=absolute_difference,
            percentage_improvement=percentage_improvement,
            statistical_analysis=statistical_analysis,
            risk_adjusted_improvement=relative_improvement  # Simplified
        )
    
    async def _analyze_shadow_risks(self, test_id: str) -> Dict:
        """Analyze risks associated with shadow test"""
        
        shadow_test = self._active_shadow_tests[test_id]
        trades = shadow_test['environment']['performance_tracking']['trades']
        
        if not trades:
            return {
                'max_drawdown': Decimal('0'),
                'volatility_increase': Decimal('0'),
                'correlation_impact': Decimal('0'),
                'overall_risk_score': 50
            }
        
        # Calculate maximum drawdown
        cumulative_pnl = Decimal('0')
        peak = Decimal('0')
        max_drawdown = Decimal('0')
        
        for trade in trades:
            cumulative_pnl += Decimal(str(trade['pnl']))
            peak = max(peak, cumulative_pnl)
            drawdown = peak - cumulative_pnl
            max_drawdown = max(max_drawdown, drawdown)
        
        # Calculate volatility
        daily_returns = list(shadow_test['environment']['performance_tracking']['daily_returns'].values())
        volatility = Decimal(str(np.std(daily_returns))) if len(daily_returns) > 1 else Decimal('0')
        
        # Estimate volatility increase (placeholder)
        baseline_volatility = Decimal('0.015')  # 1.5% baseline
        volatility_increase = (volatility - baseline_volatility) / baseline_volatility if baseline_volatility > 0 else Decimal('0')
        
        # Calculate overall risk score (0-100, lower is better)
        drawdown_score = min(float(max_drawdown) * 1000, 100)  # Drawdown component
        volatility_score = min(float(volatility) * 1000, 50)   # Volatility component
        overall_risk_score = int(drawdown_score + volatility_score)
        
        return {
            'max_drawdown': max_drawdown,
            'volatility_increase': volatility_increase,
            'correlation_impact': Decimal('0'),  # Placeholder
            'overall_risk_score': overall_risk_score
        }
    
    async def _validate_shadow_results(self, shadow_perf: PerformanceMetrics,
                                     comparison: PerformanceComparison,
                                     risk_analysis: Dict) -> Dict:
        """Validate shadow test results against acceptance criteria"""
        
        validation = {
            'passed': True,
            'issues': [],
            'significance_level': 0.95,
            'recommendation': 'proceed'
        }
        
        # Check minimum improvement threshold
        if comparison.relative_improvement < self.config['min_improvement_threshold']:
            validation['issues'].append(
                f"Improvement {comparison.relative_improvement:.2%} below minimum threshold {self.config['min_improvement_threshold']:.2%}"
            )
        
        # Check maximum drawdown
        if risk_analysis['max_drawdown'] > self.config['max_drawdown_threshold']:
            validation['issues'].append(
                f"Max drawdown {risk_analysis['max_drawdown']:.2%} exceeds threshold {self.config['max_drawdown_threshold']:.2%}"
            )
            validation['passed'] = False
        
        # Check statistical significance
        if not comparison.statistical_analysis.statistically_significant:
            validation['issues'].append("Results not statistically significant")
        
        # Check sample size
        if shadow_perf.total_trades < self.config['min_trades_simulated']:
            validation['issues'].append(
                f"Insufficient trades: {shadow_perf.total_trades} < {self.config['min_trades_simulated']}"
            )
            validation['passed'] = False
        
        # Check risk score
        if risk_analysis['overall_risk_score'] > 80:
            validation['issues'].append(f"High risk score: {risk_analysis['overall_risk_score']}")
            validation['passed'] = False
        
        # Determine recommendation
        if not validation['passed']:
            validation['recommendation'] = 'reject'
        elif validation['issues']:
            validation['recommendation'] = 'modify'
        else:
            validation['recommendation'] = 'proceed'
        
        return validation
    
    # Public API methods
    
    async def get_active_shadow_tests(self) -> List[Dict]:
        """Get list of currently active shadow tests"""
        return [
            {
                'test_id': test_id,
                'start_time': data['start_time'],
                'signals_generated': data['signals_generated'],
                'trades_simulated': data['trades_simulated'],
                'validation_status': data['validation_status']
            }
            for test_id, data in self._active_shadow_tests.items()
        ]
    
    async def get_shadow_test_status(self, test_id: str) -> Optional[Dict]:
        """Get detailed status of a specific shadow test"""
        if test_id not in self._active_shadow_tests:
            return None
        
        data = self._active_shadow_tests[test_id]
        
        return {
            'test_id': test_id,
            'start_time': data['start_time'],
            'duration': datetime.utcnow() - data['start_time'],
            'signals_generated': data['signals_generated'],
            'trades_simulated': data['trades_simulated'],
            'validation_status': data['validation_status'],
            'completion_status': await self._check_shadow_completion(test_id),
            'current_performance': await self._calculate_shadow_performance(test_id) if data['trades_simulated'] > 0 else None
        }
    
    async def stop_shadow_test(self, test_id: str, reason: str = "Manual stop") -> bool:
        """Stop a running shadow test"""
        if test_id not in self._active_shadow_tests:
            return False
        
        logger.info(f"Stopping shadow test {test_id}: {reason}")
        
        # Update validation status
        self._active_shadow_tests[test_id]['validation_status'] = f'stopped: {reason}'
        
        return True