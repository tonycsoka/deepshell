import logging
from ui.printer import printer
from config.settings import LOG, LOG_LEVEL, LOG_TO_FILE, LOG_TO_UI

class Logger:
    _logger = None
    LEVELS = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL,
    }

    _logging_enabled = LOG
    _use_fancy_print = LOG_TO_UI 
    _use_file_handler = LOG_TO_FILE

    @classmethod
    def get_logger(cls, name="deepshell", level=LOG_LEVEL, log_file="deepshell.log"):
        """Returns a logger instance with a selectable log level, logging only to a file."""
        if cls._logger is None and cls._logging_enabled:
            cls._logger = logging.getLogger(name)
            log_level = cls.LEVELS.get(level.lower(), logging.INFO)
            cls._logger.setLevel(log_level)
 
            if cls._use_file_handler:
                file_handler = logging.FileHandler(log_file)
                file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                file_handler.setFormatter(file_formatter)
                cls._logger.addHandler(file_handler)

            if cls._use_fancy_print:
                cls._logger.addHandler(FancyPrintHandler())

        return cls._logger


class FancyPrintHandler(logging.Handler):
    def __init__(self):
        super().__init__()
      
    def emit(self, record):
        """Emit the log record using fancy_print."""
        try:
            msg = self.format(record)
            printer(msg)
        except Exception:
            self.handleError(record)
