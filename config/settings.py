from config.system_prompts import *
from enum import Enum, auto

class Mode(Enum):
    DEFAULT = auto()
    CODE = auto()
    SHELL = auto()
    SYSTEM = auto()
  
# Settings
DEFAULT_MODEL = "deepseek-r1:14b"
DEFAULT_HOST = "http://localhost:11434"
CODE_MODEL = "deepseek-coder-v2:16b"
SHELL_MODEL = "deepseek-coder-v2:16b"

# Mapping Mode to Configuration
MODE_CONFIGS = {
    Mode.DEFAULT: {"model": DEFAULT_MODEL, "temp": 0.6, "prompt": "", "stream": True},
    Mode.CODE:    {"model": CODE_MODEL, "temp": 0.5, "prompt": CODE, "stream": True},
    Mode.SHELL:   {"model": SHELL_MODEL, "temp": 0.4, "prompt": SHELL, "stream": True},
    Mode.SYSTEM:  {"model": SHELL_MODEL, "temp": 0.5, "prompt": SYSTEM, "stream": True},
}


