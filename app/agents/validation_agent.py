import logging

from app.utils.models import (
    WorkflowIntelligence, AgentSuitabilityScore, ValidationResult, ValidationFinding,
)

logger = logging.getLogger(__name__)


class ValidationAgent:
    """
    The governance gate of AgentSense. Before any blueprint is handed off, the
    Validation Agent runs guardrail checks over the workflow profile, the score,
    and the recommended design, then decides whether the plan can ship as-is or
    must pass through a human reviewer (Human-in-the-Loop).

    Deterministic by design: governance decisions should be auditable and
    reproducible, not stochastic.
    """

    def validate(self, intel: WorkflowIntelligence, score: AgentSuitabilityScore,
                 recommendation: dict) -> ValidationResult:
        findings: list[ValidationFinding] = []
        requires_human = False
        risk = "Low"

        rec_patterns = " ".join(recommendation.get("recommended_patterns", [])).lower()
        governance_text = (recommendation.get("governance", "") + " " + rec_patterns).lower()

        # 1. Compliance sensitivity → demand a HITL gate.
        if intel.compliance_sensitivity.lower() == "high":
            has_hitl = "human" in governance_text or "hitl" in governance_text or "gate" in governance_text
            findings.append(ValidationFinding(
                check="Compliance / HITL gate",
                status="pass" if has_hitl else "fail",
                detail=("HITL gate present for a high-compliance workflow." if has_hitl
                        else "High compliance sensitivity but no human-in-the-loop gate in the design."),
            ))
            requires_human = True
            risk = "High"
            if not has_hitl:
                # fold the missing gate into governance guidance
                recommendation.setdefault("governance", "")
        else:
            findings.append(ValidationFinding(
                check="Compliance / HITL gate", status="pass",
                detail="Compliance sensitivity does not mandate a mandatory human gate.",
            ))

        # 2. Error cost → reflection/critic or escalation expected.
        if intel.error_cost.lower() == "high":
            has_safety = any(k in governance_text for k in ("audit", "guardrail", "escalat", "critic", "reflect", "validation"))
            findings.append(ValidationFinding(
                check="High error-cost safeguards",
                status="pass" if has_safety else "warn",
                detail=("Audit/guardrail/escalation safeguards present." if has_safety
                        else "High error cost — recommend adding audit trail and escalation routing."),
            ))
            requires_human = True
            risk = "High" if risk != "High" else risk

        # 3. Data availability → autonomy only with adequate data.
        if intel.data_availability.lower() == "low" and score.classification in ("High",):
            findings.append(ValidationFinding(
                check="Data readiness vs autonomy",
                status="warn",
                detail="High autonomy recommended but data availability is Low — start assisted, not autonomous.",
            ))
            risk = "Medium" if risk == "Low" else risk

        # 4. Honesty check — don't agentify something that shouldn't be.
        if score.classification == "Not Suitable":
            findings.append(ValidationFinding(
                check="Right-tool check", status="pass",
                detail="Correctly flagged as not suitable for agents — recommend standard software/RPA.",
            ))

        # 5. Audit trail always expected in production.
        findings.append(ValidationFinding(
            check="Auditability",
            status="pass" if "audit" in governance_text else "warn",
            detail=("Audit trail referenced in governance." if "audit" in governance_text
                    else "Add an audit-trail/observability layer before production."),
        ))

        has_fail = any(f.status == "fail" for f in findings)
        approved = (not has_fail) and (not requires_human)

        summary_bits = []
        if requires_human:
            summary_bits.append("Human review required before deployment")
        if has_fail:
            summary_bits.append("blocking guardrail gap detected")
        if approved:
            summary_bits.append("Design cleared for automated handoff")
        summary = "; ".join(summary_bits) + f". Risk level: {risk}."

        return ValidationResult(
            approved=approved,
            requires_human_review=requires_human or has_fail,
            risk_level=risk,
            findings=findings,
            summary=summary,
        )


validation_agent = ValidationAgent()
