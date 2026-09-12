from apps.api.app.services.jobs.deduplication import (
    are_jobs_duplicate,
    canonicalize_application_url,
    compute_description_hash,
)


def test_compute_description_hash_deterministic():
    desc_1 = "Build FastAPI services.\n5+ years experience."
    desc_2 = "build fastapi services. 5+ years experience.   "
    h1 = compute_description_hash(desc_1)
    h2 = compute_description_hash(desc_2)
    assert h1 == h2
    assert len(h1) == 64


def test_canonicalize_application_url_removes_tracking():
    url_with_tracking = (
        "https://company.com/jobs/123/?utm_source=linkedin&utm_medium=cpc&ref=aggregator&source=jobicy"
    )
    clean = canonicalize_application_url(url_with_tracking)
    assert clean == "https://company.com/jobs/123"
    assert "utm_" not in clean
    assert "ref=" not in clean


def test_duplicate_on_exact_source_and_external_id():
    is_dup = are_jobs_duplicate(
        job_a_source="HIMALAYAS",
        job_a_ext_id="guid-123",
        job_a_url="https://site.com/apply",
        job_a_company_norm="acme",
        job_a_title_norm="engineer",
        job_a_desc_hash="hash1",
        job_b_source="HIMALAYAS",
        job_b_ext_id="guid-123",
        job_b_url="https://diff.com/apply",
        job_b_company_norm="different",
        job_b_title_norm="diff title",
        job_b_desc_hash="hash2",
    )
    assert is_dup is True


def test_duplicate_on_canonical_application_url():
    is_dup = are_jobs_duplicate(
        job_a_source="HIMALAYAS",
        job_a_ext_id="him-1",
        job_a_url="https://careers.google.com/jobs/results/456/?utm_source=himalayas",
        job_a_company_norm="google",
        job_a_title_norm="swe",
        job_a_desc_hash="hash1",
        job_b_source="JOBICY",
        job_b_ext_id="jobicy-2",
        job_b_url="https://careers.google.com/jobs/results/456/?ref=jobicy",
        job_b_company_norm="google",
        job_b_title_norm="software engineer",
        job_b_desc_hash="hash2",
    )
    assert is_dup is True


def test_duplicate_on_company_title_and_description_hash():
    desc = "Build backend services in Python"
    d_hash = compute_description_hash(desc)

    is_dup = are_jobs_duplicate(
        job_a_source="HIMALAYAS",
        job_a_ext_id="him-1",
        job_a_url=None,
        job_a_company_norm="alpha data",
        job_a_title_norm="backend engineer",
        job_a_desc_hash=d_hash,
        job_b_source="JOBICY",
        job_b_ext_id="jobicy-2",
        job_b_url=None,
        job_b_company_norm="alpha data",
        job_b_title_norm="backend engineer",
        job_b_desc_hash=d_hash,
    )
    assert is_dup is True


def test_distinct_jobs_not_merged():
    # Same company, different role
    is_dup1 = are_jobs_duplicate(
        job_a_source="HIMALAYAS",
        job_a_ext_id="him-1",
        job_a_url="https://company.com/jobs/backend",
        job_a_company_norm="alpha data",
        job_a_title_norm="backend engineer",
        job_a_desc_hash="hash1",
        job_b_source="HIMALAYAS",
        job_b_ext_id="him-2",
        job_b_url="https://company.com/jobs/frontend",
        job_b_company_norm="alpha data",
        job_b_title_norm="frontend engineer",
        job_b_desc_hash="hash2",
    )
    assert is_dup1 is False

    # Same role, different company
    is_dup2 = are_jobs_duplicate(
        job_a_source="HIMALAYAS",
        job_a_ext_id="him-1",
        job_a_url="https://alpha.com/jobs/backend",
        job_a_company_norm="alpha data",
        job_a_title_norm="backend engineer",
        job_a_desc_hash="hash1",
        job_b_source="JOBICY",
        job_b_ext_id="jobicy-2",
        job_b_url="https://beta.com/jobs/backend",
        job_b_company_norm="beta labs",
        job_b_title_norm="backend engineer",
        job_b_desc_hash="hash1",
    )
    assert is_dup2 is False
