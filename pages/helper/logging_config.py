"""
Comprehensive logging configuration for the application.
"""
import logging
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
import traceback


class LoggerSetup:
    """Centralized logging configuration."""
    
    @staticmethod
    def setup_logging(
        log_level: str = "INFO",
        log_file: Optional[str] = None,
        log_dir: str = "logs"
    ):
        """
        Setup comprehensive logging for the application.
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Optional log file name
            log_dir: Directory for log files
        """
        # Create logs directory if it doesn't exist
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)
        
        # Generate log file name if not provided
        if not log_file:
            log_file = f"app_{datetime.now().strftime('%Y%m%d')}.log"
        
        log_file_path = log_path / log_file
        
        # Configure logging format
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        date_format = '%Y-%m-%d %H:%M:%S'
        
        # Convert string log level to logging constant
        numeric_level = getattr(logging, log_level.upper(), logging.INFO)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)
        
        # Remove existing handlers
        root_logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_formatter = logging.Formatter(log_format, date_format)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # File handler
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setLevel(numeric_level)
        file_formatter = logging.Formatter(log_format, date_format)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        # Error file handler (for errors and above)
        error_file_handler = logging.FileHandler(log_path / f"error_{log_file}")
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(file_formatter)
        root_logger.addHandler(error_file_handler)
        
        logging.info(f"Logging initialized - Level: {log_level}, File: {log_file_path}")
        
        return root_logger


class ErrorHandler:
    """Centralized error handling with logging."""
    
    @staticmethod
    def handle_error(
        error: Exception,
        context: str = "",
        logger: Optional[logging.Logger] = None,
        reraise: bool = False,
        user_message: str = "An error occurred. Please try again later."
    ):
        """
        Handle errors with proper logging and user feedback.
        
        Args:
            error: The exception that occurred
            context: Additional context about where the error occurred
            logger: Logger instance to use
            reraise: Whether to reraise the exception
            user_message: User-friendly error message
        """
        if logger is None:
            logger = logging.getLogger(__name__)
        
        # Log the error with full traceback
        error_msg = f"{context}: {str(error)}" if context else str(error)
        logger.error(f"Error occurred: {error_msg}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # In a Streamlit context, show user-friendly message
        try:
            import streamlit as st
            st.error(f"❌ {user_message}")
            if logger.level <= logging.DEBUG:
                with st.expander("Technical Details"):
                    st.code(traceback.format_exc())
        except ImportError:
            pass
        
        if reraise:
            raise error
    
    @staticmethod
    def log_function_call(logger: logging.Logger, func_name: str, **kwargs):
        """Log function call with parameters."""
        params = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        logger.debug(f"Calling {func_name}({params})")
    
    @staticmethod
    def log_function_result(logger: logging.Logger, func_name: str, result, **kwargs):
        """Log function result."""
        logger.debug(f"{func_name} returned: {type(result).__name__}")
    
    @staticmethod
    def create_audit_log(
        action: str,
        user: str,
        details: str = "",
        logger: Optional[logging.Logger] = None
    ):
        """
        Create an audit log entry for important actions.
        
        Args:
            action: Action performed (e.g., "CASE_CREATED", "MATCH_FOUND")
            user: User who performed the action
            details: Additional details about the action
            logger: Logger instance to use
        """
        if logger is None:
            logger = logging.getLogger(__name__)
        
        audit_message = f"AUDIT: {action} by {user}"
        if details:
            audit_message += f" - {details}"
        
        logger.info(audit_message)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_exception(logger: logging.Logger, exception: Exception, context: str = ""):
    """
    Log an exception with context.
    
    Args:
        logger: Logger instance
        exception: Exception to log
        context: Additional context
    """
    error_msg = f"{context}: {str(exception)}" if context else str(exception)
    logger.error(error_msg, exc_info=True)


# Initialize logging on module import
def initialize_logging():
    """Initialize logging configuration."""
    log_level = os.getenv("LOG_LEVEL", "INFO")
    LoggerSetup.setup_logging(log_level=log_level)


# Auto-initialize logging when module is imported
initialize_logging()