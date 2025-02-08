import asyncio
from ollama import AsyncClient
from chat.streamer import rich_print, thinking_animation
from chat.filtering import Filtering

class OllamaClient:
    def __init__(self, host, model, config, config_name, stream, render_output, show_thinking):
        self.client = AsyncClient(host=host)
        self.model = model 
        self.host = host
        self.config = config
        self.config_name = config_name
        self.stream = stream or True
        self.render_output = render_output or True
        self.show_thinking = show_thinking or False
        self.thoughts_buffer = []   
        self.history = []
        self.filtering = Filtering(self)
    
    async def chat(self, user_input):
        """
        Sends a chat request, filters the raw response, and renders it.
        Pipeline: raw stream → filtering → rendering.
        """
        response = ""
        animation_task = asyncio.create_task(thinking_animation())
        self.history.append({"role": "user", "content": user_input})
        raw_stream = await self._chat_stream(self.history)
        animation_task.cancel()

        async for chunk in self.filtering._filter_thoughts(raw_stream): 
            response += chunk
            if self.render_output and self.config_name == "default":
                await rich_print(chunk)
        # 
        if self.config_name == "shell":
            response = await self.filtering._extract_code(response, self.render_output, True)
        elif self.config_name == "code":
            response = await self.filtering._extract_code(response, self.render_output) 
        self.history.append({"role": "assistant", "content": response})

        
        return response

    async def _chat_stream(self, user_input):
        """
        Sends the chat request to the Ollama API and returns the raw stream.
        """
        return await self.client.chat(
            model=self.model,
            messages=user_input,
            options=self.config,
            stream=self.stream
        )

