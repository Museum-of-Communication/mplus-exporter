from datetime import datetime


class Logger:
    COLORS = {
        "INFO": "\033[39m",  # White/Default
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m",  # Red
        "SUCCESS": "\033[92m",  # Green
        "RESET": "\033[0m",  # Reset color
    }

    @staticmethod
    def log(text: str, type: str = "RESET"):
        """Prints text in a color depending on the type."""
        color = Logger.COLORS.get(type.upper(), Logger.COLORS["RESET"])
        timestamp = datetime.now()
        print(f"{timestamp} ===> {color}{text}{Logger.COLORS['RESET']}")
