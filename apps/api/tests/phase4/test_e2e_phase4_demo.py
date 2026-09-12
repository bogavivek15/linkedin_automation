"""
Tests for CareerOS Phase 4 Complete 18-Step Real Code Path Demo Execution.
"""

import pytest
from uuid import uuid4
from apps.api.app.services.demo.scenario import DemoScenarioService


@pytest.mark.asyncio
async def test_complete_real_phase4_demo_execution():
    user_id = str(uuid4())
    result = await DemoScenarioService.execute_real_phase4_demo(user_id=user_id)

    assert result["success"] is True
    assert result["steps_completed"] == 18
    assert "demo_run_id" in result

    # Check opportunity evaluations
    safe_opp = result["opportunity_safe"]
    assert safe_opp["company"] == "Google DeepMind"
    assert safe_opp["match_score"] >= 80.0
    assert safe_opp["trust_score"] >= 90.0

    scam_opp = result["opportunity_scam"]
    assert scam_opp["company"] == "Apex Global Tech"
    assert scam_opp["decision"] == "REJECT"

    # Check 18 step logs
    logs = result["step_logs"]
    assert len(logs) == 18
    assert any("Candidate profile" in l for l in logs)
    assert any("confirmed Docker" in l for l in logs)
    assert any("Apex Global flagged HIGH risk" in l for l in logs)
    assert any("Application package prepared" in l for l in logs)
    assert any("sandbox" in l for l in logs)
    assert any("INTERVIEW" in l for l in logs)
    assert any("Presence Agent" in l for l in logs)
    assert any("Rejection recorded" in l for l in logs)
    assert any("SSE" in l for l in logs)
