"""
Insight Candidate Engine (Programmatic)

Generates evidence-backed insight candidates BEFORE LLM involvement.
Each insight has: type, title, support_count, effect_size, confidence, evidence_refs.
Insights are ranked by: support_count × effect_size × actionability.
"""
import uuid
import math
import logging
from typing import Any, Optional
from app.models.schemas import InsightCandidate, MappingDecision

logger = logging.getLogger(__name__)

ACTIONABILITY = {
    "temporal_spike": 0.80,
    "workload_imbalance": 0.85,
    "customer_specific_delay": 0.75,
    "assignee_performance_gap": 0.80,
    "category_recurrence": 0.70,
    "satisfaction_degradation": 0.90,
    "self_service_opportunity": 0.85,
    "routing_problem": 0.80,
    "queue_bottleneck": 0.85,
    "rework_loop_pattern": 0.70,
    "outlier_case": 0.50,
    "backlog_aging": 0.80,
}


def _rank_score(insight_type: str, support_count: int, effect_size: float, confidence: float) -> float:
    actionability = ACTIONABILITY.get(insight_type, 0.60)
    log_support = math.log(max(1, support_count))
    return round(log_support * effect_size * confidence * actionability, 4)


class InsightCandidateEngine:

    def generate(self, metrics: dict[str, Any], mapping: MappingDecision, row_count: int) -> list[InsightCandidate]:
        candidates: list[InsightCandidate] = []

        candidates.extend(self._weekday_spike_insights(metrics, row_count))
        candidates.extend(self._category_surge_insights(metrics, row_count))
        candidates.extend(self._assignee_performance_gap(metrics, row_count))
        candidates.extend(self._customer_delay_insights(metrics, row_count))
        candidates.extend(self._satisfaction_degradation(metrics))
        candidates.extend(self._queue_bottleneck_insights(metrics))
        candidates.extend(self._reopen_loop_insights(metrics, row_count))
        candidates.extend(self._backlog_aging_insights(metrics, row_count))
        candidates.extend(self._self_service_opportunity(metrics, mapping))
        candidates.extend(self._routing_problem_insights(metrics, row_count))

        # Rank and return top insights
        candidates.sort(key=lambda x: x.rank_score, reverse=True)
        return candidates[:15]

    def _weekday_spike_insights(self, metrics: dict, total: int) -> list[InsightCandidate]:
        results = []
        weekday_data = metrics.get("weekday_patterns", [])
        if not weekday_data:
            return results

        mean_count = sum(w["count"] for w in weekday_data) / 7
        if mean_count == 0:
            return results

        for wd in weekday_data:
            ratio = wd["relative_to_mean"]
            if ratio > 1.4:  # 40% above mean
                effect = ratio - 1.0
                support = wd["count"]
                confidence = min(0.90, 0.55 + effect * 0.3)
                results.append(InsightCandidate(
                    insight_id=str(uuid.uuid4()),
                    insight_type="temporal_spike",
                    title=f"Volume Spike on {wd['weekday_name']}s",
                    description_seed=(
                        f"{wd['weekday_name']} accounts for {wd['count']:,} incidents "
                        f"({ratio:.1f}x the daily average of {mean_count:.0f}). "
                        f"This pattern suggests systematic demand drivers on this day."
                    ),
                    support_count=support,
                    impacted_population_pct=round(support / total * 100, 2),
                    comparison_baseline=f"Daily average: {mean_count:.0f} incidents",
                    effect_size=round(effect, 3),
                    confidence=round(confidence, 3),
                    evidence_refs={
                        "weekday": wd["weekday_name"],
                        "weekday_count": wd["count"],
                        "mean_count": round(mean_count, 1),
                        "ratio": round(ratio, 2),
                    },
                    recommended_action_seed=(
                        "Investigate demand drivers on this day. Consider proactive communication, "
                        "pre-emptive FAQs, or staffing adjustments."
                    ),
                    rank_score=_rank_score("temporal_spike", support, effect, confidence),
                ))
        return results

    def _category_surge_insights(self, metrics: dict, total: int) -> list[InsightCandidate]:
        results = []
        cats = metrics.get("top_categories", [])
        if not cats or len(cats) < 3:
            return results

        # Top category vs rest
        top = cats[0]
        if top["pct"] > 25:
            effect = top["pct"] / 100
            confidence = 0.85
            results.append(InsightCandidate(
                insight_id=str(uuid.uuid4()),
                insight_type="category_recurrence",
                title=f"Dominant Category: '{top['category']}'",
                description_seed=(
                    f"Category '{top['category']}' accounts for {top['pct']:.1f}% of all cases ({top['count']:,} records). "
                    f"This concentration suggests a systematic, recurring issue that may be addressable at root cause."
                ),
                support_count=top["count"],
                impacted_population_pct=top["pct"],
                comparison_baseline="All other categories combined",
                effect_size=round(effect, 3),
                confidence=confidence,
                evidence_refs={
                    "category": top["category"],
                    "count": top["count"],
                    "pct": top["pct"],
                    "total_records": total,
                },
                recommended_action_seed=(
                    f"Deep-dive into '{top['category']}': identify whether this is addressable via "
                    "self-service, documentation improvement, or proactive measures."
                ),
                rank_score=_rank_score("category_recurrence", top["count"], effect, confidence),
            ))

        # Category with high duration vs average
        cat_dur = metrics.get("category_duration", [])
        overall_avg = metrics.get("duration_metrics", {}).get("mean_minutes")
        if overall_avg and cat_dur:
            for cd in cat_dur[:10]:
                if cd.get("avg_duration_minutes") and cd["count"] >= 10:
                    ratio = cd["avg_duration_minutes"] / overall_avg
                    if ratio > 1.5:
                        effect = ratio - 1.0
                        support = cd["count"]
                        confidence = min(0.85, 0.55 + (support / total) * 5)
                        results.append(InsightCandidate(
                            insight_id=str(uuid.uuid4()),
                            insight_type="category_recurrence",
                            title=f"High Resolution Time in '{cd['category']}'",
                            description_seed=(
                                f"Category '{cd['category']}' has an average resolution time of "
                                f"{cd['avg_duration_minutes']:.0f} minutes ({ratio:.1f}x the overall average of "
                                f"{overall_avg:.0f} minutes). This affects {cd['count']:,} cases."
                            ),
                            support_count=support,
                            impacted_population_pct=round(support / total * 100, 2),
                            comparison_baseline=f"Overall average: {overall_avg:.0f} min",
                            effect_size=round(effect, 3),
                            confidence=round(confidence, 3),
                            evidence_refs={
                                "category": cd["category"],
                                "avg_duration_minutes": cd["avg_duration_minutes"],
                                "overall_avg_minutes": overall_avg,
                                "ratio": round(ratio, 2),
                                "count": cd["count"],
                            },
                            recommended_action_seed=(
                                f"Analyze resolution patterns in '{cd['category']}'. "
                                "Consider knowledge base improvements, escalation path optimization, or specialized training."
                            ),
                            rank_score=_rank_score("category_recurrence", support, effect, round(confidence, 3)),
                        ))
        return results

    def _assignee_performance_gap(self, metrics: dict, total: int) -> list[InsightCandidate]:
        results = []
        assignees = metrics.get("top_assignees", [])
        overall_avg = metrics.get("duration_metrics", {}).get("median_minutes")

        if not assignees or len(assignees) < 3 or not overall_avg:
            return results

        # Filter to assignees with enough cases
        qualified = [a for a in assignees if a["case_count"] >= 10 and a.get("median_duration_minutes")]
        if len(qualified) < 2:
            return results

        # Find outlier assignees (significantly above or below median)
        durations = [a["median_duration_minutes"] for a in qualified]
        mean_dur = sum(durations) / len(durations)
        std_dur = math.sqrt(sum((d - mean_dur) ** 2 for d in durations) / len(durations)) if len(durations) > 1 else 0

        for a in qualified:
            if std_dur > 0 and a["median_duration_minutes"]:
                z = (a["median_duration_minutes"] - mean_dur) / std_dur
                if abs(z) > 1.5:
                    direction = "longer" if z > 0 else "shorter"
                    effect = abs(z) / 3.0  # normalize
                    support = a["case_count"]
                    confidence = min(0.85, 0.50 + (support / total) * 10)

                    # Satisfaction component
                    sat_note = ""
                    if a.get("avg_satisfaction"):
                        sat_note = f" Average satisfaction: {a['avg_satisfaction']:.2f}."

                    results.append(InsightCandidate(
                        insight_id=str(uuid.uuid4()),
                        insight_type="assignee_performance_gap",
                        title=f"Performance Gap: {a['actor']}",
                        description_seed=(
                            f"Assignee '{a['actor']}' handles {a['case_count']:,} cases with a median resolution time of "
                            f"{a['median_duration_minutes']:.0f} minutes — {abs(z):.1f} standard deviations {direction} "
                            f"than the group average of {mean_dur:.0f} minutes.{sat_note}"
                        ),
                        support_count=support,
                        impacted_population_pct=round(support / total * 100, 2),
                        comparison_baseline=f"Group median: {mean_dur:.0f} min",
                        effect_size=round(effect, 3),
                        confidence=round(confidence, 3),
                        evidence_refs={
                            "actor": a["actor"],
                            "case_count": a["case_count"],
                            "median_duration_minutes": a["median_duration_minutes"],
                            "group_mean_minutes": round(mean_dur, 2),
                            "z_score": round(z, 3),
                            "avg_satisfaction": a.get("avg_satisfaction"),
                        },
                        recommended_action_seed=(
                            "Review workload distribution, case type assignment, and support resources for this assignee. "
                            "Consider targeted coaching, knowledge base access, or workload rebalancing."
                        ),
                        rank_score=_rank_score("assignee_performance_gap", support, effect, round(confidence, 3)),
                    ))
        return results

    def _customer_delay_insights(self, metrics: dict, total: int) -> list[InsightCandidate]:
        results = []
        customers = metrics.get("top_customers", [])
        overall_avg = metrics.get("duration_metrics", {}).get("median_minutes")

        if not customers or not overall_avg:
            return results

        qualified = [c for c in customers if c["case_count"] >= 5 and c.get("avg_duration_minutes")]
        if len(qualified) < 2:
            return results

        durations = [c["avg_duration_minutes"] for c in qualified]
        mean_dur = sum(durations) / len(durations)

        for c in qualified[:10]:
            if c.get("avg_duration_minutes") and mean_dur:
                ratio = c["avg_duration_minutes"] / mean_dur
                if ratio > 1.6:
                    effect = ratio - 1.0
                    support = c["case_count"]
                    confidence = min(0.80, 0.45 + (support / total) * 10)
                    results.append(InsightCandidate(
                        insight_id=str(uuid.uuid4()),
                        insight_type="customer_specific_delay",
                        title=f"Elevated Resolution Time for '{c['actor']}'",
                        description_seed=(
                            f"Customer '{c['actor']}' experiences average resolution times of "
                            f"{c['avg_duration_minutes']:.0f} minutes — {ratio:.1f}x the customer average of "
                            f"{mean_dur:.0f} minutes. This may indicate complexity, routing issues, or prioritization gaps."
                        ),
                        support_count=support,
                        impacted_population_pct=round(support / total * 100, 2),
                        comparison_baseline=f"Customer group average: {mean_dur:.0f} min",
                        effect_size=round(effect, 3),
                        confidence=round(confidence, 3),
                        evidence_refs={
                            "customer": c["actor"],
                            "case_count": c["case_count"],
                            "avg_duration_minutes": c["avg_duration_minutes"],
                            "customer_mean_minutes": round(mean_dur, 2),
                            "ratio": round(ratio, 2),
                            "avg_satisfaction": c.get("avg_satisfaction"),
                        },
                        recommended_action_seed=(
                            f"Review case history for '{c['actor']}'. Identify if this is a complexity, "
                            "routing, or capacity issue. Consider dedicated SLA or escalation path."
                        ),
                        rank_score=_rank_score("customer_specific_delay", support, effect, round(confidence, 3)),
                    ))
        return results

    def _satisfaction_degradation(self, metrics: dict) -> list[InsightCandidate]:
        results = []
        sat_stats = metrics.get("satisfaction_stats", {})
        if not sat_stats or not sat_stats.get("mean"):
            return results

        mean_sat = sat_stats["mean"]
        min_sat = sat_stats.get("min", 0)
        max_sat = sat_stats.get("max", 10)

        # If mean satisfaction is low relative to scale
        scale_max = max_sat or 10
        sat_ratio = mean_sat / scale_max if scale_max else 0.5

        if sat_ratio < 0.65:
            effect = 1.0 - sat_ratio
            results.append(InsightCandidate(
                insight_id=str(uuid.uuid4()),
                insight_type="satisfaction_degradation",
                title="Below-Target Customer Satisfaction",
                description_seed=(
                    f"Average satisfaction score is {mean_sat:.2f} (scale: {min_sat}-{scale_max}), "
                    f"representing {sat_ratio:.0%} of the maximum. "
                    "This indicates systemic service quality issues requiring attention."
                ),
                support_count=int(metrics.get("duration_metrics", {}).get("case_count", 100)),
                impacted_population_pct=100.0,
                comparison_baseline=f"Scale max: {scale_max}",
                effect_size=round(effect, 3),
                confidence=0.80,
                evidence_refs={
                    "mean_satisfaction": mean_sat,
                    "scale_max": scale_max,
                    "sat_ratio": round(sat_ratio, 3),
                    "std_dev": sat_stats.get("std_dev"),
                },
                recommended_action_seed=(
                    "Identify top dissatisfaction drivers through text analysis of comments. "
                    "Correlate low satisfaction with specific categories, assignees, or resolution times."
                ),
                rank_score=_rank_score("satisfaction_degradation", 1000, effect, 0.80),
            ))

        # Assignees with low satisfaction vs group
        assignees = metrics.get("top_assignees", [])
        with_sat = [a for a in assignees if a.get("avg_satisfaction") and a["case_count"] >= 5]
        if len(with_sat) >= 3:
            sat_vals = [a["avg_satisfaction"] for a in with_sat]
            group_mean = sum(sat_vals) / len(sat_vals)
            for a in with_sat:
                if a["avg_satisfaction"] < group_mean * 0.85:
                    gap = group_mean - a["avg_satisfaction"]
                    effect = gap / group_mean
                    results.append(InsightCandidate(
                        insight_id=str(uuid.uuid4()),
                        insight_type="satisfaction_degradation",
                        title=f"Low Satisfaction for Assignee '{a['actor']}'",
                        description_seed=(
                            f"Assignee '{a['actor']}' has an average satisfaction score of "
                            f"{a['avg_satisfaction']:.2f}, compared to the group average of {group_mean:.2f} "
                            f"(gap: {gap:.2f} points across {a['case_count']:,} cases)."
                        ),
                        support_count=a["case_count"],
                        impacted_population_pct=0.0,
                        comparison_baseline=f"Group mean: {group_mean:.2f}",
                        effect_size=round(effect, 3),
                        confidence=0.75,
                        evidence_refs={
                            "actor": a["actor"],
                            "avg_satisfaction": a["avg_satisfaction"],
                            "group_mean_satisfaction": round(group_mean, 3),
                            "gap": round(gap, 3),
                            "case_count": a["case_count"],
                        },
                        recommended_action_seed=(
                            "Review recent cases handled by this assignee. Identify patterns in "
                            "low-satisfaction incidents and provide targeted coaching."
                        ),
                        rank_score=_rank_score("satisfaction_degradation", a["case_count"], effect, 0.75),
                    ))
        return results

    def _queue_bottleneck_insights(self, metrics: dict) -> list[InsightCandidate]:
        results = []
        groups = metrics.get("top_groups", [])
        overall_median = metrics.get("duration_metrics", {}).get("median_minutes")

        if not groups or not overall_median:
            return results

        qualified = [g for g in groups if g["case_count"] >= 10 and g.get("p95_duration_minutes")]
        if not qualified:
            return results

        p95_vals = [g["p95_duration_minutes"] for g in qualified]
        mean_p95 = sum(p95_vals) / len(p95_vals)

        for g in qualified:
            if g.get("p95_duration_minutes") and g["p95_duration_minutes"] > mean_p95 * 1.5:
                effect = (g["p95_duration_minutes"] - mean_p95) / mean_p95
                support = g["case_count"]
                confidence = min(0.85, 0.55 + min(support / 200, 0.30))

                queue_ratio = g["p95_duration_minutes"] / overall_median if overall_median else 1
                results.append(InsightCandidate(
                    insight_id=str(uuid.uuid4()),
                    insight_type="queue_bottleneck",
                    title=f"Queue Bottleneck: Group '{g['actor']}'",
                    description_seed=(
                        f"Group '{g['actor']}' shows a P95 resolution time of {g['p95_duration_minutes']:.0f} minutes "
                        f"— {queue_ratio:.1f}x the overall median. The tail of the distribution indicates systematic "
                        f"queuing delays for {support:,} cases."
                    ),
                    support_count=support,
                    impacted_population_pct=0.0,
                    comparison_baseline=f"Group P95 mean: {mean_p95:.0f} min",
                    effect_size=round(effect, 3),
                    confidence=round(confidence, 3),
                    evidence_refs={
                        "group": g["actor"],
                        "p95_minutes": g["p95_duration_minutes"],
                        "group_mean_p95": round(mean_p95, 2),
                        "overall_median": overall_median,
                        "case_count": support,
                    },
                    recommended_action_seed=(
                        f"Investigate queue depth and capacity for group '{g['actor']}'. "
                        "Consider cross-training, load balancing, or capacity expansion."
                    ),
                    rank_score=_rank_score("queue_bottleneck", support, effect, round(confidence, 3)),
                ))
        return results

    def _reopen_loop_insights(self, metrics: dict, total: int) -> list[InsightCandidate]:
        results = []
        reopen = metrics.get("reopen_signals", {})
        if not reopen or not reopen.get("reopened_count"):
            return results

        rate = reopen.get("reopen_rate_pct", 0)
        count = reopen.get("reopened_count", 0)
        if rate > 3:
            effect = rate / 100
            confidence = 0.80 if count > 50 else 0.65
            results.append(InsightCandidate(
                insight_id=str(uuid.uuid4()),
                insight_type="rework_loop_pattern",
                title="Significant Case Reopen/Escalation Rate",
                description_seed=(
                    f"{count:,} cases ({rate:.1f}%) show signs of reopening or escalation. "
                    "High reopen rates indicate insufficient first-contact resolution quality or "
                    "premature case closure."
                ),
                support_count=count,
                impacted_population_pct=rate,
                comparison_baseline="Target: < 3% reopen rate",
                effect_size=round(effect, 3),
                confidence=round(confidence, 3),
                evidence_refs={
                    "reopened_count": count,
                    "reopen_rate_pct": rate,
                    "total_cases": total,
                },
                recommended_action_seed=(
                    "Analyze patterns in reopened cases. Identify common root causes and improve "
                    "resolution verification, closure criteria, and agent training."
                ),
                rank_score=_rank_score("rework_loop_pattern", count, effect, round(confidence, 3)),
            ))
        return results

    def _backlog_aging_insights(self, metrics: dict, total: int) -> list[InsightCandidate]:
        results = []
        aging = metrics.get("backlog_aging", [])
        if not aging:
            return results

        old_cases = sum(b["count"] for b in aging if "31" in b["age_bucket"] or "90" in b["age_bucket"] or "180" in b["age_bucket"])
        if old_cases > 0:
            pct = old_cases / total * 100
            effect = pct / 100
            confidence = 0.80
            results.append(InsightCandidate(
                insight_id=str(uuid.uuid4()),
                insight_type="backlog_aging",
                title="Stale Backlog: Cases Older Than 30 Days",
                description_seed=(
                    f"{old_cases:,} open cases ({pct:.1f}%) are more than 30 days old. "
                    "An aging backlog indicates capacity constraints, prioritization issues, or "
                    "blocked cases that require management attention."
                ),
                support_count=old_cases,
                impacted_population_pct=round(pct, 2),
                comparison_baseline="Healthy target: < 5% cases older than 30 days",
                effect_size=round(effect, 3),
                confidence=confidence,
                evidence_refs={"aging_breakdown": aging, "old_cases": old_cases, "total": total},
                recommended_action_seed=(
                    "Conduct backlog triage. Prioritize or close stale cases. "
                    "Review capacity and implement aging-based escalation policies."
                ),
                rank_score=_rank_score("backlog_aging", old_cases, effect, confidence),
            ))
        return results

    def _self_service_opportunity(self, metrics: dict, mapping: MappingDecision) -> list[InsightCandidate]:
        results = []
        cats = metrics.get("top_categories", [])
        if not cats:
            return results

        # Look for categories that suggest self-serviceable issues
        SELF_SERVICE_KEYWORDS = [
            "password", "reset", "unlock", "access", "login", "account",
            "permission", "vpn", "wifi", "network", "email setup", "printer",
            "software install", "update", "how to", "training"
        ]

        for cat in cats[:15]:
            cat_lower = cat["category"].lower()
            if any(kw in cat_lower for kw in SELF_SERVICE_KEYWORDS) and cat["pct"] > 3:
                effect = cat["pct"] / 100
                confidence = 0.70
                results.append(InsightCandidate(
                    insight_id=str(uuid.uuid4()),
                    insight_type="self_service_opportunity",
                    title=f"Self-Service Opportunity: '{cat['category']}'",
                    description_seed=(
                        f"'{cat['category']}' accounts for {cat['count']:,} cases ({cat['pct']:.1f}%). "
                        f"This category likely contains repeatable, addressable requests that could be "
                        f"reduced through self-service portals, automated workflows, or improved documentation."
                    ),
                    support_count=cat["count"],
                    impacted_population_pct=cat["pct"],
                    comparison_baseline="Benchmark: Similar categories reduced 40-60% with self-service",
                    effect_size=round(effect, 3),
                    confidence=confidence,
                    evidence_refs={
                        "category": cat["category"],
                        "count": cat["count"],
                        "pct": cat["pct"],
                        "keywords_matched": [kw for kw in SELF_SERVICE_KEYWORDS if kw in cat_lower],
                    },
                    recommended_action_seed=(
                        f"Develop self-service capability for '{cat['category']}'. "
                        "Consider knowledge articles, chatbot flows, or automated provisioning."
                    ),
                    rank_score=_rank_score("self_service_opportunity", cat["count"], effect, confidence),
                ))
        return results

    def _routing_problem_insights(self, metrics: dict, total: int) -> list[InsightCandidate]:
        results = []
        matrix = metrics.get("customer_assignee_matrix", [])
        if not matrix or len(matrix) < 5:
            return results

        # High variance in assignee assignment for same customer
        from collections import defaultdict
        customer_assignees: dict[str, list] = defaultdict(list)
        for row in matrix:
            customer_assignees[row["customer"]].append(row)

        for customer, rows in customer_assignees.items():
            if len(rows) >= 4:
                durations = [r["avg_duration_minutes"] for r in rows if r.get("avg_duration_minutes")]
                if len(durations) >= 3:
                    mean_d = sum(durations) / len(durations)
                    max_d = max(durations)
                    if mean_d > 0 and max_d / mean_d > 2.0:
                        support = sum(r["count"] for r in rows)
                        effect = (max_d - mean_d) / mean_d
                        confidence = min(0.75, 0.45 + support / total * 5)
                        results.append(InsightCandidate(
                            insight_id=str(uuid.uuid4()),
                            insight_type="routing_problem",
                            title=f"Routing Inconsistency for Customer '{customer}'",
                            description_seed=(
                                f"Customer '{customer}' cases are handled by {len(rows)} different assignees "
                                f"with resolution times ranging from {min(durations):.0f} to {max_d:.0f} minutes "
                                f"(ratio {max_d/mean_d:.1f}x). High variance suggests inconsistent routing or skill matching."
                            ),
                            support_count=support,
                            impacted_population_pct=round(support / total * 100, 2),
                            comparison_baseline=f"Mean across assignees: {mean_d:.0f} min",
                            effect_size=round(effect, 3),
                            confidence=round(confidence, 3),
                            evidence_refs={
                                "customer": customer,
                                "assignee_count": len(rows),
                                "min_duration": round(min(durations), 2),
                                "max_duration": round(max_d, 2),
                                "mean_duration": round(mean_d, 2),
                            },
                            recommended_action_seed=(
                                f"Review case routing logic for '{customer}'. "
                                "Implement skill-based routing or dedicated account support."
                            ),
                            rank_score=_rank_score("routing_problem", support, effect, round(confidence, 3)),
                        ))
        return results
