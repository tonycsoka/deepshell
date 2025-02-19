from ollama_client.client_deployer import ClientDeployer
from pipeline.pipe_filter import PipeFilter
from config.settings import Mode


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

    def _initialize_shell_mode(self,chatbot,chatbot_filter):
        """
        Initializes SHELL mode by deploying both a SYSTEM listener and a SHELL generator.
        """

        listener, listener_filter = chatbot, chatbot_filter
        listener.switch_mode(Mode.SYSTEM)# SYSTEM chatbot (listener)
        generator, generator_filter = self.deploy_chatbot(Mode.SHELL)  # SHELL chatbot (generator)

        listener.keep_history = False
        generator.keep_history = False

        return generator, generator_filter, listener, listener_filter

    async def chatbot_init(self):
        """
        Initializes the chatbot based on its mode.
        """
        chatbot, chatbot_filter = self.deploy_chatbot()
        mode = chatbot.mode

        if self.ui:
            await self.ui.fancy_print("[yellow]Initializing chatbot, please wait...[/yellow]\n")

        if mode == Mode.SHELL:
            return self._initialize_shell_mode(chatbot,chatbot_filter)

        return chatbot, chatbot_filter


