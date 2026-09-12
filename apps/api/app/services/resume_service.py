import io
import os
import re
import zipfile
from uuid import UUID, uuid4

import docx
import pymupdf
from apps.api.app.core.errors import CareerOSError
from apps.api.app.core.logging import logger
from apps.api.app.core.security import sanitize_filename
from apps.api.app.domain.resume.models import (
    ParsedResume,
    ResumeClaim,
    SectionType,
)
from apps.api.app.domain.resume.rules import ClaimEvidenceValidator
from apps.api.app.services.ai.provider import AIProvider, get_ai_provider

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_DOCX_UNCOMPRESSED_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_DOCX_ENTRIES = 1000
MAX_COMPRESSION_RATIO = 100.0

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}

SECTION_MAPPING: dict[SectionType, list[str]] = {
    "SUMMARY": [
        r"summary",
        r"professional\s+summary",
        r"profile",
        r"about\s+me",
        r"executive\s+summary",
        r"career\s+objective",
        r"objective",
    ],
    "EXPERIENCE": [
        r"experience",
        r"work\s+experience",
        r"professional\s+experience",
        r"employment\s+history",
        r"employment",
        r"work\s+history",
        r"relevant\s+experience",
    ],
    "PROJECTS": [
        r"projects",
        r"key\s+projects",
        r"personal\s+projects",
        r"portfolio",
        r"technical\s+projects",
        r"project\s+experience",
    ],
    "EDUCATION": [
        r"education",
        r"academic\s+background",
        r"academic\s+history",
        r"qualifications",
        r"degrees",
    ],
    "SKILLS": [
        r"skills",
        r"technical\s+skills",
        r"core\s+competencies",
        r"technologies",
        r"skills\s+&\s+tools",
        r"tools\s+&\s+technologies",
        r"programming\s+languages",
    ],
    "CERTIFICATIONS": [
        r"certifications",
        r"certificates",
        r"licenses",
        r"credentials",
    ],
    "ACHIEVEMENTS": [
        r"achievements",
        r"honors",
        r"honors\s+&\s+awards",
        r"awards",
    ],
    "PUBLICATIONS": [
        r"publications",
        r"papers",
        r"research",
    ],
    "CONTACT": [
        r"contact",
        r"contact\s+information",
        r"personal\s+details",
    ],
}


class ResumeService:
    @classmethod
    def validate_file(cls, filename: str, content_type: str, file_bytes: bytes) -> str:
        """
        Comprehensive server-side validation:
        - Filename sanitization and path traversal prevention
        - Extension verification
        - Size bounds checking (max 5MB)
        - Magic bytes / file signature validation
        """
        # 1. Sanitize filename
        clean_filename = sanitize_filename(filename)
        _, ext = os.path.splitext(clean_filename.lower())
        if ext not in ALLOWED_EXTENSIONS:
            raise CareerOSError(
                code="INVALID_FILE_TYPE",
                message=f"File extension '{ext}' is not supported. Use .pdf, .docx, or .txt.",
                status_code=415,
            )

        # 2. File size validation
        file_size = len(file_bytes)
        if file_size == 0:
            raise CareerOSError(
                code="EMPTY_DOCUMENT",
                message="Uploaded file is empty (0 bytes)",
                status_code=422,
            )
        if file_size > MAX_FILE_SIZE:
            raise CareerOSError(
                code="FILE_TOO_LARGE",
                message=f"File exceeds maximum allowed limit of 5MB ({file_size} bytes)",
                status_code=400,
            )

        # 3. Magic-byte verification
        if ext == ".pdf":
            if not file_bytes.startswith(b"%PDF-"):
                raise CareerOSError(
                    code="INVALID_FILE_SIGNATURE",
                    message="File header signature does not match PDF format",
                    status_code=400,
                )
        elif ext == ".docx":
            if not file_bytes.startswith(b"PK\x03\x04"):
                raise CareerOSError(
                    code="INVALID_FILE_SIGNATURE",
                    message="File header signature does not match DOCX format",
                    status_code=400,
                )
        elif ext == ".txt":
            # Ensure text is not binary executable or arbitrary shell payload
            # Check for null bytes in initial sample
            if b"\x00" in file_bytes[:1024]:
                raise CareerOSError(
                    code="INVALID_FILE_SIGNATURE",
                    message="Binary null bytes detected in text document",
                    status_code=400,
                )

        return clean_filename

    @classmethod
    def extract_text_from_pdf(cls, file_bytes: bytes) -> tuple[str, int]:
        """
        Defensive text extraction from PDF using PyMuPDF.
        Returns (raw_text, page_count).
        """
        try:
            doc = pymupdf.open(stream=file_bytes, filetype="pdf")
            if doc.is_encrypted:
                raise CareerOSError(
                    code="MALFORMED_DOCUMENT",
                    message="Encrypted or password-protected PDFs are not supported",
                    status_code=422,
                )
            pages = len(doc)
            if pages == 0:
                raise CareerOSError(
                    code="EMPTY_DOCUMENT",
                    message="PDF document contains zero pages",
                    status_code=422,
                )

            extracted_pages: list[str] = []
            for i in range(pages):
                page = doc[i]
                extracted_pages.append(page.get_text("text"))

            doc.close()
            full_text = "\n".join(extracted_pages).strip()
            return full_text, pages
        except CareerOSError:
            raise
        except Exception as e:
            raise CareerOSError(
                code="MALFORMED_DOCUMENT",
                message=f"Failed to parse PDF document: {e!s}",
                status_code=422,
            )

    @classmethod
    def extract_text_from_docx(cls, file_bytes: bytes) -> str:
        """
        Defensive DOCX extraction with ZIP decompression bomb protection,
        entry limit enforcement, and path traversal validation.
        """
        stream = io.BytesIO(file_bytes)
        try:
            with zipfile.ZipFile(stream) as zf:
                total_uncompressed = 0
                entries = zf.infolist()

                if len(entries) > MAX_DOCX_ENTRIES:
                    raise CareerOSError(
                        code="MALFORMED_DOCUMENT",
                        message="DOCX archive exceeds maximum entry limit",
                        status_code=400,
                    )

                for info in entries:
                    # Guard against directory traversal inside zip
                    if ".." in info.filename or info.filename.startswith(("/", "\\")):
                        raise CareerOSError(
                            code="MALFORMED_DOCUMENT",
                            message="Suspicious entry path detected in DOCX archive",
                            status_code=400,
                        )
                    total_uncompressed += info.file_size

                if total_uncompressed > MAX_DOCX_UNCOMPRESSED_SIZE:
                    raise CareerOSError(
                        code="FILE_TOO_LARGE",
                        message="DOCX decompressed content exceeds maximum safety threshold",
                        status_code=400,
                    )

                compressed_size = max(1, len(file_bytes))
                ratio = total_uncompressed / compressed_size
                if ratio > MAX_COMPRESSION_RATIO:
                    raise CareerOSError(
                        code="MALFORMED_DOCUMENT",
                        message="High compression ratio detected (potential zip bomb)",
                        status_code=400,
                    )

            # Extract paragraphs and tables using python-docx
            stream.seek(0)
            doc = docx.Document(stream)
            text_parts: list[str] = []

            for paragraph in doc.paragraphs:
                p_text = paragraph.text.strip()
                if p_text:
                    text_parts.append(p_text)

            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(
                        cell.text.strip() for cell in row.cells if cell.text.strip()
                    )
                    if row_text:
                        text_parts.append(row_text)

            return "\n".join(text_parts).strip()
        except CareerOSError:
            raise
        except Exception as e:
            raise CareerOSError(
                code="MALFORMED_DOCUMENT",
                message=f"Failed to parse DOCX document: {e!s}",
                status_code=422,
            )

    @classmethod
    def extract_text_from_txt(cls, file_bytes: bytes) -> str:
        """
        Defensive text extraction from TXT with multi-encoding fallback.
        """
        encodings = ["utf-8", "utf-8-sig", "latin-1"]
        for enc in encodings:
            try:
                return file_bytes.decode(enc).strip()
            except UnicodeDecodeError:
                continue

        return file_bytes.decode("utf-8", errors="replace").strip()

    @classmethod
    def detect_sections(cls, raw_text: str) -> dict[str, str]:
        """
        Segment and normalize resume text into canonical section types.
        Handles alternate headings, casing variations, and delimiters.
        """
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        sections: dict[str, list[str]] = {
            "SUMMARY": [],
            "EXPERIENCE": [],
            "PROJECTS": [],
            "EDUCATION": [],
            "SKILLS": [],
            "CERTIFICATIONS": [],
            "ACHIEVEMENTS": [],
            "PUBLICATIONS": [],
            "CONTACT": [],
            "OTHER": [],
        }

        current_section = "SUMMARY"

        for line in lines:
            line_cleaned = line.lower().strip(":#-_*•= ")

            matched_section: SectionType | None = None
            for sec_type, patterns in SECTION_MAPPING.items():
                for pat in patterns:
                    if re.fullmatch(pat, line_cleaned):
                        matched_section = sec_type
                        break
                if matched_section:
                    break

            if matched_section:
                current_section = matched_section
            else:
                sections[current_section].append(line)

        # Clean empty sections
        return {k: "\n".join(v).strip() for k, v in sections.items() if v}

    @classmethod
    async def process_claims(
        cls,
        resume_id: UUID,
        raw_text: str,
        sections: dict[str, str],
        ai_provider: AIProvider | None = None,
    ) -> list[ResumeClaim]:
        """
        Two-pass claims provenance pipeline:
        Pass 1: Deterministic extraction & AI provider proposals
        Pass 2: Deterministic Evidence Grounding & Verification
        """
        provider = ai_provider or get_ai_provider()

        # Generate structured claims proposal
        proposed_claims = await provider.extract_claims_proposal(
            resume_id=resume_id,
            raw_text=raw_text,
            sections=sections,
        )

        validated_claims: list[ResumeClaim] = []

        for claim in proposed_claims:
            # Deterministic evidence grounding evaluation
            status, score, allowed = ClaimEvidenceValidator.evaluate_claim(
                statement=claim.statement,
                evidence=claim.evidence_text,
                full_text=raw_text,
            )

            validated_claims.append(
                ResumeClaim(
                    id=claim.id,
                    resume_id=resume_id,
                    claim_type=claim.claim_type,
                    statement=claim.statement,
                    source_type=claim.source_type,
                    source_id=claim.source_id,
                    evidence_text=claim.evidence_text,
                    verification_status=status,
                    confidence_score=score,
                    allowed_in_tailoring=allowed,
                )
            )

        return validated_claims

    @classmethod
    async def parse_and_process_resume(
        cls,
        filename: str,
        content_type: str,
        file_bytes: bytes,
        user_id: UUID | None = None,
        ai_provider: AIProvider | None = None,
    ) -> ParsedResume:
        """
        End-to-end resume pipeline:
        Validation -> Text Extraction -> Section Segmentation -> Chunks -> Claims -> Verification
        """
        clean_filename = cls.validate_file(filename, content_type, file_bytes)
        _, ext = os.path.splitext(clean_filename.lower())

        # Extract text based on verified type
        if ext == ".pdf":
            raw_text, _ = cls.extract_text_from_pdf(file_bytes)
        elif ext == ".docx":
            raw_text = cls.extract_text_from_docx(file_bytes)
        else:
            raw_text = cls.extract_text_from_txt(file_bytes)

        if not raw_text or not raw_text.strip():
            raise CareerOSError(
                code="EMPTY_DOCUMENT",
                message="The uploaded document contains no extractable text",
                status_code=422,
            )

        resume_id = uuid4()
        sections = cls.detect_sections(raw_text)

        # Create structured section-aware chunks for semantic persistence and retrieval
        from apps.api.app.services.embedding.chunking import create_section_aware_chunks
        from apps.api.app.services.embedding.service import EmbeddingService

        chunks = create_section_aware_chunks(
            resume_id=resume_id,
            sections=sections,
            user_id=user_id,
        )

        # Generate 768-dim semantic embeddings for chunks with deduplication
        try:
            chunks = await EmbeddingService.embed_chunks(chunks)
        except Exception as embed_err:
            logger.warning(
                f"Embedding generation failed for resume {resume_id}: {embed_err!s}",
                extra={"operation": "EMBEDDING_FAILED", "resume_id": str(resume_id)},
            )

        # Extract & verify atomic claims with full provenance lineage
        claims = await cls.process_claims(
            resume_id=resume_id,
            raw_text=raw_text,
            sections=sections,
            ai_provider=ai_provider,
        )

        return ParsedResume(
            id=resume_id,
            user_id=user_id,
            file_name=clean_filename,
            file_size=len(file_bytes),
            mime_type=content_type,
            raw_text=raw_text,
            status="PROCESSED",
            sections=sections,
            chunks=chunks,
            claims=claims,
        )
