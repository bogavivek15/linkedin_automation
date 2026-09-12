import html
import json
import logging
import re
from typing import Any
from urllib.parse import urlparse

from apps.api.app.core.errors import CareerOSError
from apps.api.app.domain.job.models import RawJobPayload
from apps.api.app.services.jobs.normalization import clean_description
from apps.api.app.services.jobs.security import SafeHttpClient

logger = logging.getLogger("careeros.jobs.user_url")

JSON_LD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
OG_TITLE_RE = re.compile(
    r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
META_DESC_RE = re.compile(
    r'<meta[^>]+(?:name|property)=["\'](?:og:)?description["\'][^>]+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
TITLE_TAG_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


class UserUrlJobImporter:
    """
    Safely analyzes a user-supplied public job URL.
    - SSRF & redirect-checked safe HTTP fetch
    - Structured JSON-LD JobPosting parser with HTML meta tag fallback
    - Zero credentialed scraping, zero CAPTCHA bypass
    """

    def __init__(self, client: SafeHttpClient | None = None):
        self.client = client or SafeHttpClient()

    async def import_url(self, url: str) -> RawJobPayload:
        if not url or not url.strip():
            raise CareerOSError(
                code="JOB_URL_UNSAFE",
                message="URL cannot be empty",
                status_code=400,
            )

        # 1. Safe fetch with SSRF and redirect validation
        html_content, final_url = await self.client.fetch_url(url.strip())

        # 2. Extract structured data
        raw_data = self._extract_job_data(html_content, final_url)

        return RawJobPayload(
            source="USER_SUBMISSION",
            external_id=final_url,
            source_url=final_url,
            raw_data=raw_data,
        )

    def _extract_job_data(self, html_text: str, source_url: str) -> dict[str, Any]:
        """
        Extract JobPosting JSON-LD or fallback to meta/body tags.
        """
        # 1. Check for JSON-LD JobPosting
        json_ld_blocks = JSON_LD_RE.findall(html_text)
        for block in json_ld_blocks:
            try:
                data = json.loads(block.strip())
                # Could be a single object or a @graph list
                candidates = data.get("@graph", [data]) if isinstance(data, dict) else data
                if isinstance(candidates, dict):
                    candidates = [candidates]

                for item in candidates:
                    if isinstance(item, dict):
                        item_type = str(item.get("@type", "")).lower()
                        if "jobposting" in item_type:
                            hiring_org = item.get("hiringOrganization")
                            company_name = ""
                            if isinstance(hiring_org, dict):
                                company_name = hiring_org.get("name", "")
                            elif isinstance(hiring_org, str):
                                company_name = hiring_org

                            return {
                                "title": item.get("title", ""),
                                "companyName": company_name,
                                "description": item.get("description", ""),
                                "location": str(item.get("jobLocation", "")),
                                "employmentType": item.get("employmentType", ""),
                                "datePosted": item.get("datePosted", ""),
                                "validThrough": item.get("validThrough", ""),
                                "url": item.get("url") or source_url,
                                "source_type": "json_ld",
                            }
            except Exception:
                continue

        # 2. Fallback to OpenGraph / Meta / Title tags
        title = ""
        og_title = OG_TITLE_RE.search(html_text)
        if og_title:
            title = html.unescape(og_title.group(1).strip())
        else:
            tag_title = TITLE_TAG_RE.search(html_text)
            if tag_title:
                title = html.unescape(tag_title.group(1).strip())

        # Derive company and clean title if title is "Role at Company"
        company = ""
        if " at " in title:
            parts = title.split(" at ", 1)
            title, company = parts[0].strip(), parts[1].strip()
        elif " - " in title:
            parts = title.rsplit(" - ", 1)
            title, company = parts[0].strip(), parts[1].strip()

        if not company:
            # Fallback to domain name
            netloc = urlparse(source_url).netloc
            company = netloc.split(".")[0].capitalize()

        description = ""
        meta_desc = META_DESC_RE.search(html_text)
        if meta_desc:
            description = html.unescape(meta_desc.group(1).strip())
        else:
            description = clean_description(html_text)[:2000]

        return {
            "title": title or "Discovered Job Opportunity",
            "companyName": company or "Unknown Company",
            "description": description,
            "url": source_url,
            "source_type": "html_meta",
        }
