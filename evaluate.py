"""Convenience entry point for evaluation.

Usage:
    python evaluate.py                  # Quick mode (default)
    python evaluate.py --mode quick     # Quick: 10 queries, <3 min
    python evaluate.py --mode standard  # Standard: 30 queries, <10 min
    python evaluate.py --mode full      # Full: 100 queries
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from evaluation.run_evaluation import main

if __name__ == "__main__":
    asyncio.run(main())
