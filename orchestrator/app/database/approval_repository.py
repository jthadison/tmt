"""
Approval Request Repository.

Implements repository pattern for approval request operations including
creation, status updates, and queries.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ApprovalRequest

logger = logging.getLogger(__name__)


class ApprovalRepository:
    """
    Repository for approval request database operations.

    Provides methods for managing approval workflow with proper error
    handling and transaction management.
    """

    def __init__(self, session_factory):
        """
        Initialize approval repository.

        Args:
            session_factory: Async session factory for database operations
        """
        self.session_factory = session_factory

    async def create_approval_request(self, approval_data: Dict) -> ApprovalRequest:
        """
        Create approval request record.

        Args:
            approval_data: Dictionary containing approval request fields

        Returns:
            ApprovalRequest: Created approval request

        Raises:
            Exception: If database operation fails
        """
        try:
            async with self.session_factory() as session:
                approval_request = ApprovalRequest(
                    approval_request_id=approval_data['approval_request_id'],
                    suggestion_id=approval_data['suggestion_id'],
                    parameter=approval_data['parameter'],
                    current_value=approval_data.get('current_value'),
                    suggested_value=approval_data.get('suggested_value'),
                    change_pct=approval_data.get('change_pct'),
                    improvement_pct=approval_data.get('improvement_pct'),
                    p_value=approval_data.get('p_value'),
                    status='PENDING'
                )

                session.add(approval_request)
                await session.commit()
                await session.refresh(approval_request)

                logger.info(f"✅ Created approval request: {approval_request.approval_request_id}")
                return approval_request

        except Exception as e:
            logger.error(f"Failed to create approval request: {e}", exc_info=True)
            raise

    async def get_approval_request(self, approval_request_id: str) -> Optional[Dict]:
        """
        Get approval request by ID.

        Args:
            approval_request_id: Unique approval request identifier

        Returns:
            Optional[Dict]: Approval request data or None if not found
        """
        try:
            async with self.session_factory() as session:
                stmt = select(ApprovalRequest).where(
                    ApprovalRequest.approval_request_id == approval_request_id
                )

                result = await session.execute(stmt)
                approval_request = result.scalar_one_or_none()

                if not approval_request:
                    return None

                return {
                    'approval_request_id': approval_request.approval_request_id,
                    'suggestion_id': approval_request.suggestion_id,
                    'parameter': approval_request.parameter,
                    'current_value': float(approval_request.current_value) if approval_request.current_value else None,
                    'suggested_value': float(approval_request.suggested_value) if approval_request.suggested_value else None,
                    'change_pct': float(approval_request.change_pct) if approval_request.change_pct else None,
                    'improvement_pct': float(approval_request.improvement_pct) if approval_request.improvement_pct else None,
                    'p_value': float(approval_request.p_value) if approval_request.p_value else None,
                    'status': approval_request.status,
                    'requested_at': approval_request.requested_at.isoformat(),
                    'approved_by': approval_request.approved_by,
                    'approved_at': approval_request.approved_at.isoformat() if approval_request.approved_at else None,
                    'rejection_reason': approval_request.rejection_reason
                }

        except Exception as e:
            logger.error(f"Failed to get approval request: {e}", exc_info=True)
            return None

    async def update_approval_status(
        self,
        approval_request_id: str,
        status: str,
        approved_by: str,
        approved_at: datetime,
        notes: Optional[str] = None
    ) -> None:
        """
        Update approval request status.

        Args:
            approval_request_id: Unique approval request identifier
            status: New status (APPROVED or REJECTED)
            approved_by: Who approved/rejected the request
            approved_at: When the decision was made
            notes: Optional notes or rejection reason
        """
        try:
            async with self.session_factory() as session:
                stmt = select(ApprovalRequest).where(
                    ApprovalRequest.approval_request_id == approval_request_id
                )

                result = await session.execute(stmt)
                approval_request = result.scalar_one_or_none()

                if not approval_request:
                    raise ValueError(f"Approval request not found: {approval_request_id}")

                approval_request.status = status
                approval_request.approved_by = approved_by
                approval_request.approved_at = approved_at

                if status == 'REJECTED' and notes:
                    approval_request.rejection_reason = notes

                await session.commit()

                logger.info(f"✅ Updated approval request {approval_request_id} status to {status}")

        except Exception as e:
            logger.error(f"Failed to update approval status: {e}", exc_info=True)
            raise

    async def get_pending_approval_requests(self) -> List[Dict]:
        """
        Get all pending approval requests.

        Returns:
            List[Dict]: Pending approval requests
        """
        try:
            async with self.session_factory() as session:
                stmt = select(ApprovalRequest).where(
                    ApprovalRequest.status == 'PENDING'
                ).order_by(ApprovalRequest.requested_at.desc())

                result = await session.execute(stmt)
                approval_requests = result.scalars().all()

                pending_requests = []
                for req in approval_requests:
                    pending_requests.append({
                        'approval_request_id': req.approval_request_id,
                        'suggestion_id': req.suggestion_id,
                        'parameter': req.parameter,
                        'current_value': float(req.current_value) if req.current_value else None,
                        'suggested_value': float(req.suggested_value) if req.suggested_value else None,
                        'change_pct': float(req.change_pct) if req.change_pct else None,
                        'improvement_pct': float(req.improvement_pct) if req.improvement_pct else None,
                        'p_value': float(req.p_value) if req.p_value else None,
                        'requested_at': req.requested_at.isoformat()
                    })

                logger.info(f"Retrieved {len(pending_requests)} pending approval requests")
                return pending_requests

        except Exception as e:
            logger.error(f"Failed to get pending approvals: {e}", exc_info=True)
            return []
