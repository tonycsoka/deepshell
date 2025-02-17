#FileProcessing Config 

SUPPORTED_EXTENSIONS = [
    # General text formats
    '.txt', '.md', '.json', '.csv', '.ini', '.cfg', '.xml',  
    '.yaml', '.yml', '.toml', '.log', '.sql', '.html', '.htm',  
    '.css', '.js', '.conf', '.properties', '.rst',

    # Programming languages
    '.py', '.c', '.cpp', '.h', '.hpp', '.java', '.cs', '.rs', '.go',  
    '.rb', '.php', '.sh', '.bat', '.pl', '.lua', '.swift', '.kt', '.m',  
    '.r', '.jl', '.dart', '.ts', '.v', '.scala', '.fs', '.asm', '.s',  
    '.vbs', '.ps1', '.clj', '.groovy', '.perl', '.f90', '.f95', '.ml'
]

IGNORED_FOLDERS =  ['__pycache__', '.git', '.svn', '.hg']

#Processing large text files
MAX_FILE_SIZE = 3 * 1024 * 1024
MAX_LINES = 600
CHUNK_SIZE = 4000

