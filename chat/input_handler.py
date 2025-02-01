def process_input(user_input, file_content):
    """
    Prepares user input by combining prompt and file content.
    Formats piped input the same way as file input.
    """
    if file_content:
        formatted_content = f"File Content:\n{file_content.strip()}"  # Ensure consistent formatting
        if user_input.strip():
            return f"Prompt:\n{user_input.strip()}\n\n{formatted_content}"
        return formatted_content  # If only file/piped input exists
    return user_input.strip()

