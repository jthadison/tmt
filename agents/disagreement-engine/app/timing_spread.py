"""
Timing Spread Mechanism - Manages entry timing distribution.
Implements AC3: Entry timing spreads increased during high-signal periods.
"""
import logging
import hashlib
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
import numpy as np

from .models import AccountDecision, OriginalSignal, DisagreementProfile

logger = logging.getLogger(__name__)


class TimingSpreadEngine:
    """
    Manages entry timing distribution to avoid coordinated execution.
    
    During high-signal periods, spreads out entry times to reduce correlation
    and avoid simultaneous execution patterns.
    """
    
    def __init__(self):
        # Configuration
        self.base_timing_spread = 30  # Base spread in seconds
        self.high_signal_threshold = 5  # Signals per hour to trigger high-signal mode
        self.max_timing_spread = 300  # Maximum spread in seconds (5 minutes)
        
        # Signal frequency tracking
        self.recent_signals = []
        self.high_signal_mode = False
        
        logger.info("TimingSpreadEngine initialized")

    def calculate_entry_timings(
        self,
        decisions: List[AccountDecision],
        signal: OriginalSignal,
        personalities: Dict[str, DisagreementProfile]
    ) -> List[AccountDecision]:
        """
        Calculate and assign entry timings for all account decisions.
        
        Args:
            decisions: List of account decisions
            signal: Original signal information
            personalities: Personality profiles for timing preferences
            
        Returns:
            Updated decisions with timing modifications
        """
        logger.debug(f"Calculating entry timings for {len(decisions)} decisions")
        
        # Update signal frequency tracking
        self._update_signal_frequency()
        
        # Determine current timing spread based on signal frequency
        timing_spread = self._determine_timing_spread()
        
        # Get participating accounts (those taking or modifying the signal)
        participating_decisions = [
            d for d in decisions 
            if d.decision.value in ['take', 'modify']
        ]
        
        if not participating_decisions:
            logger.debug("No participating decisions, no timing spread needed")
            return decisions
        
        # Calculate timing distribution
        timings = self._generate_timing_distribution(
            len(participating_decisions),
            timing_spread,
            personalities
        )
        
        # Assign timings to decisions
        for i, decision in enumerate(participating_decisions):
            personality = personalities.get(decision.personality_id)
            
            # Apply personality-based timing preferences
            base_timing = timings[i]
            adjusted_timing = self._apply_personality_timing(base_timing, personality)
            
            # Update decision with timing
            if decision.modifications.timing is None:
                decision.modifications.timing = adjusted_timing
            else:
                # Combine with existing timing
                decision.modifications.timing += adjusted_timing
            
            logger.debug(f"Account {decision.account_id}: timing = {decision.modifications.timing:.1f}s")
        
        logger.info(f"Applied timing spread of {timing_spread}s to {len(participating_decisions)} accounts")
        
        return decisions

    def _update_signal_frequency(self) -> None:
        """Update recent signal frequency tracking."""
        now = datetime.utcnow()
        self.recent_signals.append(now)
        
        # Clean old signals (keep last 2 hours)
        cutoff = now - timedelta(hours=2)
        self.recent_signals = [
            timestamp for timestamp in self.recent_signals
            if timestamp >= cutoff
        ]
        
        # Calculate signals per hour over last hour
        one_hour_ago = now - timedelta(hours=1)
        recent_count = len([
            timestamp for timestamp in self.recent_signals
            if timestamp >= one_hour_ago
        ])
        
        # Update high signal mode
        was_high_signal = self.high_signal_mode
        self.high_signal_mode = recent_count >= self.high_signal_threshold
        
        if self.high_signal_mode != was_high_signal:
            logger.info(f"High signal mode: {self.high_signal_mode} ({recent_count} signals/hour)")

    def _determine_timing_spread(self) -> float:
        """Determine timing spread based on current signal frequency."""
        
        if self.high_signal_mode:
            # Increase spread during high-signal periods
            signals_last_hour = len([
                timestamp for timestamp in self.recent_signals
                if timestamp >= datetime.utcnow() - timedelta(hours=1)
            ])
            
            # Scale spread based on signal frequency
            frequency_multiplier = min(3.0, signals_last_hour / self.high_signal_threshold)
            timing_spread = self.base_timing_spread * frequency_multiplier
            
            logger.debug(f"High signal mode: {signals_last_hour} signals/hour, "
                        f"multiplier={frequency_multiplier:.1f}, spread={timing_spread:.0f}s")
        else:
            # Normal spread
            timing_spread = self.base_timing_spread
            logger.debug(f"Normal timing spread: {timing_spread:.0f}s")
        
        return min(timing_spread, self.max_timing_spread)

    def _generate_timing_distribution(
        self,
        num_accounts: int,
        timing_spread: float,
        personalities: Dict[str, DisagreementProfile]
    ) -> List[float]:
        """Generate timing distribution for accounts."""
        
        if num_accounts <= 1:
            return [0.0]
        
        # Create base timing distribution
        if timing_spread <= 0:
            return [0.0] * num_accounts
        
        # Use different distribution strategies
        distribution_type = self._select_distribution_type()
        
        if distribution_type == "uniform":
            timings = self._uniform_distribution(num_accounts, timing_spread)
        elif distribution_type == "clustered":
            timings = self._clustered_distribution(num_accounts, timing_spread)
        elif distribution_type == "staggered":
            timings = self._staggered_distribution(num_accounts, timing_spread)
        else:  # random
            timings = self._random_distribution(num_accounts, timing_spread)
        
        # Deterministic shuffle based on signal ID
        # Create reproducible ordering based on signal
        signal_hash = hashlib.md5(f"{num_accounts}{distribution_type}{datetime.now().hour}".encode()).hexdigest()
        indices = list(range(len(timings)))
        # Sort indices based on hash to create deterministic shuffle
        indices.sort(key=lambda x: hashlib.md5(f"{signal_hash}{x}".encode()).hexdigest())
        timings = [timings[i] for i in indices]
        
        logger.debug(f"Generated {distribution_type} timing distribution: "
                    f"min={min(timings):.1f}s, max={max(timings):.1f}s, "
                    f"mean={np.mean(timings):.1f}s")
        
        return timings

    def _select_distribution_type(self) -> str:
        """Select timing distribution type based on current conditions."""
        
        # Deterministic distribution selection based on time and mode
        hour_hash = hashlib.md5(f"{datetime.now().hour}{datetime.now().minute // 10}".encode()).hexdigest()
        selector = int(hour_hash[:2], 16) % 100

        if self.high_signal_mode:
            # During high signal periods, prefer more spread out distributions
            if selector < 40:
                return "staggered"
            elif selector < 70:
                return "uniform"
            elif selector < 90:
                return "random"
            else:
                return "clustered"
        else:
            # Normal periods, more natural clustering
            if selector < 40:
                return "clustered"
            elif selector < 70:
                return "random"
            elif selector < 90:
                return "uniform"
            else:
                return "staggered"

    def _uniform_distribution(self, num_accounts: int, spread: float) -> List[float]:
        """Create uniform timing distribution."""
        if num_accounts <= 1:
            return [0.0]
        
        step = spread / (num_accounts - 1)
        return [i * step for i in range(num_accounts)]

    def _clustered_distribution(self, num_accounts: int, spread: float) -> List[float]:
        """Create clustered timing distribution (more natural)."""
        timings = []
        
        # Create 2-3 clusters
        num_clusters = min(3, max(2, num_accounts // 3))
        accounts_per_cluster = num_accounts // num_clusters
        
        # Deterministic cluster centers
        cluster_centers = []
        for i in range(num_clusters):
            center_hash = hashlib.md5(f"cluster{i}{spread}".encode()).hexdigest()
            center_position = (int(center_hash[:8], 16) % 100) / 100.0
            cluster_centers.append(spread * center_position)
        cluster_centers.sort()
        
        for i, center in enumerate(cluster_centers):
            cluster_size = accounts_per_cluster
            if i == len(cluster_centers) - 1:
                cluster_size += num_accounts % num_clusters  # Handle remainder
            
            # Add accounts around cluster center
            for j in range(cluster_size):
                # Deterministic offset around cluster center
                offset_hash = hashlib.md5(f"{i}{j}{center}".encode()).hexdigest()
                offset_factor = ((int(offset_hash[:4], 16) % 200) - 100) / 1000.0  # -0.1 to 0.1
                offset = spread * offset_factor
                timing = max(0, center + offset)
                timings.append(timing)
        
        return timings[:num_accounts]

    def _staggered_distribution(self, num_accounts: int, spread: float) -> List[float]:
        """Create staggered timing distribution with regular intervals."""
        if num_accounts <= 1:
            return [0.0]
        
        base_interval = spread / num_accounts
        timings = []
        
        for i in range(num_accounts):
            # Base timing with small random offset
            base_timing = i * base_interval
            # Deterministic offset
            offset_hash = hashlib.md5(f"uniform{i}{base_timing}".encode()).hexdigest()
            offset_factor = ((int(offset_hash[:4], 16) % 40) - 20) / 100.0  # -0.2 to 0.2
            offset = base_interval * offset_factor
            timing = max(0, base_timing + offset)
            timings.append(timing)
        
        return timings

    def _random_distribution(self, num_accounts: int, spread: float) -> List[float]:
        """Create pseudo-random timing distribution (deterministic)."""
        timings = []
        for i in range(num_accounts):
            timing_hash = hashlib.md5(f"random{i}{spread}".encode()).hexdigest()
            timing_factor = (int(timing_hash[:8], 16) % 10000) / 10000.0
            timings.append(spread * timing_factor)
        return timings

    def _apply_personality_timing(
        self,
        base_timing: float,
        personality: DisagreementProfile
    ) -> float:
        """Apply personality-based timing adjustments."""
        
        if not personality:
            return base_timing
        
        # Get personality factors
        risk_aversion = personality.biases.risk_aversion
        conformity = personality.biases.crowd_following
        
        # Risk-averse traders tend to wait longer
        risk_adjustment = risk_aversion * 10  # Up to 10 seconds
        
        # Non-conformist traders vary timing more (deterministic)
        conformity_hash = hashlib.md5(f"{conformity}{base_timing}".encode()).hexdigest()
        conformity_factor = ((int(conformity_hash[:4], 16) % 200) - 50) / 10.0  # -5 to 15
        conformity_adjustment = (1.0 - conformity) * conformity_factor
        
        # Apply situational modifiers for time of day
        time_modifier = self._get_time_of_day_modifier(personality)
        
        adjusted_timing = base_timing + risk_adjustment + conformity_adjustment + time_modifier
        
        # Ensure timing is non-negative
        adjusted_timing = max(0, adjusted_timing)
        
        logger.debug(f"Timing adjustment: base={base_timing:.1f}s, "
                    f"risk={risk_adjustment:.1f}s, conformity={conformity_adjustment:.1f}s, "
                    f"time={time_modifier:.1f}s, final={adjusted_timing:.1f}s")
        
        return adjusted_timing

    def _get_time_of_day_modifier(self, personality: DisagreementProfile) -> float:
        """Get timing modifier based on time of day preferences."""
        
        current_hour = datetime.utcnow().hour
        
        # Get time-specific modifiers from personality
        time_modifiers = personality.situational_modifiers.time_of_day
        
        if str(current_hour) in time_modifiers:
            return time_modifiers[str(current_hour)] * 5  # Scale to seconds
        
        # Default modifiers for different sessions
        # Deterministic session-based timing adjustments
        session_hash = hashlib.md5(f"session{current_hour}{datetime.now().minute}".encode()).hexdigest()
        session_factor = (int(session_hash[:4], 16) % 100) / 100.0

        if 8 <= current_hour <= 12:  # London session
            return -2 + (4 * session_factor)  # -2 to 2
        elif 13 <= current_hour <= 17:  # NY session
            return -3 + (8 * session_factor)  # -3 to 5
        elif 22 <= current_hour or current_hour <= 6:  # Asian session
            return 8 * session_factor  # 0 to 8
        else:  # Overlap periods
            return -1 + (4 * session_factor)  # -1 to 3

    def get_timing_statistics(self, recent_decisions: List[AccountDecision]) -> Dict[str, float]:
        """Get timing spread statistics for monitoring."""
        
        # Extract timings from recent decisions
        timings = [
            d.modifications.timing for d in recent_decisions
            if d.modifications.timing is not None and d.decision.value in ['take', 'modify']
        ]
        
        if not timings:
            return {"count": 0}
        
        return {
            "count": len(timings),
            "mean_timing": np.mean(timings),
            "max_spread": max(timings) - min(timings),
            "std_timing": np.std(timings),
            "median_timing": np.median(timings),
            "high_signal_mode": self.high_signal_mode,
            "signals_last_hour": len([
                timestamp for timestamp in self.recent_signals
                if timestamp >= datetime.utcnow() - timedelta(hours=1)
            ])
        }

    def reset_signal_tracking(self) -> None:
        """Reset signal frequency tracking (for testing)."""
        self.recent_signals = []
        self.high_signal_mode = False
        logger.info("Reset signal frequency tracking")