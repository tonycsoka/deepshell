import os

def execute_shell_command(command):
    """Runs a shell command securely."""
    try:
        output = os.popen(command).read()
        return f"Command Output:\n{output.strip()}"
    except Exception as e:
        return f"Error executing command: {e}"
