"""
A/B Testing Framework

Provides gradual change validation through controlled testing, statistical analysis,
and automated promotion/rollback decisions for safe learning system evolution.
"""

import json
import hashlib
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Set, Any, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import random
import math
from pathlib import Path
import statistics

from learning_rollback_system import ModelMetrics, LearningSnapshot

logger = logging.getLogger(__name__)


class TestStatus(Enum):
    """A/B test status"""
    PLANNED = "planned"
    RUNNING = "running" 
    COMPLETED = "completed"
    ABORTED = "aborted"
    ROLLED_BACK = "rolled_back"
    PROMOTED = "promoted"


class TestDecision(Enum):
    """A/B test result decisions"""
    PROMOTE_TEST = "promote_test"
    ROLLBACK_TEST = "rollback_test"
    EXTEND_TEST = "extend_test"
    MANUAL_REVIEW = "manual_review"
    INCONCLUSIVE = "inconclusive"


class GroupType(Enum):
    """Test group types"""
    CONTROL = "control"
    TEST = "test"


@dataclass
class ModelChange:
    """Definition of a model change being tested"""
    change_id: str
    change_type: str  # parameter_adjustment, algorithm_update, feature_addition, etc.
    description: str
    implemented_at: datetime
    version: str
    
    # Change details
    parameters: Dict[str, Any]
    affected_components: List[str]
    expected_impact: str
    risk_level: str  # low, medium, high
    
    # Rollback information
    rollback_data: Dict[str, Any]
    can_rollback: bool


@dataclass
class TestGroup:
    """A/B test group configuration"""
    group_id: str
    group_type: GroupType
    account_ids: List[str]
    group_size: int
    
    # Performance tracking
    baseline_metrics: Optional[ModelMetrics] = None
    current_metrics: Optional[ModelMetrics] = None
    daily_metrics: List[ModelMetrics] = None
    
    # Changes applied (only for test groups)
    applied_changes: List[ModelChange] = None
    
    def __post_init__(self):
        if self.daily_metrics is None:
            self.daily_metrics = []
        if self.applied_changes is None:
            self.applied_changes = []


@dataclass
class StatisticalAnalysis:
    """Statistical analysis results for A/B test"""
    sample_size_control: int
    sample_size_test: int
    
    # Power analysis
    statistical_power: float  # 0-1, typically want > 0.8
    effect_size: float  # Cohen's d
    minimum_detectable_effect: float
    
    # Significance testing
    p_value: float
    confidence_interval: Tuple[float, float]
    confidence_level: float  # 0.95 = 95%
    statistically_significant: bool
    
    # Performance differences
    performance_difference_percent: float
    control_performance: float
    test_performance: float
    
    # Test validity
    validity_checks: Dict[str, bool]
    warnings: List[str]


@dataclass
class ABTestEvent:
    """Event in A/B test lifecycle"""
    event_id: str
    timestamp: datetime
    event_type: str  # created, started, stopped, promoted, rolled_back
    description: str
    triggered_by: str  # system, user_id
    
    # Event details
    event_data: Dict[str, Any]
    impact_assessment: Dict[str, Any]


@dataclass 
class ABTest:
    """Complete A/B test definition and tracking"""
    test_id: str
    test_name: str
    description: str
    
    # Test configuration
    start_date: datetime
    planned_end_date: datetime
    actual_end_date: Optional[datetime] = None
    rollout_percentage: float = 50.0  # Percentage in test group
    minimum_sample_size: int = 100
    confidence_level: float = 0.95
    minimum_effect_size: float = 0.1  # 10% improvement
    
    # Test groups
    control_group: TestGroup = None
    test_group: TestGroup = None
    
    # Statistical tracking
    statistical_analysis: Optional[StatisticalAnalysis] = None
    daily_analysis: List[StatisticalAnalysis] = None
    
    # Test results
    final_decision: Optional[TestDecision] = None
    decision_reason: str = ""
    decision_confidence: float = 0.0
    automated_decision: bool = False
    
    # Status and history
    status: TestStatus = TestStatus.PLANNED
    status_history: List[ABTestEvent] = None
    
    # Metadata
    created_by: str = "system"
    tags: List[str] = None
    
    def __post_init__(self):
        if self.daily_analysis is None:
            self.daily_analysis = []
        if self.status_history is None:
            self.status_history = []
        if self.tags is None:
            self.tags = []


class TestGroupAssignment:
    """Handles assignment of accounts to test groups"""
    
    def __init__(self, randomization_seed: Optional[int] = None):
        self.randomization_seed = randomization_seed or 42
        random.seed(self.randomization_seed)
        
    def assign_test_groups(self, available_accounts: List[str], 
                          test_percentage: float = 50.0,
                          exclusion_criteria: Optional[Dict[str, Any]] = None) -> Tuple[List[str], List[str]]:
        """Assign accounts to control and test groups"""
        try:
            # Apply exclusion criteria
            eligible_accounts = self._filter_eligible_accounts(available_accounts, exclusion_criteria)
            
            if len(eligible_accounts) < 10:
                raise ValueError(f"Insufficient eligible accounts: {len(eligible_accounts)} < 10")
            
            # Randomize account order
            randomized_accounts = eligible_accounts.copy()
            random.shuffle(randomized_accounts)
            
            # Calculate group sizes
            total_accounts = len(randomized_accounts)
            test_size = int(total_accounts * (test_percentage / 100.0))
            control_size = total_accounts - test_size
            
            # Assign groups
            test_accounts = randomized_accounts[:test_size]
            control_accounts = randomized_accounts[test_size:]
            
            logger.info(f"Assigned {len(control_accounts)} control, {len(test_accounts)} test accounts")
            
            return control_accounts, test_accounts
            
        except Exception as e:
            logger.error(f"Failed to assign test groups: {e}")
            raise
    
    def stratified_assignment(self, accounts_with_strata: Dict[str, Dict[str, Any]], 
                            test_percentage: float = 50.0) -> Tuple[List[str], List[str]]:
        """Assign accounts using stratified randomization to ensure balanced groups"""
        control_accounts = []
        test_accounts = []
        
        # Group accounts by strata (e.g., account size, risk level, region)
        strata_groups = self._group_by_strata(accounts_with_strata)
        
        for stratum, accounts in strata_groups.items():
            if len(accounts) < 2:
                continue  # Skip strata with too few accounts
                
            # Randomize within stratum
            stratum_accounts = list(accounts)
            random.shuffle(stratum_accounts)
            
            # Assign proportionally within stratum
            test_size = int(len(stratum_accounts) * (test_percentage / 100.0))
            
            stratum_test = stratum_accounts[:test_size]
            stratum_control = stratum_accounts[test_size:]
            
            test_accounts.extend(stratum_test)
            control_accounts.extend(stratum_control)
        
        return control_accounts, test_accounts
    
    def _filter_eligible_accounts(self, accounts: List[str], 
                                 exclusion_criteria: Optional[Dict[str, Any]]) -> List[str]:
        """Filter accounts based on eligibility criteria"""
        if not exclusion_criteria:
            return accounts
        
        eligible = []
        for account in accounts:
            # In production, this would check against account metadata
            # For now, simple filtering logic
            if self._meets_eligibility_criteria(account, exclusion_criteria):
                eligible.append(account)
        
        return eligible
    
    def _meets_eligibility_criteria(self, account: str, criteria: Dict[str, Any]) -> bool:
        """Check if account meets eligibility criteria"""
        # Mock implementation - in production, would check real account data
        if criteria.get("min_account_age_days"):
            # Mock: assume accounts with 'new' in name are too new
            if "new" in account.lower():
                return False
        
        if criteria.get("exclude_high_risk"):
            # Mock: assume accounts with 'risk' in name are high risk
            if "risk" in account.lower():
                return False
        
        return True
    
    def _group_by_strata(self, accounts_with_strata: Dict[str, Dict[str, Any]]) -> Dict[str, List[str]]:
        """Group accounts by stratification criteria"""
        strata_groups = {}
        
        for account_id, metadata in accounts_with_strata.items():
            # Create stratum key from relevant metadata
            stratum_key = f"{metadata.get('region', 'unknown')}_{metadata.get('risk_level', 'medium')}"
            
            if stratum_key not in strata_groups:
                strata_groups[stratum_key] = []
            
            strata_groups[stratum_key].append(account_id)
        
        return strata_groups


class StatisticalEngine:
    """Performs statistical analysis for A/B tests"""
    
    def __init__(self):
        self.default_confidence_level = 0.95
        self.minimum_sample_size = 30
    
    def analyze_test_results(self, control_metrics: List[ModelMetrics], 
                           test_metrics: List[ModelMetrics],
                           confidence_level: float = 0.95) -> StatisticalAnalysis:
        """Perform comprehensive statistical analysis of A/B test results"""
        try:
            if len(control_metrics) < self.minimum_sample_size or len(test_metrics) < self.minimum_sample_size:
                raise ValueError(f"Insufficient sample size: control={len(control_metrics)}, test={len(test_metrics)}")
            
            # Extract primary metric (Sharpe ratio) for analysis
            control_values = [m.sharpe_ratio for m in control_metrics]
            test_values = [m.sharpe_ratio for m in test_metrics]
            
            # Calculate basic statistics
            control_mean = statistics.mean(control_values)
            test_mean = statistics.mean(test_values)
            control_std = statistics.stdev(control_values) if len(control_values) > 1 else 0
            test_std = statistics.stdev(test_values) if len(test_values) > 1 else 0
            
            # Effect size (Cohen's d)
            pooled_std = math.sqrt(((len(control_values) - 1) * control_std**2 + 
                                  (len(test_values) - 1) * test_std**2) / 
                                 (len(control_values) + len(test_values) - 2))
            
            effect_size = (test_mean - control_mean) / pooled_std if pooled_std > 0 else 0
            
            # Statistical significance test (Welch's t-test)
            p_value = self._welch_t_test(control_values, test_values)
            
            # Confidence interval for difference
            confidence_interval = self._confidence_interval_difference(
                control_values, test_values, confidence_level
            )
            
            # Statistical power calculation
            statistical_power = self._calculate_power(
                effect_size, len(control_values), len(test_values), confidence_level
            )
            
            # Performance difference
            performance_diff = ((test_mean - control_mean) / control_mean * 100) if control_mean != 0 else 0
            
            # Minimum detectable effect
            min_detectable_effect = self._minimum_detectable_effect(
                len(control_values), len(test_values), statistical_power, confidence_level
            )
            
            # Validity checks
            validity_checks = self._perform_validity_checks(control_metrics, test_metrics)
            
            # Generate warnings
            warnings = self._generate_warnings(
                control_values, test_values, effect_size, statistical_power, validity_checks
            )
            
            return StatisticalAnalysis(
                sample_size_control=len(control_values),
                sample_size_test=len(test_values),
                statistical_power=statistical_power,
                effect_size=effect_size,
                minimum_detectable_effect=min_detectable_effect,
                p_value=p_value,
                confidence_interval=confidence_interval,
                confidence_level=confidence_level,
                statistically_significant=p_value < (1 - confidence_level),
                performance_difference_percent=performance_diff,
                control_performance=control_mean,
                test_performance=test_mean,
                validity_checks=validity_checks,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"Statistical analysis failed: {e}")
            raise
    
    def _welch_t_test(self, sample1: List[float], sample2: List[float]) -> float:
        """Perform Welch's t-test for unequal variances"""
        n1, n2 = len(sample1), len(sample2)
        mean1, mean2 = statistics.mean(sample1), statistics.mean(sample2)
        var1 = statistics.variance(sample1) if n1 > 1 else 0
        var2 = statistics.variance(sample2) if n2 > 1 else 0
        
        if var1 == 0 and var2 == 0:
            return 1.0 if mean1 == mean2 else 0.0
        
        # Welch's t-statistic
        t_stat = (mean1 - mean2) / math.sqrt(var1/n1 + var2/n2)
        
        # Degrees of freedom (Welch-Satterthwaite equation)
        df = (var1/n1 + var2/n2)**2 / ((var1/n1)**2/(n1-1) + (var2/n2)**2/(n2-1))
        
        # Approximate p-value using t-distribution (simplified)
        # In production, would use proper statistical library
        p_value = 2 * (1 - self._t_cdf(abs(t_stat), df))
        
        return max(0.0, min(1.0, p_value))
    
    def _t_cdf(self, t: float, df: float) -> float:
        """Simplified t-distribution CDF approximation"""
        # Very rough approximation - in production, use scipy.stats
        if df > 30:
            # Approximate with normal distribution for large df
            return 0.5 + 0.5 * math.erf(t / math.sqrt(2))
        else:
            # Simplified approximation for small df
            return 0.5 + 0.3 * math.atan(t / math.sqrt(df))
    
    def _confidence_interval_difference(self, sample1: List[float], sample2: List[float], 
                                      confidence_level: float) -> Tuple[float, float]:
        """Calculate confidence interval for difference in means"""
        n1, n2 = len(sample1), len(sample2)
        mean1, mean2 = statistics.mean(sample1), statistics.mean(sample2)
        var1 = statistics.variance(sample1) if n1 > 1 else 0
        var2 = statistics.variance(sample2) if n2 > 1 else 0
        
        diff = mean2 - mean1
        se_diff = math.sqrt(var1/n1 + var2/n2)
        
        # Critical value (approximate)
        alpha = 1 - confidence_level
        z_critical = 1.96  # Approximate for 95% CI
        
        margin_error = z_critical * se_diff
        
        return (diff - margin_error, diff + margin_error)
    
    def _calculate_power(self, effect_size: float, n1: int, n2: int, 
                        confidence_level: float) -> float:
        """Calculate statistical power"""
        # Simplified power calculation
        alpha = 1 - confidence_level
        
        # Approximate power calculation
        if abs(effect_size) < 0.1:
            return 0.1  # Low power for small effects
        elif abs(effect_size) < 0.3:
            return 0.5  # Medium power
        else:
            return min(0.95, 0.8 + abs(effect_size))  # High power for large effects
    
    def _minimum_detectable_effect(self, n1: int, n2: int, power: float, 
                                  confidence_level: float) -> float:
        """Calculate minimum detectable effect size"""
        # Simplified calculation based on sample size
        total_n = n1 + n2
        
        if total_n < 50:
            return 0.5  # Large effect needed for small samples
        elif total_n < 200:
            return 0.3  # Medium effect
        else:
            return 0.1  # Small effect detectable with large samples
    
    def _perform_validity_checks(self, control_metrics: List[ModelMetrics], 
                                test_metrics: List[ModelMetrics]) -> Dict[str, bool]:
        """Perform various validity checks on the test data"""
        checks = {}
        
        # Check for sufficient sample size
        checks["sufficient_sample_size"] = (len(control_metrics) >= self.minimum_sample_size and 
                                          len(test_metrics) >= self.minimum_sample_size)
        
        # Check for balanced group sizes
        size_ratio = min(len(control_metrics), len(test_metrics)) / max(len(control_metrics), len(test_metrics))
        checks["balanced_groups"] = size_ratio >= 0.7
        
        # Check for normal-ish distribution (simplified)
        control_values = [m.sharpe_ratio for m in control_metrics]
        test_values = [m.sharpe_ratio for m in test_metrics]
        
        checks["control_variance_reasonable"] = statistics.variance(control_values) < 10 if len(control_values) > 1 else True
        checks["test_variance_reasonable"] = statistics.variance(test_values) < 10 if len(test_values) > 1 else True
        
        # Check for data quality
        checks["no_extreme_outliers"] = self._check_outliers(control_values + test_values)
        
        return checks
    
    def _check_outliers(self, values: List[float]) -> bool:
        """Simple outlier detection"""
        if len(values) < 4:
            return True
        
        q1 = statistics.quantiles(values, n=4)[0]
        q3 = statistics.quantiles(values, n=4)[2]
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        outliers = [v for v in values if v < lower_bound or v > upper_bound]
        return len(outliers) / len(values) < 0.1  # Less than 10% outliers
    
    def _generate_warnings(self, control_values: List[float], test_values: List[float],
                          effect_size: float, statistical_power: float,
                          validity_checks: Dict[str, bool]) -> List[str]:
        """Generate warnings about test validity"""
        warnings = []
        
        if not validity_checks.get("sufficient_sample_size", True):
            warnings.append("Sample size may be insufficient for reliable results")
        
        if not validity_checks.get("balanced_groups", True):
            warnings.append("Test groups are imbalanced - results may be biased")
        
        if statistical_power < 0.8:
            warnings.append(f"Statistical power is low ({statistical_power:.2f}) - test may miss real effects")
        
        if abs(effect_size) < 0.1:
            warnings.append("Effect size is very small - practical significance questionable")
        
        if not validity_checks.get("no_extreme_outliers", True):
            warnings.append("Extreme outliers detected - may affect result validity")
        
        return warnings


class ABTestFramework:
    """Main A/B testing framework coordinating all components"""
    
    def __init__(self, storage_path: str = "./ab_tests"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.group_assignment = TestGroupAssignment()
        self.statistical_engine = StatisticalEngine()
        
        # Test registry
        self.active_tests: Dict[str, ABTest] = {}
        self.completed_tests: Dict[str, ABTest] = {}
        
        # Configuration
        self.auto_decision_enabled = True
        self.daily_analysis_enabled = True
        
        # Load existing tests
        self._load_existing_tests()
    
    def create_ab_test(self, test_name: str, description: str,
                      model_changes: List[ModelChange],
                      available_accounts: List[str],
                      test_config: Optional[Dict[str, Any]] = None) -> str:
        """Create and start a new A/B test"""
        try:
            # Generate test ID
            test_id = f"test_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            
            # Apply default configuration
            config = {
                "test_percentage": 50.0,
                "minimum_sample_size": 100,
                "confidence_level": 0.95,
                "minimum_effect_size": 0.1,
                "duration_days": 14
            }
            if test_config:
                config.update(test_config)
            
            # Assign test groups
            control_accounts, test_accounts = self.group_assignment.assign_test_groups(
                available_accounts, config["test_percentage"]
            )
            
            # Create test groups
            control_group = TestGroup(
                group_id=f"{test_id}_control",
                group_type=GroupType.CONTROL,
                account_ids=control_accounts,
                group_size=len(control_accounts)
            )
            
            test_group = TestGroup(
                group_id=f"{test_id}_test",
                group_type=GroupType.TEST,
                account_ids=test_accounts,
                group_size=len(test_accounts),
                applied_changes=model_changes
            )
            
            # Create A/B test
            ab_test = ABTest(
                test_id=test_id,
                test_name=test_name,
                description=description,
                start_date=datetime.utcnow(),
                planned_end_date=datetime.utcnow() + timedelta(days=config["duration_days"]),
                rollout_percentage=config["test_percentage"],
                minimum_sample_size=config["minimum_sample_size"],
                confidence_level=config["confidence_level"],
                minimum_effect_size=config["minimum_effect_size"],
                control_group=control_group,
                test_group=test_group,
                status=TestStatus.PLANNED,
                created_by="system"
            )
            
            # Apply changes to test group
            self._apply_changes_to_test_group(test_group, model_changes)
            
            # Start test
            self._start_test(ab_test)
            
            # Store test
            self._store_test(ab_test)
            self.active_tests[test_id] = ab_test
            
            logger.info(f"Created A/B test: {test_id} with {len(control_accounts)} control, {len(test_accounts)} test accounts")
            
            return test_id
            
        except Exception as e:
            logger.error(f"Failed to create A/B test: {e}")
            raise
    
    def update_test_metrics(self, test_id: str, 
                           control_metrics: List[ModelMetrics],
                           test_metrics: List[ModelMetrics]) -> bool:
        """Update test metrics and perform analysis"""
        try:
            if test_id not in self.active_tests:
                raise ValueError(f"Test not found: {test_id}")
            
            test = self.active_tests[test_id]
            
            # Update group metrics
            if control_metrics:
                test.control_group.current_metrics = control_metrics[-1]  # Latest metrics
                test.control_group.daily_metrics.extend(control_metrics)
            
            if test_metrics:
                test.test_group.current_metrics = test_metrics[-1]
                test.test_group.daily_metrics.extend(test_metrics)
            
            # Perform statistical analysis if we have sufficient data
            if (len(test.control_group.daily_metrics) >= test.minimum_sample_size and
                len(test.test_group.daily_metrics) >= test.minimum_sample_size):
                
                try:
                    analysis = self.statistical_engine.analyze_test_results(
                        test.control_group.daily_metrics,
                        test.test_group.daily_metrics,
                        test.confidence_level
                    )
                    
                    test.statistical_analysis = analysis
                    test.daily_analysis.append(analysis)
                    
                    # Check for auto-decision
                    if self.auto_decision_enabled and test.status == TestStatus.RUNNING:
                        decision = self._make_automated_decision(test, analysis)
                        if decision != TestDecision.INCONCLUSIVE:
                            self._execute_test_decision(test, decision, automated=True)
                except Exception as analysis_error:
                    logger.warning(f"Statistical analysis failed for {test_id}: {analysis_error}")
            
            # Update storage
            self._store_test(test)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update test metrics for {test_id}: {e}")
            raise  # Re-raise the exception instead of returning False
    
    def make_test_decision(self, test_id: str, manual_decision: Optional[TestDecision] = None) -> TestDecision:
        """Make decision on A/B test (manual or automated)"""
        try:
            if test_id not in self.active_tests:
                raise ValueError(f"Test not found: {test_id}")
            
            test = self.active_tests[test_id]
            
            if manual_decision:
                decision = manual_decision
                automated = False
            else:
                if not test.statistical_analysis:
                    raise ValueError("No statistical analysis available for decision")
                decision = self._make_automated_decision(test, test.statistical_analysis)
                automated = True
            
            # Execute decision
            self._execute_test_decision(test, decision, automated)
            
            return decision
            
        except Exception as e:
            logger.error(f"Failed to make test decision for {test_id}: {e}")
            raise
    
    def get_test_status(self, test_id: str) -> Dict[str, Any]:
        """Get comprehensive test status and metrics"""
        try:
            test = self.active_tests.get(test_id) or self.completed_tests.get(test_id)
            if not test:
                raise ValueError(f"Test not found: {test_id}")
            
            status = {
                "test_info": {
                    "test_id": test.test_id,
                    "test_name": test.test_name,
                    "description": test.description,
                    "status": test.status.value,
                    "start_date": test.start_date.isoformat(),
                    "planned_end_date": test.planned_end_date.isoformat(),
                    "actual_end_date": test.actual_end_date.isoformat() if test.actual_end_date else None
                },
                "groups": {
                    "control": {
                        "size": test.control_group.group_size,
                        "account_count": len(test.control_group.account_ids),
                        "current_metrics": asdict(test.control_group.current_metrics) if test.control_group.current_metrics else None,
                        "data_points": len(test.control_group.daily_metrics)
                    },
                    "test": {
                        "size": test.test_group.group_size,
                        "account_count": len(test.test_group.account_ids),
                        "current_metrics": asdict(test.test_group.current_metrics) if test.test_group.current_metrics else None,
                        "data_points": len(test.test_group.daily_metrics),
                        "changes_applied": len(test.test_group.applied_changes)
                    }
                },
                "analysis": asdict(test.statistical_analysis) if test.statistical_analysis else None,
                "decision": {
                    "final_decision": test.final_decision.value if test.final_decision else None,
                    "decision_reason": test.decision_reason,
                    "decision_confidence": test.decision_confidence,
                    "automated_decision": test.automated_decision
                }
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get test status for {test_id}: {e}")
            raise
    
    def get_framework_analytics(self) -> Dict[str, Any]:
        """Get A/B testing framework analytics"""
        all_tests = list(self.active_tests.values()) + list(self.completed_tests.values())
        
        analytics = {
            "summary": {
                "total_tests": len(all_tests),
                "active_tests": len(self.active_tests),
                "completed_tests": len(self.completed_tests),
                "successful_promotions": len([t for t in all_tests if t.final_decision == TestDecision.PROMOTE_TEST]),
                "rollbacks": len([t for t in all_tests if t.final_decision == TestDecision.ROLLBACK_TEST])
            },
            "performance": {
                "average_test_duration_days": self._calculate_average_test_duration(all_tests),
                "success_rate": self._calculate_success_rate(all_tests),
                "automated_decision_rate": len([t for t in all_tests if t.automated_decision]) / max(1, len(all_tests))
            },
            "statistical_quality": {
                "average_statistical_power": self._calculate_average_power(all_tests),
                "tests_with_sufficient_sample": len([t for t in all_tests 
                                                   if t.statistical_analysis and 
                                                   t.statistical_analysis.sample_size_control >= t.minimum_sample_size])
            }
        }
        
        return analytics
    
    def _apply_changes_to_test_group(self, test_group: TestGroup, changes: List[ModelChange]) -> None:
        """Apply model changes to test group accounts"""
        # In production, this would actually apply the changes to the models
        # For now, just record what changes should be applied
        test_group.applied_changes = changes
        logger.info(f"Applied {len(changes)} changes to test group {test_group.group_id}")
    
    def _start_test(self, test: ABTest) -> None:
        """Start the A/B test"""
        test.status = TestStatus.RUNNING
        
        # Create start event
        start_event = ABTestEvent(
            event_id=f"start_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.utcnow(),
            event_type="started",
            description=f"A/B test {test.test_name} started",
            triggered_by="system",
            event_data={"test_percentage": test.rollout_percentage},
            impact_assessment={"accounts_affected": len(test.test_group.account_ids)}
        )
        
        test.status_history.append(start_event)
    
    def _make_automated_decision(self, test: ABTest, analysis: StatisticalAnalysis) -> TestDecision:
        """Make automated decision based on statistical analysis"""
        # Check if test duration is completed
        test_completed = datetime.utcnow() >= test.planned_end_date
        
        if not test_completed:
            # Early stopping conditions - only for very strong signals
            if analysis.statistically_significant and analysis.statistical_power > 0.9:
                if analysis.performance_difference_percent > test.minimum_effect_size * 200:  # 2x minimum for early stop
                    if analysis.test_performance > analysis.control_performance:
                        return TestDecision.PROMOTE_TEST
                elif analysis.performance_difference_percent < -test.minimum_effect_size * 200:
                    return TestDecision.ROLLBACK_TEST
            
            # Continue running if not conclusive
            return TestDecision.INCONCLUSIVE
        
        # Test duration completed - make final decision
        if not analysis.statistically_significant:
            if analysis.statistical_power < 0.8:
                return TestDecision.EXTEND_TEST
            else:
                return TestDecision.INCONCLUSIVE
        
        # Statistically significant result
        if analysis.performance_difference_percent > test.minimum_effect_size * 100:
            return TestDecision.PROMOTE_TEST
        elif analysis.performance_difference_percent < -test.minimum_effect_size * 100:
            return TestDecision.ROLLBACK_TEST
        else:
            return TestDecision.INCONCLUSIVE
    
    def _execute_test_decision(self, test: ABTest, decision: TestDecision, automated: bool) -> None:
        """Execute the test decision"""
        test.final_decision = decision
        test.automated_decision = automated
        test.actual_end_date = datetime.utcnow()
        
        if decision == TestDecision.PROMOTE_TEST:
            test.status = TestStatus.PROMOTED
            test.decision_reason = "Test group significantly outperformed control group"
            test.decision_confidence = test.statistical_analysis.confidence_level if test.statistical_analysis else 0.9
            # In production: apply changes to all accounts
            
        elif decision == TestDecision.ROLLBACK_TEST:
            test.status = TestStatus.ROLLED_BACK  
            test.decision_reason = "Test group underperformed or showed negative results"
            test.decision_confidence = test.statistical_analysis.confidence_level if test.statistical_analysis else 0.9
            # In production: revert changes from test accounts
            
        elif decision == TestDecision.EXTEND_TEST:
            test.planned_end_date = datetime.utcnow() + timedelta(days=7)  # Extend by one week
            test.decision_reason = "Insufficient power or data - extending test duration"
            return  # Don't move to completed
            
        else:
            test.status = TestStatus.COMPLETED
            test.decision_reason = "Test completed but results were inconclusive"
            test.decision_confidence = 0.5
        
        # Move to completed tests
        if test.test_id in self.active_tests:
            del self.active_tests[test.test_id]
            self.completed_tests[test.test_id] = test
        
        # Create decision event
        decision_event = ABTestEvent(
            event_id=f"decision_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.utcnow(),
            event_type=decision.value,
            description=f"Test decision: {decision.value}",
            triggered_by="system" if automated else "manual",
            event_data={"decision": decision.value, "automated": automated},
            impact_assessment={"confidence": test.decision_confidence}
        )
        
        test.status_history.append(decision_event)
        
        logger.info(f"Executed test decision for {test.test_id}: {decision.value}")
    
    def _store_test(self, test: ABTest) -> None:
        """Store test data to disk"""
        test_file = self.storage_path / f"{test.test_id}.json"
        
        # Convert to JSON-serializable format
        test_data = asdict(test)
        
        with open(test_file, 'w') as f:
            json.dump(test_data, f, indent=2, default=str)
    
    def _load_existing_tests(self) -> None:
        """Load existing tests from storage"""
        if not self.storage_path.exists():
            return
        
        for test_file in self.storage_path.glob("test_*.json"):
            try:
                with open(test_file, 'r') as f:
                    test_data = json.load(f)
                
                # Reconstruct test object (simplified)
                test_id = test_data["test_id"]
                status = TestStatus(test_data["status"])
                
                if status in [TestStatus.RUNNING, TestStatus.PLANNED]:
                    # Simplified reconstruction - in production would be more complete
                    pass
                    
            except Exception as e:
                logger.warning(f"Failed to load test {test_file}: {e}")
    
    def _calculate_average_test_duration(self, tests: List[ABTest]) -> float:
        """Calculate average test duration in days"""
        completed_tests = [t for t in tests if t.actual_end_date]
        if not completed_tests:
            return 0.0
        
        durations = [(t.actual_end_date - t.start_date).days for t in completed_tests]
        return sum(durations) / len(durations)
    
    def _calculate_success_rate(self, tests: List[ABTest]) -> float:
        """Calculate rate of successful test promotions"""
        decided_tests = [t for t in tests if t.final_decision]
        if not decided_tests:
            return 0.0
        
        successful = len([t for t in decided_tests if t.final_decision == TestDecision.PROMOTE_TEST])
        return successful / len(decided_tests)
    
    def _calculate_average_power(self, tests: List[ABTest]) -> float:
        """Calculate average statistical power of completed tests"""
        tests_with_analysis = [t for t in tests if t.statistical_analysis]
        if not tests_with_analysis:
            return 0.0
        
        powers = [t.statistical_analysis.statistical_power for t in tests_with_analysis]
        return sum(powers) / len(powers)