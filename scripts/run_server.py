#!/usr/bin/env python3
"""
Run the Race Strategy Workbench backend server.

Usage:
    python scripts/run_server.py
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from rsw.main import main

if __name__ == "__main__":
    main()
