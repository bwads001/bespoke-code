"""Command-line interface for the code assistant."""
import argparse
import os
import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Optional
from .utils import read_file, Colors
from .interactive import interactive_mode, InteractiveSession
from config.config import (
    DEFAULT_TEMPERATURE,
    OLLAMA_URL,
    MODEL_NAME,
    GENERATION_MAX_TOKENS
)

logger = logging.getLogger(__name__)

def setup_workspace(workspace_dir: Optional[Path] = None) -> Path:
    """Setup and validate workspace directory."""
    workspace_dir = workspace_dir or Path("./workspace")
    try:
        workspace_dir.mkdir(parents=True, exist_ok=True)
        return workspace_dir
    except Exception as e:
        logger.error(f"Failed to create workspace directory: {e}")
        raise

def validate_temperature(value: float) -> float:
    """Validate temperature is within acceptable range."""
    try:
        temp = float(value)
        if not 0.0 <= temp <= 1.0:
            raise ValueError("Temperature must be between 0.0 and 1.0")
        return temp
    except ValueError as e:
        logger.error(f"Invalid temperature value: {e}")
        raise

def load_context_files(files: List[str]) -> str:
    """Load and combine context from multiple files."""
    if not files:
        return ""
    
    context_parts = []
    for file_path in files:
        try:
            content = read_file(file_path)
            context_parts.append(content)
        except Exception as e:
            logger.warning(f"Failed to read context file {file_path}: {e}")
            print(f"{Colors.WARNING}Warning: Could not read context file {file_path}{Colors.RESET}")
    
    return "\n".join(context_parts)

async def process_single_prompt(prompt: str, context: str = "", temperature: float = DEFAULT_TEMPERATURE):
    """Process a single prompt without entering interactive mode."""
    workspace_dir = setup_workspace()
    session = InteractiveSession(workspace_dir, temperature)
    await session.process_input(prompt, context)

def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description='Code Assistant - AI-powered coding assistant',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Environment Variables:
    OLLAMA_URL       API endpoint URL (default: {OLLAMA_URL})
    MODEL_NAME       Model to use (default: {MODEL_NAME})
    TEMPERATURE      Generation temperature (default: {DEFAULT_TEMPERATURE})
    MAX_TOKENS      Maximum tokens per response (default: {GENERATION_MAX_TOKENS})
    LOG_LEVEL       Logging level (default: INFO)

Examples:
    # Run in interactive mode
    python bespoke_code.py -i

    # Process single prompt
    python bespoke_code.py -p "Create a hello world script"

    # Use context files
    python bespoke_code.py -i -f context.txt -f requirements.txt

    # Set custom temperature
    python bespoke_code.py -i -t 0.8
"""
    )
    
    parser.add_argument(
        '--file', '-f',
        action='append',
        help='Context file(s) to include'
    )
    parser.add_argument(
        '--temperature', '-t',
        type=validate_temperature,
        default=float(os.environ.get('TEMPERATURE', DEFAULT_TEMPERATURE)),
        help='Generation temperature (0.0-1.0)'
    )
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Force interactive mode'
    )
    parser.add_argument(
        '--prompt', '-p',
        help='Single prompt to process'
    )
    parser.add_argument(
        '--max-tokens',
        type=int,
        default=GENERATION_MAX_TOKENS,
        help=f'Maximum tokens per response (default: {GENERATION_MAX_TOKENS})'
    )
    
    return parser

def main():
    """Main entry point for the application."""
    try:
        parser = create_parser()
        args = parser.parse_args()
        
        # Load context files
        context = load_context_files(args.file)
        
        # Validate temperature
        temperature = validate_temperature(args.temperature)
        
        # Setup workspace
        setup_workspace()
        
        # Run in appropriate mode
        if args.prompt and not args.interactive:
            asyncio.run(process_single_prompt(args.prompt, context, temperature))
        else:
            asyncio.run(interactive_mode(context=context, temperature=temperature))
            
    except KeyboardInterrupt:
        print(f"\n{Colors.LOG}Operation cancelled by user.{Colors.RESET}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Application error: {e}")
        print(f"\n{Colors.ERROR}Error: {str(e)}{Colors.RESET}")
        sys.exit(1)

if __name__ == "__main__":
    main() 