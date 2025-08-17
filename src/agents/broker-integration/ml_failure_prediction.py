"""
Machine Learning Integration for Predictive Failure Detection
Future Enhancement: ML-based failure prediction and prevention
"""
import asyncio
import logging
import time
import json
import pickle
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import warnings

# Suppress sklearn warnings for clean output
warnings.filterwarnings('ignore', category=UserWarning)

logger = logging.getLogger(__name__)


class PredictionModel(Enum):
    """Available ML models for failure prediction"""
    LOGISTIC_REGRESSION = "logistic_regression"
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"
    NEURAL_NETWORK = "neural_network"
    ENSEMBLE = "ensemble"


class FailureType(Enum):
    """Types of failures that can be predicted"""
    CONNECTION_FAILURE = "connection_failure"
    RATE_LIMIT_BREACH = "rate_limit_breach"
    AUTHENTICATION_FAILURE = "auth_failure"
    SERVER_ERROR = "server_error"
    TIMEOUT = "timeout"
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"


@dataclass
class FailureFeatures:
    """Feature vector for failure prediction"""
    timestamp: datetime
    
    # System metrics
    error_rate_1min: float = 0.0
    error_rate_5min: float = 0.0
    error_rate_15min: float = 0.0
    avg_response_time_1min: float = 0.0
    avg_response_time_5min: float = 0.0
    avg_response_time_15min: float = 0.0
    
    # Circuit breaker metrics
    circuit_breaker_failure_count: int = 0
    circuit_breaker_state: int = 0  # 0=CLOSED, 1=HALF_OPEN, 2=OPEN
    
    # Rate limiting metrics
    rate_limit_utilization: float = 0.0
    requests_per_second: float = 0.0
    queue_depth: int = 0
    
    # Service health metrics
    healthy_services_count: int = 0
    degraded_services_count: int = 0
    unavailable_services_count: int = 0
    
    # Time-based features
    hour_of_day: int = 0
    day_of_week: int = 0
    is_market_hours: bool = False
    
    # Historical patterns
    failures_last_hour: int = 0
    failures_last_day: int = 0
    time_since_last_failure: float = 0.0  # minutes
    
    def to_array(self) -> np.ndarray:
        """Convert features to numpy array for ML models"""
        return np.array([
            self.error_rate_1min,
            self.error_rate_5min,
            self.error_rate_15min,
            self.avg_response_time_1min,
            self.avg_response_time_5min,
            self.avg_response_time_15min,
            self.circuit_breaker_failure_count,
            self.circuit_breaker_state,
            self.rate_limit_utilization,
            self.requests_per_second,
            self.queue_depth,
            self.healthy_services_count,
            self.degraded_services_count,
            self.unavailable_services_count,
            self.hour_of_day,
            self.day_of_week,
            int(self.is_market_hours),
            self.failures_last_hour,
            self.failures_last_day,
            self.time_since_last_failure
        ])
        
    @property
    def feature_names(self) -> List[str]:
        """Get feature names for model interpretation"""
        return [
            'error_rate_1min', 'error_rate_5min', 'error_rate_15min',
            'avg_response_time_1min', 'avg_response_time_5min', 'avg_response_time_15min',
            'circuit_breaker_failure_count', 'circuit_breaker_state',
            'rate_limit_utilization', 'requests_per_second', 'queue_depth',
            'healthy_services_count', 'degraded_services_count', 'unavailable_services_count',
            'hour_of_day', 'day_of_week', 'is_market_hours',
            'failures_last_hour', 'failures_last_day', 'time_since_last_failure'
        ]


@dataclass
class FailurePrediction:
    """Prediction result from ML model"""
    failure_type: FailureType
    probability: float
    confidence: float
    time_horizon_minutes: int
    recommended_action: str
    features_used: FailureFeatures
    model_used: PredictionModel
    prediction_timestamp: datetime
    
    def to_dict(self) -> Dict:
        return {
            'failure_type': self.failure_type.value,
            'probability': self.probability,
            'confidence': self.confidence,
            'time_horizon_minutes': self.time_horizon_minutes,
            'recommended_action': self.recommended_action,
            'model_used': self.model_used.value,
            'prediction_timestamp': self.prediction_timestamp.isoformat()
        }


class FailurePredictionModel:
    """Base class for failure prediction models"""
    
    def __init__(self, model_type: PredictionModel):
        self.model_type = model_type
        self.model = None
        self.is_trained = False
        self.training_data: List[Tuple[FailureFeatures, bool]] = []
        self.feature_importance: Optional[Dict[str, float]] = None
        
    async def train(self, training_data: List[Tuple[FailureFeatures, bool]]):
        """Train the model with historical data"""
        self.training_data = training_data
        
        if len(training_data) < 100:
            logger.warning(f"Insufficient training data: {len(training_data)} samples")
            return
            
        # Prepare training data
        X = np.array([features.to_array() for features, _ in training_data])
        y = np.array([label for _, label in training_data])
        
        # Train model based on type
        await self._train_model(X, y)
        self.is_trained = True
        
    async def _train_model(self, X: np.ndarray, y: np.ndarray):
        """Train the specific model implementation"""
        try:
            if self.model_type == PredictionModel.LOGISTIC_REGRESSION:
                from sklearn.linear_model import LogisticRegression
                self.model = LogisticRegression(random_state=42)
                self.model.fit(X, y)
                
            elif self.model_type == PredictionModel.RANDOM_FOREST:
                from sklearn.ensemble import RandomForestClassifier
                self.model = RandomForestClassifier(
                    n_estimators=100, random_state=42, max_depth=10
                )
                self.model.fit(X, y)
                
                # Extract feature importance
                feature_names = self.training_data[0][0].feature_names
                importance_scores = self.model.feature_importances_
                self.feature_importance = dict(zip(feature_names, importance_scores))
                
            elif self.model_type == PredictionModel.GRADIENT_BOOSTING:
                from sklearn.ensemble import GradientBoostingClassifier
                self.model = GradientBoostingClassifier(
                    n_estimators=100, random_state=42, max_depth=6
                )
                self.model.fit(X, y)
                
            elif self.model_type == PredictionModel.NEURAL_NETWORK:
                from sklearn.neural_network import MLPClassifier
                self.model = MLPClassifier(
                    hidden_layer_sizes=(50, 25), random_state=42, max_iter=500
                )
                self.model.fit(X, y)
                
        except ImportError as e:
            logger.error(f"ML library not available: {e}")
            # Fallback to simple threshold-based model
            await self._train_fallback_model(X, y)
            
    async def _train_fallback_model(self, X: np.ndarray, y: np.ndarray):
        """Fallback model when sklearn is not available"""
        # Simple threshold-based model
        self.model = {
            'type': 'threshold',
            'thresholds': {
                'error_rate_threshold': 0.05,  # 5% error rate
                'response_time_threshold': 1000,  # 1 second
                'circuit_breaker_threshold': 3   # 3 failures
            }
        }
        
    async def predict(self, features: FailureFeatures) -> float:
        """Predict failure probability"""
        if not self.is_trained:
            return 0.0
            
        if isinstance(self.model, dict) and self.model.get('type') == 'threshold':
            return await self._predict_threshold(features)
        else:
            try:
                X = features.to_array().reshape(1, -1)
                probabilities = self.model.predict_proba(X)
                return float(probabilities[0][1])  # Probability of failure
            except Exception as e:
                logger.error(f"Model prediction error: {e}")
                return 0.0
                
    async def _predict_threshold(self, features: FailureFeatures) -> float:
        """Fallback threshold-based prediction"""
        thresholds = self.model['thresholds']
        risk_score = 0.0
        
        # Error rate risk
        if features.error_rate_1min > thresholds['error_rate_threshold']:
            risk_score += 0.4
            
        # Response time risk
        if features.avg_response_time_1min > thresholds['response_time_threshold']:
            risk_score += 0.3
            
        # Circuit breaker risk
        if features.circuit_breaker_failure_count >= thresholds['circuit_breaker_threshold']:
            risk_score += 0.3
            
        return min(1.0, risk_score)
        
    def save_model(self, path: Path):
        """Save trained model to disk"""
        model_data = {
            'model_type': self.model_type.value,
            'model': self.model,
            'is_trained': self.is_trained,
            'feature_importance': self.feature_importance
        }
        
        with open(path, 'wb') as f:
            pickle.dump(model_data, f)
            
    def load_model(self, path: Path):
        """Load trained model from disk"""
        try:
            with open(path, 'rb') as f:
                model_data = pickle.load(f)
                
            self.model = model_data['model']
            self.is_trained = model_data['is_trained']
            self.feature_importance = model_data.get('feature_importance')
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")


class FailurePredictionEngine:
    """Main engine for ML-based failure prediction"""
    
    def __init__(self):
        self.models: Dict[FailureType, FailurePredictionModel] = {}
        self.feature_collector = FeatureCollector()
        self.prediction_history: List[FailurePrediction] = []
        self.training_enabled = True
        self.prediction_threshold = 0.7  # Minimum probability to trigger action
        
        # Initialize models for each failure type
        self._initialize_models()
        
    def _initialize_models(self):
        """Initialize ML models for each failure type"""
        model_configs = {
            FailureType.CONNECTION_FAILURE: PredictionModel.RANDOM_FOREST,
            FailureType.RATE_LIMIT_BREACH: PredictionModel.LOGISTIC_REGRESSION,
            FailureType.AUTHENTICATION_FAILURE: PredictionModel.GRADIENT_BOOSTING,
            FailureType.SERVER_ERROR: PredictionModel.ENSEMBLE,
            FailureType.TIMEOUT: PredictionModel.RANDOM_FOREST,
            FailureType.CIRCUIT_BREAKER_OPEN: PredictionModel.NEURAL_NETWORK
        }
        
        for failure_type, model_type in model_configs.items():
            self.models[failure_type] = FailurePredictionModel(model_type)
            
    async def collect_training_data(self, 
                                  error_handler,
                                  circuit_breaker_manager,
                                  rate_limit_manager,
                                  degradation_manager) -> List[Tuple[FailureFeatures, bool]]:
        """Collect training data from system components"""
        training_data = []
        
        # Generate features for current state
        features = await self.feature_collector.collect_features(
            error_handler, circuit_breaker_manager, 
            rate_limit_manager, degradation_manager
        )
        
        # For training, we need historical data with known outcomes
        # This would typically be collected over time and stored
        # For now, simulate some training data based on current patterns
        
        return training_data
        
    async def train_models(self, 
                          error_handler,
                          circuit_breaker_manager, 
                          rate_limit_manager,
                          degradation_manager):
        """Train all prediction models"""
        if not self.training_enabled:
            return
            
        logger.info("Starting ML model training...")
        
        # Collect training data
        training_data = await self.collect_training_data(
            error_handler, circuit_breaker_manager,
            rate_limit_manager, degradation_manager
        )
        
        if len(training_data) < 50:
            logger.warning("Insufficient data for training, using baseline models")
            # Use pre-configured baseline models
            await self._setup_baseline_models()
            return
            
        # Train each model
        for failure_type, model in self.models.items():
            relevant_data = self._filter_training_data(training_data, failure_type)
            if len(relevant_data) >= 20:
                await model.train(relevant_data)
                logger.info(f"Trained {failure_type.value} prediction model")
                
    async def _setup_baseline_models(self):
        """Setup baseline models with reasonable defaults"""
        for failure_type, model in self.models.items():
            # Create minimal training data for baseline
            baseline_data = self._generate_baseline_training_data(failure_type)
            await model.train(baseline_data)
            
    def _generate_baseline_training_data(self, failure_type: FailureType) -> List[Tuple[FailureFeatures, bool]]:
        """Generate baseline training data for initial model"""
        data = []
        now = datetime.now(timezone.utc)
        
        # Generate synthetic examples
        for i in range(100):
            features = FailureFeatures(timestamp=now)
            
            # Set features based on failure type patterns
            if failure_type == FailureType.CONNECTION_FAILURE:
                features.error_rate_1min = 0.1 if i < 20 else 0.01
                features.avg_response_time_1min = 2000 if i < 20 else 500
                label = i < 20
                
            elif failure_type == FailureType.RATE_LIMIT_BREACH:
                features.rate_limit_utilization = 0.95 if i < 20 else 0.5
                features.requests_per_second = 150 if i < 20 else 50
                label = i < 20
                
            else:
                # Default pattern
                features.error_rate_1min = 0.08 if i < 20 else 0.02
                label = i < 20
                
            data.append((features, label))
            
        return data
        
    def _filter_training_data(self, data: List, failure_type: FailureType) -> List:
        """Filter training data relevant to specific failure type"""
        # This would implement logic to identify which historical events
        # correspond to which failure types
        return data  # Simplified for now
        
    async def predict_failures(self,
                             error_handler,
                             circuit_breaker_manager,
                             rate_limit_manager, 
                             degradation_manager) -> List[FailurePrediction]:
        """Generate failure predictions for all failure types"""
        # Collect current features
        features = await self.feature_collector.collect_features(
            error_handler, circuit_breaker_manager,
            rate_limit_manager, degradation_manager
        )
        
        predictions = []
        
        for failure_type, model in self.models.items():
            if not model.is_trained:
                continue
                
            probability = await model.predict(features)
            
            if probability >= self.prediction_threshold:
                prediction = FailurePrediction(
                    failure_type=failure_type,
                    probability=probability,
                    confidence=self._calculate_confidence(model, features),
                    time_horizon_minutes=self._estimate_time_horizon(failure_type, probability),
                    recommended_action=self._get_recommended_action(failure_type, probability),
                    features_used=features,
                    model_used=model.model_type,
                    prediction_timestamp=datetime.now(timezone.utc)
                )
                
                predictions.append(prediction)
                
        self.prediction_history.extend(predictions)
        return predictions
        
    def _calculate_confidence(self, model: FailurePredictionModel, features: FailureFeatures) -> float:
        """Calculate confidence in the prediction"""
        if not model.is_trained:
            return 0.0
            
        # Simple confidence based on feature importance and training data size
        base_confidence = min(0.9, len(model.training_data) / 1000)
        
        # Adjust based on feature quality
        if model.feature_importance:
            # Higher confidence if important features are present
            important_features = [k for k, v in model.feature_importance.items() if v > 0.1]
            confidence_boost = len(important_features) / len(model.feature_importance)
            base_confidence *= (1 + confidence_boost * 0.2)
            
        return min(0.95, base_confidence)
        
    def _estimate_time_horizon(self, failure_type: FailureType, probability: float) -> int:
        """Estimate time until failure is likely to occur"""
        # Base time horizons by failure type (in minutes)
        base_times = {
            FailureType.CONNECTION_FAILURE: 15,
            FailureType.RATE_LIMIT_BREACH: 5,
            FailureType.AUTHENTICATION_FAILURE: 30,
            FailureType.SERVER_ERROR: 10,
            FailureType.TIMEOUT: 8,
            FailureType.CIRCUIT_BREAKER_OPEN: 12
        }
        
        base_time = base_times.get(failure_type, 15)
        
        # Higher probability = shorter time horizon
        time_factor = 1.0 - (probability - 0.5) * 0.6  # Scale down for high probability
        return max(2, int(base_time * time_factor))
        
    def _get_recommended_action(self, failure_type: FailureType, probability: float) -> str:
        """Get recommended preventive action"""
        actions = {
            FailureType.CONNECTION_FAILURE: "Reduce connection pool size, enable connection retries",
            FailureType.RATE_LIMIT_BREACH: "Reduce request rate, enable adaptive rate limiting", 
            FailureType.AUTHENTICATION_FAILURE: "Refresh authentication tokens, check credentials",
            FailureType.SERVER_ERROR: "Enable graceful degradation, prepare fallback data",
            FailureType.TIMEOUT: "Reduce timeout thresholds, enable request queuing",
            FailureType.CIRCUIT_BREAKER_OPEN: "Reduce failure threshold, enable manual intervention"
        }
        
        base_action = actions.get(failure_type, "Monitor system closely")
        
        if probability > 0.9:
            base_action = f"URGENT: {base_action}"
        elif probability > 0.8:
            base_action = f"HIGH PRIORITY: {base_action}"
            
        return base_action
        
    def get_prediction_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary of recent predictions"""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        recent_predictions = [
            p for p in self.prediction_history 
            if p.prediction_timestamp >= cutoff
        ]
        
        summary = {
            'total_predictions': len(recent_predictions),
            'high_risk_predictions': len([p for p in recent_predictions if p.probability > 0.8]),
            'predictions_by_type': {},
            'average_confidence': 0.0,
            'recent_predictions': [p.to_dict() for p in recent_predictions[-10:]]
        }
        
        # Group by failure type
        for prediction in recent_predictions:
            failure_type = prediction.failure_type.value
            if failure_type not in summary['predictions_by_type']:
                summary['predictions_by_type'][failure_type] = 0
            summary['predictions_by_type'][failure_type] += 1
            
        # Calculate average confidence
        if recent_predictions:
            summary['average_confidence'] = sum(p.confidence for p in recent_predictions) / len(recent_predictions)
            
        return summary


class FeatureCollector:
    """Collects features from system components for ML models"""
    
    async def collect_features(self,
                             error_handler,
                             circuit_breaker_manager,
                             rate_limit_manager,
                             degradation_manager) -> FailureFeatures:
        """Collect current system features"""
        now = datetime.now(timezone.utc)
        
        features = FailureFeatures(timestamp=now)
        
        # Time-based features
        features.hour_of_day = now.hour
        features.day_of_week = now.weekday()
        features.is_market_hours = self._is_market_hours(now)
        
        # Error handler metrics
        if error_handler:
            error_stats = error_handler.get_error_statistics()
            features.failures_last_hour = error_stats.get('total_errors', 0)
            
        # Circuit breaker metrics
        if circuit_breaker_manager:
            cb_status = circuit_breaker_manager.get_all_status()
            for name, status in cb_status.items():
                features.circuit_breaker_failure_count = max(
                    features.circuit_breaker_failure_count,
                    status.get('failure_count', 0)
                )
                if status.get('state') == 'open':
                    features.circuit_breaker_state = 2
                elif status.get('state') == 'half_open':
                    features.circuit_breaker_state = 1
                    
        # Rate limiting metrics
        if rate_limit_manager:
            rate_status = rate_limit_manager.get_all_status()
            if 'global_oanda' in rate_status:
                global_status = rate_status['global_oanda']
                features.rate_limit_utilization = global_status.get('utilization_percentage', 0) / 100
                features.requests_per_second = global_status.get('requests_per_second', 0)
                
        # Degradation manager metrics
        if degradation_manager:
            system_status = degradation_manager.get_system_status()
            service_statuses = degradation_manager.get_service_statuses()
            
            for service_name, service_status in service_statuses.items():
                health = service_status.get('health', 'unknown')
                if health == 'healthy':
                    features.healthy_services_count += 1
                elif health == 'degraded':
                    features.degraded_services_count += 1
                elif health == 'unavailable':
                    features.unavailable_services_count += 1
                    
        return features
        
    def _is_market_hours(self, dt: datetime) -> bool:
        """Check if current time is during market hours"""
        # Simplified: Monday-Friday, 9 AM - 4 PM UTC
        if dt.weekday() >= 5:  # Weekend
            return False
        return 9 <= dt.hour < 16


# Global ML prediction engine instance
_global_ml_engine = FailurePredictionEngine()


def get_global_ml_engine() -> FailurePredictionEngine:
    """Get global ML prediction engine instance"""
    return _global_ml_engine