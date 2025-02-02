# Bespoke Code Assistant

A Python-based interactive coding assistant powered by Qwen 2.5 Coder model via Ollama, with built-in file system operations support and color-coded output.

## Features

- 🤖 Interactive AI coding assistant
- 🎨 Color-coded output for better readability
  - Blue: AI responses
  - Cyan: Tool operations
  - Red: Errors
  - Yellow: System messages
  - Green: User input
- 📝 File system operations with safety checks
- 💬 Context-aware responses with history management
- 🔄 Streaming responses for real-time feedback
- 📊 Token management for optimal context usage

## Prerequisites

- Python 3.x
- Ollama installed and running locally

## Installation & Development

### Option 1: Local Development (Recommended for Development)

1. Clone the repository:
```bash
git clone [your-repo-url]
cd bespoke-code
```

2. Create and activate a virtual environment:
```bash
# Create virtual environment
python -m venv venv

# Activate on Windows
venv\Scripts\activate

# Activate on Unix or MacOS
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up Ollama:
```bash
# Start Ollama service (if not running)
ollama serve

# In another terminal, pull the required model
ollama pull qwen2.5-coder:7b
```

5. Run the application:
```bash
python bespoke-code.py
```

### Option 2: Docker Deployment (Recommended for Production)

#### Prerequisites
1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/Mac) or Docker Engine (Linux)
2. Make sure Docker is running on your system

#### Quick Start
1. Open a terminal in the project directory
2. Build and start the services:
```bash
docker-compose up -d
```
3. Watch the initialization process:
```bash
docker-compose logs -f
```

The first launch will:
- Download required Docker images
- Pull the Qwen 2.5 Coder model (~5-10 minutes)
- Start the interactive assistant

#### Accessing the Application
Once everything is running:
```bash
# Attach to the running application
docker-compose exec bespoke-code python bespoke-code.py

# Or start a new instance
docker-compose run --rm bespoke-code python bespoke-code.py
```

#### Useful Docker Commands

**Check Status:**
```bash
# View running services
docker-compose ps

# Check initialization progress
docker-compose logs -f ollama-init

# Check application logs
docker-compose logs -f bespoke-code
```

**Managing Services:**
```bash
# Stop all services
docker-compose down

# Restart services
docker-compose restart

# Rebuild after changes
docker-compose up -d --build

# Complete reset (removes model)
docker-compose down -v
```

**Troubleshooting:**
- If the model download seems stuck:
  ```bash
  docker-compose logs -f ollama-init
  ```
- If the application isn't responding:
  ```bash
  docker-compose restart bespoke-code
  ```
- For a fresh start:
  ```bash
  docker-compose down -v
  docker-compose up -d
  ```

## Project Structure

```
.
├── bespoke-code.py    # Main application file
├── config.py        # Configuration settings
├── prompts.py       # System prompts and instructions
├── utils.py         # Utility functions and colors
├── tools.py         # File system operations
├── requirements.txt # Project dependencies
├── Dockerfile      # Container definition
├── docker-compose.yml # Container orchestration
├── .gitignore      # Git ignore patterns
└── LICENSE.md      # MIT License
```

## Usage

### Interactive Mode

```bash
python bespoke-code.py -i
```

or simply:

```bash
python bespoke-code.py
```

### Single Prompt Mode

```bash
python bespoke-code.py --prompt "Your prompt here"
```

### Additional Options

- `--file` or `-f`: Provide context files (can be used multiple times)
- `--temperature` or `-t`: Set generation temperature (default: 0.7)
- `--interactive` or `-i`: Force interactive mode even with prompt
- `--prompt` or `-p`: Single prompt to send to the model

Example with context file:
```bash
python bespoke-code.py -f context.py --prompt "Explain this code"
```

## Available Tools

### File Operations
- `write_file(filename, content)`: Write or append to files
- `read_file(filename)`: Read file contents
- `list_files(path=".")`: List files in directory
- `delete_file(filename)`: Delete a file

### Directory Operations
- `create_directory(dirname)`: Create new directories

### JSON Operations
- `save_json(filename, data)`: Save dictionary as JSON
- `load_json(filename)`: Load JSON file as dictionary

## Technical Details

- Uses Ollama API at `http://localhost:11434/api/generate`
- Maximum context window: 32,768 tokens
  - System reserved: 4,000 tokens
  - Query reserved: 2,000 tokens
  - History available: ~26,000 tokens
- Workspace management for safe file operations
- Streaming response support for real-time output
- Comprehensive logging with configurable levels

## Interactive Commands

- Type `exit` or `quit` to end the session
- Type `clear` to clear conversation history
- Use Ctrl+C to cancel current generation
- Empty input is ignored

## Error Handling

- Graceful handling of API errors
- Safe file operations with verification
- Conversation history management to prevent context overflow
- Proper cleanup on exit

## Workspace Management

All file operations are performed in a dedicated workspace directory (`./workspace`) for safety. The workspace is automatically created if it doesn't exist.

## Security Notes

- All file operations are contained within the workspace directory
- API calls are made only to local Ollama instance
- No sensitive data is transmitted externally
- Tool operations are verified before confirming success

## Contributing

Feel free to open issues or submit pull requests for improvements. Please ensure you follow the existing code structure and add appropriate tests for new features.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details. 