"""
Unit tests for CareerOS Phase 20 — Deterministic Evaluation Quality Gates.
"""

import pytest
from apps.api.app.evaluation.runner import EvaluationSuiteRunner


@pytest.mark.asyncio
async def test_evaluation_suite_passes_quality_gates():
    """
    Asserts that the evaluation suite achieves 100% pass rate across
    matching, trust, and decision benchmarks.
    """
    results = await EvaluationSuiteRunner.run_all_evaluations()

    assert results["overall_pass_rate"] == 1.0
    assert results["matching"]["passed"] == results["matching"]["total"]
    assert results["trust"]["passed"] == results["trust"]["total"]
    assert results["decision"]["passed"] == results["decision"]["total"]
