import asyncio
import sys
from config.settings import ClientDeployer
from utils.symlink_utils import create_symlink, remove_symlink
from chatbot_manager.chatbot_manager import ChatManager
from utils.file_utils import FileUtils
from utils.command_processor import CommandProcessor

async def main():
    """Main function to handle Ollama Chat Mode."""
    deployer = ClientDeployer()
    ollama_client = deployer.deploy()  # This will now only deal with API interactions
    args = deployer.args

    if args.install:
        create_symlink()
        return
    if args.uninstall:
        remove_symlink()
        return

    user_input = args.prompt or args.string_input or None
    chat_manager = ChatManager(ollama_client)

    if not sys.stdin.isatty():
        ollama_client.render_output = False
        utils = FileUtils()
        pipe = await utils.read_pipe()
        if pipe:
            if user_input:
                processor = CommandProcessor(ollama_client)
                user_input = processor.format_input(user_input,pipe)
            else: 
                user_input = pipe

        await chat_manager.task_manager(user_input)
    
        return
    else:

        await chat_manager.start_chat(user_input,args.file)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        sys.exit(f"Error: {e}")

