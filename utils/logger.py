import logging
from config.settings import LOGGING,LOGGING_LEVEL

class Logger:
    _logger = None
    LEVELS = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL,
    }
    
    _logging_enabled = LOGGING

    @classmethod
    def get_logger(cls, name="deepshell", level=LOGGING_LEVEL, log_file="deepshell.log"):
        """Returns a logger instance with a selectable log level, logging only to a file."""
        if cls._logger is None:
            cls._logger = logging.getLogger(name)
            log_level = cls.LEVELS.get(level.lower(), logging.INFO)
            cls._logger.setLevel(log_level)
            
            # File handler (logs to a file only)
            file_handler = logging.FileHandler(log_file)
            file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(file_formatter)
            cls._logger.addHandler(file_handler)
            
        return cls._logger
