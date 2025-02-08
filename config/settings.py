
import sys
from config.system_prompts import DEFAULT, CODE, SHELL
from ollama_client.api_client import OllamaClient
from utils.args_utils import parse_args 

# Settings
DEFAULT_MODEL = "deepseek-r1:14b"
DEFAULT_HOST = "http://localhost:11434"
CODE_MODEL = "deepseek-coder-v2:16b"
SHELL_MODEL = "deepseek-coder-v2:16b"

class ClientDeployer:
    def __init__(self, config_name="default"):
        # If no args are passed, we try to fetch them from the utility
        self.args = parse_args()  # Get args using your utility function
        self.config_name = config_name or self.args.config_name  # Priority on the config_name

        # Default settings
        self.host = DEFAULT_HOST
        self.model = DEFAULT_MODEL
        self.config = self.generate_config(temp=0.6, prompt=DEFAULT)
        self.stream = True

        # Now let's prioritize the config_name and adjust accordingly
        if self.args.shell or self.config_name == "shell":
            self._configure_shell()
        elif self.args.code or self.config_name == "code":
            self._configure_code()
        else:
            self._configure_default()

    def deploy(self):
        # Override values with args if provided
        if self.args.host:
            self.host = self.args.host
        if self.args.model:
            self.model = self.args.model

        # Create and return the OllamaClient instance
        return OllamaClient(
            host=self.host,
            model=self.model,
            config=self.config,
            config_name=self.config_name,
            stream=self.stream,
            render_output=not sys.stdout.isatty(),
            show_thinking=self.args.thinking
        )

    def _configure_shell(self):
        self.config = self.generate_config(temp=0.4, prompt=SHELL)
        self.config_name = "shell"
        self.model = SHELL_MODEL
        self.stream = False

    def _configure_code(self):
        self.config = self.generate_config(temp=0.5, prompt=CODE)
        self.config_name = "code"
        self.model = CODE_MODEL
        self.stream = True

    def _configure_default(self):
        self.config = self.generate_config(temp=0.6, prompt=DEFAULT)
        self.config_name = "default"
        self.model = DEFAULT_MODEL

    def generate_config(self, temp=0.7, prompt=DEFAULT):
        """
        Generates a configuration dictionary for the client.
        """
        config = {
            "temperature": temp,
            "system": prompt,
        }
        return config

    def generate_helper_config(self, supported_actions=["open", "find", "play"]):
        """
        Generates a helper configuration for specific intents.
        """
        system_prompt = f"""
        You are an AI that extracts user intent and target from messages.
        Your response must be in JSON format:
        {{"intent": "open file", "target": "config.json"}}

        Supported actions:
        - {', '.join(supported_actions)}

        If none of the actions were detected:
        - reply "None"
        """
        return self.generate_config(temp=0.6, prompt=system_prompt)

    # Default configuration setup (moved inside the class for better structure)
    def get_default_config(self):
        return self.generate_config(temp=0.6, prompt=DEFAULT)

    def get_code_config(self):
        return self.generate_config(temp=0.5, prompt=CODE)

    def get_shell_config(self):
        return self.generate_config(temp=0.4, prompt=SHELL)

