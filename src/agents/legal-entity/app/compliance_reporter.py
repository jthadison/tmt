"""Compliance reporting and entity separation verification."""

import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
import numpy as np
from scipy import stats

from sqlalchemy.orm import Session
from sqlalchemy import and_, func, distinct

from .models import (
    LegalEntity, EntityAuditLog, DecisionLog,
    ComplianceReport, EntityStatus
)
from .entity_manager import EntityManager
from .audit_service import AuditService
from .tos_manager import ToSManager
from .geographic_service import GeographicService


class ComplianceReporter:
    """Generates compliance reports and verifies entity separation."""
    
    def __init__(
        self,
        db_session: Session,
        entity_manager: EntityManager,
        audit_service: AuditService,
        tos_manager: ToSManager,
        geographic_service: GeographicService
    ):
        self.db = db_session
        self.entity_manager = entity_manager
        self.audit_service = audit_service
        self.tos_manager = tos_manager
        self.geographic_service = geographic_service
    
    async def generate_entity_separation_report(
        self,
        period_start: datetime,
        period_end: datetime,
        entity_ids: Optional[List[UUID]] = None
    ) -> ComplianceReport:
        """Generate comprehensive entity separation compliance report."""
        # Get entities to analyze
        query = self.db.query(LegalEntity).filter(
            LegalEntity.status == EntityStatus.ACTIVE.value
        )
        
        if entity_ids:
            query = query.filter(LegalEntity.entity_id.in_(entity_ids))
        
        entities = query.all()
        
        # Calculate compliance metrics
        independence_metrics = await self._calculate_independence_metrics(
            entities, period_start, period_end
        )
        
        trading_patterns = await self._analyze_trading_patterns(
            entities, period_start, period_end
        )
        
        audit_summary = await self._generate_audit_summary(
            entities, period_start, period_end
        )
        
        regulatory_compliance = await self._check_regulatory_compliance(entities)
        
        # Calculate overall compliance score
        compliance_score = self._calculate_compliance_score(
            independence_metrics,
            trading_patterns,
            audit_summary,
            regulatory_compliance
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            compliance_score,
            independence_metrics,
            trading_patterns,
            regulatory_compliance
        )
        
        return ComplianceReport(
            period_start=period_start,
            period_end=period_end,
            total_entities=len(entities),
            active_entities=len([e for e in entities if e.status == EntityStatus.ACTIVE.value]),
            compliance_score=compliance_score,
            independence_metrics=independence_metrics,
            trading_patterns=trading_patterns,
            audit_summary=audit_summary,
            regulatory_compliance=regulatory_compliance,
            recommendations=recommendations
        )
    
    async def _calculate_independence_metrics(
        self,
        entities: List[LegalEntity],
        period_start: datetime,
        period_end: datetime
    ) -> Dict[str, Any]:
        """Calculate metrics demonstrating entity independence."""
        if not entities:
            return {"error": "No entities to analyze"}
        
        entity_ids = [e.entity_id for e in entities]
        
        # Get all decisions in period
        decisions = self.db.query(DecisionLog).filter(
            and_(
                DecisionLog.entity_id.in_(entity_ids),
                DecisionLog.timestamp >= period_start,
                DecisionLog.timestamp <= period_end
            )
        ).all()
        
        if not decisions:
            return {
                "total_decisions": 0,
                "correlation_score": 0.0,
                "timing_variance": 0.0,
                "decision_uniqueness": 1.0,
                "independence_verified": True
            }
        
        # Group decisions by entity
        entity_decisions = {}
        for decision in decisions:
            if decision.entity_id not in entity_decisions:
                entity_decisions[decision.entity_id] = []
            entity_decisions[decision.entity_id].append(decision)
        
        # Calculate timing correlations
        timing_correlation = await self._calculate_timing_correlation(entity_decisions)
        
        # Calculate decision uniqueness
        decision_uniqueness = await self._calculate_decision_uniqueness(decisions)
        
        # Calculate timing variance
        timing_variance = await self._calculate_timing_variance(entity_decisions)
        
        # Statistical independence test
        independence_test = await self._perform_independence_test(entity_decisions)
        
        return {
            "total_decisions": len(decisions),
            "entities_analyzed": len(entity_ids),
            "correlation_score": timing_correlation,
            "timing_variance": timing_variance,
            "decision_uniqueness": decision_uniqueness,
            "independence_test": independence_test,
            "independence_verified": timing_correlation < 0.3 and decision_uniqueness > 0.7,
            "details": {
                "decisions_per_entity": {
                    str(eid): len(decs) for eid, decs in entity_decisions.items()
                },
                "average_delay_between_entities": self._calculate_average_delay(entity_decisions),
                "personality_distribution": self._get_personality_distribution(decisions)
            }
        }
    
    async def _analyze_trading_patterns(
        self,
        entities: List[LegalEntity],
        period_start: datetime,
        period_end: datetime
    ) -> Dict[str, Any]:
        """Analyze trading patterns for independence verification."""
        entity_ids = [e.entity_id for e in entities]
        
        # Get trade-related audit logs
        trade_logs = self.db.query(EntityAuditLog).filter(
            and_(
                EntityAuditLog.entity_id.in_(entity_ids),
                EntityAuditLog.action_type.in_(["trade_entry", "trade_exit"]),
                EntityAuditLog.created_at >= period_start,
                EntityAuditLog.created_at <= period_end
            )
        ).all()
        
        if not trade_logs:
            return {
                "total_trades": 0,
                "pattern_analysis": "No trading activity in period"
            }
        
        # Analyze patterns per entity
        entity_patterns = {}
        for entity in entities:
            entity_trades = [
                log for log in trade_logs if log.entity_id == entity.entity_id
            ]
            
            if entity_trades:
                entity_patterns[str(entity.entity_id)] = {
                    "total_trades": len(entity_trades),
                    "trade_frequency": len(entity_trades) / ((period_end - period_start).days or 1),
                    "personality": entity.metadata.get("personality_profile", "unknown"),
                    "risk_profile": entity.metadata.get("risk_tolerance", 0.5)
                }
        
        # Check for suspicious patterns
        suspicious_patterns = []
        
        # Check for simultaneous trades
        time_groups = {}
        for log in trade_logs:
            time_key = log.created_at.replace(second=0, microsecond=0)
            if time_key not in time_groups:
                time_groups[time_key] = []
            time_groups[time_key].append(log.entity_id)
        
        for time_key, entity_list in time_groups.items():
            if len(set(entity_list)) > len(entities) * 0.5:
                suspicious_patterns.append({
                    "type": "simultaneous_trades",
                    "timestamp": time_key.isoformat(),
                    "entities_involved": len(set(entity_list))
                })
        
        return {
            "total_trades": len(trade_logs),
            "entities_trading": len(entity_patterns),
            "entity_patterns": entity_patterns,
            "suspicious_patterns": suspicious_patterns,
            "pattern_diversity_score": self._calculate_pattern_diversity(entity_patterns)
        }
    
    async def _generate_audit_summary(
        self,
        entities: List[LegalEntity],
        period_start: datetime,
        period_end: datetime
    ) -> Dict[str, Any]:
        """Generate audit trail summary for entities."""
        entity_ids = [e.entity_id for e in entities]
        summaries = {}
        
        for entity_id in entity_ids:
            summary = await self.audit_service.generate_audit_summary(
                entity_id,
                period_days=(period_end - period_start).days
            )
            summaries[str(entity_id)] = summary
        
        # Aggregate results
        total_logs = sum(s.get("total_logs", 0) for s in summaries.values())
        all_valid = all(s.get("integrity_valid", False) for s in summaries.values())
        
        return {
            "total_audit_logs": total_logs,
            "integrity_valid": all_valid,
            "entity_summaries": summaries,
            "coverage_complete": all(
                s.get("coverage_complete", False) for s in summaries.values()
            ),
            "average_logs_per_entity": total_logs / len(entities) if entities else 0
        }
    
    async def _check_regulatory_compliance(
        self,
        entities: List[LegalEntity]
    ) -> Dict[str, Any]:
        """Check regulatory compliance for all entities."""
        compliance_results = {}
        
        for entity in entities:
            # Check ToS compliance
            tos_compliance = await self.tos_manager.check_compliance(entity.entity_id)
            
            # Check geographic compliance
            geo_restrictions = await self.geographic_service.get_entity_restrictions(
                entity.entity_id
            )
            
            # Check entity compliance status
            entity_compliance = await self.entity_manager.check_entity_compliance(
                entity.entity_id
            )
            
            compliance_results[str(entity.entity_id)] = {
                "entity_name": entity.entity_name,
                "jurisdiction": entity.jurisdiction,
                "tos_compliant": tos_compliance["compliant"],
                "geographic_compliant": geo_restrictions["restriction_level"] != "prohibited",
                "overall_compliant": entity_compliance.is_compliant,
                "issues": entity_compliance.issues
            }
        
        # Calculate aggregate compliance
        total_compliant = sum(
            1 for r in compliance_results.values() if r["overall_compliant"]
        )
        
        return {
            "total_entities": len(entities),
            "compliant_entities": total_compliant,
            "compliance_rate": total_compliant / len(entities) if entities else 0,
            "entity_compliance": compliance_results,
            "jurisdictions": list(set(e.jurisdiction for e in entities))
        }
    
    async def _calculate_timing_correlation(
        self,
        entity_decisions: Dict[UUID, List[DecisionLog]]
    ) -> float:
        """Calculate correlation in decision timing between entities."""
        if len(entity_decisions) < 2:
            return 0.0
        
        # Extract timestamps for each entity
        entity_times = {}
        for entity_id, decisions in entity_decisions.items():
            entity_times[entity_id] = [
                d.timestamp.timestamp() for d in decisions
            ]
        
        # Calculate pairwise correlations
        correlations = []
        entity_ids = list(entity_times.keys())
        
        for i in range(len(entity_ids)):
            for j in range(i + 1, len(entity_ids)):
                times1 = entity_times[entity_ids[i]]
                times2 = entity_times[entity_ids[j]]
                
                # Find common time windows
                min_len = min(len(times1), len(times2))
                if min_len > 1:
                    # Calculate time differences
                    diffs1 = np.diff(times1[:min_len])
                    diffs2 = np.diff(times2[:min_len])
                    
                    if len(diffs1) > 0 and len(diffs2) > 0:
                        correlation = np.corrcoef(diffs1, diffs2)[0, 1]
                        if not np.isnan(correlation):
                            correlations.append(abs(correlation))
        
        return np.mean(correlations) if correlations else 0.0
    
    async def _calculate_decision_uniqueness(
        self,
        decisions: List[DecisionLog]
    ) -> float:
        """Calculate uniqueness score for decisions."""
        if not decisions:
            return 1.0
        
        # Extract unique factors
        unique_factors = set()
        total_factors = 0
        
        for decision in decisions:
            if decision.independent_factors:
                unique_seed = decision.independent_factors.get("unique_seed")
                if unique_seed:
                    unique_factors.add(unique_seed)
                    total_factors += 1
        
        if total_factors == 0:
            return 0.0
        
        return len(unique_factors) / total_factors
    
    async def _calculate_timing_variance(
        self,
        entity_decisions: Dict[UUID, List[DecisionLog]]
    ) -> float:
        """Calculate variance in decision timing."""
        all_delays = []
        
        for decisions in entity_decisions.values():
            if len(decisions) > 1:
                timestamps = sorted([d.timestamp for d in decisions])
                for i in range(1, len(timestamps)):
                    delay = (timestamps[i] - timestamps[i-1]).total_seconds()
                    all_delays.append(delay)
        
        if not all_delays:
            return 0.0
        
        return statistics.stdev(all_delays) if len(all_delays) > 1 else 0.0
    
    async def _perform_independence_test(
        self,
        entity_decisions: Dict[UUID, List[DecisionLog]]
    ) -> Dict[str, Any]:
        """Perform statistical test for independence."""
        if len(entity_decisions) < 2:
            return {"test": "insufficient_data", "p_value": 1.0, "independent": True}
        
        # Prepare data for chi-square test
        entity_ids = list(entity_decisions.keys())
        
        # Create contingency table for decision types
        decision_types = set()
        for decisions in entity_decisions.values():
            for d in decisions:
                decision_types.add(d.decision_type)
        
        if not decision_types:
            return {"test": "no_decisions", "p_value": 1.0, "independent": True}
        
        # Build contingency table
        contingency_table = []
        for entity_id in entity_ids:
            entity_counts = []
            for decision_type in decision_types:
                count = sum(
                    1 for d in entity_decisions[entity_id]
                    if d.decision_type == decision_type
                )
                entity_counts.append(count)
            contingency_table.append(entity_counts)
        
        # Perform chi-square test
        try:
            chi2, p_value, dof, expected = stats.chi2_contingency(contingency_table)
            
            return {
                "test": "chi_square",
                "chi2_statistic": chi2,
                "p_value": p_value,
                "degrees_of_freedom": dof,
                "independent": p_value > 0.05,
                "interpretation": "Entities show independent behavior" if p_value > 0.05 
                                else "Potential correlation detected"
            }
        except:
            return {"test": "error", "p_value": 1.0, "independent": True}
    
    def _calculate_average_delay(
        self,
        entity_decisions: Dict[UUID, List[DecisionLog]]
    ) -> float:
        """Calculate average delay between entity decisions."""
        if len(entity_decisions) < 2:
            return 0.0
        
        # Get all decision timestamps across entities
        all_timestamps = []
        for entity_id, decisions in entity_decisions.items():
            for decision in decisions:
                all_timestamps.append((decision.timestamp, entity_id))
        
        all_timestamps.sort()
        
        # Calculate delays between different entities
        delays = []
        for i in range(1, len(all_timestamps)):
            if all_timestamps[i][1] != all_timestamps[i-1][1]:
                delay = (all_timestamps[i][0] - all_timestamps[i-1][0]).total_seconds()
                delays.append(delay)
        
        return statistics.mean(delays) if delays else 0.0
    
    def _get_personality_distribution(
        self,
        decisions: List[DecisionLog]
    ) -> Dict[str, int]:
        """Get distribution of personality profiles in decisions."""
        distribution = {}
        for decision in decisions:
            personality = decision.personality_profile or "unknown"
            distribution[personality] = distribution.get(personality, 0) + 1
        return distribution
    
    def _calculate_pattern_diversity(
        self,
        entity_patterns: Dict[str, Dict[str, Any]]
    ) -> float:
        """Calculate diversity score for trading patterns."""
        if not entity_patterns:
            return 0.0
        
        # Extract features
        frequencies = []
        personalities = set()
        risk_profiles = []
        
        for pattern in entity_patterns.values():
            frequencies.append(pattern.get("trade_frequency", 0))
            personalities.add(pattern.get("personality", "unknown"))
            risk_profiles.append(pattern.get("risk_profile", 0.5))
        
        # Calculate diversity metrics
        freq_variance = statistics.stdev(frequencies) if len(frequencies) > 1 else 0
        personality_diversity = len(personalities) / len(entity_patterns)
        risk_variance = statistics.stdev(risk_profiles) if len(risk_profiles) > 1 else 0
        
        # Combine metrics
        diversity_score = (
            min(1.0, freq_variance / 10) * 0.3 +
            personality_diversity * 0.4 +
            min(1.0, risk_variance * 2) * 0.3
        )
        
        return diversity_score
    
    def _calculate_compliance_score(
        self,
        independence_metrics: Dict[str, Any],
        trading_patterns: Dict[str, Any],
        audit_summary: Dict[str, Any],
        regulatory_compliance: Dict[str, Any]
    ) -> float:
        """Calculate overall compliance score."""
        scores = []
        
        # Independence score
        if independence_metrics.get("independence_verified"):
            scores.append(1.0)
        else:
            correlation = independence_metrics.get("correlation_score", 1.0)
            scores.append(max(0, 1.0 - correlation))
        
        # Pattern diversity score
        diversity = trading_patterns.get("pattern_diversity_score", 0)
        scores.append(diversity)
        
        # Audit integrity score
        if audit_summary.get("integrity_valid"):
            scores.append(1.0)
        else:
            scores.append(0.5)
        
        # Regulatory compliance score
        compliance_rate = regulatory_compliance.get("compliance_rate", 0)
        scores.append(compliance_rate)
        
        # Calculate weighted average
        weights = [0.3, 0.2, 0.2, 0.3]  # Independence, Patterns, Audit, Regulatory
        weighted_score = sum(s * w for s, w in zip(scores, weights))
        
        return min(1.0, max(0.0, weighted_score))
    
    def _generate_recommendations(
        self,
        compliance_score: float,
        independence_metrics: Dict[str, Any],
        trading_patterns: Dict[str, Any],
        regulatory_compliance: Dict[str, Any]
    ) -> List[str]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []
        
        # Compliance score recommendations
        if compliance_score < 0.7:
            recommendations.append("Overall compliance score below threshold - immediate review required")
        elif compliance_score < 0.85:
            recommendations.append("Compliance score acceptable but improvements recommended")
        
        # Independence recommendations
        correlation = independence_metrics.get("correlation_score", 0)
        if correlation > 0.5:
            recommendations.append("High correlation detected - increase decision timing variance")
        
        uniqueness = independence_metrics.get("decision_uniqueness", 1)
        if uniqueness < 0.7:
            recommendations.append("Low decision uniqueness - enhance personality differentiation")
        
        # Pattern recommendations
        suspicious = trading_patterns.get("suspicious_patterns", [])
        if suspicious:
            recommendations.append(f"Suspicious patterns detected ({len(suspicious)}) - review and adjust")
        
        # Regulatory recommendations
        compliant_rate = regulatory_compliance.get("compliance_rate", 0)
        if compliant_rate < 1.0:
            non_compliant = regulatory_compliance.get("total_entities", 0) - \
                          regulatory_compliance.get("compliant_entities", 0)
            recommendations.append(f"{non_compliant} entities non-compliant - address issues immediately")
        
        # Audit recommendations
        if not independence_metrics.get("independence_verified"):
            recommendations.append("Entity independence not verified - implement additional variance")
        
        if not recommendations:
            recommendations.append("All compliance metrics within acceptable ranges - maintain current practices")
        
        return recommendations