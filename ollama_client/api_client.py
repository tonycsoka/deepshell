from ollama import AsyncClient

class OllamaClient:
    def __init__(self, host):
        self.client = AsyncClient(host=host)

    async def chat(self, model, messages, stream=True):
        """
        Sends a chat request to the Ollama API.
        """
        return await self.client.chat(model=model, messages=messages, stream=stream)
