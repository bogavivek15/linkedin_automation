"""
CareerOS Phase 9 — Application Safety Unit Tests.

Validates that sensitive fields (OTP, CAPTCHA, 2FA, credentials, payments)
and unauthorized execution modes are reliably detected and block autonomous application.
"""

from apps.api.app.domain.decision.models import ApplicationContext
from apps.api.app.domain.decision.risk import (
    detect_sensitive_application_signals,
    is_application_safe_for_automation,
)


def test_detect_otp_in_context():
    """Detects OTP requirements in context or URL/text."""
    ctx = ApplicationContext(
        application_url="https://jobs.example.com/apply?step=verify_otp",
        execution_mode="API",
    )
    signals = detect_sensitive_application_signals(ctx)
    assert "OTP_SUBMISSION" in signals

    is_safe, blockers = is_application_safe_for_automation(ctx, signals)
    assert is_safe is False
    assert any("OTP_SUBMISSION" in b for b in blockers)


def test_detect_captcha_challenge():
    """Detects CAPTCHA challenges."""
    ctx = ApplicationContext(
        application_url="https://company.recruitee.com/apply",
        execution_mode="API",
        sensitive_signals=["CAPTCHA_CHALLENGE"],
    )
    signals = detect_sensitive_application_signals(ctx, ["Please complete the hCaptcha before submitting."])
    assert "CAPTCHA_CHALLENGE" in signals

    is_safe, blockers = is_application_safe_for_automation(ctx, signals)
    assert is_safe is False
    assert any("CAPTCHA_CHALLENGE" in b for b in blockers)


def test_detect_banking_and_payment_requests():
    """Detects bank accounts, credit cards, or application fees."""
    ctx = ApplicationContext(
        application_url="https://apply.example.com/fees",
        execution_mode="API",
    )
    signals = detect_sensitive_application_signals(
        ctx,
        ["A mandatory registration fee of $50 is required alongside your bank account number."],
    )
    assert "BANK_DETAILS" in signals
    assert "PAYMENT_FEE" in signals

    is_safe, _ = is_application_safe_for_automation(ctx, signals)
    assert is_safe is False


def test_unauthorized_execution_mode_blocks_automation():
    """External web pages requiring user interaction (USER_HANDOFF) cannot be auto-applied."""
    ctx = ApplicationContext(
        application_url="https://careers.workday.com/job/123",
        execution_mode="USER_HANDOFF",
    )
    signals = detect_sensitive_application_signals(ctx)
    is_safe, blockers = is_application_safe_for_automation(ctx, signals)
    assert is_safe is False
    assert "unauthorized_execution_mode:USER_HANDOFF" in blockers


def test_clean_api_mode_passes():
    """An authorized API without sensitive requirements passes safety checks."""
    ctx = ApplicationContext(
        application_url="https://api.greenhouse.io/v1/boards/example/jobs/123",
        execution_mode="API",
        requires_sensitive_info=False,
    )
    signals = detect_sensitive_application_signals(ctx)
    assert len(signals) == 0

    is_safe, blockers = is_application_safe_for_automation(ctx, signals)
    assert is_safe is True
    assert len(blockers) == 0
