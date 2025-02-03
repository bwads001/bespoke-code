"""Main entry point for the code assistant."""
import argparse
import os
import asyncio
import logging
from pathlib import Path
from colorama import init

from config.config import DEFAULT_TEMPERATURE
from .utils import Colors, read_file
from .interactive import interactive_mode, InteractiveSession

# Initialize colorama for Windows support
init()

# Get log level from environment or default to INFO
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
log_level = getattr(logging, log_level, logging.INFO)

# Update logging configuration
logging.basicConfig(
    level=log_level,
    format=f'{Colors.LOG}%(levelname)s: %(message)s{Colors.RESET}',
    datefmt='%H:%M:%S'
)

# Configure loggers
logger = logging.getLogger(__name__)

async def process_single_prompt(prompt: str, context: str = "", temperature: float = DEFAULT_TEMPERATURE):
    """Process a single prompt without entering interactive mode."""
    workspace_dir = Path("./workspace")
    workspace_dir.mkdir(parents=True, exist_ok=True)
    
    session = InteractiveSession(workspace_dir, temperature)
    await session.process_input(prompt, context)

def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description='Bespoke Code Assistant')
    parser.add_argument('--file', '-f', action='append', help='Context file(s)')
    parser.add_argument('--temperature', '-t', type=float, 
                       default=float(os.environ.get('TEMPERATURE', DEFAULT_TEMPERATURE)),
                       help='Generation temperature')
    parser.add_argument('--interactive', '-i', action='store_true', help='Force interactive mode')
    parser.add_argument('--prompt', '-p', help='Single prompt to process')
    
    args = parser.parse_args()
    context = ""
    
    if args.file:
        context = "\n".join(read_file(f) for f in args.file)
    
    if args.prompt and not args.interactive:
        asyncio.run(process_single_prompt(args.prompt, context, args.temperature))
    else:
        asyncio.run(interactive_mode(context=context, temperature=args.temperature))

if __name__ == "__main__":
    main()