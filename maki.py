import json
import os
import subprocess
import secrets
from openai import OpenAI


def _load_env_file():
    """Read `~/.env` or `MAKI_ENV_FILE`, populate `os.environ` with variables not already set"""

    env_file = os.environ.get('MAKI_ENV_FILE', os.path.expanduser('~/.env'))

    if not os.path.exists(env_file):
        return

    with open(env_file, 'r') as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()

        if not line or line.startswith('#'):
            continue

        if line.startswith('export '):
            line = line[7:]

        if line.startswith('"') and line.endswith('"'):
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()[1:-1]  # Remove the quotes
        elif line.find('=') != -1:
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
        else:
            key = line
            value = ''

        if key not in os.environ:
            os.environ[key] = value


SESSION_HOME = os.path.expanduser(
    os.environ.get("MAKI_HOME", "~/.maki")
)


client = None
MODEL = None


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
    global client, MODEL

    base_url = os.environ.get("MAKI_BASE_URL", "http://localhost:8080/v1")
    model = os.environ.get("MAKI_MODEL")

    src = Source("local", base_url, model)

    client = src.client
    MODEL = src.get_model()


DIM, CYAN, GREEN, YELLOW, RED, MAGENTA, BOLD, RESET = (
    "\033[2m", "\033[36m", "\033[32m", "\033[33m", "\033[31m", "\033[35m",
    "\033[1m", "\033[0m",
)


def _banner():
    """Display startup banner with model name."""
    print(f"{BOLD}maki{RESET} - {CYAN}{MODEL}{RESET}")


def list_dir(path="."):
    """Return sorted directory listing."""
    try:
        entries = sorted(os.listdir(path))
        return "\n".join(entries)
    except Exception as e:
        return f"Error: {str(e)}"


def read_file(path, offset=1, limit=400):
    """Read a file's contents with pagination."""
    if not os.path.exists(path):
        return f"Error: file not found: {path}"
    
    try:
        with open(path, 'r') as f:
            lines = f.readlines()

        start_idx = offset - 1
        end_idx = start_idx + limit

        if start_idx >= len(lines):
            return f"Error: offset {offset} exceeds file length ({len(lines)} lines)"

        selected_lines = lines[start_idx:end_idx]

        output = []
        for i, line in enumerate(selected_lines, start=start_idx + 1):
            num_str = f"{i:>6}"
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
    response = input(YELLOW + message + RESET).strip().lower()
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

    print()
    print(f"{CYAN}(calling tool: {name}){RESET}")
    arg_preview = json.dumps(args)
    print(f"{DIM}{arg_preview}{RESET}")
    print()

    if name in ('edit_file', 'write_file', 'run_bash'):
        message = f"Run {name} with: {arg_preview}? (y/n) "
        if not confirm(message):
            print(f"{YELLOW}Cancelled: {name} was not executed.{RESET}")
            return "Cancelled by user"

    try:
        result = fn(**args)
    except Exception as e:
        result = f"ERROR: {type(e).__name__}: {e}"

    print(result if len(result) < 800 else result[:800] + f"\n... [{len(result) - 800} more chars]")
    return result


def open_stream(msg, tools=TOOLS):
    """Open streaming connection to the single LLM endpoint."""
    global client, MODEL
    stream = client.chat.completions.create(
        model=MODEL,
        messages=msg,
        tools=tools,
        stream=True,
        temperature=0.7
    )
    return stream


TURN_DONE = "done"
TURN_TOOL = "tool"


def model_turn(messages):
    """Core turn execution with streaming."""
    content = []
    tcs = {}
    mode = None
    reasoning_chars = 0
    timings = None

    stream = open_stream(messages)

    for chunk in stream:
        if chunk.choices:
            d = chunk.choices[0].delta
            extra = getattr(chunk, "model_extra", None) or {}

            if "timings" in extra:
                timings = extra["timings"]

            rc = getattr(d, "reasoning_content", None) or (d.model_extra or {}).get("reasoning_content")
            if rc:
                if mode != 'think':
                    print(f"{DIM}(thinking)")
                    print()
                    mode = 'think'
                print(f"{DIM}{rc}{RESET}", end="", flush=True)
                if not content and not tcs:
                    reasoning_chars += len(rc)
                if not content and not tcs and reasoning_chars >= 36000:
                    print()
                    print(f"{YELLOW}(reasoning-only limit reached){RESET}")
                    close = getattr(stream, "close", None)
                    if close:
                        close()
                    break

            if d.content:
                if mode == 'think':
                    print()
                mode = 'say'
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
        stats = f"context: {prompt_n}, tokens: {gen_n}\n"
        print("\n────────────────────────────")
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
            print(f"{RED}Error parsing args{RESET}")

        messages.append({"role": "assistant", "content": text or None, "tool_calls": [
            {"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": c["args"]}}
            for c in ordered]})

        for idx, (c, args) in enumerate(zip(ordered, parsed_args)):
            result = run_tool(c["name"], args)
            messages.append({"role": "tool", "tool_call_id": c["id"], "content": result})
        return TURN_TOOL

    if content:
        messages.append({"role": "assistant", "content": text or None, "tool_calls": []})

    return TURN_DONE


def _run_model_turn_loop(messages):
    """Run model_turn in a loop that breaks after 10 iterations or if status is TURN_DONE."""
    for i in range(10):
        status = model_turn(messages)
        if status == TURN_DONE:
            break


def save_session(messages, session_id):
    """Save the current session messages as a JSON file in the sessions directory."""

    session_dir = os.path.join(SESSION_HOME, "sessions")
    os.makedirs(session_dir, exist_ok=True)
    filename = f"{session_id}.json"
    filepath = os.path.join(session_dir, filename)

    with open(filepath, "w") as f:
        json.dump(messages, f, indent=2)

    print(f"{GREEN}(session saved){RESET}")


# Load the environment file at startup
_load_env_file()

# Initialize the source
_init_source()


def main():

    _banner()
    messages = [{"role": "system", "content": SYSTEM}]
    session_id = f"{secrets.token_hex(3)}"

    while True:
        print(f"{DIM}/exit (end session) {RESET}")
        user = input()

        if user == "/exit":
            save_session(messages, session_id)
            break

        print()
        messages.append({"role": "user", "content": user})
        _run_model_turn_loop(messages)

        save_session(messages, session_id)


if __name__ == "__main__":
    main()