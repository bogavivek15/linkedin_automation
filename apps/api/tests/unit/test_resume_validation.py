import pytest
from apps.api.app.core.errors import CareerOSError
from apps.api.app.services.resume_service import ResumeService


def test_validate_valid_pdf_file():
    pdf_bytes = b"%PDF-1.7\nSample content"
    clean_name = ResumeService.validate_file("my_resume.pdf", "application/pdf", pdf_bytes)
    assert clean_name == "my_resume.pdf"


def test_validate_valid_docx_file(sample_docx_bytes):
    clean_name = ResumeService.validate_file(
        "profile.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        sample_docx_bytes,
    )
    assert clean_name == "profile.docx"


def test_validate_valid_txt_file(sample_txt_bytes):
    clean_name = ResumeService.validate_file("resume.txt", "text/plain", sample_txt_bytes)
    assert clean_name == "resume.txt"


def test_reject_empty_file():
    with pytest.raises(CareerOSError) as exc:
        ResumeService.validate_file("empty.pdf", "application/pdf", b"")
    assert exc.value.code == "EMPTY_DOCUMENT"


def test_reject_oversized_file():
    large_bytes = b"%PDF-1.7\n" + b"X" * (6 * 1024 * 1024)
    with pytest.raises(CareerOSError) as exc:
        ResumeService.validate_file("oversized.pdf", "application/pdf", large_bytes)
    assert exc.value.code == "FILE_TOO_LARGE"


def test_reject_unsupported_extension():
    with pytest.raises(CareerOSError) as exc:
        ResumeService.validate_file("malicious.exe", "application/x-msdownload", b"MZ\x90\x00")
    assert exc.value.code == "INVALID_FILE_TYPE"


def test_reject_invalid_pdf_magic_bytes():
    # PDF extension but wrong header bytes
    with pytest.raises(CareerOSError) as exc:
        ResumeService.validate_file("fake.pdf", "application/pdf", b"NOT_A_PDF_STREAM")
    assert exc.value.code == "INVALID_FILE_SIGNATURE"


def test_reject_invalid_docx_magic_bytes():
    # DOCX extension but wrong header bytes
    with pytest.raises(CareerOSError) as exc:
        ResumeService.validate_file(
            "fake.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            b"NOT_ZIP_BYTES",
        )
    assert exc.value.code == "INVALID_FILE_SIGNATURE"


def test_reject_binary_txt():
    # TXT with embedded null bytes
    with pytest.raises(CareerOSError) as exc:
        ResumeService.validate_file("bad.txt", "text/plain", b"Hello\x00World\x00Binary")
    assert exc.value.code == "INVALID_FILE_SIGNATURE"


@pytest.mark.parametrize(
    "dangerous_name",
    [
        "../../etc/passwd.pdf",
        "..\\windows\\system32.pdf",
        "/root/resume.pdf",
        "resume\0null.pdf",
    ],
)
def test_reject_path_traversal_filenames(dangerous_name):
    with pytest.raises(CareerOSError) as exc:
        ResumeService.validate_file(dangerous_name, "application/pdf", b"%PDF-1.5")
    assert exc.value.code == "INVALID_FILENAME"
