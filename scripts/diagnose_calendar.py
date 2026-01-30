import logging
import os
import sys
from pathlib import Path


logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def _bootstrap_package() -> None:
    """Ensure the packaged sources under ``src/`` are importable."""
    root = Path(__file__).resolve().parents[1]
    src_dir = root / "src"
    if str(src_dir) not in sys.path and src_dir.exists():
        sys.path.insert(0, str(src_dir))


_bootstrap_package()


def check_env_vars():
    from politikk_moter.calendar_integration import (
        CALENDAR_SOURCES,
        _resolve_calendar_id,
    )
    logger.info("=== Checking Environment Variables ===")
    
    # Check Service Account
    sa_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
    if sa_json:
        logger.info("✅ GOOGLE_SERVICE_ACCOUNT_JSON is set (length: %s)", len(sa_json))
    else:
        logger.warning("❌ GOOGLE_SERVICE_ACCOUNT_JSON is NOT set")

    # Check Calendar IDs
    for source_id, config in CALENDAR_SOURCES.items():
        logger.info("\nChecking source: %s", source_id)
        if 'calendar_id' in config:
            logger.info("  - Has hardcoded calendar_id: %s...", config['calendar_id'][:10])
        
        if 'env' in config:
            env_var = config['env']
            val = os.getenv(env_var)
            if val:
                logger.info("  - Env var %s is set: %s", env_var, val)
            else:
                logger.warning("  - Env var %s is NOT set", env_var)
        
        resolved_id = _resolve_calendar_id(source_id)
        if resolved_id:
            logger.info("  ✅ Resolved ID: %s...", resolved_id[:10])
        else:
            logger.warning("  ❌ Could not resolve ID")


def test_auth():
    logger.info("\n=== Testing Authentication ===")
    # Try to authenticate with a dummy ID just to check credentials
    from politikk_moter.calendar_integration import GoogleCalendarIntegration
    integration = GoogleCalendarIntegration("dummy_id")
    if integration.authenticate():
        logger.info("✅ Authentication successful")
    else:
        logger.error("❌ Authentication failed")

if __name__ == "__main__":
    check_env_vars()
    # Only test auth if SA is present, to avoid hanging if that's the issue
    if os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON'):
        test_auth()
