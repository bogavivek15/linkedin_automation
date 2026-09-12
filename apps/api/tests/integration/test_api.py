import io


def test_health_endpoint(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    assert json_data["data"]["status"] == "healthy"
    assert "x-request-id" in response.headers


def test_resume_upload_endpoint(client, sample_pdf_bytes):
    files = {"file": ("test_resume.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")}
    response = client.post("/api/v1/resumes/upload", files=files)
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    assert len(json_data["data"]["claims"]) > 0
    assert json_data["meta"]["total_claims"] == len(json_data["data"]["claims"])
    assert "x-request-id" in response.headers


def test_decision_evaluate_endpoint(client):
    payload = {
        "match_score": 94.0,
        "trust_score": 91.0,
        "risk_level": "LOW",
        "has_hard_constraint_violation": False,
    }
    response = client.post("/api/v1/decision/evaluate", json=payload)
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    assert json_data["data"]["final_score"] == 93.7
    assert json_data["data"]["outcome"] == "AUTO_APPLY"
