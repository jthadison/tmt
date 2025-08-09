"""
Tests for Pattern Confidence Scoring System

Tests the multi-factor confidence scoring with detailed validation
of each scoring component and weight adjustment mechanisms.
"""

import pytest
import pandas as pd
import numpy as np
from decimal import Decimal
from datetime import datetime, timedelta

from agents.market_analysis.app.wyckoff.confidence_scorer import (
    PatternConfidenceScorer,
    ConfidenceScore,
    MarketContext
)


class TestPatternConfidenceScorer:
    """Test suite for pattern confidence scoring"""
    
    def setup_method(self):
        self.scorer = PatternConfidenceScorer()
    
    def generate_test_data(self, pattern_type: str = 'accumulation') -> tuple:
        """Generate test data optimized for specific pattern types"""
        np.random.seed(42)
        
        if pattern_type == 'accumulation':
            # Sideways movement with declining volatility
            base_price = 1.1000
            prices = []
            volumes = []
            
            for i in range(30):
                volatility = max(0.0005, 0.002 - (i/30) * 0.0015)
                price_change = np.random.normal(0, volatility)
                price = base_price + price_change * (1 - i/60)  # Decreasing range
                
                # Volume higher on strength
                if price_change > 0:
                    volume = np.random.uniform(1400, 2000)
                else:
                    volume = np.random.uniform(800, 1200)
                
                high = price + abs(np.random.normal(0, volatility/3))
                low = price - abs(np.random.normal(0, volatility/3))
                open_price = prices[-1]['close'] if prices else price
                
                prices.append({
                    'open': open_price,
                    'high': max(open_price, high, price),
                    'low': min(open_price, low, price),
                    'close': price
                })
                volumes.append(volume)
                
        elif pattern_type == 'markup':
            # Strong upward movement with volume confirmation
            base_price = 1.1000
            prices = []
            volumes = []
            
            for i in range(25):
                trend_component = i * 0.0008  # Strong uptrend
                noise = np.random.normal(0, 0.0003)
                price = base_price + trend_component + noise
                
                # Volume expansion on breakouts
                if i > 0 and price > max([p['high'] for p in prices[-min(3, i):]]):
                    volume = np.random.uniform(2000, 2800)  # High volume on breakouts
                else:
                    volume = np.random.uniform(1200, 1600)
                
                high = price + abs(np.random.normal(0, 0.0002))
                low = price - abs(np.random.normal(0, 0.0001))
                open_price = prices[-1]['close'] if prices else price
                
                prices.append({
                    'open': open_price,
                    'high': max(open_price, high, price),
                    'low': min(open_price, low, price),
                    'close': price
                })
                volumes.append(volume)
        
        else:
            # Default: generate neutral data
            prices = []
            volumes = []
            base_price = 1.1000
            
            for i in range(30):
                price = base_price + np.random.normal(0, 0.001)
                volume = np.random.uniform(1000, 1500)
                
                high = price + abs(np.random.normal(0, 0.0005))
                low = price - abs(np.random.normal(0, 0.0005))
                open_price = prices[-1]['close'] if prices else price
                
                prices.append({
                    'open': open_price,
                    'high': max(open_price, high, price),
                    'low': min(open_price, low, price),
                    'close': price
                })
                volumes.append(volume)
        
        price_df = pd.DataFrame(prices)
        volume_series = pd.Series(volumes)
        return price_df, volume_series
    
    def test_overall_confidence_calculation(self):
        """Test overall confidence score calculation"""
        price_data, volume_data = self.generate_test_data('accumulation')
        
        pattern_data = {
            'phase': 'accumulation',
            'criteria': {
                'volume_on_strength': {'score': 85},
                'price_range_contraction': {'score': 78},
                'support_holding': {'score': 82}
            }
        }
        
        result = self.scorer.calculate_pattern_confidence(pattern_data, price_data, volume_data)
        
        # Validate result structure
        assert isinstance(result, ConfidenceScore)
        assert 0 <= result.overall_confidence <= 100
        assert len(result.factor_scores) == 5  # All five factors
        assert sum(result.factor_weights.values()) == Decimal('1.0')  # Weights sum to 1
        
        # Validate factor scores
        for factor_name, score in result.factor_scores.items():
            assert 0 <= score <= 100, f"Factor {factor_name} score {score} out of range"
        
        # Validate confidence level classification
        assert result.confidence_level in ['low', 'medium', 'high', 'very_high']
        
        # Check if confidence level matches score
        if result.overall_confidence >= 80:
            assert result.confidence_level == 'very_high'
        elif result.overall_confidence >= 65:
            assert result.confidence_level == 'high'
        elif result.overall_confidence >= 45:
            assert result.confidence_level == 'medium'
        else:
            assert result.confidence_level == 'low'
    
    def test_volume_confirmation_scoring(self):
        """Test volume confirmation factor scoring"""
        price_data, volume_data = self.generate_test_data('markup')
        
        # Test with strong volume criteria
        pattern_data = {
            'criteria': {
                'volume_on_strength': {'score': 90},
                'breakout_volume': {'score': 85},
                'volume_confirmation': {'score': 88}
            }
        }
        
        score = self.scorer._score_volume_confirmation(pattern_data, volume_data)
        
        assert isinstance(score, Decimal)
        assert 0 <= score <= 100
        assert score >= 80  # Should be high with strong volume criteria
        
        # Test with weak volume criteria
        pattern_data_weak = {
            'criteria': {
                'volume_on_strength': {'score': 30},
                'volume_divergence': {'score': 25}
            }
        }
        
        score_weak = self.scorer._score_volume_confirmation(pattern_data_weak, volume_data)
        assert score_weak < score  # Should be lower
    
    def test_price_structure_scoring(self):
        """Test price structure quality factor scoring"""
        price_data, volume_data = self.generate_test_data('accumulation')
        
        # Test with good structure criteria
        pattern_data = {
            'phase': 'accumulation',
            'criteria': {
                'price_range_contraction': {'score': 85},
                'support_holding': {'score': 80},
                'sideways_movement': {'score': 88}
            }
        }
        
        score = self.scorer._score_price_structure_quality(pattern_data, price_data)
        
        assert isinstance(score, Decimal)
        assert 0 <= score <= 100
        
        # Test fallback when no criteria available
        pattern_data_empty = {'criteria': {}}
        score_fallback = self.scorer._score_price_structure_quality(pattern_data_empty, price_data)
        assert 0 <= score_fallback <= 100
    
    def test_timeframe_alignment_scoring(self):
        """Test timeframe alignment factor scoring"""
        # Test with good alignment
        timeframe_data_good = {
            'alignment_score': 85,
            'conflicts': [],
            'dominant_timeframe': '4h'
        }
        
        score = self.scorer._score_timeframe_alignment(timeframe_data_good)
        assert isinstance(score, Decimal)
        assert score >= 80
        
        # Test with conflicts
        timeframe_data_conflicts = {
            'alignment_score': 60,
            'conflicts': [
                {'severity': 'high'},
                {'severity': 'medium'}
            ],
            'dominant_timeframe': '1h'
        }
        
        score_conflicts = self.scorer._score_timeframe_alignment(timeframe_data_conflicts)
        assert score_conflicts < score  # Should be penalized for conflicts
        
        # Test with no timeframe data
        score_none = self.scorer._score_timeframe_alignment(None)
        assert score_none == Decimal('50')  # Neutral score
    
    def test_historical_performance_scoring(self):
        """Test historical performance factor scoring"""
        # Test known pattern types
        known_patterns = ['accumulation', 'markup', 'distribution', 'markdown', 'spring', 'upthrust']
        
        for pattern_type in known_patterns:
            score = self.scorer._score_historical_performance(pattern_type)
            assert isinstance(score, Decimal)
            assert score > 0
            assert score <= 100
            
            # Check that score reflects performance data
            perf_data = self.scorer.pattern_performance_db.get(pattern_type)
            if perf_data:
                success_rate = perf_data['success_rate']
                # Score should correlate with success rate
                expected_min = success_rate * 80  # 80% weight on success rate
                assert score >= expected_min * 0.8  # Allow some variation
        
        # Test unknown pattern type
        score_unknown = self.scorer._score_historical_performance('unknown_pattern')
        assert score_unknown == Decimal('40')  # Conservative default
    
    def test_market_context_scoring(self):
        """Test market context factor scoring"""
        # Test different pattern-context combinations
        test_cases = [
            ('accumulation', 'ranging_sideways'),
            ('markup', 'trending_up'),
            ('distribution', 'ranging_sideways'), 
            ('markdown', 'trending_down')
        ]
        
        for pattern_type, context_type in test_cases:
            price_data, volume_data = self.generate_test_data(pattern_type)
            
            pattern_data = {'phase': pattern_type}
            
            score = self.scorer._score_market_context(pattern_data, price_data, volume_data)
            
            assert isinstance(score, Decimal)
            assert 0 <= score <= 100
    
    def test_market_context_determination(self):
        """Test market context determination"""
        # Test trending up market
        trending_up_data = pd.DataFrame({
            'close': [1.1000 + i * 0.0005 for i in range(30)]  # Clear uptrend
        })
        trending_up_volume = pd.Series([1000] * 30)
        
        context = self.scorer._determine_market_context(trending_up_data, trending_up_volume)
        assert context in [MarketContext.TRENDING_UP, MarketContext.VOLATILE]
        
        # Test ranging market
        ranging_data = pd.DataFrame({
            'close': [1.1000 + np.random.uniform(-0.0002, 0.0002) for _ in range(30)]
        })
        ranging_volume = pd.Series([1000] * 30)
        
        context = self.scorer._determine_market_context(ranging_data, ranging_volume)
        assert context in [MarketContext.RANGING, MarketContext.LOW_VOLATILITY]
    
    def test_custom_weight_adjustment(self):
        """Test custom weight adjustment functionality"""
        price_data, volume_data = self.generate_test_data('accumulation')
        
        pattern_data = {
            'phase': 'accumulation',
            'criteria': {
                'volume_on_strength': {'score': 80},
                'price_range_contraction': {'score': 75}
            }
        }
        
        # Test with custom weights emphasizing volume
        custom_weights = {
            'volume_confirmation': Decimal('0.50'),  # Increased from 0.30
            'price_structure': Decimal('0.20'),     # Decreased from 0.25
            'timeframe_alignment': Decimal('0.15'),  # Decreased from 0.20
            'historical_performance': Decimal('0.10'), # Decreased from 0.15
            'market_context': Decimal('0.05')       # Decreased from 0.10
        }
        
        result_custom = self.scorer.calculate_pattern_confidence(
            pattern_data, price_data, volume_data, custom_weights=custom_weights
        )
        
        # Test with default weights
        result_default = self.scorer.calculate_pattern_confidence(
            pattern_data, price_data, volume_data
        )
        
        # Custom weights should be applied
        assert result_custom.factor_weights == custom_weights
        assert result_default.factor_weights == self.scorer.default_weights
        
        # Results should be different due to different weights
        assert result_custom.overall_confidence != result_default.overall_confidence
    
    def test_weight_adjustment_for_market_conditions(self):
        """Test dynamic weight adjustment based on market conditions"""
        # Test trending market conditions
        trending_conditions = {
            'trend_strength': 0.8,
            'volatility': 0.02
        }
        
        adjusted_weights = self.scorer.adjust_weights_for_conditions(trending_conditions)
        
        # Volume weight should be increased in trending markets
        assert adjusted_weights['volume_confirmation'] > self.scorer.default_weights['volume_confirmation']
        
        # Weights should still sum to 1.0
        assert abs(sum(adjusted_weights.values()) - Decimal('1.0')) < Decimal('0.001')
        
        # Test ranging market conditions
        ranging_conditions = {
            'trend_strength': 0.2,
            'volatility': 0.01
        }
        
        adjusted_weights_ranging = self.scorer.adjust_weights_for_conditions(ranging_conditions)
        
        # Structure weight should be increased in ranging markets
        assert adjusted_weights_ranging['price_structure'] > self.scorer.default_weights['price_structure']
    
    def test_confidence_level_classification(self):
        """Test confidence level classification accuracy"""
        test_scores = [
            (95, 'very_high'),
            (85, 'very_high'),
            (80, 'very_high'),
            (75, 'high'),
            (65, 'high'),
            (55, 'medium'),
            (45, 'medium'),
            (35, 'low'),
            (15, 'low')
        ]
        
        for score, expected_level in test_scores:
            classified_level = self.scorer._classify_confidence_level(Decimal(str(score)))
            assert classified_level == expected_level, f"Score {score} should be {expected_level}, got {classified_level}"
    
    def test_risk_assessment(self):
        """Test risk assessment generation"""
        factor_scores = {
            'volume_confirmation': Decimal('85'),
            'price_structure': Decimal('80'),
            'timeframe_alignment': Decimal('75'),
            'historical_performance': Decimal('70'),
            'market_context': Decimal('60')
        }
        
        # Test high confidence scenario
        high_confidence = Decimal('80')
        risk = self.scorer._assess_risk(high_confidence, factor_scores, 'accumulation')
        assert risk in ['low', 'medium', 'high']
        
        # Test low confidence scenario
        low_confidence = Decimal('30')
        risk_low = self.scorer._assess_risk(low_confidence, factor_scores, 'accumulation')
        assert risk_low == 'high'
        
        # Test weak factor scores
        weak_factors = factor_scores.copy()
        weak_factors['volume_confirmation'] = Decimal('25')
        weak_factors['price_structure'] = Decimal('20')
        
        risk_weak = self.scorer._assess_risk(Decimal('70'), weak_factors, 'accumulation')
        assert risk_weak == 'high'  # Should override high confidence
    
    def test_recommendation_generation(self):
        """Test trading recommendation generation"""
        factor_scores = {
            'volume_confirmation': Decimal('85'),
            'price_structure': Decimal('80'),
            'timeframe_alignment': Decimal('75'),
            'historical_performance': Decimal('70'),
            'market_context': Decimal('65')
        }
        
        # Test strong signals
        strong_patterns = ['accumulation', 'spring', 'distribution', 'upthrust']
        for pattern in strong_patterns:
            recommendation = self.scorer._generate_recommendation(
                Decimal('80'), factor_scores, pattern
            )
            assert isinstance(recommendation, str)
            if pattern in ['accumulation', 'spring']:
                assert 'BUY' in recommendation or 'LONG' in recommendation
            elif pattern in ['distribution', 'upthrust']:
                assert 'SELL' in recommendation or 'SHORT' in recommendation
        
        # Test weak signals
        weak_recommendation = self.scorer._generate_recommendation(
            Decimal('30'), factor_scores, 'accumulation'
        )
        assert 'NO ACTION' in weak_recommendation or 'MONITOR' in weak_recommendation
    
    def test_edge_cases(self):
        """Test edge cases and error handling"""
        # Empty pattern data
        empty_pattern = {'criteria': {}}
        price_data, volume_data = self.generate_test_data()
        
        result = self.scorer.calculate_pattern_confidence(empty_pattern, price_data, volume_data)
        assert isinstance(result, ConfidenceScore)
        assert result.overall_confidence >= 0
        
        # Minimal data
        minimal_price = pd.DataFrame({
            'open': [1.1000],
            'high': [1.1005],
            'low': [1.0995],
            'close': [1.1002]
        })
        minimal_volume = pd.Series([1000])
        
        result_minimal = self.scorer.calculate_pattern_confidence(
            {'phase': 'test'}, minimal_price, minimal_volume
        )
        assert isinstance(result_minimal, ConfidenceScore)
        
        # Invalid weights (should be normalized)
        invalid_weights = {
            'volume_confirmation': Decimal('0.5'),
            'price_structure': Decimal('0.3'),
            'timeframe_alignment': Decimal('0.3'),  # Total > 1.0
            'historical_performance': Decimal('0.2'),
            'market_context': Decimal('0.1')
        }
        
        adjusted_weights = self.scorer.adjust_weights_for_conditions({})
        # Should handle weight normalization in the actual implementation
        total_weight = sum(adjusted_weights.values())
        assert abs(total_weight - Decimal('1.0')) < Decimal('0.01')
    
    def test_performance_data_integration(self):
        """Test integration with performance database"""
        # Verify all default pattern types have performance data
        for pattern_type in ['accumulation', 'markup', 'distribution', 'markdown', 'spring', 'upthrust']:
            assert pattern_type in self.scorer.pattern_performance_db
            
            perf_data = self.scorer.pattern_performance_db[pattern_type]
            assert 'success_rate' in perf_data
            assert 'avg_profit' in perf_data
            assert 0 <= perf_data['success_rate'] <= 1
            assert isinstance(perf_data['avg_profit'], (int, float))
        
        # Test score correlation with performance
        high_performance = self.scorer._score_historical_performance('spring')  # Should be high
        low_performance = self.scorer._score_historical_performance('unknown')  # Conservative
        
        assert high_performance > low_performance


if __name__ == "__main__":
    pytest.main([__file__, "-v"])