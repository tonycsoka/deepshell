import asyncio
from ollama import AsyncClient
from config.enum import Mode

class OllamaClient:
    def __init__(self, host, model, config, mode, stream=True, render_output=True, show_thinking=False):
        self.client = AsyncClient(host=host)
        self.model = model
        self.config = config
        self.mode = mode
        self.stream = stream
        self.render_output = render_output
        self.show_thinking = show_thinking
        self.output_buffer = asyncio.Queue()
        self.history = []
        self.last_response = ""

    async def _chat_stream(self, input):
        """Fetches response from the Ollama API and streams into output buffer."""
       
        self.history.append({"role": "user", "content": input})

        async for part in await self.client.chat(
            model=self.model,
            messages=self.history,
            options=self.config,
            stream=self.stream
        ):
            await self.output_buffer.put(part.get('message', {}).get('content', ''))  # Push raw stream into buffer
        if self.mode == Mode.SHELL:
            self.history = []
        await self.output_buffer.put(None)

