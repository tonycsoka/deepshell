import os
import re
import sys
from config.settings import DEFAULT_CONFIG, CODE_CONFIG, SHELL_CONFIG
from utils.file_utils import read_file, read_folder

class CommandProcessor:
    """Handles user input, command processing, mode switching, and file handling."""

    MODE_COMMANDS = {
        "generate code": CODE_CONFIG,
        "generate script": CODE_CONFIG,
        "generate bash script": CODE_CONFIG,
        "generate shell command": SHELL_CONFIG,
        "default mode": DEFAULT_CONFIG,
        "default config": DEFAULT_CONFIG,
    }

    ACTION_WORDS = {"find", "open", "read"}

    def __init__(self, default_config):
        self.default_config = default_config
        self.config = default_config

    def handle_command(self, user_input):
        """Processes commands and updates config or file content accordingly."""
        if user_input:
            new_config = self.detect_mode_switch(user_input)
            if new_config:
                if new_config == DEFAULT_CONFIG:
                    return ""
                return user_input

        return user_input

    def detect_mode_switch(self, user_input):
        """Detects mode switching commands and updates config."""
        for keyword, config in self.MODE_COMMANDS.items():
            if keyword in user_input:
                config_name = keyword
                print(f"Switching to {config_name} mode")
                #print(config)
                self.config = config
                return config
        return None

    def process_file_or_folder(self, user_input):
        """Handles file or folder operations (find, read, open)."""
        file_content = None  

        parts = re.split(r"\band\b", user_input, maxsplit=1)
        main_command = parts[0].strip()
        additional_action = parts[1].strip() if len(parts) > 1 else None

        tokens = main_command.split()
        if not tokens:
            return None

        action = next((word for word in tokens if word in self.ACTION_WORDS), None)
        if not action:
            return None

        target_index = tokens.index(action) + 1
        target = " ".join(tokens[target_index:]) if target_index < len(tokens) else ""

        if target == "this folder":
            folder_path = os.getcwd()
            file_content = read_folder(folder_path)
        elif target:
            file_content = read_file(target)

        if file_content and additional_action:
            return f"{additional_action}\n\nFile Content:\n{file_content.strip()}"

        return file_content  

    def format_input(self, user_input, file_content):
        """Prepares user input by combining prompt and file content."""
        if file_content:
            formatted_content = f"File Content:\n{file_content.strip()}"
            if user_input:
                return f"Prompt:\n{user_input}\n\n{formatted_content}"
            return formatted_content  
        return user_input

    def get_user_input(self):
        """Handles interactive user input, mode switching, and file handling."""
        if sys.stdin.isatty():  # Interactive mode
            try:
                user_input = input("You: ").strip()
                if user_input.lower() == "exit":
                    return "exit"
                return user_input
            except KeyboardInterrupt:
                print("\nExiting chat.")
                return "exit"

        else:  # Piped input mode, seems like it can't switch between pipe and user input
            try:
                user_input = sys.stdin.read().strip()  # Read the entire input
                return user_input if user_input else "exit"  # Exit if empty
            except EOFError:
                print("OOF")
                return "exit"
     
