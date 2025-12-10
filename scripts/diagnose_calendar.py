
import os
import sys
from src.politikk_moter.calendar_integration import CALENDAR_SOURCES, _resolve_calendar_id, GoogleCalendarIntegration

def check_env_vars():
    print("=== Checking Environment Variables ===")
    
    # Check Service Account
    sa_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
    if sa_json:
        print("✅ GOOGLE_SERVICE_ACCOUNT_JSON is set (length: {})".format(len(sa_json)))
    else:
        print("❌ GOOGLE_SERVICE_ACCOUNT_JSON is NOT set")

    # Check Calendar IDs
    for source_id, config in CALENDAR_SOURCES.items():
        print(f"\nChecking source: {source_id}")
        if 'calendar_id' in config:
            print(f"  - Has hardcoded calendar_id: {config['calendar_id'][:10]}...")
        
        if 'env' in config:
            env_var = config['env']
            val = os.getenv(env_var)
            if val:
                print(f"  - Env var {env_var} is set: {val}")
            else:
                print(f"  - Env var {env_var} is NOT set")
        
        resolved_id = _resolve_calendar_id(source_id)
        if resolved_id:
            print(f"  ✅ Resolved ID: {resolved_id[:10]}...")
        else:
            print(f"  ❌ Could not resolve ID")

def test_auth():
    print("\n=== Testing Authentication ===")
    # Try to authenticate with a dummy ID just to check credentials
    integration = GoogleCalendarIntegration("dummy_id")
    if integration.authenticate():
        print("✅ Authentication successful")
    else:
        print("❌ Authentication failed")

if __name__ == "__main__":
    check_env_vars()
    # Only test auth if SA is present, to avoid hanging if that's the issue
    if os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON'):
        test_auth()
