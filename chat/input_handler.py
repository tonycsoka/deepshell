import os

from config.settings import DEFAULT_CONFIG, CODE_CONFIG, SHELL_CONFIG
from utils.file_utils import read_file, read_folder


def process_input(user_input, file_content):
    """
    Prepares user input by combining prompt and file content.
    Detects "read this folder" or "read <filename>" and processes it immediately.
    """
    # If there's file content, format it properly
    if file_content:
        formatted_content = f"File Content:\n{file_content.strip()}"
        if user_input:
            return f"Prompt:\n{user_input}\n\n{formatted_content}"
        return formatted_content  # If only file/piped input exists

    return user_input

def commands_handler(user_input):
    """
    Handles commands for finding, opening, and reading files or folders.
    Supports "this folder" to refer to the current directory.
    Splits commands using 'and' for additional processing.
    """
    user_input = user_input.strip().lower()
    config_name = DEFAULT_CONFIG

    if any(keyword in user_input for keyword in ["generate code", "generate script", "generate bash script"]):
        print("switching to coding mode")
        return user_input, CODE_CONFIG

    elif "shell command" in user_input:
        print("switching to shell generator mode")
        return user_input, SHELL_CONFIG

    elif any(keyword in user_input for keyword in ["default mode", "default config"]):
        print("switching to default mode")
        return None, DEFAULT_CONFIG

        
    # Check if "and" exists to split the command into two parts
    main_input, additional_action = (user_input.split("and", 1) + [""])[:2]
    main_input, additional_action = main_input.strip(), additional_action.strip()

    # Identify action keywords (find, open, read)
    action_words = ["find", "open", "read"]
    tokens = main_input.split()

    if not tokens:
        return None, None # No valid command found

    # Check for action word in the input
    action = next((word for word in tokens if word in action_words), None)
    if not action:
        return None, None
    # No recognized command found

    # Determine the target (file/folder name)
    target_index = tokens.index(action) + 1
    target = " ".join(tokens[target_index:]) if target_index < len(tokens) else ""

    # If the user specified "this folder", use the current directory
    if target == "this folder":
        folder_path = os.getcwd()
        file_content = read_folder(folder_path)
    else:
        file_content = read_file(target) if target else None  # Try reading a file

    # If file/folder content is found and there's an additional action, process it
    if file_content and additional_action:
        return process_input(additional_action, file_content), None

    return file_content, None
