"""
Signal Generation Engine

Main orchestrator for the comprehensive signal generation system that integrates
Wyckoff pattern detection, volume analysis, risk-reward optimization, and
frequency management to produce high-confidence trading signals.
"""

from typing import Dict, List, Tuple, Optional, Any
import pandas as pd
import numpy as np
from decimal import Decimal
from datetime import datetime, timedelta
import logging
import asyncio

from .signal_metadata import TradingSignal, ConfidenceBreakdown, MarketContext, PatternDetails, EntryConfirmation
from .parameter_calculator import SignalParameterCalculator
from .risk_reward_optimizer import RiskRewardOptimizer
from .frequency_manager import SignalFrequencyManager
from .market_state_detector import MarketStateDetector
from .performance_tracker import SignalPerformanceTracker

# Import existing components
from ..wyckoff.confidence_scorer import PatternConfidenceScorer
from ..wyckoff.phase_detector import WyckoffPhaseDetector
from ..volume_analysis.wyckoff_integration import WyckoffVolumeIntegrator

logger = logging.getLogger(__name__)


class SignalGenerator:
    """
    Comprehensive signal generation engine that produces high-confidence trading signals.
    
    Features:
    - Integration with Wyckoff pattern detection and volume analysis
    - Confidence threshold filtering (>75%)
    - Risk-reward optimization (minimum 1:2)
    - Signal frequency management (max 3 per week per account)
    - Market state filtering
    - Comprehensive signal metadata and performance tracking
    """
    
    def __init__(self,
                 confidence_threshold: float = 75.0,
                 min_risk_reward: float = 2.0,
                 enable_market_filtering: bool = True,
                 enable_frequency_management: bool = True,
                 enable_performance_tracking: bool = True):
        """
        Initialize the signal generation engine.
        
        Args:
            confidence_threshold: Minimum confidence for signal generation
            min_risk_reward: Minimum risk-reward ratio required
            enable_market_filtering: Enable market state filtering
            enable_frequency_management: Enable frequency controls
            enable_performance_tracking: Enable performance tracking
        """
        self.confidence_threshold = confidence_threshold
        self.min_risk_reward = min_risk_reward
        self.enable_market_filtering = enable_market_filtering
        self.enable_frequency_management = enable_frequency_management
        self.enable_performance_tracking = enable_performance_tracking
        
        # Initialize components
        self.parameter_calculator = SignalParameterCalculator(min_risk_reward=min_risk_reward)
        self.rr_optimizer = RiskRewardOptimizer(min_risk_reward=min_risk_reward)
        self.frequency_manager = SignalFrequencyManager() if enable_frequency_management else None
        self.market_state_detector = MarketStateDetector() if enable_market_filtering else None
        self.performance_tracker = SignalPerformanceTracker() if enable_performance_tracking else None
        
        # Initialize Wyckoff components
        self.confidence_scorer = PatternConfidenceScorer()
        self.phase_detector = WyckoffPhaseDetector()
        self.volume_integrator = WyckoffVolumeIntegrator()
        
        # Signal generation statistics
        self.generation_stats = {
            'total_attempts': 0,
            'signals_generated': 0,
            'filtered_by_confidence': 0,
            'filtered_by_rr': 0,
            'filtered_by_market_state': 0,
            'filtered_by_frequency': 0,
            'last_reset': datetime.now()
        }
    
    async def generate_signal(self,
                            symbol: str,
                            timeframe: str,
                            price_data: pd.DataFrame,
                            volume_data: pd.Series,
                            account_id: str = None) -> Dict:
        """
        Main signal generation pipeline.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe for analysis
            price_data: OHLC price data
            volume_data: Volume data
            account_id: Account identifier for frequency management
            
        Returns:
            Dict containing signal or rejection reason
        """
        self.generation_stats['total_attempts'] += 1
        
        try:
            # Step 1: Detect Wyckoff patterns
            logger.debug(f"Starting signal generation for {symbol} {timeframe}")
            patterns = await self._detect_wyckoff_patterns(price_data, volume_data)
            
            if not patterns:
                return {
                    'signal_generated': False,
                    'reason': 'no_patterns_detected',
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'timestamp': datetime.now()
                }
            
            # Step 2: Enhance patterns with volume analysis
            enhanced_patterns = await self._enhance_patterns_with_volume(
                patterns, price_data, volume_data
            )
            
            # Step 3: Filter by confidence threshold
            high_confidence_patterns = [
                p for p in enhanced_patterns 
                if p.get('confidence', 0) >= self.confidence_threshold
            ]
            
            if not high_confidence_patterns:
                self.generation_stats['filtered_by_confidence'] += 1
                return {
                    'signal_generated': False,
                    'reason': 'insufficient_confidence',
                    'highest_confidence': max([p.get('confidence', 0) for p in enhanced_patterns]),
                    'required_confidence': self.confidence_threshold,
                    'patterns_detected': len(patterns)
                }
            
            # Step 4: Check market state suitability
            if self.enable_market_filtering:
                market_state_analysis = await self._analyze_market_state(price_data, volume_data)
                
                if not market_state_analysis.get('signals_recommended', True):
                    self.generation_stats['filtered_by_market_state'] += 1
                    return {
                        'signal_generated': False,
                        'reason': 'unsuitable_market_state',
                        'market_state': market_state_analysis.get('market_state'),
                        'suitability_score': market_state_analysis.get('trading_suitability', {}).get('suitability_score', 0),
                        'recommendations': market_state_analysis.get('trading_suitability', {}).get('recommendations', [])
                    }
            else:
                market_state_analysis = {'market_state': 'analysis_disabled'}
            
            # Step 5: Select best pattern
            best_pattern = self._select_best_pattern(high_confidence_patterns)
            
            # Step 6: Calculate signal parameters
            signal_params = await self._calculate_signal_parameters(
                best_pattern, price_data, volume_data, market_state_analysis
            )
            
            # Step 7: Optimize risk-reward ratio
            optimization_result = self.rr_optimizer.optimize_signal_parameters(
                signal_params, best_pattern, price_data, market_state_analysis
            )
            
            if not optimization_result.get('success', False):
                self.generation_stats['filtered_by_rr'] += 1
                return {
                    'signal_generated': False,
                    'reason': 'insufficient_risk_reward',
                    'optimization_details': optimization_result,
                    'required_rr': self.min_risk_reward
                }
            
            optimized_params = optimization_result['params']
            
            # Step 8: Check frequency limits (if enabled and account provided)
            if self.enable_frequency_management and account_id:
                frequency_check = self.frequency_manager.check_signal_allowance(
                    account_id, optimized_params, symbol
                )
                
                if not frequency_check.get('allowed', False):
                    self.generation_stats['filtered_by_frequency'] += 1
                    return {
                        'signal_generated': False,
                        'reason': 'frequency_limit_exceeded',
                        'frequency_details': frequency_check
                    }
            else:
                frequency_check = {'allowed': True, 'reason': 'frequency_management_disabled'}
            
            # Step 9: Create comprehensive signal metadata
            signal = await self._create_trading_signal(
                symbol, timeframe, best_pattern, optimized_params, 
                market_state_analysis, account_id
            )
            
            # Step 10: Register signal with frequency manager
            if self.enable_frequency_management and account_id:
                registration = self.frequency_manager.register_signal(
                    account_id, signal.to_dict(), symbol,
                    replace_signal_id=frequency_check.get('signal_to_replace', {}).get('signal_id')
                )
            else:
                registration = {'registered': True, 'reason': 'frequency_management_disabled'}
            
            # Step 11: Log generation success
            self.generation_stats['signals_generated'] += 1
            logger.info(f"Signal generated for {symbol}: {signal.pattern_type} "
                       f"(confidence: {signal.confidence}%, R:R: {signal.risk_reward_ratio}:1)")
            
            return {
                'signal_generated': True,
                'signal': signal,
                'signal_dict': signal.to_dict(),
                'generation_metadata': {
                    'patterns_analyzed': len(patterns),
                    'patterns_high_confidence': len(high_confidence_patterns),
                    'market_state_analysis': market_state_analysis,
                    'optimization_applied': optimization_result.get('optimization_summary', {}),
                    'frequency_check': frequency_check,
                    'registration': registration,
                    'generation_timestamp': datetime.now()
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating signal for {symbol}: {str(e)}")
            return {
                'signal_generated': False,
                'reason': 'generation_error',
                'error': str(e),
                'symbol': symbol,
                'timeframe': timeframe
            }
    
    async def _detect_wyckoff_patterns(self, price_data: pd.DataFrame, volume_data: pd.Series) -> List[Dict]:
        """Detect Wyckoff patterns using the phase detector"""
        try:
            # Use the existing PhaseDetector
            patterns = self.phase_detector.detect_patterns(price_data, volume_data)
            
            # Convert to list format if needed
            if isinstance(patterns, dict):
                patterns = [patterns] if patterns.get('type') else []
            
            return patterns or []
            
        except Exception as e:
            logger.error(f"Error detecting Wyckoff patterns: {e}")
            return []
    
    async def _enhance_patterns_with_volume(self, 
                                          patterns: List[Dict],
                                          price_data: pd.DataFrame,
                                          volume_data: pd.Series) -> List[Dict]:
        """Enhance patterns with volume analysis"""
        try:
            enhanced_patterns = []
            
            for pattern in patterns:
                # Use volume integrator to enhance pattern
                enhanced_pattern = self.volume_integrator.enhance_pattern_with_volume(
                    pattern, price_data, volume_data
                )
                
                # Calculate enhanced confidence score
                enhanced_confidence = self.confidence_scorer.calculate_confidence(
                    enhanced_pattern, price_data, volume_data
                )
                
                enhanced_pattern['confidence'] = enhanced_confidence
                enhanced_patterns.append(enhanced_pattern)
            
            return enhanced_patterns
            
        except Exception as e:
            logger.error(f"Error enhancing patterns with volume: {e}")
            return patterns  # Return original patterns if enhancement fails
    
    async def _analyze_market_state(self, price_data: pd.DataFrame, volume_data: pd.Series) -> Dict:
        """Analyze market state for signal filtering"""
        try:
            market_analysis = self.market_state_detector.detect_market_state(price_data, volume_data)
            return market_analysis
        except Exception as e:
            logger.error(f"Error analyzing market state: {e}")
            return {'market_state': 'analysis_error', 'signals_recommended': True}
    
    def _select_best_pattern(self, patterns: List[Dict]) -> Dict:
        """Select the best pattern from high-confidence patterns"""
        if not patterns:
            return {}
        
        # Sort by confidence and pattern quality
        def pattern_score(pattern):
            confidence = pattern.get('confidence', 0)
            strength = pattern.get('strength', 50)
            
            # Pattern type preferences (some patterns are inherently better)
            type_scores = {
                'spring': 100,
                'upthrust': 100,
                'sign_of_strength': 90,
                'sign_of_weakness': 90,
                'accumulation': 85,
                'distribution': 85,
                'backup': 80,
                'test': 75
            }
            
            type_score = type_scores.get(pattern.get('type', 'unknown'), 60)
            
            # Composite score
            return (confidence * 0.5) + (strength * 0.3) + (type_score * 0.2)
        
        return max(patterns, key=pattern_score)
    
    async def _calculate_signal_parameters(self,
                                         pattern: Dict,
                                         price_data: pd.DataFrame,
                                         volume_data: pd.Series,
                                         market_context: Dict) -> Dict:
        """Calculate signal parameters using the parameter calculator"""
        try:
            params = self.parameter_calculator.calculate_signal_parameters(
                pattern, price_data, volume_data, market_context
            )
            return params
        except Exception as e:
            logger.error(f"Error calculating signal parameters: {e}")
            return {}
    
    async def _create_trading_signal(self,
                                   symbol: str,
                                   timeframe: str,
                                   pattern: Dict,
                                   optimized_params: Dict,
                                   market_analysis: Dict,
                                   account_id: str = None) -> TradingSignal:
        """Create comprehensive TradingSignal object"""
        
        # Extract confidence breakdown
        confidence_breakdown = ConfidenceBreakdown(
            pattern_confidence=pattern.get('confidence', 0),
            volume_confirmation=pattern.get('volume_confirmation', 0),
            timeframe_alignment=pattern.get('timeframe_alignment', 80),
            market_context=market_analysis.get('trading_suitability', {}).get('suitability_score', 60),
            trend_strength=pattern.get('trend_strength', 70),
            support_resistance=pattern.get('sr_strength', 75),
            total_confidence=pattern.get('confidence', 0)
        )
        
        # Extract market context
        market_context = MarketContext(
            session=market_analysis.get('session_analysis', {}).get('current_session', 'unknown'),
            volatility_regime=market_analysis.get('volatility_analysis', {}).get('regime', 'normal'),
            market_state=market_analysis.get('market_state', 'unknown'),
            trend_direction=market_analysis.get('trend_analysis', {}).get('direction', 'sideways'),
            trend_strength=market_analysis.get('trend_analysis', {}).get('strength', 50),
            atr_normalized=market_analysis.get('volatility_analysis', {}).get('atr_percentage', 1.0),
            volume_regime=market_analysis.get('volume_analysis', {}).get('regime', 'normal')
        )
        
        # Extract pattern details
        pattern_details = PatternDetails(
            pattern_type=pattern.get('type', 'unknown'),
            wyckoff_phase=pattern.get('wyckoff_phase', 'Unknown'),
            pattern_stage=pattern.get('stage', 'mature'),
            key_levels={
                'support': pattern.get('support_level', 0),
                'resistance': pattern.get('resistance_level', 0),
                'entry': float(optimized_params.get('entry_price', 0)),
                'stop': float(optimized_params.get('stop_loss', 0))
            },
            pattern_duration_bars=pattern.get('duration_bars', 20),
            pattern_height_points=pattern.get('height_points', 0),
            volume_characteristics=pattern.get('volume_characteristics', {}),
            invalidation_level=pattern.get('invalidation_level', 0)
        )
        
        # Extract entry confirmation
        entry_confirmation_data = optimized_params.get('entry_confirmation', {})
        entry_confirmation = EntryConfirmation(
            volume_spike_required=entry_confirmation_data.get('volume_spike_required', True),
            volume_threshold_multiplier=entry_confirmation_data.get('volume_threshold_multiplier', 2.0),
            momentum_threshold=entry_confirmation_data.get('momentum_threshold', 0.3),
            timeout_minutes=entry_confirmation_data.get('timeout_minutes', 60),
            price_confirmation_required=entry_confirmation_data.get('price_confirmation_required', True),
            min_candle_close_percentage=entry_confirmation_data.get('min_candle_close_percentage', 0.7)
        )
        
        # Extract timing estimates
        timing_estimates = optimized_params.get('timing_estimates', {})
        
        # Create TradingSignal
        signal = TradingSignal(
            signal_id=None,  # Will be generated in __post_init__
            symbol=symbol,
            timeframe=timeframe,
            signal_type=optimized_params.get('signal_type', 'long'),
            pattern_type=pattern.get('type', 'unknown'),
            confidence=pattern.get('confidence', 0),
            confidence_breakdown=confidence_breakdown,
            entry_price=optimized_params.get('entry_price', Decimal('0')),
            stop_loss=optimized_params.get('stop_loss', Decimal('0')),
            take_profit_1=optimized_params.get('take_profit_1', Decimal('0')),
            take_profit_2=optimized_params.get('take_profit_2'),
            take_profit_3=optimized_params.get('take_profit_3'),
            generated_at=datetime.now(),
            valid_until=timing_estimates.get('valid_until', datetime.now() + timedelta(hours=24)),
            expected_hold_time_hours=timing_estimates.get('expected_hold_time_hours', 24),
            market_context=market_context,
            pattern_details=pattern_details,
            entry_confirmation=entry_confirmation,
            contributing_factors=self._identify_contributing_factors(pattern, optimized_params, market_analysis)
        )
        
        return signal
    
    def _identify_contributing_factors(self, 
                                     pattern: Dict,
                                     params: Dict,
                                     market_analysis: Dict) -> List[str]:
        """Identify factors that contributed to signal generation"""
        factors = []
        
        # Pattern-specific factors
        pattern_type = pattern.get('type')
        if pattern_type:
            factors.append(f"wyckoff_{pattern_type}_pattern")
        
        # Confidence factors
        confidence = pattern.get('confidence', 0)
        if confidence >= 90:
            factors.append('very_high_confidence')
        elif confidence >= 85:
            factors.append('high_confidence')
        
        # Volume factors
        if pattern.get('volume_confirmation', 0) > 80:
            factors.append('strong_volume_confirmation')
        
        # Risk-reward factors
        rr_ratio = params.get('optimization_metadata', {}).get('optimized_rr', 0)
        if rr_ratio >= 4:
            factors.append('excellent_risk_reward')
        elif rr_ratio >= 3:
            factors.append('good_risk_reward')
        
        # Market context factors
        market_state = market_analysis.get('market_state')
        if market_state == 'trending':
            factors.append('trending_market')
        elif market_state == 'breakout':
            factors.append('breakout_conditions')
        
        # Volatility factors
        volatility = market_analysis.get('volatility_analysis', {}).get('regime')
        if volatility == 'normal':
            factors.append('normal_volatility')
        
        return factors
    
    def get_generation_statistics(self) -> Dict:
        """Get signal generation statistics"""
        stats = self.generation_stats.copy()
        
        # Calculate success rates
        if stats['total_attempts'] > 0:
            stats['success_rate'] = (stats['signals_generated'] / stats['total_attempts']) * 100
            stats['confidence_filter_rate'] = (stats['filtered_by_confidence'] / stats['total_attempts']) * 100
            stats['rr_filter_rate'] = (stats['filtered_by_rr'] / stats['total_attempts']) * 100
            stats['market_filter_rate'] = (stats['filtered_by_market_state'] / stats['total_attempts']) * 100
            stats['frequency_filter_rate'] = (stats['filtered_by_frequency'] / stats['total_attempts']) * 100
        else:
            stats.update({
                'success_rate': 0,
                'confidence_filter_rate': 0,
                'rr_filter_rate': 0,
                'market_filter_rate': 0,
                'frequency_filter_rate': 0
            })
        
        return stats
    
    def reset_generation_statistics(self):
        """Reset generation statistics"""
        self.generation_stats = {
            'total_attempts': 0,
            'signals_generated': 0,
            'filtered_by_confidence': 0,
            'filtered_by_rr': 0,
            'filtered_by_market_state': 0,
            'filtered_by_frequency': 0,
            'last_reset': datetime.now()
        }
    
    def update_configuration(self, config_updates: Dict) -> Dict:
        """Update signal generator configuration"""
        updated_params = []
        
        if 'confidence_threshold' in config_updates:
            old_threshold = self.confidence_threshold
            self.confidence_threshold = config_updates['confidence_threshold']
            updated_params.append(f"confidence_threshold: {old_threshold} -> {self.confidence_threshold}")
        
        if 'min_risk_reward' in config_updates:
            old_rr = self.min_risk_reward
            self.min_risk_reward = config_updates['min_risk_reward']
            self.parameter_calculator.min_risk_reward = self.min_risk_reward
            self.rr_optimizer.min_risk_reward = self.min_risk_reward
            updated_params.append(f"min_risk_reward: {old_rr} -> {self.min_risk_reward}")
        
        if 'enable_market_filtering' in config_updates:
            self.enable_market_filtering = config_updates['enable_market_filtering']
            updated_params.append(f"market_filtering: {self.enable_market_filtering}")
        
        if 'enable_frequency_management' in config_updates:
            self.enable_frequency_management = config_updates['enable_frequency_management']
            updated_params.append(f"frequency_management: {self.enable_frequency_management}")
        
        logger.info(f"Updated signal generator configuration: {'; '.join(updated_params)}")
        
        return {
            'configuration_updated': True,
            'updated_parameters': updated_params,
            'current_configuration': {
                'confidence_threshold': self.confidence_threshold,
                'min_risk_reward': self.min_risk_reward,
                'enable_market_filtering': self.enable_market_filtering,
                'enable_frequency_management': self.enable_frequency_management,
                'enable_performance_tracking': self.enable_performance_tracking
            }
        }
    
    def get_active_signals_summary(self, account_id: str = None) -> Dict:
        """Get summary of active signals for monitoring"""
        if not self.enable_frequency_management or not account_id:
            return {'frequency_management_disabled': True}
        
        return self.frequency_manager.get_weekly_signal_capacity(account_id)