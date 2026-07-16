# maki

A coding agent. As simple as it gets. Runs tools in your current directory. Only works with local AI.


## Prerequisites

- **Python 3** - Python 3.8 or higher
- **Local AI model** - An OpenAI-compatible API endpoint (default: `http://localhost:8080/v1`)


## Installation

1. **Quick start:**

   ```bash
   pip install openai
   export MAKI_BASE_URL=http://localhost:8080/v1
   export MAKI_MODEL=your-model-name
   python maki.py
   ```

2. **Or install as a package:**

   ```bash
   pip install .
   ```

   This installs `maki` as a package, allowing you to use it in your project directories.


3. **Set up environment variables:**

   Create a `~/.env` file with the following:

   ```bash
   # LLM API endpoint
   MAKI_BASE_URL=http://localhost:8080/v1

   # Model name
   MAKI_MODEL=your-model-name
   ```

   Alternatively, set these as environment variables directly:
   ```bash
   export MAKI_BASE_URL=http://localhost:8080/v1
   export MAKI_MODEL=your-model-name
   ```

3. **Run the agent:**

   ```bash
   maki
   ```

## Features

- **Interactive Terminal Chat** - Conversational coding assistant with streaming responses
- **File Operations**
  - `read_file` - Read files with pagination support
  - `write_file` - Write/overwrite files
  - `edit_file` - Replace exact occurrences of text in files
- **Directory Navigation** - List directory contents
- **Shell Execution** - Run bash commands with output capture
- **Session Management**
  - Auto-save conversations to `~/.maki/sessions/`
  - Resume previous sessions with `/session <id>`
  - List sessions with `/sessions`
- **Tool Calling** - Native support for function calling with LLMs
- **Token Tracking** - Displays prompt and generation token counts
- **YOLO Mode** - Disable "hitl" (human-in-the-loop) confirmation prompts for slop results

## Commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/yolo` | Enable YOLO mode (no confirmation prompts) |
| `/yoloff` | Disable YOLO mode (hitl enabled) |
| `/sessions` | List all saved sessions |
| `/session <id>` | Resume a specific session |
| `/exit` | Exit the session |

## Configuration

By default, sessions are stored in `~/.maki/sessions/`. You can customize this with the `MAKI_HOME` environment variable:

```bash
export MAKI_HOME=~/my-maki
```

## Built with

maki was developed using the following AI tools and models:

- [**minion**](https://github.com/Sentdex/minion)  (a better coding agent)
- **Qwen3-Coder-30B-A3B-Instruct-Q3_K_M.gguf**
- **Qwen3.5-9B-Q6_K.gguf**

## License

MIT License. See [`LICENSE`](LICENSE).
