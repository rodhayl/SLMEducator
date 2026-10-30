"""
Logging service for SLMEducator
"""

import os
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
import structlog


class LoggingService:
    """Structured logging service"""

    def __init__(self):
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)

        # Configure structlog
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        # Set up file handlers
        self._setup_handlers()

    def _setup_handlers(self):
        """Set up logging handlers"""
        # Main application log
        main_handler = logging.FileHandler(self.log_dir / "slm_educator.log")
        main_handler.setLevel(logging.DEBUG)
        main_handler.setFormatter(logging.Formatter("%(message)s"))

        # Error log
        error_handler = logging.FileHandler(self.log_dir / "errors.log")
        error_handler.setLevel(logging.WARNING)
        error_handler.setFormatter(logging.Formatter("%(message)s"))

        # Console handler for development
        console_handler = logging.StreamHandler()
        console_level = logging.DEBUG if os.getenv("SLM_DEV_MODE") else logging.INFO
        console_handler.setLevel(console_level)
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(main_handler)
        root_logger.addHandler(error_handler)
        root_logger.addHandler(console_handler)

    def get_logger(self, name: str) -> structlog.BoundLogger:
        """Get a structured logger"""
        return structlog.get_logger(name)

    def log_event(
        self,
        logger_name: str,
        level: str,
        event_type: str,
        user_id: Optional[int] = None,
        **kwargs,
    ):
        """Log a structured event"""
        logger = self.get_logger(logger_name)

        log_data = {
            "event_type": event_type,
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **kwargs,
        }

        # Map level to logger method
        level_method = getattr(logger, level.lower(), logger.info)
        level_method(event_type, **log_data)

    def log_crud_operation(
        self,
        operation: str,
        entity: str,
        entity_id: Any,
        user_id: Optional[int] = None,
        **kwargs,
    ):
        """Log CRUD operation"""
        self.log_event(
            "crud",
            "INFO",
            f"crud.{operation}",
            user_id=user_id,
            entity=entity,
            entity_id=entity_id,
            **kwargs,
        )

    def log_auth_event(
        self,
        event: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        success: bool = True,
        **kwargs,
    ):
        """Log authentication event"""
        self.log_event(
            "auth",
            "INFO" if success else "WARNING",
            f"auth.{event}",
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            success=success,
            **kwargs,
        )

    def log_ai_operation(
        self,
        operation: str,
        provider: str,
        model: str,
        user_id: Optional[int] = None,
        success: bool = True,
        duration_ms: Optional[int] = None,
        **kwargs,
    ):
        """Log AI operation"""
        level = "INFO" if success else "ERROR"
        self.log_event(
            "ai",
            level,
            f"ai.{operation}",
            user_id=user_id,
            provider=provider,
            model=model,
            success=success,
            duration_ms=duration_ms,
            **kwargs,
        )

    def log_ui_event(
        self,
        event: str,
        component: str,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        **kwargs,
    ):
        """Log UI event"""
        self.log_event(
            "ui",
            "INFO",
            f"ui.{event}",
            user_id=user_id,
            component=component,
            action=action,
            **kwargs,
        )

    def log_error(
        self,
        error_type: str,
        error_message: str,
        user_id: Optional[int] = None,
        **kwargs,
    ):
        """Log error event"""
        self.log_event(
            "error",
            "ERROR",
            f"error.{error_type}",
            user_id=user_id,
            error_message=error_message,
            **kwargs,
        )

    def log_performance(
        self, operation: str, duration_ms: int, user_id: Optional[int] = None, **kwargs
    ):
        """Log performance metric"""
        self.log_event(
            "performance",
            "INFO",
            f"performance.{operation}",
            user_id=user_id,
            duration_ms=duration_ms,
            **kwargs,
        )

    def rotate_logs(self):
        """Rotate log files when they get too large (10MB limit)"""
        max_size = 10 * 1024 * 1024  # 10MB

        for log_file in ["slm_educator.log", "errors.log"]:
            log_path = self.log_dir / log_file
            if log_path.exists() and log_path.stat().st_size > max_size:
                # Rename old log
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = self.log_dir / f"{log_file}.{timestamp}"
                log_path.rename(backup_path)

                # Create new log file (will be created automatically by logger)


# Global logging service instance
_logging_service: Optional[LoggingService] = None


def get_logging_service() -> LoggingService:
    """Get the global logging service instance"""
    global _logging_service
    if _logging_service is None:
        _logging_service = LoggingService()
    return _logging_service


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a logger instance"""
    return get_logging_service().get_logger(name)
