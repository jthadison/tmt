"""
Signal Frequency Manager

Manages signal generation frequency to prevent overtrading by enforcing
weekly limits per account and providing intelligent signal prioritization
and substitution mechanisms.
"""

from typing import Dict, List, Tuple, Optional
import pandas as pd
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import logging
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


class SignalFrequencyManager:
    """
    Manages signal generation frequency and quality-based prioritization.
    
    Features:
    - Weekly signal limits per account (default: 3)
    - Signal quality scoring and ranking
    - Intelligent signal substitution
    - Cooling-off periods between similar signals
    - Account-specific signal preferences
    """
    
    def __init__(self,
                 default_weekly_limit: int = 3,
                 cooling_off_hours: int = 24,
                 min_quality_score: float = 60.0,
                 enable_substitution: bool = True):
        """
        Initialize frequency manager.
        
        Args:
            default_weekly_limit: Default weekly signal limit per account
            cooling_off_hours: Hours to wait before similar signals
            min_quality_score: Minimum quality score for signal acceptance
            enable_substitution: Allow replacing lower quality signals
        """
        self.default_weekly_limit = default_weekly_limit
        self.cooling_off_hours = cooling_off_hours
        self.min_quality_score = min_quality_score
        self.enable_substitution = enable_substitution
        
        # In-memory storage (would be replaced with database in production)
        self.signal_history = defaultdict(list)  # account_id -> [signals]
        self.account_limits = {}  # account_id -> custom limit
        self.account_preferences = defaultdict(dict)  # account_id -> preferences
        self.signal_cooldowns = defaultdict(list)  # symbol -> [(timestamp, pattern_type)]
    
    def check_signal_allowance(self, 
                              account_id: str,
                              proposed_signal: Dict,
                              symbol: str) -> Dict:
        """
        Check if account can accept a new signal based on frequency limits.
        
        Args:
            account_id: Trading account identifier
            proposed_signal: The signal being evaluated
            symbol: Trading symbol
            
        Returns:
            Dict with allowance decision and metadata
        """
        # Get current week's signals for this account
        current_week_signals = self._get_current_week_signals(account_id)
        weekly_limit = self._get_account_weekly_limit(account_id)
        
        # Check cooling-off period
        cooldown_check = self._check_cooling_off_period(symbol, proposed_signal)
        if not cooldown_check['allowed']:
            return {
                'allowed': False,
                'reason': 'cooling_off_period',
                'details': cooldown_check,
                'next_allowed_time': cooldown_check['next_allowed_time']
            }
        
        # If under limit, allow signal
        if len(current_week_signals) < weekly_limit:
            return {
                'allowed': True,
                'reason': 'under_limit',
                'current_count': len(current_week_signals),
                'weekly_limit': weekly_limit,
                'slots_remaining': weekly_limit - len(current_week_signals)
            }
        
        # At limit - check if substitution is possible
        if self.enable_substitution:
            substitution_result = self._evaluate_signal_substitution(
                account_id, proposed_signal, current_week_signals
            )
            
            if substitution_result['substitution_possible']:
                return {
                    'allowed': True,
                    'reason': 'substitution',
                    'substitution_details': substitution_result,
                    'signal_to_replace': substitution_result['signal_to_replace']
                }
        
        # Over limit and no substitution possible
        return {
            'allowed': False,
            'reason': 'weekly_limit_exceeded',
            'current_count': len(current_week_signals),
            'weekly_limit': weekly_limit,
            'lowest_quality_signal': self._find_lowest_quality_signal(current_week_signals),
            'suggested_improvements': self._suggest_signal_improvements(proposed_signal)
        }
    
    def register_signal(self, 
                       account_id: str,
                       signal: Dict,
                       symbol: str,
                       replace_signal_id: str = None) -> Dict:
        """
        Register a new signal with the frequency manager.
        
        Args:
            account_id: Trading account identifier
            signal: Complete signal information
            symbol: Trading symbol
            replace_signal_id: ID of signal to replace (for substitution)
            
        Returns:
            Registration confirmation
        """
        signal_record = {
            'signal_id': signal.get('signal_id'),
            'symbol': symbol,
            'pattern_type': signal.get('pattern_type'),
            'confidence': signal.get('confidence'),
            'quality_score': signal.get('quality_score', 0),
            'risk_reward_ratio': signal.get('risk_reward_ratio'),
            'generated_at': signal.get('generated_at', datetime.now()),
            'status': 'active',
            'account_id': account_id
        }
        
        # Handle signal replacement
        if replace_signal_id:
            self._replace_signal(account_id, replace_signal_id, signal_record)
        else:
            self.signal_history[account_id].append(signal_record)
        
        # Register cooling-off period
        self._register_cooldown(symbol, signal.get('pattern_type'))
        
        # Clean up old signals
        self._cleanup_old_signals()
        
        return {
            'registered': True,
            'signal_id': signal_record['signal_id'],
            'account_signals_count': len(self._get_current_week_signals(account_id)),
            'registration_timestamp': datetime.now()
        }
    
    def calculate_signal_quality_score(self, signal: Dict) -> float:
        """
        Calculate comprehensive signal quality score (0-100).
        
        Factors:
        - Pattern confidence (40%)
        - Risk-reward ratio (30%) 
        - Market context suitability (20%)
        - Signal uniqueness (10%)
        """
        try:
            confidence = signal.get('confidence', 0)
            rr_ratio = signal.get('risk_reward_ratio', 0)
            
            # Base score from confidence (0-40 points)
            confidence_score = (confidence / 100) * 40
            
            # Risk-reward score (0-30 points, capped at 5:1 R:R)
            rr_normalized = min(rr_ratio, 5.0) / 5.0
            rr_score = rr_normalized * 30
            
            # Market context score (0-20 points)
            market_context = signal.get('market_context', {})
            context_score = self._score_market_context(market_context)
            
            # Signal uniqueness score (0-10 points)
            uniqueness_score = self._score_signal_uniqueness(signal)
            
            total_score = confidence_score + rr_score + context_score + uniqueness_score
            
            return round(total_score, 2)
            
        except Exception as e:
            logger.error(f"Error calculating signal quality score: {e}")
            return 0.0
    
    def get_account_signal_statistics(self, account_id: str, days: int = 30) -> Dict:
        """Get signal statistics for an account"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        account_signals = [
            s for s in self.signal_history.get(account_id, [])
            if start_date <= self._parse_datetime(s['generated_at']) <= end_date
        ]
        
        if not account_signals:
            return {
                'total_signals': 0,
                'period_days': days,
                'signals_per_week': 0,
                'average_quality_score': 0,
                'pattern_distribution': {},
                'symbol_distribution': {}
            }
        
        # Calculate statistics
        total_signals = len(account_signals)
        signals_per_week = (total_signals / days) * 7
        avg_quality = sum(s.get('quality_score', 0) for s in account_signals) / total_signals
        
        # Pattern distribution
        pattern_counts = defaultdict(int)
        for signal in account_signals:
            pattern_counts[signal.get('pattern_type', 'unknown')] += 1
        
        # Symbol distribution
        symbol_counts = defaultdict(int)
        for signal in account_signals:
            symbol_counts[signal.get('symbol', 'unknown')] += 1
        
        return {
            'total_signals': total_signals,
            'period_days': days,
            'signals_per_week': round(signals_per_week, 2),
            'average_quality_score': round(avg_quality, 2),
            'pattern_distribution': dict(pattern_counts),
            'symbol_distribution': dict(symbol_counts),
            'current_week_count': len(self._get_current_week_signals(account_id)),
            'weekly_limit': self._get_account_weekly_limit(account_id)
        }
    
    def set_account_weekly_limit(self, account_id: str, limit: int) -> bool:
        """Set custom weekly limit for an account"""
        if limit < 1 or limit > 10:  # Reasonable bounds
            return False
        
        self.account_limits[account_id] = limit
        logger.info(f"Set weekly limit for account {account_id} to {limit}")
        return True
    
    def set_account_preferences(self, account_id: str, preferences: Dict) -> bool:
        """Set signal preferences for an account"""
        allowed_preferences = {
            'preferred_patterns': list,
            'min_confidence': (int, float),
            'min_risk_reward': (int, float),
            'max_signals_per_symbol': int,
            'preferred_sessions': list,
            'avoid_high_volatility': bool
        }
        
        validated_preferences = {}
        for key, value in preferences.items():
            if key in allowed_preferences:
                expected_type = allowed_preferences[key]
                if isinstance(expected_type, tuple):
                    if isinstance(value, expected_type):
                        validated_preferences[key] = value
                elif isinstance(value, expected_type):
                    validated_preferences[key] = value
        
        self.account_preferences[account_id].update(validated_preferences)
        logger.info(f"Updated preferences for account {account_id}: {validated_preferences}")
        return True
    
    def _get_current_week_signals(self, account_id: str) -> List[Dict]:
        """Get signals generated in the current week for an account"""
        now = datetime.now()
        
        # Calculate start of current week (Monday)
        days_since_monday = now.weekday()
        week_start = now - timedelta(days=days_since_monday, 
                                   hours=now.hour, 
                                   minutes=now.minute, 
                                   seconds=now.second, 
                                   microseconds=now.microsecond)
        
        return [
            signal for signal in self.signal_history.get(account_id, [])
            if self._parse_datetime(signal['generated_at']) >= week_start and signal['status'] == 'active'
        ]
    
    def _get_account_weekly_limit(self, account_id: str) -> int:
        """Get weekly limit for an account (custom or default)"""
        return self.account_limits.get(account_id, self.default_weekly_limit)
    
    def _parse_datetime(self, dt_value):
        """Parse datetime value that could be datetime object or ISO string"""
        if isinstance(dt_value, datetime):
            return dt_value
        elif isinstance(dt_value, str):
            try:
                # Handle ISO format datetime strings
                if dt_value.endswith('Z'):
                    dt_value = dt_value.replace('Z', '+00:00')
                return datetime.fromisoformat(dt_value.replace('Z', '+00:00'))
            except ValueError:
                # If parsing fails, return current time as fallback
                return datetime.now()
        else:
            # If it's neither datetime nor string, return current time
            return datetime.now()
    
    def _check_cooling_off_period(self, symbol: str, signal: Dict) -> Dict:
        """Check if signal respects cooling-off period"""
        pattern_type = signal.get('pattern_type')
        now = datetime.now()
        cutoff_time = now - timedelta(hours=self.cooling_off_hours)
        
        # Check for recent similar signals
        recent_signals = [
            (timestamp, pattern) for timestamp, pattern in self.signal_cooldowns.get(symbol, [])
            if timestamp > cutoff_time and pattern == pattern_type
        ]
        
        if recent_signals:
            most_recent = max(recent_signals, key=lambda x: x[0])
            next_allowed = most_recent[0] + timedelta(hours=self.cooling_off_hours)
            
            return {
                'allowed': False,
                'reason': 'cooling_off_period',
                'pattern_type': pattern_type,
                'hours_remaining': (next_allowed - now).total_seconds() / 3600,
                'next_allowed_time': next_allowed,
                'last_similar_signal': most_recent[0]
            }
        
        return {'allowed': True}
    
    def _evaluate_signal_substitution(self, 
                                    account_id: str,
                                    new_signal: Dict,
                                    existing_signals: List[Dict]) -> Dict:
        """Evaluate if new signal can replace an existing one"""
        new_quality = self.calculate_signal_quality_score(new_signal)
        
        # Find the lowest quality existing signal
        if not existing_signals:
            return {'substitution_possible': False, 'reason': 'no_existing_signals'}
        
        existing_with_quality = []
        for signal in existing_signals:
            quality = signal.get('quality_score', 0)
            if quality == 0:  # Recalculate if not stored
                quality = self.calculate_signal_quality_score(signal)
            existing_with_quality.append((signal, quality))
        
        # Sort by quality (lowest first)
        existing_with_quality.sort(key=lambda x: x[1])
        lowest_quality_signal, lowest_quality = existing_with_quality[0]
        
        # Check if new signal is significantly better
        quality_improvement = new_quality - lowest_quality
        min_improvement_threshold = 15.0  # Minimum 15 point improvement required
        
        if quality_improvement >= min_improvement_threshold:
            return {
                'substitution_possible': True,
                'signal_to_replace': lowest_quality_signal,
                'quality_improvement': quality_improvement,
                'new_signal_quality': new_quality,
                'replaced_signal_quality': lowest_quality,
                'reason': f'Quality improvement of {quality_improvement:.1f} points'
            }
        
        return {
            'substitution_possible': False,
            'reason': 'insufficient_quality_improvement',
            'quality_difference': quality_improvement,
            'min_required_improvement': min_improvement_threshold
        }
    
    def _replace_signal(self, account_id: str, old_signal_id: str, new_signal_record: Dict):
        """Replace an existing signal with a new one"""
        account_signals = self.signal_history.get(account_id, [])
        
        for i, signal in enumerate(account_signals):
            if signal['signal_id'] == old_signal_id:
                # Mark old signal as replaced
                account_signals[i]['status'] = 'replaced'
                account_signals[i]['replaced_at'] = datetime.now()
                
                # Add new signal
                account_signals.append(new_signal_record)
                
                logger.info(f"Replaced signal {old_signal_id} with {new_signal_record['signal_id']} "
                          f"for account {account_id}")
                break
    
    def _register_cooldown(self, symbol: str, pattern_type: str):
        """Register a cooling-off period for a symbol/pattern combination"""
        now = datetime.now()
        self.signal_cooldowns[symbol].append((now, pattern_type))
        
        # Clean up old cooldowns (keep only recent ones)
        cutoff_time = now - timedelta(hours=self.cooling_off_hours * 2)
        self.signal_cooldowns[symbol] = [
            (timestamp, pattern) for timestamp, pattern in self.signal_cooldowns[symbol]
            if timestamp > cutoff_time
        ]
    
    def _cleanup_old_signals(self):
        """Clean up old signal records to prevent memory bloat"""
        cutoff_date = datetime.now() - timedelta(days=90)  # Keep 90 days of history
        
        for account_id in list(self.signal_history.keys()):
            self.signal_history[account_id] = [
                signal for signal in self.signal_history[account_id]
                if self._parse_datetime(signal['generated_at']) > cutoff_date
            ]
            
            # Remove account if no signals remaining
            if not self.signal_history[account_id]:
                del self.signal_history[account_id]
    
    def _score_market_context(self, market_context: Dict) -> float:
        """Score market context suitability (0-20 points)"""
        if not market_context:
            return 10.0  # Neutral score
        
        score = 10.0  # Base score
        
        # Market state scoring
        market_state = market_context.get('market_state', 'unknown')
        state_scores = {
            'trending': 20,
            'breakout': 18,
            'ranging': 15,
            'weak_trend': 12,
            'transitional': 8,
            'choppy': 3,
            'volatile_trend': 5
        }
        score = state_scores.get(market_state, 10)
        
        # Adjust for volatility
        volatility = market_context.get('volatility_regime', 'normal')
        volatility_adjustments = {
            'low': -2,
            'normal': 0,
            'high': -1,
            'extreme': -5
        }
        score += volatility_adjustments.get(volatility, 0)
        
        # Adjust for session
        session = market_context.get('session', 'unknown')
        session_scores = {
            'london': 2,
            'new_york': 2,
            'overlap': 3,
            'asian': 1,
            'off_hours': -2
        }
        score += session_scores.get(session, 0)
        
        return max(0, min(20, score))
    
    def _score_signal_uniqueness(self, signal: Dict) -> float:
        """Score signal uniqueness to avoid clustering (0-10 points)"""
        # In a full implementation, this would check for:
        # - Similar patterns on same symbol recently
        # - Correlation with other active signals
        # - Pattern diversity in current signal set
        
        # Simplified scoring for now
        pattern_type = signal.get('pattern_type', 'unknown')
        
        # Rare patterns get higher uniqueness scores
        pattern_rarity_scores = {
            'spring': 10,
            'upthrust': 10,
            'sign_of_strength': 8,
            'sign_of_weakness': 8,
            'accumulation': 6,
            'distribution': 6,
            'backup': 4,
            'test': 5
        }
        
        return pattern_rarity_scores.get(pattern_type, 5)
    
    def _find_lowest_quality_signal(self, signals: List[Dict]) -> Dict:
        """Find the signal with lowest quality score"""
        if not signals:
            return {}
        
        lowest_signal = signals[0]
        lowest_quality = lowest_signal.get('quality_score', 0)
        
        for signal in signals[1:]:
            quality = signal.get('quality_score', 0)
            if quality < lowest_quality:
                lowest_quality = quality
                lowest_signal = signal
        
        return {
            'signal_id': lowest_signal.get('signal_id'),
            'quality_score': lowest_quality,
            'pattern_type': lowest_signal.get('pattern_type'),
            'symbol': lowest_signal.get('symbol'),
            'generated_at': lowest_signal.get('generated_at')
        }
    
    def _suggest_signal_improvements(self, signal: Dict) -> List[str]:
        """Suggest improvements to make signal more competitive"""
        suggestions = []
        
        confidence = signal.get('confidence', 0)
        rr_ratio = signal.get('risk_reward_ratio', 0)
        
        if confidence < 80:
            suggestions.append(f"Increase confidence (currently {confidence:.1f}%) - wait for stronger pattern confirmation")
        
        if rr_ratio < 3.0:
            suggestions.append(f"Improve risk-reward ratio (currently {rr_ratio:.1f}:1) - consider better entry/exit levels")
        
        market_context = signal.get('market_context', {})
        if market_context.get('market_state') == 'choppy':
            suggestions.append("Avoid signals in choppy market conditions - wait for clearer market state")
        
        return suggestions
    
    def get_weekly_signal_capacity(self, account_id: str) -> Dict:
        """Get current week's signal capacity information"""
        current_signals = self._get_current_week_signals(account_id)
        weekly_limit = self._get_account_weekly_limit(account_id)
        
        return {
            'weekly_limit': weekly_limit,
            'signals_used': len(current_signals),
            'signals_remaining': max(0, weekly_limit - len(current_signals)),
            'utilization_percentage': (len(current_signals) / weekly_limit) * 100,
            'current_signals': [
                {
                    'signal_id': s['signal_id'],
                    'symbol': s['symbol'],
                    'pattern_type': s['pattern_type'],
                    'quality_score': s.get('quality_score', 0),
                    'generated_at': s['generated_at']
                }
                for s in current_signals
            ]
        }