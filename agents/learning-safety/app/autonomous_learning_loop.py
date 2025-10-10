"""
Autonomous learning agent with continuous learning loop.

Implements 24-hour learning cycle that automatically analyzes trade performance,
identifies optimization opportunities, and generates parameter improvement suggestions.
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional

from .performance_analyzer import PerformanceAnalyzer
from .audit_logger import AuditLogger


logger = logging.getLogger(__name__)


class AutonomousLearningAgent:
    """
    Autonomous learning agent with continuous 24-hour learning cycle.

    Automatically analyzes recent trade performance every 24 hours across
    multiple dimensions (session, pattern, confidence) and identifies
    optimization opportunities without manual intervention.
    """

    def __init__(
        self,
        trade_repository,
        performance_analyzer: Optional[PerformanceAnalyzer] = None,
        audit_logger: Optional[AuditLogger] = None,
        parameter_suggestion_engine = None,
        shadow_tester = None,
        cycle_interval: Optional[int] = None
    ):
        """
        Initialize autonomous learning agent.

        Args:
            trade_repository: Repository for accessing trade history
            performance_analyzer: Performance analyzer instance (creates new if None)
            audit_logger: Audit logger instance (creates new if None)
            parameter_suggestion_engine: Parameter suggestion engine instance (optional)
            shadow_tester: Shadow testing framework instance (optional)
            cycle_interval: Learning cycle interval in seconds (default: 86400 = 24 hours)
        """
        self.trade_repository = trade_repository
        self.performance_analyzer = performance_analyzer or PerformanceAnalyzer()
        self.audit_logger = audit_logger or AuditLogger()
        self.parameter_suggestion_engine = parameter_suggestion_engine
        self.shadow_tester = shadow_tester

        # Learning cycle interval (default: 24 hours)
        if cycle_interval is None:
            cycle_interval = int(os.getenv("LEARNING_CYCLE_INTERVAL", "86400"))
        self.cycle_interval = cycle_interval

        # Cycle state tracking
        self.cycle_state = "IDLE"  # IDLE, RUNNING, COMPLETED, FAILED
        self.last_run_timestamp: Optional[datetime] = None
        self.next_run_timestamp: Optional[datetime] = None
        self.suggestions_generated_count = 0
        self.active_tests_count = 0
        self._running = False
        self._task: Optional[asyncio.Task] = None

        logger.info(
            f"✅ AutonomousLearningAgent initialized "
            f"(cycle interval: {cycle_interval}s, "
            f"suggestion_engine: {parameter_suggestion_engine is not None}, "
            f"shadow_tester: {shadow_tester is not None})"
        )

    async def continuous_learning_loop(self) -> None:
        """
        Continuous learning loop that runs every 24 hours.

        Implements infinite loop that:
        1. Queries recent trades from database
        2. Analyzes performance across all dimensions
        3. Logs results to audit trail
        4. Sleeps for configured interval
        5. Repeats

        Handles errors gracefully without crashing the loop.
        """
        self._running = True
        logger.info("🔄 Starting continuous learning loop")

        while self._running:
            cycle_id = str(uuid.uuid4())
            self.cycle_state = "RUNNING"

            try:
                # Log cycle start
                self.last_run_timestamp = datetime.now()
                self.next_run_timestamp = self.last_run_timestamp + timedelta(
                    seconds=self.cycle_interval
                )
                self.audit_logger.log_cycle_start(self.last_run_timestamp, cycle_id)

                logger.info(f"📊 Starting learning cycle {cycle_id}")

                # Step 1: Query recent trades
                logger.info("📈 Querying recent trades from database...")
                trades = await self.trade_repository.get_recent_trades(limit=100)
                logger.info(f"✅ Retrieved {len(trades)} trades for analysis")

                # Check if sufficient data available
                if len(trades) < 10:
                    logger.info(
                        f"ℹ️  Insufficient trades for analysis ({len(trades)} < 10), "
                        "skipping cycle"
                    )
                    self.audit_logger.log_insufficient_data(
                        cycle_id, len(trades), 10
                    )
                    self.cycle_state = "COMPLETED"
                    await self._sleep_until_next_cycle()
                    continue

                # Step 2: Analyze performance
                logger.info("🔍 Analyzing performance across all dimensions...")
                analysis = self.performance_analyzer.analyze_performance(trades)

                logger.info(
                    f"✅ Analysis complete: {analysis.trade_count} trades analyzed"
                )
                logger.info(f"   Best session: {analysis.best_session}")
                logger.info(f"   Worst session: {analysis.worst_session}")

                # Step 3: Log analysis results
                self.audit_logger.log_cycle_complete(cycle_id, analysis)

                # Step 4: Generate parameter suggestions (if engine available)
                if self.parameter_suggestion_engine:
                    logger.info("🔍 Generating parameter suggestions...")
                    suggestions = self.parameter_suggestion_engine.generate_suggestions(
                        analysis,
                        max_suggestions=3
                    )
                    self.suggestions_generated_count = len(suggestions)
                    logger.info(f"✅ Generated {len(suggestions)} suggestions")

                    # Step 5: Start shadow tests for top suggestions (if shadow tester available)
                    if self.shadow_tester and suggestions:
                        logger.info("🧪 Starting shadow tests for top suggestions...")
                        for suggestion in suggestions:
                            try:
                                test_id = await self.shadow_tester.start_test(
                                    suggestion,
                                    allocation=0.10,
                                    duration_days=7
                                )
                                self.active_tests_count += 1
                                logger.info(
                                    f"   Started test {test_id} for {suggestion.parameter} "
                                    f"on {suggestion.session}"
                                )
                            except Exception as e:
                                logger.error(
                                    f"   ❌ Failed to start test for suggestion "
                                    f"{suggestion.suggestion_id}: {e}"
                                )

                # Step 6: Evaluate completed shadow tests (if shadow tester available)
                if self.shadow_tester:
                    logger.info("📊 Checking for completed shadow tests...")
                    try:
                        completed_tests = await self.shadow_tester.get_completed_tests()
                        logger.info(f"   Found {len(completed_tests)} completed tests")

                        for test in completed_tests:
                            try:
                                evaluation = await self.shadow_tester.evaluate_test(test.test_id)
                                logger.info(
                                    f"   Evaluated test {test.test_id}: "
                                    f"{'DEPLOY' if evaluation.should_deploy else 'NO DEPLOY'}"
                                )
                                # Store evaluation for auto-deployment (Story 13.3)
                            except Exception as e:
                                logger.error(
                                    f"   ❌ Failed to evaluate test {test.test_id}: {e}"
                                )
                    except Exception as e:
                        logger.error(f"❌ Failed to get completed tests: {e}")

                # Set cycle state to completed
                self.cycle_state = "COMPLETED"
                logger.info(f"✅ Learning cycle {cycle_id} completed successfully")

            except Exception as e:
                # Handle errors without crashing loop
                self.cycle_state = "FAILED"
                logger.error(f"❌ Learning cycle {cycle_id} failed: {e}", exc_info=True)
                self.audit_logger.log_cycle_failed(cycle_id, e)

            finally:
                # Sleep for configured interval before next cycle
                if self._running:
                    await self._sleep_until_next_cycle()

        logger.info("🛑 Continuous learning loop stopped")

    async def _sleep_until_next_cycle(self) -> None:
        """
        Sleep until next learning cycle.

        Logs countdown at regular intervals for visibility.
        """
        if not self.next_run_timestamp:
            self.next_run_timestamp = datetime.now() + timedelta(
                seconds=self.cycle_interval
            )

        remaining_seconds = (self.next_run_timestamp - datetime.now()).total_seconds()
        remaining_seconds = max(0, remaining_seconds)

        logger.info(
            f"⏰ Next learning cycle in {remaining_seconds:.0f}s "
            f"(at {self.next_run_timestamp.isoformat()})"
        )

        # Sleep in chunks to allow for responsive shutdown
        chunk_size = 60  # Check every 60 seconds
        while remaining_seconds > 0 and self._running:
            sleep_time = min(chunk_size, remaining_seconds)
            await asyncio.sleep(sleep_time)
            remaining_seconds -= sleep_time

    def get_cycle_status(self) -> Dict:
        """
        Get current learning cycle status.

        Returns:
            Dict: Status information including cycle state, timestamps, and counters
        """
        return {
            "cycle_state": self.cycle_state,
            "last_run_timestamp": (
                self.last_run_timestamp.isoformat()
                if self.last_run_timestamp
                else None
            ),
            "next_run_timestamp": (
                self.next_run_timestamp.isoformat()
                if self.next_run_timestamp
                else None
            ),
            "suggestions_generated_count": self.suggestions_generated_count,
            "active_tests_count": self.active_tests_count,
            "cycle_interval_seconds": self.cycle_interval,
            "running": self._running
        }

    async def start(self) -> None:
        """
        Start the autonomous learning loop in the background.

        Creates an asyncio task that runs the continuous learning loop.
        """
        if self._task is None or self._task.done():
            self._running = True
            self._task = asyncio.create_task(self.continuous_learning_loop())
            logger.info("✅ Autonomous learning loop started")
        else:
            logger.warning("⚠️  Learning loop already running")

    async def stop(self) -> None:
        """
        Stop the autonomous learning loop gracefully.

        Cancels the learning loop task and waits for cleanup.
        """
        if self._task and not self._task.done():
            self._running = False
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                logger.info("✅ Autonomous learning loop stopped")
        else:
            logger.info("ℹ️  Learning loop not running")
