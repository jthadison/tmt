"""
Deployment data models for auto-deployment system.

Defines dataclasses for deployment results, rollback operations, and
deployment stage tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional


@dataclass
class DeploymentResult:
    """
    Result of a deployment operation.

    Attributes:
        success: Whether deployment was successful
        deployment_id: Unique deployment identifier
        reason: Explanation of deployment result
        pending_approval: Whether manual approval is required
        stages_completed: Number of rollout stages completed (0-4)
        rollback_triggered: Whether automatic rollback was triggered
        deployed_at: Timestamp of deployment start
    """
    success: bool
    deployment_id: Optional[str] = None
    reason: str = ""
    pending_approval: bool = False
    stages_completed: int = 0
    rollback_triggered: bool = False
    deployed_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate deployment result data."""
        if self.stages_completed < 0 or self.stages_completed > 4:
            raise ValueError(f"stages_completed must be 0-4, got {self.stages_completed}")


@dataclass
class RollbackResult:
    """
    Result of a rollback operation.

    Attributes:
        success: Whether rollback was successful
        deployment_id: Deployment ID that was rolled back
        reason: Explanation of why rollback occurred
        reverted_to: Dictionary of previous parameter values
        rolled_back_at: Timestamp of rollback execution
    """
    success: bool
    deployment_id: str
    reason: str
    reverted_to: Dict[str, Decimal]
    rolled_back_at: Optional[datetime] = None


@dataclass
class DeploymentStage:
    """
    Information about a deployment stage.

    Represents one stage of the gradual rollout process (10%, 25%, 50%, or 100%).

    Attributes:
        stage_number: Stage number (1-4)
        allocation_pct: Percentage of signals allocated to this stage
        start_date: When this stage started
        end_date: When this stage completed (None if still running)
        status: Current status (ACTIVE, COMPLETED, ROLLED_BACK)
        baseline_metrics: Performance metrics before deployment
        current_metrics: Performance metrics during this stage
        degradation_pct: Performance degradation percentage (negative = improvement)
    """
    stage_number: int
    allocation_pct: Decimal
    start_date: datetime
    end_date: Optional[datetime] = None
    status: str = "ACTIVE"
    baseline_metrics: Dict[str, Decimal] = field(default_factory=dict)
    current_metrics: Dict[str, Decimal] = field(default_factory=dict)
    degradation_pct: Optional[Decimal] = None

    def __post_init__(self):
        """Validate deployment stage data."""
        if self.stage_number not in [1, 2, 3, 4]:
            raise ValueError(f"stage_number must be 1-4, got {self.stage_number}")

        if self.allocation_pct not in [Decimal('0.10'), Decimal('0.25'), Decimal('0.50'), Decimal('1.00')]:
            raise ValueError(f"allocation_pct must be 0.10, 0.25, 0.50, or 1.00, got {self.allocation_pct}")

        if self.status not in ['ACTIVE', 'COMPLETED', 'ROLLED_BACK']:
            raise ValueError(f"status must be ACTIVE, COMPLETED, or ROLLED_BACK, got {self.status}")
