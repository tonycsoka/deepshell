from rich.console import Console
from rich.live import Live
from chat.input_handler import commands_handler, process_input
from chat.output_renderer import render_response
from ollama_client.stream_handler import stream_chat_response
import sys

console = Console()

async def start_chat(model, host, config, show_thinking, user_input, file_content):
    print(f"Chat mode activated with model: {model} on {host}. Type 'exit' to quit.\n")
    default_config = config
    history = [] 
    
    if not file_content and user_input:
        file_content, new_config = commands_handler(user_input)
        if new_config:
            config = new_config

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
                if not file_content and user_input:
                    file_content, new_config = commands_handler(user_input)
                    if new_config:
                        config = new_config
                        if config == default_config:
                            user_input = ""
                            continue

                if user_input=="":
                   continue
                else:
                    user_input = process_input (user_input, file_content)
            else:
                # If input is coming from a pipe, exit or wait for more
                break

        history.append({"role": "user", "content": user_input})  # Add to history for use in the session
        with Live(console=console, refresh_per_second=30, vertical_overflow="ellipsis") as live:
            response = await stream_chat_response(user_input, model, host, config, show_thinking, history, live)
            render_response(response, live)
            history.append({"role": "assistant", "content": response})
            user_input = ""
            file_content = ""
        print()  # Add a newline after the response to ensure clean output

