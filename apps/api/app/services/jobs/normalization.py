import html
import re
from datetime import datetime, timezone
from typing import Any

from apps.api.app.domain.job.models import EmploymentType, WorkMode
from dateutil import parser as date_parser

# Regular expressions for cleaning
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_STYLE_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
MULTIPLE_SPACES_RE = re.compile(r"[ \t]+")
MULTIPLE_NEWLINES_RE = re.compile(r"\n\s*\n+")

COMPANY_SUFFIX_RE = re.compile(
    r"\b(inc|inc\.|llc|l\.l\.c\.|ltd|ltd\.|pvt|pvt\.|pvt ltd|private limited|corp|corp\.|corporation|co\.|gmbh|technologies|solutions)\b",
    re.IGNORECASE,
)

TITLE_PREFIX_SUFFIX_RE = re.compile(
    r"(\[[^\]]+\]|\([^\)]*(remote|h/f|m/f/d|urgent|full[- ]?time|part[- ]?time|contract)[^\)]*\))",
    re.IGNORECASE,
)


def normalize_title(raw_title: str) -> tuple[str, str]:
    """
    Returns: (cleaned_title, normalized_title)
    cleaned_title: Display title without annoying brackets/tags
    normalized_title: Lowercase alphanumeric representation for deduplication
    """
    if not raw_title:
        return ("Unknown Title", "unknown title")

    cleaned = TITLE_PREFIX_SUFFIX_RE.sub("", raw_title).strip()
    cleaned = MULTIPLE_SPACES_RE.sub(" ", cleaned).strip(" -:|")
    if not cleaned:
        cleaned = raw_title.strip()

    # Lowercase, remove special chars for indexing
    normalized = re.sub(r"[^a-z0-9\s]", " ", cleaned.lower())
    normalized = MULTIPLE_SPACES_RE.sub(" ", normalized).strip()

    return cleaned, normalized


def normalize_company(raw_company: str) -> tuple[str, str]:
    """
    Returns: (cleaned_company, normalized_company)
    cleaned_company: Preserved original proper casing
    normalized_company: Legal suffixes stripped, lowercase for deduplication
    """
    if not raw_company:
        return ("Unknown Company", "unknown company")

    cleaned = raw_company.strip()
    # Strip legal suffixes for deduplication
    normalized = COMPANY_SUFFIX_RE.sub("", cleaned)
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized.lower())
    normalized = MULTIPLE_SPACES_RE.sub(" ", normalized).strip()
    if not normalized:
        normalized = cleaned.lower()

    return cleaned, normalized


def normalize_location(raw_location: str | list[str] | None) -> str:
    """
    Normalize location, handling list restrictions or string variations.
    """
    if not raw_location:
        return "Remote"

    if isinstance(raw_location, list):
        filtered = [str(x).strip() for x in raw_location if str(x).strip()]
        return ", ".join(filtered) if filtered else "Remote"

    cleaned = str(raw_location).strip()
    if not cleaned or cleaned.lower() in ("anywhere", "worldwide", "remote", "global"):
        return "Remote"

    return cleaned


def normalize_work_mode(raw_mode: Any, raw_location: str | None = None) -> WorkMode:
    """
    Normalize work mode into controlled vocabulary (REMOTE, HYBRID, ONSITE, UNKNOWN).
    """
    combined = f"{raw_mode or ''} {raw_location or ''}".lower()

    if "hybrid" in combined:
        return WorkMode.HYBRID
    if "onsite" in combined or "on-site" in combined or "office" in combined:
        return WorkMode.ONSITE
    if "remote" in combined or "anywhere" in combined or "telecommute" in combined:
        return WorkMode.REMOTE

    return WorkMode.REMOTE  # Default for Himalayas and Jobicy remote feeds


def normalize_employment_type(raw_type: Any) -> EmploymentType:
    """
    Normalize employment type into controlled vocabulary.
    """
    if not raw_type:
        return EmploymentType.FULL_TIME

    if isinstance(raw_type, list) and raw_type:
        text = " ".join(str(x) for x in raw_type).lower()
    else:
        text = str(raw_type).lower()

    if "intern" in text:
        return EmploymentType.INTERNSHIP
    if "contract" in text or "freelance" in text:
        return EmploymentType.CONTRACT
    if "part" in text:
        return EmploymentType.PART_TIME
    if "temp" in text:
        return EmploymentType.TEMPORARY
    if "apprentice" in text:
        return EmploymentType.APPRENTICESHIP
    if "full" in text:
        return EmploymentType.FULL_TIME

    return EmploymentType.FULL_TIME


def normalize_salary(
    min_val: Any = None,
    max_val: Any = None,
    currency: str | None = None,
    period: str | None = None,
) -> tuple[float | None, float | None, str]:
    """
    Safely parse salary numbers. Never fabricates missing salaries.
    Annualizes hourly/monthly rates only if period is unambiguous.
    """
    s_min: float | None = None
    s_max: float | None = None
    curr = (currency or "USD").upper().strip()

    try:
        if min_val is not None:
            v = float(min_val)
            if v > 0:
                s_min = v
    except (ValueError, TypeError):
        pass

    try:
        if max_val is not None:
            v = float(max_val)
            if v > 0:
                s_max = v
    except (ValueError, TypeError):
        pass

    # Handle hourly / monthly periods if explicitly provided
    if period:
        p_lower = str(period).lower()
        if "hour" in p_lower:
            # e.g. $50/hr -> ~100k annual (2000 hours)
            if s_min and s_min < 1000:
                s_min = round(s_min * 2000, 2)
            if s_max and s_max < 1000:
                s_max = round(s_max * 2000, 2)
        elif "month" in p_lower:
            if s_min and s_min < 50000:
                s_min = round(s_min * 12, 2)
            if s_max and s_max < 50000:
                s_max = round(s_max * 12, 2)

    return s_min, s_max, curr


def normalize_datetime(raw_date: Any) -> datetime | None:
    """
    Parse ISO strings, timestamps, or RFC dates into timezone-aware UTC datetime.
    """
    if not raw_date:
        return None

    if isinstance(raw_date, datetime):
        if raw_date.tzinfo is None:
            return raw_date.replace(tzinfo=timezone.utc)
        return raw_date.astimezone(timezone.utc)

    # If epoch timestamp
    if isinstance(raw_date, (int, float)):
        try:
            return datetime.fromtimestamp(raw_date, tz=timezone.utc)
        except Exception:
            return None

    date_str = str(raw_date).strip()
    if not date_str:
        return None

    try:
        dt = date_parser.parse(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def clean_description(raw_html_or_text: str) -> str:
    """
    Clean job description:
    - Strips script and style tags
    - Converts <br>, <p>, <li>, <div> into clean line breaks
    - Decodes HTML entities (&amp; -> &, &nbsp; -> ' ')
    - Strips remaining tags
    - Collapses excess whitespace while preserving semantic paragraphs
    """
    if not raw_html_or_text:
        return ""

    text = raw_html_or_text
    # 1. Remove script/style
    text = SCRIPT_STYLE_RE.sub("", text)

    # 2. Convert common block tags to newlines
    text = re.sub(r"<(br|p|li|div|h[1-6]|tr)[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</(p|div|li|h[1-6]|tr)>", "\n", text, flags=re.IGNORECASE)

    # 3. Strip remaining tags
    text = TAG_RE.sub(" ", text)

    # 4. Decode HTML entities and non-breaking spaces
    text = html.unescape(text).replace("\xa0", " ")

    # 5. Clean whitespace per line
    lines = [MULTIPLE_SPACES_RE.sub(" ", line).strip() for line in text.split("\n")]
    cleaned = "\n".join(line for line in lines if line)

    # 6. Normalize paragraph spacing
    cleaned = MULTIPLE_NEWLINES_RE.sub("\n\n", cleaned).strip()
    return cleaned
