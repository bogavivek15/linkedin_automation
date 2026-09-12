import json
import logging
import re
import sys
from datetime import datetime, timezone

SENSITIVE_PATTERNS = [
    re.compile(r"(bearer\s+)[a-zA-Z0-9_\-\.]{10,}", re.IGNORECASE),
    re.compile(r'(["\']?(?:password|token|secret|cookie|otp|2fa|api_key)["\']?\s*[:=]\s*["\']?)([^"\'\s&,]+)', re.IGNORECASE),
]


def redact_sensitive_data(text: str) -> str:
    """
    Deterministically scrubs secrets, tokens, cookies, OTPs, and passwords from log strings.
    """
    cleaned = text
    for pattern in SENSITIVE_PATTERNS:
        cleaned = pattern.sub(r"\1[REDACTED]", cleaned)
    return cleaned


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        raw_msg = record.getMessage()
        safe_msg = redact_sensitive_data(raw_msg)

        log_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": safe_msg,
            "logger": record.name,
        }
        if hasattr(record, "request_id"):
            log_record["request_id"] = getattr(record, "request_id")
        if hasattr(record, "agent_run_id"):
            log_record["agent_run_id"] = getattr(record, "agent_run_id")
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)


def get_logger(name: str = "careeros") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


logger = get_logger()
