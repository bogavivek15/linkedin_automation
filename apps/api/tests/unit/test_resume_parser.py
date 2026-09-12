import pytest
from apps.api.app.core.errors import CareerOSError
from apps.api.app.services.resume_service import ResumeService


def test_extract_text_from_standard_pdf(sample_pdf_bytes):
    text, pages = ResumeService.extract_text_from_pdf(sample_pdf_bytes)
    assert pages >= 1
    assert "Vivek Bogavalli" in text
    assert "Professional Summary" in text
    assert "Technical Skills" in text


def test_extract_text_from_multi_column_pdf(multi_column_pdf_bytes):
    text, pages = ResumeService.extract_text_from_pdf(multi_column_pdf_bytes)
    assert pages >= 1
    assert "alex@careeros.ai" in text
    assert "Core Competencies" in text
    assert "Lead Platform Engineer" in text


def test_extract_text_from_docx(sample_docx_bytes):
    text = ResumeService.extract_text_from_docx(sample_docx_bytes)
    assert "Vivek Bogavalli" in text
    assert "Technical Skills" in text
    assert "Horizon AI" in text
    assert "CareerOS Resume Intelligence" in text


def test_extract_text_from_txt(sample_txt_bytes):
    text = ResumeService.extract_text_from_txt(sample_txt_bytes)
    assert "VIVEK BOGAVALLI" in text
    assert "WORK EXPERIENCE" in text
    assert "LangGraph" in text


def test_reject_malformed_pdf(malformed_pdf_bytes):
    with pytest.raises(CareerOSError) as exc:
        ResumeService.extract_text_from_pdf(malformed_pdf_bytes)
    assert exc.value.code == "MALFORMED_DOCUMENT"


def test_section_detection_standard_headings():
    resume_text = """
    Vivek Bogavalli
    Email: vivek@example.com

    Summary
    Experienced AI and distributed systems engineer.

    Work Experience
    Senior AI Engineer at TechCo (2022-2024)
    - Architected scalable LangGraph pipelines

    Projects
    CareerOS Platform
    - Engineered verifiable claims engine

    Education
    B.S. in Computer Science (2020)

    Skills
    Python, FastAPI, TypeScript, PostgreSQL
    """
    sections = ResumeService.detect_sections(resume_text)
    assert "SUMMARY" in sections
    assert "EXPERIENCE" in sections
    assert "PROJECTS" in sections
    assert "EDUCATION" in sections
    assert "SKILLS" in sections


def test_section_detection_alternative_and_mixed_case_headings():
    resume_text = """
    Alex Smith

    ABOUT ME
    Passionate software engineer.

    EMPLOYMENT HISTORY
    Platform Engineer at GlobalCorp (2021-Present)
    - Managed Kubernetes clusters

    Technical Projects
    Distributed Cache
    - Built Redis cache with 99.9% hit rate

    ACADEMIC BACKGROUND
    Master in Information Systems, 2021

    CORE COMPETENCIES
    Go, Docker, Kubernetes, AWS

    HONORS & AWARDS
    Engineering Excellence Award 2023

    CERTIFICATIONS
    AWS Certified Solutions Architect
    """
    sections = ResumeService.detect_sections(resume_text)
    assert "SUMMARY" in sections
    assert "EXPERIENCE" in sections
    assert "PROJECTS" in sections
    assert "EDUCATION" in sections
    assert "SKILLS" in sections
    assert "ACHIEVEMENTS" in sections
    assert "CERTIFICATIONS" in sections


def test_section_detection_missing_sections():
    # Only skills and education
    resume_text = """
    Candidate With No Experience

    Technical Skills
    Python, SQL

    Education
    University of Waterloo, 2024
    """
    sections = ResumeService.detect_sections(resume_text)
    assert "SKILLS" in sections
    assert "EDUCATION" in sections
    assert "EXPERIENCE" not in sections
    assert "PROJECTS" not in sections
