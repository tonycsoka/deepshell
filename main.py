import asyncio
import sys
from config.settings import deploy_client
from chat.manager import start_chat
from utils.symlink_utils import create_symlink, remove_symlink
from utils.file_utils import read_pipe
from ollama_client.api_client import OllamaClient
from utils.args_utils import parse_args 
from chat.input_handler import CommandProcessor

async def main():
    """Main function to handle Ollama Chat Mode."""
    args = parse_args()

    if args.install:
        create_symlink()
        return
    if args.uninstall:
        remove_symlink()
        return

    ollama_client = deploy_client(args)
    command_processor = CommandProcessor(ollama_client)

    user_input = args.prompt or args.string_input or ""
    # Prioritize file argument over piped input.
    if args.file:
        file_content = await command_processor.process_file_or_folder(args.file)
    elif not sys.stdin.isatty():
        file_content =  await read_pipe()
    else:
        file_content = None
   
    if file_content:
        user_input = command_processor.format_input(user_input, file_content)
    else:
        user_input = await command_processor.handle_command(user_input)
   
    await start_chat(ollama_client,user_input)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        sys.exit(f"Error: {e}")
