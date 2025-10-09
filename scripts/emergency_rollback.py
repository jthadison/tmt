#!/usr/bin/env python
"""
Emergency Configuration Rollback Script

One-command rollback to last known good configuration.

Usage:
    python scripts/emergency_rollback.py [--version VERSION] [--reason REASON]

Examples:
    # Rollback to previous version
    python scripts/emergency_rollback.py --reason "Critical production issue"

    # Rollback to specific version
    python scripts/emergency_rollback.py --version 1.0.0 --reason "Emergency fix"
"""

import sys
import argparse
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.config_manager.app.config_manager import ConfigurationManager
from agents.config_manager.app.rollback import RollbackManager
from agents.config_manager.app.slack_notifier import SlackNotifier

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Emergency configuration rollback",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--version",
        help="Version to rollback to (default: previous version)",
        default=None
    )

    parser.add_argument(
        "--reason",
        help="Reason for emergency rollback",
        default="Emergency rollback initiated via script"
    )

    parser.add_argument(
        "--no-notify",
        action="store_true",
        help="Don't send Slack notifications"
    )

    args = parser.parse_args()

    logger.critical("=" * 60)
    logger.critical("EMERGENCY CONFIGURATION ROLLBACK INITIATED")
    logger.critical("=" * 60)

    try:
        # Initialize managers
        repo_root = Path(__file__).parent.parent
        config_dir = repo_root / "config" / "parameters"
        schema_path = config_dir / "schema.json"

        logger.info(f"Config directory: {config_dir}")
        logger.info(f"Schema path: {schema_path}")

        # Create managers
        config_manager = ConfigurationManager(
            config_dir=config_dir,
            schema_path=schema_path,
            repo_path=repo_root
        )

        rollback_manager = RollbackManager(config_manager)

        # Get current version
        current_version = config_manager.get_active_version()
        logger.warning(f"Current version: {current_version}")

        # Determine target version
        target_version = args.version
        if target_version is None:
            logger.info("No target version specified, using previous version")

        # Confirm rollback
        if target_version:
            logger.warning(f"Target version: {target_version}")
        else:
            logger.warning("Target version: Previous version (auto-detected)")

        logger.warning(f"Reason: {args.reason}")

        print("\n⚠️  WARNING: This will rollback the configuration! ⚠️")
        print(f"\nFrom: v{current_version or 'unknown'}")
        print(f"To: v{target_version or 'previous'}")
        print(f"Reason: {args.reason}\n")

        confirmation = input("Type 'ROLLBACK' to confirm: ")

        if confirmation != "ROLLBACK":
            logger.info("Rollback cancelled by user")
            print("❌ Rollback cancelled")
            return 1

        # Perform emergency rollback
        logger.critical("Executing emergency rollback...")

        rolled_back_config = rollback_manager.rollback(
            version=target_version,
            reason=args.reason,
            emergency=True,
            notify=not args.no_notify
        )

        logger.critical("=" * 60)
        logger.critical("EMERGENCY ROLLBACK COMPLETED SUCCESSFULLY")
        logger.critical("=" * 60)

        print(f"\n✅ Rollback successful!")
        print(f"   From: v{current_version}")
        print(f"   To: v{rolled_back_config.version}")
        print(f"\n📝 New active configuration: v{rolled_back_config.version}")
        print(f"   Author: {rolled_back_config.author}")
        print(f"   Effective: {rolled_back_config.effective_date}")

        if not args.no_notify:
            print(f"\n📢 Slack notification sent")

        print("\n⚠️  Next steps:")
        print("   1. Verify system is operating normally")
        print("   2. Investigate root cause of issue")
        print("   3. Create incident report")
        print("   4. Plan fix for next deployment\n")

        return 0

    except Exception as e:
        logger.critical(f"Emergency rollback FAILED: {e}", exc_info=True)
        print(f"\n❌ Emergency rollback FAILED: {e}")
        print("\n⚠️  Manual intervention required!")
        print("   1. Check configuration files in config/parameters/")
        print("   2. Verify Git repository status")
        print("   3. Contact system administrator")
        return 1


if __name__ == "__main__":
    sys.exit(main())
