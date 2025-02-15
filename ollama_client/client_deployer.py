import sys
from ollama_client.api_client import OllamaClient
from utils.args_utils import parse_args 
from config.settings import *

class ClientDeployer:
    def __init__(self):
        self.args = parse_args()  # Get args using your utility function

        # Determine mode dynamically
        self.mode = Mode.SHELL if self.args.shell else Mode.CODE if self.args.code else Mode.DEFAULT
        
        # Apply mode-specific settings
        config = MODE_CONFIGS[self.mode]
        self.host = DEFAULT_HOST
        self.model = config["model"]
        self.config = self.generate_config(temp=config["temp"], prompt=config["prompt"])
        self.stream = config["stream"]

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
            mode=self.mode,  
            stream=self.stream,
            render_output=sys.stdout.isatty(),
            show_thinking=self.args.thinking
        )

    def generate_config(self, temp=0.7, prompt=DEFAULT):
        return {"temperature": temp, "system": prompt}

