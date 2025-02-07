import sys
from config.system_prompts import DEFAULT,CODE,SHELL
from ollama_client.api_client import OllamaClient


#Settings
DEFAULT_MODEL = "deepseek-r1:14b"
DEFAULT_HOST = "http://localhost:11434"


def generate_config(temp=0.7,prompt=DEFAULT):
    config = {
            "temperature": temp,
            "system": prompt,
    }
    return config

def generate_helper_config(supported_actions=["open","find","play"]) :
    
    system_prompt = f"""
    You are an AI that extracts user intent and target from messages.
    Your response must be in JSON format:
    {{"intent": "open file", "target": "config.json"}}

    Supported actions:
    - {', '.join(supported_actions)}

    If none of the actions were detected:
    - reply "None"

    """
    return generate_config(temp=0.6, prompt=system_prompt)

DEFAULT_CONFIG = generate_config(temp=0.6, prompt=DEFAULT)
CODE_CONFIG = generate_config(temp=0.5, prompt=CODE)
SHELL_CONFIG = generate_config(temp=0.4, prompt=SHELL)

def deploy_client(args):

    if args.shell:
        config = SHELL_CONFIG
        config_name = "shell"
    elif args.code: 
        config = CODE_CONFIG
        config_name = "code"
    else:
        config = DEFAULT_CONFIG
        config_name = "default"

    ollama_client = OllamaClient(
        host=args.host,
        model=args.model,
        config=config,
        config_name=config_name,
        stream=True,
        render_output= not sys.stdout.isatty(),
        show_thinking=args.thinking
    )
    return ollama_client
