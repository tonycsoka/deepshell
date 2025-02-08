import asyncio
import sys
from config.settings import ClientDeployer
from chat.manager import start_chat
from utils.symlink_utils import create_symlink, remove_symlink
from utils.file_utils import FileUtils
from chat.input_handler import CommandProcessor

async def main():

    """Main function to handle Ollama Chat Mode."""
    deployer = ClientDeployer()
    ollama_client = deployer.deploy()
    file_utils = FileUtils()
    command_processor = CommandProcessor(ollama_client) 
    args = deployer.args

    if args.install:
        create_symlink()
        return
    if args.uninstall:
        remove_symlink()
        return

    user_input = args.prompt or args.string_input or ""
    # Prioritize file argument over piped input.
    if args.file:
        file_content = await command_processor.process_file_or_folder(args.file)
    elif not sys.stdin.isatty():
        file_content =  await file_utils.read_pipe()
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
