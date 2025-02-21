from config.system_prompts import *
from enum import Enum, auto

class Mode(Enum):
    DEFAULT = auto()
    ADVANCED = auto()
    CODE = auto()
    SHELL = auto()
    SYSTEM = auto()
    HELPER = auto()
    VISION = auto()
    EMBEDDING = auto()
  
# Settings
DEFAULT_HOST = "http://localhost:11434"

DEFAULT_MODEL = "deepseek-r1:7b"
ADVANCED_MODEL = "deepseek-r1:14b"
CODE_MODEL = "deepseek-coder-v2:16b"
SHELL_MODEL = "deepseek-coder-v2:16b"
HELPER_MODEL = "deepseek-r1:1.5b"
VISION_MODEL = "llama3.2-vision:11b"
EMBEDDING_MODEL = "nomic-embed-text:latest"

# Mapping Mode to Configuration
MODE_CONFIGS = {
    Mode.DEFAULT: {"model": DEFAULT_MODEL, "temp": 0.4, "prompt": "", "stream": True},
    Mode.ADVANCED: {"model": ADVANCED_MODEL, "temp": 0.5, "prompt": "", "stream": True},
    Mode.CODE:    {"model": CODE_MODEL, "temp": 0.5, "prompt": CODE, "stream": True},
    Mode.SHELL:   {"model": SHELL_MODEL, "temp": 0.4, "prompt": SHELL, "stream": True},
    Mode.SYSTEM:  {"model": SHELL_MODEL, "temp": 0.5, "prompt": SYSTEM, "stream": True},
    Mode.HELPER:  {"model": HELPER_MODEL, "temp": 0.2, "prompt": HELPER, "stream": False},
    Mode.VISION:  {"model": VISION_MODEL, "temp": 0.6, "prompt": "", "stream": False},
    Mode.EMBEDDING:  {"model": EMBEDDING_MODEL, "temp": 0.5, "prompt": "", "stream": False},
}



