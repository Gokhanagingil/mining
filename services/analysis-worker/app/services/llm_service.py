"""
LLM Commentary Layer

Architecture:
- Provider abstraction (LLMProvider base class)
- OpenAI adapter (GPT-4o)
- Mock/fallback for when no API key is configured

LLM receives only the evidence pack (never raw CSV).
"""
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Optional
from app.core.config import settings
from app.models.schemas import InsightCandidate

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert process analyst and management consultant specializing in ITSM, 
operational efficiency, and data-driven process improvement. You analyze pre-computed metrics and 
insight candidates extracted from enterprise process data.

CRITICAL RULES:
1. Never invent metrics, numbers, or statistics not present in the provided evidence pack.
2. Never make claims beyond what the evidence supports.
3. If confidence is low, explicitly state uncertainty.
4. All insights must reference specific evidence from the provided data.
5. Write for a management audience: precise, actionable, evidence-backed.
6. Tone: Professional, authoritative, direct. No hedging clichés like "it appears" unless genuinely uncertain.
"""

def _build_evidence_prompt(evidence_pack: dict) -> str:
    ds = evidence_pack.get("dataset_summary", {})
    metrics = evidence_pack.get("metric_summary", {})
    insights = evidence_pack.get("ranked_insights", [])
    mapping = evidence_pack.get("mapping_decisions", {})

    top_insights_text = ""
    for i, ins in enumerate(insights[:8], 1):
        top_insights_text += f"""
{i}. [{ins.get('insight_type', 'unknown').upper()}] {ins.get('title', '')}
   Support: {ins.get('support_count', 0):,} cases | Effect size: {ins.get('effect_size', 0):.2f} | Confidence: {ins.get('confidence', 0):.0%}
   Description: {ins.get('description_seed', '')}
   Evidence: {json.dumps(ins.get('evidence_refs', {}), indent=2)[:500]}
   Action seed: {ins.get('recommended_action_seed', '')}
"""

    duration = metrics.get("duration_metrics", {})
    sat = metrics.get("satisfaction_stats", {})
    reopen = metrics.get("reopen_signals", {})

    return f"""
EVIDENCE PACK FOR ANALYSIS
===========================

DATASET SUMMARY:
- Total records: {ds.get('row_count', 'N/A'):,}
- Columns: {ds.get('column_count', 'N/A')}
- Date range: {ds.get('date_range', 'N/A')}
- Detected domains: {', '.join(ds.get('domains_detected', []))}

KEY MAPPED COLUMNS:
{json.dumps(mapping, indent=2)[:800]}

OVERALL DURATION METRICS:
- Mean resolution: {duration.get('mean_minutes', 'N/A')} min
- Median resolution: {duration.get('median_minutes', 'N/A')} min
- P95 resolution: {duration.get('p95_minutes', 'N/A')} min
- Case count with duration: {duration.get('case_count', 'N/A')}

SATISFACTION:
- Mean score: {sat.get('mean', 'N/A')}
- Scale: {sat.get('min', 'N/A')} to {sat.get('max', 'N/A')}
- Std dev: {sat.get('std_dev', 'N/A')}

REOPEN/LOOP SIGNALS:
- Reopen rate: {reopen.get('reopen_rate_pct', 'N/A')}%
- Reopened cases: {reopen.get('reopened_count', 'N/A')}

TOP RANKED INSIGHT CANDIDATES (pre-computed programmatically):
{top_insights_text}

FULL METRICS SUMMARY:
{json.dumps({k: v for k, v in metrics.items() if k not in ['outlier_cases', 'customer_assignee_matrix']}, indent=2)[:3000]}

---
TASK: Based ONLY on the evidence above, generate a structured analysis report.
Do not invent any numbers or patterns not present in the data.
"""


def _build_output_format() -> str:
    return """
OUTPUT FORMAT (respond with valid JSON only):
{
  "executive_summary": "3-5 sentence executive summary highlighting the 2-3 most critical findings with specific numbers from the evidence",
  "process_manager_summary": "Detailed operational summary for process managers covering patterns, bottlenecks, and improvement opportunities with specific evidence",
  "top_bottlenecks": [
    {
      "title": "...",
      "description": "Evidence-backed description with specific numbers",
      "severity": "critical|high|medium|low",
      "recommendation": "Specific, actionable recommendation"
    }
  ],
  "hypotheses": [
    {
      "hypothesis": "Testable hypothesis based on data pattern",
      "supporting_evidence": "Specific data points that support this",
      "confidence": "high|medium|low"
    }
  ],
  "recommendations": [
    {
      "title": "...",
      "description": "What to do and why",
      "expected_impact": "What measurable outcome is expected",
      "effort": "low|medium|high",
      "priority": 1
    }
  ],
  "disclaimer": "Note any data quality issues, limitations, or areas where confidence is low"
}
"""


class LLMProvider(ABC):
    @abstractmethod
    def generate_commentary(self, evidence_pack: dict) -> dict:
        pass


class OpenAIProvider(LLMProvider):
    def __init__(self):
        from openai import OpenAI
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model

    def generate_commentary(self, evidence_pack: dict) -> dict:
        prompt = _build_evidence_prompt(evidence_pack) + _build_output_format()

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=4000,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            result = json.loads(content)
            result["model_used"] = self.model
            result["is_mock"] = False
            result["generated_at"] = datetime.now(timezone.utc).isoformat()
            return result
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise


class MockLLMProvider(LLMProvider):
    """
    Deterministic mock that generates plausible commentary from the evidence pack
    without calling any external API. Used when no API key is configured.
    """

    def generate_commentary(self, evidence_pack: dict) -> dict:
        ds = evidence_pack.get("dataset_summary", {})
        metrics = evidence_pack.get("metric_summary", {})
        insights = evidence_pack.get("ranked_insights", [])
        duration = metrics.get("duration_metrics", {})
        sat = metrics.get("satisfaction_stats", {})
        reopen = metrics.get("reopen_signals", {})

        row_count = ds.get("row_count", 0)
        mean_dur = duration.get("mean_minutes")
        median_dur = duration.get("median_minutes")
        p95_dur = duration.get("p95_minutes")

        # Build evidence-grounded executive summary
        exec_parts = []
        if row_count:
            exec_parts.append(f"Analysis covers {row_count:,} process records.")
        if median_dur:
            exec_parts.append(
                f"Median resolution time is {median_dur:.0f} minutes "
                f"(mean: {mean_dur:.0f} min; P95: {p95_dur:.0f} min), indicating substantial tail-end delays."
            )
        if sat.get("mean") and sat.get("max"):
            ratio = sat["mean"] / sat["max"]
            exec_parts.append(
                f"Average satisfaction score of {sat['mean']:.2f}/{sat['max']:.0f} ({ratio:.0%}) "
                f"{'indicates room for significant improvement' if ratio < 0.7 else 'is within acceptable range but has improvement potential'}."
            )
        if insights:
            top = insights[0]
            exec_parts.append(
                f"The highest-priority finding is: {top.get('title', 'an identified operational pattern')} "
                f"affecting {top.get('support_count', 0):,} cases with an effect size of {top.get('effect_size', 0):.2f}."
            )
        if reopen.get("reopen_rate_pct", 0) > 3:
            exec_parts.append(
                f"A {reopen['reopen_rate_pct']:.1f}% case reopen rate signals first-contact resolution quality gaps."
            )

        exec_summary = " ".join(exec_parts) if exec_parts else (
            "Analysis complete. Review the insight candidates below for detailed findings."
        )

        # Build bottlenecks from top insights
        bottlenecks = []
        for ins in insights[:4]:
            severity_map = {
                "satisfaction_degradation": "critical",
                "queue_bottleneck": "high",
                "assignee_performance_gap": "high",
                "temporal_spike": "medium",
                "rework_loop_pattern": "high",
                "backlog_aging": "high",
                "customer_specific_delay": "medium",
                "self_service_opportunity": "low",
            }
            bottlenecks.append({
                "title": ins.get("title", ""),
                "description": ins.get("description_seed", ""),
                "severity": severity_map.get(ins.get("insight_type", ""), "medium"),
                "recommendation": ins.get("recommended_action_seed", ""),
            })

        # Build hypotheses
        hypotheses = []
        for ins in insights[:3]:
            hypotheses.append({
                "hypothesis": f"The pattern '{ins.get('title', '')}' is likely caused by {_hypothesize(ins)}",
                "supporting_evidence": ins.get("description_seed", ""),
                "confidence": "high" if ins.get("confidence", 0) > 0.75 else "medium" if ins.get("confidence", 0) > 0.50 else "low",
            })

        # Build recommendations
        recommendations = []
        for i, ins in enumerate(insights[:5], 1):
            recommendations.append({
                "title": ins.get("title", ""),
                "description": ins.get("recommended_action_seed", ""),
                "expected_impact": _estimate_impact(ins),
                "effort": "low" if ins.get("insight_type") in ["self_service_opportunity"] else "medium",
                "priority": i,
            })

        # Process manager summary
        pm_parts = [exec_summary]
        if duration:
            pm_parts.append(
                f"The {duration.get('case_count', 0):,} resolved cases show a P75-P95 spread of "
                f"{duration.get('p75_minutes', 0):.0f}–{duration.get('p95_minutes', 0):.0f} minutes, "
                "indicating significant tail-end processing delays that warrant investigation."
            )
        if insights:
            pm_parts.append(
                f"{len(insights)} insight candidates were identified programmatically. "
                "The findings are ranked by a composite score of support volume, effect size, and actionability. "
                "Review each insight's evidence references before taking action."
            )

        # Disclaimer
        quality_warnings = evidence_pack.get("schema_profile", [])
        disclaimer = (
            "This analysis is based on deterministic pattern detection from the uploaded dataset. "
            "Correlation does not imply causation. Verify hypotheses with domain experts before "
            "implementing changes. Note: AI commentary was generated by the mock provider (no external API call). "
            "Configure OPENAI_API_KEY for richer LLM-powered analysis."
        )

        return {
            "executive_summary": exec_summary,
            "process_manager_summary": " ".join(pm_parts),
            "top_bottlenecks": bottlenecks,
            "hypotheses": hypotheses,
            "recommendations": recommendations,
            "disclaimer": disclaimer,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "model_used": "mock-evidence-based-v1",
            "is_mock": True,
        }


def _hypothesize(insight: dict) -> str:
    itype = insight.get("insight_type", "")
    hypotheses = {
        "temporal_spike": "demand patterns tied to organizational rhythms (e.g., end-of-week, post-maintenance windows, seasonal cycles)",
        "workload_imbalance": "uneven case assignment logic, skill-based routing gaps, or capacity misalignment",
        "customer_specific_delay": "complex case types, routing mismatch, or insufficient dedicated support capacity",
        "assignee_performance_gap": "skill gaps, workload saturation, tool access differences, or onboarding status",
        "category_recurrence": "root cause not being addressed, insufficient self-service alternatives, or training gaps",
        "satisfaction_degradation": "resolution quality issues, communication gaps, or unmet SLA expectations",
        "self_service_opportunity": "lack of self-service tooling for predictable, repeatable request types",
        "routing_problem": "routing rules not accounting for customer complexity or assignee specialization",
        "queue_bottleneck": "capacity constraints, triage delays, or priority misclassification",
        "rework_loop_pattern": "premature case closure, insufficient resolution verification, or unclear closure criteria",
        "backlog_aging": "capacity constraints, blocked dependencies, or insufficient escalation policies",
    }
    return hypotheses.get(itype, "systemic process or capacity factors requiring further investigation")


def _estimate_impact(insight: dict) -> str:
    itype = insight.get("insight_type", "")
    impacts = {
        "temporal_spike": f"Reduce peak-day case volume and improve staffing efficiency",
        "workload_imbalance": "Reduce median resolution time and improve team utilization",
        "customer_specific_delay": "Improve customer satisfaction and reduce escalation risk",
        "assignee_performance_gap": "Reduce resolution time variance and improve consistency",
        "category_recurrence": "Reduce volume in this category through root cause resolution",
        "satisfaction_degradation": "Improve CSAT/NPS and reduce churn risk",
        "self_service_opportunity": "Deflect 30-50% of this category to self-service",
        "routing_problem": "Reduce resolution time variance for affected customers",
        "queue_bottleneck": "Reduce P95 resolution time for this group",
        "rework_loop_pattern": "Reduce reopen rate and improve first-contact resolution",
        "backlog_aging": "Clear aged backlog and reduce customer wait time",
    }
    return impacts.get(itype, "Measurable improvement in process efficiency metrics")


class LLMService:
    def __init__(self):
        self._provider: Optional[LLMProvider] = None

    def _get_provider(self) -> LLMProvider:
        if self._provider is None:
            if settings.openai_api_key and not settings.use_mock_llm:
                try:
                    self._provider = OpenAIProvider()
                    logger.info("Using OpenAI LLM provider")
                except Exception as e:
                    logger.warning(f"OpenAI provider init failed, falling back to mock: {e}")
                    self._provider = MockLLMProvider()
            else:
                logger.info("No OPENAI_API_KEY configured or mock forced, using mock LLM provider")
                self._provider = MockLLMProvider()
        return self._provider

    def generate_commentary(self, evidence_pack: dict) -> dict:
        provider = self._get_provider()
        try:
            return provider.generate_commentary(evidence_pack)
        except Exception as e:
            logger.error(f"LLM provider failed: {e}, falling back to mock")
            return MockLLMProvider().generate_commentary(evidence_pack)
