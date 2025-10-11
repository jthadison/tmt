"""
Parameter History Repository for deployment tracking.

Implements repository pattern for parameter history operations including
deployment records, stage tracking, rollback logging, and audit trail queries.
"""

import logging
import json
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ParameterHistory

logger = logging.getLogger(__name__)


class ParameterHistoryRepository:
    """
    Repository for parameter history database operations.

    Provides methods for tracking parameter deployments, logging changes,
    and querying audit trail with proper error handling and transaction management.
    """

    def __init__(self, session_factory):
        """
        Initialize parameter history repository.

        Args:
            session_factory: Async session factory for database operations
        """
        self.session_factory = session_factory

    async def create_deployment_record(self, deployment: Dict) -> ParameterHistory:
        """
        Create deployment record in parameter_history table.

        Args:
            deployment: Dictionary containing deployment fields:
                - deployment_id (str): Unique deployment identifier
                - suggestion_id (str): Associated suggestion ID
                - parameter (str): Parameter name
                - session (str, optional): Trading session
                - current_value (float): Current parameter value
                - suggested_value (float): New parameter value
                - deployment_stage (int): Rollout stage (1-4)
                - allocation_pct (float): Signal allocation percentage
                - baseline_metrics (dict): Performance before deployment
                - status (str): Deployment status
                - changed_by (str): Who/what triggered change
                - reason (str): Explanation for change

        Returns:
            ParameterHistory: Created record

        Raises:
            Exception: If database operation fails
        """
        try:
            async with self.session_factory() as session:
                # Encode baseline_metrics as JSON
                baseline_metrics_json = json.dumps(deployment.get('baseline_metrics', {}))

                record = ParameterHistory(
                    change_time=datetime.now(timezone.utc),
                    parameter_mode=deployment.get('parameter', 'unknown'),
                    session=deployment.get('session'),
                    confidence_threshold=Decimal(str(deployment.get('suggested_value', 0)))
                        if deployment.get('parameter') == 'confidence_threshold' else None,
                    min_risk_reward=Decimal(str(deployment.get('suggested_value', 0)))
                        if deployment.get('parameter') == 'min_risk_reward' else None,
                    reason=deployment.get('reason', ''),
                    changed_by=deployment.get('changed_by', 'learning_agent'),
                    deployment_id=deployment.get('deployment_id'),
                    deployment_stage=deployment.get('deployment_stage'),
                    baseline_metrics=baseline_metrics_json,
                    status=deployment.get('status', 'ACTIVE')
                )

                session.add(record)
                await session.commit()
                await session.refresh(record)

                logger.info(f"✅ Created deployment record: {deployment.get('deployment_id')}")
                return record

        except Exception as e:
            logger.error(f"Failed to create deployment record: {e}", exc_info=True)
            raise

    async def log_deployment_stage(
        self,
        deployment_id: str,
        stage: int,
        metrics: Dict
    ) -> None:
        """
        Update deployment record with current stage and metrics.

        Args:
            deployment_id: Unique deployment identifier
            stage: Stage number (1-4)
            metrics: Current performance metrics
        """
        try:
            async with self.session_factory() as session:
                # Find latest record for this deployment at this stage
                stmt = select(ParameterHistory).where(
                    and_(
                        ParameterHistory.deployment_id == deployment_id,
                        ParameterHistory.deployment_stage == stage
                    )
                ).order_by(desc(ParameterHistory.created_at)).limit(1)

                result = await session.execute(stmt)
                record = result.scalar_one_or_none()

                if record:
                    # Update existing record with current metrics
                    current_metrics = json.loads(record.baseline_metrics) if record.baseline_metrics else {}
                    current_metrics['current'] = metrics
                    record.baseline_metrics = json.dumps(current_metrics)
                    await session.commit()

                    logger.info(f"✅ Updated deployment stage {stage} for {deployment_id}")

        except Exception as e:
            logger.error(f"Failed to log deployment stage: {e}", exc_info=True)
            raise

    async def log_rollback(
        self,
        deployment_id: str,
        reason: str,
        reverted_to: Dict
    ) -> None:
        """
        Log rollback event to parameter_history.

        Args:
            deployment_id: Deployment ID that was rolled back
            reason: Reason for rollback
            reverted_to: Previous parameter values
        """
        try:
            async with self.session_factory() as session:
                # Update all records for this deployment to ROLLED_BACK status
                stmt = select(ParameterHistory).where(
                    ParameterHistory.deployment_id == deployment_id
                )

                result = await session.execute(stmt)
                records = result.scalars().all()

                for record in records:
                    record.status = 'ROLLED_BACK'

                # Create new rollback log entry
                rollback_record = ParameterHistory(
                    change_time=datetime.now(timezone.utc),
                    parameter_mode='ROLLBACK',
                    reason=f"ROLLBACK: {reason}",
                    changed_by='learning_agent',
                    deployment_id=deployment_id,
                    status='ROLLED_BACK'
                )

                session.add(rollback_record)
                await session.commit()

                logger.info(f"✅ Logged rollback for deployment {deployment_id}")

        except Exception as e:
            logger.error(f"Failed to log rollback: {e}", exc_info=True)
            raise

    async def get_recent_deployments(self, days: int = 7) -> List[ParameterHistory]:
        """
        Get deployments within last N days.

        Args:
            days: Number of days to look back

        Returns:
            List[ParameterHistory]: Deployment records ordered by time DESC
        """
        try:
            async with self.session_factory() as session:
                cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)

                stmt = select(ParameterHistory).where(
                    and_(
                        ParameterHistory.deployment_id.isnot(None),
                        ParameterHistory.change_time >= cutoff_time
                    )
                ).order_by(desc(ParameterHistory.change_time))

                result = await session.execute(stmt)
                records = result.scalars().all()

                logger.info(f"Retrieved {len(records)} deployments from last {days} days")
                return list(records)

        except Exception as e:
            logger.error(f"Failed to get recent deployments: {e}", exc_info=True)
            return []

    async def get_deployment_audit_trail(self, deployment_id: str) -> List[Dict]:
        """
        Get complete audit trail for a specific deployment.

        Returns chronological list of all decisions and actions for this deployment.

        Args:
            deployment_id: Unique deployment identifier

        Returns:
            List[Dict]: Audit log entries with timestamps, decisions, and metrics
        """
        try:
            async with self.session_factory() as session:
                stmt = select(ParameterHistory).where(
                    ParameterHistory.deployment_id == deployment_id
                ).order_by(ParameterHistory.change_time)

                result = await session.execute(stmt)
                records = result.scalars().all()

                audit_trail = []
                for record in records:
                    audit_trail.append({
                        'timestamp': record.change_time.isoformat(),
                        'action': f"Stage {record.deployment_stage}" if record.deployment_stage else "Deployment",
                        'parameter_mode': record.parameter_mode,
                        'session': record.session,
                        'confidence_threshold': float(record.confidence_threshold) if record.confidence_threshold else None,
                        'min_risk_reward': float(record.min_risk_reward) if record.min_risk_reward else None,
                        'reason': record.reason,
                        'changed_by': record.changed_by,
                        'status': record.status,
                        'baseline_metrics': json.loads(record.baseline_metrics) if record.baseline_metrics else {}
                    })

                logger.info(f"Retrieved audit trail for {deployment_id}: {len(audit_trail)} entries")
                return audit_trail

        except Exception as e:
            logger.error(f"Failed to get deployment audit trail: {e}", exc_info=True)
            return []

    async def get_deployment(self, deployment_id: str) -> Optional[Dict]:
        """
        Get deployment record by ID.

        Args:
            deployment_id: Unique deployment identifier

        Returns:
            Optional[Dict]: Deployment data or None if not found
        """
        try:
            async with self.session_factory() as session:
                stmt = select(ParameterHistory).where(
                    ParameterHistory.deployment_id == deployment_id
                ).order_by(ParameterHistory.change_time).limit(1)

                result = await session.execute(stmt)
                record = result.scalar_one_or_none()

                if not record:
                    return None

                return {
                    'deployment_id': record.deployment_id,
                    'start_time': record.change_time,
                    'parameter': record.parameter_mode,
                    'session': record.session,
                    'status': record.status,
                    'baseline_metrics': json.loads(record.baseline_metrics) if record.baseline_metrics else {}
                }

        except Exception as e:
            logger.error(f"Failed to get deployment: {e}", exc_info=True)
            return None

    async def get_previous_parameters(self, deployment_id: str) -> Dict[str, Decimal]:
        """
        Get previous parameter values before this deployment.

        Args:
            deployment_id: Deployment to get previous values for

        Returns:
            Dict[str, Decimal]: Previous parameter values
        """
        try:
            async with self.session_factory() as session:
                # Get the deployment record
                deployment = await self.get_deployment(deployment_id)
                if not deployment:
                    return {}

                # Get the parameter change before this deployment
                stmt = select(ParameterHistory).where(
                    and_(
                        ParameterHistory.change_time < deployment['start_time'],
                        ParameterHistory.session == deployment['session']
                    )
                ).order_by(desc(ParameterHistory.change_time)).limit(1)

                result = await session.execute(stmt)
                previous_record = result.scalar_one_or_none()

                if not previous_record:
                    # No previous record, return default values
                    return {
                        'confidence_threshold': Decimal('70.0'),
                        'min_risk_reward': Decimal('2.5')
                    }

                return {
                    'confidence_threshold': previous_record.confidence_threshold or Decimal('70.0'),
                    'min_risk_reward': previous_record.min_risk_reward or Decimal('2.5'),
                    'session': previous_record.session
                }

        except Exception as e:
            logger.error(f"Failed to get previous parameters: {e}", exc_info=True)
            return {}

    async def get_last_deployment(self) -> Optional[Dict]:
        """
        Get the most recent deployment record.

        Returns:
            Optional[Dict]: Last deployment data or None if no deployments exist
        """
        try:
            async with self.session_factory() as session:
                stmt = select(ParameterHistory).where(
                    ParameterHistory.deployment_id.isnot(None)
                ).order_by(desc(ParameterHistory.change_time)).limit(1)

                result = await session.execute(stmt)
                record = result.scalar_one_or_none()

                if not record:
                    return None

                return {
                    'deployment_id': record.deployment_id,
                    'deployed_at': record.change_time
                }

        except Exception as e:
            logger.error(f"Failed to get last deployment: {e}", exc_info=True)
            return None

    async def update_deployment_status(self, deployment_id: str, status: str) -> None:
        """
        Update deployment status.

        Args:
            deployment_id: Unique deployment identifier
            status: New status (PENDING, ACTIVE, COMPLETED, ROLLED_BACK)
        """
        try:
            async with self.session_factory() as session:
                stmt = select(ParameterHistory).where(
                    ParameterHistory.deployment_id == deployment_id
                )

                result = await session.execute(stmt)
                records = result.scalars().all()

                for record in records:
                    record.status = status

                await session.commit()

                logger.info(f"✅ Updated deployment {deployment_id} status to {status}")

        except Exception as e:
            logger.error(f"Failed to update deployment status: {e}", exc_info=True)
            raise
