import logging
import os
from datetime import datetime

def setup_logging():
    """
    Sets up logging to output to both console and a file.
    """
    log_directory = "logs"
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    log_filename = datetime.now().strftime("bot_%Y-%m-%d_%H-%M-%S.log")
    log_filepath = os.path.join(log_directory, log_filename)

    # Create logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO) # Set default logging level

    # Create console handler and set level to info
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Create file handler and set level to debug
    file_handler = logging.FileHandler(log_filepath)
    file_handler.setLevel(logging.DEBUG) # File will capture more detailed logs
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    logging.info(f"Logging initialized. Logs will be saved to {log_filepath}")
    return logger

# Example usage (for testing this module directly)
if __name__ == '__main__':
    logger = setup_logging()
    logger.debug("This is a debug message.")
    logger.info("This is an info message.")
    logger.warning("This is a warning message.")
    logger.error("This is an error message.")
    logger.critical("This is a critical message.")
