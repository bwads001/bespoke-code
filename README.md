# Code Assistant

A Python-based AI code assistant powered by Ollama models. Provides an interactive interface for code generation, file operations, and AI-powered assistance.

## Prerequisites

- Python 3.11 or higher
- [Ollama](https://ollama.ai/) installed and running locally
- One of the supported Ollama models pulled (see Model Options below)

## Installation

1. Clone the repository:
```bash
git clone [Bespoke Code](https://github.com/bwads001/bespoke-code.git)
cd [bespoke-code]
```

2. Create and activate a virtual environment:
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Ensure Ollama is running with a supported model:
```bash
# Start Ollama (if not running)
ollama serve

# Pull the default model
ollama pull qwen2.5-coder:7b

# Start the model
ollama run qwen2.5-coder:7b
```

Note: Keep the Ollama model running in a separate terminal window while using the code assistant.

## Usage

### Interactive Mode
```bash
# Start the interactive session
python bespoke_code.py

# To exit: type 'exit' or 'quit'
# To clear history: type 'clear'
```

### Model Options

The following Ollama models are supported:
- qwen2.5-coder:7b (default, recommended)
- qwen2.5-coder:14b
- qwen2.5-coder:32b
- codellama:7b
- codellama:13b
- codellama:34b
- mixtral:8x7b
- deepseek-r1:7b
- deepseek-r1:14b
- deepseek-r1:32b

To use a different model, set the `OLLAMA_MODEL` environment variable:
```bash
# Windows
set OLLAMA_MODEL=codellama:7b
python bespoke_code.py

# Linux/Mac
OLLAMA_MODEL=codellama:7b python bespoke_code.py
```

## Docker Support

While Docker support is included, it's recommended to run the application directly for the best interactive experience. Docker usage may require additional configuration for proper terminal interaction.

### Basic Docker Usage
```bash
# Build the image
docker build -t bespoke-code .

# Run with interactive terminal
docker run -it --rm \
  -v ./workspace:/app/workspace \
  bespoke-code
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| OLLAMA_MODEL | qwen2.5-coder:7b | Model to use with Ollama |
| TEMPERATURE | 0.7 | Model temperature (0.0-1.0) |
| LOG_LEVEL | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |

## License

MIT License - see LICENSE file for details. 