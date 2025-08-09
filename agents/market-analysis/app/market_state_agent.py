"""
Market State Detection Agent - Main integration point for all market state analysis
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import asyncio
import json
from dataclasses import asdict
import logging

from .market_state_detector import MarketRegimeClassifier, MarketState
from .session_detector import TradingSessionDetector
from .economic_event_monitor import EconomicEventMonitor
from .correlation_analyzer import CorrelationAnalyzer
from .volatility_analyzer import VolatilityAnalyzer
from .parameter_adjustment_engine import ParameterAdjustmentEngine, TradingParameters

logger = logging.getLogger(__name__)


class MarketStateAgent:
    """
    Main Market State Detection Agent that coordinates all analysis components
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Market State Agent
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        
        # Initialize components
        self.regime_classifier = MarketRegimeClassifier()
        self.session_detector = TradingSessionDetector()
        self.event_monitor = EconomicEventMonitor(
            api_key=self.config.get('economic_api_key')
        )
        self.correlation_analyzer = CorrelationAnalyzer()
        self.volatility_analyzer = VolatilityAnalyzer()
        self.parameter_engine = ParameterAdjustmentEngine()
        
        # State storage
        self.current_state: Optional[MarketState] = None
        self.state_history: List[MarketState] = []
        self.max_history_size = 100
        
        # Event publishing
        self.event_publishers = []
        
        # Update intervals (seconds)
        self.update_intervals = {
            'regime': 300,  # 5 minutes
            'session': 60,   # 1 minute
            'events': 900,   # 15 minutes
            'correlation': 600,  # 10 minutes
            'volatility': 300    # 5 minutes
        }
        
        self.last_updates = {
            'regime': None,
            'session': None,
            'events': None,
            'correlation': None,
            'volatility': None
        }
    
    async def analyze_market_state(
        self,
        price_data: Dict[str, List[Dict]],
        volume_data: Optional[Dict[str, List[Dict]]] = None
    ) -> MarketState:
        """
        Perform comprehensive market state analysis
        
        Args:
            price_data: Dictionary of instrument price data
            volume_data: Optional volume data
            
        Returns:
            Complete market state
        """
        current_time = datetime.now(timezone.utc)
        
        # Get primary symbol for analysis (default to EURUSD)
        primary_symbol = self.config.get('primary_symbol', 'EURUSD')
        primary_price_data = price_data.get(primary_symbol, [])
        primary_volume_data = volume_data.get(primary_symbol, []) if volume_data else []
        
        # 1. Analyze market regime
        regime_analysis = self.regime_classifier.classify_market_regime(
            primary_price_data,
            primary_volume_data
        )
        
        # 2. Detect trading session
        session = self.session_detector.detect_current_session(current_time)
        
        # 3. Get economic events
        economic_events = await self._get_economic_events()
        
        # 4. Analyze correlations
        correlation_analysis = self._analyze_correlations(price_data)
        
        # 5. Analyze volatility
        volatility_metrics = self.volatility_analyzer.calculate_comprehensive_volatility(
            primary_price_data
        )
        
        # 6. Build comprehensive market state
        market_state_data = {
            'regime': regime_analysis['regime'],
            'regime_confidence': regime_analysis['confidence'],
            'session': {
                'name': session.name,
                'type': session.type,
                'expected_volatility': session.expected_volatility,
                'is_peak': session.is_peak
            },
            'volatility_regime': volatility_metrics.volatility_regime.value,
            'volatility_percentile': volatility_metrics.volatility_percentile,
            'economic_events': economic_events,
            'correlation_breakdown': correlation_analysis.get('breakdown_analysis'),
            'indicators': regime_analysis['indicators']
        }
        
        # 7. Adjust parameters based on market state
        parameter_adjustment = self.parameter_engine.adjust_parameters_for_market_state(
            market_state_data
        )
        
        # 8. Create market state object
        market_state = MarketState(
            regime=regime_analysis['regime'],
            confidence=regime_analysis['confidence'],
            session=asdict(session),
            volatility={
                'regime': volatility_metrics.volatility_regime.value,
                'percentile': volatility_metrics.volatility_percentile,
                'atr_values': volatility_metrics.atr_values,
                'historical': volatility_metrics.historical_volatility,
                'expansion': volatility_metrics.expansion_detected,
                'contraction': volatility_metrics.contraction_detected
            },
            correlations=correlation_analysis,
            economic_events=economic_events,
            timestamp=current_time,
            indicators=regime_analysis['indicators'],
            parameter_adjustments=asdict(parameter_adjustment.adjusted_params)
        )
        
        # 9. Check for state changes and publish events
        await self._check_state_changes(market_state)
        
        # 10. Update state
        self.current_state = market_state
        self._add_to_history(market_state)
        
        return market_state
    
    async def _get_economic_events(self) -> List[Dict[str, Any]]:
        """
        Get upcoming economic events
        
        Returns:
            List of economic events
        """
        try:
            events = await self.event_monitor.get_upcoming_events(hours_ahead=24)
            
            # Convert to dict format
            event_dicts = []
            for event in events:
                event_dicts.append({
                    'event_name': event.event_name,
                    'country': event.country,
                    'currency': event.currency,
                    'event_time': event.event_time.isoformat(),
                    'importance': event.importance.value,
                    'restriction_window': {
                        'start': event.restriction_window['start'].isoformat(),
                        'end': event.restriction_window['end'].isoformat()
                    },
                    'affected_pairs': event.affected_pairs
                })
            
            return event_dicts
        except Exception as e:
            logger.error(f"Failed to get economic events: {e}")
            return []
    
    def _analyze_correlations(
        self, 
        price_data: Dict[str, List[Dict]]
    ) -> Dict[str, Any]:
        """
        Analyze correlations between instruments
        
        Args:
            price_data: Dictionary of instrument price data
            
        Returns:
            Correlation analysis results
        """
        try:
            # Calculate correlation matrix
            correlation_matrix = self.correlation_analyzer.calculate_correlation_matrix(
                price_data
            )
            
            # Detect anomalies
            anomalies = self.correlation_analyzer.detect_correlation_anomalies(
                correlation_matrix
            )
            
            # Analyze breakdown
            breakdown_analysis = self.correlation_analyzer.analyze_correlation_breakdown(
                anomalies
            )
            
            # Update history
            self.correlation_analyzer.update_correlation_history(correlation_matrix)
            
            return {
                'matrix': correlation_matrix,
                'anomalies': [
                    {
                        'pair1': a.pair1,
                        'pair2': a.pair2,
                        'current': a.current_correlation,
                        'historical': a.historical_correlation,
                        'deviation': a.deviation,
                        'severity': a.severity
                    }
                    for a in anomalies[:5]  # Top 5 anomalies
                ],
                'breakdown_analysis': breakdown_analysis
            }
        except Exception as e:
            logger.error(f"Correlation analysis failed: {e}")
            return {
                'matrix': {},
                'anomalies': [],
                'breakdown_analysis': {'severity': 'none'}
            }
    
    async def _check_state_changes(self, new_state: MarketState):
        """
        Check for significant state changes and publish events
        
        Args:
            new_state: New market state
        """
        if not self.current_state:
            # First state, publish initial event
            await self._publish_state_change_event(None, new_state)
            return
        
        # Check for regime change
        if new_state.regime != self.current_state.regime:
            await self._publish_state_change_event(
                self.current_state,
                new_state,
                change_type='regime'
            )
        
        # Check for volatility regime change
        if new_state.volatility['regime'] != self.current_state.volatility['regime']:
            await self._publish_state_change_event(
                self.current_state,
                new_state,
                change_type='volatility'
            )
        
        # Check for session change
        if new_state.session['name'] != self.current_state.session['name']:
            await self._publish_state_change_event(
                self.current_state,
                new_state,
                change_type='session'
            )
        
        # Check for correlation breakdown
        new_breakdown = new_state.correlations.get('breakdown_analysis', {})
        old_breakdown = self.current_state.correlations.get('breakdown_analysis', {})
        
        if new_breakdown.get('severity') != old_breakdown.get('severity'):
            await self._publish_state_change_event(
                self.current_state,
                new_state,
                change_type='correlation'
            )
    
    async def _publish_state_change_event(
        self,
        old_state: Optional[MarketState],
        new_state: MarketState,
        change_type: str = 'initial'
    ):
        """
        Publish market state change event
        
        Args:
            old_state: Previous state (None for initial)
            new_state: New state
            change_type: Type of change
        """
        event = {
            'event_type': 'market.state.changed',
            'change_type': change_type,
            'timestamp': new_state.timestamp.isoformat(),
            'new_state': {
                'regime': new_state.regime,
                'confidence': new_state.confidence,
                'session': new_state.session['name'],
                'volatility_regime': new_state.volatility['regime']
            }
        }
        
        if old_state:
            event['previous_state'] = {
                'regime': old_state.regime,
                'confidence': old_state.confidence,
                'session': old_state.session['name'],
                'volatility_regime': old_state.volatility['regime']
            }
        
        # Add parameter changes
        event['parameter_adjustments'] = new_state.parameter_adjustments
        
        # Publish to all registered publishers
        for publisher in self.event_publishers:
            try:
                await publisher(event)
            except Exception as e:
                logger.error(f"Failed to publish event: {e}")
    
    def register_event_publisher(self, publisher):
        """
        Register an event publisher callback
        
        Args:
            publisher: Async callable that accepts event dict
        """
        self.event_publishers.append(publisher)
    
    def check_trading_restrictions(
        self, 
        symbol: str,
        current_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Check if trading is restricted for a symbol
        
        Args:
            symbol: Trading symbol
            current_time: Current time (defaults to now)
            
        Returns:
            Restriction information
        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        
        restrictions = []
        
        # Check economic event restrictions
        event_restriction = self.event_monitor.is_trading_restricted(symbol, current_time)
        if event_restriction['restricted']:
            restrictions.append({
                'type': 'economic_event',
                'reason': event_restriction['reason'],
                'ends': event_restriction.get('restriction_ends')
            })
        
        # Check volatility restrictions
        if self.current_state and self.current_state.volatility['regime'] == 'extreme':
            restrictions.append({
                'type': 'volatility',
                'reason': 'Extreme volatility detected',
                'ends': None
            })
        
        # Check correlation breakdown restrictions
        if self.current_state:
            breakdown = self.current_state.correlations.get('breakdown_analysis', {})
            if breakdown.get('severity') in ['extreme', 'high']:
                restrictions.append({
                    'type': 'correlation',
                    'reason': f"Correlation breakdown: {breakdown.get('severity')}",
                    'ends': None
                })
        
        return {
            'restricted': len(restrictions) > 0,
            'restrictions': restrictions
        }
    
    def get_current_parameters(self) -> TradingParameters:
        """
        Get current adjusted trading parameters
        
        Returns:
            Current trading parameters
        """
        return self.parameter_engine.current_parameters
    
    def get_state_summary(self) -> Dict[str, Any]:
        """
        Get summary of current market state
        
        Returns:
            State summary
        """
        if not self.current_state:
            return {
                'status': 'no_data',
                'message': 'No market state available'
            }
        
        state = self.current_state
        
        return {
            'status': 'active',
            'timestamp': state.timestamp.isoformat(),
            'market_regime': {
                'type': state.regime,
                'confidence': state.confidence,
                'characteristics': self.regime_classifier.get_regime_characteristics(state.regime)
            },
            'session': state.session,
            'volatility': {
                'regime': state.volatility['regime'],
                'percentile': state.volatility['percentile'],
                'expansion': state.volatility['expansion'],
                'contraction': state.volatility['contraction']
            },
            'correlations': {
                'anomaly_count': len(state.correlations.get('anomalies', [])),
                'breakdown_severity': state.correlations.get('breakdown_analysis', {}).get('severity', 'none')
            },
            'economic_events': {
                'upcoming_count': len(state.economic_events),
                'high_impact_count': sum(1 for e in state.economic_events if e.get('importance') == 'high')
            },
            'current_parameters': asdict(self.get_current_parameters()),
            'parameter_adjustments': self.parameter_engine.get_adjustment_summary()
        }
    
    def _add_to_history(self, state: MarketState):
        """
        Add state to history
        
        Args:
            state: Market state to add
        """
        self.state_history.append(state)
        
        # Trim history if needed
        if len(self.state_history) > self.max_history_size:
            self.state_history = self.state_history[-self.max_history_size:]
    
    async def start_monitoring(self):
        """Start continuous market state monitoring"""
        logger.info("Starting market state monitoring")
        
        while True:
            try:
                # This would fetch real market data in production
                # For now, it's a placeholder for the monitoring loop
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(60)