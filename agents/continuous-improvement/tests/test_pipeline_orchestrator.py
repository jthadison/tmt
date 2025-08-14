"""
Tests for Continuous Improvement Pipeline Orchestrator
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from pipeline_orchestrator import ContinuousImprovementOrchestrator
from models import (
    ImprovementTest, ImprovementSuggestion, TestPhase, ImprovementType,
    Priority, RiskLevel, ImplementationComplexity, SuggestionStatus
)


class TestContinuousImprovementOrchestrator:
    """Test suite for ContinuousImprovementOrchestrator"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance for testing"""
        return ContinuousImprovementOrchestrator()
    
    @pytest.fixture
    def mock_improvement_test(self):
        """Create mock improvement test"""
        return ImprovementTest(
            name="Test Improvement",
            description="Test improvement for testing",
            hypothesis="This should improve performance",
            improvement_type=ImprovementType.PARAMETER_OPTIMIZATION,
            risk_assessment="medium"
        )
    
    @pytest.fixture
    def mock_suggestion(self):
        """Create mock improvement suggestion"""
        return ImprovementSuggestion(
            title="Test Suggestion",
            description="Test suggestion for testing",
            rationale="This should help performance",
            suggestion_type=ImprovementType.PARAMETER_OPTIMIZATION,
            category="test_category",
            priority=Priority.MEDIUM,
            risk_level=RiskLevel.MEDIUM,
            implementation_effort=ImplementationComplexity.MEDIUM,
            priority_score=70.0
        )
    
    @pytest.mark.asyncio
    async def test_start_pipeline(self, orchestrator):
        """Test pipeline startup"""
        result = await orchestrator.start_pipeline()
        assert result is True
        assert orchestrator._running is True
    
    @pytest.mark.asyncio
    async def test_stop_pipeline(self, orchestrator):
        """Test pipeline shutdown"""
        await orchestrator.start_pipeline()
        result = await orchestrator.stop_pipeline()
        assert result is True
        assert orchestrator._running is False
    
    @pytest.mark.asyncio
    async def test_execute_improvement_cycle(self, orchestrator):
        """Test improvement cycle execution"""
        await orchestrator.start_pipeline()
        
        # Add a mock suggestion
        mock_suggestion = ImprovementSuggestion(
            title="Test Suggestion",
            description="Test description",
            rationale="Test rationale",
            suggestion_type=ImprovementType.PARAMETER_OPTIMIZATION,
            category="test",
            priority_score=80.0
        )
        orchestrator.pipeline.pending_suggestions.append(mock_suggestion)
        
        results = await orchestrator.execute_improvement_cycle()
        
        assert results.success is True
        assert orchestrator._cycle_count == 1
        assert orchestrator._last_cycle_time is not None
    
    @pytest.mark.asyncio
    async def test_should_test_suggestion_high_priority(self, orchestrator, mock_suggestion):
        """Test suggestion approval for high priority suggestions"""
        mock_suggestion.priority_score = 90.0
        mock_suggestion.priority = Priority.HIGH
        
        result = await orchestrator._should_test_suggestion(mock_suggestion)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_should_test_suggestion_low_priority(self, orchestrator, mock_suggestion):
        """Test suggestion rejection for low priority suggestions"""
        mock_suggestion.priority_score = 30.0
        mock_suggestion.priority = Priority.LOW
        
        result = await orchestrator._should_test_suggestion(mock_suggestion)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_should_test_suggestion_resource_limit(self, orchestrator, mock_suggestion):
        """Test suggestion rejection when resource limits reached"""
        # Fill up the pipeline with active tests
        for i in range(5):  # Max concurrent tests
            test = ImprovementTest(
                name=f"Test {i}",
                current_phase=TestPhase.ROLLOUT_10
            )
            orchestrator.pipeline.active_improvements.append(test)
        
        mock_suggestion.priority_score = 90.0
        result = await orchestrator._should_test_suggestion(mock_suggestion)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_create_improvement_test(self, orchestrator, mock_suggestion):
        """Test improvement test creation"""
        test = await orchestrator._create_improvement_test(mock_suggestion)
        
        assert test is not None
        assert test.name == mock_suggestion.title
        assert test.description == mock_suggestion.description
        assert test.improvement_type == mock_suggestion.suggestion_type
        assert test.control_group is not None
        assert test.treatment_group is not None
    
    @pytest.mark.asyncio
    async def test_get_pipeline_status(self, orchestrator):
        """Test pipeline status retrieval"""
        await orchestrator.start_pipeline()
        
        status = await orchestrator.get_pipeline_status()
        
        assert 'pipeline_id' in status
        assert 'running' in status
        assert status['running'] is True
        assert 'cycle_count' in status
        assert 'metrics' in status
    
    @pytest.mark.asyncio
    async def test_get_active_tests(self, orchestrator, mock_improvement_test):
        """Test active tests retrieval"""
        orchestrator.pipeline.active_improvements.append(mock_improvement_test)
        
        active_tests = await orchestrator.get_active_tests()
        
        assert len(active_tests) == 1
        assert active_tests[0]['test_id'] == mock_improvement_test.test_id
        assert active_tests[0]['name'] == mock_improvement_test.name
    
    @pytest.mark.asyncio
    async def test_approve_test_advancement(self, orchestrator, mock_improvement_test):
        """Test manual test approval"""
        mock_improvement_test.human_review_required = True
        orchestrator.pipeline.active_improvements.append(mock_improvement_test)
        
        result = await orchestrator.approve_test_advancement(
            mock_improvement_test.test_id, 
            "test_approver", 
            "Approved for testing"
        )
        
        assert result is True
        assert len(mock_improvement_test.approvals) == 1
        assert mock_improvement_test.human_review_required is False
    
    @pytest.mark.asyncio
    async def test_emergency_stop_test(self, orchestrator, mock_improvement_test):
        """Test emergency stop functionality"""
        orchestrator.pipeline.active_improvements.append(mock_improvement_test)
        
        result = await orchestrator.emergency_stop_test(
            mock_improvement_test.test_id, 
            "Emergency stop for testing"
        )
        
        assert result is True
        assert mock_improvement_test.current_phase == TestPhase.ROLLED_BACK
        assert "Emergency stop" in mock_improvement_test.rollback_reason
    
    def test_set_components(self, orchestrator):
        """Test component dependency injection"""
        mock_component = Mock()
        
        orchestrator.set_components(test_component=mock_component)
        
        assert orchestrator.test_component == mock_component
    
    @pytest.mark.asyncio
    async def test_validate_configuration_valid(self, orchestrator):
        """Test configuration validation with valid config"""
        result = await orchestrator._validate_configuration()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_configuration_invalid_rollback_threshold(self, orchestrator):
        """Test configuration validation with invalid rollback threshold"""
        orchestrator.pipeline.configuration.rollback_threshold = Decimal('0.10')  # Positive (invalid)
        
        result = await orchestrator._validate_configuration()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_validate_configuration_invalid_max_tests(self, orchestrator):
        """Test configuration validation with invalid max concurrent tests"""
        orchestrator.pipeline.configuration.max_concurrent_tests = 0
        
        result = await orchestrator._validate_configuration()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_next_phase_progression(self, orchestrator):
        """Test phase progression logic"""
        next_phase = await orchestrator._get_next_phase(TestPhase.SHADOW)
        assert next_phase == TestPhase.ROLLOUT_10
        
        next_phase = await orchestrator._get_next_phase(TestPhase.ROLLOUT_10)
        assert next_phase == TestPhase.ROLLOUT_25
        
        next_phase = await orchestrator._get_next_phase(TestPhase.ROLLOUT_50)
        assert next_phase == TestPhase.ROLLOUT_100
        
        next_phase = await orchestrator._get_next_phase(TestPhase.ROLLOUT_100)
        assert next_phase is None  # Complete
    
    @pytest.mark.asyncio
    async def test_update_pipeline_metrics(self, orchestrator):
        """Test pipeline metrics update"""
        # Add some completed and rolled back tests
        completed_test = ImprovementTest(
            name="Completed Test",
            current_phase=TestPhase.COMPLETED
        )
        rolled_back_test = ImprovementTest(
            name="Rolled Back Test", 
            current_phase=TestPhase.ROLLED_BACK
        )
        
        orchestrator.pipeline.active_improvements.extend([completed_test, rolled_back_test])
        
        await orchestrator._update_pipeline_metrics()
        
        assert orchestrator.pipeline.pipeline_metrics.improvement_success_rate == 0.5
        assert orchestrator.pipeline.pipeline_metrics.rollback_rate == 0.5
        assert orchestrator.pipeline.status.successful_deployments == 1
        assert orchestrator.pipeline.status.rollbacks == 1


@pytest.mark.asyncio
async def test_integration_full_cycle():
    """Integration test for full improvement cycle"""
    orchestrator = ContinuousImprovementOrchestrator()
    
    # Start pipeline
    await orchestrator.start_pipeline()
    
    # Add a high-priority suggestion
    suggestion = ImprovementSuggestion(
        title="High Priority Test",
        description="High priority improvement for integration testing",
        rationale="Should be implemented immediately",
        suggestion_type=ImprovementType.PARAMETER_OPTIMIZATION,
        category="integration_test",
        priority=Priority.HIGH,
        priority_score=95.0,
        risk_level=RiskLevel.LOW,
        implementation_effort=ImplementationComplexity.LOW
    )
    
    orchestrator.pipeline.pending_suggestions.append(suggestion)
    
    # Execute improvement cycle
    results = await orchestrator.execute_improvement_cycle()
    
    # Verify results
    assert results.success is True
    assert len(results.new_tests_created) > 0
    assert len(orchestrator.pipeline.active_improvements) > 0
    
    # Verify suggestion was processed
    assert suggestion.status == SuggestionStatus.TESTING
    assert suggestion.implementation_date is not None
    
    # Stop pipeline
    await orchestrator.stop_pipeline()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])