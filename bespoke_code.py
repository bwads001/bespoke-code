#!/usr/bin/env python3
"""Main entry point for the code assistant.

This module serves as the primary entry point for the code assistant application.
It provides both interactive and single-prompt modes, with support for context files
and temperature configuration.
"""

import os
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import and run the main application
from core.cli import main

if __name__ == "__main__":
    main() 