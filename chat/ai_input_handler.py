#Not fully functional yet
import os
import re
import sys
import json
from ollama_client.api_client import OllamaClient
from config.settings import DEFAULT_CONFIG, DEFAULT_MODEL, DEFAULT_HOST
from utils.file_utils import read_file, read_folder, prompt_search
from prompt_toolkit.shortcuts import prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit import PromptSession

session = PromptSession()

# Mode and function commands
MODE_COMMANDS = {
    "generate code": DEFAULT_CONFIG,
    "generate script": DEFAULT_CONFIG,
    "default mode": DEFAULT_CONFIG,
}

FUNCTION_MAP = {
    "read file": read_file,
    "read folder": read_folder,
    "find": os.path.exists,
}

THINKING_KEYWORDS = ["enable thinking", "show thinking", "analyze"]

# Generate SYSTEM_PROMPT dynamically to include all commands
def generate_system_prompt():
    supported_intents = ["switch mode", "read file", "read folder", "find", "run command"]
    all_commands = list(MODE_COMMANDS.keys()) + list(FUNCTION_MAP.keys())

    system_prompt = f"""
    You are an AI that extracts user intent and action details from messages.
    Your response must be in JSON format:
    {{"intent": "open file", "target": "config.json"}}

    Supported intents:
    - {', '.join(supported_intents)}
    Available commands:
    - {', '.join(all_commands)}

    Ensure 'target' is meaningful.
    """

    return system_prompt

# Default config now includes the dynamically generated system prompt
HELPER_CONFIG = {
    "temperature": 0.6,
    "system": generate_system_prompt(),
}

async def get_user_input(prompt="You: "):
    """Handles interactive user input asynchronously."""
    if sys.stdin.isatty():
        try:
            user_input = await session.prompt_async(prompt)
            return user_input.strip() if user_input.lower() != "exit" else "exit"
        except KeyboardInterrupt:
            print("\nExiting chat.")
            return "exit"
    else:
        try:
            user_input = sys.stdin.read().strip()
            return user_input if user_input else "exit"
        except EOFError:
            return "exit"

class CommandProcessor:
    """Handles user input, AI-driven command processing, mode switching, and task execution."""

    def __init__(self, ollama_client):
        self.ollama_client = ollama_client
        self.config = self.ollama_client.config

    def is_thinking_command(self, user_input):
        """Checks if the input contains any of the thinking-related keywords."""
        return any(keyword in user_input.lower() for keyword in THINKING_KEYWORDS)

    async def handle_command(self, user_input):
        """Processes user input and executes the appropriate action."""
        target, additional_action = self.extract_target_and_action(user_input)

        if self.is_thinking_command(user_input):
            self.ollama_client.show_thinking = True
            return "Thinking enabled."

        if "disable thinking" in user_input.lower():
            self.ollama_client.show_thinking = False
            return "Thinking disabled."

        if target:
            # Use interactive prompt if needed
            if not os.path.exists(target):
                target = prompt_search(target)
                if not target:
                    return f"No results found for '{target}'."

            return self.format_input(user_input, self.process_target(target, additional_action))

        # Fall back to AI processing if no target was found
        return await self.get_ai_response(user_input)

    def extract_target_and_action(self, user_input):
        """Extracts target (file/folder) and optional additional action."""
        parts = re.split(r"\band\b", user_input, maxsplit=1)
        main_command = parts[0].strip()
        additional_action = parts[1].strip() if len(parts) > 1 else None

        tokens = main_command.split()
        if not tokens:
            return None, None

        action = next((word for word in tokens if word in FUNCTION_MAP), None)
        if not action:
            return None, None

        target_index = tokens.index(action) + 1
        target = " ".join(tokens[target_index:]) if target_index < len(tokens) else ""
        if target == "this folder":
            target = os.getcwd()

        return target, additional_action

    def process_target(self, target, additional_action):
        """Processes manually extracted targets."""
        if os.path.isdir(target):
            file_content = read_folder(target)
        elif os.path.isfile(target):
            file_content = read_file(target)
        else:
            return f"Unknown target: {target}"

        return additional_action if additional_action else file_content

    async def get_ai_response(self, user_input):
        """Processes the AI response synchronously and removes unnecessary metadata."""
        new_client = OllamaClient(config=HELPER_CONFIG, stream=False)
        raw_response = await new_client.chat([{"role": "user", "content": user_input}])

        # Extract and clean response
        ai_message = raw_response.get("message", {})
        ai_content = ai_message.get("content", "").strip()

        # Remove unwanted placeholders
        ai_content = re.sub(r"<think>.*?</think>", "", ai_content, flags=re.DOTALL).strip()

        # If response is empty or irrelevant, return a fallback
        return ai_content if ai_content else "I'm here to help. What do you need?"

    async def process_ai_response(self, ai_response, user_input):
        """Handles AI-extracted intents."""
        intent = ai_response.get("intent")
        target = ai_response.get("target")

        if intent == "switch mode":
            return self.switch_mode(target)

        if intent in FUNCTION_MAP and target:
            return FUNCTION_MAP[intent](target)

        if intent == "run command":
            return self.confirm_execute_command(target)

        return f"AI: {target}" if target else "I didn't understand that."

    def switch_mode(self, mode_name):
        """Handles mode switching."""
        for keyword, config in MODE_COMMANDS.items():
            if keyword in mode_name.lower():
                self.ollama_client.config = config
                return f"Mode switched to {keyword}"
        return "Invalid mode specified."

    def confirm_execute_command(self, command):
        """Confirms and executes a shell command."""
        if not command:
            return "No command specified."

        choices = ["Execute", "Modify", "Cancel"]
        completer = WordCompleter(choices, ignore_case=True)

        while True:
            choice = prompt("Choose action: ", completer=completer).strip().lower()
            if choice == "execute":
                return self.execute_shell_command(command)
            elif choice == "modify":
                command = prompt("Modify command: ", default=command).strip()
            elif choice == "cancel":
                return "Command execution canceled."
            else:
                print("Invalid choice. Please select Execute, Modify, or Cancel.")

    def execute_shell_command(self, command):
        """Runs a shell command securely."""
        try:
            output = os.popen(command).read()
            return f"Command Output:\n{output.strip()}"
        except Exception as e:
            return f"Error executing command: {e}"

    def format_input(self, user_input, content):
        """Formats the input for display."""
        return f"Prompt:\n{user_input}\n\nContent:\n{content.strip()}" if content else user_input