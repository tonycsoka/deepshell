import os
import re
from utils.file_utils import FileUtils
from chat.user_input import UIManager

class CommandProcessor:
    """Handles user input"""
    
    def __init__(self, ollama_client):
        self.ollama_client = ollama_client
        self.default_config = ollama_client.config
        self.config = ollama_client.config
        self.prompt_search = UIManager.prompt_search
    
    async def handle_command(self, user_input):
        """Processes commands, handles file/folder operations, and updates config."""
        if user_input:
            target, additional_action = await self.detect_action(user_input)
            if target:
                file_content = await self.process_file_or_folder(target)
                if file_content:
                    return self.format_input(user_input, file_content, additional_action)
            else:
                if additional_action == "cancel":
                    return None

        return user_input

    async def detect_action(self, user_input):
        """Detects action and extracts target and additional action."""
        parts = re.split(r"\band\b", user_input, maxsplit=1)
        main_command = parts[0].strip()
        additional_action = parts[1].strip() if len(parts) > 1 else None
        actions = {"find", "open", "read"}
        tokens = main_command.split()
        if not tokens:
            return None, None

        action = next((word for word in tokens if word in actions), None)
        if not action:
            return None, None

        target_index = tokens.index(action) + 1
        target = " ".join(tokens[target_index:]) if target_index < len(tokens) else ""

        if target == "this folder":
            target = os.getcwd()
        elif not os.path.exists(target):
            target = await self._run_search(target)
            if not target:
                return None, "cancel"

        return target, additional_action

    async def process_file_or_folder(self, target):
        """Handles file or folder operations."""
        file_utils = FileUtils()
        if os.path.exists(target):
            if os.path.isfile(target):
                return await file_utils.read_file(target)
            elif os.path.isdir(target):
                return await file_utils.read_folder(target)
        else:
            return await self._run_search(target)
        return None

    async def _run_search(self, target):
        """Run the search without using asyncio.run()."""
        return await self.prompt_search(target)

    def format_input(self, user_input, file_content, additional_action=None):
        """Prepares user input by combining prompt and file content."""
        formatted_content = f"Content:\n{file_content.strip()}"
        if additional_action:
            user_input = additional_action
        if user_input:
            return f"Prompt:\n{user_input}\n\n{formatted_content}"
        return formatted_content
