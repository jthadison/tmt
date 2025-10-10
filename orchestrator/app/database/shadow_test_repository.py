"""
Shadow test repository for database operations on shadow tests.

Implements the repository pattern for shadow test persistence with async operations,
connection pooling, and comprehensive error handling.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ShadowTest

logger = logging.getLogger(__name__)


class ShadowTestRepository:
    """
    Repository for shadow test database operations.

    Provides methods for creating, querying, and updating shadow test records
    with proper error handling and transaction management.
    """

    def __init__(self, session_factory):
        """
        Initialize shadow test repository.

        Args:
            session_factory: Async session factory for database operations
        """
        self.session_factory = session_factory

    async def create_test(self, test_data: Dict) -> ShadowTest:
        """
        Create a new shadow test in the database.

        Args:
            test_data: Dictionary containing shadow test fields:
                - test_id (str): Unique test identifier
                - suggestion_id (str): Associated suggestion ID
                - parameter_name (str): Parameter being tested
                - session (str, optional): Trading session
                - current_value (Decimal): Current parameter value
                - test_value (Decimal): Test parameter value
                - start_date (datetime): Test start timestamp
                - min_duration_days (int): Minimum test duration
                - allocation_pct (Decimal): Signal allocation percentage
                - status (str): Test status (ACTIVE, COMPLETED, TERMINATED, DEPLOYED)

        Returns:
            ShadowTest: Created shadow test ORM object

        Raises:
            Exception: If database operation fails
        """
        try:
            async with self.session_factory() as session:
                # Create shadow test object
                test_obj = ShadowTest(
                    test_id=test_data["test_id"],
                    suggestion_id=test_data["suggestion_id"],
                    parameter_name=test_data["parameter_name"],
                    session=test_data.get("session"),
                    current_value=self._to_decimal(test_data.get("current_value")),
                    test_value=self._to_decimal(test_data.get("test_value")),
                    start_date=test_data["start_date"],
                    min_duration_days=test_data.get("min_duration_days", 7),
                    allocation_pct=self._to_decimal(test_data.get("allocation_pct", "10.0")),
                    control_trades=0,
                    test_trades=0,
                    status=test_data.get("status", "ACTIVE")
                )

                session.add(test_obj)
                await session.commit()
                await session.refresh(test_obj)

                logger.info(f"✅ Created shadow test: {test_obj.test_id}")
                return test_obj

        except Exception as e:
            logger.error(f"❌ Failed to create shadow test: {e}", exc_info=True)
            raise

    async def get_active_tests(self) -> List[ShadowTest]:
        """
        Get all active shadow tests.

        Returns:
            List[ShadowTest]: List of active shadow tests

        Raises:
            Exception: If database operation fails
        """
        try:
            async with self.session_factory() as session:
                stmt = select(ShadowTest).where(ShadowTest.status == "ACTIVE")
                result = await session.execute(stmt)
                tests = result.scalars().all()

                logger.info(f"✅ Retrieved {len(tests)} active shadow tests")
                return list(tests)

        except Exception as e:
            logger.error(f"❌ Failed to get active tests: {e}", exc_info=True)
            raise

    async def get_test_by_id(self, test_id: str) -> Optional[ShadowTest]:
        """
        Get shadow test by test ID.

        Args:
            test_id: Unique test identifier

        Returns:
            Optional[ShadowTest]: Shadow test if found, None otherwise

        Raises:
            Exception: If database operation fails
        """
        try:
            async with self.session_factory() as session:
                stmt = select(ShadowTest).where(ShadowTest.test_id == test_id)
                result = await session.execute(stmt)
                test = result.scalar_one_or_none()

                if test:
                    logger.info(f"✅ Retrieved shadow test: {test_id}")
                else:
                    logger.warning(f"⚠️  Shadow test not found: {test_id}")

                return test

        except Exception as e:
            logger.error(f"❌ Failed to get shadow test {test_id}: {e}", exc_info=True)
            raise

    async def update_test_metrics(self, test_id: str, metrics: Dict) -> ShadowTest:
        """
        Update shadow test performance metrics.

        Args:
            test_id: Unique test identifier
            metrics: Dictionary containing metrics to update:
                - control_trades (int, optional): Number of control trades
                - test_trades (int, optional): Number of test trades
                - control_win_rate (Decimal, optional): Control group win rate
                - test_win_rate (Decimal, optional): Test group win rate
                - control_avg_rr (Decimal, optional): Control group avg R:R
                - test_avg_rr (Decimal, optional): Test group avg R:R

        Returns:
            ShadowTest: Updated shadow test object

        Raises:
            Exception: If database operation fails or test not found
        """
        try:
            async with self.session_factory() as session:
                stmt = select(ShadowTest).where(ShadowTest.test_id == test_id)
                result = await session.execute(stmt)
                test = result.scalar_one_or_none()

                if not test:
                    raise ValueError(f"Shadow test not found: {test_id}")

                # Update metrics
                if "control_trades" in metrics:
                    test.control_trades = metrics["control_trades"]
                if "test_trades" in metrics:
                    test.test_trades = metrics["test_trades"]
                if "control_win_rate" in metrics:
                    test.control_win_rate = self._to_decimal(metrics["control_win_rate"])
                if "test_win_rate" in metrics:
                    test.test_win_rate = self._to_decimal(metrics["test_win_rate"])
                if "control_avg_rr" in metrics:
                    test.control_avg_rr = self._to_decimal(metrics["control_avg_rr"])
                if "test_avg_rr" in metrics:
                    test.test_avg_rr = self._to_decimal(metrics["test_avg_rr"])

                # Update timestamp
                test.updated_at = datetime.now()

                await session.commit()
                await session.refresh(test)

                logger.info(f"✅ Updated metrics for shadow test: {test_id}")
                return test

        except Exception as e:
            logger.error(f"❌ Failed to update test metrics {test_id}: {e}", exc_info=True)
            raise

    async def complete_test(self, test_id: str, evaluation: Dict) -> ShadowTest:
        """
        Mark shadow test as completed with evaluation results.

        Args:
            test_id: Unique test identifier
            evaluation: Dictionary containing evaluation results:
                - improvement_pct (Decimal): Performance improvement percentage
                - p_value (Decimal): Statistical significance p-value

        Returns:
            ShadowTest: Completed shadow test object

        Raises:
            Exception: If database operation fails or test not found
        """
        try:
            async with self.session_factory() as session:
                stmt = select(ShadowTest).where(ShadowTest.test_id == test_id)
                result = await session.execute(stmt)
                test = result.scalar_one_or_none()

                if not test:
                    raise ValueError(f"Shadow test not found: {test_id}")

                # Update status and evaluation results
                test.status = "COMPLETED"
                test.end_date = datetime.now()
                test.improvement_pct = self._to_decimal(evaluation.get("improvement_pct"))
                test.p_value = self._to_decimal(evaluation.get("p_value"))
                test.updated_at = datetime.now()

                await session.commit()
                await session.refresh(test)

                logger.info(f"✅ Completed shadow test: {test_id}")
                return test

        except Exception as e:
            logger.error(f"❌ Failed to complete test {test_id}: {e}", exc_info=True)
            raise

    async def terminate_test(self, test_id: str, reason: str) -> ShadowTest:
        """
        Terminate shadow test early with reason.

        Args:
            test_id: Unique test identifier
            reason: Termination reason

        Returns:
            ShadowTest: Terminated shadow test object

        Raises:
            Exception: If database operation fails or test not found
        """
        try:
            async with self.session_factory() as session:
                stmt = select(ShadowTest).where(ShadowTest.test_id == test_id)
                result = await session.execute(stmt)
                test = result.scalar_one_or_none()

                if not test:
                    raise ValueError(f"Shadow test not found: {test_id}")

                # Update status and termination reason
                test.status = "TERMINATED"
                test.end_date = datetime.now()
                test.termination_reason = reason
                test.updated_at = datetime.now()

                await session.commit()
                await session.refresh(test)

                logger.info(f"✅ Terminated shadow test: {test_id} (reason: {reason})")
                return test

        except Exception as e:
            logger.error(f"❌ Failed to terminate test {test_id}: {e}", exc_info=True)
            raise

    async def get_completed_tests(self) -> List[ShadowTest]:
        """
        Get all completed shadow tests.

        Returns:
            List[ShadowTest]: List of completed shadow tests

        Raises:
            Exception: If database operation fails
        """
        try:
            async with self.session_factory() as session:
                stmt = select(ShadowTest).where(ShadowTest.status == "COMPLETED")
                result = await session.execute(stmt)
                tests = result.scalars().all()

                logger.info(f"✅ Retrieved {len(tests)} completed shadow tests")
                return list(tests)

        except Exception as e:
            logger.error(f"❌ Failed to get completed tests: {e}", exc_info=True)
            raise

    def _to_decimal(self, value) -> Optional[Decimal]:
        """
        Convert value to Decimal type.

        Args:
            value: Value to convert (can be int, float, str, Decimal, or None)

        Returns:
            Optional[Decimal]: Decimal value or None
        """
        if value is None:
            return None
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))
