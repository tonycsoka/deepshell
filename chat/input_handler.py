import os
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
    Handles special commands such as reading a file or folder.
    Also processes the "AND" part after reading the file or folder.
    """
    user_input = user_input.strip()

    # Check if "AND" exists in the input
    if "and" in user_input.lower():
        # Split the input into the main action (file/folder reading) and the additional command
        main_input, additional_action = user_input.split("and", 1)
        main_input = main_input.strip()  # Trim any extra spaces
        additional_action = additional_action.strip()  # Get the part after "and"

        # Handle the main input (file/folder reading)
        file_content = None
        if main_input.lower() == "open this folder":
            folder_path = os.getcwd()  # Get the current working directory
            file_content = read_folder(folder_path)  # Read the folder contents
        elif main_input.lower().startswith("open "):
            file_path = main_input[5:].strip()
            file_content = read_file(file_path)  # Read the file

        # After reading the file/folder, pass the additional action to process_input
        if file_content:
            return process_input(additional_action, file_content)  # Return the processed result of additional action

    # If "and" is not found, handle file/folder reading directly
    if user_input.lower() == "open this folder":
        folder_path = os.getcwd()  # Get the current working directory
        return read_folder(folder_path)  # Read the folder contents

    elif user_input.lower().startswith("open "):
        file_path = user_input[5:].strip()
        return read_file(file_path)  # Read the file

    return None  # Return None for normal input

