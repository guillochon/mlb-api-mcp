#!/usr/bin/env python3
"""
Coverage test runner for MLB API MCP Server.

This script provides convenient commands to run tests with coverage reporting.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*60)
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Run MLB API tests with coverage")
    parser.add_argument(
        "command",
        choices=["test", "coverage", "html", "xml", "clean"],
        help="Command to run"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--fail-under",
        type=int,
        default=85,
        help="Minimum coverage percentage (default: 85)"
    )
    
    args = parser.parse_args()
    
    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        print("Error: pyproject.toml not found. Please run from the project root.")
        sys.exit(1)
    
    if args.command == "test":
        # Run basic tests without coverage
        cmd = ["uv", "run", "pytest", "tests/"]
        if args.verbose:
            cmd.append("-v")
        success = run_command(cmd, "Running tests without coverage")
        
    elif args.command == "coverage":
        # Run tests with coverage
        cmd = [
            "uv", "run", "pytest", "tests/",
            "--cov=mlb_api",
            "--cov=generic_api",
            "--cov-report=term-missing",
            f"--cov-fail-under={args.fail_under}"
        ]
        if args.verbose:
            cmd.append("-v")
        success = run_command(cmd, "Running tests with coverage")
        
    elif args.command == "html":
        # Generate HTML coverage report
        cmd = [
            "uv", "run", "pytest", "tests/",
            "--cov=mlb_api",
            "--cov=generic_api",
            "--cov-report=html:htmlcov",
            "--cov-report=term-missing",
            f"--cov-fail-under={args.fail_under}"
        ]
        if args.verbose:
            cmd.append("-v")
        success = run_command(cmd, "Generating HTML coverage report")
        if success:
            print(f"\nHTML coverage report generated in: {Path('htmlcov').absolute()}")
            print("Open htmlcov/index.html in your browser to view the report.")
            
    elif args.command == "xml":
        # Generate XML coverage report (useful for CI/CD)
        cmd = [
            "uv", "run", "pytest", "tests/",
            "--cov=mlb_api",
            "--cov=generic_api",
            "--cov-report=xml:coverage.xml",
            "--cov-report=term-missing",
            f"--cov-fail-under={args.fail_under}"
        ]
        if args.verbose:
            cmd.append("-v")
        success = run_command(cmd, "Generating XML coverage report")
        if success:
            print(f"\nXML coverage report generated: {Path('coverage.xml').absolute()}")
            
    elif args.command == "clean":
        # Clean up coverage files
        coverage_files = [
            ".coverage",
            "coverage.xml",
            "htmlcov",
            ".pytest_cache"
        ]
        
        print("Cleaning up coverage files...")
        for file_path in coverage_files:
            path = Path(file_path)
            if path.exists():
                if path.is_dir():
                    import shutil
                    shutil.rmtree(path)
                else:
                    path.unlink()
                print(f"Removed: {file_path}")
            else:
                print(f"Not found: {file_path}")
        print("Cleanup complete!")
        success = True
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main() 