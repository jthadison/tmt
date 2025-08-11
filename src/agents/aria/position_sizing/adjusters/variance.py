"""
Anti-Detection Size Variance Engine
==================================

This module implements sophisticated position size variance generation to avoid
detection patterns by prop firms. It creates account-specific trading personalities
and applies controlled randomization within risk limits while monitoring for
detectable patterns.
"""

import logging
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID
import datetime
import hashlib
import random
import statistics

from ..models import VarianceProfile

logger = logging.getLogger(__name__)


class VarianceRecord:
    """Record of a single variance application."""
    
    def __init__(self, account_id: UUID, base_size: Decimal, varied_size: Decimal,
                 variance_factor: Decimal, timestamp: datetime.datetime):
        self.account_id = account_id
        self.base_size = base_size
        self.varied_size = varied_size
        self.variance_factor = variance_factor
        self.timestamp = timestamp
        self.variance_direction = "increase" if varied_size > base_size else "decrease"


class VarianceHistoryTracker:
    """Tracks variance history for pattern detection and avoidance."""
    
    def __init__(self):
        # In-memory storage for demo - production would use database
        self._variance_history: Dict[UUID, List[VarianceRecord]] = {}
    
    async def record_variance(self, account_id: UUID, base_size: Decimal, 
                            varied_size: Decimal, variance_factor: Decimal):
        """Record a variance application."""
        if account_id not in self._variance_history:
            self._variance_history[account_id] = []
        
        record = VarianceRecord(
            account_id=account_id,
            base_size=base_size,
            varied_size=varied_size,
            variance_factor=variance_factor,
            timestamp=datetime.datetime.utcnow()
        )
        
        self._variance_history[account_id].append(record)
        
        # Keep only last 100 records per account for performance
        if len(self._variance_history[account_id]) > 100:
            self._variance_history[account_id] = self._variance_history[account_id][-100:]
    
    async def get_recent_variances(self, account_id: UUID, count: int) -> List[VarianceRecord]:
        """Get the most recent variance records for an account."""
        history = self._variance_history.get(account_id, [])
        return history[-count:] if history else []
    
    async def get_variance_statistics(self, account_id: UUID, days: int = 30) -> Dict[str, float]:
        """Get variance statistics for pattern analysis."""
        cutoff_time = datetime.datetime.utcnow() - datetime.timedelta(days=days)
        history = self._variance_history.get(account_id, [])
        
        recent_records = [r for r in history if r.timestamp >= cutoff_time]
        
        if not recent_records:
            return {'mean': 0.0, 'std_dev': 0.0, 'count': 0}
        
        variance_factors = [float(r.variance_factor) for r in recent_records]
        
        return {
            'mean': statistics.mean(variance_factors),
            'std_dev': statistics.stdev(variance_factors) if len(variance_factors) > 1 else 0.0,
            'count': len(recent_records),
            'min': min(variance_factors),
            'max': max(variance_factors)
        }


class SizeVarianceEngine:
    """
    Generates anti-detection variance in position sizes while maintaining
    risk control and avoiding detectable patterns.
    """
    
    def __init__(self, variance_history: VarianceHistoryTracker):
        self.variance_history = variance_history
        
        # Variance configuration
        self.min_variance_pct = Decimal("5.0")   # 5% minimum variance
        self.max_variance_pct = Decimal("15.0")  # 15% maximum variance
        
        # Pattern detection thresholds
        self.pattern_std_dev_threshold = Decimal("0.02")  # 2% std dev indicates pattern
        self.consecutive_same_direction_limit = 5         # Max consecutive same direction
        
        # Account variance profiles storage
        self._variance_profiles: Dict[UUID, VarianceProfile] = {}
    
    async def apply_variance(self, base_size: Decimal, account_id: UUID) -> Decimal:
        """
        Apply anti-detection variance to position size.
        
        Args:
            base_size: Base position size before variance
            account_id: Account identifier
            
        Returns:
            Position size with variance applied
        """
        try:
            # Get or create variance profile for account
            profile = await self._get_or_create_variance_profile(account_id)
            
            # Check for existing patterns and adjust if needed
            if await self._is_forming_detectable_pattern(account_id):
                logger.info(f"Pattern detected for account {account_id}, applying pattern-breaking variance")
                return await self._apply_pattern_breaking_variance(base_size, account_id, profile)
            
            # Generate normal variance
            variance_factor = await self._generate_variance_factor(profile)
            
            # Apply directional bias based on account personality
            directional_variance = await self._apply_directional_bias(variance_factor, profile)
            
            # Calculate final size
            varied_size = base_size * directional_variance
            
            # Ensure size stays within reasonable bounds
            varied_size = await self._clamp_size_bounds(varied_size, base_size)
            
            # Record the variance for pattern tracking
            actual_variance_factor = varied_size / base_size if base_size > 0 else Decimal("1.0")
            await self.variance_history.record_variance(
                account_id, base_size, varied_size, actual_variance_factor
            )
            
            logger.debug(f"Variance applied for account {account_id}: "
                        f"base={base_size}, varied={varied_size}, "
                        f"factor={directional_variance:.4f}")
            
            return varied_size
            
        except Exception as e:
            logger.error(f"Variance application failed for account {account_id}: {str(e)}")
            # Return base size if variance fails
            return base_size
    
    async def _get_or_create_variance_profile(self, account_id: UUID) -> VarianceProfile:
        """Get existing variance profile or create new one for account."""
        if account_id in self._variance_profiles:
            return self._variance_profiles[account_id]
        
        # Create new profile based on account ID hash for consistency
        account_hash = int(hashlib.md5(str(account_id).encode()).hexdigest()[:8], 16)
        
        # Use hash to determine personality traits
        is_aggressive = (account_hash % 2) == 0  # 50% chance of aggressive profile
        
        profile = VarianceProfile(
            account_id=account_id,
            aggressive=is_aggressive,
            variance_range_min=self.min_variance_pct,
            variance_range_max=self.max_variance_pct,
            seed=account_hash,
            pattern_detected=False,
            last_updated=datetime.datetime.utcnow()
        )
        
        self._variance_profiles[account_id] = profile
        
        logger.info(f"Created variance profile for account {account_id}: "
                   f"aggressive={is_aggressive}, seed={account_hash}")
        
        return profile
    
    async def _generate_variance_factor(self, profile: VarianceProfile) -> Decimal:
        """Generate base variance factor within configured range."""
        # Create deterministic but varied random generator
        current_time = datetime.datetime.utcnow()
        time_seed = int(current_time.timestamp()) // 3600  # Change every hour
        combined_seed = profile.seed + time_seed
        
        rng = random.Random(combined_seed)
        
        # Generate variance between min and max percentage
        variance_range = float(self.max_variance_pct - self.min_variance_pct)
        base_variance = float(self.min_variance_pct)
        
        random_factor = rng.random()  # 0.0 to 1.0
        variance_pct = base_variance + (random_factor * variance_range)
        
        # Convert back to decimal
        return Decimal(str(variance_pct)) / Decimal("100")  # Convert percentage to factor
    
    async def _apply_directional_bias(self, variance_factor: Decimal, profile: VarianceProfile) -> Decimal:
        """Apply directional bias based on account personality."""
        if profile.aggressive:
            # Aggressive accounts tend toward larger positions (upward bias)
            return Decimal("1.0") + variance_factor
        else:
            # Conservative accounts tend toward smaller positions (downward bias)
            return Decimal("1.0") - variance_factor
    
    async def _is_forming_detectable_pattern(self, account_id: UUID) -> bool:
        """Detect if variance is forming a detectable pattern."""
        # Get recent variance history
        recent_variances = await self.variance_history.get_recent_variances(account_id, 20)
        
        if len(recent_variances) < 10:
            return False  # Not enough data
        
        # Check for low standard deviation (too consistent)
        variance_factors = [float(r.variance_factor) for r in recent_variances]
        
        if len(set(variance_factors)) < 3:
            logger.warning(f"Account {account_id} has very low variance diversity")
            return True
        
        # Calculate standard deviation
        std_dev = Decimal(str(statistics.stdev(variance_factors)))
        if std_dev < self.pattern_std_dev_threshold:
            logger.warning(f"Account {account_id} variance std dev {std_dev} below threshold")
            return True
        
        # Check for too many consecutive same directions
        directions = [r.variance_direction for r in recent_variances[-10:]]
        consecutive_count = 1
        max_consecutive = 1
        
        for i in range(1, len(directions)):
            if directions[i] == directions[i-1]:
                consecutive_count += 1
                max_consecutive = max(max_consecutive, consecutive_count)
            else:
                consecutive_count = 1
        
        if max_consecutive >= self.consecutive_same_direction_limit:
            logger.warning(f"Account {account_id} has {max_consecutive} consecutive same direction variances")
            return True
        
        return False
    
    async def _apply_pattern_breaking_variance(self, base_size: Decimal, account_id: UUID, 
                                             profile: VarianceProfile) -> Decimal:
        """Apply variance specifically designed to break detected patterns."""
        recent_variances = await self.variance_history.get_recent_variances(account_id, 10)
        
        if not recent_variances:
            # Fallback to normal variance
            variance_factor = await self._generate_variance_factor(profile)
            return base_size * (Decimal("1.0") + variance_factor)
        
        # Analyze recent pattern
        recent_directions = [r.variance_direction for r in recent_variances[-5:]]
        recent_factors = [r.variance_factor for r in recent_variances[-5:]]
        
        # Break the pattern by doing the opposite of recent trend
        most_common_direction = max(set(recent_directions), key=recent_directions.count)
        
        # Generate variance factor with opposite bias
        base_variance = (self.min_variance_pct + self.max_variance_pct) / Decimal("2")  # Middle value
        variance_factor = base_variance / Decimal("100")
        
        if most_common_direction == "increase":
            # Recent trend was increases, apply decrease
            pattern_breaking_factor = Decimal("1.0") - variance_factor
        else:
            # Recent trend was decreases, apply increase
            pattern_breaking_factor = Decimal("1.0") + variance_factor
        
        # Add some additional randomization to avoid creating new pattern
        time_seed = int(datetime.datetime.utcnow().timestamp()) % 1000
        rng = random.Random(profile.seed + time_seed)
        additional_noise = Decimal(str(rng.uniform(-0.02, 0.02)))  # ±2% additional noise
        
        final_factor = pattern_breaking_factor + additional_noise
        
        # Mark pattern as detected in profile
        profile.pattern_detected = True
        profile.last_updated = datetime.datetime.utcnow()
        
        return base_size * final_factor
    
    async def _clamp_size_bounds(self, varied_size: Decimal, base_size: Decimal) -> Decimal:
        """Ensure varied size stays within reasonable bounds."""
        # Don't allow variance to make size too extreme
        min_allowed = base_size * Decimal("0.5")   # No smaller than 50% of base
        max_allowed = base_size * Decimal("2.0")   # No larger than 200% of base
        
        clamped_size = max(min_allowed, min(varied_size, max_allowed))
        
        if clamped_size != varied_size:
            logger.debug(f"Size clamped: {varied_size} -> {clamped_size}")
        
        return clamped_size
    
    async def get_variance_analysis(self, account_id: UUID) -> Dict[str, any]:
        """Get comprehensive variance analysis for an account."""
        profile = self._variance_profiles.get(account_id)
        if not profile:
            return {'error': 'No variance profile found'}
        
        # Get statistics
        stats = await self.variance_history.get_variance_statistics(account_id, 30)
        
        # Check pattern status
        pattern_detected = await self._is_forming_detectable_pattern(account_id)
        
        # Get recent variance trend
        recent_variances = await self.variance_history.get_recent_variances(account_id, 10)
        recent_directions = [r.variance_direction for r in recent_variances]
        
        direction_counts = {
            'increase': recent_directions.count('increase'),
            'decrease': recent_directions.count('decrease')
        }
        
        return {
            'account_id': str(account_id),
            'profile': {
                'aggressive': profile.aggressive,
                'variance_range': f"{profile.variance_range_min}%-{profile.variance_range_max}%",
                'pattern_detected': profile.pattern_detected,
                'last_updated': profile.last_updated.isoformat()
            },
            'statistics': stats,
            'pattern_analysis': {
                'pattern_detected': pattern_detected,
                'recent_direction_counts': direction_counts,
                'total_records': len(recent_variances)
            }
        }
    
    async def reset_pattern_detection(self, account_id: UUID):
        """Reset pattern detection flag for an account."""
        if account_id in self._variance_profiles:
            self._variance_profiles[account_id].pattern_detected = False
            self._variance_profiles[account_id].last_updated = datetime.datetime.utcnow()
            logger.info(f"Pattern detection reset for account {account_id}")
    
    def configure_variance_range(self, min_pct: Decimal, max_pct: Decimal):
        """Configure global variance range."""
        self.min_variance_pct = min_pct
        self.max_variance_pct = max_pct
        logger.info(f"Variance range configured: {min_pct}%-{max_pct}%")