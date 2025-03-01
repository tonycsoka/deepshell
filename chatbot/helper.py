import platform
from datetime import datetime
from utils.logger import Logger

logger = Logger.get_logger()

class PromptHelper:
    """
    A utility class for generating shell command prompts and analyzing command output.
    """

    user_system = platform.uname()
    current_time = datetime.now().strftime("%d-%m-%y %H:%M:%S")

    @staticmethod
    def shell_helper(user_input: str) -> str:
        """
        Generates a shell command prompt for the user's system.

        Args:
            user_input (str): The user's request for a shell command.

        Returns:
            str: A formatted prompt instructing the model to generate a shell command.
        """
        return f"""
        You are a shell command generator only.
        In response to a user request generate a shell command for {PromptHelper.user_system}
        Do not include anything else beyond the command itself. If command requires administrative privileges, make sure to include 'sudo'.
        User request: {user_input}"""

    @staticmethod
    def analyzer_helper(command: str, output: str) -> str:
        """
        Generates a prompt to analyze command output.

        Args:
            command (str): The executed shell command.
            output (str): The output of the command.

        Returns:
            str: A formatted prompt instructing the model to analyze and summarize key details.
        """
        return f"""
        Analyze the output of the following command: {command}  
        Summarize key details, highlighting errors, warnings, and important findings.
        Current system time for reference: {PromptHelper.current_time}
        Output: {output}  
        """

    @staticmethod
    def topics_helper(history: list) -> str:
        """
        Generates a prompt instructing the model to name a topic and provide a description in JSON format 
        based on conversation history provided as a list.

        Args:
            history (list): A list of dictionaries containing the role and message of previous conversation exchanges.

        Returns:
            str: A formatted prompt instructing the model to reply in JSON format.
        """
        history_text = str(history)
        
        logger.debug(f"Topics helper: injected history: {history_text}")
        return f"""
        Based on the following conversation history, please name a topic and provide a description of that topic in JSON format:

        {history_text}

        The response should be a JSON object with the following keys:
        - "topic_name": The name of the topic.
        - "topic_description": A brief description of the topic.
        """


    @staticmethod
    def metadata_code(content: str) -> str:
        return f"""
        Analyze the following code and generate structured metadata in JSON format. The metadata should include the following categories:
        1. Functions: List of function names and their descriptions (if any).
        2. Classes: List of class names and a brief description of their purpose.
        3. Purpose: A brief summary of what the code is meant to accomplish or its functionality.

        Code:
        {content}
        """
