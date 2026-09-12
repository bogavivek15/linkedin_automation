import io
from uuid import uuid4


def test_resume_upload_generates_embeddings_and_status(client, sample_pdf_bytes):
    # Upload resume
    files = {"file": ("vivek_resume.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")}
    upload_res = client.post("/api/v1/resumes/upload", files=files)
    assert upload_res.status_code == 200
    resume_id = upload_res.json()["data"]["id"]

    # Verify embeddings status
    status_res = client.get(f"/api/v1/resumes/{resume_id}/embeddings/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["success"] is True
    assert status_data["data"]["embedded_chunks"] > 0
    assert status_data["data"]["dimensions"] == 768
    assert status_data["data"]["status"] == "READY"


def test_semantic_search_endpoint_returns_ranked_results(client, sample_pdf_bytes):
    # Upload resume
    files = {"file": ("engineer_resume.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")}
    upload_res = client.post("/api/v1/resumes/upload", files=files)
    assert upload_res.status_code == 200

    # Execute semantic search
    search_res = client.get("/api/v1/search/semantic?q=LangGraph+FastAPI+multi-agent&limit=5")
    assert search_res.status_code == 200
    body = search_res.json()
    assert body["success"] is True
    assert "data" in body
    assert len(body["data"]) > 0

    first_result = body["data"][0]
    assert "similarity" in first_result
    assert 0.0 <= first_result["similarity"] <= 1.0
    assert "content" in first_result
    assert "embedding" not in first_result  # Raw vectors must never be exposed!
    assert "x-request-id" in search_res.headers


def test_semantic_search_user_isolation_prevented(client, sample_pdf_bytes):
    user_a = str(uuid4())
    user_b = str(uuid4())

    # User A uploads a resume
    files = {"file": ("user_a_secret_resume.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")}
    upload_res = client.post(
        "/api/v1/resumes/upload",
        files=files,
        headers={"x-user-id": user_a},
    )
    assert upload_res.status_code == 200

    # User B searches with query matching User A's resume
    search_res_user_b = client.get(
        "/api/v1/search/semantic?q=Autonomous+multi-agent+LangGraph",
        headers={"x-user-id": user_b},
    )
    assert search_res_user_b.status_code == 200
    data_b = search_res_user_b.json()["data"]
    # User B must NOT see any of User A's chunks
    assert len(data_b) == 0

    # User A searches same query -> User A receives their own chunks
    search_res_user_a = client.get(
        "/api/v1/search/semantic?q=Autonomous+multi-agent+LangGraph",
        headers={"x-user-id": user_a},
    )
    assert search_res_user_a.status_code == 200
    data_a = search_res_user_a.json()["data"]
    assert len(data_a) > 0


def test_semantic_search_empty_query_rejected(client):
    res = client.get("/api/v1/search/semantic?q=")
    assert res.status_code == 422
