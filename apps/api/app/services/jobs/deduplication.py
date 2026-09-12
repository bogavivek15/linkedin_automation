import hashlib
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


def compute_description_hash(cleaned_description: str) -> str:
    """
    Deterministic SHA-256 fingerprint of the normalized job description.
    """
    canonical = " ".join(cleaned_description.lower().split())
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def canonicalize_application_url(url: str | None) -> str | None:
    """
    Remove marketing tracking parameters (utm_*, ref, source, fbclid, etc.)
    so the same destination URL matches across different aggregators.
    """
    if not url:
        return None

    try:
        parsed = urlparse(url.strip())
        if not parsed.netloc:
            return url.strip()

        query_params = parse_qs(parsed.query, keep_blank_values=False)
        # Filter out tracking query keys
        filtered_params = {
            k: v
            for k, v in query_params.items()
            if not (
                k.lower().startswith("utm_")
                or k.lower() in ("ref", "source", "fbclid", "gclid", "mc_cid", "mc_eid")
            )
        }

        new_query = urlencode(filtered_params, doseq=True)
        # Reconstruct URL without tracking params and lowercase scheme/host
        return urlunparse(
            (
                parsed.scheme.lower(),
                parsed.netloc.lower(),
                parsed.path.rstrip("/"),
                parsed.params,
                new_query,
                "",  # remove fragment
            )
        )
    except Exception:
        return url.strip()


def are_jobs_duplicate(
    job_a_source: str,
    job_a_ext_id: str,
    job_a_url: str | None,
    job_a_company_norm: str,
    job_a_title_norm: str,
    job_a_desc_hash: str,
    job_b_source: str,
    job_b_ext_id: str,
    job_b_url: str | None,
    job_b_company_norm: str,
    job_b_title_norm: str,
    job_b_desc_hash: str,
) -> bool:
    """
    Multi-signal weighted duplicate check:
    1. Exact source + external_id match -> True
    2. Canonical application URL match -> True
    3. Exact company + title + description fingerprint match -> True
    Otherwise -> False
    """
    # 1. Exact source + ID match
    if job_a_source.upper() == job_b_source.upper() and job_a_ext_id == job_b_ext_id:
        return True

    # 2. Canonical application URL match (if both present and non-trivial)
    canon_a = canonicalize_application_url(job_a_url)
    canon_b = canonicalize_application_url(job_b_url)
    if canon_a and canon_b and canon_a == canon_b:
        return True

    # 3. Composite match: same normalized company, same normalized title, same description hash
    if (
        job_a_company_norm
        and job_b_company_norm
        and job_a_company_norm == job_b_company_norm
        and job_a_title_norm
        and job_b_title_norm
        and job_a_title_norm == job_b_title_norm
        and job_a_desc_hash
        and job_b_desc_hash
        and job_a_desc_hash == job_b_desc_hash
    ):
        return True

    return False
