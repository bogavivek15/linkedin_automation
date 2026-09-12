"""
Tests for Application Question Answering and Sensitivity Protection.
"""

from apps.api.app.domain.application.answers import generate_application_answer
from apps.api.app.domain.application.claims import VerifiedClaimIndex


def test_answer_sensitive_question_blocks_automation():
    index = VerifiedClaimIndex()
    profile = {"full_name": "Jane"}
    job = {"title": "SWE"}

    sensitive_q = "Please provide your bank account number and IFSC code for direct deposit."
    ans = generate_application_answer(sensitive_q, profile, job, index)

    assert ans.requires_verification is True
    assert ans.confidence == "LOW"
    assert "SENSITIVE" in ans.answer


def test_answer_salary_question_with_preference():
    index = VerifiedClaimIndex()
    profile = {"full_name": "Jane"}
    job = {"title": "SWE"}
    prefs = {"minimum_salary": 95000.0}

    salary_q = "What is your desired base salary expectation?"
    ans = generate_application_answer(salary_q, profile, job, index, preferences=prefs)

    assert ans.requires_verification is False
    assert "$95000" in ans.answer
    assert ans.confidence == "HIGH"


def test_answer_salary_question_without_preference():
    index = VerifiedClaimIndex()
    profile = {"full_name": "Jane"}
    job = {"title": "SWE"}

    salary_q = "What is your target salary?"
    ans = generate_application_answer(salary_q, profile, job, index, preferences={})

    assert ans.requires_verification is True
    assert ans.confidence == "LOW"


def test_answer_work_authorization_unverified():
    index = VerifiedClaimIndex()
    profile = {"full_name": "Jane"}
    job = {"title": "SWE"}

    work_auth_q = "Are you legally authorized to work in the country of employment?"
    ans = generate_application_answer(work_auth_q, profile, job, index, preferences={})

    assert ans.requires_verification is True
    assert "UNVERIFIED" in ans.answer


def test_answer_unverified_skill_question():
    index = VerifiedClaimIndex()  # Has no docker claim
    profile = {"full_name": "Jane"}
    job = {"title": "SWE"}

    docker_q = "Describe your experience with Docker."
    ans = generate_application_answer(docker_q, profile, job, index)

    assert ans.requires_verification is True
    assert "UNVERIFIED" in ans.answer
    assert "Docker" in ans.verification_reason
