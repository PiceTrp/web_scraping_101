import logging

def setup_logging(log_file="output.log", level=logging.INFO):
    """
    Sets up a logger to output messages to both console and a file.

    Args:
        log_file (str): The name of the log file.
        level (int): The logging level (e.g., logging.INFO, logging.DEBUG).

    Returns:
        logging.Logger: The configured logger instance.
    """
    # Create a logger
    logger = logging.getLogger(__name__)
    logger.setLevel(level)

    # Prevent adding multiple handlers if the function is called multiple times
    if not logger.handlers:
        # Create file handler which logs even debug messages
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)

        # Create console handler with a higher log level
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)

        # Create formatter and add it to the handlers
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Add the handlers to the logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger

LOGGER = setup_logging()

# Example usage (optional, for testing logger_config.py directly)
# if __name__ == "__main__":
#     my_logger = setup_logging()
#     my_logger.info("This is an info message from logger_config.py")
#     my_logger.warning("This is a warning message from logger_config.py")
#     my_logger.error("This is an error message from logger_config.py")