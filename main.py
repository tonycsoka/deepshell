import asyncio
import sys
from config.settings import ClientDeployer
from utils.symlink_utils import create_symlink, remove_symlink
from chatbot_manager.chatbot_manager import ChatManager
from utils.file_utils import FileUtils
from utils.command_processor import CommandProcessor
from ui.ui import ChatMode
from config.settings import Mode

def main():
    # You can also choose a mode here if desired:
    deployer = ClientDeployer(mode=Mode.DEFAULT)
    ollama_client = deployer.deploy()  # Now includes the mode in the client
    args = deployer.args

    if args.install:
        create_symlink()
        return
    if args.uninstall:
        remove_symlink()
        return

    user_input = args.prompt or args.string_input or None
    
    if sys.stdin.isatty():
        app = ChatMode(ollama_client, user_input, args.file)
        app.run()
    else:
        ollama_client.render_output = False
        chat_manager = ChatManager(ollama_client)
        utils = FileUtils()
        pipe = asyncio.create_task(utils.read_pipe())
        if pipe:
            if user_input:
                processor = CommandProcessor(ollama_client)
                user_input = processor.format_input(user_input, pipe)
            else: 
                user_input = pipe
        asyncio.create_task(chat_manager.task_manager(user_input))
        return

if __name__ == "__main__":
    main()
