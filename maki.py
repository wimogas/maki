import os
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


SYSTEM = """You are a terminal coding agent."""


def open_stream(msg):
    """Open streaming connection to the single LLM endpoint.
    Returns (stream_iterator, usage_dict) for consumption by model_turn.
    """
    global client, MODEL
    
    stream = client.chat.completions.create(
        model=MODEL,
        messages=msg,
        stream=True,
        temperature=0.7
    )
    
    return stream, {"total_cost": 0}


def model_turn(system_prompt):
    """Core turn execution with streaming.
    Sends the system prompt to the model and streams back the response.
    """
    global messages
    
    messages = [{"role": "system", "content": system_prompt},
                {"role": "user", "content": "Who are you?"}]

    stream, usage = open_stream(messages)
    
    response_text = ""
    for chunk in stream:
        if chunk.choices:
            delta = chunk.choices[0].delta
            if delta.content:
                response_text += delta.content
                print(delta.content, end="", flush=True)
    
    print()  # Newline after streaming
    
    messages.append({"role": "assistant", "content": response_text})
    
    return response_text


# Load the environment file at startup
_load_env_file()

# Initialize the source
source = _init_source()

# Display banner
_banner()

# Test 1 assistant response
model_turn(SYSTEM)