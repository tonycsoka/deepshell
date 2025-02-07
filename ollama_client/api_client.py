from ollama import AsyncClient
from rich.console import Console
from chat.streamer import render_response 
from chat.filtering import Filtering  

class OllamaClient:
    def __init__(self, host, model, config, config_name, stream,render_output, show_thinking):
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
        self.console = Console()
        self.filtering = Filtering(self)
           
    
    async def chat(self, user_input):
        """
        Sends a chat request, filters the raw response, and renders it.
        Pipeline: raw stream → filtering → rendering.
        """
        response = ""
       
        self.history.append({"role": "user", "content": user_input})
        raw_stream = await self._chat_stream(self.history)
        self.history.append({"role": "assistant", "content": response})
        async for chunk in self.filtering._filter_thoughts(raw_stream): 
            response += chunk
            if self.render_output and self.config_name == "default":
                await render_response(chunk, self.console)
       
        if self.config_name == "code":
            response = self.filtering._extract_code(response,self.render_output)
        elif self.config_name == "shell":
            response = self.filtering._extract_code(response,self.render_output,True)
       
        if self.render_output and self.config_name != "default":
            await render_response(response, self.console) 

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
