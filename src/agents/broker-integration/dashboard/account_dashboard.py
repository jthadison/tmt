"""
Account Dashboard Components
Story 8.2 - Task 5: Create dashboard components (AC: 1-8)
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass, asdict
from enum import Enum
import json

from ..account_manager import OandaAccountManager, AccountSummary
from ..instrument_service import OandaInstrumentService, InstrumentSpread
from ..realtime_updates import AccountUpdateService, AccountUpdate, UpdateType
from ..historical_data import HistoricalDataService, BalanceHistoryData, TimeInterval

logger = logging.getLogger(__name__)

class WidgetStatus(Enum):
    LOADING = "loading"
    READY = "ready"
    ERROR = "error"
    UPDATING = "updating"

@dataclass
class DashboardWidget:
    """Base dashboard widget"""
    widget_id: str
    title: str
    status: WidgetStatus
    last_update: Optional[datetime]
    data: Dict[str, Any]
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'widget_id': self.widget_id,
            'title': self.title,
            'status': self.status.value,
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'data': self.data,
            'error_message': self.error_message
        }

@dataclass
class AccountSummaryWidget(DashboardWidget):
    """Account summary widget showing balance, P&L, and equity"""
    
    @classmethod
    def from_account_summary(cls, summary: AccountSummary) -> 'AccountSummaryWidget':
        """Create widget from account summary"""
        data = {
            'account_id': summary.account_id,
            'currency': summary.currency.value,
            'balance': float(summary.balance),
            'unrealized_pl': float(summary.unrealized_pl),
            'realized_pl': float(summary.realized_pl),
            'equity': float(summary.account_equity),
            'nav': float(summary.nav),
            'leverage': summary.leverage,
            'pl_color': 'green' if summary.unrealized_pl >= 0 else 'red',
            'equity_change': float(summary.unrealized_pl),
            'equity_change_percent': float((summary.unrealized_pl / summary.balance) * 100) if summary.balance != 0 else 0
        }
        
        return cls(
            widget_id="account_summary",
            title="Account Summary",
            status=WidgetStatus.READY,
            last_update=datetime.utcnow(),
            data=data
        )

@dataclass
class MarginStatusWidget(DashboardWidget):
    """Margin status widget showing margin usage and safety levels"""
    
    @classmethod
    def from_account_summary(cls, summary: AccountSummary) -> 'MarginStatusWidget':
        """Create widget from account summary"""
        margin_level = summary.calculate_margin_level()
        
        # Determine margin status color
        if summary.is_margin_closeout():
            status_color = 'red'
            status_text = 'DANGER'
        elif summary.is_margin_call():
            status_color = 'orange' 
            status_text = 'WARNING'
        elif margin_level < 200:
            status_color = 'yellow'
            status_text = 'CAUTION'
        else:
            status_color = 'green'
            status_text = 'SAFE'
        
        data = {
            'margin_used': float(summary.margin_used),
            'margin_available': float(summary.margin_available),
            'margin_level': float(margin_level),
            'margin_level_percent': float(margin_level),
            'free_margin': float(summary.calculate_free_margin()),
            'margin_call_level': float(summary.margin_call_percent),
            'margin_closeout_level': float(summary.margin_closeout_percent),
            'status_color': status_color,
            'status_text': status_text,
            'is_margin_call': summary.is_margin_call(),
            'is_margin_closeout': summary.is_margin_closeout(),
            'margin_usage_percent': float((summary.margin_used / (summary.margin_used + summary.margin_available)) * 100) if (summary.margin_used + summary.margin_available) != 0 else 0
        }
        
        return cls(
            widget_id="margin_status",
            title="Margin Status",
            status=WidgetStatus.READY,
            last_update=datetime.utcnow(),
            data=data
        )

@dataclass
class PositionCounterWidget(DashboardWidget):
    """Position and order counter widget"""
    
    @classmethod
    def from_account_summary(cls, summary: AccountSummary) -> 'PositionCounterWidget':
        """Create widget from account summary"""
        data = {
            'open_positions': summary.open_position_count,
            'pending_orders': summary.pending_order_count,
            'total_trades': summary.open_position_count + summary.pending_order_count,
            'positions_color': 'blue' if summary.open_position_count > 0 else 'gray',
            'orders_color': 'orange' if summary.pending_order_count > 0 else 'gray'
        }
        
        return cls(
            widget_id="position_counter",
            title="Positions & Orders",
            status=WidgetStatus.READY,
            last_update=datetime.utcnow(),
            data=data
        )

@dataclass
class InstrumentSpreadWidget(DashboardWidget):
    """Instrument spread table widget"""
    
    @classmethod
    def from_spreads(cls, spreads: Dict[str, InstrumentSpread]) -> 'InstrumentSpreadWidget':
        """Create widget from instrument spreads"""
        spread_data = []
        for instrument, spread in spreads.items():
            spread_data.append({
                'instrument': instrument,
                'display_name': instrument.replace('_', '/'),
                'bid': float(spread.bid),
                'ask': float(spread.ask),
                'spread': float(spread.spread),
                'spread_pips': float(spread.spread_pips),
                'tradeable': spread.tradeable,
                'liquidity': spread.liquidity,
                'status_color': 'green' if spread.tradeable else 'red',
                'spread_color': 'green' if spread.spread_pips <= 2 else 'orange' if spread.spread_pips <= 5 else 'red'
            })
        
        # Sort by spread (best spreads first)
        spread_data.sort(key=lambda x: x['spread_pips'])
        
        data = {
            'spreads': spread_data,
            'total_instruments': len(spread_data),
            'tradeable_count': sum(1 for s in spread_data if s['tradeable']),
            'average_spread': sum(s['spread_pips'] for s in spread_data) / len(spread_data) if spread_data else 0
        }
        
        return cls(
            widget_id="instrument_spreads",
            title="Instrument Spreads",
            status=WidgetStatus.READY,
            last_update=datetime.utcnow(),
            data=data
        )

@dataclass
class BalanceHistoryWidget(DashboardWidget):
    """Balance history chart widget"""
    
    @classmethod
    def from_history_data(cls, history_data: BalanceHistoryData) -> 'BalanceHistoryWidget':
        """Create widget from balance history"""
        chart_data = history_data.to_chart_format()
        
        # Calculate additional metrics
        if history_data.data_points:
            start_balance = float(history_data.data_points[0].balance)
            end_balance = float(history_data.data_points[-1].balance)
            total_return = end_balance - start_balance
            total_return_percent = (total_return / start_balance * 100) if start_balance != 0 else 0
        else:
            start_balance = end_balance = total_return = total_return_percent = 0
        
        data = {
            'chart_data': chart_data,
            'period_days': (history_data.end_date - history_data.start_date).days,
            'start_balance': start_balance,
            'end_balance': end_balance,
            'total_return': total_return,
            'total_return_percent': total_return_percent,
            'max_drawdown': float(history_data.metrics.max_drawdown_percent),
            'volatility': float(history_data.volatility),
            'trend': history_data.trend.value,
            'data_points_count': len(history_data.data_points),
            'return_color': 'green' if total_return >= 0 else 'red'
        }
        
        return cls(
            widget_id="balance_history",
            title="Balance History (30 Days)",
            status=WidgetStatus.READY,
            last_update=datetime.utcnow(),
            data=data
        )

@dataclass
class EquityCurveWidget(DashboardWidget):
    """Equity curve visualization widget"""
    
    @classmethod
    def from_history_data(cls, history_data: BalanceHistoryData) -> 'EquityCurveWidget':
        """Create widget from balance history"""
        # Prepare equity curve data
        equity_data = []
        peak_equity = 0
        drawdown_data = []
        
        for point in history_data.data_points:
            equity_value = float(point.equity)
            peak_equity = max(peak_equity, equity_value)
            
            drawdown_percent = 0
            if peak_equity > 0:
                drawdown_percent = ((peak_equity - equity_value) / peak_equity) * 100
            
            equity_data.append({
                'timestamp': int(point.timestamp.timestamp() * 1000),
                'equity': equity_value,
                'balance': float(point.balance),
                'unrealized_pl': float(point.unrealized_pl)
            })
            
            drawdown_data.append({
                'timestamp': int(point.timestamp.timestamp() * 1000),
                'drawdown': drawdown_percent
            })
        
        data = {
            'equity_curve': equity_data,
            'drawdown_curve': drawdown_data,
            'performance_metrics': asdict(history_data.metrics),
            'trend_direction': history_data.trend.value,
            'volatility_percent': float(history_data.volatility),
            'chart_config': {
                'type': 'line',
                'responsive': True,
                'scales': {
                    'x': {'type': 'time'},
                    'y': {'beginAtZero': False}
                }
            }
        }
        
        return cls(
            widget_id="equity_curve",
            title="Equity Curve & Performance",
            status=WidgetStatus.READY,
            last_update=datetime.utcnow(),
            data=data
        )

class AccountDashboard:
    """Main account dashboard coordinating all widgets"""
    
    def __init__(self, 
                 account_manager: OandaAccountManager,
                 instrument_service: OandaInstrumentService,
                 update_service: AccountUpdateService,
                 historical_service: HistoricalDataService):
        
        self.account_manager = account_manager
        self.instrument_service = instrument_service
        self.update_service = update_service
        self.historical_service = historical_service
        
        # Widget storage
        self.widgets: Dict[str, DashboardWidget] = {}
        
        # Update callbacks
        self.update_callbacks: List[callable] = []
        
        # Configuration
        self.major_pairs = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'USD_CHF', 'AUD_USD', 'USD_CAD', 'NZD_USD']
        self.auto_refresh_interval = 30  # seconds
        
        # Metrics
        self.metrics = {
            'widget_updates': 0,
            'update_errors': 0,
            'last_full_refresh': None,
            'refresh_duration': 0
        }
        
        # Subscribe to real-time updates
        self._setup_update_subscriptions()
    
    def _setup_update_subscriptions(self):
        """Set up subscriptions to real-time updates"""
        self.update_service.subscribe_to_updates(
            UpdateType.ACCOUNT_SUMMARY,
            self._handle_account_update
        )
        self.update_service.subscribe_to_updates(
            UpdateType.BALANCE,
            self._handle_balance_update
        )
        self.update_service.subscribe_to_updates(
            UpdateType.MARGIN,
            self._handle_margin_update
        )
        self.update_service.subscribe_to_updates(
            UpdateType.SPREADS,
            self._handle_spreads_update
        )
        self.update_service.subscribe_to_updates(
            UpdateType.POSITIONS,
            self._handle_positions_update
        )
    
    async def initialize(self):
        """Initialize the dashboard with initial data"""
        logger.info("Initializing account dashboard")
        
        try:
            # Load initial data for all widgets
            await self.refresh_all_widgets()
            
            # Start watching major pairs for spreads
            for pair in self.major_pairs:
                self.update_service.watch_instrument(pair)
            
            logger.info("Account dashboard initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize dashboard: {e}")
            raise
    
    async def refresh_all_widgets(self) -> Dict[str, DashboardWidget]:
        """Refresh all dashboard widgets with latest data"""
        start_time = datetime.utcnow()
        
        try:
            # Fetch all required data
            summary = await self.account_manager.get_account_summary(use_cache=False)
            spreads = await self.instrument_service.get_current_prices(self.major_pairs)
            history_data = await self.historical_service.get_balance_history(days=30)
            
            # Update all widgets
            self.widgets['account_summary'] = AccountSummaryWidget.from_account_summary(summary)
            self.widgets['margin_status'] = MarginStatusWidget.from_account_summary(summary)
            self.widgets['position_counter'] = PositionCounterWidget.from_account_summary(summary)
            self.widgets['instrument_spreads'] = InstrumentSpreadWidget.from_spreads(spreads)
            self.widgets['balance_history'] = BalanceHistoryWidget.from_history_data(history_data)
            self.widgets['equity_curve'] = EquityCurveWidget.from_history_data(history_data)
            
            # Update metrics
            self.metrics['last_full_refresh'] = datetime.utcnow()
            self.metrics['refresh_duration'] = (datetime.utcnow() - start_time).total_seconds()
            self.metrics['widget_updates'] += len(self.widgets)
            
            # Notify callbacks
            await self._notify_update_callbacks('full_refresh', self.widgets)
            
            return self.widgets
            
        except Exception as e:
            self.metrics['update_errors'] += 1
            logger.error(f"Failed to refresh dashboard widgets: {e}")
            
            # Set error status on all widgets
            for widget_id in ['account_summary', 'margin_status', 'position_counter', 
                            'instrument_spreads', 'balance_history', 'equity_curve']:
                if widget_id not in self.widgets:
                    self.widgets[widget_id] = DashboardWidget(
                        widget_id=widget_id,
                        title=widget_id.replace('_', ' ').title(),
                        status=WidgetStatus.ERROR,
                        last_update=datetime.utcnow(),
                        data={},
                        error_message=str(e)
                    )
                else:
                    self.widgets[widget_id].status = WidgetStatus.ERROR
                    self.widgets[widget_id].error_message = str(e)
            
            raise
    
    async def get_widget(self, widget_id: str) -> Optional[DashboardWidget]:
        """Get a specific widget by ID"""
        return self.widgets.get(widget_id)
    
    async def get_all_widgets(self) -> Dict[str, DashboardWidget]:
        """Get all dashboard widgets"""
        return self.widgets.copy()
    
    async def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get dashboard summary with key metrics"""
        summary = await self.account_manager.get_account_summary()
        
        return {
            'account_id': summary.account_id,
            'currency': summary.currency.value,
            'equity': float(summary.account_equity),
            'balance': float(summary.balance),
            'unrealized_pl': float(summary.unrealized_pl),
            'margin_level': float(summary.calculate_margin_level()),
            'open_positions': summary.open_position_count,
            'pending_orders': summary.pending_order_count,
            'widgets_count': len(self.widgets),
            'last_update': self.metrics['last_full_refresh'].isoformat() if self.metrics['last_full_refresh'] else None,
            'status': 'operational' if all(w.status != WidgetStatus.ERROR for w in self.widgets.values()) else 'degraded'
        }
    
    def add_update_callback(self, callback: callable):
        """Add callback for dashboard updates"""
        self.update_callbacks.append(callback)
    
    def remove_update_callback(self, callback: callable):
        """Remove update callback"""
        if callback in self.update_callbacks:
            self.update_callbacks.remove(callback)
    
    async def _notify_update_callbacks(self, update_type: str, data: Any):
        """Notify all registered callbacks of updates"""
        for callback in self.update_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(update_type, data)
                else:
                    callback(update_type, data)
            except Exception as e:
                logger.error(f"Error in dashboard update callback: {e}")
    
    async def _handle_account_update(self, update: AccountUpdate):
        """Handle account summary updates"""
        try:
            summary = AccountSummary(**update.data)
            
            # Update relevant widgets
            self.widgets['account_summary'] = AccountSummaryWidget.from_account_summary(summary)
            self.widgets['margin_status'] = MarginStatusWidget.from_account_summary(summary)
            self.widgets['position_counter'] = PositionCounterWidget.from_account_summary(summary)
            
            # Record balance snapshot for historical tracking
            self.historical_service.record_balance_snapshot(
                balance=summary.balance,
                unrealized_pl=summary.unrealized_pl,
                realized_pl=summary.realized_pl,
                equity=summary.account_equity,
                margin_used=summary.margin_used,
                margin_available=summary.margin_available,
                open_positions=summary.open_position_count,
                pending_orders=summary.pending_order_count
            )
            
            await self._notify_update_callbacks('account_summary', {
                'account_summary': self.widgets['account_summary'],
                'margin_status': self.widgets['margin_status'],
                'position_counter': self.widgets['position_counter']
            })
            
        except Exception as e:
            logger.error(f"Error handling account update: {e}")
    
    async def _handle_balance_update(self, update: AccountUpdate):
        """Handle balance-specific updates"""
        try:
            # Update account summary widget with balance changes
            if 'account_summary' in self.widgets:
                widget = self.widgets['account_summary']
                widget.data.update(update.data)
                widget.last_update = datetime.utcnow()
                widget.status = WidgetStatus.READY
            
            await self._notify_update_callbacks('balance', {'balance': update.data})
            
        except Exception as e:
            logger.error(f"Error handling balance update: {e}")
    
    async def _handle_margin_update(self, update: AccountUpdate):
        """Handle margin-specific updates"""
        try:
            # Update margin status widget
            if 'margin_status' in self.widgets:
                widget = self.widgets['margin_status']
                widget.data.update(update.data)
                widget.last_update = datetime.utcnow()
                widget.status = WidgetStatus.READY
            
            await self._notify_update_callbacks('margin', {'margin': update.data})
            
        except Exception as e:
            logger.error(f"Error handling margin update: {e}")
    
    async def _handle_spreads_update(self, update: AccountUpdate):
        """Handle instrument spreads updates"""
        try:
            spreads_data = update.data.get('spreads', {})
            
            # Convert to InstrumentSpread objects
            spreads = {}
            for instrument, spread_data in spreads_data.items():
                spreads[instrument] = type('InstrumentSpread', (), {
                    'instrument': instrument,
                    'bid': Decimal(str(spread_data['bid'])),
                    'ask': Decimal(str(spread_data['ask'])),
                    'spread': Decimal(str(spread_data['spread'])),
                    'spread_pips': Decimal(str(spread_data['spread_pips'])),
                    'tradeable': spread_data['tradeable'],
                    'liquidity': spread_data.get('liquidity', 10),
                    'timestamp': datetime.utcnow()
                })()
            
            # Update spreads widget
            self.widgets['instrument_spreads'] = InstrumentSpreadWidget.from_spreads(spreads)
            
            await self._notify_update_callbacks('spreads', {'spreads': self.widgets['instrument_spreads']})
            
        except Exception as e:
            logger.error(f"Error handling spreads update: {e}")
    
    async def _handle_positions_update(self, update: AccountUpdate):
        """Handle positions updates"""
        try:
            # This might require refreshing position counter
            if 'position_counter' in self.widgets:
                # For now, trigger a refresh of account summary
                summary = await self.account_manager.get_account_summary(use_cache=False)
                self.widgets['position_counter'] = PositionCounterWidget.from_account_summary(summary)
            
            await self._notify_update_callbacks('positions', {'positions': update.data})
            
        except Exception as e:
            logger.error(f"Error handling positions update: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get dashboard metrics"""
        return self.metrics.copy()