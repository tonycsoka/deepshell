import asyncio
from ollama import AsyncClient
from config.settings import MODE_CONFIGS, Mode


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
        self.keep_history = True
        self.history = []
        self.last_response = ""
        self.pause_stream = False

    def switch_mode(self, mode):
        """Dynamically switches mode and updates config."""
        if mode == self.mode:
            return

        config = MODE_CONFIGS[mode]
        self.model = config["model"]
        self.config = {"temperature": config["temp"], "system": config["prompt"]}
        self.stream = config["stream"]
        self.mode = mode
        self.history.clear()

    async def _chat_stream(self, input):
        """Fetches response from the Ollama API and streams into output buffer."""

        input = {"role": "user", "content": input}
        if self.keep_history:
            self.history.append(input)
            input = self.history
        else:
            input = [input]

        async for part in await self.client.chat(
            model=self.model,
            messages=input,
            options=self.config,
            stream=self.stream
        ):
            if not self.pause_stream:
                await self.output_buffer.put(part.get('message', {}).get('content', ''))
        if not self.pause_stream:
            await self.output_buffer.put(None)

    async def _describe_image(self, image: str | None):
        if not image:
            return "No image provided"

        if self.mode == Mode.VISION:
            message = {'role': 'user', 'content': 'Describe this image', 'images': [image]}
            response = await AsyncClient().chat(model=self.model, messages=[message])
            
            message_data = response.get('message')
            if not message_data:
                return "No message in response"

            content = message_data.get('content')
            return content if isinstance(content, str) else "No content found"

    async def _fetch_response(self, message):
       
        message = {'role': 'user', 'content': message}
        response = await AsyncClient().chat(model=self.model, messages=[message])
            
        message_data = response.get('message')
        if not message_data:
            return "No message in response"

        content = message_data.get('content')
        return content if isinstance(content, str) else "No content found"
