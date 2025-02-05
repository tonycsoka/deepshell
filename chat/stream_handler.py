from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown

class StreamHandler:
    def __init__(self, ollama_client, show_output=True):
        """
        Initializes the StreamHandler.
        """
        self.client = ollama_client
        self.console = Console()
        self.show_output = show_output 
        self.thoughts_buffer = self.client.thoughts_buffer

    async def stream_chat_response(self, user_input):
        """
        Fetches and streams AI responses and renders them live.
        """
        thinking = False
        response = ""  # Reset response for new query
        partial_thought = ""  # Buffer for incomplete thought chunks
        displaying_thinking_message = False  # Tracks if "AI is thinking..." was displayed
        first_chunk = True  # Flag to prepend "AI's Answer:" only once

        stream = await self.client.chat(user_input)

        if self.show_output:
            with Live(Markdown(""), console=self.console, refresh_per_second=10, vertical_overflow="ellipsis") as live:
                async for chunk in stream:
                    message = chunk.get('message', {}).get('content', '')

                    # Handle thinking state
                    if thinking:
                        partial_thought += message

                    # Detect start of <think> block
                    if "<think>" in message:
                        thinking = True
                        before_think, after_think = message.split("<think>", 1)
                        response += before_think  # Keep text before <think>
                        partial_thought = after_think  # Store text after <think>

                        if not self.client.show_thinking and not displaying_thinking_message:
                            live.update(Markdown("\n**AI is thinking...**\n"))
                            displaying_thinking_message = True  # Ensure it prints only once
                        continue

                    # Detect end of <think> block
                    if "</think>" in message:
                        thinking = False
                        thought_content, after_think = partial_thought.split("</think>", 1)
                        self.thoughts_buffer.append(thought_content.strip())  # Store thought content
                        if self.client.show_thinking:
                            response += f"\n**AI's Thoughts:** {thought_content.strip()}\n"
                        message = after_think  # Keep text after </think>
                        partial_thought = ""  # Reset buffer
                        displaying_thinking_message = False  # Reset flag
                    elif thinking:
                        continue  # Skip displaying content inside <think> block

                    # Append message to response and update UI
                    if first_chunk and message.strip():
                        message = f"\n**AI:** {message.strip()}\n"  # Prepend only once
                        first_chunk = False  # Disable for future chunks

                    response += message
                    live.update(Markdown(response))  # Update the live display after every response chunk

            return response
        else:
            async for chunk in stream:
                message = chunk.get('message', {}).get('content', '')

                if thinking:
                    partial_thought += message

                if "<think>" in message:
                    thinking = True
                    before_think, after_think = message.split("<think>", 1)
                    response += before_think
                    partial_thought = after_think
                    if not self.client.show_thinking and not displaying_thinking_message:
                        print("\n**AI is thinking...**\n")
                        displaying_thinking_message = True
                    continue

                if "</think>" in message:
                    thinking = False
                    thought_content, after_think = partial_thought.split("</think>", 1)
                    self.thoughts_buffer.append(thought_content.strip())
                    if self.client.show_thinking:
                        response += f"\n**AI's Thoughts:** {thought_content.strip()}\n"
                    message = after_think
                    partial_thought = ""
                    displaying_thinking_message = False

                elif thinking:
                    continue  # Skip displaying content inside <think> block

                if first_chunk and message.strip():
                    message = f"\n**AI:** {message.strip()}\n"
                    first_chunk = False

                response += message

            return response

    def render_response(self, response):
        """
        Renders the response in a formatted way using Rich.
        Updates the response live in the terminal.
        """
        with Live(Markdown(response), console=self.console, refresh_per_second=10, vertical_overflow="ellipsis") as live:
            live.update(Markdown(response))
