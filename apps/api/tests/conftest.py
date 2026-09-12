import pytest
from apps.api.app.core.config import settings
from apps.api.app.main import app
from apps.api.app.repositories.decision_repository import DecisionRepository
from apps.api.app.repositories.match_repository import MatchRepository
from apps.api.app.repositories.resume_repository import ResumeRepository
from apps.api.app.services.embedding.service import EmbeddingService
from apps.api.tests.fixtures.generator import (
    create_malformed_pdf,
    create_minimal_resume_pdf,
    create_multi_column_resume_pdf,
    create_prompt_injection_resume_pdf,
    create_resume_docx,
    create_resume_txt,
    create_standard_resume_pdf,
)
from fastapi.testclient import TestClient

# Ensure test mode for deterministic mock embedding execution
settings.app_env = "test"


@pytest.fixture(autouse=True)
def clean_repository_store():
    ResumeRepository.reset_store()
    MatchRepository.reset_store()
    DecisionRepository.reset_store()
    EmbeddingService.reset_cache()
    yield
    ResumeRepository.reset_store()
    MatchRepository.reset_store()
    DecisionRepository.reset_store()
    EmbeddingService.reset_cache()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_pdf_bytes():
    return create_standard_resume_pdf()


@pytest.fixture
def multi_column_pdf_bytes():
    return create_multi_column_resume_pdf()


@pytest.fixture
def minimal_pdf_bytes():
    return create_minimal_resume_pdf()


@pytest.fixture
def sample_docx_bytes():
    return create_resume_docx()


@pytest.fixture
def sample_txt_bytes():
    return create_resume_txt()


@pytest.fixture
def malformed_pdf_bytes():
    return create_malformed_pdf()


@pytest.fixture
def prompt_injection_pdf_bytes():
    return create_prompt_injection_resume_pdf()
