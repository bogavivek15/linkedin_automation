import io
from uuid import uuid4


def test_upload_pdf_resume_endpoint(client, sample_pdf_bytes):
    files = {"file": ("standard_resume.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")}
    response = client.post("/api/v1/resumes/upload", files=files)
    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert "data" in body
    assert body["data"]["file_name"] == "standard_resume.pdf"
    assert len(body["data"]["claims"]) > 0
    assert len(body["data"]["chunks"]) > 0
    assert body["meta"]["total_claims"] == len(body["data"]["claims"])
    assert "x-request-id" in response.headers


def test_upload_docx_resume_endpoint(client, sample_docx_bytes):
    files = {
        "file": (
            "resume.docx",
            io.BytesIO(sample_docx_bytes),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }
    response = client.post("/api/v1/resumes/upload", files=files)
    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert body["data"]["file_name"] == "resume.docx"
    assert len(body["data"]["claims"]) > 0


def test_upload_txt_resume_endpoint(client, sample_txt_bytes):
    files = {"file": ("resume.txt", io.BytesIO(sample_txt_bytes), "text/plain")}
    response = client.post("/api/v1/resumes/upload", files=files)
    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert body["data"]["file_name"] == "resume.txt"
    assert len(body["data"]["claims"]) > 0


def test_get_resume_claims_endpoint(client, sample_pdf_bytes):
    # First upload a resume
    files = {"file": ("my_resume.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")}
    upload_res = client.post("/api/v1/resumes/upload", files=files)
    assert upload_res.status_code == 200
    resume_id = upload_res.json()["data"]["id"]

    # Retrieve its claims
    claims_res = client.get(f"/api/v1/resumes/{resume_id}/claims")
    assert claims_res.status_code == 200

    claims_body = claims_res.json()
    assert claims_body["success"] is True
    assert isinstance(claims_body["data"], list)
    assert len(claims_body["data"]) > 0
    assert claims_body["meta"]["resume_id"] == resume_id
    assert "verified_count" in claims_body["meta"]


def test_get_resume_metadata_endpoint(client, sample_pdf_bytes):
    files = {"file": ("meta_resume.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")}
    upload_res = client.post("/api/v1/resumes/upload", files=files)
    resume_id = upload_res.json()["data"]["id"]

    meta_res = client.get(f"/api/v1/resumes/{resume_id}")
    assert meta_res.status_code == 200
    assert meta_res.json()["data"]["file_name"] == "meta_resume.pdf"


def test_cross_user_isolation_prevented(client, sample_pdf_bytes):
    user_a = str(uuid4())
    user_b = str(uuid4())

    # User A uploads a resume
    files = {"file": ("user_a_resume.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")}
    upload_res = client.post(
        "/api/v1/resumes/upload",
        files=files,
        headers={"x-user-id": user_a},
    )
    assert upload_res.status_code == 200
    resume_id = upload_res.json()["data"]["id"]

    # User B attempts to access User A's claims -> MUST return 403 Forbidden
    unauthorized_res = client.get(
        f"/api/v1/resumes/{resume_id}/claims",
        headers={"x-user-id": user_b},
    )
    assert unauthorized_res.status_code == 403
    error_body = unauthorized_res.json()
    assert error_body["success"] is False
    assert error_body["error"]["code"] == "FORBIDDEN"


def test_upload_invalid_file_signature_returns_400(client):
    files = {"file": ("corrupt.pdf", io.BytesIO(b"NOT_A_VALID_PDF_STREAM"), "application/pdf")}
    res = client.post("/api/v1/resumes/upload", files=files)
    assert res.status_code == 400
    body = res.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_FILE_SIGNATURE"


def test_get_nonexistent_resume_returns_404(client):
    random_id = str(uuid4())
    res = client.get(f"/api/v1/resumes/{random_id}")
    assert res.status_code == 404
    body = res.json()
    assert body["success"] is False
    assert body["error"]["code"] == "RESUME_NOT_FOUND"
