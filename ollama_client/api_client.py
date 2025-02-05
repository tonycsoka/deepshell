from ollama import AsyncClient
from config.settings import DEFAULT_MODEL, DEFAULT_HOST
from config.settings import generate_config

class OllamaClient:
    def __init__(self, host=DEFAULT_HOST, model=DEFAULT_MODEL, config=generate_config(), stream=True, show_thinking=False):
        """
        Initializes the OllamaClient for chat interactions.
        """
        self.client = AsyncClient(host=host)
        self.host = host
        self.model = model
        self.config = config
        self.stream = stream
        self.show_thinking = show_thinking
        self.thoughts_buffer = []
        self.history = []

    async def chat(self,user_input):
        """
        Sends a chat request and streams the response.
        """
        return await self.client.chat(
                model=self.model,
                messages=user_input,
                options=self.config,
                stream=self.stream
            )

