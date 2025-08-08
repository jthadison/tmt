"""Tests for entity management functionality."""

import pytest
from datetime import datetime
from uuid import uuid4

from app.models import (
    LegalEntityCreate, EntityType, EntityStatus,
    DecisionLog, ActionType
)


@pytest.mark.asyncio
async def test_create_entity(entity_manager):
    """Test creating a new legal entity."""
    entity_data = LegalEntityCreate(
        entity_name="Test Corp",
        entity_type=EntityType.CORPORATION,
        jurisdiction="US",
        registered_address="456 Business Blvd",
        incorporation_date=datetime(2024, 6, 1)
    )
    
    entity = await entity_manager.create_entity(entity_data)
    
    assert entity.entity_name == "Test Corp"
    assert entity.entity_type == EntityType.CORPORATION
    assert entity.jurisdiction == "US"
    assert entity.status == EntityStatus.ACTIVE
    assert "personality_profile" in entity.metadata
    assert "risk_tolerance" in entity.metadata


@pytest.mark.asyncio
async def test_get_entity(entity_manager, sample_entity):
    """Test retrieving an entity."""
    entity = await entity_manager.get_entity(sample_entity.entity_id)
    
    assert entity is not None
    assert entity.entity_id == sample_entity.entity_id
    assert entity.entity_name == sample_entity.entity_name


@pytest.mark.asyncio
async def test_list_entities(entity_manager, multiple_entities):
    """Test listing entities with filters."""
    # List all entities
    all_entities = await entity_manager.list_entities()
    assert len(all_entities) == len(multiple_entities)
    
    # Filter by status
    active_entities = await entity_manager.list_entities(status=EntityStatus.ACTIVE)
    assert len(active_entities) == len(multiple_entities)
    
    # Filter by jurisdiction
    us_entities = await entity_manager.list_entities(jurisdiction="US")
    assert len(us_entities) == len(multiple_entities)


@pytest.mark.asyncio
async def test_update_entity_status(entity_manager, sample_entity):
    """Test updating entity status."""
    success = await entity_manager.update_entity_status(
        sample_entity.entity_id,
        EntityStatus.SUSPENDED,
        "Compliance review required"
    )
    
    assert success is True
    
    # Verify status was updated
    entity = await entity_manager.get_entity(sample_entity.entity_id)
    assert entity.status == EntityStatus.SUSPENDED


@pytest.mark.asyncio
async def test_ensure_entity_independence(entity_manager, sample_entity):
    """Test decision independence mechanism."""
    base_decision = {
        "action": "buy",
        "symbol": "EURUSD",
        "size": 0.1,
        "analysis": {
            "confidence": 75.0,
            "signals": ["MA_cross", "RSI_oversold"]
        }
    }
    
    result = await entity_manager.ensure_entity_independence(
        sample_entity.entity_id,
        "trade_entry",
        base_decision
    )
    
    assert "decision" in result
    assert "rationale" in result
    assert "delay_ms" in result
    assert result["delay_ms"] > 0
    assert result["entity_id"] == str(sample_entity.entity_id)
    
    # Verify decision was logged
    decision_log = entity_manager.db.query(DecisionLog).filter(
        DecisionLog.entity_id == sample_entity.entity_id
    ).first()
    
    assert decision_log is not None
    assert decision_log.decision_type == "trade_entry"
    assert decision_log.personality_profile == "moderate"


@pytest.mark.asyncio
async def test_check_entity_compliance(entity_manager, sample_entity):
    """Test entity compliance checking."""
    compliance = await entity_manager.check_entity_compliance(sample_entity.entity_id)
    
    assert compliance.entity_id == sample_entity.entity_id
    assert compliance.entity_name == sample_entity.entity_name
    assert isinstance(compliance.independence_score, float)
    assert 0 <= compliance.independence_score <= 1
    assert isinstance(compliance.issues, list)


@pytest.mark.asyncio
async def test_personality_variation(entity_manager, multiple_entities):
    """Test that different entities produce different decisions."""
    base_decision = {
        "action": "buy",
        "symbol": "GBPUSD",
        "size": 0.2,
        "entry": 1.2500
    }
    
    decisions = []
    for entity in multiple_entities:
        result = await entity_manager.ensure_entity_independence(
            entity.entity_id,
            "trade_entry",
            base_decision
        )
        decisions.append(result)
    
    # Verify decisions are different
    sizes = [d["decision"].get("size") for d in decisions]
    delays = [d["delay_ms"] for d in decisions]
    
    # At least some variation should exist
    assert len(set(sizes)) > 1 or len(set(delays)) > 1
    
    # Check personality influence
    for i, decision in enumerate(decisions):
        personality = multiple_entities[i].metadata["personality_profile"]
        if personality == "conservative":
            assert decision["decision"]["size"] <= base_decision["size"]
        elif personality == "aggressive":
            assert decision["decision"]["size"] >= base_decision["size"] * 0.9


@pytest.mark.asyncio
async def test_registration_number_generation(entity_manager):
    """Test automatic registration number generation."""
    entity_data = LegalEntityCreate(
        entity_name="Auto Reg Corp",
        entity_type=EntityType.CORPORATION,
        jurisdiction="UK",
        registered_address="10 Downing St",
        incorporation_date=datetime(2024, 1, 1)
    )
    
    entity = await entity_manager.create_entity(entity_data)
    
    assert entity.registration_number is not None
    assert entity.registration_number.startswith("REG-")
    assert len(entity.registration_number) > 10


@pytest.mark.asyncio
async def test_duplicate_entity_handling(entity_manager):
    """Test handling of duplicate entities."""
    entity_data = LegalEntityCreate(
        entity_name="Unique Corp",
        entity_type=EntityType.CORPORATION,
        jurisdiction="US",
        registration_number="UNIQUE-123",
        registered_address="123 Unique St",
        incorporation_date=datetime(2024, 1, 1)
    )
    
    # Create first entity
    entity1 = await entity_manager.create_entity(entity_data)
    assert entity1 is not None
    
    # Try to create duplicate with same registration number
    with pytest.raises(ValueError):
        await entity_manager.create_entity(entity_data)