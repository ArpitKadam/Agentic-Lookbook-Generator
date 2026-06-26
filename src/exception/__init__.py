import sys
import traceback
from types import ModuleType
from src.logger import logger

class CustomException(Exception):
    def __init__(self, error_message: str, error_details: ModuleType):
        """
        Custom Exception wrapper that automatically parses tracebacks and logs errors.
        
        :param error_message: Custom text description of the error.
        :param error_details: The active 'sys' module passed from the except block.
        """
        super().__init__(error_message)
        self.error_message = error_message

        exc_type, exc_value, exc_tb = error_details.exc_info()

        if exc_tb:
            self.filename = exc_tb.tb_frame.f_code.co_filename
            self.lineno = exc_tb.tb_lineno
            self.traceback_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        else:
            self.filename = "Unknown"
            self.lineno = -1
            self.traceback_str = "No Traceback available."

        logger.error(self.__str__())
        logger.error(f"Full Stack Trace:\n{self.traceback_str}")

    def __str__(self) -> str:
        return (
            f"\n[EXCEPTION CAUGHT]\n"
            f"File    : {self.filename}\n"
            f"Line    : {self.lineno}\n"
            f"Error   : {self.error_message}\n"
            f"----------------------------------------"
        )
