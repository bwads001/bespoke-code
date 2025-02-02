from colorama import init, Fore, Style

# Initialize colorama for Windows support
init()

class Colors:
    USER = Fore.GREEN
    AI = Fore.BLUE
    TOOL_OUTPUT = Fore.CYAN
    ERROR = Fore.RED
    LOG = Fore.YELLOW
    RESET = Style.RESET_ALL

def estimate_tokens(text):
    """
    Roughly estimate the number of tokens in a text.
    This is a simple approximation (about 4 chars per token for English text).
    For code, the ratio might be closer to 3 chars per token.
    """
    chars_per_token = 3 if any(keyword in text for keyword in ['def ', 'class ', 'import ', 'print(']) else 4
    return len(text) // chars_per_token

def read_file(file_path):
    """Read the contents of a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return None 