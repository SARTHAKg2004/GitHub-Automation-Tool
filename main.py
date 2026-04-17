"""
GitHub Repository Validator - Main Entry Point
Run: python main.py
"""

import sys
import os
import argparse

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(__file__))

from modules.logger import setupLogger
from modules.scanner import RepositoryScanner
from modules.reportGenerator import generateExcelReport
from dashboard.app import runDashboard
from modules.github_incremental import get_incremental_changes


def parseArgs():
    parser = argparse.ArgumentParser(
        description="GitHub Repository Validator - Production Grade"
    )
    parser.add_argument(
        "--url", type=str, help="GitHub repository URL to scan"
    )
    parser.add_argument(
        "--dashboard", action="store_true", default=True,
        help="Launch web dashboard (default: True)"
    )
    parser.add_argument(
        "--output", type=str, default="uploads/report.xlsx",
        help="Output Excel report path"
    )
    parser.add_argument(
        "--workers", type=int, default=8,
        help="Number of parallel workers (default: 8)"
    )
    parser.add_argument(
        "--deep-scan-threshold", type=int, default=3,
        help="Rule-based issue count to trigger deep LLM scan (default: 3)"
    )
    return parser.parse_args()


def main():
    args = parseArgs()
    logger = setupLogger()

    # 🔹 DASHBOARD MODE
    if args.dashboard and not args.url:
        logger.info("Starting GitHub Validator Dashboard...")
        runDashboard()

    # 🔹 CLI MODE
    elif args.url:
        logger.info(f"Starting CLI scan for: {args.url}")

        scanner = RepositoryScanner(
            maxWorkers=args.workers,
            deepScanThreshold=args.deep_scan_threshold
        )

        # 🔥 GitHub API based incremental scan
        try:
            changed_files = get_incremental_changes(args.url)

            if changed_files is None:
                logger.info("🔄 First scan → running full scan")
            elif len(changed_files) == 0:
                logger.info("✅ No changes detected → minimal scan")
            else:
                logger.info(f"⚡ Incremental scan: {len(changed_files)} files")

        except Exception as e:
            logger.warning(f"Incremental scan failed: {e}")
            changed_files = None

        # 🔹 Run scanner
        results = scanner.scanRepository(
            args.url,
            changed_files=changed_files
        )

        outputPath = generateExcelReport(results, args.output)

        logger.info(f"Scan complete. Report saved to: {outputPath}")
        print(f"\n✅ Scan Complete! Report: {outputPath}")
        print(f"   Total Files  : {results['summary']['totalFiles']}")
        print(f"   Issues Found : {results['summary']['totalIssues']}")
        print(f"   Clean Files  : {results['summary']['cleanFiles']}")
        print(f"   Failed Files : {results['summary']['failedFiles']}")
        print(f"   Skipped Files: {results['summary']['skippedFiles']}")

    # 🔹 FALLBACK
    else:
        print("Usage:")
        print("  Dashboard: python main.py --dashboard")
        print("  CLI Scan : python main.py --url https://github.com/user/repo")


if __name__ == "__main__":
    main()