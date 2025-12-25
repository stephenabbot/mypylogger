"""Command-line entry point for badge system.

This module provides a command-line interface for the badge system,
allowing manual badge updates and configuration checks.
"""

import sys

from badges import main

if __name__ == "__main__":
    sys.exit(main())
