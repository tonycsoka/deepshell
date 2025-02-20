import os
import re
from utils.file_utils import FileUtils
from utils.shell_utils import CommandExecutor

class CommandProcessor:
    """Handles user input"""
    
    def __init__(self, ui=None):
        self.ui = ui
        self.file_utils = FileUtils(ui)
        self.executor = CommandExecutor(ui)
    
    async def handle_command(self, user_input):
        """Processes commands, handles file/folder operations, and updates config."""
        bypass_flag = False
        
        if user_input.startswith("!"):
            user_input = user_input[1:] 
            bypass_flag = True
            return user_input, bypass_flag

        if user_input:
            target, additional_action = await self.detect_action(user_input)
            if target:
                file_content = await self.file_utils.process_file_or_folder(target)
                if file_content:
                    if self.ui:
                        await self.ui.fancy_print("\n[cyan]System:[/cyan] File processing complete. \nSubmiting the input to the chatbot")

                    return self.format_input(user_input, file_content, additional_action)
            else:
                if additional_action == "cancel":
                    return None

        return user_input

    async def detect_action(self, user_input):
        """Detects action, validates/finds target, and processes file/folder."""
    
        # Extract action and target
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

        # Convert "this folder" to current working directory
        if target.lower() == "this folder":
            target = os.getcwd()

        # Validate or find target
        target = target.strip()
        if not os.path.exists(target):
            choice = await self.file_utils.prompt_search(target)
            if not choice and self.ui:
                await self.ui.fancy_print("\n[yellow]Nothing found[/yellow]")
                return None, None
            target = choice

        # Ensure default additional action if none is specified
        if target and not additional_action:
            additional_action = "Analyze this content"
        
        return target, additional_action

    def format_input(self, user_input, file_content, additional_action=None):
        """Prepares user input by combining prompt and file content."""
        formatted_content = f"Content:\n{file_content}"
        if additional_action:
            user_input = additional_action
        if user_input:
            return f"\n{formatted_content}\nUser Prompt:\n{user_input}\n"
        return formatted_content
