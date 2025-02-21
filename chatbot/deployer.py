from utils.logger import Logger
from pipeline.pipe_filter import PipeFilter
from ollama_client.client_deployer import ClientDeployer

logger = Logger.get_logger()

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
        logger.info(f"Chatbot deployed in {chatbot.mode.name}")
        return chatbot, PipeFilter(chatbot)


