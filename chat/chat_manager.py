import readline
from rich.console import Console
from rich.live import Live
from chat.input_handler import process_input
from chat.output_renderer import render_response
from ollama_client.stream_handler import stream_chat_response
import sys

console = Console()

async def start_chat(model, host, show_thinking, user_input, file_content):
    print(f"Chat mode activated with model: {model} on {host}. Type 'exit' to quit.\n")

    history = [] 

    user_input = process_input(user_input, file_content)

    while True:
        # If no user input was passed (either empty or from file), attempt to get input
        if user_input=="":
            if sys.stdin.isatty():
                # If input is interactive (not piped)
                try:
                    user_input = input("You: ")  # Regular prompt
                except KeyboardInterrupt:
                    print("\nExiting chat.")
                    break

                if user_input.lower() == 'exit':
                    break

                readline.add_history(user_input)  # Add to history for use in the session
            else:
                # If input is coming from a pipe, exit or wait for more
                break

        with Live(console=console, refresh_per_second=30, vertical_overflow="ellipsis") as live:
            response = await stream_chat_response(user_input, model, host, show_thinking, history, live)
            render_response(response, live)
            user_input = ""  # Reset user_input after processing
        print()  # Add a newline after the response to ensure clean output

