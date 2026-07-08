import os


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


# Load the environment file at startup
_load_env_file()
