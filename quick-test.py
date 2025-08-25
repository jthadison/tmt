#!/usr/bin/env python3
"""Quick test of psutil usage"""

import psutil

print("Testing psutil process iteration...")

try:
    count = 0
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            info = proc.as_dict(attrs=['pid', 'name'])
            count += 1
            if count > 5:  # Just test first few
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    print(f"✅ psutil working, tested {count} processes")
    
    # Test connections method
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            connections = proc.connections()
            print(f"✅ connections() method works for PID {proc.pid}")
            break
        except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError) as e:
            continue
        except Exception as e:
            print(f"⚠️ connections() error: {e}")
            break
    
except Exception as e:
    print(f"❌ psutil error: {e}")
    import traceback
    traceback.print_exc()