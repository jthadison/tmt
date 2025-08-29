#!/usr/bin/env python3
"""
End-to-End Trading Pipeline Integration Test

Tests the complete trading pipeline:
Market Analysis → Signal Generation → Orchestrator → Execution Engine → OANDA

This script validates that all services can communicate and process signals correctly.
"""

import asyncio
import aiohttp
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pipeline_test")

class TradingPipelineTest:
    """End-to-end trading pipeline integration test"""
    
    def __init__(self):
        self.services = {
            "orchestrator": "http://localhost:8000",
            "market_analysis": "http://localhost:8002",
            "execution_engine": "http://localhost:8004"
        }
        self.test_results = {}
    
    async def run_complete_test(self) -> Dict[str, Any]:
        """Run complete integration test suite"""
        logger.info("🚀 Starting End-to-End Trading Pipeline Test")
        logger.info("=" * 60)
        
        test_start = time.time()
        
        # Test 1: Service Health Checks
        await self.test_service_health()
        
        # Test 2: Market Data Pipeline
        await self.test_market_data_pipeline()
        
        # Test 3: Signal Generation
        await self.test_signal_generation()
        
        # Test 4: Signal Processing via Orchestrator
        await self.test_orchestrator_signal_processing()
        
        # Test 5: Direct Execution Engine Integration
        await self.test_execution_engine_direct()
        
        # Test 6: End-to-End Signal-to-Execution
        await self.test_end_to_end_pipeline()
        
        test_duration = time.time() - test_start
        
        # Generate test report
        report = self.generate_test_report(test_duration)
        
        logger.info("=" * 60)
        logger.info("📊 Integration Test Complete")
        logger.info(f"⏱️ Total Duration: {test_duration:.2f}s")
        
        return report
    
    async def test_service_health(self):
        """Test that all services are running and healthy"""
        logger.info("🏥 Testing Service Health...")
        
        health_results = {}
        
        for service, url in self.services.items():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{url}/health", timeout=5) as response:
                        if response.status == 200:
                            health_data = await response.json()
                            health_results[service] = {
                                "status": "✅ HEALTHY",
                                "response_time": response.headers.get("X-Response-Time", "N/A"),
                                "data": health_data
                            }
                            logger.info(f"  ✅ {service}: {health_data}")
                        else:
                            health_results[service] = {
                                "status": f"❌ UNHEALTHY ({response.status})",
                                "error": await response.text()
                            }
                            logger.error(f"  ❌ {service}: Status {response.status}")
                            
            except Exception as e:
                health_results[service] = {
                    "status": "❌ UNREACHABLE", 
                    "error": str(e)
                }
                logger.error(f"  ❌ {service}: {e}")
        
        self.test_results["service_health"] = health_results
    
    async def test_market_data_pipeline(self):
        """Test market data retrieval from market analysis service"""
        logger.info("📈 Testing Market Data Pipeline...")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Test market overview endpoint
                async with session.get(
                    f"{self.services['market_analysis']}/api/market-overview", 
                    timeout=10
                ) as response:
                    if response.status == 200:
                        market_data = await response.json()
                        
                        # Validate data structure
                        if "data" in market_data and "major_pairs" in market_data["data"]:
                            pairs = market_data["data"]["major_pairs"]
                            logger.info(f"  ✅ Retrieved data for {len(pairs)} currency pairs")
                            
                            # Check for required fields
                            for pair in pairs[:2]:  # Check first 2 pairs
                                required_fields = ["symbol", "price", "trend", "volatility"]
                                missing_fields = [f for f in required_fields if f not in pair]
                                if missing_fields:
                                    logger.warning(f"  ⚠️ Missing fields in {pair['symbol']}: {missing_fields}")
                                else:
                                    logger.info(f"  ✅ {pair['symbol']}: {pair['price']} ({pair['trend']})")
                            
                            self.test_results["market_data"] = {
                                "status": "✅ SUCCESS",
                                "pairs_count": len(pairs),
                                "sample_data": pairs[0] if pairs else None
                            }
                        else:
                            self.test_results["market_data"] = {
                                "status": "❌ INVALID_STRUCTURE",
                                "data": market_data
                            }
                    else:
                        error_text = await response.text()
                        self.test_results["market_data"] = {
                            "status": f"❌ HTTP_{response.status}",
                            "error": error_text
                        }
                        
        except Exception as e:
            logger.error(f"  ❌ Market data test failed: {e}")
            self.test_results["market_data"] = {
                "status": "❌ EXCEPTION",
                "error": str(e)
            }
    
    async def test_signal_generation(self):
        """Test signal generation from market analysis"""
        logger.info("🎯 Testing Signal Generation...")
        
        test_instruments = ["EUR_USD", "GBP_USD"]
        signal_results = {}
        
        for instrument in test_instruments:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{self.services['market_analysis']}/api/signals/{instrument}",
                        timeout=10
                    ) as response:
                        if response.status == 200:
                            signal_data = await response.json()
                            
                            if signal_data.get("signal"):
                                signal = signal_data["signal"]
                                logger.info(f"  ✅ {instrument}: {signal['direction']} @ {signal['confidence']}")
                                signal_results[instrument] = {
                                    "status": "✅ SIGNAL_GENERATED",
                                    "signal": signal
                                }
                            else:
                                reason = signal_data.get("reason", "Unknown")
                                logger.info(f"  ⚪ {instrument}: No signal ({reason})")
                                signal_results[instrument] = {
                                    "status": "⚪ NO_SIGNAL", 
                                    "reason": reason
                                }
                        else:
                            error_text = await response.text()
                            logger.error(f"  ❌ {instrument}: HTTP {response.status}")
                            signal_results[instrument] = {
                                "status": f"❌ HTTP_{response.status}",
                                "error": error_text
                            }
                            
            except Exception as e:
                logger.error(f"  ❌ {instrument}: {e}")
                signal_results[instrument] = {
                    "status": "❌ EXCEPTION",
                    "error": str(e)
                }
        
        self.test_results["signal_generation"] = signal_results
    
    async def test_orchestrator_signal_processing(self):
        """Test signal processing via orchestrator"""
        logger.info("🎼 Testing Orchestrator Signal Processing...")
        
        # Create test signal
        test_signal = {
            "id": f"test_signal_{int(time.time())}",
            "instrument": "EUR_USD",
            "direction": "long",
            "confidence": 0.85,
            "entry_price": 1.0500,
            "stop_loss": 1.0450,
            "take_profit": 1.0600,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.services['orchestrator']}/api/signals",
                    json=test_signal,
                    timeout=15
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"  ✅ Signal processed: {result.get('status')}")
                        self.test_results["orchestrator_signal"] = {
                            "status": "✅ SUCCESS",
                            "result": result
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"  ❌ Orchestrator returned {response.status}: {error_text}")
                        self.test_results["orchestrator_signal"] = {
                            "status": f"❌ HTTP_{response.status}",
                            "error": error_text
                        }
                        
        except Exception as e:
            logger.error(f"  ❌ Orchestrator signal test failed: {e}")
            self.test_results["orchestrator_signal"] = {
                "status": "❌ EXCEPTION",
                "error": str(e)
            }
    
    async def test_execution_engine_direct(self):
        """Test direct execution engine order submission"""
        logger.info("⚡ Testing Direct Execution Engine...")
        
        # Create test order
        test_order = {
            "account_id": "test_account",
            "instrument": "EUR_USD",
            "order_type": "market",
            "side": "buy",
            "units": 1000,
            "take_profit_price": 1.0600,
            "stop_loss_price": 1.0450,
            "client_extensions": {
                "id": f"test_order_{int(time.time())}",
                "tag": "integration_test",
                "comment": "End-to-end pipeline test"
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.services['execution_engine']}/api/orders",
                    json=test_order,
                    timeout=10
                ) as response:
                    if response.status in [200, 201]:
                        result = await response.json()
                        logger.info(f"  ✅ Order submitted: {result.get('order_id', 'N/A')}")
                        self.test_results["execution_engine"] = {
                            "status": "✅ SUCCESS",
                            "result": result
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"  ❌ Execution engine returned {response.status}")
                        self.test_results["execution_engine"] = {
                            "status": f"❌ HTTP_{response.status}",
                            "error": error_text
                        }
                        
        except Exception as e:
            logger.error(f"  ❌ Execution engine test failed: {e}")
            self.test_results["execution_engine"] = {
                "status": "❌ EXCEPTION",
                "error": str(e)
            }
    
    async def test_end_to_end_pipeline(self):
        """Test complete end-to-end signal processing pipeline"""
        logger.info("🔄 Testing End-to-End Pipeline...")
        
        pipeline_start = time.time()
        
        try:
            # Step 1: Get market data
            logger.info("  📊 Step 1: Fetching market data...")
            market_data = None
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.services['market_analysis']}/api/market-overview") as response:
                    if response.status == 200:
                        data = await response.json()
                        market_data = data.get("data", {}).get("major_pairs", [])
                        logger.info(f"    ✅ Retrieved {len(market_data)} pairs")
                    else:
                        raise Exception(f"Market data fetch failed: {response.status}")
            
            # Step 2: Generate signal from market data
            logger.info("  🎯 Step 2: Generating signal...")
            if market_data:
                # Use the first pair with a strong trend
                selected_pair = None
                for pair in market_data:
                    if abs(pair.get("change_24h", 0)) > 0.005:  # Look for significant movement
                        selected_pair = pair
                        break
                
                if not selected_pair:
                    selected_pair = market_data[0]  # Fallback to first pair
                
                # Generate signal based on market data
                signal = self.create_signal_from_market_data(selected_pair)
                logger.info(f"    ✅ Generated {signal['direction']} signal for {signal['instrument']}")
                
                # Step 3: Process signal via orchestrator
                logger.info("  🎼 Step 3: Processing via orchestrator...")
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.services['orchestrator']}/api/signals",
                        json=signal,
                        timeout=20
                    ) as response:
                        if response.status == 200:
                            orchestrator_result = await response.json()
                            logger.info(f"    ✅ Orchestrator processed: {orchestrator_result.get('status')}")
                            
                            pipeline_duration = time.time() - pipeline_start
                            
                            self.test_results["end_to_end"] = {
                                "status": "✅ SUCCESS",
                                "duration_seconds": pipeline_duration,
                                "signal": signal,
                                "orchestrator_result": orchestrator_result,
                                "steps_completed": 3
                            }
                            
                            logger.info(f"  ✅ End-to-end pipeline completed in {pipeline_duration:.2f}s")
                        else:
                            error_text = await response.text()
                            raise Exception(f"Orchestrator processing failed: {response.status} - {error_text}")
            else:
                raise Exception("No market data available for signal generation")
                
        except Exception as e:
            pipeline_duration = time.time() - pipeline_start
            logger.error(f"  ❌ End-to-end pipeline failed: {e}")
            self.test_results["end_to_end"] = {
                "status": "❌ FAILED",
                "duration_seconds": pipeline_duration,
                "error": str(e)
            }
    
    def create_signal_from_market_data(self, market_pair: Dict) -> Dict:
        """Create a trading signal from market data"""
        symbol = market_pair["symbol"]
        price = market_pair["price"]
        change_24h = market_pair.get("change_24h", 0)
        trend = market_pair.get("trend", "neutral")
        volatility = market_pair.get("volatility", 0.01)
        
        # Determine direction based on trend and change
        if trend == "bullish" and change_24h > 0.005:
            direction = "long"
            confidence = min(0.9, 0.75 + abs(change_24h) * 10)
        elif trend == "bearish" and change_24h < -0.005:
            direction = "short"
            confidence = min(0.9, 0.75 + abs(change_24h) * 10)
        else:
            # Force a signal for testing
            direction = "long" if change_24h >= 0 else "short"
            confidence = 0.76  # Just above threshold
        
        # Calculate levels
        if direction == "long":
            entry_price = price
            stop_loss = price * (1 - volatility * 2)
            take_profit = price * (1 + volatility * 3)
        else:
            entry_price = price
            stop_loss = price * (1 + volatility * 2)
            take_profit = price * (1 - volatility * 3)
        
        return {
            "id": f"e2e_signal_{symbol}_{int(time.time())}",
            "instrument": symbol,
            "direction": direction,
            "confidence": round(confidence, 2),
            "entry_price": round(entry_price, 5),
            "stop_loss": round(stop_loss, 5),
            "take_profit": round(take_profit, 5),
            "timestamp": datetime.now().isoformat(),
            "timeframe": "M15",
            "analysis_source": "integration_test"
        }
    
    def generate_test_report(self, duration: float) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        
        # Count successes and failures
        total_tests = len(self.test_results)
        successful_tests = 0
        failed_tests = 0
        
        for test_name, result in self.test_results.items():
            if isinstance(result, dict):
                status = result.get("status", "")
                if "✅" in status or "SUCCESS" in status:
                    successful_tests += 1
                elif "❌" in status or "FAILED" in status or "EXCEPTION" in status:
                    failed_tests += 1
            elif isinstance(result, dict):  # For nested results like service health
                for service_result in result.values():
                    if isinstance(service_result, dict):
                        status = service_result.get("status", "")
                        if "✅" in status:
                            successful_tests += 1
                        elif "❌" in status:
                            failed_tests += 1
        
        overall_status = "✅ PASS" if failed_tests == 0 else f"❌ FAIL ({failed_tests} failures)"
        
        report = {
            "test_summary": {
                "overall_status": overall_status,
                "duration_seconds": duration,
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "failed_tests": failed_tests,
                "success_rate": f"{(successful_tests/(successful_tests+failed_tests)*100):.1f}%" if (successful_tests+failed_tests) > 0 else "0%"
            },
            "detailed_results": self.test_results,
            "recommendations": self.generate_recommendations()
        }
        
        return report
    
    def generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        # Check service health
        if "service_health" in self.test_results:
            for service, result in self.test_results["service_health"].items():
                if "❌" in result.get("status", ""):
                    if "UNREACHABLE" in result["status"]:
                        recommendations.append(f"Start the {service} service - it appears to be down")
                    else:
                        recommendations.append(f"Check {service} service configuration - returning errors")
        
        # Check pipeline integration
        if "end_to_end" in self.test_results:
            e2e_result = self.test_results["end_to_end"]
            if "✅" in e2e_result.get("status", ""):
                recommendations.append("✅ End-to-end pipeline is working correctly")
            else:
                recommendations.append("❌ End-to-end pipeline needs attention - check service integration")
        
        # General recommendations
        if not recommendations:
            recommendations.append("All tests passed - system is ready for trading")
        
        return recommendations

async def main():
    """Main test execution"""
    test = TradingPipelineTest()
    
    try:
        report = await test.run_complete_test()
        
        # Print summary
        print("\n" + "=" * 80)
        print("📊 INTEGRATION TEST REPORT")
        print("=" * 80)
        
        summary = report["test_summary"]
        print(f"Overall Status: {summary['overall_status']}")
        print(f"Duration: {summary['duration_seconds']:.2f}s")
        print(f"Tests: {summary['successful_tests']}/{summary['total_tests']} passed ({summary['success_rate']})")
        
        print("\n📋 Recommendations:")
        for rec in report["recommendations"]:
            print(f"  • {rec}")
        
        print("\n🔧 Next Steps:")
        if "✅" in summary["overall_status"]:
            print("  • System is ready for live trading")
            print("  • Consider running load testing")
            print("  • Monitor performance in production")
        else:
            print("  • Fix failing services before proceeding")
            print("  • Re-run integration tests after fixes")
            print("  • Check logs for detailed error information")
        
    except KeyboardInterrupt:
        logger.info("Integration test interrupted by user")
    except Exception as e:
        logger.error(f"Integration test failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())