"""
End-to-End Test for Emergency Rollback System
Tests the complete rollback functionality via API endpoints
"""

import asyncio
import aiohttp
import json
from datetime import datetime

async def test_rollback_system_endpoints():
    """Test the emergency rollback system via API endpoints"""

    base_url = "http://localhost:8089"

    print("🔍 Testing Emergency Rollback System API Endpoints")
    print("=" * 60)

    async with aiohttp.ClientSession() as session:

        # 1. Test System Health
        print("\n1️⃣ Testing System Health...")
        try:
            async with session.get(f"{base_url}/health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    print(f"✅ System Health: {health_data.get('status', 'unknown')}")
                else:
                    print(f"❌ Health check failed: {response.status}")
                    return
        except Exception as e:
            print(f"❌ Cannot connect to orchestrator at {base_url}: {e}")
            print("Make sure the orchestrator is running with:")
            print("cd orchestrator && OANDA_API_KEY=your_key ENABLE_TRADING=true PORT=8089 python -m app.main")
            return

        # 2. Test Rollback Status
        print("\n2️⃣ Testing Emergency Rollback Status...")
        try:
            async with session.get(f"{base_url}/emergency-rollback/status") as response:
                if response.status == 200:
                    status_data = await response.json()
                    print(f"✅ Rollback Status: {status_data.get('status')}")
                    print(f"   Ready for rollback: {status_data.get('ready_for_rollback')}")
                else:
                    print(f"❌ Status check failed: {response.status}")
        except Exception as e:
            print(f"❌ Status check error: {e}")

        # 3. Test Automatic Trigger Check
        print("\n3️⃣ Testing Automatic Trigger Detection...")
        try:
            async with session.post(f"{base_url}/emergency-rollback/check-triggers") as response:
                if response.status == 200:
                    trigger_data = await response.json()
                    trigger_detected = trigger_data.get('trigger_detected', False)
                    trigger_type = trigger_data.get('trigger_type')
                    print(f"✅ Trigger Check Complete")
                    print(f"   Trigger Detected: {trigger_detected}")
                    if trigger_detected:
                        print(f"   Trigger Type: {trigger_type}")
                        print("   ⚠️ System would automatically rollback under these conditions!")
                    else:
                        print("   System is within acceptable parameters")
                else:
                    print(f"❌ Trigger check failed: {response.status}")
        except Exception as e:
            print(f"❌ Trigger check error: {e}")

        # 4. Test Emergency Contact System
        print("\n4️⃣ Testing Emergency Contact System...")
        try:
            async with session.get(f"{base_url}/emergency-contacts") as response:
                if response.status == 200:
                    contacts_data = await response.json()
                    contact_count = contacts_data.get('total_count', 0)
                    print(f"✅ Emergency Contacts: {contact_count} contacts configured")
                else:
                    print(f"❌ Contacts check failed: {response.status}")
        except Exception as e:
            print(f"❌ Contacts check error: {e}")

        # 5. Test Notification System (Test Mode)
        print("\n5️⃣ Testing Emergency Notification System...")
        try:
            async with session.post(f"{base_url}/emergency-contacts/test-notification") as response:
                if response.status == 200:
                    notification_data = await response.json()
                    total = notification_data.get('total_notifications', 0)
                    successful = notification_data.get('successful_notifications', 0)
                    print(f"✅ Test Notifications: {successful}/{total} successful")
                else:
                    print(f"❌ Notification test failed: {response.status}")
        except Exception as e:
            print(f"❌ Notification test error: {e}")

        # 6. Test Rollback History
        print("\n6️⃣ Testing Rollback History...")
        try:
            async with session.get(f"{base_url}/emergency-rollback/history") as response:
                if response.status == 200:
                    history_data = await response.json()
                    history_count = len(history_data.get('history', []))
                    print(f"✅ Rollback History: {history_count} past events")
                else:
                    print(f"❌ History check failed: {response.status}")
        except Exception as e:
            print(f"❌ History check error: {e}")

        # 7. Test Manual Rollback (DRY RUN - ASK FIRST)
        print("\n7️⃣ Manual Emergency Rollback Test...")
        confirm = input("⚠️  Do you want to test ACTUAL emergency rollback? This will switch to Cycle 4 parameters! (yes/no): ")

        if confirm.lower() == 'yes':
            print("\n🚨 EXECUTING EMERGENCY ROLLBACK TEST...")
            rollback_data = {
                "reason": "End-to-end system test - manual rollback verification",
                "notify_contacts": False  # Don't spam contacts during testing
            }

            try:
                async with session.post(f"{base_url}/emergency-rollback", json=rollback_data) as response:
                    if response.status == 200:
                        rollback_result = await response.json()
                        print(f"✅ Emergency Rollback Executed Successfully!")
                        print(f"   Event ID: {rollback_result.get('event_id')}")
                        print(f"   Previous Mode: {rollback_result.get('previous_mode')}")
                        print(f"   New Mode: {rollback_result.get('new_mode')}")
                        print(f"   Validation: {'PASSED' if rollback_result.get('validation_successful') else 'FAILED'}")

                        # Check recovery validation
                        recovery_info = rollback_result.get('recovery_validation', {})
                        if recovery_info.get('triggered'):
                            print(f"   Recovery Validation: {recovery_info.get('status')}")
                            print(f"   Recovery Score: {recovery_info.get('score')}/100")
                            print(f"   Recovery Confirmed: {recovery_info.get('recovery_confirmed')}")

                        print("\n✅ ROLLBACK TEST COMPLETED SUCCESSFULLY!")
                        print("   System has been switched to Cycle 4 Universal parameters")
                        print("   You can now verify the parameter change in the market analysis agent")

                    else:
                        error_text = await response.text()
                        print(f"❌ Emergency rollback failed: {response.status}")
                        print(f"   Error: {error_text}")
            except Exception as e:
                print(f"❌ Rollback execution error: {e}")
        else:
            print("⏭️  Skipping actual rollback test")

        # 8. Test Recovery Validation History (if rollback was performed)
        if confirm.lower() == 'yes':
            print("\n8️⃣ Testing Recovery Validation History...")
            try:
                async with session.get(f"{base_url}/recovery-validation/history") as response:
                    if response.status == 200:
                        validation_history = await response.json()
                        history_count = len(validation_history.get('history', []))
                        print(f"✅ Recovery Validation History: {history_count} validations")

                        if history_count > 0:
                            latest = validation_history['history'][0]
                            print(f"   Latest Validation: {latest.get('overall_status')}")
                            print(f"   Recovery Confirmed: {latest.get('recovery_confirmed')}")
                    else:
                        print(f"❌ Validation history check failed: {response.status}")
            except Exception as e:
                print(f"❌ Validation history error: {e}")

    print("\n" + "=" * 60)
    print("🎯 Emergency Rollback System Test Complete")
    print("=" * 60)

    if confirm.lower() == 'yes':
        print("\n⚠️  IMPORTANT: System has been rolled back to Cycle 4 parameters")
        print("   - Trading parameters have been reset to conservative baseline")
        print("   - You may want to restart agents to ensure they pick up new parameters")
        print("   - Monitor system performance to ensure stable operation")


async def test_monitoring_system():
    """Test the rollback monitoring system"""

    base_url = "http://localhost:8089"

    print("\n🔍 Testing Rollback Monitoring System")
    print("=" * 50)

    async with aiohttp.ClientSession() as session:

        # 1. Check monitoring status
        print("\n1️⃣ Checking Monitoring Status...")
        try:
            async with session.get(f"{base_url}/rollback-monitor/status") as response:
                if response.status == 200:
                    status_data = await response.json()
                    print(f"✅ Monitoring Active: {status_data.get('monitoring_active')}")
                    print(f"   Check Interval: {status_data.get('check_interval_seconds')} seconds")
                else:
                    print(f"❌ Monitoring status check failed: {response.status}")
        except Exception as e:
            print(f"❌ Monitoring status error: {e}")

        # 2. Test starting monitoring (if not active)
        print("\n2️⃣ Testing Monitoring Start/Stop...")
        try:
            # Try to start monitoring
            async with session.post(f"{base_url}/rollback-monitor/start") as response:
                if response.status == 200:
                    start_result = await response.json()
                    print(f"✅ Monitoring Started: {start_result.get('status')}")
                else:
                    print(f"⚠️  Monitoring start response: {response.status} (may already be running)")

            # Wait a moment
            await asyncio.sleep(2)

            # Stop monitoring
            async with session.post(f"{base_url}/rollback-monitor/stop") as response:
                if response.status == 200:
                    stop_result = await response.json()
                    print(f"✅ Monitoring Stopped: {stop_result.get('status')}")
                else:
                    print(f"❌ Monitoring stop failed: {response.status}")

        except Exception as e:
            print(f"❌ Monitoring control error: {e}")

    print("\n✅ Monitoring System Test Complete")


if __name__ == "__main__":
    print("🚀 Emergency Rollback System - End-to-End Test")
    print("=" * 60)
    print("This test will verify all components of the emergency rollback system:")
    print("  • System health and status")
    print("  • Automatic trigger detection")
    print("  • Emergency contact system")
    print("  • Recovery validation")
    print("  • Manual rollback execution (optional)")
    print("  • Monitoring system")
    print()

    print("⚠️  PREREQUISITES:")
    print("  • Orchestrator must be running on port 8089")
    print("  • Market analysis agent should be running")
    print("  • Emergency rollback system should be initialized")
    print()

    proceed = input("Ready to proceed with testing? (yes/no): ")
    if proceed.lower() != 'yes':
        print("Test cancelled.")
        exit()

    # Run the main test
    asyncio.run(test_rollback_system_endpoints())

    # Test monitoring system
    test_monitoring = input("\nTest monitoring system? (yes/no): ")
    if test_monitoring.lower() == 'yes':
        asyncio.run(test_monitoring_system())

    print("\n🎉 All tests completed!")