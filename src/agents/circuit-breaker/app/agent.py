"""
CrewAI Circuit Breaker Agent Implementation

Implements the AI agent using CrewAI framework for intelligent
circuit breaker decision making and coordination.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import asyncio

from crewai import Agent, Task, Crew, Process
from langchain.llms import OpenAI
from langchain.tools import Tool
import structlog

from .models import BreakerLevel, BreakerState, TriggerReason, SystemHealth, MarketConditions
from .config import config

logger = structlog.get_logger(__name__)


class CircuitBreakerAIAgent:
    """
    AI-powered circuit breaker agent that makes intelligent decisions
    about system protection and emergency responses.
    """
    
    def __init__(self, breaker_manager, emergency_stop_manager, health_monitor):
        self.breaker_manager = breaker_manager
        self.emergency_stop_manager = emergency_stop_manager
        self.health_monitor = health_monitor
        
        # Initialize LLM
        self.llm = OpenAI(
            temperature=0.1,  # Low temperature for consistent decisions
            model_name="gpt-3.5-turbo",
            max_tokens=500
        )
        
        # Create tools for the agent
        self.tools = self._create_agent_tools()
        
        # Create the circuit breaker agent
        self.circuit_breaker_agent = Agent(
            role='Circuit Breaker Specialist',
            goal='Monitor system health and make intelligent decisions about circuit breaker activation to protect the trading system',
            backstory="""You are an expert system reliability engineer specializing in circuit breaker patterns 
            and system protection. Your role is to monitor trading system health metrics and make rapid decisions 
            about when to trigger emergency stops to prevent cascade failures. You must balance system protection 
            with trading continuity, only triggering breakers when absolutely necessary.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
            tools=self.tools
        )
        
        logger.info("Circuit Breaker AI Agent initialized")
    
    def _create_agent_tools(self) -> List[Tool]:
        """Create tools that the agent can use"""
        
        def get_current_health_status(input_text: str) -> str:
            """Get current system health metrics"""
            try:
                health = self.health_monitor.get_current_health()
                if health:
                    return f"""Current System Health:
- CPU Usage: {health.cpu_usage:.1f}%
- Memory Usage: {health.memory_usage:.1f}%
- Disk Usage: {health.disk_usage:.1f}%
- Error Rate: {health.error_rate:.2%}
- Response Time: {health.response_time}ms
- Active Connections: {health.active_connections}
- Timestamp: {health.timestamp}"""
                else:
                    return "Health metrics not available"
            except Exception as e:
                return f"Error getting health status: {str(e)}"
        
        def get_breaker_status(input_text: str) -> str:
            """Get current circuit breaker status"""
            try:
                status = self.breaker_manager.get_all_breaker_status()
                return f"""Circuit Breaker Status:
- System Breaker: {status['system_breaker']['state']}
- Agent Breakers: {len(status['agent_breakers'])} active
- Account Breakers: {len(status['account_breakers'])} active
- Overall Healthy: {status['overall_healthy']}"""
            except Exception as e:
                return f"Error getting breaker status: {str(e)}"
        
        def analyze_system_risk(input_text: str) -> str:
            """Analyze current system risk level"""
            try:
                health = self.health_monitor.get_current_health()
                if not health:
                    return "Cannot analyze risk - health data unavailable"
                
                risk_factors = []
                risk_score = 0
                
                # CPU risk
                if health.cpu_usage > 80:
                    risk_factors.append(f"High CPU usage: {health.cpu_usage:.1f}%")
                    risk_score += 2 if health.cpu_usage > 90 else 1
                
                # Memory risk
                if health.memory_usage > 80:
                    risk_factors.append(f"High memory usage: {health.memory_usage:.1f}%")
                    risk_score += 2 if health.memory_usage > 90 else 1
                
                # Error rate risk
                if health.error_rate > 0.1:
                    risk_factors.append(f"High error rate: {health.error_rate:.1%}")
                    risk_score += 3 if health.error_rate > 0.2 else 1
                
                # Response time risk
                if health.response_time > config.response_time_threshold:
                    risk_factors.append(f"Slow response time: {health.response_time}ms")
                    risk_score += 2
                
                risk_level = "LOW"
                if risk_score >= 5:
                    risk_level = "CRITICAL"
                elif risk_score >= 3:
                    risk_level = "HIGH"
                elif risk_score >= 1:
                    risk_level = "MEDIUM"
                
                return f"""System Risk Analysis:
Risk Level: {risk_level}
Risk Score: {risk_score}/10
Risk Factors: {'; '.join(risk_factors) if risk_factors else 'None detected'}

Recommendations:
{self._get_risk_recommendations(risk_level, risk_factors)}"""
                
            except Exception as e:
                return f"Error analyzing system risk: {str(e)}"
        
        def recommend_breaker_action(input_text: str) -> str:
            """Recommend circuit breaker action based on current conditions"""
            try:
                health = self.health_monitor.get_current_health()
                status = self.breaker_manager.get_all_breaker_status()
                
                if not health:
                    return "Cannot recommend action - health data unavailable"
                
                recommendations = []
                
                # Check for critical conditions
                if health.error_rate > config.error_rate_threshold:
                    recommendations.append(f"TRIGGER SYSTEM BREAKER - Error rate {health.error_rate:.1%} exceeds threshold")
                
                if health.response_time > config.response_time_threshold * 2:
                    recommendations.append(f"TRIGGER SYSTEM BREAKER - Response time {health.response_time}ms critically high")
                
                if health.cpu_usage > 95 or health.memory_usage > 95:
                    recommendations.append("TRIGGER AGENT BREAKER - Resource exhaustion imminent")
                
                # Check for warning conditions
                if health.error_rate > config.error_rate_threshold * 0.5:
                    recommendations.append("WARNING - Monitor error rate closely")
                
                if health.response_time > config.response_time_threshold * 0.8:
                    recommendations.append("WARNING - Response time approaching threshold")
                
                if not recommendations:
                    recommendations.append("NORMAL - All systems operating within parameters")
                
                return f"""Circuit Breaker Recommendations:
{chr(10).join(f'- {rec}' for rec in recommendations)}

Current Status: System={'TRIPPED' if not status['overall_healthy'] else 'NORMAL'}"""
                
            except Exception as e:
                return f"Error generating recommendations: {str(e)}"
        
        return [
            Tool(
                name="get_health_status",
                description="Get current system health metrics including CPU, memory, error rates",
                func=get_current_health_status
            ),
            Tool(
                name="get_breaker_status", 
                description="Get current status of all circuit breakers (agent, account, system level)",
                func=get_breaker_status
            ),
            Tool(
                name="analyze_risk",
                description="Analyze current system risk level and identify risk factors",
                func=analyze_system_risk
            ),
            Tool(
                name="recommend_action",
                description="Recommend circuit breaker actions based on current system conditions",
                func=recommend_breaker_action
            )
        ]
    
    def _get_risk_recommendations(self, risk_level: str, risk_factors: List[str]) -> str:
        """Get recommendations based on risk level"""
        if risk_level == "CRITICAL":
            return "IMMEDIATE ACTION REQUIRED - Consider system-level circuit breaker activation"
        elif risk_level == "HIGH":
            return "HIGH PRIORITY - Monitor closely, prepare for possible breaker activation"
        elif risk_level == "MEDIUM":
            return "MONITOR - Increased vigilance recommended, check for trending issues"
        else:
            return "NORMAL - Continue routine monitoring"
    
    async def analyze_system_condition(
        self,
        health_metrics: SystemHealth,
        market_conditions: Optional[MarketConditions] = None,
        context: str = "routine_check"
    ) -> Dict[str, Any]:
        """
        Use AI agent to analyze system conditions and provide recommendations.
        
        Args:
            health_metrics: Current system health metrics
            market_conditions: Current market conditions (if available)
            context: Context for the analysis (routine_check, alert_investigation, etc.)
            
        Returns:
            Dictionary with analysis results and recommendations
        """
        try:
            # Create analysis task
            analysis_task = Task(
                description=f"""Analyze the current trading system health and provide circuit breaker recommendations.
                
Context: {context}
Current System Health:
- CPU Usage: {health_metrics.cpu_usage:.1f}%
- Memory Usage: {health_metrics.memory_usage:.1f}%  
- Disk Usage: {health_metrics.disk_usage:.1f}%
- Error Rate: {health_metrics.error_rate:.2%}
- Response Time: {health_metrics.response_time}ms
- Active Connections: {health_metrics.active_connections}

Please use your tools to:
1. Get current breaker status
2. Analyze system risk level
3. Provide specific recommendations for circuit breaker actions
4. Assess if immediate intervention is required

Focus on protecting system stability while minimizing unnecessary trading interruptions.""",
                agent=self.circuit_breaker_agent,
                expected_output="Structured analysis with risk assessment and specific action recommendations"
            )
            
            # Create crew and execute
            crew = Crew(
                agents=[self.circuit_breaker_agent],
                tasks=[analysis_task],
                verbose=True,
                process=Process.sequential
            )
            
            # Execute in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, crew.kickoff)
            
            # Parse and structure the result
            analysis_result = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "context": context,
                "ai_analysis": result,
                "health_snapshot": health_metrics.dict(),
                "recommendations": self._extract_recommendations(result),
                "risk_level": self._extract_risk_level(result),
                "immediate_action_required": self._requires_immediate_action(result)
            }
            
            logger.info(
                "AI analysis completed",
                context=context,
                risk_level=analysis_result["risk_level"],
                immediate_action=analysis_result["immediate_action_required"]
            )
            
            return analysis_result
            
        except Exception as e:
            logger.exception("AI analysis failed", error=str(e))
            
            # Fallback analysis based on thresholds
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "context": context,
                "ai_analysis": f"AI analysis failed: {str(e)}",
                "health_snapshot": health_metrics.dict(),
                "recommendations": self._fallback_recommendations(health_metrics),
                "risk_level": self._calculate_fallback_risk(health_metrics),
                "immediate_action_required": self._fallback_immediate_action_check(health_metrics),
                "error": str(e)
            }
    
    def _extract_recommendations(self, ai_result: str) -> List[str]:
        """Extract actionable recommendations from AI analysis"""
        try:
            recommendations = []
            lines = str(ai_result).split('\n')
            
            for line in lines:
                line = line.strip()
                if any(keyword in line.upper() for keyword in ['RECOMMEND', 'SUGGEST', 'ACTION', 'TRIGGER']):
                    recommendations.append(line)
            
            return recommendations if recommendations else ["Continue monitoring"]
            
        except Exception:
            return ["Unable to parse recommendations"]
    
    def _extract_risk_level(self, ai_result: str) -> str:
        """Extract risk level from AI analysis"""
        try:
            result_upper = str(ai_result).upper()
            
            if any(word in result_upper for word in ['CRITICAL', 'EMERGENCY', 'IMMEDIATE']):
                return "CRITICAL"
            elif any(word in result_upper for word in ['HIGH', 'URGENT', 'TRIGGER']):
                return "HIGH"
            elif any(word in result_upper for word in ['MEDIUM', 'WARNING', 'CAUTION']):
                return "MEDIUM"
            else:
                return "LOW"
                
        except Exception:
            return "UNKNOWN"
    
    def _requires_immediate_action(self, ai_result: str) -> bool:
        """Determine if immediate action is required"""
        try:
            result_upper = str(ai_result).upper()
            
            immediate_keywords = [
                'IMMEDIATE', 'EMERGENCY', 'CRITICAL', 'TRIGGER BREAKER',
                'SYSTEM BREAKER', 'URGENT', 'HALT'
            ]
            
            return any(keyword in result_upper for keyword in immediate_keywords)
            
        except Exception:
            return False
    
    def _fallback_recommendations(self, health_metrics: SystemHealth) -> List[str]:
        """Provide fallback recommendations when AI analysis fails"""
        recommendations = []
        
        if health_metrics.error_rate > config.error_rate_threshold:
            recommendations.append("Consider system-level circuit breaker due to high error rate")
        
        if health_metrics.response_time > config.response_time_threshold:
            recommendations.append("Monitor response times - approaching threshold")
        
        if health_metrics.cpu_usage > 90:
            recommendations.append("High CPU usage detected - consider load reduction")
        
        if health_metrics.memory_usage > 90:
            recommendations.append("High memory usage detected - investigate memory leaks")
        
        return recommendations if recommendations else ["Continue routine monitoring"]
    
    def _calculate_fallback_risk(self, health_metrics: SystemHealth) -> str:
        """Calculate risk level using simple threshold rules"""
        risk_score = 0
        
        if health_metrics.error_rate > config.error_rate_threshold:
            risk_score += 3
        elif health_metrics.error_rate > config.error_rate_threshold * 0.5:
            risk_score += 1
        
        if health_metrics.response_time > config.response_time_threshold:
            risk_score += 2
        
        if health_metrics.cpu_usage > 90 or health_metrics.memory_usage > 90:
            risk_score += 2
        
        if risk_score >= 4:
            return "CRITICAL"
        elif risk_score >= 2:
            return "HIGH"
        elif risk_score >= 1:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _fallback_immediate_action_check(self, health_metrics: SystemHealth) -> bool:
        """Simple threshold check for immediate action"""
        return (
            health_metrics.error_rate > config.error_rate_threshold or
            health_metrics.response_time > config.response_time_threshold * 2 or
            health_metrics.cpu_usage > 95 or
            health_metrics.memory_usage > 95
        )
    
    async def investigate_alert(self, alert_type: str, alert_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use AI agent to investigate specific alerts and provide recommendations.
        
        Args:
            alert_type: Type of alert to investigate
            alert_details: Details about the alert
            
        Returns:
            Investigation results with recommendations
        """
        try:
            # Get current health for context
            health = self.health_monitor.get_current_health()
            if health:
                return await self.analyze_system_condition(
                    health, 
                    context=f"alert_investigation_{alert_type}"
                )
            else:
                return {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "alert_type": alert_type,
                    "status": "unable_to_investigate",
                    "error": "Health metrics not available"
                }
                
        except Exception as e:
            logger.exception("Alert investigation failed", error=str(e))
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "alert_type": alert_type,
                "status": "investigation_failed",
                "error": str(e)
            }