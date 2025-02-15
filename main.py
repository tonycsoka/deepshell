import sys
import asyncio
from ollama_client.client_deployer import ClientDeployer
from utils.symlink_utils import create_symlink, remove_symlink
from chatbot_manager.chatbot_manager import ChatManager
from ui.ui import ChatMode
from utils.pipe_utils import PipeUtils

def main():
    deployer = ClientDeployer()
    ollama_client = deployer.deploy()
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
        pipe_utils = PipeUtils(chat_manager)
        asyncio.run(pipe_utils.run(ollama_client, user_input)) 

if __name__ == "__main__":
    main()
