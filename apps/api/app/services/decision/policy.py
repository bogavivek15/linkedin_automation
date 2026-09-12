"""
CareerOS Phase 9 — Decision Policy Engine Service Interface.

Re-exports the pure domain DecisionPolicyEngine.
"""

from apps.api.app.services.decision.service import DecisionEngine as DecisionPolicyEngine

__all__ = ["DecisionPolicyEngine"]
