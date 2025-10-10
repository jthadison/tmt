"""
Approval Workflow for High-Risk Parameter Changes.

Manages manual approval process for parameter changes exceeding 10% threshold.
Creates approval requests, sends notifications, and tracks approval status.
"""

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Dict

from .models.suggestion_models import ParameterSuggestion

logger = logging.getLogger(__name__)


class ApprovalWorkflow:
    """
    Manages approval workflow for high-risk parameter changes.

    Implements manual approval requirement for parameter changes exceeding 10%,
    including request creation, notification, and status tracking.
    """

    def __init__(self, approval_repository):
        """
        Initialize approval workflow.

        Args:
            approval_repository: Repository for approval request persistence
        """
        self.approval_repo = approval_repository
        self.approval_threshold = Decimal('0.10')  # 10%

    def requires_approval(self, suggestion: ParameterSuggestion) -> bool:
        """
        Check if suggestion requires manual approval.

        Approval required if parameter change exceeds 10% threshold.

        Args:
            suggestion: Parameter suggestion to evaluate

        Returns:
            bool: True if manual approval required, False otherwise
        """
        try:
            # Calculate parameter change percentage
            current_value = suggestion.current_value
            suggested_value = suggestion.suggested_value

            if current_value == 0:
                # Avoid division by zero
                change_pct = Decimal('1.0')
            else:
                change_pct = abs(suggested_value - current_value) / abs(current_value)

            requires_approval = change_pct > self.approval_threshold

            logger.info(f"Suggestion {suggestion.suggestion_id} change: {change_pct:.1%} "
                       f"(threshold: {self.approval_threshold:.1%}) - "
                       f"Approval required: {requires_approval}")

            return requires_approval

        except Exception as e:
            logger.error(f"Error checking approval requirement: {e}", exc_info=True)
            # Err on the side of caution - require approval if error
            return True

    async def create_approval_request(
        self,
        suggestion: ParameterSuggestion,
        evaluation: Dict
    ) -> str:
        """
        Create approval request for high-risk parameter change.

        Generates approval request record, stores in database, and sends
        notification to operators for review.

        Args:
            suggestion: Parameter suggestion requiring approval
            evaluation: Test evaluation results with metrics

        Returns:
            str: Approval request ID

        Raises:
            Exception: If approval request creation fails
        """
        try:
            # Generate approval request ID
            approval_request_id = str(uuid.uuid4())

            # Calculate parameter change percentage
            current_value = suggestion.current_value
            suggested_value = suggestion.suggested_value

            if current_value == 0:
                change_pct = Decimal('1.0')
            else:
                change_pct = abs(suggested_value - current_value) / abs(current_value)

            # Extract evaluation metrics
            improvement_pct = Decimal(str(evaluation.get('improvement_pct', 0)))
            p_value = Decimal(str(evaluation.get('p_value', 1.0)))

            # Create approval request record
            approval_data = {
                'approval_request_id': approval_request_id,
                'suggestion_id': suggestion.suggestion_id,
                'parameter': suggestion.parameter,
                'current_value': float(current_value),
                'suggested_value': float(suggested_value),
                'change_pct': float(change_pct),
                'improvement_pct': float(improvement_pct),
                'p_value': float(p_value),
                'status': 'PENDING',
                'requested_at': datetime.now(timezone.utc)
            }

            await self.approval_repo.create_approval_request(approval_data)

            # Send notification to operators
            await self._send_approval_notification(
                approval_request_id,
                suggestion,
                evaluation,
                change_pct
            )

            logger.info(f"✅ Created approval request {approval_request_id} for suggestion {suggestion.suggestion_id}")

            return approval_request_id

        except Exception as e:
            logger.error(f"Failed to create approval request: {e}", exc_info=True)
            raise

    async def check_approval_status(self, approval_request_id: str) -> str:
        """
        Check approval request status.

        Args:
            approval_request_id: Unique approval request identifier

        Returns:
            str: Status ('APPROVED', 'REJECTED', or 'PENDING')

        Raises:
            ValueError: If approval request not found
        """
        try:
            approval_request = await self.approval_repo.get_approval_request(approval_request_id)

            if not approval_request:
                raise ValueError(f"Approval request not found: {approval_request_id}")

            status = approval_request.get('status', 'PENDING')
            logger.info(f"Approval request {approval_request_id} status: {status}")

            return status

        except Exception as e:
            logger.error(f"Failed to check approval status: {e}", exc_info=True)
            raise

    async def approve_request(
        self,
        approval_request_id: str,
        approved_by: str,
        notes: Optional[str] = None
    ) -> bool:
        """
        Approve a parameter change request.

        Args:
            approval_request_id: Unique approval request identifier
            approved_by: Username/identifier of approver
            notes: Optional approval notes

        Returns:
            bool: True if approval successful

        Raises:
            ValueError: If approval request not found or already processed
        """
        try:
            approval_request = await self.approval_repo.get_approval_request(approval_request_id)

            if not approval_request:
                raise ValueError(f"Approval request not found: {approval_request_id}")

            if approval_request.get('status') != 'PENDING':
                raise ValueError(f"Approval request already processed: {approval_request.get('status')}")

            # Update approval request
            await self.approval_repo.update_approval_status(
                approval_request_id=approval_request_id,
                status='APPROVED',
                approved_by=approved_by,
                approved_at=datetime.now(timezone.utc),
                notes=notes
            )

            logger.info(f"✅ Approved request {approval_request_id} by {approved_by}")

            # TODO: Trigger deployment process for approved suggestion

            return True

        except Exception as e:
            logger.error(f"Failed to approve request: {e}", exc_info=True)
            raise

    async def reject_request(
        self,
        approval_request_id: str,
        rejected_by: str,
        reason: str
    ) -> bool:
        """
        Reject a parameter change request.

        Args:
            approval_request_id: Unique approval request identifier
            rejected_by: Username/identifier of rejector
            reason: Reason for rejection

        Returns:
            bool: True if rejection successful

        Raises:
            ValueError: If approval request not found or already processed
        """
        try:
            approval_request = await self.approval_repo.get_approval_request(approval_request_id)

            if not approval_request:
                raise ValueError(f"Approval request not found: {approval_request_id}")

            if approval_request.get('status') != 'PENDING':
                raise ValueError(f"Approval request already processed: {approval_request.get('status')}")

            # Update approval request
            await self.approval_repo.update_approval_status(
                approval_request_id=approval_request_id,
                status='REJECTED',
                approved_by=rejected_by,
                approved_at=datetime.now(timezone.utc),
                notes=reason
            )

            logger.info(f"❌ Rejected request {approval_request_id} by {rejected_by}: {reason}")

            return True

        except Exception as e:
            logger.error(f"Failed to reject request: {e}", exc_info=True)
            raise

    async def get_pending_approvals(self) -> list:
        """
        Get all pending approval requests.

        Returns:
            list: Pending approval requests
        """
        try:
            pending_requests = await self.approval_repo.get_pending_approval_requests()

            logger.info(f"Retrieved {len(pending_requests)} pending approval requests")

            return pending_requests

        except Exception as e:
            logger.error(f"Failed to get pending approvals: {e}", exc_info=True)
            return []

    async def _send_approval_notification(
        self,
        approval_request_id: str,
        suggestion: ParameterSuggestion,
        evaluation: Dict,
        change_pct: Decimal
    ) -> None:
        """
        Send notification to operators about approval request.

        Args:
            approval_request_id: Approval request ID
            suggestion: Parameter suggestion
            evaluation: Test evaluation results
            change_pct: Parameter change percentage
        """
        # TODO: Implement notification system (Slack, email, dashboard alert)
        logger.warning(f"⚠️  APPROVAL REQUIRED: {approval_request_id}")
        logger.info(f"Parameter: {suggestion.parameter}")
        logger.info(f"Session: {suggestion.session}")
        logger.info(f"Current Value: {suggestion.current_value}")
        logger.info(f"Suggested Value: {suggestion.suggested_value}")
        logger.info(f"Change: {change_pct:.1%}")
        logger.info(f"Expected Improvement: {suggestion.expected_improvement:.1%}")
        logger.info(f"Reason: {suggestion.reason}")
