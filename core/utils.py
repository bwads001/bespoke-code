"""Utility functions and classes for core functionality."""
from colorama import init, Fore, Style

# Initialize colorama for Windows support
init()

class Colors:
    """Color definitions for consistent UI formatting."""
    # Basic colors
    USER = Fore.WHITE
    AI = Fore.LIGHTBLUE_EX
    TOOL_OUTPUT = Fore.CYAN
    ERROR = Fore.RED
    LOG = Fore.YELLOW
    SUCCESS = Fore.GREEN
    WARNING = Fore.YELLOW
    RESET = Style.RESET_ALL
    
    @classmethod
    def format(cls, text: str, color) -> str:
        """Format text with color and reset."""
        return f"{color}{text}{cls.RESET}"
    
    @classmethod
    def error(cls, text: str) -> str:
        """Format error message."""
        return cls.format(f"🚫 {text}", cls.ERROR)
    
    @classmethod
    def success(cls, text: str) -> str:
        """Format success message."""
        return cls.format(f"✓ {text}", cls.SUCCESS)
    
    @classmethod
    def warning(cls, text: str) -> str:
        """Format warning message."""
        return cls.format(f"⚠ {text}", cls.WARNING)
    
    @classmethod
    def info(cls, text: str) -> str:
        """Format info message."""
        return cls.format(f"ℹ {text}", cls.LOG)
    
    @classmethod
    def user(cls, text: str) -> str:
        """Format user message."""
        return cls.format(text, cls.USER)
    
    @classmethod
    def ai(cls, text: str) -> str:
        """Format AI message."""
        return cls.format(text, cls.AI)
    
    @classmethod
    def tool(cls, text: str) -> str:
        """Format tool output."""
        return cls.format(text, cls.TOOL_OUTPUT)

def estimate_tokens(text: str) -> int:
    """
    Roughly estimate the number of tokens in a text.
    This is a simple approximation (about 4 chars per token for English text).
    For code, the ratio might be closer to 3 chars per token.
    
    Args:
        text (str): The text to estimate tokens for
        
    Returns:
        int: Estimated number of tokens
    """
    chars_per_token = 3 if any(keyword in text for keyword in ['def ', 'class ', 'import ', 'print(']) else 4
    return len(text) // chars_per_token

def read_file(file_path: str) -> str | None:
    """Read the contents of a file.
    
    Args:
        file_path (str): Path to the file to read
        
    Returns:
        str | None: File contents or None if reading fails
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return None 