import sys
from config.system_prompts import DEFAULT, CODE, SHELL
from ollama_client.api_client import OllamaClient
from utils.args_utils import parse_args 
from config.enum import Mode 


# Settings
DEFAULT_MODEL = "deepseek-r1:14b"
DEFAULT_HOST = "http://localhost:11434"
CODE_MODEL = "deepseek-coder-v2:16b"
SHELL_MODEL = "deepseek-coder-v2:16b"


class ClientDeployer:
    def __init__(self, mode):
        self.args = parse_args()  # Get args using your utility function
        
        # Determine mode: either from the provided argument or based on command-line args.
        if self.args.shell:
            self.mode = Mode.SHELL
        elif self.args.code:
            self.mode = Mode.CODE
        elif mode is not None:
            self.mode = mode
        else:
            self.mode = Mode.DEFAULT

        # Default settings
        self.host = DEFAULT_HOST
        self.model = DEFAULT_MODEL
        self.config = self.generate_config(temp=0.6, prompt=DEFAULT)
        self.stream = True

        # Adjust settings based on mode
        if self.mode == Mode.SHELL:
            self._configure_shell()
        elif self.mode == Mode.CODE:
            self._configure_code()
        else:
            self._configure_default()

    def deploy(self):
        # Override values with args if provided
        if self.args.host:
            self.host = self.args.host
        if self.args.model:
            self.model = self.args.model

        # Create and return the OllamaClient instance.
        # (Make sure your OllamaClient is adjusted to accept a 'mode' attribute.)
        return OllamaClient(
            host=self.host,
            model=self.model,
            config=self.config,
            mode=self.mode,  # Passing the enum value
            stream=self.stream,
            render_output=sys.stdout.isatty(),
            show_thinking=self.args.thinking
        )

    def _configure_shell(self):
        self.config = self.generate_config(temp=0.4, prompt=SHELL)
        self.mode = Mode.SHELL
        self.model = SHELL_MODEL
        self.stream = True

    def _configure_code(self):
        self.config = self.generate_config(temp=0.5, prompt=CODE)
        self.mode = Mode.CODE
        self.model = CODE_MODEL
        self.stream = True

    def _configure_default(self):
        self.config = self.generate_config(temp=0.6, prompt=DEFAULT)
        self.mode = Mode.DEFAULT
        self.model = DEFAULT_MODEL

    def generate_config(self, temp=0.7, prompt=DEFAULT):
        return {
            "temperature": temp,
            "system": prompt,
        }
