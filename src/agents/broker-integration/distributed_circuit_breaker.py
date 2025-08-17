"""
Distributed Circuit Breaker System
Future Enhancement: Multi-instance coordination for circuit breakers
"""
import asyncio
import logging
import time
import json
import hashlib
from typing import Dict, List, Optional, Any, Set, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

from circuit_breaker import (
    OandaCircuitBreaker, CircuitBreakerState, CircuitBreakerEvent,
    CircuitBreakerManager
)

logger = logging.getLogger(__name__)


class DistributedState(Enum):
    """Distributed circuit breaker states"""
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    COORDINATION_REQUIRED = "coordination_required"


class ConsensusAlgorithm(Enum):
    """Consensus algorithms for distributed decision making"""
    MAJORITY_VOTE = "majority_vote"
    RAFT = "raft"
    GOSSIP = "gossip"
    WEIGHTED_VOTE = "weighted_vote"


@dataclass
class InstanceInfo:
    """Information about a circuit breaker instance"""
    instance_id: str
    hostname: str
    last_heartbeat: datetime
    circuit_states: Dict[str, str]  # breaker_name -> state
    failure_counts: Dict[str, int]  # breaker_name -> count
    load_factor: float = 1.0  # Load weighting for decisions
    region: str = "default"
    version: str = "1.0.0"
    
    def to_dict(self) -> Dict:
        return {
            'instance_id': self.instance_id,
            'hostname': self.hostname,
            'last_heartbeat': self.last_heartbeat.isoformat(),
            'circuit_states': self.circuit_states,
            'failure_counts': self.failure_counts,
            'load_factor': self.load_factor,
            'region': self.region,
            'version': self.version
        }
        
    @classmethod
    def from_dict(cls, data: Dict) -> 'InstanceInfo':
        return cls(
            instance_id=data['instance_id'],
            hostname=data['hostname'],
            last_heartbeat=datetime.fromisoformat(data['last_heartbeat'].replace('Z', '+00:00')),
            circuit_states=data['circuit_states'],
            failure_counts=data['failure_counts'],
            load_factor=data.get('load_factor', 1.0),
            region=data.get('region', 'default'),
            version=data.get('version', '1.0.0')
        )


@dataclass
class DistributedDecision:
    """Distributed decision for circuit breaker state"""
    breaker_name: str
    decision: CircuitBreakerState
    consensus_reached: bool
    participating_instances: List[str]
    voting_results: Dict[str, str]
    decision_timestamp: datetime
    decision_id: str
    confidence_score: float
    
    def to_dict(self) -> Dict:
        return {
            'breaker_name': self.breaker_name,
            'decision': self.decision.value,
            'consensus_reached': self.consensus_reached,
            'participating_instances': self.participating_instances,
            'voting_results': self.voting_results,
            'decision_timestamp': self.decision_timestamp.isoformat(),
            'decision_id': self.decision_id,
            'confidence_score': self.confidence_score
        }


class DistributedCoordinator:
    """Coordinates circuit breaker decisions across multiple instances"""
    
    def __init__(self, 
                 instance_id: str,
                 hostname: str,
                 consensus_algorithm: ConsensusAlgorithm = ConsensusAlgorithm.MAJORITY_VOTE):
        self.instance_id = instance_id
        self.hostname = hostname
        self.consensus_algorithm = consensus_algorithm
        
        # Instance tracking
        self.known_instances: Dict[str, InstanceInfo] = {}
        self.last_heartbeat_sent = datetime.now(timezone.utc)
        self.heartbeat_interval = timedelta(seconds=30)
        self.instance_timeout = timedelta(minutes=2)
        
        # Decision tracking
        self.recent_decisions: List[DistributedDecision] = []
        self.pending_votes: Dict[str, Dict] = {}  # decision_id -> voting state
        
        # Communication layer (mock for now, would use Redis/etcd/etc in production)
        self.message_bus = MockDistributedMessageBus()
        
        # Callbacks
        self.state_change_callbacks: List[Callable] = []
        
    async def start(self):
        """Start the distributed coordinator"""
        logger.info(f"Starting distributed coordinator for instance {self.instance_id}")
        
        # Register this instance
        await self._register_instance()
        
        # Start background tasks
        asyncio.create_task(self._heartbeat_loop())
        asyncio.create_task(self._cleanup_loop())
        asyncio.create_task(self._message_handler_loop())
        
    async def _register_instance(self):
        """Register this instance with the distributed system"""
        instance_info = InstanceInfo(
            instance_id=self.instance_id,
            hostname=self.hostname,
            last_heartbeat=datetime.now(timezone.utc),
            circuit_states={},
            failure_counts={}
        )
        
        self.known_instances[self.instance_id] = instance_info
        await self.message_bus.publish('instance_register', instance_info.to_dict())
        
    async def _heartbeat_loop(self):
        """Send periodic heartbeats to maintain instance registration"""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval.total_seconds())
                await self._send_heartbeat()
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                
    async def _send_heartbeat(self):
        """Send heartbeat with current circuit breaker states"""
        now = datetime.now(timezone.utc)
        
        if self.instance_id in self.known_instances:
            instance_info = self.known_instances[self.instance_id]
            instance_info.last_heartbeat = now
            
            await self.message_bus.publish('heartbeat', {
                'instance_id': self.instance_id,
                'timestamp': now.isoformat(),
                'circuit_states': instance_info.circuit_states,
                'failure_counts': instance_info.failure_counts
            })
            
        self.last_heartbeat_sent = now
        
    async def _cleanup_loop(self):
        """Clean up expired instances and decisions"""
        while True:
            try:
                await asyncio.sleep(60)  # Clean up every minute
                await self._cleanup_expired_instances()
                await self._cleanup_old_decisions()
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
                
    async def _cleanup_expired_instances(self):
        """Remove instances that haven't sent heartbeats"""
        now = datetime.now(timezone.utc)
        expired_instances = []
        
        for instance_id, info in self.known_instances.items():
            if instance_id != self.instance_id:  # Don't remove self
                if now - info.last_heartbeat > self.instance_timeout:
                    expired_instances.append(instance_id)
                    
        for instance_id in expired_instances:
            logger.info(f"Removing expired instance: {instance_id}")
            del self.known_instances[instance_id]
            
    async def _cleanup_old_decisions(self):
        """Clean up old decisions"""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        self.recent_decisions = [
            d for d in self.recent_decisions 
            if d.decision_timestamp >= cutoff
        ]
        
    async def _message_handler_loop(self):
        """Handle incoming distributed messages"""
        while True:
            try:
                message = await self.message_bus.receive()
                if message:
                    await self._handle_message(message)
                else:
                    await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Message handler error: {e}")
                await asyncio.sleep(1)
                
    async def _handle_message(self, message: Dict):
        """Handle incoming distributed message"""
        message_type = message.get('type')
        data = message.get('data', {})
        
        if message_type == 'instance_register':
            await self._handle_instance_register(data)
        elif message_type == 'heartbeat':
            await self._handle_heartbeat(data)
        elif message_type == 'vote_request':
            await self._handle_vote_request(data)
        elif message_type == 'vote_response':
            await self._handle_vote_response(data)
        elif message_type == 'decision_broadcast':
            await self._handle_decision_broadcast(data)
            
    async def _handle_instance_register(self, data: Dict):
        """Handle new instance registration"""
        instance_info = InstanceInfo.from_dict(data)
        self.known_instances[instance_info.instance_id] = instance_info
        logger.info(f"Registered new instance: {instance_info.instance_id}")
        
    async def _handle_heartbeat(self, data: Dict):
        """Handle heartbeat from another instance"""
        instance_id = data.get('instance_id')
        if instance_id and instance_id in self.known_instances:
            instance_info = self.known_instances[instance_id]
            instance_info.last_heartbeat = datetime.fromisoformat(
                data['timestamp'].replace('Z', '+00:00')
            )
            instance_info.circuit_states = data.get('circuit_states', {})
            instance_info.failure_counts = data.get('failure_counts', {})
            
    async def update_circuit_state(self, 
                                 breaker_name: str,
                                 new_state: CircuitBreakerState,
                                 failure_count: int = 0):
        """Update circuit breaker state and coordinate with other instances"""
        # Update local state
        if self.instance_id in self.known_instances:
            instance_info = self.known_instances[self.instance_id]
            instance_info.circuit_states[breaker_name] = new_state.value
            instance_info.failure_counts[breaker_name] = failure_count
            
        # Check if coordination is needed
        if await self._requires_coordination(breaker_name, new_state):
            decision = await self._coordinate_decision(breaker_name, new_state)
            return decision
        else:
            # Local decision is sufficient
            return DistributedDecision(
                breaker_name=breaker_name,
                decision=new_state,
                consensus_reached=True,
                participating_instances=[self.instance_id],
                voting_results={self.instance_id: new_state.value},
                decision_timestamp=datetime.now(timezone.utc),
                decision_id=str(uuid.uuid4()),
                confidence_score=1.0
            )
            
    async def _requires_coordination(self, 
                                   breaker_name: str,
                                   new_state: CircuitBreakerState) -> bool:
        """Check if state change requires distributed coordination"""
        # Always coordinate for OPEN state changes
        if new_state == CircuitBreakerState.OPEN:
            return True
            
        # Coordinate if multiple instances have this breaker
        instances_with_breaker = [
            instance_id for instance_id, info in self.known_instances.items()
            if breaker_name in info.circuit_states
        ]
        
        return len(instances_with_breaker) > 1
        
    async def _coordinate_decision(self, 
                                 breaker_name: str,
                                 proposed_state: CircuitBreakerState) -> DistributedDecision:
        """Coordinate decision across distributed instances"""
        decision_id = str(uuid.uuid4())
        
        # Request votes from other instances
        vote_request = {
            'decision_id': decision_id,
            'breaker_name': breaker_name,
            'proposed_state': proposed_state.value,
            'requesting_instance': self.instance_id,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        await self.message_bus.publish('vote_request', vote_request)
        
        # Wait for votes
        votes = await self._collect_votes(decision_id, timeout_seconds=10)
        
        # Make decision based on consensus algorithm
        decision = await self._make_consensus_decision(
            breaker_name, proposed_state, votes, decision_id
        )
        
        # Broadcast decision
        await self.message_bus.publish('decision_broadcast', decision.to_dict())
        
        self.recent_decisions.append(decision)
        return decision
        
    async def _collect_votes(self, decision_id: str, timeout_seconds: int = 10) -> Dict[str, str]:
        """Collect votes from other instances"""
        self.pending_votes[decision_id] = {
            'votes': {self.instance_id: 'pending'},
            'start_time': time.perf_counter()
        }
        
        # Wait for votes
        end_time = time.perf_counter() + timeout_seconds
        
        while time.perf_counter() < end_time:
            if decision_id in self.pending_votes:
                votes = self.pending_votes[decision_id]['votes']
                
                # Check if we have enough votes
                total_instances = len(self.known_instances)
                received_votes = len([v for v in votes.values() if v != 'pending'])
                
                if received_votes >= (total_instances // 2 + 1):  # Majority
                    break
                    
            await asyncio.sleep(0.1)
            
        # Return collected votes
        if decision_id in self.pending_votes:
            votes = self.pending_votes[decision_id]['votes']
            del self.pending_votes[decision_id]
            return votes
        else:
            return {self.instance_id: 'timeout'}
            
    async def _handle_vote_request(self, data: Dict):
        """Handle vote request from another instance"""
        decision_id = data['decision_id']
        breaker_name = data['breaker_name']
        proposed_state = CircuitBreakerState(data['proposed_state'])
        requesting_instance = data['requesting_instance']
        
        # Determine our vote
        vote = await self._determine_vote(breaker_name, proposed_state)
        
        # Send vote response
        vote_response = {
            'decision_id': decision_id,
            'voting_instance': self.instance_id,
            'vote': vote.value,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        await self.message_bus.publish('vote_response', vote_response)
        
    async def _handle_vote_response(self, data: Dict):
        """Handle vote response from another instance"""
        decision_id = data['decision_id']
        voting_instance = data['voting_instance']
        vote = data['vote']
        
        if decision_id in self.pending_votes:
            self.pending_votes[decision_id]['votes'][voting_instance] = vote
            
    async def _handle_decision_broadcast(self, data: Dict):
        """Handle decision broadcast from coordinating instance"""
        decision = DistributedDecision(
            breaker_name=data['breaker_name'],
            decision=CircuitBreakerState(data['decision']),
            consensus_reached=data['consensus_reached'],
            participating_instances=data['participating_instances'],
            voting_results=data['voting_results'],
            decision_timestamp=datetime.fromisoformat(
                data['decision_timestamp'].replace('Z', '+00:00')
            ),
            decision_id=data['decision_id'],
            confidence_score=data['confidence_score']
        )
        
        # Apply decision locally if consensus was reached
        if decision.consensus_reached:
            await self._apply_distributed_decision(decision)
            
        self.recent_decisions.append(decision)
        
    async def _determine_vote(self, 
                            breaker_name: str,
                            proposed_state: CircuitBreakerState) -> CircuitBreakerState:
        """Determine how to vote on a proposed state change"""
        # Get local circuit breaker state
        if self.instance_id in self.known_instances:
            instance_info = self.known_instances[self.instance_id]
            current_local_state = instance_info.circuit_states.get(breaker_name)
            
            if current_local_state:
                local_state = CircuitBreakerState(current_local_state)
                
                # Vote logic based on current local state and proposed state
                if proposed_state == CircuitBreakerState.OPEN:
                    # Support opening if we're also experiencing issues
                    if local_state in [CircuitBreakerState.OPEN, CircuitBreakerState.HALF_OPEN]:
                        return CircuitBreakerState.OPEN
                    else:
                        # Check local failure count
                        failure_count = instance_info.failure_counts.get(breaker_name, 0)
                        if failure_count >= 2:  # Some failures locally
                            return CircuitBreakerState.OPEN
                        else:
                            return CircuitBreakerState.HALF_OPEN  # Conservative vote
                            
                elif proposed_state == CircuitBreakerState.CLOSED:
                    # Support closing if we're healthy
                    if local_state == CircuitBreakerState.CLOSED:
                        return CircuitBreakerState.CLOSED
                    else:
                        return CircuitBreakerState.HALF_OPEN  # Gradual recovery
                        
        # Default conservative vote
        return CircuitBreakerState.HALF_OPEN
        
    async def _make_consensus_decision(self,
                                     breaker_name: str,
                                     proposed_state: CircuitBreakerState,
                                     votes: Dict[str, str],
                                     decision_id: str) -> DistributedDecision:
        """Make consensus decision based on collected votes"""
        if self.consensus_algorithm == ConsensusAlgorithm.MAJORITY_VOTE:
            return await self._majority_vote_decision(
                breaker_name, proposed_state, votes, decision_id
            )
        elif self.consensus_algorithm == ConsensusAlgorithm.WEIGHTED_VOTE:
            return await self._weighted_vote_decision(
                breaker_name, proposed_state, votes, decision_id
            )
        else:
            # Default to majority vote
            return await self._majority_vote_decision(
                breaker_name, proposed_state, votes, decision_id
            )
            
    async def _majority_vote_decision(self,
                                    breaker_name: str,
                                    proposed_state: CircuitBreakerState,
                                    votes: Dict[str, str],
                                    decision_id: str) -> DistributedDecision:
        """Make decision based on majority vote"""
        # Count votes
        vote_counts = {}
        valid_votes = []
        
        for instance_id, vote in votes.items():
            if vote not in ['pending', 'timeout']:
                valid_votes.append(vote)
                vote_counts[vote] = vote_counts.get(vote, 0) + 1
                
        # Find majority decision
        total_votes = len(valid_votes)
        majority_threshold = total_votes // 2 + 1
        
        consensus_reached = False
        final_decision = proposed_state  # Default
        confidence_score = 0.0
        
        if total_votes > 0:
            # Find most voted state
            max_votes = max(vote_counts.values())
            most_voted_states = [
                state for state, count in vote_counts.items() 
                if count == max_votes
            ]
            
            if len(most_voted_states) == 1 and max_votes >= majority_threshold:
                consensus_reached = True
                final_decision = CircuitBreakerState(most_voted_states[0])
                confidence_score = max_votes / total_votes
            else:
                # No clear majority, use conservative approach
                if CircuitBreakerState.HALF_OPEN.value in vote_counts:
                    final_decision = CircuitBreakerState.HALF_OPEN
                    confidence_score = 0.5
                    
        return DistributedDecision(
            breaker_name=breaker_name,
            decision=final_decision,
            consensus_reached=consensus_reached,
            participating_instances=list(votes.keys()),
            voting_results=votes,
            decision_timestamp=datetime.now(timezone.utc),
            decision_id=decision_id,
            confidence_score=confidence_score
        )
        
    async def _weighted_vote_decision(self,
                                    breaker_name: str,
                                    proposed_state: CircuitBreakerState,
                                    votes: Dict[str, str],
                                    decision_id: str) -> DistributedDecision:
        """Make decision based on weighted votes (by load factor)"""
        # Calculate weighted votes
        weighted_votes = {}
        total_weight = 0.0
        
        for instance_id, vote in votes.items():
            if vote not in ['pending', 'timeout'] and instance_id in self.known_instances:
                weight = self.known_instances[instance_id].load_factor
                if vote not in weighted_votes:
                    weighted_votes[vote] = 0.0
                weighted_votes[vote] += weight
                total_weight += weight
                
        # Find weighted majority
        consensus_reached = False
        final_decision = proposed_state
        confidence_score = 0.0
        
        if total_weight > 0:
            max_weight = max(weighted_votes.values())
            winning_states = [
                state for state, weight in weighted_votes.items()
                if weight == max_weight
            ]
            
            if len(winning_states) == 1 and max_weight > total_weight / 2:
                consensus_reached = True
                final_decision = CircuitBreakerState(winning_states[0])
                confidence_score = max_weight / total_weight
                
        return DistributedDecision(
            breaker_name=breaker_name,
            decision=final_decision,
            consensus_reached=consensus_reached,
            participating_instances=list(votes.keys()),
            voting_results=votes,
            decision_timestamp=datetime.now(timezone.utc),
            decision_id=decision_id,
            confidence_score=confidence_score
        )
        
    async def _apply_distributed_decision(self, decision: DistributedDecision):
        """Apply distributed decision locally"""
        # Notify callbacks about the decision
        for callback in self.state_change_callbacks:
            try:
                await callback(decision)
            except Exception as e:
                logger.error(f"Decision callback error: {e}")
                
        logger.info(f"Applied distributed decision: {decision.breaker_name} -> {decision.decision.value}")
        
    def add_state_change_callback(self, callback: Callable):
        """Add callback for distributed state changes"""
        self.state_change_callbacks.append(callback)
        
    def get_cluster_status(self) -> Dict[str, Any]:
        """Get status of the distributed cluster"""
        now = datetime.now(timezone.utc)
        
        return {
            'local_instance_id': self.instance_id,
            'total_instances': len(self.known_instances),
            'active_instances': len([
                info for info in self.known_instances.values()
                if (now - info.last_heartbeat).total_seconds() < 120
            ]),
            'consensus_algorithm': self.consensus_algorithm.value,
            'recent_decisions_count': len(self.recent_decisions),
            'pending_votes_count': len(self.pending_votes),
            'instances': {
                instance_id: {
                    'hostname': info.hostname,
                    'last_heartbeat_ago': (now - info.last_heartbeat).total_seconds(),
                    'circuit_count': len(info.circuit_states),
                    'region': info.region
                }
                for instance_id, info in self.known_instances.items()
            }
        }


class MockDistributedMessageBus:
    """Mock message bus for testing (would use Redis/etcd/etc in production)"""
    
    def __init__(self):
        self.messages: List[Dict] = []
        self.subscribers: Dict[str, List[Callable]] = {}
        
    async def publish(self, topic: str, data: Dict):
        """Publish message to topic"""
        message = {
            'type': topic,
            'data': data,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        self.messages.append(message)
        
        # Notify subscribers (in real implementation, this would be handled by message bus)
        if topic in self.subscribers:
            for callback in self.subscribers[topic]:
                try:
                    await callback(message)
                except Exception as e:
                    logger.error(f"Subscriber callback error: {e}")
                    
    async def receive(self) -> Optional[Dict]:
        """Receive next message (simplified for mock)"""
        if self.messages:
            return self.messages.pop(0)
        return None
        
    async def subscribe(self, topic: str, callback: Callable):
        """Subscribe to topic"""
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        self.subscribers[topic].append(callback)


class DistributedCircuitBreakerManager(CircuitBreakerManager):
    """Circuit breaker manager with distributed coordination"""
    
    def __init__(self, 
                 instance_id: Optional[str] = None,
                 hostname: Optional[str] = None):
        super().__init__()
        
        self.instance_id = instance_id or f"instance_{uuid.uuid4().hex[:8]}"
        self.hostname = hostname or "localhost"
        
        # Initialize distributed coordinator
        self.coordinator = DistributedCoordinator(
            self.instance_id, self.hostname
        )
        
        # Add callback to handle distributed decisions
        self.coordinator.add_state_change_callback(self._handle_distributed_decision)
        
    async def start_distributed_coordination(self):
        """Start distributed coordination"""
        await self.coordinator.start()
        
    async def _handle_distributed_decision(self, decision: DistributedDecision):
        """Handle distributed circuit breaker decision"""
        breaker_name = decision.breaker_name
        new_state = decision.decision
        
        if breaker_name in self.circuit_breakers:
            breaker = self.circuit_breakers[breaker_name]
            
            # Apply distributed decision
            if new_state == CircuitBreakerState.CLOSED:
                await breaker.manual_reset(f"Distributed decision: {decision.decision_id}")
            elif new_state == CircuitBreakerState.OPEN:
                # Force open state (simplified)
                breaker.state = CircuitBreakerState.OPEN
                breaker.opened_at = datetime.now(timezone.utc)
                
            logger.info(f"Applied distributed decision for {breaker_name}: {new_state.value}")
            
    async def execute_with_breaker(self,
                                 breaker_name: str,
                                 func: Callable,
                                 *args,
                                 **kwargs) -> Any:
        """Execute with distributed circuit breaker coordination"""
        breaker = self.get_or_create_breaker(breaker_name)
        
        try:
            result = await breaker.call(func, *args, **kwargs)
            
            # Update distributed state on success
            await self.coordinator.update_circuit_state(
                breaker_name, breaker.state, breaker.failure_count
            )
            
            return result
            
        except Exception as e:
            # Update distributed state on failure
            await self.coordinator.update_circuit_state(
                breaker_name, breaker.state, breaker.failure_count
            )
            raise
            
    def get_distributed_status(self) -> Dict[str, Any]:
        """Get distributed circuit breaker status"""
        local_status = self.get_all_status()
        cluster_status = self.coordinator.get_cluster_status()
        
        return {
            'local_circuit_breakers': local_status,
            'distributed_cluster': cluster_status,
            'coordination_active': True
        }


# Global distributed circuit breaker manager
_global_distributed_cb_manager = None


def get_global_distributed_circuit_breaker_manager() -> DistributedCircuitBreakerManager:
    """Get global distributed circuit breaker manager instance"""
    global _global_distributed_cb_manager
    if _global_distributed_cb_manager is None:
        _global_distributed_cb_manager = DistributedCircuitBreakerManager()
    return _global_distributed_cb_manager