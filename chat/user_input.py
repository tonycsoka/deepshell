import sys
import os
from prompt_toolkit import PromptSession
from prompt_toolkit.shortcuts import prompt, radiolist_dialog
from prompt_toolkit.completion import WordCompleter

async def get_user_input(prompt="You: "):
    """
    Handles interactive user input using prompt_toolkit asynchronously.
    In piped mode, it falls back to sys.stdin.read().
    """
    if sys.stdin.isatty():
        session = PromptSession()
        try:
            user_input = await session.prompt_async(prompt)
            user_input = user_input.strip()
            if user_input.lower() == "exit":
                return "exit"
            return user_input
        except KeyboardInterrupt:
            print("\nExiting chat.")
            return "exit"
    else:
        try:
            user_input = sys.stdin.read().strip()
            return user_input if user_input else "exit"
        except EOFError:
            return "exit"

async def prompt_search(missing_path):
    """
    Searches for a missing file or folder in the home directory and prompts the user to select one.
    """
    home_dir = os.path.expanduser("~")
    
    while True:
        results = []

        for root, dirs, files in os.walk(home_dir):
            # Exclude hidden folders and files
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            files = [f for f in files if not f.startswith(".")]

            # Search for matching files and directories
            for name in files + dirs:
                if missing_path.lower() in name.lower():
                    results.append(os.path.join(root, name))

        if not results:
            retry = await radiolist_dialog(
                title="No matches found",
                text=f"No matches found for '{missing_path}'. Would you like to try again?",
                values=[("yes", "Yes"), ("no", "No")]
            ).run_async()  # Async call here to avoid blocking
            if retry == "no":
                return None
            missing_path = await prompt("Modify search term:", default=missing_path).strip()
            continue

        if len(results) > 10:
            action = await radiolist_dialog(
                title="Too many matches",
                text=f"More than 10 matches found for '{missing_path}'. Would you like to modify your search or display all?",
                values=[("modify", "Modify Search"), ("show", "Show All")]
            ).run_async()  # Async call
            if action == "modify":
                missing_path = await prompt("Modify search term:", default=missing_path).strip()
                continue

        # Display search results to the user
        choice = await radiolist_dialog(
            title="Select a file",
            text=f"Multiple matches found for '{missing_path}'. Please choose one:",
            values=[(res, res) for res in results] + [("cancel", "Cancel")]
        ).run_async()  # Async call
        
        if choice == "cancel":
            return None
        
        return choice
def confirm_execute_command(command):
    """Confirms and executes a shell command."""
    if not command:
        return "No command specified."

    choices = ["Execute", "Modify", "Cancel"]
    completer = WordCompleter(choices, ignore_case=True)

    while True:
        choice = prompt("Choose action: ", completer=completer).strip().lower()
        if choice == "execute":
            return command
        elif choice == "modify":
            command = prompt("Modify command: ", default=command).strip()
        elif choice == "cancel":
            return "Command execution canceled."
        else:
            print("Invalid choice. Please select Execute, Modify, or Cancel.")
