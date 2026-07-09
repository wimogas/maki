import json
import os
import subprocess
from openai import OpenAI


def _load_env_file():
    """Read `~/.env` or `MAKI_ENV_FILE`, populate `os.environ` with variables not already set
    Handle comments, blank lines, `export` prefixes, quoted values"""
    # First try to get the environment file from the MAKI_ENV_FILE environment variable
    env_file = os.environ.get('MAKI_ENV_FILE', os.path.expanduser('~/.env'))

    # If the file doesn't exist, we can't do anything
    if not os.path.exists(env_file):
        return

    # Read the file
    with open(env_file, 'r') as f:
        lines = f.readlines()

    # Process each line
    for line in lines:
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith('#'):
            continue

        # Handle `export` prefix
        if line.startswith('export '):
            line = line[7:]  # Remove 'export '

        # Handle quoted values
        if line.startswith('"') and line.endswith('"'):
            # Simple case: quoted string
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()[1:-1]  # Remove the quotes
        elif line.find('=') != -1:
            # Unquoted value
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
        else:
            # Just a key with no value (treat as empty value)
            key = line
            value = ''

        # Only set the environment variable if it's not already set
        if key not in os.environ:
            os.environ[key] = value


class Source:
    def __init__(self, name, base_url, model=None):
        self.name = name
        self.base_url = base_url
        self.api_key = "noop"
        self.model = model
        self.client = OpenAI(base_url=base_url, api_key=self.api_key)


    def get_model(self):
        return self.model


def _init_source():
    """Build one Source (name, base_url, api_key, model, OpenAI client) from env vars."""
    global client, MODEL, ACTIVE
    
    # Build source from env vars
    base_url = os.environ.get("MAKI_BASE_URL", "http://localhost:8080/v1")
    model = os.environ.get("MAKI_MODEL")
    
    # Create the source
    src = Source("local", base_url, model)
    
    # Set globals
    client = src.client
    MODEL = src.get_model()
    ACTIVE = src
    
    return src


def _banner():
    """Display startup banner with model name."""
    print(f"maki - {MODEL}")


def list_dir(path="."):
    """Return sorted directory listing."""
    try:
        entries = sorted(os.listdir(path))
        return "\n".join(entries)
    except Exception as e:
        return f"Error: {str(e)}"


def read_file(path, offset=1, limit=400):
    """Read a file's contents with pagination.
    Returns lines numbered (1-based, like `cat -n`): a right-aligned number, a tab, then the line.
    Large files return only a window — pass offset and limit to page through.
    """
    if not os.path.exists(path):
        return f"Error: file not found: {path}"
    
    try:
        with open(path, 'r') as f:
            lines = f.readlines()
        
        # Calculate start index (offset is 1-based)
        start_idx = offset - 1
        end_idx = start_idx + limit
        
        # Handle edge cases
        if start_idx >= len(lines):
            return f"Error: offset {offset} exceeds file length ({len(lines)} lines)"
        
        # Slice the lines
        selected_lines = lines[start_idx:end_idx]
        
        # Format output with line numbers
        output = []
        for i, line in enumerate(selected_lines, start=start_idx + 1):
            # Right-align number, tab, then content
            num_str = f"{i:>6}"  # 6-character width for alignment
            output.append(f"{num_str}\t{line.rstrip('\n')}")
        
        return "\n".join(output)
    
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"


def write_file(path, content):
    with open(path, "w") as f:
        f.write(content)
    return f"{content}"


def edit_file(path, old, new):
    """Replace one exact occurrence of `old` with `new` in a file."""
    if not os.path.exists(path):
        return f"Error: file not found: {path}"
    
    try:
        with open(path, "r") as f:
            content = f.read()
        
        if old not in content:
            return f"Error: could not find {old!r} in file"
        
        new_content = content.replace(old, new, 1)  # Replace only the first occurrence
        
        with open(path, "w") as f:
            f.write(new_content)
        
        return f"Success: replaced {old!r} with {new!r} in {path}"
    
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"


def run_bash(command):
    """Run a shell command and return output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120
        )
        output = result.stdout
        error = result.stderr
        return_code = result.returncode
        
        if error:
            output += f"\n\nstderr: {error}"
        
        if return_code != 0:
            return f"Command failed with exit code {return_code}:\n{output}"
        else:
            return output
    
    except subprocess.TimeoutExpired:
        return "Command timed out after 120 seconds"
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"


def confirm(message="Confirm assistant action? (y/n) "):
    """Prompt the user for a y/n confirmation."""
    response = input(message).strip().lower()
    if response in ('y', 'yes'):
        return True
    elif response in ('n', 'no'):
        return False
    else:
        print(f"Invalid input '{response}'. Please enter 'y' or 'n'.")
        return confirm(message)


SYSTEM = """You are a terminal coding agent helping the user in the current directory. Use the following tools when necessary:

- list_dir: List a directory
- read_file: Read a file's contents with pagination. Returns lines numbered (1-based, like `cat -n`): a right-aligned number, a tab, then the line. Large files return only a window — pass offset and limit to page through.
- write_file: Write (overwrite) a file.
- edit_file: Replace one exact occurrence of `old` with `new` in a file.
- run_bash: Run a shell command and return output.

"""


DISPATCH = {
    "read_file": read_file, "write_file": write_file, "edit_file": edit_file, "list_dir": list_dir, "run_bash": run_bash
}


TOOLS = [
    {"type": "function", "function": {"name": "read_file", "description": "Read a file's contents with pagination. Returns lines numbered (1-based, like `cat -n`): a right-aligned number, a tab, then the line. Large files return only a window — pass offset and limit to page through.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "offset": {"type": "integer"}, "limit": {"type": "integer"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "write_file", "description": "Write (overwrite) a file","parameters": {"type": "object", "properties": {"path": {"type": "string"},"content": {"type": "string"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "edit_file", "description": "Replace one exact occurrence of `old` with `new` in a file.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}}, "required": ["path", "old", "new"]}}},
    {"type": "function", "function": {"name": "list_dir", "description": "List a directory",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "run_bash", "description": "Run a shell command",
        "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}}},
]


def run_tool(name, args):
    fn = DISPATCH.get(name)

    if not fn:
        return f"ERROR: unknown tool {name}"
    arg_preview = json.dumps(args)
    if len(arg_preview) > 120:
        arg_preview = arg_preview[:117] + "..."
    print(f"{arg_preview}")

    # Confirm before running edit, write, or bash commands
    if name in ('edit_file', 'write_file', 'run_bash'):
        message = f"Run {name} with: {arg_preview} (y/n) "
        if not confirm(message):
            print(f"Cancelled: {name} was not executed.")
            return "Cancelled by user"

    try:
        result = fn(**args)
    except Exception as e:
        result = f"ERROR: {type(e).__name__}: {e}"

    print(result)

    return result

def open_stream(msg, tools=TOOLS):
    """Open streaming connection to the single LLM endpoint.
    Returns (stream_iterator, usage_dict) for consumption by model_turn.
    """
    global client, MODEL

    stream = client.chat.completions.create(
        model=MODEL,
        messages=msg,
        tools=tools,
        stream=True,
        temperature=0.7
    )
    
    return stream, {"total_cost": 0}


def model_turn(system_prompt):
    """Core turn execution with streaming.
    Sends the system prompt to the model and streams back the response.
    """
    global messages

    content = []
    tcs = {}
    reasoning_chars = 0
    timings = None

    messages = [{"role": "system", "content": system_prompt},
                {"role": "user", "content": "Add a new file called sample.py that prints Hello World"}]

    stream, usage = open_stream(messages)

    for chunk in stream:
        if chunk.choices:
            d = chunk.choices[0].delta
            extra = getattr(chunk, "model_extra", None) or {}
            if "timings" in extra:
                timings = extra["timings"]
            rc = getattr(d, "reasoning_content", None) or (d.model_extra or {}).get("reasoning_content")
            if rc:
                print(f"{rc}", end="", flush=True)
                if not content and not tcs:
                    reasoning_chars += len(rc)
                if not content and not tcs and reasoning_chars >= 36000:
                    print()
                    print(f"reasoning only limit reached")
                    close = getattr(stream, "close", None)
                    if close:
                        close()
                    break
            if d.content:
                print(d.content, end="", flush=True)
                content.append(d.content)
            for tc in (d.tool_calls or []):
                s = tcs.setdefault(tc.index, {"id": "", "name": "", "args": ""})
                if tc.id:
                    s["id"] = tc.id
                if tc.function and tc.function.name:
                    s["name"] = tc.function.name
                if tc.function and tc.function.arguments:
                    s["args"] += tc.function.arguments

    text = "".join(content)

    if timings and timings.get("predicted_n"):
        prompt_n = timings.get("prompt_n", 0)
        gen_n = timings["predicted_n"]
        stats = f"context: {prompt_n}, tokens: {gen_n}"
        print(stats)

    if tcs:
        ordered = [tcs[i] for i in sorted(tcs)]
        parsed_args = []
        parse_error = None

        for c in ordered:
            try:
                parsed_args.append(json.loads(c["args"] or "{}"))
            except json.JSONDecodeError as e:
                parse_error = (c, e)
                break
        if parse_error is not None:
            print("Error parsing args")

        messages.append({"role": "assistant", "content": text or None, "tool_calls": [
            {"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": c["args"]}}
            for c in ordered]})

        for idx, (c, args) in enumerate(zip(ordered, parsed_args)):
            result = run_tool(c["name"], args)
            messages.append({"role": "tool", "tool_call_id": c["id"], "content": result})

    if content:
        messages.append({"role": "assistant", "content": text or None, "tool_calls": []})

    print()
    print("LOG ------------------------------\n", messages, "\n----------------------------------")


# Load the environment file at startup
_load_env_file()

# Initialize the source
source = _init_source()

# Display banner
_banner()

# Test 1 assistant response
model_turn(SYSTEM)