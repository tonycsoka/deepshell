from rich.console import Console
from rich.live import Live
from chat.input_handler import CommandProcessor
from chat.output_renderer import render_response
from ollama_client.stream_handler import stream_chat_response

console = Console()

async def start_chat(model, host, config, show_thinking, user_input="", file_content=None):
    print(f"Chat mode activated with model: {model} on {host}. Type 'exit' to quit.\n")
    default_config = config
    command_processor = CommandProcessor(default_config=config)
    history = []

    # Process file/folder commands at startup
    if user_input and not file_content:
        file_content = command_processor.process_file_or_folder(user_input)  # Ensure file content is retrieved
    user_input = command_processor.handle_command(user_input)
    user_input = command_processor.format_input(user_input,file_content)
    if command_processor.config != config:
        config = command_processor.config

    while True:
        # Get user input (interactive or piped)
        if user_input == "":
            user_input = command_processor.get_user_input()
            if user_input:
                file_content = command_processor.process_file_or_folder(user_input)  # Ensure file content is retrieved
                user_input = command_processor.handle_command(user_input)           

        if user_input == "exit":
            print("Exiting chat.")
            break  
        user_input = command_processor.format_input(user_input,file_content)
        if command_processor.config != config and command_processor.config == default_config:
            continue
        elif command_processor.config != config:
            config = command_processor.config

        history.append({"role": "user", "content": user_input})

        with Live(console=console, refresh_per_second=30, vertical_overflow="ellipsis") as live:
            response = await stream_chat_response(user_input, model, host, config, show_thinking, history, live)
            render_response(response, live)
            history.append({"role": "assistant", "content": response})

        user_input = ""
        file_content = ""

