#!/usr/bin/env python3
"""
F1 Race Strategy Workbench - Main Entry Point

Usage:
    python run.py                    # Start full application (backend + opens browser)
    python run.py --backend-only     # Start backend only
    python run.py --test             # Run all tests
    python run.py --test unit        # Run unit tests
    python run.py --test api         # Run API tests
    python run.py --download 2023 1  # Download session data
    python run.py --dev              # Development mode with auto-reload
"""

import argparse
import os
import subprocess
import sys
import webbrowser
from pathlib import Path

# Ensure src is in path
ROOT_DIR = Path(__file__).parent
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))
os.environ["PYTHONPATH"] = str(SRC_DIR)


def run_backend(dev_mode: bool = False, port: int = 8000) -> None:
    """Start the backend server."""
    print("🏎️  Starting F1 Race Strategy Workbench...")
    
    cmd = [
        sys.executable, "-m", "uvicorn",
        "rsw.main:app",
        "--host", "0.0.0.0",
        "--port", str(port),
    ]
    
    if dev_mode:
        cmd.append("--reload")
        print("   Running in development mode with auto-reload")
    
    print(f"   Backend: http://localhost:{port}")
    print(f"   API Docs: http://localhost:{port}/docs")
    print("\n   Press Ctrl+C to stop\n")
    
    subprocess.run(cmd, cwd=ROOT_DIR)


def run_frontend() -> None:
    """Start the frontend dev server."""
    frontend_dir = ROOT_DIR / "frontend"
    
    # Check if node_modules exists
    if not (frontend_dir / "node_modules").exists():
        print("📦 Installing frontend dependencies...")
        subprocess.run(["npm", "install"], cwd=frontend_dir, check=True)
    
    print("🖥️  Starting frontend...")
    subprocess.run(["npm", "run", "dev"], cwd=frontend_dir)


def run_tests(test_type: str = "all") -> int:
    """Run tests."""
    print(f"🧪 Running {test_type} tests...\n")
    
    cmd = [sys.executable, "-m", "pytest", "-v"]
    
    if test_type == "unit":
        cmd.extend(["tests/", "-k", "not api and not integration"])
    elif test_type == "api":
        cmd.extend(["tests/test_api_endpoints.py"])
    elif test_type == "strategy":
        cmd.extend(["tests/test_strategy.py"])
    elif test_type == "exceptions":
        cmd.extend(["tests/test_exceptions.py"])
    elif test_type == "all":
        cmd.extend(["tests/", "--tb=short"])
    else:
        cmd.extend(["tests/", "-k", test_type])
    
    result = subprocess.run(cmd, cwd=ROOT_DIR)
    return result.returncode


def run_tests_with_coverage() -> int:
    """Run tests with coverage report."""
    print("🧪 Running tests with coverage...\n")
    
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "--cov=rsw",
        "--cov-report=term-missing",
        "--cov-report=html:coverage_html",
        "-v"
    ]
    
    result = subprocess.run(cmd, cwd=ROOT_DIR)
    
    if result.returncode == 0:
        print(f"\n📊 Coverage report: {ROOT_DIR}/coverage_html/index.html")
    
    return result.returncode


def download_session(year: int, round_num: int, session_type: str = "Race") -> None:
    """Download a session for replay."""
    print(f"📥 Downloading {year} Round {round_num} {session_type}...")
    
    cmd = [
        sys.executable, "scripts/download_session.py",
        "--year", str(year),
        "--round", str(round_num),
        "--session", session_type,
    ]
    
    subprocess.run(cmd, cwd=ROOT_DIR)


def run_full_app() -> None:
    """Run both backend and frontend."""
    import threading
    import time
    
    print("🏁 Starting F1 Race Strategy Workbench (Full Stack)")
    print("=" * 50)
    
    # Start backend in background
    def start_backend():
        run_backend(dev_mode=True)
    
    backend_thread = threading.Thread(target=start_backend, daemon=True)
    backend_thread.start()
    
    # Wait for backend to start
    time.sleep(2)
    
    # Open browser
    webbrowser.open("http://localhost:5173")
    
    # Start frontend (blocking)
    run_frontend()


def type_check() -> int:
    """Run type checking with mypy."""
    print("🔍 Running type checks...\n")
    cmd = [sys.executable, "-m", "mypy", "src/rsw", "--ignore-missing-imports"]
    result = subprocess.run(cmd, cwd=ROOT_DIR)
    return result.returncode


def lint() -> int:
    """Run linting with ruff."""
    print("🧹 Running linter...\n")
    cmd = [sys.executable, "-m", "ruff", "check", "src/rsw"]
    result = subprocess.run(cmd, cwd=ROOT_DIR)
    return result.returncode


def format_code() -> None:
    """Format code with ruff."""
    print("✨ Formatting code...\n")
    subprocess.run([sys.executable, "-m", "ruff", "format", "src/rsw"], cwd=ROOT_DIR)
    subprocess.run([sys.executable, "-m", "ruff", "check", "--fix", "src/rsw"], cwd=ROOT_DIR)
    print("Done!")


def main():
    parser = argparse.ArgumentParser(
        description="F1 Race Strategy Workbench",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py                     Start full application
  python run.py --backend           Start backend only  
  python run.py --test              Run all tests
  python run.py --test strategy     Run strategy tests
  python run.py --coverage          Run tests with coverage
  python run.py --download 2023 1   Download Bahrain 2023
  python run.py --lint              Run linter
  python run.py --format            Format code
        """
    )
    
    parser.add_argument("--backend", "-b", action="store_true",
                        help="Start backend server only")
    parser.add_argument("--frontend", "-f", action="store_true",
                        help="Start frontend only")
    parser.add_argument("--dev", "-d", action="store_true",
                        help="Development mode with auto-reload")
    parser.add_argument("--port", "-p", type=int, default=8000,
                        help="Backend port (default: 8000)")
    parser.add_argument("--test", "-t", nargs="?", const="all",
                        help="Run tests (all, unit, api, strategy)")
    parser.add_argument("--coverage", "-c", action="store_true",
                        help="Run tests with coverage")
    parser.add_argument("--download", nargs=2, type=int, metavar=("YEAR", "ROUND"),
                        help="Download session data")
    parser.add_argument("--lint", action="store_true",
                        help="Run linter")
    parser.add_argument("--format", action="store_true",
                        help="Format code")
    parser.add_argument("--typecheck", action="store_true",
                        help="Run type checking")
    
    args = parser.parse_args()
    
    # Handle commands
    if args.test:
        sys.exit(run_tests(args.test))
    
    if args.coverage:
        sys.exit(run_tests_with_coverage())
    
    if args.download:
        download_session(args.download[0], args.download[1])
        return
    
    if args.lint:
        sys.exit(lint())
    
    if args.format:
        format_code()
        return
    
    if args.typecheck:
        sys.exit(type_check())
    
    if args.frontend:
        run_frontend()
        return
    
    if args.backend:
        run_backend(dev_mode=args.dev, port=args.port)
        return
    
    # Default: run full app
    run_full_app()


if __name__ == "__main__":
    main()
