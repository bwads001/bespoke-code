#!/usr/bin/env python3
"""Main entry point for the code assistant.

This module serves as the primary entry point for the code assistant application.
It provides both interactive and single-prompt modes, with support for context files
and temperature configuration.
"""

import os
import sys
import asyncio
import logging
from core.interactive import interactive_mode

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import and run the main application
from core.cli import main

async def main():
    await interactive_mode()

if __name__ == "__main__":
    asyncio.run(main()) 