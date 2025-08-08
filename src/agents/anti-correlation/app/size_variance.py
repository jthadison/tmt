"""Position size variance system for anti-correlation."""

import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
from enum import Enum
import math

from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc

from .models import (
    SizeVarianceRequest, SizeVarianceResponse, AccountCorrelationProfile,
    PositionData
)

logger = logging.getLogger(__name__)


class SizeVarianceStrategy(str, Enum):
    """Size variance strategies."""
    PERCENTAGE_BASED = "percentage_based"
    RISK_ADJUSTED = "risk_adjusted"
    ACCOUNT_PERSONALITY = "account_personality"
    CORRELATION_ADAPTIVE = "correlation_adaptive"
    MARKET_CONDITIONS = "market_conditions"


class RiskLevel(str, Enum):
    """Risk levels for size variance."""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class SizeVarianceManager:
    """Manages position size variance to prevent correlation detection."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.default_variance_range = (0.05, 0.15)  # 5-15% variance
        self.personality_variance_profiles = {
            "conservative": {"min": 0.05, "max": 0.10, "bias": -0.02},
            "moderate": {"min": 0.05, "max": 0.15, "bias": 0.0},
            "aggressive": {"min": 0.08, "max": 0.20, "bias": 0.03},
            "systematic": {"min": 0.04, "max": 0.12, "bias": -0.01},
            "opportunistic": {"min": 0.06, "max": 0.18, "bias": 0.02}
        }
        self.size_history = {}  # Track size adjustments per account
        self.risk_limits = {}  # Risk limits per account
    
    async def calculate_size_variance(
        self,
        request: SizeVarianceRequest
    ) -> SizeVarianceResponse:
        """Calculate appropriate size variance for a position."""
        account_id = request.account_id
        base_size = request.base_size
        symbol = request.symbol
        variance_range = request.variance_range
        
        # Get account profile for personality-based variance
        profile = await self._get_account_profile(account_id)
        
        # Determine variance strategy
        strategy = self._select_variance_strategy(account_id, symbol, profile)
        
        # Calculate variance based on strategy
        variance_factor = await self._calculate_variance_factor(
            account_id, symbol, base_size, variance_range, strategy, profile
        )
        
        # Apply variance to base size
        adjusted_size = await self._apply_size_variance(
            account_id, base_size, variance_factor, symbol
        )
        
        # Ensure compliance with risk limits
        adjusted_size = await self._enforce_risk_limits(
            account_id, symbol, adjusted_size, base_size
        )
        
        # Record size variance
        await self._record_size_variance(
            account_id, symbol, base_size, adjusted_size, variance_factor, strategy
        )
        
        response = SizeVarianceResponse(
            account_id=account_id,
            original_size=base_size,
            adjusted_size=adjusted_size,
            variance_applied=adjusted_size - base_size,
            variance_percentage=(adjusted_size - base_size) / base_size * 100,
            personality_factor=profile.personality_type
        )
        
        logger.info(
            f"Size variance for {account_id}: {base_size:.3f} -> {adjusted_size:.3f} "
            f"({response.variance_percentage:.1f}%) strategy={strategy.value}"
        )
        
        return response
    
    async def bulk_calculate_variances(
        self,
        requests: List[SizeVarianceRequest],
        ensure_diversity: bool = True
    ) -> List[SizeVarianceResponse]:
        """Calculate size variances for multiple accounts with diversity enforcement."""
        responses = []
        
        # Calculate individual variances
        for request in requests:
            response = await self.calculate_size_variance(request)
            responses.append(response)
        
        # Ensure diversity across accounts if requested
        if ensure_diversity and len(responses) > 1:
            responses = await self._ensure_size_diversity(responses)
        
        return responses
    
    async def get_variance_statistics(
        self,
        account_id: Optional[UUID] = None,
        symbol: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get size variance statistics for analysis."""
        # This would query database for historical variance data
        # For now, simulate statistics
        
        stats = {
            "period_days": days,
            "total_variances": random.randint(50, 200),
            "average_variance_percentage": random.uniform(8, 12),
            "min_variance_percentage": random.uniform(5, 7),
            "max_variance_percentage": random.uniform(15, 18),
            "variance_distribution": {
                "0-5%": random.randint(5, 15),
                "5-10%": random.randint(25, 40),
                "10-15%": random.randint(30, 50),
                "15-20%": random.randint(10, 25),
                ">20%": random.randint(0, 5)
            },
            "effectiveness_metrics": await self._calculate_variance_effectiveness(account_id)
        }
        
        return stats
    
    async def optimize_variance_profiles(
        self,
        account_ids: List[UUID]
    ) -> Dict[str, Any]:
        """Optimize variance profiles based on performance and correlation data."""
        optimization_results = {}
        
        for account_id in account_ids:
            # Analyze current performance
            performance = await self._analyze_variance_performance(account_id)
            
            # Get current profile
            profile = await self._get_account_profile(account_id)
            
            # Optimize variance parameters
            optimized_params = await self._optimize_variance_parameters(
                account_id, profile, performance
            )
            
            # Update profile
            await self._update_variance_profile(account_id, optimized_params)
            
            optimization_results[str(account_id)] = {
                "current_performance": performance,
                "optimized_parameters": optimized_params,
                "expected_improvement": random.uniform(0.05, 0.15)
            }
        
        return optimization_results
    
    async def detect_size_patterns(
        self,
        account_ids: List[UUID],
        days: int = 30
    ) -> Dict[str, Any]:
        """Detect potentially suspicious size patterns across accounts."""
        pattern_analysis = {
            "account_count": len(account_ids),
            "analysis_period": days,
            "pattern_risks": {},
            "overall_risk_score": 0.0,
            "recommendations": []
        }
        
        for account_id in account_ids:
            account_risks = await self._analyze_account_size_patterns(account_id, days)
            pattern_analysis["pattern_risks"][str(account_id)] = account_risks
        
        # Calculate cross-account correlation in size patterns
        cross_correlation = await self._analyze_cross_account_size_correlation(account_ids)
        pattern_analysis["cross_account_correlation"] = cross_correlation
        
        # Calculate overall risk score
        individual_risks = [
            risks["risk_score"] for risks in pattern_analysis["pattern_risks"].values()
        ]
        pattern_analysis["overall_risk_score"] = (
            sum(individual_risks) / len(individual_risks) * 0.7 +
            cross_correlation["risk_score"] * 0.3
        )
        
        # Generate recommendations
        pattern_analysis["recommendations"] = self._generate_pattern_recommendations(
            pattern_analysis["overall_risk_score"], cross_correlation
        )
        
        return pattern_analysis
    
    def _select_variance_strategy(
        self,
        account_id: UUID,
        symbol: str,
        profile: AccountCorrelationProfile
    ) -> SizeVarianceStrategy:
        """Select appropriate variance strategy."""
        # Strategy selection based on account characteristics and market conditions
        
        # If account has high correlation history, use adaptive strategy
        if profile.correlation_history and max(profile.correlation_history) > 0.7:
            return SizeVarianceStrategy.CORRELATION_ADAPTIVE
        
        # For systematic personalities, use risk-adjusted approach
        if profile.personality_type == "systematic":
            return SizeVarianceStrategy.RISK_ADJUSTED
        
        # During high volatility, use market conditions strategy
        current_hour = datetime.utcnow().hour
        if 13 <= current_hour <= 17:  # London-NY overlap (high volatility)
            return SizeVarianceStrategy.MARKET_CONDITIONS
        
        # Default to personality-based
        return SizeVarianceStrategy.ACCOUNT_PERSONALITY
    
    async def _calculate_variance_factor(
        self,
        account_id: UUID,
        symbol: str,
        base_size: float,
        variance_range: Tuple[float, float],
        strategy: SizeVarianceStrategy,
        profile: AccountCorrelationProfile
    ) -> float:
        """Calculate variance factor based on selected strategy."""
        
        if strategy == SizeVarianceStrategy.PERCENTAGE_BASED:
            return self._percentage_based_variance(variance_range)
        
        elif strategy == SizeVarianceStrategy.RISK_ADJUSTED:
            return await self._risk_adjusted_variance(
                account_id, symbol, base_size, variance_range
            )
        
        elif strategy == SizeVarianceStrategy.ACCOUNT_PERSONALITY:
            return self._personality_based_variance(profile, variance_range)
        
        elif strategy == SizeVarianceStrategy.CORRELATION_ADAPTIVE:
            return await self._correlation_adaptive_variance(
                account_id, variance_range, profile
            )
        
        elif strategy == SizeVarianceStrategy.MARKET_CONDITIONS:
            return await self._market_conditions_variance(
                symbol, variance_range
            )
        
        else:
            return self._percentage_based_variance(variance_range)
    
    def _percentage_based_variance(
        self,
        variance_range: Tuple[float, float]
    ) -> float:
        """Simple percentage-based variance."""
        min_var, max_var = variance_range
        variance_factor = random.uniform(min_var, max_var)
        
        # Random direction (increase or decrease)
        direction = random.choice([-1, 1])
        return 1.0 + (variance_factor * direction)
    
    async def _risk_adjusted_variance(
        self,
        account_id: UUID,
        symbol: str,
        base_size: float,
        variance_range: Tuple[float, float]
    ) -> float:
        """Risk-adjusted variance based on account risk metrics."""
        # Get account risk profile
        risk_profile = await self._get_account_risk_profile(account_id)
        
        # Adjust variance based on current risk exposure
        risk_adjustment = 1.0
        if risk_profile["current_exposure"] > risk_profile["max_exposure"] * 0.8:
            # High exposure - reduce variance to avoid further risk
            risk_adjustment = 0.7
        elif risk_profile["current_exposure"] < risk_profile["max_exposure"] * 0.3:
            # Low exposure - can afford higher variance
            risk_adjustment = 1.2
        
        min_var, max_var = variance_range
        base_variance = random.uniform(min_var, max_var)
        adjusted_variance = base_variance * risk_adjustment
        
        # Bias towards size reduction if over-exposed
        if risk_profile["current_exposure"] > risk_profile["max_exposure"] * 0.7:
            direction = -1  # Reduce size
        else:
            direction = random.choice([-1, 1])
        
        return 1.0 + (adjusted_variance * direction)
    
    def _personality_based_variance(
        self,
        profile: AccountCorrelationProfile,
        variance_range: Tuple[float, float]
    ) -> float:
        """Personality-based variance calculation."""
        personality_config = self.personality_variance_profiles.get(
            profile.personality_type, 
            self.personality_variance_profiles["moderate"]
        )
        
        # Use personality-specific range
        variance = random.uniform(personality_config["min"], personality_config["max"])
        
        # Apply personality bias
        bias = personality_config["bias"]
        direction = 1 if random.random() > 0.5 - bias else -1
        
        return 1.0 + (variance * direction)
    
    async def _correlation_adaptive_variance(
        self,
        account_id: UUID,
        variance_range: Tuple[float, float],
        profile: AccountCorrelationProfile
    ) -> float:
        """Correlation-adaptive variance to reduce detected patterns."""
        # Get recent correlation levels (would integrate with CorrelationMonitor)
        recent_correlation = await self._get_recent_correlation(account_id)
        
        min_var, max_var = variance_range
        
        # Higher correlation -> higher variance to break patterns
        if recent_correlation > 0.7:
            variance = random.uniform(max_var * 0.8, max_var * 1.2)
        elif recent_correlation > 0.5:
            variance = random.uniform(min_var * 1.2, max_var)
        else:
            variance = random.uniform(min_var, max_var * 0.8)
        
        # Random direction with slight bias based on recent patterns
        recent_bias = await self._get_recent_size_bias(account_id)
        direction_prob = 0.5 - recent_bias  # Counteract recent bias
        direction = 1 if random.random() > direction_prob else -1
        
        return 1.0 + (variance * direction)
    
    async def _market_conditions_variance(
        self,
        symbol: str,
        variance_range: Tuple[float, float]
    ) -> float:
        """Market conditions-based variance."""
        # Get market conditions (simulated)
        market_volatility = random.uniform(0.3, 1.2)
        market_trend = random.uniform(-1, 1)
        
        min_var, max_var = variance_range
        
        # Higher volatility -> higher variance allowed
        volatility_adjustment = min(1.5, 0.8 + market_volatility * 0.4)
        adjusted_max_var = max_var * volatility_adjustment
        
        variance = random.uniform(min_var, adjusted_max_var)
        
        # Slight bias based on market trend
        trend_bias = market_trend * 0.1
        direction_prob = 0.5 + trend_bias
        direction = 1 if random.random() < direction_prob else -1
        
        return 1.0 + (variance * direction)
    
    async def _apply_size_variance(
        self,
        account_id: UUID,
        base_size: float,
        variance_factor: float,
        symbol: str
    ) -> float:
        """Apply variance factor to base size with additional considerations."""
        adjusted_size = base_size * variance_factor
        
        # Ensure minimum position size
        min_size = 0.01  # Minimum lot size
        adjusted_size = max(min_size, abs(adjusted_size))
        
        # Preserve original direction
        if base_size < 0:
            adjusted_size = -adjusted_size
        
        # Apply anti-pattern variance to avoid creating detectable patterns
        adjusted_size = await self._apply_anti_pattern_size_variance(
            account_id, symbol, adjusted_size, base_size
        )
        
        return adjusted_size
    
    async def _apply_anti_pattern_size_variance(
        self,
        account_id: UUID,
        symbol: str,
        calculated_size: float,
        base_size: float
    ) -> float:
        """Apply additional variance to avoid creating detectable patterns."""
        # Get recent size adjustments for this account/symbol
        recent_adjustments = await self._get_recent_size_adjustments(
            account_id, symbol, hours=24
        )
        
        if len(recent_adjustments) < 2:
            return calculated_size
        
        # Analyze recent pattern
        recent_factors = [adj["variance_factor"] for adj in recent_adjustments]
        avg_factor = sum(recent_factors) / len(recent_factors)
        
        current_factor = calculated_size / base_size
        
        # If current factor is too similar to recent average, add variance
        if abs(current_factor - avg_factor) < 0.05:
            additional_variance = random.uniform(-0.03, 0.03)
            calculated_size *= (1 + additional_variance)
        
        # Check for regular spacing patterns
        if len(recent_adjustments) >= 3:
            spacings = []
            for i in range(1, len(recent_adjustments)):
                spacing = recent_adjustments[i]["adjusted_size"] - recent_adjustments[i-1]["adjusted_size"]
                spacings.append(spacing)
            
            # If spacings are too regular, randomize
            if len(spacings) > 1:
                spacing_variance = sum((s - sum(spacings)/len(spacings))**2 for s in spacings) / len(spacings)
                if spacing_variance < 0.01:  # Very regular
                    calculated_size += random.uniform(-0.05, 0.05) * abs(calculated_size)
        
        return calculated_size
    
    async def _enforce_risk_limits(
        self,
        account_id: UUID,
        symbol: str,
        adjusted_size: float,
        base_size: float
    ) -> float:
        """Enforce risk limits on adjusted position size."""
        risk_limits = await self._get_risk_limits(account_id)
        
        # Check maximum position size
        max_position = risk_limits.get("max_position_size", 10.0)
        if abs(adjusted_size) > max_position:
            # Scale down while maintaining variance direction
            scaling_factor = max_position / abs(adjusted_size)
            adjusted_size *= scaling_factor
        
        # Check maximum variance from base
        max_variance_factor = risk_limits.get("max_variance_factor", 1.5)
        variance_factor = abs(adjusted_size) / abs(base_size)
        if variance_factor > max_variance_factor:
            scaling_factor = max_variance_factor / variance_factor
            adjusted_size = base_size + (adjusted_size - base_size) * scaling_factor
        
        # Ensure minimum meaningful variance
        min_variance = risk_limits.get("min_variance_absolute", 0.01)
        if abs(adjusted_size - base_size) < min_variance:
            direction = 1 if adjusted_size > base_size else -1
            adjusted_size = base_size + (min_variance * direction)
        
        return adjusted_size
    
    async def _ensure_size_diversity(
        self,
        responses: List[SizeVarianceResponse]
    ) -> List[SizeVarianceResponse]:
        """Ensure diversity in size adjustments across multiple accounts."""
        if len(responses) < 2:
            return responses
        
        # Calculate variance percentages
        variance_percentages = [r.variance_percentage for r in responses]
        
        # If variances are too similar, add additional diversity
        avg_variance = sum(variance_percentages) / len(variance_percentages)
        similarity_threshold = 2.0  # 2% threshold
        
        for i, response in enumerate(responses):
            if abs(response.variance_percentage - avg_variance) < similarity_threshold:
                # Add additional variance to create diversity
                additional_variance = random.uniform(-3.0, 3.0)
                new_variance_pct = response.variance_percentage + additional_variance
                
                # Recalculate adjusted size
                variance_factor = 1.0 + (new_variance_pct / 100.0)
                new_adjusted_size = response.original_size * variance_factor
                
                responses[i] = SizeVarianceResponse(
                    account_id=response.account_id,
                    original_size=response.original_size,
                    adjusted_size=new_adjusted_size,
                    variance_applied=new_adjusted_size - response.original_size,
                    variance_percentage=new_variance_pct,
                    personality_factor=response.personality_factor
                )
        
        return responses
    
    async def _get_account_profile(self, account_id: UUID) -> AccountCorrelationProfile:
        """Get account correlation profile."""
        # This would load from database in production
        return AccountCorrelationProfile(
            account_id=account_id,
            personality_type=random.choice(["conservative", "moderate", "aggressive", "systematic"]),
            risk_tolerance=random.uniform(0.3, 0.8),
            typical_delay_range=(5.0, 25.0),
            size_variance_preference=random.uniform(0.05, 0.15),
            correlation_history=[random.uniform(0.2, 0.6) for _ in range(5)],
            adjustment_frequency=random.randint(2, 8)
        )
    
    async def _get_account_risk_profile(self, account_id: UUID) -> Dict[str, float]:
        """Get account risk profile."""
        return {
            "current_exposure": random.uniform(0.3, 0.8),
            "max_exposure": 1.0,
            "risk_tolerance": random.uniform(0.3, 0.7),
            "daily_var": random.uniform(0.02, 0.08)
        }
    
    async def _get_risk_limits(self, account_id: UUID) -> Dict[str, float]:
        """Get risk limits for account."""
        return {
            "max_position_size": 5.0,
            "max_variance_factor": 1.3,
            "min_variance_absolute": 0.01
        }
    
    async def _get_recent_correlation(self, account_id: UUID) -> float:
        """Get recent correlation level for account."""
        # Would integrate with CorrelationMonitor
        return random.uniform(0.2, 0.8)
    
    async def _get_recent_size_bias(self, account_id: UUID) -> float:
        """Get recent bias in size adjustments."""
        # Analyze recent size adjustments for bias
        return random.uniform(-0.1, 0.1)
    
    async def _get_recent_size_adjustments(
        self,
        account_id: UUID,
        symbol: str,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get recent size adjustments for pattern analysis."""
        # Would query database for historical adjustments
        # Return simulated data
        return [
            {
                "adjusted_size": random.uniform(0.5, 2.0),
                "variance_factor": random.uniform(0.9, 1.1),
                "timestamp": datetime.utcnow() - timedelta(hours=random.uniform(1, hours))
            }
            for _ in range(random.randint(2, 8))
        ]
    
    async def _record_size_variance(
        self,
        account_id: UUID,
        symbol: str,
        original_size: float,
        adjusted_size: float,
        variance_factor: float,
        strategy: SizeVarianceStrategy
    ):
        """Record size variance in history."""
        if str(account_id) not in self.size_history:
            self.size_history[str(account_id)] = []
        
        self.size_history[str(account_id)].append({
            "symbol": symbol,
            "original_size": original_size,
            "adjusted_size": adjusted_size,
            "variance_factor": variance_factor,
            "strategy": strategy.value,
            "timestamp": datetime.utcnow()
        })
        
        # Keep only recent history
        cutoff_time = datetime.utcnow() - timedelta(days=30)
        self.size_history[str(account_id)] = [
            h for h in self.size_history[str(account_id)]
            if h["timestamp"] > cutoff_time
        ]
    
    async def _calculate_variance_effectiveness(
        self,
        account_id: Optional[UUID]
    ) -> Dict[str, Any]:
        """Calculate effectiveness metrics for variance system."""
        return {
            "correlation_reduction": random.uniform(0.1, 0.3),
            "pattern_disruption_score": random.uniform(0.6, 0.9),
            "trade_quality_impact": random.uniform(-0.02, 0.01),
            "detection_risk_reduction": random.uniform(0.2, 0.5)
        }
    
    async def _analyze_variance_performance(self, account_id: UUID) -> Dict[str, Any]:
        """Analyze variance performance for an account."""
        return {
            "variance_consistency": random.uniform(0.7, 0.9),
            "correlation_impact": random.uniform(0.1, 0.4),
            "profitability_impact": random.uniform(-0.03, 0.02),
            "pattern_detection_risk": random.uniform(0.1, 0.4)
        }
    
    async def _optimize_variance_parameters(
        self,
        account_id: UUID,
        profile: AccountCorrelationProfile,
        performance: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Optimize variance parameters based on performance."""
        current_range = (profile.size_variance_preference * 0.5, profile.size_variance_preference * 2)
        
        # Adjust based on performance
        if performance["correlation_impact"] > 0.3:
            # Good correlation reduction - maintain or increase variance
            new_range = (current_range[0], current_range[1] * 1.1)
        else:
            # Poor correlation reduction - increase variance range
            new_range = (current_range[0] * 0.9, current_range[1] * 1.2)
        
        return {
            "variance_range": new_range,
            "strategy_preference": random.choice(list(SizeVarianceStrategy)),
            "risk_adjustment": random.uniform(0.9, 1.1)
        }
    
    async def _update_variance_profile(
        self,
        account_id: UUID,
        optimized_params: Dict[str, Any]
    ):
        """Update variance profile with optimized parameters."""
        # Would update database in production
        logger.info(f"Updated variance profile for {account_id}: {optimized_params}")
    
    async def _analyze_account_size_patterns(
        self,
        account_id: UUID,
        days: int
    ) -> Dict[str, Any]:
        """Analyze size patterns for a single account."""
        # Would analyze actual size history from database
        return {
            "pattern_regularity": random.uniform(0.1, 0.6),
            "size_clustering": random.uniform(0.2, 0.5),
            "temporal_patterns": random.uniform(0.1, 0.4),
            "risk_score": random.uniform(0.2, 0.7),
            "recommendations": ["Increase variance range", "Adjust timing patterns"]
        }
    
    async def _analyze_cross_account_size_correlation(
        self,
        account_ids: List[UUID]
    ) -> Dict[str, Any]:
        """Analyze size correlation across multiple accounts."""
        return {
            "average_correlation": random.uniform(0.2, 0.5),
            "max_correlation": random.uniform(0.4, 0.7),
            "synchronized_adjustments": random.randint(0, 5),
            "risk_score": random.uniform(0.1, 0.6)
        }
    
    def _generate_pattern_recommendations(
        self,
        overall_risk_score: float,
        cross_correlation: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on pattern analysis."""
        recommendations = []
        
        if overall_risk_score > 0.7:
            recommendations.append("High risk detected - increase variance ranges significantly")
        elif overall_risk_score > 0.5:
            recommendations.append("Moderate risk - adjust variance strategies")
        
        if cross_correlation["risk_score"] > 0.6:
            recommendations.append("High cross-account correlation - implement forced diversity")
        
        if cross_correlation["synchronized_adjustments"] > 3:
            recommendations.append("Too many synchronized adjustments - add temporal separation")
        
        if not recommendations:
            recommendations.append("Size variance patterns within acceptable ranges")
        
        return recommendations