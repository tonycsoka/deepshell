import os

# Executable name and symlink directory
EXECUTABLE_NAME = "deepshell" 

def create_symlink():
    """Create symlink for deepshell in ~/.local/bin"""
    bin_dir = os.path.expanduser("~/.local/bin")  # Or any directory in PATH
    symlink_path = os.path.join(bin_dir, EXECUTABLE_NAME)

    # Ensure the target directory exists
    if not os.path.exists(bin_dir):
        os.makedirs(bin_dir)

    # Create symlink
    if not os.path.exists(symlink_path):
        os.symlink(os.path.abspath(EXECUTABLE_NAME), symlink_path)
        print(f"Symlink created at {symlink_path}")
    else:
        print(f"Symlink already exists at {symlink_path}")

def remove_symlink():
    """Remove the symlink for deepshell from ~/.local/bin"""
    bin_dir = os.path.expanduser("~/.local/bin")  # Or any directory in PATH
    symlink_path = os.path.join(bin_dir, EXECUTABLE_NAME)

    # Remove symlink if it exists
    if os.path.exists(symlink_path):
        os.remove(symlink_path)
        print(f"Symlink removed from {symlink_path}")
    else:
        print(f"No symlink found at {symlink_path}")
