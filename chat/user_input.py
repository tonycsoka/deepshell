import sys
import asyncio
from prompt_toolkit import PromptSession
from prompt_toolkit.shortcuts import prompt, radiolist_dialog
from prompt_toolkit.completion import WordCompleter
from chat.streamer import rich_print
from utils.file_utils import FileUtils

class UIManager:
    session = PromptSession()

    @staticmethod
    async def get_user_input(prompt_text="You: ", is_password=False):
        """Handles interactive user input asynchronously."""
        if sys.stdin.isatty():
            try:
                return await UIManager.session.prompt_async(prompt_text, is_password=is_password)
            except KeyboardInterrupt:
                return "exit"
        else:
            return sys.stdin.read().strip() or "exit"

    @staticmethod
    async def confirm_execute_command(command):
        """Prompts user to execute, modify, or cancel a command."""
        choices = ["Execute", "Modify", "Cancel"]
        completer = WordCompleter(choices, ignore_case=True)

        await rich_print(f"Command to be executed: {command}")

        while True:
            choice = await asyncio.to_thread(prompt, "Choose action (Execute / Modify / Cancel): ", completer=completer)
            choice = choice.strip().lower()

            if choice in ("execute", "e"):
                return command
            elif choice in ("modify", "m"):
                command = await asyncio.to_thread(prompt, "Modify command: ", default=command)
                return command.strip()
            elif choice in ("cancel", "c"):
                await rich_print("Command execution canceled.")
                return None
            else:
                await rich_print("Invalid choice. Please select Execute (E), Modify (M), or Cancel (C).")

    @staticmethod
    async def yes_no_prompt(text):
        """Simple yes/no prompt for user decisions."""
        choice = await radiolist_dialog(
            title="Confirmation",
            text=text,
            values=[("yes", "Yes"), ("no", "No")]
        ).run_async()
        return choice == "yes"

    @staticmethod
    async def prompt_search(missing_path):
        """Prompts user to refine search and select a file/folder."""
        file_utils = FileUtils()
        search_files = file_utils.search_files
        while True:
            results = await search_files(missing_path)

            if not results:
                retry = await radiolist_dialog(
                    title="No matches found",
                    text=f"No matches found for '{missing_path}'. Would you like to try again?",
                    values=[("yes", "Yes"), ("no", "No")]
                ).run_async()

                if retry == "no":
                    return None
                
                missing_path = (await prompt("Modify search term:", default=missing_path)).strip()
                continue

            if len(results) > 10:
                action = await radiolist_dialog(
                    title="Too many matches",
                    text=f"More than 10 matches found for '{missing_path}'. Modify search or display all?",
                    values=[("modify", "Modify Search"), ("show", "Show All")]
                ).run_async()

                if action == "modify":
                    missing_path = (await prompt("Modify search term:", default=missing_path)).strip()
                    continue

            choice = await radiolist_dialog(
                title="Select a file",
                text=f"Multiple matches found for '{missing_path}'. Please choose one:",
                values=[(res, res) for res in results] + [("cancel", "Cancel")]
            ).run_async()

            if choice == "cancel":
                return None
            
            return choice
