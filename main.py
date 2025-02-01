import argparse
import asyncio
import sys
from config.settings import DEFAULT_MODEL, DEFAULT_HOST
from chat.chat_manager import start_chat
from utils.symlink_utils import create_symlink, remove_symlink
from utils.file_utils import read_file

async def main():
    parser = argparse.ArgumentParser(description="Ollama Chat Mode") 
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="Specify the AI model")
    parser.add_argument("--host", type=str, default=DEFAULT_HOST, help="Specify the Ollama API host")
    parser.add_argument("--thinking", action="store_true", help="Show thinking sections")
    parser.add_argument("--prompt", type=str, default="", help="Chat message")
    parser.add_argument("--file", type=str, help="File to include in chat")
    parser.add_argument("--install", action="store_true", help="Install symlink for deepshell")
    parser.add_argument("--uninstall", action="store_true", help="Uninstall symlink for deepshell")
    parser.add_argument("string_input", nargs="?", type=str, help="Optional string input")

    args = parser.parse_args()

    if args.install:
        create_symlink()
        return
    elif args.uninstall:
        remove_symlink()
        return

    # Detect piped input and treat it as file content
    file_content = ""
    if not sys.stdin.isatty():  # Means input is being piped
        file_content = sys.stdin.read().strip()  # Read the piped content

    # Read file content if a file is provided
    if args.file:
        file_content = read_file(args.file)

    # Use `--prompt` as the main user query
    user_input = args.prompt

    if not user_input and args.string_input:
        # If no --prompt flag is provided, use the optional string_input
        user_input = args.string_input

    await start_chat(
        model=args.model,
        host=args.host,
        show_thinking=args.thinking,
        user_input=user_input,
        file_content=file_content,
    )

if __name__ == "__main__":
    asyncio.run(main())

