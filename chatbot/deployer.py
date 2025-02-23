from utils.logger import Logger
from pipeline.pipe_filter import PipeFilter
from ollama_client.client_deployer import ClientDeployer

logger = Logger.get_logger()

class ChatBotDeployer:
    """
    Deploys a ready-to-use chatbot with its own pipeline filter.
    """
    def __init__(self):
        self.client_deployer = ClientDeployer()

    @staticmethod
    def deploy_chatbot(mode=None):
        """
        Deploys a chatbot with an optional mode.
        """
        client_deployer = ClientDeployer()  # Creating an instance inside the static method
        chatbot = client_deployer.deploy()
        if mode:
            chatbot.switch_mode(mode)
        logger.info(f"Chatbot deployed in {chatbot.mode.name}")
        return chatbot, PipeFilter(chatbot)

