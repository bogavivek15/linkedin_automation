from apps.api.app.domain.job.models import RawJobPayload
from apps.api.app.services.jobs.providers.base import JobProvider


class MockHimalayasProvider(JobProvider):
    """
    Deterministic offline mock for Himalayas jobs.
    """

    @property
    def name(self) -> str:
        return "HIMALAYAS"

    async def fetch_jobs(
        self,
        *,
        limit: int = 20,
        query: str | None = None,
        page: int = 1,
    ) -> list[RawJobPayload]:
        return [
            RawJobPayload(
                source=self.name,
                external_id="him-101",
                source_url="https://himalayas.app/jobs/senior-python-engineer-101",
                raw_data={
                    "guid": "him-101",
                    "title": "Senior Python Backend Engineer [Remote]",
                    "companyName": "Alpha Data Corp Inc.",
                    "description": (
                        "<p>We are seeking a <strong>Senior Python Backend Engineer</strong> with 5+ years experience.</p>"
                        "<p>Requirements:</p>"
                        "<ul>"
                        "<li>5+ years of experience in Python and FastAPI</li>"
                        "<li>Strong PostgreSQL and Docker expertise</li>"
                        "<li>Experience with Kubernetes is a plus</li>"
                        "</ul>"
                        "<p>Nice to have:</p>"
                        "<ul>"
                        "<li>Familiarity with Redis and AWS</li>"
                        "</ul>"
                    ),
                    "minSalary": 120000,
                    "maxSalary": 160000,
                    "currency": "USD",
                    "locationRestrictions": ["Worldwide"],
                    "employmentType": "Full-time",
                    "pubDate": "2026-03-01T10:00:00Z",
                    "applicationLink": "https://alphadata.com/careers/backend-eng",
                },
            ),
            RawJobPayload(
                source=self.name,
                external_id="him-102",
                source_url="https://himalayas.app/jobs/react-frontend-developer-102",
                raw_data={
                    "guid": "him-102",
                    "title": "Lead Frontend Developer (React & TypeScript)",
                    "companyName": "Modern Web Labs LLC",
                    "description": (
                        "<p>Build modern React and Next.js applications.</p>"
                        "<p>Requirements: 3+ years experience with React, TypeScript, and Tailwind CSS.</p>"
                    ),
                    "minSalary": 90000,
                    "maxSalary": 130000,
                    "currency": "USD",
                    "locationRestrictions": ["US Only"],
                    "employmentType": "Full-time",
                    "pubDate": "2026-03-02T12:00:00Z",
                    "applicationLink": "https://modernweblabs.io/jobs/react-lead",
                },
            ),
        ][:limit]


class MockJobicyProvider(JobProvider):
    """
    Deterministic offline mock for Jobicy jobs.
    Notice him-101 / jobicy-201 represent a cross-provider opportunity!
    """

    @property
    def name(self) -> str:
        return "JOBICY"

    async def fetch_jobs(
        self,
        *,
        limit: int = 20,
        query: str | None = None,
        page: int = 1,
    ) -> list[RawJobPayload]:
        return [
            RawJobPayload(
                source=self.name,
                external_id="jobicy-201",
                source_url="https://jobicy.com/jobs/senior-python-backend-engineer",
                raw_data={
                    "id": "jobicy-201",
                    "jobTitle": "Senior Python Backend Engineer",
                    "companyName": "Alpha Data Corp",
                    "jobDescription": (
                        "<p>Seeking a Senior Python Backend Engineer with 5+ years experience in Python and FastAPI.</p>"
                        "<p>Requirements: PostgreSQL, Docker.</p>"
                        "<p>Nice to have: Redis, AWS, Kubernetes.</p>"
                    ),
                    "salaryMin": 120000,
                    "salaryMax": 160000,
                    "salaryCurrency": "USD",
                    "salaryPeriod": "yearly",
                    "jobGeo": "Worldwide",
                    "jobType": ["Full-Time"],
                    "pubDate": "2026-03-01T10:30:00Z",
                    "url": "https://alphadata.com/careers/backend-eng?utm_source=jobicy&ref=aggregator",
                },
            ),
            RawJobPayload(
                source=self.name,
                external_id="jobicy-202",
                source_url="https://jobicy.com/jobs/ai-data-scientist",
                raw_data={
                    "id": "jobicy-202",
                    "jobTitle": "AI & ML Engineer",
                    "companyName": "DeepCognition Technologies",
                    "jobDescription": (
                        "<p>Develop machine learning models with PyTorch and LangChain.</p>"
                        "<p>Must have: Python, PyTorch, Scikit-Learn. 2+ years of experience.</p>"
                    ),
                    "salaryMin": 110000,
                    "salaryMax": 150000,
                    "salaryCurrency": "USD",
                    "salaryPeriod": "yearly",
                    "jobGeo": "Remote - India",
                    "jobType": ["Full-Time"],
                    "pubDate": "2026-03-03T09:00:00Z",
                    "url": "https://deepcognition.ai/careers/ai-eng",
                },
            ),
        ][:limit]
