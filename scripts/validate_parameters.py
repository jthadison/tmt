#!/usr/bin/env python3
"""
Parameter Validation CLI Script - Story 11.7, Task 10

Command-line interface for validating parameter configurations.
Can be used standalone or in CI/CD pipelines.
"""

import sys
import os
import argparse
import asyncio
import logging
from pathlib import Path

# Add agents to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.validation_pipeline.app.pipeline import ValidationPipeline
from agents.validation_pipeline.app.models import MonteCarloConfig
from agents.validation_pipeline.app.report_generator import ReportGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Validate trading parameter configuration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Validate configuration and save JSON report
  python validate_parameters.py --config-file config/parameters/active.yaml --output-file validation_results.json

  # Validate with custom Monte Carlo runs
  python validate_parameters.py --config-file config/parameters/active.yaml --monte-carlo-runs 500

  # Generate Markdown report for PR comment
  python validate_parameters.py --config-file config/parameters/active.yaml --format markdown

Exit Codes:
  0 - Validation passed (APPROVED)
  1 - Validation failed (REJECTED)
  2 - Pipeline error
        '''
    )

    parser.add_argument(
        '--config-file',
        required=True,
        help='Path to parameter configuration file (YAML or JSON)'
    )

    parser.add_argument(
        '--output-file',
        default='validation_results.json',
        help='Path to save validation report (default: validation_results.json)'
    )

    parser.add_argument(
        '--format',
        choices=['json', 'markdown'],
        default='json',
        help='Output report format (default: json)'
    )

    parser.add_argument(
        '--monte-carlo-runs',
        type=int,
        default=1000,
        help='Number of Monte Carlo simulation runs (default: 1000)'
    )

    parser.add_argument(
        '--parallel-workers',
        type=int,
        default=4,
        help='Number of parallel workers for Monte Carlo (default: 4)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate config file exists
    config_file = Path(args.config_file)
    if not config_file.exists():
        logger.error(f"Config file not found: {args.config_file}")
        return 2

    logger.info(f"Starting parameter validation for: {args.config_file}")
    logger.info(f"Monte Carlo runs: {args.monte_carlo_runs}")
    logger.info(f"Parallel workers: {args.parallel_workers}")

    try:
        # Create Monte Carlo config
        mc_config = MonteCarloConfig(
            num_runs=args.monte_carlo_runs,
            parallel_workers=args.parallel_workers
        )

        # Create validation pipeline
        pipeline = ValidationPipeline(monte_carlo_config=mc_config)

        # Run validation
        logger.info("Running validation pipeline...")
        report = await pipeline.validate_parameter_change(
            str(config_file),
            None  # We'll save manually based on format
        )

        # Generate and save report
        report_gen = ReportGenerator()

        if args.format == 'json':
            report_gen.save_report(report, args.output_file, format='json')
            logger.info(f"JSON report saved to: {args.output_file}")
        else:  # markdown
            report_gen.save_report(report, args.output_file, format='markdown')
            logger.info(f"Markdown report saved to: {args.output_file}")

        # Print summary to console
        print("\n" + "=" * 80)
        print("VALIDATION SUMMARY")
        print("=" * 80)
        print(f"Status: {report.status.value}")
        print(f"Duration: {report.duration_seconds:.1f}s")
        print(f"All Checks Passed: {report.all_checks_passed}")
        print()

        print("Individual Checks:")
        print(f"  ✓ Schema Validation: {'PASSED' if report.schema_validation.passed else 'FAILED'}")
        print(f"  ✓ Overfitting Score: {'PASSED' if report.overfitting_validation.passed else 'FAILED'} ({report.overfitting_validation.overfitting_score:.3f})")
        print(f"  ✓ Walk-Forward Backtest: {'PASSED' if report.walk_forward_validation.passed else 'FAILED'}")
        print(f"  ✓ Monte Carlo Simulation: {'PASSED' if report.monte_carlo_validation.passed else 'FAILED'}")
        print(f"  ✓ Stress Testing: {'PASSED' if report.stress_test_validation.passed else 'FAILED'}")
        print(f"  ✓ Acceptance Criteria: {report.acceptance_criteria.passed_count}/{len(report.acceptance_criteria.all_criteria)} passed")
        print()

        if report.recommendations:
            print("Recommendations:")
            for rec in report.recommendations:
                print(f"  - {rec}")
            print()

        print("=" * 80)

        # Exit with appropriate code
        if report.all_checks_passed:
            logger.info("✅ Validation PASSED - Parameters approved for deployment")
            return 0
        else:
            logger.warning("❌ Validation FAILED - Parameters blocked from deployment")
            return 1

    except Exception as e:
        logger.error(f"Validation pipeline error: {e}", exc_info=True)
        return 2


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
