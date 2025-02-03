from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown

class StreamHandler:
    def __init__(self, ollama_client, console=None, refresh_per_second=10):
        """
        Initializes the StreamHandler.
        """
        self.client = ollama_client
        self.console = console or Console()
        self.refresh_per_second = refresh_per_second
        self.thinking = False
        self.response = ""

    async def stream_chat_response(self, user_input):
        """
        Fetches and streams AI responses and renders them live.
        """
        self.response = ""  # Reset the response for each new query
        stream = await self.client.chat(user_input)

        # Use Live to render the response in real-time
        with Live(Markdown(""), console=self.console, refresh_per_second=self.refresh_per_second, vertical_overflow="ellipsis") as live:
            async for chunk in stream:
                message = chunk['message']['content']

                # Handle thinking state and update UI
                if not self.client.show_thinking:
                    if "<think>" in message:
                        self.thinking = True
                        live.update(Markdown("**AI:** Hmmm..."))
                        continue  
                    if "</think>" in message:
                        self.thinking = False
                        continue  
                    if self.thinking:
                        continue  

                # Append the message to the response and update live
                self.response += message
                live.update(Markdown(self.response))

        return self.response

    def render_response(self, response):
        """
        Renders the response in a formatted way using Rich.
        Updates the response live in the terminal.
        """
        # Display the response using live update (if not streaming)
        with Live(Markdown(response), console=self.console, refresh_per_second=self.refresh_per_second, vertical_overflow="ellipsis") as live:
            live.update(Markdown(response))
