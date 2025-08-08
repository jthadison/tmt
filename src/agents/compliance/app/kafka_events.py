"""
Kafka event handling for Compliance Agent

Consumes trading signals and publishes compliance results.
"""

import json
import logging
from typing import Dict, Any, Callable
from datetime import datetime

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
import asyncio

from .models import ValidationRequest, ValidationResult, ViolationType
from .rules_engine import RulesEngine
from .config import get_settings


logger = logging.getLogger(__name__)


class ComplianceKafkaHandler:
    """Handles Kafka events for compliance validation"""
    
    def __init__(self, rules_engine: RulesEngine):
        self.rules_engine = rules_engine
        self.settings = get_settings()
        self.consumer = None
        self.producer = None
        self.running = False
    
    async def start(self):
        """Start Kafka consumer and producer"""
        self.consumer = AIOKafkaConsumer(
            'trading.signals.generated',
            'execution.order.placed',
            'market.position.updated',
            bootstrap_servers=self.settings.kafka_bootstrap_servers,
            group_id=self.settings.kafka_consumer_group,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            enable_auto_commit=True,
            auto_offset_reset='latest'
        )
        
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.settings.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8')
        )
        
        await self.consumer.start()
        await self.producer.start()
        
        self.running = True
        logger.info("Compliance Kafka handler started")
    
    async def stop(self):
        """Stop Kafka consumer and producer"""
        self.running = False
        
        if self.consumer:
            await self.consumer.stop()
        
        if self.producer:
            await self.producer.stop()
        
        logger.info("Compliance Kafka handler stopped")
    
    async def consume_events(self):
        """Main event consumption loop"""
        while self.running:
            try:
                async for message in self.consumer:
                    await self._handle_message(message)
            except Exception as e:
                logger.error(f"Error consuming Kafka messages: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _handle_message(self, message):
        """Handle individual Kafka message"""
        try:
            topic = message.topic
            value = message.value
            
            logger.info(f"Received message from topic {topic}")
            
            if topic == 'trading.signals.generated':
                await self._handle_trading_signal(value)
            elif topic == 'execution.order.placed':
                await self._handle_order_placed(value)
            elif topic == 'market.position.updated':
                await self._handle_position_update(value)
            else:
                logger.warning(f"Unknown topic: {topic}")
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def _handle_trading_signal(self, signal_data: Dict[str, Any]):
        """Handle trading signal for pre-trade validation"""
        try:
            # Extract validation request from signal
            account_id = signal_data.get('account_id')
            trade_order_data = signal_data.get('trade_order', {})
            
            if not account_id or not trade_order_data:
                logger.warning("Incomplete trading signal data")
                return
            
            # Create validation request (simplified - would need proper data mapping)
            validation_request = ValidationRequest(
                account_id=account_id,
                trade_order=trade_order_data,
                current_positions=signal_data.get('current_positions', []),
                upcoming_news=signal_data.get('upcoming_news', [])
            )
            
            # Validate the trade
            # Note: This is simplified - would need actual account fetching
            result = await self._validate_trade_from_signal(validation_request)
            
            # Publish validation result
            await self._publish_validation_result(result)
            
        except Exception as e:
            logger.error(f"Error handling trading signal: {e}")
    
    async def _handle_order_placed(self, order_data: Dict[str, Any]):
        """Handle order placement event for position tracking"""
        try:
            account_id = order_data.get('account_id')
            order_id = order_data.get('order_id')
            
            logger.info(f"Order placed for account {account_id}, order {order_id}")
            
            # Update position tracking
            # This would update the database with new position information
            
        except Exception as e:
            logger.error(f"Error handling order placed: {e}")
    
    async def _handle_position_update(self, position_data: Dict[str, Any]):
        """Handle position update for P&L tracking"""
        try:
            account_id = position_data.get('account_id')
            position_id = position_data.get('position_id')
            realized_pnl = position_data.get('realized_pnl', 0.0)
            unrealized_pnl = position_data.get('unrealized_pnl', 0.0)
            
            logger.info(f"Position updated for account {account_id}")
            
            # Update account P&L and check compliance
            # This would trigger real-time compliance monitoring
            
        except Exception as e:
            logger.error(f"Error handling position update: {e}")
    
    async def _validate_trade_from_signal(self, request: ValidationRequest) -> ValidationResult:
        """Validate trade from signal data (simplified implementation)"""
        # This is a simplified implementation
        # In reality, would fetch full account data from database
        return ValidationResult(
            is_valid=True,
            compliance_status="compliant",
            violations=[],
            warnings=[],
            reason="Pre-validation via Kafka signal",
            details={"source": "kafka_signal"}
        )
    
    async def _publish_validation_result(self, result: ValidationResult):
        """Publish validation result to appropriate topic"""
        try:
            if result.is_valid:
                topic = 'compliance.validation.passed'
            else:
                topic = 'compliance.violation.detected'
            
            message_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "validation_result": result.dict(),
                "source": "compliance-agent"
            }
            
            await self.producer.send(topic, message_data)
            logger.info(f"Published validation result to {topic}")
            
        except Exception as e:
            logger.error(f"Error publishing validation result: {e}")
    
    async def publish_compliance_violation(
        self,
        account_id: str,
        violation_type: ViolationType,
        details: Dict[str, Any]
    ):
        """Publish compliance violation event"""
        try:
            message_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "account_id": account_id,
                "violation_type": violation_type.value,
                "details": details,
                "severity": "critical" if violation_type in [
                    ViolationType.DAILY_LOSS_EXCEEDED,
                    ViolationType.MAX_DRAWDOWN_EXCEEDED
                ] else "warning",
                "source": "compliance-agent"
            }
            
            await self.producer.send('compliance.violation.detected', message_data)
            logger.warning(f"Published compliance violation for account {account_id}: {violation_type.value}")
            
        except Exception as e:
            logger.error(f"Error publishing compliance violation: {e}")
    
    async def publish_account_suspended(
        self,
        account_id: str,
        reason: str,
        details: Dict[str, Any]
    ):
        """Publish account suspension event"""
        try:
            message_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "account_id": account_id,
                "reason": reason,
                "details": details,
                "action": "suspend_trading",
                "source": "compliance-agent"
            }
            
            await self.producer.send('compliance.account.suspended', message_data)
            logger.critical(f"Published account suspension for {account_id}: {reason}")
            
        except Exception as e:
            logger.error(f"Error publishing account suspension: {e}")


# Global Kafka handler instance
kafka_handler = None


async def start_kafka_handler(rules_engine: RulesEngine):
    """Start the global Kafka handler"""
    global kafka_handler
    kafka_handler = ComplianceKafkaHandler(rules_engine)
    await kafka_handler.start()
    
    # Start consuming in background
    asyncio.create_task(kafka_handler.consume_events())


async def stop_kafka_handler():
    """Stop the global Kafka handler"""
    global kafka_handler
    if kafka_handler:
        await kafka_handler.stop()


def get_kafka_handler() -> ComplianceKafkaHandler:
    """Get the global Kafka handler"""
    global kafka_handler
    return kafka_handler