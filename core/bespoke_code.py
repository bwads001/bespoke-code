import requests
import json
import argparse
import sys
from pathlib import Path
import os

# Add parent directory to Python path when running as script
if __name__ == '__main__':
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tools import Tools
import logging
from colorama import init, Fore, Style

from config.config import *
from config.prompts import SYSTEM_PROMPT, TOOL_INSTRUCTIONS
from utils import Colors, estimate_tokens, read_file

# Initialize colorama for Windows support
init()

# Color constants for different message types
class Colors:
    USER = Fore.GREEN
    AI = Fore.BLUE
    TOOL_OUTPUT = Fore.CYAN
    ERROR = Fore.RED
    LOG = Fore.YELLOW
    RESET = Style.RESET_ALL

# Update logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format=f'{Colors.LOG}%(levelname)s: %(message)s{Colors.RESET}',
    datefmt='%H:%M:%S'
)

# Configure loggers
logger = logging.getLogger(__name__)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logger.setLevel(logging.WARNING)

# Define the URL for your Ollama instance
OLLAMA_URL = "http://localhost:11434/api/generate"

# Constants for context management
# Qwen 2.5 7B has a 32k context window
QWEN_MAX_TOKENS = 32768
# Reserve tokens for system prompt, current query, and results
SYSTEM_RESERVED_TOKENS = 4000  # System prompt + tool instructions
QUERY_RESERVED_TOKENS = 2000   # Current query and immediate context
# Maximum tokens for conversation history
MAX_HISTORY_TOKENS = QWEN_MAX_TOKENS - SYSTEM_RESERVED_TOKENS - QUERY_RESERVED_TOKENS  # About 26k tokens for history

def generate_text(prompt, context="", max_tokens=2000, temperature=0.7, conversation_history=None):
    """
    Generate text using the qwen2.5-coder:7b model hosted on Ollama.

    Args:
        prompt (str): The input prompt for the model.
        context (str): Additional context from files.
        max_tokens (int): The maximum number of tokens to generate in the response.
        temperature (float): Controls randomness; lower values make the output more deterministic.
        conversation_history (list): List of previous exchanges.

    Returns:
        str: The generated text from the model.
    """
    # Prepare the conversation context
    logger.debug("Building prompt...")
    full_prompt = SYSTEM_PROMPT + "\n\n" + TOOL_INSTRUCTIONS + "\n\n"
    
    if context:
        logger.debug("Adding context...")
        full_prompt += f"Context:\n{context}\n\n"
    else:
        logger.info("2. No Context provided")
    
    if conversation_history:
        logger.debug(f"Adding {len(conversation_history)} previous exchanges")
        full_prompt += "Previous conversation:\n"
        for entry in conversation_history:
            full_prompt += f"User: {entry['user']}\nAssistant: {entry['assistant']}\n\n"
            logger.debug(f"History entry:\nUser: {entry['user']}\nAssistant: {entry['assistant'][:100]}...")
    else:
        logger.info("3. No Conversation History")
    
    logger.debug("4. Adding Current Prompt:")
    logger.debug(prompt)
    full_prompt += f"User: {prompt}\nAssistant:"
    
    # Log token estimation at debug level
    estimated_tokens = estimate_tokens(full_prompt)
    logger.debug(f"=== Prompt Stats ===")
    logger.debug(f"Estimated total tokens: {estimated_tokens}")
    logger.debug(f"Max tokens allowed: {max_tokens}")
    logger.debug("==================")

    # Define the request payload
    data = {
        "model": "qwen2.5-coder:7b",
        "prompt": full_prompt,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True
    }

    try:
        # Send a POST request to the Ollama API
        logger.debug("Sending request to Ollama API...")
        response = requests.post(OLLAMA_URL, json=data, stream=True)
        response.raise_for_status()

        # Process the streaming response
        generated_text = ""
        current_response = ""
        for line in response.iter_lines():
            if line:
                json_response = json.loads(line)
                if 'response' in json_response:
                    chunk = json_response['response']
                    # Only color the AI's direct responses (starting with 🤖)
                    if chunk.startswith('🤖'):
                        if current_response:  # End previous response
                            print(f"{Colors.RESET}", end='', flush=True)
                        print(f"{Colors.AI}", end='', flush=True)
                        current_response = chunk
                    else:
                        current_response += chunk
                    print(chunk, end='', flush=True)
                    generated_text += chunk
                
                if json_response.get('done', False):
                    if current_response:  # End last response
                        print(f"{Colors.RESET}", end='', flush=True)
                    print()  # New line at the end
                    break

        logger.debug(f"Response generated (length: {len(generated_text)} chars)")
        return generated_text

    except requests.exceptions.RequestException as e:
        logger.error(f"Error interacting with Ollama API: {e}")
        print(f"{Colors.ERROR}🚫 Error: {e}{Colors.RESET}")
        return ""

def execute_tool(response, prompt, tools, context="", temperature=0.7, conversation_history=None):
    """Parse and execute tool commands from the response."""
    import re
    
    # Find tool commands in the response
    tool_pattern = r'<tool>(.*?)</tool>\s*<args>(.*?)</args>'
    matches = list(re.finditer(tool_pattern, response, re.DOTALL))
    results = []
    
    for match in matches:
        tool_name = match.group(1).strip()
        args_content = match.group(2)
        
        logger.debug(f"Raw tool arguments:\n{args_content}")
        
        args = [
            line 
            for line in args_content.splitlines()
            if line.strip() and not line.strip().startswith(('mode=', '<!--', '```'))
        ]
        
        logger.debug(f"Processed arguments: {args}")
        
        if hasattr(tools, tool_name):
            tool_func = getattr(tools, tool_name)
            try:
                if tool_name == 'write_file':
                    if len(args) < 2:
                        raise Exception("Missing filename or content for write_file")
                    filename = args[0].strip()
                    content_lines = args[1:]
                    if content_lines:
                        def get_indent(line):
                            return len(line) - len(line.lstrip())
                        indents = [get_indent(line) for line in content_lines if line.strip()]
                        if indents:
                            min_indent = min(indents)
                            content_lines = [line[min_indent:] if line.strip() else '' for line in content_lines]
                    
                    content = '\n'.join(content_lines)
                    content = content.replace('\\n', '\n').replace('\\t', '\t')
                    
                    result = tool_func(filename, content)
                    file_path = tools.workspace_dir / filename
                    if not file_path.exists():
                        raise Exception(f"File {filename} was not created")
                    print(f"\n{Colors.TOOL_OUTPUT}```\nOperation Result:\n{result}\nFile contents:\n{content}\n```{Colors.RESET}")
                else:
                    result = tool_func(*[arg.strip() for arg in args])
                    print(f"\n{Colors.TOOL_OUTPUT}```\nOperation Result:\n{result}\n```{Colors.RESET}")
                
                results.append({"tool": tool_name, "result": result, "success": True, "content": content if tool_name == 'write_file' else result})
            except Exception as e:
                error_msg = str(e)
                print(f"\n{Colors.ERROR}```\nError:\n{error_msg}\n```{Colors.RESET}")
                results.append({"tool": tool_name, "result": error_msg, "success": False})
        else:
            error_msg = f"Operation not supported"
            print(f"\n{Colors.ERROR}```\nError:\n{error_msg}\n```{Colors.RESET}")
            results.append({"tool": tool_name, "result": error_msg, "success": False})
    
    # If there were tool executions, only generate a follow-up for errors or incomplete tasks
    if results:
        operations_summary = []
        has_errors = False
        for r in results:
            if not r['success']:
                has_errors = True
                operations_summary.append(f"Operation failed: {r['result']}")
        
        # Only generate follow-up if there were errors
        if has_errors:
            operation_context = "\n".join(operations_summary)
            follow_up = generate_text(
                f"""TASK CONTINUATION:
The user asked: "{prompt}"

Some operations failed:
{operation_context}

Please address the errors and complete the task.""",
                context=context,
                temperature=temperature,
                conversation_history=conversation_history
            )
            return response + "\n" + operation_context + "\n" + follow_up
    
    return response

def interactive_mode(context="", temperature=0.7):
    """
    Run an interactive conversation session with the model.
    """
    tools = Tools()
    conversation_history = []
    print(f"\n{Colors.LOG}Entering interactive mode. Type 'exit' or 'quit' to end the session.")
    print(f"Type 'clear' to clear conversation history.{Colors.RESET}")
    print("----------------------------------------")
    
    while True:
        try:
            print(f"\n{Colors.USER}> {Colors.RESET}", end='', flush=True)
            user_input = input().strip()
            
            if user_input.lower() in ['exit', 'quit']:
                print(f"{Colors.LOG}Exiting...{Colors.RESET}")
                break
            elif user_input.lower() == 'clear':
                conversation_history = []
                print(f"{Colors.LOG}Conversation history cleared.{Colors.RESET}")
                continue
            elif not user_input:
                continue
                
            # Generate response
            response = generate_text(
                user_input,
                context=context,
                temperature=temperature,
                conversation_history=conversation_history
            )
            
            # Execute any tool commands and get complete response with results
            full_response = execute_tool(response, user_input, tools, context, temperature, conversation_history)
            
            # Add to conversation history
            conversation_history.append({
                'user': user_input,
                'assistant': full_response
            })
            
            # Manage history size
            total_tokens = sum(estimate_tokens(f"{ex['user']}\n{ex['assistant']}")
                             for ex in conversation_history)
            
            if total_tokens > MAX_HISTORY_TOKENS:
                removed_exchanges = 0
                while (sum(estimate_tokens(f"{ex['user']}\n{ex['assistant']}")
                          for ex in conversation_history) > MAX_HISTORY_TOKENS):
                    conversation_history.pop(0)
                    removed_exchanges += 1
                
                print(f"\n{Colors.LOG}[Note: Removed {removed_exchanges} oldest conversation exchanges to keep within context limit]{Colors.RESET}")
                
        except KeyboardInterrupt:
            print(f"\n{Colors.LOG}Use 'exit' or 'quit' to end the session properly.{Colors.RESET}")
            continue
        except EOFError:
            break

def main():
    parser = argparse.ArgumentParser(description='Interact with Qwen2.5-coder model via Ollama')
    parser.add_argument('--file', '-f', action='append', help='Path to file(s) to use as context. Can be specified multiple times.')
    parser.add_argument('--temperature', '-t', type=float, default=0.7, help='Temperature for generation (default: 0.7)')
    parser.add_argument('--prompt', '-p', help='Prompt to send to the model. If not provided, will enter interactive mode.')
    parser.add_argument('--interactive', '-i', action='store_true', help='Force interactive mode even with prompt')
    
    args = parser.parse_args()

    # Read context from files if provided
    context = ""
    if args.file:
        for file_path in args.file:
            content = read_file(file_path)
            if content:
                context += f"\nContent of {file_path}:\n{content}\n"
    
    # Handle interactive mode
    if args.interactive or not args.prompt:
        interactive_mode(context, args.temperature)
        return
        
    # Single prompt mode
    generate_text(args.prompt, context, temperature=args.temperature)

if __name__ == "__main__":
    main()