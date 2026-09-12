from apps.api.app.domain.job.models import EmploymentType, WorkMode
from apps.api.app.services.jobs.extraction import extract_requirements, extract_skills_from_text
from apps.api.app.services.jobs.normalization import (
    clean_description,
    normalize_company,
    normalize_datetime,
    normalize_employment_type,
    normalize_location,
    normalize_salary,
    normalize_title,
    normalize_work_mode,
)


def test_title_normalization():
    cleaned, normalized = normalize_title("Senior AI Engineer [Remote] - (Urgent)")
    assert cleaned == "Senior AI Engineer"
    assert normalized == "senior ai engineer"

    cleaned2, normalized2 = normalize_title("Full-Stack Developer (H/F)")
    assert cleaned2 == "Full-Stack Developer"
    assert "full stack developer" in normalized2 or "full-stack developer" in normalized2


def test_company_normalization():
    cleaned, normalized = normalize_company("Alpha Data Corp Inc.")
    assert cleaned == "Alpha Data Corp Inc."
    assert normalized == "alpha data"

    _, norm2 = normalize_company("Innovatech Solutions Pvt Ltd")
    assert norm2 == "innovatech"

    _, norm3 = normalize_company("Acme LLC")
    assert norm3 == "acme"


def test_location_normalization():
    assert normalize_location(None) == "Remote"
    assert normalize_location("Anywhere") == "Remote"
    assert normalize_location(["US", "Canada"]) == "US, Canada"
    assert normalize_location("Bengaluru, India") == "Bengaluru, India"


def test_work_mode_normalization():
    assert normalize_work_mode("Hybrid", "New York") == WorkMode.HYBRID
    assert normalize_work_mode("On-site", "London") == WorkMode.ONSITE
    assert normalize_work_mode(None, "Remote - US") == WorkMode.REMOTE


def test_employment_type_normalization():
    assert normalize_employment_type("Full Time") == EmploymentType.FULL_TIME
    assert normalize_employment_type("Contract") == EmploymentType.CONTRACT
    assert normalize_employment_type(["Internship"]) == EmploymentType.INTERNSHIP
    assert normalize_employment_type("Part-time") == EmploymentType.PART_TIME


def test_salary_normalization_never_fabricates():
    # If missing, stays None
    s_min, s_max, curr = normalize_salary(None, None, None)
    assert s_min is None
    assert s_max is None
    assert curr == "USD"

    # Direct valid numbers
    s_min, s_max, curr = normalize_salary("100000", "140000", "EUR")
    assert s_min == 100000.0
    assert s_max == 140000.0
    assert curr == "EUR"

    # Hourly rate conversion
    s_min, s_max, _ = normalize_salary(50, 75, period="hourly")
    assert s_min == 100000.0
    assert s_max == 150000.0


def test_datetime_normalization():
    dt = normalize_datetime("2026-03-01T10:00:00Z")
    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 3
    assert dt.day == 1

    assert normalize_datetime("invalid-date-string") is None
    assert normalize_datetime(None) is None


def test_description_cleaning_preserves_content():
    raw_html = (
        "<script>alert('xss');</script>"
        "<p>We are seeking a <strong>Python Developer</strong>.</p>"
        "<ul><li>FastAPI &amp; PostgreSQL</li><li>Docker</li></ul>"
        "<div>Apply now &nbsp; please.</div>"
    )
    cleaned = clean_description(raw_html)
    assert "alert" not in cleaned
    assert "Python Developer" in cleaned
    assert "FastAPI & PostgreSQL" in cleaned
    assert "Docker" in cleaned
    assert "Apply now please." in cleaned


def test_skill_extraction_and_alias_normalization():
    text = "We require ReactJS, TypeScript, Postgres, and Docker."
    skills = extract_skills_from_text(text)
    assert "react" in skills
    assert "typescript" in skills
    assert "postgresql" in skills
    assert "docker" in skills


def test_requirements_and_preferred_skills_separation():
    desc = (
        "We are looking for an engineer with 4+ years of experience.\n"
        "Requirements:\n"
        "- Strong Python and FastAPI skills\n"
        "- PostgreSQL and Docker\n"
        "Nice to have:\n"
        "- Kubernetes, Redis, and AWS\n"
    )
    req, pref, exp = extract_requirements(desc)
    assert exp == 4.0
    assert "python" in req
    assert "fastapi" in req
    assert "postgresql" in req
    assert "docker" in req

    assert "kubernetes" in pref
    assert "redis" in pref
    assert "aws" in pref
    # Preferred must not include required
    assert "python" not in pref
