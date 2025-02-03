from chat.input_handler import CommandProcessor
from chat.stream_handler import StreamHandler

async def start_chat(ollama_client, user_input="", file_content=None):
    stream_handler = StreamHandler(ollama_client)
    render_response = stream_handler.render_response# Create StreamHandler instance
    render_response(f"Chat mode activated with model: {ollama_client.model} on {ollama_client.host}. Type 'exit' to quit.\n")

    default_config = ollama_client.config
    command_processor = CommandProcessor(default_config)
    history = ollama_client.history

    # Process file/folder commands at startup
    if user_input and not file_content:
        file_content = command_processor.process_file_or_folder(user_input)
    user_input = command_processor.handle_command(user_input)
    user_input = command_processor.format_input(user_input, file_content)
    if command_processor.config != ollama_client.config:
        ollama_client.config = command_processor.config

    while True:
        if user_input == "":
            user_input = await command_processor.get_user_input()
            if user_input:
                file_content = command_processor.process_file_or_folder(user_input)
                user_input = command_processor.handle_command(user_input)

        if user_input == "exit":
            render_response("Exiting chat.")
            break 

        user_input = command_processor.format_input(user_input, file_content)
        if command_processor.config != ollama_client.config and command_processor.config == default_config:
            continue
        elif command_processor.config != ollama_client.config:
            ollama_client.config = command_processor.config

        history.append({"role": "user", "content": user_input})
        
        # Get the response from StreamHandler (this will also handle live updates)
        response = await stream_handler.stream_chat_response(history)
        history.append({"role": "assistant", "content": response})

        user_input = ""
        file_content = ""
        ollama_client.history = history
