# Code Assistant

A Python-based AI code assistant powered by Ollama models. Provides an interactive interface for code generation, file operations, and AI-powered assistance.

## Features

- 🤖 Ollama integration with multiple model support
- 💻 Interactive mode for direct code assistance
- 🔄 File operations with verification
- 🛡️ Environment state management
- 🐳 Docker support with configurable settings

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Interactive Mode
```bash
# Run in interactive mode
python bespoke_code.py -i

# With context files
python bespoke_code.py -i -f context.txt

# With custom temperature
python bespoke_code.py -i -t 0.5
```

### Single Prompt Mode
```bash
# Process a single prompt
python bespoke_code.py -p "Create a new Python file that prints Hello World"
```

## Docker Deployment

### Quick Start
```bash
# Start with default settings
docker-compose up -d
```

### Custom Configuration
```bash
# Use a different model
OLLAMA_MODEL=codellama:7b docker-compose up -d

# Configure runtime settings
TEMPERATURE=0.8 LOG_LEVEL=DEBUG docker-compose up -d
```

### Available Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| OLLAMA_MODEL | qwen2.5-coder:7b | Model to use with Ollama |
| PYTHON_VERSION | 3.11 | Python version for the application |
| LOG_LEVEL | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| TEMPERATURE | 0.7 | Model temperature for response creativity (0.0-1.0) |

### Model Options

The system supports these Ollama models:
- qwen2.5-coder:7b (default)
- codellama:7b
- codellama:13b
- codellama:34b
- mixtral:8x7b
- deepseek-r1:7b
- deepseek-r1:14b

## License

MIT License - see LICENSE file for details. 