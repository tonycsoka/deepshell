from enum import Enum, auto
from config.system_prompts import *

class Mode(Enum):
    DEFAULT = auto()
    ADVANCED = auto()
    CODE = auto()
    SHELL = auto()
    SYSTEM = auto()
    VISION = auto()

# Settings
DEFAULT_HOST = "http://localhost:11434"

DEFAULT_MODEL = "deepseek-r1:14b"
CODE_MODEL = "deepseek-coder-v2:16b"
SHELL_MODEL = "deepseek-coder-v2:16b"
VISION_MODEL = "llama3.2-vision:11b"
EMBEDDING_MODEL = "nomic-embed-text:latest"

# Mapping Mode to Configuration
MODE_CONFIGS = {
    Mode.DEFAULT: {"model": DEFAULT_MODEL, "temp": 0.4, "prompt": "", "stream": True},
    Mode.CODE:    {"model": CODE_MODEL, "temp": 0.5, "prompt": CODE, "stream": True},
    Mode.SHELL:   {"model": SHELL_MODEL, "temp": 0.4, "prompt": SHELL, "stream": True},
    Mode.SYSTEM:  {"model": SHELL_MODEL, "temp": 0.5, "prompt": SYSTEM, "stream": True},
    Mode.VISION:  {"model": VISION_MODEL, "temp": 0.6, "prompt": "", "stream": False},

}

#Logging
LOGGING = True
LOGGING_LEVEL = "info"

#FileProcessing Config 
PROCESS_IMAGES = False


#Processing large text files

MAX_FILE_SIZE = 3 * 1024 * 1024 #3MB
MAX_LINES = 600
CHUNK_SIZE = 4000

SUPPORTED_EXTENSIONS = [
    # General text formats
    '.txt', '.md', '.json', '.csv', '.ini', '.cfg', '.xml',  
    '.yaml', '.yml', '.toml', '.log', '.sql', '.html', '.htm',  
    '.css', '.js', '.conf', '.properties', '.rst',

    # Programming languages
    '.py', '.c', '.cpp', '.h', '.hpp', '.java', '.cs', '.rs', '.go',  
    '.rb', '.php', '.sh', '.bat', '.pl', '.lua', '.swift', '.kt', '.m',  
    '.r', '.jl', '.dart', '.ts', '.v', '.scala', '.fs', '.asm', '.s',  
    '.vbs', '.ps1', '.clj', '.groovy', '.perl', '.f90', '.f95', '.ml',
    
    # Image formats
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.svg'
]

IGNORED_FOLDERS =  ['__pycache__', '.git', '.svn', '.hg', 'android-studio', 'miniconda3']


