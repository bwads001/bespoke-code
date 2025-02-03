# API Configuration
import os

# Ollama API settings - override with environment variables for Docker
OLLAMA_URL = os.getenv('OLLAMA_API_URL', 'http://localhost:11434')
MODEL_NAME = os.getenv('OLLAMA_MODEL', 'qwen2.5-coder:7b')
# Check available models with: curl http://localhost:11434/api/tags

# Token Management
MODEL_MAX_TOKENS = 32768  # Maximum context window for the model
SYSTEM_RESERVED_TOKENS = 4000  # System prompt + tool instructions
QUERY_RESERVED_TOKENS = 2000   # Current query and immediate context
MAX_HISTORY_TOKENS = MODEL_MAX_TOKENS - SYSTEM_RESERVED_TOKENS - QUERY_RESERVED_TOKENS

# Generation Configuration
GENERATION_MAX_TOKENS = 2000  # Maximum tokens to generate per response
DEFAULT_TEMPERATURE = 0.3  # Temperature for model generation 
