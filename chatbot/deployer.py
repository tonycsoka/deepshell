import asyncio
from ollama_client.client_deployer import ClientDeployer
from pipeline.pipe_filter import PipeFilter
from config.settings import Mode
from config.system_prompts import *

class ChatBotDeployer:
    """
    Deploys a ready-to-use chatbot with its own pipeline filter.
    """
    def __init__(self, ui=None):
        self.client_deployer = ClientDeployer()
        self.ui = ui

    def deploy_chatbot(self, mode=None):
        """
        Deploys a chatbot with an optional mode.
        """
        chatbot = self.client_deployer.deploy()
        if mode:
            chatbot.switch_mode(mode)
        return chatbot, PipeFilter(chatbot)

    async def _initialize_shell_mode(self, chatbot):
        """
        Handles initialization for SHELL mode by deploying a listener and running both tasks.
        """
        listener, listener_filter = self.deploy_chatbot(Mode.SYSTEM)
        listener.init = True

        analyzer_task = asyncio.create_task(listener._chat_stream(SYSTEM))
        await asyncio.sleep(1)
        generator_task = asyncio.create_task(chatbot._chat_stream(SHELL))

        await asyncio.gather(analyzer_task, generator_task)
        listener.init = False

        return listener, listener_filter

    async def chatbot_init(self):
        """
        Initializes the chatbot based on its mode.
        """
        chatbot, chatbot_filter = self.deploy_chatbot()
        chatbot.init = True
        mode = chatbot.mode

        if self.ui:
            await self.ui.fancy_print("[yellow]Initializing chatbot, please wait...[/yellow]\n")

        # Ensure `listener` and `listener_filter` are always initialized
        listener, listener_filter = None, None  

        mode_handlers = {
            Mode.SHELL: self._initialize_shell_mode,
            Mode.CODE: chatbot._chat_stream,
            Mode.SYSTEM: chatbot._chat_stream,
        }

        if mode in mode_handlers:
            if mode == Mode.SHELL:
                listener, listener_filter = await mode_handlers[mode](chatbot)
            else:
                await mode_handlers[mode](mode)


        chatbot.init = False

        return (chatbot, chatbot_filter, listener, listener_filter) if listener is not None else (chatbot, chatbot_filter)
