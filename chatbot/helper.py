import platform

class PromptHelper:
    """
    A utility class for generating shell command prompts and analyzing command output.
    """

    user_system = platform.uname()

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
        Output: {output}  
        """

