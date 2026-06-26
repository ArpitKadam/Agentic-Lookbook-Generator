import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
import colorlog


class Logger:
    _logger_instance = None

    @classmethod
    def get_logger(cls, name="Agentic LookBook Logger"):
        if cls._logger_instance is None:
            logs_dir = os.path.join(os.getcwd(), "logs")
            os.makedirs(logs_dir, exist_ok=True)

            log_filename = f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
            log_file_path = os.path.join(logs_dir, log_filename)

            logger = logging.getLogger(name)
            logger.setLevel(logging.DEBUG)
            logger.propagate = False

            if not logger.handlers:

                file_handler = RotatingFileHandler(log_file_path, maxBytes=5 * 1024 * 1024, backupCount=3)
                file_formatter = logging.Formatter(
                    fmt="[%(asctime)s] %(lineno)4d | %(levelname)-8s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S"
                )
                file_handler.setFormatter(file_formatter)
                logger.addHandler(file_handler)

                console_handler = logging.StreamHandler()

                console_formatter = colorlog.ColoredFormatter(
                    fmt="%(log_color)s[%(asctime)s] %(lineno)4d | %(levelname)-8s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                    log_colors={
                        'DEBUG': 'cyan',
                        'INFO': 'green',
                        'WARNING': 'yellow',
                        'ERROR': 'red',
                        'CRITICAL': 'bold_red',
                    }
                )
                
                console_handler.setFormatter(console_formatter)
                logger.addHandler(console_handler)

            cls._logger_instance = logger

        return cls._logger_instance


logger = Logger.get_logger("Agentic LookBook Logger")

if __name__ == "__main__":
    logger.info("Logger initialized successfully.")