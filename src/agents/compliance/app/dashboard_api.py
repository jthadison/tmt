"""
Compliance dashboard API endpoints for real-time compliance monitoring.
Provides comprehensive compliance data for Funding Pips dashboard.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from .models import Account, Position, ComplianceStatus
from .funding_pips import FundingPipsCompliance
from .daily_loss_tracker import DailyLossTracker
from .static_drawdown_monitor import StaticDrawdownMonitor
from .stop_loss_enforcer import MandatoryStopLossEnforcer
from .weekend_closure import WeekendClosureAutomation
from .minimum_hold_time import MinimumHoldTimeEnforcer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/compliance/dashboard", tags=["compliance-dashboard"])


class ComplianceDashboardData(BaseModel):
    """Comprehensive compliance dashboard data model."""
    account_id: str
    prop_firm: str
    overall_status: str
    compliance_score: int
    daily_loss: Dict[str, Any]
    drawdown: Dict[str, Any]
    stop_loss: Dict[str, Any]
    weekend_closure: Dict[str, Any]
    hold_time: Dict[str, Any]
    active_positions: List[Dict[str, Any]]
    recent_alerts: List[Dict[str, Any]]
    performance_metrics: Dict[str, Any]
    last_updated: str


class ComplianceAlert(BaseModel):
    """Compliance alert model."""
    alert_type: str
    severity: str
    message: str
    timestamp: str
    requires_action: bool
    metadata: Dict[str, Any]


# Initialize compliance components
funding_pips = FundingPipsCompliance()
daily_loss_tracker = DailyLossTracker()
drawdown_monitor = StaticDrawdownMonitor()
stop_loss_enforcer = MandatoryStopLossEnforcer()
weekend_closure = WeekendClosureAutomation()
hold_time_enforcer = MinimumHoldTimeEnforcer()


@router.get("/status/{account_id}", response_model=ComplianceDashboardData)
async def get_compliance_dashboard(account_id: str):
    """
    Get comprehensive compliance dashboard data for account.
    
    Args:
        account_id: Account identifier
        
    Returns:
        Complete compliance status and metrics
    """
    try:
        # Get account data (mock implementation)
        account = await _get_account_data(account_id)
        
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Get positions data
        positions = await _get_account_positions(account_id)
        
        # Collect compliance data from all components
        dashboard_data = ComplianceDashboardData(
            account_id=account_id,
            prop_firm="Funding Pips",
            overall_status=_calculate_overall_status(account),
            compliance_score=_calculate_compliance_score(account),
            daily_loss=daily_loss_tracker.get_daily_loss_status(account),
            drawdown=drawdown_monitor.get_drawdown_status(account),
            stop_loss=stop_loss_enforcer.get_stop_loss_requirements_summary(),
            weekend_closure=weekend_closure.get_weekend_closure_status(account_id),
            hold_time=_get_hold_time_summary(positions),
            active_positions=_format_positions_for_dashboard(positions),
            recent_alerts=await _get_recent_alerts(account_id),
            performance_metrics=_get_performance_metrics(account_id),
            last_updated=datetime.utcnow().isoformat()
        )
        
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Error getting compliance dashboard for {account_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/alerts/{account_id}")
async def get_compliance_alerts(
    account_id: str,
    limit: int = Query(50, le=100),
    severity: Optional[str] = Query(None, regex="^(info|warning|critical)$")
):
    """
    Get compliance alerts for account.
    
    Args:
        account_id: Account identifier
        limit: Maximum number of alerts to return
        severity: Filter by severity level
        
    Returns:
        List of compliance alerts
    """
    try:
        # Get alerts from various compliance components
        alerts = []
        
        # Daily loss alerts
        daily_alerts = await _get_daily_loss_alerts(account_id, limit)
        alerts.extend(daily_alerts)
        
        # Drawdown alerts
        drawdown_alerts = await _get_drawdown_alerts(account_id, limit)
        alerts.extend(drawdown_alerts)
        
        # Weekend closure alerts
        weekend_alerts = await _get_weekend_alerts(account_id, limit)
        alerts.extend(weekend_alerts)
        
        # Hold time alerts
        hold_time_alerts = await _get_hold_time_alerts(account_id, limit)
        alerts.extend(hold_time_alerts)
        
        # Filter by severity if specified
        if severity:
            alerts = [alert for alert in alerts if alert['severity'] == severity]
        
        # Sort by timestamp (most recent first)
        alerts.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Apply limit
        alerts = alerts[:limit]
        
        return {"alerts": alerts, "total_count": len(alerts)}
        
    except Exception as e:
        logger.error(f"Error getting alerts for {account_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/metrics/{account_id}")
async def get_compliance_metrics(
    account_id: str,
    days: int = Query(7, ge=1, le=90)
):
    """
    Get detailed compliance metrics for account.
    
    Args:
        account_id: Account identifier
        days: Number of days to include in metrics
        
    Returns:
        Comprehensive compliance metrics
    """
    try:
        metrics = {
            'account_id': account_id,
            'analysis_period_days': days,
            'daily_loss_metrics': daily_loss_tracker.get_statistics(
                await _get_account_data(account_id)
            ),
            'drawdown_metrics': drawdown_monitor.get_recovery_metrics(
                await _get_account_data(account_id)
            ),
            'stop_loss_metrics': stop_loss_enforcer.get_account_stop_loss_metrics(account_id),
            'weekend_closure_metrics': weekend_closure.get_closure_statistics(account_id, days),
            'hold_time_metrics': hold_time_enforcer.get_account_hold_time_statistics(account_id, days),
            'compliance_trends': await _get_compliance_trends(account_id, days),
            'risk_analysis': await _get_risk_analysis(account_id),
            'generated_at': datetime.utcnow().isoformat()
        }
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting metrics for {account_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/positions/{account_id}")
async def get_position_compliance_status(account_id: str):
    """
    Get compliance status for all positions.
    
    Args:
        account_id: Account identifier
        
    Returns:
        Position-level compliance details
    """
    try:
        positions = await _get_account_positions(account_id)
        account = await _get_account_data(account_id)
        
        position_statuses = []
        
        for position in positions:
            # Get hold time status
            hold_status = hold_time_enforcer.get_position_hold_status(position)
            
            # Check stop loss compliance
            stop_loss_compliant = position.stop_loss is not None
            
            # Calculate position risk
            position_risk = _calculate_position_risk(account, position)
            
            position_status = {
                'position_id': position.position_id,
                'symbol': position.symbol,
                'direction': position.direction,
                'size': float(position.size),
                'entry_price': float(position.entry_price),
                'current_price': float(getattr(position, 'current_price', position.entry_price)),
                'unrealized_pnl': float(position.unrealized_pnl),
                'hold_time_status': hold_status,
                'stop_loss_compliant': stop_loss_compliant,
                'stop_loss': float(position.stop_loss) if position.stop_loss else None,
                'position_risk_percentage': position_risk,
                'compliance_issues': _get_position_compliance_issues(position, hold_status, stop_loss_compliant),
                'can_close': hold_status['can_close'] and stop_loss_compliant,
                'opened_at': position.open_time.isoformat()
            }
            
            position_statuses.append(position_status)
        
        return {
            'account_id': account_id,
            'total_positions': len(positions),
            'compliant_positions': len([p for p in position_statuses if not p['compliance_issues']]),
            'positions': position_statuses
        }
        
    except Exception as e:
        logger.error(f"Error getting position compliance for {account_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/override/{account_id}")
async def create_compliance_override(
    account_id: str,
    override_type: str,
    reason: str,
    duration_minutes: int = 60
):
    """
    Create compliance override for account.
    
    Args:
        account_id: Account identifier
        override_type: Type of override (daily_loss, weekend_closure, etc.)
        reason: Reason for override
        duration_minutes: Override duration
        
    Returns:
        Override details
    """
    try:
        if override_type == "daily_loss":
            override_data = daily_loss_tracker.create_emergency_override(
                account_id, reason, duration_minutes
            )
        elif override_type == "weekend_closure":
            override_data = weekend_closure.create_manual_override(
                account_id, reason, duration_minutes // 60
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid override type")
        
        logger.warning(f"Compliance override created: {override_type} for {account_id}")
        return override_data
        
    except Exception as e:
        logger.error(f"Error creating override for {account_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/reports/{account_id}")
async def generate_compliance_report(
    account_id: str,
    report_type: str = Query("comprehensive", regex="^(daily|weekly|monthly|comprehensive)$"),
    format: str = Query("json", regex="^(json|pdf)$")
):
    """
    Generate compliance report for account.
    
    Args:
        account_id: Account identifier
        report_type: Type of report to generate
        format: Report format
        
    Returns:
        Generated compliance report
    """
    try:
        account = await _get_account_data(account_id)
        
        # Determine report period
        days_map = {"daily": 1, "weekly": 7, "monthly": 30, "comprehensive": 90}
        days = days_map.get(report_type, 7)
        
        report = {
            'account_id': account_id,
            'report_type': report_type,
            'generated_at': datetime.utcnow().isoformat(),
            'period_days': days,
            'summary': await _generate_report_summary(account, days),
            'daily_loss_report': daily_loss_tracker.get_statistics(account),
            'drawdown_analysis': drawdown_monitor.get_recovery_metrics(account),
            'stop_loss_report': stop_loss_enforcer.generate_stop_loss_report(account, days),
            'weekend_closure_analysis': weekend_closure.get_closure_statistics(account_id, days),
            'hold_time_analysis': hold_time_enforcer.get_account_hold_time_statistics(account_id, days),
            'compliance_score_history': await _get_compliance_score_history(account_id, days),
            'recommendations': await _generate_compliance_recommendations(account_id, days)
        }
        
        return report
        
    except Exception as e:
        logger.error(f"Error generating report for {account_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Helper functions

async def _get_account_data(account_id: str) -> Optional[Account]:
    """Get account data (mock implementation)."""
    # Mock account data
    return Account(
        account_id=account_id,
        prop_firm="Funding Pips",
        balance=Decimal('100000.00'),
        initial_balance=Decimal('100000.00'),
        daily_pnl=Decimal('-1250.00'),
        unrealized_pnl=Decimal('-450.00'),
        daily_trades_count=8
    )


async def _get_account_positions(account_id: str) -> List[Position]:
    """Get account positions (mock implementation)."""
    # Mock positions data
    return [
        Position(
            position_id=f"{account_id}_pos_1",
            account_id=account_id,
            symbol="EURUSD",
            direction="buy",
            size=Decimal('0.1'),
            entry_price=Decimal('1.0950'),
            stop_loss=Decimal('1.0930'),
            unrealized_pnl=Decimal('-20.00'),
            open_time=datetime.utcnow() - timedelta(minutes=45)
        ),
        Position(
            position_id=f"{account_id}_pos_2",
            account_id=account_id,
            symbol="GBPUSD",
            direction="sell",
            size=Decimal('0.05'),
            entry_price=Decimal('1.2750'),
            stop_loss=Decimal('1.2770'),
            unrealized_pnl=Decimal('15.50'),
            open_time=datetime.utcnow() - timedelta(minutes=25)
        )
    ]


def _calculate_overall_status(account: Account) -> str:
    """Calculate overall compliance status."""
    # Simple status calculation based on daily loss and drawdown
    daily_loss_pct = abs(account.daily_pnl) / account.initial_balance
    current_equity = account.balance + account.unrealized_pnl
    drawdown_pct = (account.initial_balance - current_equity) / account.initial_balance
    
    if daily_loss_pct >= 0.04 or drawdown_pct >= 0.08:
        return "violation"
    elif daily_loss_pct >= 0.032 or drawdown_pct >= 0.064:
        return "warning"
    elif daily_loss_pct >= 0.024 or drawdown_pct >= 0.048:
        return "caution"
    else:
        return "compliant"


def _calculate_compliance_score(account: Account) -> int:
    """Calculate overall compliance score (0-100)."""
    score = 100
    
    # Daily loss impact
    daily_loss_pct = abs(account.daily_pnl) / account.initial_balance
    if daily_loss_pct > 0.032:
        score -= int((daily_loss_pct - 0.032) * 500)
    
    # Drawdown impact
    current_equity = account.balance + account.unrealized_pnl
    drawdown_pct = (account.initial_balance - current_equity) / account.initial_balance
    if drawdown_pct > 0.05:
        score -= int((drawdown_pct - 0.05) * 333)
    
    return max(0, min(100, score))


def _get_hold_time_summary(positions: List[Position]) -> Dict[str, Any]:
    """Get hold time summary for all positions."""
    if not positions:
        return {"total_positions": 0, "compliant_positions": 0, "compliance_rate": 100.0}
    
    compliant_count = 0
    for position in positions:
        compliant, _ = hold_time_enforcer.check_hold_time_compliance(position)
        if compliant:
            compliant_count += 1
    
    return {
        "total_positions": len(positions),
        "compliant_positions": compliant_count,
        "compliance_rate": (compliant_count / len(positions)) * 100,
        "minimum_hold_time_seconds": hold_time_enforcer.minimum_hold_seconds
    }


def _format_positions_for_dashboard(positions: List[Position]) -> List[Dict[str, Any]]:
    """Format positions for dashboard display."""
    formatted_positions = []
    
    for position in positions:
        hold_status = hold_time_enforcer.get_position_hold_status(position)
        
        formatted_position = {
            "position_id": position.position_id,
            "symbol": position.symbol,
            "direction": position.direction,
            "size": float(position.size),
            "entry_price": float(position.entry_price),
            "stop_loss": float(position.stop_loss) if position.stop_loss else None,
            "unrealized_pnl": float(position.unrealized_pnl),
            "hold_time_status": hold_status,
            "can_close": hold_status["can_close"]
        }
        
        formatted_positions.append(formatted_position)
    
    return formatted_positions


async def _get_recent_alerts(account_id: str) -> List[Dict[str, Any]]:
    """Get recent alerts for account."""
    # Mock implementation - would aggregate from all compliance components
    return [
        {
            "alert_type": "daily_loss_warning",
            "severity": "warning",
            "message": "Daily loss approaching 80% of limit",
            "timestamp": (datetime.utcnow() - timedelta(minutes=15)).isoformat(),
            "requires_action": False
        }
    ]


def _get_performance_metrics(account_id: str) -> Dict[str, Any]:
    """Get performance metrics for account."""
    return {
        "compliance_score": 92,
        "violations_this_week": 0,
        "avg_hold_time_minutes": 45,
        "stop_loss_effectiveness": 95.5,
        "weekend_closure_success_rate": 100.0
    }


async def _get_daily_loss_alerts(account_id: str, limit: int) -> List[Dict]:
    """Get daily loss related alerts."""
    # Mock implementation
    return []


async def _get_drawdown_alerts(account_id: str, limit: int) -> List[Dict]:
    """Get drawdown related alerts."""
    # Mock implementation
    return []


async def _get_weekend_alerts(account_id: str, limit: int) -> List[Dict]:
    """Get weekend closure related alerts."""
    # Mock implementation
    return []


async def _get_hold_time_alerts(account_id: str, limit: int) -> List[Dict]:
    """Get hold time related alerts."""
    # Mock implementation
    return []


async def _get_compliance_trends(account_id: str, days: int) -> Dict[str, Any]:
    """Get compliance trends over time."""
    # Mock implementation
    return {
        "daily_scores": [95, 92, 88, 94, 96, 91, 93],
        "trend": "stable"
    }


async def _get_risk_analysis(account_id: str) -> Dict[str, Any]:
    """Get risk analysis for account."""
    # Mock implementation
    return {
        "overall_risk_level": "moderate",
        "risk_factors": ["approaching daily loss warning"],
        "risk_score": 75
    }


def _calculate_position_risk(account: Account, position: Position) -> float:
    """Calculate position risk as percentage of account."""
    if not position.stop_loss:
        return 0.0
    
    risk_amount = abs(position.entry_price - position.stop_loss) * position.size
    return float((risk_amount / account.balance) * 100)


def _get_position_compliance_issues(position: Position, hold_status: Dict, stop_loss_compliant: bool) -> List[str]:
    """Get compliance issues for position."""
    issues = []
    
    if not stop_loss_compliant:
        issues.append("Missing stop loss")
    
    if not hold_status["can_close"]:
        issues.append(f"Minimum hold time not met ({hold_status['time_remaining_seconds']}s remaining)")
    
    return issues


async def _generate_report_summary(account: Account, days: int) -> Dict[str, Any]:
    """Generate report summary."""
    return {
        "overall_compliance": "good",
        "violations": 0,
        "warnings": 2,
        "compliance_score": _calculate_compliance_score(account)
    }


async def _get_compliance_score_history(account_id: str, days: int) -> List[Dict]:
    """Get compliance score history."""
    # Mock implementation
    return [
        {"date": "2025-01-07", "score": 92},
        {"date": "2025-01-06", "score": 95},
        {"date": "2025-01-05", "score": 88}
    ]


async def _generate_compliance_recommendations(account_id: str, days: int) -> List[str]:
    """Generate compliance recommendations."""
    return [
        "Consider tighter stop losses to reduce daily loss risk",
        "Maintain current position sizing discipline",
        "Weekend closure automation is working well"
    ]