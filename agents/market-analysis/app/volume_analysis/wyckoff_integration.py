"""
Wyckoff-Volume Analysis Integration

Integrates comprehensive volume analysis with existing Wyckoff pattern detection
to enhance pattern confidence and signal quality as specified in Story 3.3.
"""

from typing import Dict, List, Tuple, Optional, Any
import pandas as pd
import numpy as np
from datetime import datetime
import logging

from .spike_detector import VolumeSpikeDetector
from .divergence_detector import VolumeDivergenceDetector
from .ad_line import AccumulationDistributionLine
from .vwap_analyzer import VWAPAnalyzer
from .volume_classifier import VolumeClassifier
from .volume_profile import VolumeProfileBuilder

logger = logging.getLogger(__name__)


class WyckoffVolumeIntegrator:
    """
    Integrates volume analysis components with Wyckoff pattern detection
    to provide enhanced pattern validation and confidence scoring.
    """
    
    def __init__(self):
        """Initialize volume analysis components."""
        self.spike_detector = VolumeSpikeDetector()
        self.divergence_detector = VolumeDivergenceDetector()
        self.ad_line_analyzer = AccumulationDistributionLine()
        self.vwap_analyzer = VWAPAnalyzer()
        self.volume_classifier = VolumeClassifier()
        self.volume_profiler = VolumeProfileBuilder()
        
        # Volume confirmation weights for different Wyckoff events
        self.wyckoff_volume_weights = {
            'accumulation': {
                'volume_on_strength': 0.25,
                'volume_dryup_weakness': 0.20,
                'ad_line_confirmation': 0.20,
                'smart_money_activity': 0.15,
                'vwap_support': 0.10,
                'volume_profile_poc': 0.10
            },
            'distribution': {
                'volume_on_weakness': 0.25,
                'volume_expansion_selling': 0.20,
                'ad_line_divergence': 0.20,
                'retail_activity': 0.15,
                'vwap_resistance': 0.10,
                'volume_profile_rejection': 0.10
            },
            'spring': {
                'volume_spike_recovery': 0.30,
                'volume_divergence': 0.25,
                'smart_money_absorption': 0.20,
                'vwap_reclaim': 0.15,
                'ad_line_support': 0.10
            },
            'upthrust': {
                'volume_climax': 0.30,
                'volume_divergence': 0.25,
                'retail_distribution': 0.20,
                'vwap_failure': 0.15,
                'ad_line_weakness': 0.10
            }
        }
    
    def enhance_wyckoff_pattern(self,
                              wyckoff_pattern: Dict,
                              price_data: pd.DataFrame,
                              volume_data: pd.Series) -> Dict:
        """
        Enhance a detected Wyckoff pattern with comprehensive volume analysis.
        
        Args:
            wyckoff_pattern: Detected Wyckoff pattern from existing engine
            price_data: OHLC price data
            volume_data: Volume data
            
        Returns:
            Enhanced pattern with volume confirmation analysis
        """
        if not wyckoff_pattern or len(price_data) != len(volume_data):
            return {'error': 'Invalid input data'}
        
        pattern_type = wyckoff_pattern.get('type', 'unknown')
        
        try:
            # Comprehensive volume analysis
            volume_analysis = self._perform_comprehensive_volume_analysis(
                price_data, volume_data
            )
            
            # Pattern-specific volume confirmation
            volume_confirmation = self._calculate_pattern_volume_confirmation(
                pattern_type, wyckoff_pattern, volume_analysis
            )
            
            # Enhanced confidence scoring
            enhanced_confidence = self._calculate_enhanced_confidence(
                wyckoff_pattern, volume_confirmation
            )
            
            # Generate volume-based signals
            volume_signals = self._generate_volume_enhanced_signals(
                pattern_type, volume_analysis, wyckoff_pattern
            )
            
            # Risk assessment with volume context
            risk_assessment = self._assess_volume_risk_factors(
                volume_analysis, wyckoff_pattern
            )
            
            # Create enhanced pattern
            enhanced_pattern = {
                **wyckoff_pattern,
                'volume_analysis': volume_analysis,
                'volume_confirmation': volume_confirmation,
                'enhanced_confidence': enhanced_confidence,
                'volume_signals': volume_signals,
                'risk_assessment': risk_assessment,
                'integration_timestamp': datetime.now().isoformat(),
                'volume_enhancement_applied': True
            }
            
            return enhanced_pattern
            
        except Exception as e:
            logger.error(f"Error enhancing Wyckoff pattern: {str(e)}")
            return {
                **wyckoff_pattern,
                'volume_enhancement_error': str(e),
                'volume_enhancement_applied': False
            }
    
    def _perform_comprehensive_volume_analysis(self,
                                             price_data: pd.DataFrame,
                                             volume_data: pd.Series) -> Dict:
        """
        Perform comprehensive volume analysis using all available components.
        """
        analysis_results = {}
        
        try:
            # Volume spike analysis
            spike_analysis = self.spike_detector.detect_volume_spikes(price_data, volume_data)
            analysis_results['spikes'] = spike_analysis
            
            # Volume divergence analysis
            divergence_analysis = self.divergence_detector.detect_divergences(price_data, volume_data)
            analysis_results['divergences'] = divergence_analysis
            
            # A/D Line analysis
            ad_analysis = self.ad_line_analyzer.calculate_ad_line(price_data, volume_data)
            analysis_results['accumulation_distribution'] = ad_analysis
            
            # VWAP analysis
            vwap_analysis = self.vwap_analyzer.calculate_vwap_with_bands(price_data, volume_data)
            analysis_results['vwap'] = vwap_analysis
            
            # Volume classification
            classification_analysis = self.volume_classifier.classify_volume_type(
                price_data, volume_data
            )
            analysis_results['classification'] = classification_analysis
            
            # Volume profile analysis
            profile_analysis = self.volume_profiler.build_volume_profile(price_data, volume_data)
            analysis_results['profile'] = profile_analysis
            
            # Summary metrics
            analysis_results['summary'] = self._create_analysis_summary(analysis_results)
            
        except Exception as e:
            logger.error(f"Error in comprehensive volume analysis: {str(e)}")
            analysis_results['error'] = str(e)
        
        return analysis_results
    
    def _calculate_pattern_volume_confirmation(self,
                                             pattern_type: str,
                                             wyckoff_pattern: Dict,
                                             volume_analysis: Dict) -> Dict:
        """
        Calculate volume confirmation score for specific Wyckoff pattern types.
        """
        if pattern_type not in self.wyckoff_volume_weights:
            return {'confirmation_score': 50, 'factors': [], 'note': 'Unknown pattern type'}
        
        weights = self.wyckoff_volume_weights[pattern_type]
        confirmation_factors = []
        total_score = 0.0
        
        try:
            # Pattern-specific volume confirmation logic
            if pattern_type == 'accumulation':
                total_score, confirmation_factors = self._confirm_accumulation_volume(
                    volume_analysis, weights
                )
                
            elif pattern_type == 'distribution':
                total_score, confirmation_factors = self._confirm_distribution_volume(
                    volume_analysis, weights
                )
                
            elif pattern_type == 'spring':
                total_score, confirmation_factors = self._confirm_spring_volume(
                    volume_analysis, weights, wyckoff_pattern
                )
                
            elif pattern_type == 'upthrust':
                total_score, confirmation_factors = self._confirm_upthrust_volume(
                    volume_analysis, weights, wyckoff_pattern
                )
                
            else:
                # General pattern confirmation
                total_score, confirmation_factors = self._confirm_general_volume(
                    volume_analysis, pattern_type
                )
            
        except Exception as e:
            logger.error(f"Error calculating volume confirmation: {str(e)}")
            return {
                'confirmation_score': 50,
                'factors': [],
                'error': str(e)
            }
        
        return {
            'confirmation_score': round(min(100, max(0, total_score)), 2),
            'factors': confirmation_factors,
            'pattern_type': pattern_type,
            'analysis_quality': self._assess_confirmation_quality(confirmation_factors)
        }
    
    def _confirm_accumulation_volume(self, volume_analysis: Dict, weights: Dict) -> Tuple[float, List[Dict]]:
        """Confirm accumulation pattern with volume analysis."""
        score = 0.0
        factors = []
        
        # Volume on strength analysis
        classification = volume_analysis.get('classification', {})
        smart_money_pct = classification.get('smart_money_periods', 0) / max(1, classification.get('total_periods', 1)) * 100
        
        if smart_money_pct > 60:
            strength_score = 80
            factors.append({
                'factor': 'volume_on_strength',
                'score': strength_score,
                'description': f'High smart money activity ({smart_money_pct:.1f}%)'
            })
        elif smart_money_pct > 40:
            strength_score = 60
            factors.append({
                'factor': 'volume_on_strength', 
                'score': strength_score,
                'description': f'Moderate smart money activity ({smart_money_pct:.1f}%)'
            })
        else:
            strength_score = 20
            factors.append({
                'factor': 'volume_on_strength',
                'score': strength_score,
                'description': f'Low smart money activity ({smart_money_pct:.1f}%)'
            })
        
        score += strength_score * weights['volume_on_strength']
        
        # A/D Line confirmation
        ad_analysis = volume_analysis.get('accumulation_distribution', {})
        ad_trend = ad_analysis.get('ad_trend', 'unknown')
        
        if ad_trend == 'uptrend':
            ad_score = 90
            factors.append({
                'factor': 'ad_line_confirmation',
                'score': ad_score,
                'description': 'A/D line supports accumulation'
            })
        elif ad_trend == 'sideways':
            ad_score = 60
            factors.append({
                'factor': 'ad_line_confirmation',
                'score': ad_score,
                'description': 'A/D line neutral during accumulation'
            })
        else:
            ad_score = 30
            factors.append({
                'factor': 'ad_line_confirmation',
                'score': ad_score,
                'description': 'A/D line diverges from accumulation'
            })
        
        score += ad_score * weights['ad_line_confirmation']
        
        # VWAP support analysis
        vwap_analysis = volume_analysis.get('vwap', {})
        current_position = vwap_analysis.get('current_position', {})
        position = current_position.get('position', 'unknown')
        
        if position in ['above_vwap', 'near_vwap']:
            vwap_score = 80
            factors.append({
                'factor': 'vwap_support',
                'score': vwap_score,
                'description': 'Price holding above VWAP during accumulation'
            })
        else:
            vwap_score = 40
            factors.append({
                'factor': 'vwap_support',
                'score': vwap_score,
                'description': 'Price below VWAP - weak accumulation support'
            })
        
        score += vwap_score * weights['vwap_support']
        
        # Add other accumulation factors...
        # Volume profile POC analysis
        profile_analysis = volume_analysis.get('profile', {})
        poc_data = profile_analysis.get('poc', {})
        poc_strength = poc_data.get('poc_strength', 0)
        
        if poc_strength > 70:
            poc_score = 85
        elif poc_strength > 40:
            poc_score = 65
        else:
            poc_score = 30
            
        factors.append({
            'factor': 'volume_profile_poc',
            'score': poc_score,
            'description': f'Volume profile POC strength: {poc_strength}'
        })
        
        score += poc_score * weights['volume_profile_poc']
        
        return score, factors
    
    def _confirm_distribution_volume(self, volume_analysis: Dict, weights: Dict) -> Tuple[float, List[Dict]]:
        """Confirm distribution pattern with volume analysis."""
        score = 0.0
        factors = []
        
        # Volume on weakness analysis
        classification = volume_analysis.get('classification', {})
        retail_pct = classification.get('retail_periods', 0) / max(1, classification.get('total_periods', 1)) * 100
        
        if retail_pct > 60:
            weakness_score = 80
            factors.append({
                'factor': 'volume_on_weakness',
                'score': weakness_score,
                'description': f'High retail activity suggests distribution ({retail_pct:.1f}%)'
            })
        else:
            weakness_score = 40
            factors.append({
                'factor': 'volume_on_weakness',
                'score': weakness_score,
                'description': f'Mixed activity during distribution ({retail_pct:.1f}%)'
            })
        
        score += weakness_score * weights['volume_on_weakness']
        
        # A/D Line divergence
        divergences = volume_analysis.get('divergences', {})
        bearish_divergences = divergences.get('bearish_divergences', [])
        
        if len(bearish_divergences) > 0:
            div_score = 85
            factors.append({
                'factor': 'ad_line_divergence',
                'score': div_score,
                'description': f'Bearish volume divergences detected: {len(bearish_divergences)}'
            })
        else:
            div_score = 30
            factors.append({
                'factor': 'ad_line_divergence',
                'score': div_score,
                'description': 'No significant volume divergences'
            })
        
        score += div_score * weights['ad_line_divergence']
        
        # Volume expansion on selling
        spikes = volume_analysis.get('spikes', {})
        recent_spikes = spikes.get('recent_spikes', [])
        distribution_spikes = [s for s in recent_spikes 
                             if s.get('classification', {}).get('type') == 'distribution']
        
        if len(distribution_spikes) > 0:
            expansion_score = 75
            factors.append({
                'factor': 'volume_expansion_selling',
                'score': expansion_score,
                'description': f'Distribution volume spikes detected: {len(distribution_spikes)}'
            })
        else:
            expansion_score = 35
            factors.append({
                'factor': 'volume_expansion_selling',
                'score': expansion_score,
                'description': 'Limited volume expansion on selling'
            })
        
        score += expansion_score * weights['volume_expansion_selling']
        
        return score, factors
    
    def _confirm_spring_volume(self, volume_analysis: Dict, weights: Dict, wyckoff_pattern: Dict) -> Tuple[float, List[Dict]]:
        """Confirm spring pattern with volume analysis."""
        score = 0.0
        factors = []
        
        # Volume spike on recovery
        spikes = volume_analysis.get('spikes', {})
        recent_spikes = spikes.get('recent_spikes', [])
        recovery_spikes = [s for s in recent_spikes 
                         if s.get('classification', {}).get('type') == 'accumulation']
        
        if len(recovery_spikes) > 0:
            avg_spike_strength = np.mean([s.get('alert_score', 0) for s in recovery_spikes])
            spike_score = min(90, avg_spike_strength)
            factors.append({
                'factor': 'volume_spike_recovery',
                'score': spike_score,
                'description': f'Volume spike on spring recovery (strength: {avg_spike_strength:.1f})'
            })
        else:
            spike_score = 25
            factors.append({
                'factor': 'volume_spike_recovery',
                'score': spike_score,
                'description': 'No significant volume spike on recovery'
            })
        
        score += spike_score * weights['volume_spike_recovery']
        
        # Volume divergence at spring low
        divergences = volume_analysis.get('divergences', {})
        bullish_divergences = divergences.get('bullish_divergences', [])
        
        if len(bullish_divergences) > 0:
            div_score = 80
            factors.append({
                'factor': 'volume_divergence',
                'score': div_score,
                'description': f'Bullish volume divergence at spring: {len(bullish_divergences)}'
            })
        else:
            div_score = 30
            factors.append({
                'factor': 'volume_divergence',
                'score': div_score,
                'description': 'No volume divergence confirmation'
            })
        
        score += div_score * weights['volume_divergence']
        
        # Smart money absorption
        classification = volume_analysis.get('classification', {})
        institutional_flow = classification.get('institutional_flow', {})
        flow_direction = institutional_flow.get('flow_direction', 'unknown')
        
        if flow_direction == 'net_accumulation':
            absorption_score = 85
            factors.append({
                'factor': 'smart_money_absorption',
                'score': absorption_score,
                'description': 'Smart money absorption detected at spring'
            })
        else:
            absorption_score = 40
            factors.append({
                'factor': 'smart_money_absorption',
                'score': absorption_score,
                'description': 'Mixed or no smart money absorption'
            })
        
        score += absorption_score * weights['smart_money_absorption']
        
        return score, factors
    
    def _confirm_upthrust_volume(self, volume_analysis: Dict, weights: Dict, wyckoff_pattern: Dict) -> Tuple[float, List[Dict]]:
        """Confirm upthrust pattern with volume analysis."""
        score = 0.0
        factors = []
        
        # Volume climax
        spikes = volume_analysis.get('spikes', {})
        extreme_spikes = [s for s in spikes.get('all_spikes', []) 
                        if s.get('severity') == 'extreme']
        
        if len(extreme_spikes) > 0:
            climax_score = 85
            factors.append({
                'factor': 'volume_climax',
                'score': climax_score,
                'description': f'Volume climax detected: {len(extreme_spikes)} extreme spikes'
            })
        else:
            climax_score = 35
            factors.append({
                'factor': 'volume_climax',
                'score': climax_score,
                'description': 'No volume climax at upthrust'
            })
        
        score += climax_score * weights['volume_climax']
        
        # Retail distribution activity
        classification = volume_analysis.get('classification', {})
        retail_pct = classification.get('retail_periods', 0) / max(1, classification.get('total_periods', 1)) * 100
        
        if retail_pct > 70:
            retail_score = 80
            factors.append({
                'factor': 'retail_distribution',
                'score': retail_score,
                'description': f'High retail activity at upthrust ({retail_pct:.1f}%)'
            })
        else:
            retail_score = 45
            factors.append({
                'factor': 'retail_distribution',
                'score': retail_score,
                'description': 'Mixed activity at upthrust'
            })
        
        score += retail_score * weights['retail_distribution']
        
        return score, factors
    
    def _confirm_general_volume(self, volume_analysis: Dict, pattern_type: str) -> Tuple[float, List[Dict]]:
        """General volume confirmation for unknown pattern types."""
        score = 50.0  # Neutral score
        factors = [{
            'factor': 'general_analysis',
            'score': 50,
            'description': f'General volume analysis for {pattern_type}'
        }]
        
        return score, factors
    
    def _calculate_enhanced_confidence(self,
                                     wyckoff_pattern: Dict,
                                     volume_confirmation: Dict) -> Dict:
        """
        Calculate enhanced confidence combining original Wyckoff confidence with volume confirmation.
        """
        original_confidence = wyckoff_pattern.get('confidence', 50)
        volume_score = volume_confirmation.get('confirmation_score', 50)
        
        # Weighted combination (70% original, 30% volume)
        enhanced_confidence = (original_confidence * 0.7) + (volume_score * 0.3)
        
        # Bonus for high volume confirmation
        if volume_score > 80:
            enhanced_confidence = min(100, enhanced_confidence + 5)
        
        # Penalty for very low volume confirmation
        elif volume_score < 30:
            enhanced_confidence = max(0, enhanced_confidence - 10)
        
        confidence_level = 'high' if enhanced_confidence >= 75 else 'medium' if enhanced_confidence >= 50 else 'low'
        
        return {
            'score': round(enhanced_confidence, 2),
            'level': confidence_level,
            'original_confidence': original_confidence,
            'volume_contribution': round((enhanced_confidence - original_confidence * 0.7) / 0.3, 2),
            'enhancement_factor': round(enhanced_confidence / original_confidence, 2) if original_confidence > 0 else 1.0
        }
    
    def _generate_volume_enhanced_signals(self,
                                        pattern_type: str,
                                        volume_analysis: Dict,
                                        wyckoff_pattern: Dict) -> Dict:
        """
        Generate trading signals enhanced with volume analysis.
        """
        signals = {
            'entry_signals': [],
            'exit_signals': [],
            'risk_signals': [],
            'confirmation_signals': []
        }
        
        try:
            # VWAP-based signals
            vwap_analysis = volume_analysis.get('vwap', {})
            vwap_signals = vwap_analysis.get('signals', {})
            
            for signal_type, signal_list in vwap_signals.items():
                if isinstance(signal_list, list):
                    for signal in signal_list:
                        if signal.get('strength', 0) > 60:
                            signals['confirmation_signals'].append({
                                'type': f'vwap_{signal_type}',
                                'strength': signal.get('strength'),
                                'details': signal,
                                'source': 'vwap_analysis'
                            })
            
            # Volume spike signals
            spike_analysis = volume_analysis.get('spikes', {})
            for alert in spike_analysis.get('alerts', []):
                if alert.get('score', 0) > 70:
                    signal_type = 'entry_signals' if 'accumulation' in alert.get('classification', '') else 'risk_signals'
                    signals[signal_type].append({
                        'type': 'volume_spike',
                        'strength': alert.get('score'),
                        'details': alert,
                        'source': 'spike_analysis'
                    })
            
            # Divergence signals
            div_analysis = volume_analysis.get('divergences', {})
            for div in div_analysis.get('all_divergences', []):
                if div.get('confidence', 0) > 60:
                    signal_type = 'entry_signals' if 'bullish' in div.get('type', '') else 'exit_signals'
                    signals[signal_type].append({
                        'type': 'volume_divergence',
                        'strength': div.get('confidence'),
                        'details': div,
                        'source': 'divergence_analysis'
                    })
            
            # A/D line signals
            ad_analysis = volume_analysis.get('accumulation_distribution', {})
            for alert in ad_analysis.get('alerts', []):
                signals['confirmation_signals'].append({
                    'type': 'ad_line',
                    'strength': alert.get('strength', 50),
                    'details': alert,
                    'source': 'ad_analysis'
                })
            
        except Exception as e:
            logger.error(f"Error generating volume-enhanced signals: {str(e)}")
            signals['error'] = str(e)
        
        return signals
    
    def _assess_volume_risk_factors(self,
                                  volume_analysis: Dict,
                                  wyckoff_pattern: Dict) -> Dict:
        """
        Assess risk factors based on volume analysis.
        """
        risk_factors = []
        risk_score = 50  # Neutral starting point
        
        try:
            # Check for conflicting volume signals
            divergences = volume_analysis.get('divergences', {})
            if divergences.get('total_divergences', 0) > 3:
                risk_factors.append({
                    'factor': 'multiple_divergences',
                    'severity': 'medium',
                    'description': f"Multiple volume divergences detected: {divergences['total_divergences']}"
                })
                risk_score += 15
            
            # Check for lack of volume confirmation
            classification = volume_analysis.get('classification', {})
            mixed_periods = classification.get('mixed_periods', 0)
            total_periods = classification.get('total_periods', 1)
            mixed_pct = (mixed_periods / total_periods) * 100
            
            if mixed_pct > 50:
                risk_factors.append({
                    'factor': 'unclear_volume_sentiment',
                    'severity': 'medium',
                    'description': f"High mixed volume activity: {mixed_pct:.1f}%"
                })
                risk_score += 10
            
            # Check for volume profile risks
            profile_analysis = volume_analysis.get('profile', {})
            shape_analysis = profile_analysis.get('shape_analysis', {})
            
            if shape_analysis.get('shape') == 'irregular':
                risk_factors.append({
                    'factor': 'irregular_volume_profile',
                    'severity': 'low',
                    'description': 'Irregular volume distribution pattern'
                })
                risk_score += 5
            
            # VWAP risk factors
            vwap_analysis = volume_analysis.get('vwap', {})
            current_position = vwap_analysis.get('current_position', {})
            
            if current_position.get('position') in ['extreme_overbought', 'extreme_oversold']:
                risk_factors.append({
                    'factor': 'extreme_vwap_position',
                    'severity': 'high',
                    'description': f"Price at extreme VWAP position: {current_position.get('position')}"
                })
                risk_score += 20
            
        except Exception as e:
            logger.error(f"Error assessing volume risk factors: {str(e)}")
            risk_factors.append({
                'factor': 'assessment_error',
                'severity': 'unknown',
                'description': f'Error in risk assessment: {str(e)}'
            })
        
        # Determine overall risk level
        if risk_score >= 80:
            risk_level = 'high'
        elif risk_score >= 60:
            risk_level = 'medium'
        elif risk_score >= 40:
            risk_level = 'low'
        else:
            risk_level = 'very_low'
        
        return {
            'risk_level': risk_level,
            'risk_score': min(100, risk_score),
            'risk_factors': risk_factors,
            'total_factors': len(risk_factors),
            'assessment_quality': 'comprehensive' if len(risk_factors) > 0 else 'basic'
        }
    
    def _create_analysis_summary(self, analysis_results: Dict) -> Dict:
        """Create summary of all volume analysis components."""
        summary = {
            'components_analyzed': len([k for k, v in analysis_results.items() if isinstance(v, dict) and 'error' not in v]),
            'total_components': 6,  # spike, divergence, ad, vwap, classification, profile
            'analysis_completeness': 0,
            'key_findings': []
        }
        
        try:
            # Calculate completeness
            successful_components = 0
            
            for component in ['spikes', 'divergences', 'accumulation_distribution', 'vwap', 'classification', 'profile']:
                if component in analysis_results and 'error' not in analysis_results[component]:
                    successful_components += 1
            
            summary['analysis_completeness'] = (successful_components / summary['total_components']) * 100
            
            # Extract key findings
            if 'spikes' in analysis_results:
                total_spikes = analysis_results['spikes'].get('total_spikes', 0)
                if total_spikes > 0:
                    summary['key_findings'].append(f"Volume spikes detected: {total_spikes}")
            
            if 'divergences' in analysis_results:
                total_divs = analysis_results['divergences'].get('total_divergences', 0)
                if total_divs > 0:
                    summary['key_findings'].append(f"Volume divergences detected: {total_divs}")
            
            if 'classification' in analysis_results:
                dominant_pattern = analysis_results['classification'].get('aggregate_analysis', {}).get('dominant_pattern', 'unknown')
                if dominant_pattern != 'unknown':
                    summary['key_findings'].append(f"Volume pattern: {dominant_pattern}")
            
        except Exception as e:
            logger.error(f"Error creating analysis summary: {str(e)}")
            summary['error'] = str(e)
        
        return summary
    
    def _assess_confirmation_quality(self, confirmation_factors: List[Dict]) -> str:
        """Assess the quality of volume confirmation analysis."""
        if not confirmation_factors:
            return 'no_data'
        
        avg_score = np.mean([factor.get('score', 0) for factor in confirmation_factors])
        factor_count = len(confirmation_factors)
        
        if avg_score >= 75 and factor_count >= 4:
            return 'high'
        elif avg_score >= 60 and factor_count >= 3:
            return 'good'
        elif avg_score >= 40 and factor_count >= 2:
            return 'moderate'
        else:
            return 'low'