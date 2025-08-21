"""
Compliance and Regulatory Reporting Engine.

Provides comprehensive compliance monitoring, regulatory reporting,
audit trail management, and risk governance capabilities.
"""

import asyncio
import json
import csv
import io
from collections import defaultdict
from datetime import datetime, date, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from uuid import UUID, uuid4

from ..core.models import (
    ComplianceRecord,
    RiskMetrics,
    Position,
    ReportType,
    AlertSeverity,
    RiskLevel
)


class RegulationType(str, Enum):
    """Regulatory framework types."""
    MIFID_II = "mifid_ii"
    CFTC = "cftc"
    SEC = "sec"
    FCA = "fca"
    ESMA = "esma"
    ASIC = "asic"
    FINRA = "finra"


class ComplianceStatus(str, Enum):
    """Compliance status enumeration."""
    COMPLIANT = "compliant"
    WARNING = "warning"
    VIOLATION = "violation"
    UNDER_REVIEW = "under_review"
    REMEDIATED = "remediated"


class ReportFormat(str, Enum):
    """Report output formats."""
    PDF = "pdf"
    CSV = "csv"
    JSON = "json"
    XML = "xml"
    XLSX = "xlsx"


class ComplianceEngine:
    """
    Comprehensive compliance monitoring and reporting engine
    with regulatory compliance, audit trails, and governance.
    """
    
    def __init__(self, retention_years: int = 7):
        self.retention_years = retention_years
        
        # Compliance tracking
        self.compliance_records: Dict[str, List[ComplianceRecord]] = defaultdict(list)
        self.audit_trail: List[Dict] = []
        self.compliance_rules: Dict[str, Dict] = {}
        
        # Regulatory requirements
        self.regulatory_limits: Dict[RegulationType, Dict] = {}
        self.reporting_schedules: Dict[str, Dict] = {}
        
        # Performance tracking
        self.compliance_checks_performed = 0
        self.violations_detected = 0
        self.reports_generated = 0
        
        # Setup default compliance rules
        self._setup_default_compliance_rules()
        self._setup_regulatory_limits()
    
    def _setup_default_compliance_rules(self):
        """Setup default compliance monitoring rules."""
        
        # Position limits
        self.compliance_rules['position_limits'] = {
            'max_single_position': Decimal('100000'),
            'max_sector_concentration': 0.25,
            'max_instrument_concentration': 0.15,
            'max_leverage': Decimal('30'),
            'check_frequency': 'real_time'
        }
        
        # Risk limits
        self.compliance_rules['risk_limits'] = {
            'max_var_95': Decimal('5000'),
            'max_daily_loss': Decimal('2000'),
            'max_drawdown': 0.15,
            'risk_score_threshold': 85.0,
            'check_frequency': 'real_time'
        }
        
        # Trading limits
        self.compliance_rules['trading_limits'] = {
            'max_trades_per_day': 500,
            'max_order_size': Decimal('50000'),
            'forbidden_instruments': [],
            'trading_hours_restriction': True,
            'check_frequency': 'per_trade'
        }
        
        # Reporting requirements
        self.compliance_rules['reporting'] = {
            'daily_risk_report': True,
            'weekly_performance_report': True,
            'monthly_compliance_summary': True,
            'transaction_reporting': True,
            'retention_period_years': self.retention_years
        }
    
    def _setup_regulatory_limits(self):
        """Setup regulatory framework limits."""
        
        # MiFID II requirements
        self.regulatory_limits[RegulationType.MIFID_II] = {
            'position_reporting_threshold': Decimal('200000'),
            'large_in_scale_threshold': Decimal('400000'),
            'transparency_reporting': True,
            'best_execution_reporting': True,
            'risk_management_requirements': True
        }
        
        # CFTC requirements
        self.regulatory_limits[RegulationType.CFTC] = {
            'large_trader_threshold': Decimal('1000000'),
            'swap_data_reporting': True,
            'position_limits': True,
            'risk_management_requirements': True
        }
        
        # FINRA requirements
        self.regulatory_limits[RegulationType.FINRA] = {
            'net_capital_requirement': Decimal('250000'),
            'customer_protection_rule': True,
            'margin_requirements': True,
            'surveillance_requirements': True
        }
    
    async def perform_compliance_check(
        self,
        account_id: str,
        risk_metrics: RiskMetrics,
        positions: List[Position],
        regulations: List[RegulationType] = None
    ) -> List[ComplianceRecord]:
        """Perform comprehensive compliance check."""
        
        self.compliance_checks_performed += 1
        compliance_records = []
        
        regulations = regulations or [RegulationType.MIFID_II, RegulationType.CFTC]
        
        # Position compliance checks
        position_records = await self._check_position_compliance(account_id, positions)
        compliance_records.extend(position_records)
        
        # Risk compliance checks
        risk_records = await self._check_risk_compliance(account_id, risk_metrics)
        compliance_records.extend(risk_records)
        
        # Trading compliance checks
        trading_records = await self._check_trading_compliance(account_id, positions)
        compliance_records.extend(trading_records)
        
        # Regulatory-specific checks
        for regulation in regulations:
            reg_records = await self._check_regulatory_compliance(
                account_id, risk_metrics, positions, regulation
            )
            compliance_records.extend(reg_records)
        
        # Store compliance records
        for record in compliance_records:
            self.compliance_records[account_id].append(record)
            
            # Count violations
            if record.status == ComplianceStatus.VIOLATION.value:
                self.violations_detected += 1
        
        # Log audit trail
        await self._log_compliance_check(account_id, compliance_records)
        
        return compliance_records
    
    async def _check_position_compliance(
        self,
        account_id: str,
        positions: List[Position]
    ) -> List[ComplianceRecord]:
        """Check position-related compliance rules."""
        records = []
        
        if not positions:
            return records
        
        total_exposure = sum(pos.notional_value for pos in positions)
        
        # Single position size limits
        max_position = self.compliance_rules['position_limits']['max_single_position']
        for position in positions:
            if position.notional_value > max_position:
                records.append(ComplianceRecord(
                    account_id=account_id,
                    record_type="position_limit_breach",
                    regulation="internal_limits",
                    requirement="Maximum single position size",
                    status=ComplianceStatus.VIOLATION.value,
                    description=f"Position in {position.instrument} exceeds limit",
                    severity=AlertSeverity.ERROR,
                    risk_rating=RiskLevel.HIGH,
                    evidence={
                        "instrument": position.instrument,
                        "position_size": float(position.notional_value),
                        "limit": float(max_position),
                        "breach_amount": float(position.notional_value - max_position)
                    },
                    remediation_actions=[
                        "Reduce position size immediately",
                        "Review position sizing algorithm",
                        "Update risk limits if justified"
                    ]
                ))
        
        # Sector concentration limits
        if total_exposure > 0:
            sector_exposure = defaultdict(Decimal)
            for position in positions:
                sector = position.asset_class.value
                sector_exposure[sector] += abs(position.market_value)
            
            max_sector_concentration = self.compliance_rules['position_limits']['max_sector_concentration']
            for sector, exposure in sector_exposure.items():
                concentration = float(exposure / total_exposure)
                if concentration > max_sector_concentration:
                    records.append(ComplianceRecord(
                        account_id=account_id,
                        record_type="sector_concentration_breach",
                        regulation="internal_limits",
                        requirement="Maximum sector concentration",
                        status=ComplianceStatus.VIOLATION.value,
                        description=f"Sector {sector} concentration exceeds limit",
                        severity=AlertSeverity.WARNING,
                        risk_rating=RiskLevel.MEDIUM,
                        evidence={
                            "sector": sector,
                            "concentration": concentration,
                            "limit": max_sector_concentration,
                            "exposure": float(exposure)
                        },
                        remediation_actions=[
                            "Diversify across sectors",
                            "Reduce exposure in over-concentrated sector",
                            "Review sector allocation strategy"
                        ]
                    ))
        
        return records
    
    async def _check_risk_compliance(
        self,
        account_id: str,
        risk_metrics: RiskMetrics
    ) -> List[ComplianceRecord]:
        """Check risk-related compliance rules."""
        records = []
        
        # VaR limits
        max_var = self.compliance_rules['risk_limits']['max_var_95']
        if risk_metrics.var_95 > max_var:
            records.append(ComplianceRecord(
                account_id=account_id,
                record_type="var_limit_breach",
                regulation="internal_risk_limits",
                requirement="Maximum 95% Value at Risk",
                status=ComplianceStatus.VIOLATION.value,
                description=f"VaR exceeds maximum limit",
                severity=AlertSeverity.ERROR,
                risk_rating=RiskLevel.HIGH,
                evidence={
                    "current_var": float(risk_metrics.var_95),
                    "limit": float(max_var),
                    "breach_amount": float(risk_metrics.var_95 - max_var)
                },
                remediation_actions=[
                    "Reduce position sizes",
                    "Increase diversification",
                    "Review risk model parameters",
                    "Consider hedging strategies"
                ]
            ))
        
        # Daily loss limits
        max_daily_loss = self.compliance_rules['risk_limits']['max_daily_loss']
        if risk_metrics.daily_pl < -max_daily_loss:
            records.append(ComplianceRecord(
                account_id=account_id,
                record_type="daily_loss_limit_breach",
                regulation="internal_risk_limits",
                requirement="Maximum daily loss",
                status=ComplianceStatus.VIOLATION.value,
                description=f"Daily loss exceeds maximum limit",
                severity=AlertSeverity.CRITICAL,
                risk_rating=RiskLevel.CRITICAL,
                evidence={
                    "daily_pl": float(risk_metrics.daily_pl),
                    "limit": float(-max_daily_loss),
                    "breach_amount": float(abs(risk_metrics.daily_pl) - max_daily_loss)
                },
                remediation_actions=[
                    "Stop new position entries",
                    "Review existing positions for exit",
                    "Activate enhanced monitoring",
                    "Consider kill switch activation"
                ]
            ))
        
        # Risk score limits
        max_risk_score = self.compliance_rules['risk_limits']['risk_score_threshold']
        if risk_metrics.risk_score > max_risk_score:
            records.append(ComplianceRecord(
                account_id=account_id,
                record_type="risk_score_limit_breach",
                regulation="internal_risk_limits",
                requirement="Maximum risk score",
                status=ComplianceStatus.WARNING.value,
                description=f"Risk score exceeds threshold",
                severity=AlertSeverity.WARNING,
                risk_rating=RiskLevel.MEDIUM,
                evidence={
                    "risk_score": risk_metrics.risk_score,
                    "threshold": max_risk_score
                },
                remediation_actions=[
                    "Review risk factors",
                    "Consider position adjustments",
                    "Monitor closely for improvements"
                ]
            ))
        
        return records
    
    async def _check_trading_compliance(
        self,
        account_id: str,
        positions: List[Position]
    ) -> List[ComplianceRecord]:
        """Check trading-related compliance rules."""
        records = []
        
        # Check for forbidden instruments
        forbidden_instruments = self.compliance_rules['trading_limits']['forbidden_instruments']
        for position in positions:
            if position.instrument in forbidden_instruments:
                records.append(ComplianceRecord(
                    account_id=account_id,
                    record_type="forbidden_instrument",
                    regulation="trading_restrictions",
                    requirement="Forbidden instrument restrictions",
                    status=ComplianceStatus.VIOLATION.value,
                    description=f"Trading in forbidden instrument {position.instrument}",
                    severity=AlertSeverity.ERROR,
                    risk_rating=RiskLevel.HIGH,
                    evidence={
                        "instrument": position.instrument,
                        "position_size": float(position.notional_value)
                    },
                    remediation_actions=[
                        "Close position immediately",
                        "Review trading restrictions",
                        "Update position filtering"
                    ]
                ))
        
        return records
    
    async def _check_regulatory_compliance(
        self,
        account_id: str,
        risk_metrics: RiskMetrics,
        positions: List[Position],
        regulation: RegulationType
    ) -> List[ComplianceRecord]:
        """Check regulatory-specific compliance requirements."""
        records = []
        
        if regulation == RegulationType.MIFID_II:
            records.extend(await self._check_mifid_ii_compliance(account_id, risk_metrics, positions))
        elif regulation == RegulationType.CFTC:
            records.extend(await self._check_cftc_compliance(account_id, risk_metrics, positions))
        elif regulation == RegulationType.FINRA:
            records.extend(await self._check_finra_compliance(account_id, risk_metrics, positions))
        
        return records
    
    async def _check_mifid_ii_compliance(
        self,
        account_id: str,
        risk_metrics: RiskMetrics,
        positions: List[Position]
    ) -> List[ComplianceRecord]:
        """Check MiFID II compliance requirements."""
        records = []
        
        limits = self.regulatory_limits[RegulationType.MIFID_II]
        
        # Position reporting threshold
        reporting_threshold = limits['position_reporting_threshold']
        for position in positions:
            if position.notional_value > reporting_threshold:
                records.append(ComplianceRecord(
                    account_id=account_id,
                    record_type="mifid_ii_position_reporting",
                    regulation="mifid_ii",
                    requirement="Position reporting threshold",
                    status=ComplianceStatus.COMPLIANT.value,
                    description=f"Position in {position.instrument} requires MiFID II reporting",
                    severity=AlertSeverity.INFO,
                    risk_rating=RiskLevel.LOW,
                    evidence={
                        "instrument": position.instrument,
                        "position_size": float(position.notional_value),
                        "threshold": float(reporting_threshold)
                    },
                    remediation_actions=[
                        "Submit position report to regulator",
                        "Ensure reporting within required timeframe",
                        "Maintain reporting documentation"
                    ]
                ))
        
        return records
    
    async def _check_cftc_compliance(
        self,
        account_id: str,
        risk_metrics: RiskMetrics,
        positions: List[Position]
    ) -> List[ComplianceRecord]:
        """Check CFTC compliance requirements."""
        records = []
        
        limits = self.regulatory_limits[RegulationType.CFTC]
        
        # Large trader threshold
        total_exposure = sum(pos.notional_value for pos in positions)
        large_trader_threshold = limits['large_trader_threshold']
        
        if total_exposure > large_trader_threshold:
            records.append(ComplianceRecord(
                account_id=account_id,
                record_type="cftc_large_trader_reporting",
                regulation="cftc",
                requirement="Large trader reporting",
                status=ComplianceStatus.COMPLIANT.value,
                description=f"Account exceeds CFTC large trader threshold",
                severity=AlertSeverity.INFO,
                risk_rating=RiskLevel.LOW,
                evidence={
                    "total_exposure": float(total_exposure),
                    "threshold": float(large_trader_threshold)
                },
                remediation_actions=[
                    "Submit large trader report",
                    "Maintain Form 102 filing",
                    "Ensure ongoing compliance monitoring"
                ]
            ))
        
        return records
    
    async def _check_finra_compliance(
        self,
        account_id: str,
        risk_metrics: RiskMetrics,
        positions: List[Position]
    ) -> List[ComplianceRecord]:
        """Check FINRA compliance requirements."""
        records = []
        
        # Net capital requirement (simplified check)
        limits = self.regulatory_limits[RegulationType.FINRA]
        net_capital_requirement = limits['net_capital_requirement']
        
        # This would normally check against actual net capital
        # For demo purposes, we'll check if total exposure suggests adequate capital
        total_exposure = sum(pos.notional_value for pos in positions)
        
        if total_exposure > net_capital_requirement * 10:  # 10:1 ratio assumption
            records.append(ComplianceRecord(
                account_id=account_id,
                record_type="finra_net_capital_concern",
                regulation="finra",
                requirement="Net capital adequacy",
                status=ComplianceStatus.WARNING.value,
                description=f"High exposure relative to net capital requirements",
                severity=AlertSeverity.WARNING,
                risk_rating=RiskLevel.MEDIUM,
                evidence={
                    "total_exposure": float(total_exposure),
                    "net_capital_requirement": float(net_capital_requirement)
                },
                remediation_actions=[
                    "Review net capital calculation",
                    "Consider reducing exposure",
                    "Ensure adequate capital buffers"
                ]
            ))
        
        return records
    
    async def generate_compliance_report(
        self,
        account_id: str,
        report_type: ReportType,
        start_date: date,
        end_date: date,
        format: ReportFormat = ReportFormat.JSON
    ) -> Dict[str, Any]:
        """Generate comprehensive compliance report."""
        
        self.reports_generated += 1
        
        # Filter records by date range
        filtered_records = [
            record for record in self.compliance_records.get(account_id, [])
            if start_date <= record.recorded_at.date() <= end_date
        ]
        
        # Compliance summary
        total_checks = len(filtered_records)
        violations = sum(1 for r in filtered_records if r.status == ComplianceStatus.VIOLATION.value)
        warnings = sum(1 for r in filtered_records if r.status == ComplianceStatus.WARNING.value)
        
        # Violation breakdown by type
        violation_types = defaultdict(int)
        for record in filtered_records:
            if record.status == ComplianceStatus.VIOLATION.value:
                violation_types[record.record_type] += 1
        
        # Regulatory breakdown
        regulatory_breakdown = defaultdict(int)
        for record in filtered_records:
            regulatory_breakdown[record.regulation] += 1
        
        report_data = {
            "report_metadata": {
                "report_id": str(uuid4()),
                "account_id": account_id,
                "report_type": report_type.value,
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat(),
                "generated_at": datetime.now().isoformat(),
                "format": format.value
            },
            "compliance_summary": {
                "total_compliance_checks": total_checks,
                "violations": violations,
                "warnings": warnings,
                "compliance_rate": (total_checks - violations) / total_checks if total_checks > 0 else 1.0,
                "risk_score": "high" if violations > 5 else "medium" if violations > 2 else "low"
            },
            "violation_analysis": {
                "total_violations": violations,
                "violation_types": dict(violation_types),
                "most_common_violation": max(violation_types.items(), key=lambda x: x[1])[0] if violation_types else None,
                "regulatory_breakdown": dict(regulatory_breakdown)
            },
            "compliance_records": [
                {
                    "record_id": str(record.record_id),
                    "record_type": record.record_type,
                    "regulation": record.regulation,
                    "requirement": record.requirement,
                    "status": record.status,
                    "description": record.description,
                    "severity": record.severity.value,
                    "risk_rating": record.risk_rating.value,
                    "recorded_at": record.recorded_at.isoformat(),
                    "evidence": record.evidence,
                    "remediation_actions": record.remediation_actions
                }
                for record in filtered_records
            ],
            "recommendations": self._generate_compliance_recommendations(filtered_records),
            "audit_trail": self._get_audit_trail_excerpt(account_id, start_date, end_date)
        }
        
        # Format-specific processing
        if format == ReportFormat.CSV:
            return self._convert_to_csv(report_data)
        elif format == ReportFormat.PDF:
            return self._convert_to_pdf(report_data)
        else:
            return report_data
    
    def _generate_compliance_recommendations(
        self,
        compliance_records: List[ComplianceRecord]
    ) -> List[str]:
        """Generate compliance improvement recommendations."""
        recommendations = []
        
        # Analyze violation patterns
        violation_types = defaultdict(int)
        for record in compliance_records:
            if record.status == ComplianceStatus.VIOLATION.value:
                violation_types[record.record_type] += 1
        
        # Generate specific recommendations
        if violation_types.get('position_limit_breach', 0) > 2:
            recommendations.append("Review and strengthen position sizing controls")
        
        if violation_types.get('risk_score_limit_breach', 0) > 3:
            recommendations.append("Implement enhanced risk monitoring and alerts")
        
        if violation_types.get('daily_loss_limit_breach', 0) > 0:
            recommendations.append("Review stop-loss strategies and risk limits")
        
        if violation_types.get('sector_concentration_breach', 0) > 1:
            recommendations.append("Improve portfolio diversification across sectors")
        
        # General recommendations
        if sum(violation_types.values()) > 10:
            recommendations.append("Conduct comprehensive compliance system review")
            recommendations.append("Consider additional compliance training")
        
        if not recommendations:
            recommendations.append("Continue current compliance practices")
            recommendations.append("Maintain regular monitoring and reviews")
        
        return recommendations
    
    def _get_audit_trail_excerpt(
        self,
        account_id: str,
        start_date: date,
        end_date: date
    ) -> List[Dict]:
        """Get audit trail excerpt for the reporting period."""
        
        # Filter audit trail by account and date
        filtered_trail = [
            entry for entry in self.audit_trail
            if entry.get('account_id') == account_id
            and start_date <= datetime.fromisoformat(entry['timestamp']).date() <= end_date
        ]
        
        # Return last 100 entries to keep report manageable
        return filtered_trail[-100:]
    
    def _convert_to_csv(self, report_data: Dict) -> str:
        """Convert compliance report to CSV format."""
        output = io.StringIO()
        
        # Write summary
        writer = csv.writer(output)
        writer.writerow(['Compliance Report Summary'])
        writer.writerow(['Account ID', report_data['report_metadata']['account_id']])
        writer.writerow(['Period', f"{report_data['report_metadata']['period_start']} to {report_data['report_metadata']['period_end']}"])
        writer.writerow(['Total Checks', report_data['compliance_summary']['total_compliance_checks']])
        writer.writerow(['Violations', report_data['compliance_summary']['violations']])
        writer.writerow(['Warnings', report_data['compliance_summary']['warnings']])
        writer.writerow(['Compliance Rate', f"{report_data['compliance_summary']['compliance_rate']:.2%}"])
        writer.writerow([])
        
        # Write detailed records
        writer.writerow(['Detailed Compliance Records'])
        writer.writerow(['Record Type', 'Regulation', 'Status', 'Severity', 'Description', 'Recorded At'])
        
        for record in report_data['compliance_records']:
            writer.writerow([
                record['record_type'],
                record['regulation'],
                record['status'],
                record['severity'],
                record['description'],
                record['recorded_at']
            ])
        
        return output.getvalue()
    
    def _convert_to_pdf(self, report_data: Dict) -> str:
        """Convert compliance report to PDF format (placeholder)."""
        # In production, use libraries like reportlab or weasyprint
        return f"PDF report generated for account {report_data['report_metadata']['account_id']}"
    
    async def _log_compliance_check(
        self,
        account_id: str,
        compliance_records: List[ComplianceRecord]
    ):
        """Log compliance check to audit trail."""
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "compliance_check",
            "account_id": account_id,
            "records_generated": len(compliance_records),
            "violations_found": sum(1 for r in compliance_records if r.status == ComplianceStatus.VIOLATION.value),
            "check_id": str(uuid4())
        }
        
        self.audit_trail.append(audit_entry)
        
        # Keep audit trail size manageable (last 10,000 entries)
        if len(self.audit_trail) > 10000:
            self.audit_trail = self.audit_trail[-10000:]
    
    def get_compliance_summary(self, account_id: Optional[str] = None) -> Dict[str, Any]:
        """Get compliance summary statistics."""
        
        if account_id:
            records = self.compliance_records.get(account_id, [])
        else:
            records = [record for record_list in self.compliance_records.values() for record in record_list]
        
        total_records = len(records)
        violations = sum(1 for r in records if r.status == ComplianceStatus.VIOLATION.value)
        warnings = sum(1 for r in records if r.status == ComplianceStatus.WARNING.value)
        
        # Recent activity (last 24 hours)
        cutoff_time = datetime.now() - timedelta(hours=24)
        recent_records = [r for r in records if r.recorded_at >= cutoff_time]
        recent_violations = sum(1 for r in recent_records if r.status == ComplianceStatus.VIOLATION.value)
        
        return {
            "total_compliance_records": total_records,
            "total_violations": violations,
            "total_warnings": warnings,
            "compliance_rate": (total_records - violations) / total_records if total_records > 0 else 1.0,
            "recent_activity": {
                "last_24h_records": len(recent_records),
                "last_24h_violations": recent_violations
            },
            "performance_metrics": {
                "compliance_checks_performed": self.compliance_checks_performed,
                "violations_detected": self.violations_detected,
                "reports_generated": self.reports_generated
            },
            "monitored_accounts": len(self.compliance_records)
        }
    
    def update_compliance_rules(self, rule_updates: Dict[str, Dict]):
        """Update compliance rules configuration."""
        self.compliance_rules.update(rule_updates)
        print(f"Updated compliance rules: {list(rule_updates.keys())}")
    
    def add_forbidden_instrument(self, instrument: str):
        """Add instrument to forbidden list."""
        forbidden_list = self.compliance_rules['trading_limits']['forbidden_instruments']
        if instrument not in forbidden_list:
            forbidden_list.append(instrument)
            print(f"Added {instrument} to forbidden instruments list")
    
    def remove_forbidden_instrument(self, instrument: str):
        """Remove instrument from forbidden list."""
        forbidden_list = self.compliance_rules['trading_limits']['forbidden_instruments']
        if instrument in forbidden_list:
            forbidden_list.remove(instrument)
            print(f"Removed {instrument} from forbidden instruments list")
    
    async def cleanup_old_records(self):
        """Clean up old compliance records based on retention policy."""
        cutoff_date = datetime.now() - timedelta(days=self.retention_years * 365)
        
        cleaned_count = 0
        for account_id in self.compliance_records:
            original_count = len(self.compliance_records[account_id])
            self.compliance_records[account_id] = [
                record for record in self.compliance_records[account_id]
                if record.recorded_at >= cutoff_date
            ]
            cleaned_count += original_count - len(self.compliance_records[account_id])
        
        # Clean audit trail
        original_audit_count = len(self.audit_trail)
        self.audit_trail = [
            entry for entry in self.audit_trail
            if datetime.fromisoformat(entry['timestamp']) >= cutoff_date
        ]
        cleaned_count += original_audit_count - len(self.audit_trail)
        
        if cleaned_count > 0:
            print(f"Cleaned up {cleaned_count} old compliance records")
        
        return cleaned_count