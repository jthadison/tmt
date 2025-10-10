"""
Auto-Deployment Manager for Trading Parameters.

Manages safe deployment of validated parameter improvements through gradual
rollout stages with automatic rollback capabilities. Implements multi-layer
validation and monitoring for production parameter changes.
"""

import logging
import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, Optional, Tuple, Any
import httpx

from .models.deployment_models import DeploymentResult, RollbackResult, DeploymentStage
from .models.suggestion_models import ParameterSuggestion


logger = logging.getLogger(__name__)


class AutoDeploymentManager:
    """
    Manages automated deployment of trading parameter improvements.

    Implements gradual rollout with validation at each stage:
    - 10% allocation for 2 days
    - 25% allocation for 2 days
    - 50% allocation for 2 days
    - 100% allocation (full deployment)

    Includes automatic rollback if performance degrades beyond threshold.
    """

    def __init__(
        self,
        parameter_history_repository,
        trade_repository,
        orchestrator_client: Optional[httpx.AsyncClient] = None,
        orchestrator_url: str = "http://localhost:8089"
    ):
        """
        Initialize auto-deployment manager.

        Args:
            parameter_history_repository: Repository for parameter history tracking
            trade_repository: Repository for trade data queries
            orchestrator_client: HTTP client for orchestrator API calls
            orchestrator_url: Base URL for orchestrator service
        """
        self.parameter_history_repo = parameter_history_repository
        self.trade_repo = trade_repository
        self.orchestrator_url = orchestrator_url
        self.orchestrator_client = orchestrator_client or httpx.AsyncClient(timeout=10.0)

        # Deployment configuration
        self.config = {
            'min_improvement_threshold': Decimal('0.20'),  # 20% minimum improvement
            'max_p_value': Decimal('0.05'),  # 95% confidence required
            'rollback_degradation_threshold': Decimal('0.15'),  # 15% degradation triggers rollback
            'approval_threshold': Decimal('0.10'),  # 10% change requires approval
            'cooldown_days': 7,  # Days between deployments
            'rollout_stages': [Decimal('0.10'), Decimal('0.25'), Decimal('0.50'), Decimal('1.00')],
            'stage_duration_days': 2,  # Days per stage
        }

        # Active deployments tracking (max 1 at a time)
        self.active_deployments: Dict[str, Dict] = {}

        logger.info("AutoDeploymentManager initialized with gradual rollout configuration")

    async def deploy_suggestion(
        self,
        suggestion: ParameterSuggestion,
        evaluation: Dict[str, Any]
    ) -> DeploymentResult:
        """
        Deploy a parameter suggestion through gradual rollout.

        Validates deployment criteria, checks approval requirements, and executes
        staged rollout with performance monitoring at each stage.

        Args:
            suggestion: Parameter suggestion to deploy
            evaluation: Test evaluation results with metrics and statistical analysis

        Returns:
            DeploymentResult: Result of deployment operation

        Raises:
            ValueError: If suggestion or evaluation data is invalid
        """
        logger.info(f"Starting deployment for suggestion {suggestion.suggestion_id}")

        try:
            # Step 1: Validate deployment criteria
            validation_result = await self._validate_deployment_criteria(suggestion, evaluation)
            if not validation_result['valid']:
                logger.warning(f"Deployment validation failed: {validation_result['reason']}")
                return DeploymentResult(
                    success=False,
                    reason=validation_result['reason']
                )

            # Step 2: Check approval requirement
            approval_result = await self._check_approval_requirement(suggestion)
            if approval_result['requires_approval']:
                logger.info(f"Manual approval required for suggestion {suggestion.suggestion_id}")
                return DeploymentResult(
                    success=False,
                    reason="Manual approval required for parameter change >10%",
                    pending_approval=True
                )

            # Step 3: Execute gradual rollout
            deployment_id = str(uuid.uuid4())
            deployment_result = await self._execute_gradual_rollout(
                deployment_id,
                suggestion,
                evaluation
            )

            return deployment_result

        except Exception as e:
            logger.error(f"Deployment failed with exception: {e}", exc_info=True)
            return DeploymentResult(
                success=False,
                reason=f"Deployment error: {str(e)}"
            )

    async def rollback_deployment(
        self,
        deployment_id: str,
        reason: str
    ) -> RollbackResult:
        """
        Rollback a deployment to previous parameter values.

        Args:
            deployment_id: Unique deployment identifier
            reason: Explanation of why rollback occurred

        Returns:
            RollbackResult: Result of rollback operation

        Raises:
            ValueError: If deployment_id not found
        """
        logger.warning(f"Rolling back deployment {deployment_id}: {reason}")

        try:
            # Get deployment record
            deployment = await self.parameter_history_repo.get_deployment(deployment_id)
            if not deployment:
                raise ValueError(f"Deployment not found: {deployment_id}")

            # Retrieve previous parameter values
            previous_values = await self.parameter_history_repo.get_previous_parameters(
                deployment_id
            )

            # Apply previous parameters via orchestrator API
            await self._apply_parameter_values(previous_values)

            # Log rollback to parameter_history
            await self.parameter_history_repo.log_rollback(
                deployment_id=deployment_id,
                reason=reason,
                reverted_to=previous_values
            )

            # Remove from active deployments
            if deployment_id in self.active_deployments:
                del self.active_deployments[deployment_id]

            # Send notification to operators
            await self._send_rollback_notification(deployment_id, reason, previous_values)

            logger.info(f"✅ Successfully rolled back deployment {deployment_id}")

            return RollbackResult(
                success=True,
                deployment_id=deployment_id,
                reason=reason,
                reverted_to=previous_values,
                rolled_back_at=datetime.now(timezone.utc)
            )

        except Exception as e:
            logger.error(f"Rollback failed: {e}", exc_info=True)
            return RollbackResult(
                success=False,
                deployment_id=deployment_id,
                reason=f"Rollback error: {str(e)}",
                reverted_to={},
                rolled_back_at=datetime.now(timezone.utc)
            )

    async def check_rollback_conditions(
        self,
        deployment_id: str
    ) -> Tuple[bool, str]:
        """
        Check if deployment should be rolled back due to performance degradation.

        Args:
            deployment_id: Unique deployment identifier

        Returns:
            Tuple[bool, str]: (should_rollback, reason)
        """
        try:
            # Get deployment record
            deployment = await self.parameter_history_repo.get_deployment(deployment_id)
            if not deployment:
                logger.error(f"Deployment not found: {deployment_id}")
                return (False, "Deployment not found")

            # Query trades since deployment start
            trades = await self.trade_repo.get_trades_since(deployment['start_time'])

            if len(trades) < 10:
                # Not enough data to evaluate yet
                return (False, "Insufficient trades for evaluation")

            # Calculate current performance metrics
            current_metrics = self._calculate_performance_metrics(trades)

            # Get baseline metrics (before deployment)
            baseline_metrics = deployment.get('baseline_metrics', {})

            # Calculate degradation percentage
            degradation_pct = self._calculate_degradation(baseline_metrics, current_metrics)

            # Check if degradation exceeds threshold
            if degradation_pct > self.config['rollback_degradation_threshold']:
                reason = f"Performance degraded by {degradation_pct:.1%} (threshold: {self.config['rollback_degradation_threshold']:.1%})"
                logger.warning(f"Rollback condition met for {deployment_id}: {reason}")
                return (True, reason)

            logger.info(f"Deployment {deployment_id} performance within acceptable range ({degradation_pct:.1%} degradation)")
            return (False, "Performance within acceptable range")

        except Exception as e:
            logger.error(f"Error checking rollback conditions: {e}", exc_info=True)
            return (False, f"Error checking conditions: {str(e)}")

    async def _validate_deployment_criteria(
        self,
        suggestion: ParameterSuggestion,
        evaluation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate multi-layer deployment criteria.

        Checks:
        - Improvement percentage > threshold
        - P-value < significance threshold
        - No active deployment in progress
        - Cooldown period elapsed

        Args:
            suggestion: Parameter suggestion
            evaluation: Test evaluation results

        Returns:
            Dict with 'valid' (bool) and 'reason' (str)
        """
        # Check improvement threshold
        improvement_pct = Decimal(str(evaluation.get('improvement_pct', 0)))
        if improvement_pct < self.config['min_improvement_threshold']:
            return {
                'valid': False,
                'reason': f"Improvement {improvement_pct:.1%} below threshold {self.config['min_improvement_threshold']:.1%}"
            }

        # Check p-value
        p_value = Decimal(str(evaluation.get('p_value', 1.0)))
        if p_value >= self.config['max_p_value']:
            return {
                'valid': False,
                'reason': f"P-value {p_value:.4f} not statistically significant (threshold: {self.config['max_p_value']:.4f})"
            }

        # Check no active deployment
        if len(self.active_deployments) > 0:
            return {
                'valid': False,
                'reason': f"Active deployment in progress (max 1 at a time)"
            }

        # Check cooldown period
        last_deployment = await self.parameter_history_repo.get_last_deployment()
        if last_deployment:
            days_since = (datetime.now(timezone.utc) - last_deployment['deployed_at']).days
            if days_since < self.config['cooldown_days']:
                return {
                    'valid': False,
                    'reason': f"Cooldown period not elapsed ({days_since}/{self.config['cooldown_days']} days)"
                }

        return {'valid': True, 'reason': 'All validation criteria met'}

    async def _check_approval_requirement(
        self,
        suggestion: ParameterSuggestion
    ) -> Dict[str, bool]:
        """
        Check if manual approval is required for this suggestion.

        Approval required if parameter change > 10%.

        Args:
            suggestion: Parameter suggestion

        Returns:
            Dict with 'requires_approval' (bool) and optional 'approval_request_id'
        """
        # Calculate parameter change percentage
        current_value = suggestion.current_value
        suggested_value = suggestion.suggested_value

        if current_value == 0:
            # Avoid division by zero
            change_pct = Decimal('1.0')
        else:
            change_pct = abs(suggested_value - current_value) / abs(current_value)

        # Check if change exceeds approval threshold
        if change_pct > self.config['approval_threshold']:
            logger.info(f"Change {change_pct:.1%} exceeds approval threshold {self.config['approval_threshold']:.1%}")
            return {'requires_approval': True}

        return {'requires_approval': False}

    async def _execute_gradual_rollout(
        self,
        deployment_id: str,
        suggestion: ParameterSuggestion,
        evaluation: Dict[str, Any]
    ) -> DeploymentResult:
        """
        Execute gradual rollout through 4 stages.

        For each stage (10%, 25%, 50%, 100%):
        1. Apply parameter at stage allocation
        2. Log deployment stage
        3. Wait for stage duration
        4. Check rollback conditions
        5. If rollback triggered, revert and exit

        Args:
            deployment_id: Unique deployment identifier
            suggestion: Parameter suggestion to deploy
            evaluation: Test evaluation results

        Returns:
            DeploymentResult with deployment outcome
        """
        logger.info(f"Executing gradual rollout for deployment {deployment_id}")

        # Track deployment as active
        self.active_deployments[deployment_id] = {
            'suggestion_id': suggestion.suggestion_id,
            'start_time': datetime.now(timezone.utc),
            'current_stage': 0
        }

        # Get baseline metrics
        baseline_metrics = await self._get_baseline_metrics(suggestion.session)

        stages_completed = 0

        try:
            for stage_num, allocation_pct in enumerate(self.config['rollout_stages'], start=1):
                logger.info(f"Starting stage {stage_num}: {allocation_pct:.0%} allocation")

                # Apply parameter at this stage allocation
                await self.apply_parameter_at_stage(
                    parameter=suggestion.parameter,
                    value=suggestion.suggested_value,
                    allocation=float(allocation_pct),
                    session=suggestion.session
                )

                # Log deployment stage start
                await self.parameter_history_repo.create_deployment_record({
                    'deployment_id': deployment_id,
                    'suggestion_id': suggestion.suggestion_id,
                    'parameter': suggestion.parameter,
                    'session': suggestion.session,
                    'current_value': float(suggestion.current_value),
                    'suggested_value': float(suggestion.suggested_value),
                    'deployment_stage': stage_num,
                    'allocation_pct': float(allocation_pct),
                    'baseline_metrics': baseline_metrics,
                    'status': 'ACTIVE',
                    'changed_by': 'learning_agent',
                    'reason': suggestion.reason
                })

                # Update active deployment tracking
                self.active_deployments[deployment_id]['current_stage'] = stage_num

                # Wait for stage duration (2 days in production, mocked in tests)
                stage_duration_seconds = self.config['stage_duration_days'] * 24 * 60 * 60
                logger.info(f"Waiting {self.config['stage_duration_days']} days for stage {stage_num} monitoring")
                await asyncio.sleep(stage_duration_seconds)

                # Check rollback conditions
                should_rollback, rollback_reason = await self.check_rollback_conditions(deployment_id)
                if should_rollback:
                    logger.warning(f"Rollback triggered at stage {stage_num}: {rollback_reason}")
                    await self.rollback_deployment(deployment_id, rollback_reason)
                    return DeploymentResult(
                        success=False,
                        deployment_id=deployment_id,
                        reason=f"Rolled back at stage {stage_num}: {rollback_reason}",
                        stages_completed=stages_completed,
                        rollback_triggered=True,
                        deployed_at=datetime.now(timezone.utc)
                    )

                stages_completed += 1
                logger.info(f"✅ Stage {stage_num} completed successfully")

            # All stages completed successfully
            await self.parameter_history_repo.update_deployment_status(
                deployment_id=deployment_id,
                status='COMPLETED'
            )

            # Remove from active deployments
            if deployment_id in self.active_deployments:
                del self.active_deployments[deployment_id]

            logger.info(f"🎉 Deployment {deployment_id} completed successfully through all stages")

            return DeploymentResult(
                success=True,
                deployment_id=deployment_id,
                reason="Deployment completed successfully through all stages",
                stages_completed=4,
                deployed_at=datetime.now(timezone.utc)
            )

        except Exception as e:
            logger.error(f"Gradual rollout failed: {e}", exc_info=True)
            # Attempt rollback on error
            await self.rollback_deployment(deployment_id, f"Deployment error: {str(e)}")
            return DeploymentResult(
                success=False,
                deployment_id=deployment_id,
                reason=f"Deployment failed: {str(e)}",
                stages_completed=stages_completed,
                rollback_triggered=True,
                deployed_at=datetime.now(timezone.utc)
            )

    async def apply_parameter_at_stage(
        self,
        parameter: str,
        value: Decimal,
        allocation: float,
        session: str
    ) -> None:
        """
        Apply parameter update to orchestrator at specific allocation.

        Args:
            parameter: Parameter name (e.g., 'confidence_threshold')
            value: New parameter value
            allocation: Percentage allocation (0.10, 0.25, 0.50, 1.00)
            session: Trading session (e.g., 'LONDON', 'NY')

        Raises:
            httpx.HTTPError: If API call fails after retries
        """
        url = f"{self.orchestrator_url}/api/v1/parameters/update"
        payload = {
            "parameter": parameter,
            "value": float(value),
            "allocation": allocation,
            "session": session,
            "applied_by": "learning_agent"
        }

        # Retry logic (3 attempts)
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                response = await self.orchestrator_client.post(url, json=payload)
                response.raise_for_status()
                logger.info(f"✅ Applied {parameter}={value} at {allocation:.0%} allocation for {session}")
                return

            except httpx.HTTPError as e:
                if attempt < max_retries:
                    logger.warning(f"API call failed (attempt {attempt}/{max_retries}): {e}")
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"Failed to apply parameter after {max_retries} attempts")
                    raise

    async def _get_baseline_metrics(self, session: str) -> Dict[str, float]:
        """
        Get baseline performance metrics before deployment.

        Args:
            session: Trading session to get metrics for

        Returns:
            Dict with win_rate, avg_rr, profit_factor
        """
        try:
            # Get recent trades for session
            trades = await self.trade_repo.get_recent_trades(session=session, limit=100)

            if not trades:
                return {'win_rate': 0.0, 'avg_rr': 0.0, 'profit_factor': 1.0}

            metrics = self._calculate_performance_metrics(trades)
            return metrics

        except Exception as e:
            logger.error(f"Error getting baseline metrics: {e}", exc_info=True)
            return {'win_rate': 0.0, 'avg_rr': 0.0, 'profit_factor': 1.0}

    def _calculate_performance_metrics(self, trades: list) -> Dict[str, float]:
        """
        Calculate performance metrics from trades.

        Args:
            trades: List of trade records

        Returns:
            Dict with win_rate, avg_rr, profit_factor
        """
        if not trades:
            return {'win_rate': 0.0, 'avg_rr': 0.0, 'profit_factor': 1.0}

        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t.get('pnl', 0) > 0)
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0.0

        # Calculate average risk-reward ratio
        rr_values = [t.get('risk_reward_ratio', 0) for t in trades if t.get('risk_reward_ratio')]
        avg_rr = sum(rr_values) / len(rr_values) if rr_values else 0.0

        # Calculate profit factor
        winning_pnl = sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) > 0)
        losing_pnl = abs(sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) <= 0))
        profit_factor = winning_pnl / losing_pnl if losing_pnl > 0 else 1.0

        return {
            'win_rate': float(win_rate),
            'avg_rr': float(avg_rr),
            'profit_factor': float(profit_factor)
        }

    def _calculate_degradation(
        self,
        baseline_metrics: Dict[str, float],
        current_metrics: Dict[str, float]
    ) -> Decimal:
        """
        Calculate performance degradation percentage.

        Args:
            baseline_metrics: Metrics before deployment
            current_metrics: Metrics during deployment

        Returns:
            Decimal: Degradation percentage (positive = worse, negative = better)
        """
        baseline_win_rate = baseline_metrics.get('win_rate', 0.0)
        current_win_rate = current_metrics.get('win_rate', 0.0)

        if baseline_win_rate == 0:
            return Decimal('0.0')

        degradation = (baseline_win_rate - current_win_rate) / baseline_win_rate
        return Decimal(str(degradation))

    async def _apply_parameter_values(self, parameter_values: Dict[str, Decimal]) -> None:
        """
        Apply parameter values to orchestrator.

        Args:
            parameter_values: Dict of parameter names to values
        """
        for parameter, value in parameter_values.items():
            await self.apply_parameter_at_stage(
                parameter=parameter,
                value=value,
                allocation=1.0,  # 100% allocation for rollback
                session=parameter_values.get('session', 'ALL')
            )

    async def _send_rollback_notification(
        self,
        deployment_id: str,
        reason: str,
        reverted_to: Dict[str, Decimal]
    ) -> None:
        """
        Send notification to operators about rollback.

        Args:
            deployment_id: Deployment that was rolled back
            reason: Reason for rollback
            reverted_to: Previous parameter values
        """
        # TODO: Implement notification system (Slack, email, etc.)
        logger.warning(f"ROLLBACK NOTIFICATION: {deployment_id} - {reason}")
        logger.info(f"Reverted to values: {reverted_to}")
