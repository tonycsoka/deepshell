import sys
import asyncio
from utils.symlink_utils import create_symlink, remove_symlink
from chatbot.manager import ChatManager
from utils.pipe_utils import PipeUtils
from utils.args_utils import parse_args 

def main():
    args = parse_args()
    
    if args.install:
        create_symlink()
        return
    if args.uninstall:
        remove_symlink()
        return

    chat_manager = ChatManager()
    pipe_utils = PipeUtils(chat_manager)
    user_input = args.prompt or args.string_input or None
    file = args.file or None
    pipe_content = None

    # Determine if input or output is piped
    stdin_piped = not sys.stdin.isatty()
    stdout_piped = not sys.stdout.isatty()

    if stdin_piped:
        pipe_content = asyncio.run(pipe_utils.read_pipe())
    if stdout_piped:
        chat_manager.ui = None
        asyncio.run(chat_manager.deploy_task(user_input,file,pipe_content))
        print(chat_manager.client.last_response, end="")
    else:
        # Normal interactive mode
        if chat_manager.ui:
            chat_manager.ui.user_input, chat_manager.ui.file, chat_manager.ui.file_content = user_input,file,pipe_content
            chat_manager.ui.run()

if __name__ == "__main__":
    main()

