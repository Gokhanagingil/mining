"""
Semantic Column Inference Engine

Rules-based inference using:
1. Column name pattern matching (weighted)
2. Data type compatibility
3. Value distribution signals
4. Format pattern recognition
"""
import re
import logging
from typing import List, Optional
from app.models.schemas import ColumnProfile, SemanticInference, SemanticRole

logger = logging.getLogger(__name__)

# Name patterns → candidate roles with base confidence
NAME_PATTERNS: list[tuple[re.Pattern, SemanticRole, float]] = [
    # Record / Case ID
    (re.compile(r'\b(number|num|nr|no|id|incident|case|ticket|record|ref|reference|sys_id)\b', re.I), SemanticRole.case_id, 0.75),
    (re.compile(r'^(id|uuid|guid|pk|key)$', re.I), SemanticRole.record_id, 0.85),
    (re.compile(r'(incident|case|ticket|request)[\s_-]*(id|number|num|no|nr)', re.I), SemanticRole.case_id, 0.90),

    # Activity / State
    (re.compile(r'^(activity|event|action|step|task|operation)$', re.I), SemanticRole.activity_name, 0.88),
    (re.compile(r'(activity|event|action)[\s_-]*(name|type|label)', re.I), SemanticRole.activity_name, 0.85),
    (re.compile(r'^(state|status|phase|stage|current_state|current_status)$', re.I), SemanticRole.status, 0.85),
    (re.compile(r'(incident|case|ticket|request)[\s_-]*(state|status)', re.I), SemanticRole.status, 0.88),

    # Timestamps
    (re.compile(r'(created|open|opened|reported|logged|submitted)[\s_-]*(at|on|date|time|timestamp|_ts)', re.I), SemanticRole.created_at, 0.90),
    (re.compile(r'^(created_at|creation_date|open_date|open_time|created_on|opened_at)$', re.I), SemanticRole.created_at, 0.95),
    (re.compile(r'(updated|modified|changed|last_modified)[\s_-]*(at|on|date|time|timestamp)', re.I), SemanticRole.updated_at, 0.88),
    (re.compile(r'^(updated_at|update_date|modified_at|sys_updated_on)$', re.I), SemanticRole.updated_at, 0.95),
    (re.compile(r'(resolved|fix|fixed|solution)[\s_-]*(at|on|date|time|timestamp)', re.I), SemanticRole.resolved_at, 0.90),
    (re.compile(r'^(resolved_at|resolve_date|resolution_date|resolved_on)$', re.I), SemanticRole.resolved_at, 0.95),
    (re.compile(r'(closed|close|end)[\s_-]*(at|on|date|time|timestamp)', re.I), SemanticRole.closed_at, 0.88),
    (re.compile(r'^(closed_at|close_date|closed_on|end_date|end_time)$', re.I), SemanticRole.closed_at, 0.95),

    # Actor / Resource
    (re.compile(r'^(assignee|assigned_to|owner|handler|agent|technician|analyst|operator)$', re.I), SemanticRole.assignee, 0.90),
    (re.compile(r'(assigned|assign)[\s_-]*(to|by|user|agent)', re.I), SemanticRole.assignee, 0.85),
    (re.compile(r'^(assignment_group|team|group|queue|support_group|resolver_group|work_group)$', re.I), SemanticRole.assignment_group, 0.88),
    (re.compile(r'(assignment|assign)[\s_-]*(group|team|queue)', re.I), SemanticRole.assignment_group, 0.85),
    (re.compile(r'(queue|routing|dispatch)[\s_-]*(name|group|team)', re.I), SemanticRole.queue, 0.80),
    (re.compile(r'^(queue)$', re.I), SemanticRole.queue, 0.82),

    # Customer
    (re.compile(r'^(customer|client|user|requester|caller|reporter|contact|account)$', re.I), SemanticRole.customer, 0.88),
    (re.compile(r'(customer|client)[\s_-]*(id|name|code|number)', re.I), SemanticRole.customer, 0.85),
    (re.compile(r'(opened|requested|reported)[\s_-]*(by|for)', re.I), SemanticRole.customer, 0.75),

    # Category
    (re.compile(r'^(category|cat|type|incident_type|request_type|service_type)$', re.I), SemanticRole.category, 0.88),
    (re.compile(r'(category|classification)[\s_-]*(name|type|label)', re.I), SemanticRole.category, 0.85),
    (re.compile(r'^(subcategory|sub_category|subtype|sub_type|sub_cat)$', re.I), SemanticRole.subcategory, 0.88),

    # Priority
    (re.compile(r'^(priority|urgency|severity|impact|criticality|sev)$', re.I), SemanticRole.priority, 0.90),
    (re.compile(r'(priority|urgency|severity)[\s_-]*(level|code|name)', re.I), SemanticRole.priority, 0.85),

    # SLA
    (re.compile(r'(sla|breach|breached|violated|violated)', re.I), SemanticRole.sla_breach_flag, 0.85),
    (re.compile(r'(sla)[\s_-]*(breach|status|flag|met)', re.I), SemanticRole.sla_breach_flag, 0.90),

    # Satisfaction
    (re.compile(r'^(satisfaction|csat|nps|rating|score|feedback_score|survey_score|happiness)$', re.I), SemanticRole.satisfaction_score, 0.90),
    (re.compile(r'(satisfaction|customer_satisfaction|csat)[\s_-]*(score|rating|value)', re.I), SemanticRole.satisfaction_score, 0.90),

    # Duration
    (re.compile(r'^(duration|time_to|resolution_time|response_time|handle_time|cycle_time|lead_time|ttr|tth)$', re.I), SemanticRole.duration, 0.88),
    (re.compile(r'(duration|time_to|resolve_time|response_time)[\s_-]*(minutes|hours|days|seconds|ms)', re.I), SemanticRole.duration, 0.90),

    # Channel / Source
    (re.compile(r'^(channel|source|contact_type|contact_channel|medium|entry_point)$', re.I), SemanticRole.channel, 0.85),
    (re.compile(r'^(source_system|system|platform|application|app)$', re.I), SemanticRole.source_system, 0.80),

    # Region
    (re.compile(r'^(region|country|location|site|office|branch|geography|geo)$', re.I), SemanticRole.region, 0.82),

    # Free text
    (re.compile(r'^(description|desc|short_description|short_desc|summary|notes|details|body)$', re.I), SemanticRole.description, 0.88),
    (re.compile(r'^(comment|comments|work_notes|note|remarks|resolution_notes)$', re.I), SemanticRole.comment_text, 0.85),
]

# Typical values for categorical fields
STATUS_VALUES = {"open", "in progress", "pending", "resolved", "closed", "cancelled", "on hold", "waiting", "new", "active", "done", "completed", "assigned", "reopened"}
PRIORITY_VALUES = {"low", "medium", "high", "critical", "p1", "p2", "p3", "p4", "1", "2", "3", "4", "urgent", "normal"}
CHANNEL_VALUES = {"email", "phone", "chat", "web", "portal", "self-service", "walk-in", "mobile", "api", "slack", "teams"}
BOOLEAN_VALUES = {"true", "false", "yes", "no", "1", "0", "t", "f", "y", "n"}


class SemanticInferenceEngine:

    def infer(self, columns: list[ColumnProfile]) -> list[SemanticInference]:
        results = []
        assigned_roles: dict[SemanticRole, float] = {}  # role → best confidence assigned so far

        for col in columns:
            inference = self._infer_column(col, assigned_roles)
            results.append(inference)
            if inference.confidence > 0.5:
                existing = assigned_roles.get(inference.inferred_role, 0.0)
                if inference.confidence > existing:
                    assigned_roles[inference.inferred_role] = inference.confidence

        return results

    def _infer_column(
        self, col: ColumnProfile, assigned: dict[SemanticRole, float]
    ) -> SemanticInference:
        candidates: dict[SemanticRole, float] = {}
        reasons: dict[SemanticRole, list[str]] = {}

        col_lower = col.column_name.lower().strip()

        # 1. Name pattern matching
        for pattern, role, base_conf in NAME_PATTERNS:
            if pattern.search(col_lower):
                if role not in candidates or candidates[role] < base_conf:
                    candidates[role] = base_conf
                    reasons[role] = [f"Column name '{col.column_name}' matches {role.value} pattern"]

        # 2. Data type boosting
        self._apply_type_signals(col, candidates, reasons)

        # 3. Value distribution signals
        self._apply_value_signals(col, candidates, reasons)

        # 4. Timestamp detection
        self._apply_timestamp_signals(col, candidates, reasons)

        # 5. Penalize if role already strongly assigned to another column
        for role in list(candidates.keys()):
            existing_conf = assigned.get(role, 0.0)
            if existing_conf > 0.7 and candidates.get(role, 0) < existing_conf:
                candidates[role] = max(0.1, candidates[role] * 0.5)

        if not candidates:
            return SemanticInference(
                column_name=col.column_name,
                inferred_role=SemanticRole.unknown,
                confidence=0.0,
                reason="No matching patterns found",
                sample_justification=f"Sample values: {col.sample_values[:5]}",
                alternative_roles=[],
            )

        # Sort by confidence
        sorted_roles = sorted(candidates.items(), key=lambda x: x[1], reverse=True)
        best_role, best_conf = sorted_roles[0]

        # Clamp confidence
        best_conf = min(0.99, max(0.01, best_conf))

        alt_roles = [
            {"role": r.value, "confidence": round(min(0.99, c), 3)}
            for r, c in sorted_roles[1:4]
            if c > 0.2
        ]

        reason_text = "; ".join(reasons.get(best_role, ["Pattern match"]))
        sample_just = f"Sample values: {col.sample_values[:5]}"

        return SemanticInference(
            column_name=col.column_name,
            inferred_role=best_role,
            confidence=round(best_conf, 3),
            reason=reason_text,
            sample_justification=sample_just,
            alternative_roles=alt_roles,
        )

    def _apply_type_signals(
        self, col: ColumnProfile, candidates: dict, reasons: dict
    ):
        t = col.inferred_type

        # Timestamp type → boost timestamp roles
        if t in ("datetime", "date"):
            for role in [SemanticRole.created_at, SemanticRole.updated_at, SemanticRole.resolved_at, SemanticRole.closed_at]:
                if role in candidates:
                    candidates[role] = min(0.99, candidates[role] + 0.10)
                    reasons.setdefault(role, []).append("Column is datetime type")

        # Numeric → boost satisfaction, duration
        if t in ("integer", "float"):
            if col.min_value and col.max_value:
                try:
                    mn, mx = float(col.min_value), float(col.max_value)
                    if 1 <= mn and mx <= 10:
                        boost = 0.15
                        for role in [SemanticRole.satisfaction_score, SemanticRole.priority]:
                            if role in candidates:
                                candidates[role] = min(0.99, candidates[role] + boost)
                    if mx > 10 and mn >= 0:
                        if SemanticRole.duration in candidates:
                            candidates[SemanticRole.duration] = min(0.99, candidates[SemanticRole.duration] + 0.10)
                except Exception:
                    pass

        # Identifier type → boost record/case id
        if t == "identifier":
            for role in [SemanticRole.record_id, SemanticRole.case_id]:
                if role in candidates:
                    candidates[role] = min(0.99, candidates[role] + 0.10)
                    reasons.setdefault(role, []).append("High cardinality identifier type")

        # High null ratio → reduce confidence for mandatory fields
        if col.null_ratio > 0.3:
            for role in [SemanticRole.case_id, SemanticRole.created_at]:
                if role in candidates:
                    candidates[role] = max(0.1, candidates[role] - 0.20)

    def _apply_value_signals(
        self, col: ColumnProfile, candidates: dict, reasons: dict
    ):
        sample_lower = {str(v).lower().strip() for v in col.sample_values}

        # Status values
        status_overlap = sample_lower & STATUS_VALUES
        if status_overlap and len(status_overlap) >= 2:
            boost = min(0.20, len(status_overlap) * 0.05)
            for role in [SemanticRole.status, SemanticRole.state]:
                candidates[role] = max(candidates.get(role, 0.0), 0.60 + boost)
                reasons.setdefault(role, []).append(f"Values match status vocabulary: {status_overlap}")

        # Priority values
        priority_overlap = sample_lower & PRIORITY_VALUES
        if priority_overlap and len(priority_overlap) >= 2:
            boost = min(0.20, len(priority_overlap) * 0.05)
            candidates[SemanticRole.priority] = max(candidates.get(SemanticRole.priority, 0.0), 0.65 + boost)
            reasons.setdefault(SemanticRole.priority, []).append(f"Values match priority vocabulary: {priority_overlap}")

        # Channel values
        channel_overlap = sample_lower & CHANNEL_VALUES
        if channel_overlap and len(channel_overlap) >= 2:
            candidates[SemanticRole.channel] = max(candidates.get(SemanticRole.channel, 0.0), 0.70)
            reasons.setdefault(SemanticRole.channel, []).append(f"Values match channel vocabulary: {channel_overlap}")

        # Boolean flag
        if sample_lower.issubset(BOOLEAN_VALUES) and len(sample_lower) <= 4:
            candidates[SemanticRole.sla_breach_flag] = max(candidates.get(SemanticRole.sla_breach_flag, 0.0), 0.55)

        # Satisfaction score: values 1-10 or 0-100
        if col.inferred_type in ("integer", "float") and col.min_value and col.max_value:
            try:
                mn, mx = float(col.min_value), float(col.max_value)
                if 1 <= mn and mx <= 10 and col.distinct_count <= 10:
                    candidates[SemanticRole.satisfaction_score] = max(
                        candidates.get(SemanticRole.satisfaction_score, 0.0), 0.70
                    )
                    reasons.setdefault(SemanticRole.satisfaction_score, []).append(
                        f"Numeric scale {mn}-{mx} with {col.distinct_count} distinct values"
                    )
                elif 0 <= mn and mx <= 100 and col.distinct_count <= 101:
                    candidates[SemanticRole.satisfaction_score] = max(
                        candidates.get(SemanticRole.satisfaction_score, 0.0), 0.60
                    )
            except Exception:
                pass

        # High distinct + long strings = description/comment
        if col.is_free_text:
            for role in [SemanticRole.description, SemanticRole.comment_text]:
                candidates[role] = max(candidates.get(role, 0.0), 0.55)
                reasons.setdefault(role, []).append("Column appears to contain free-form text")

    def _apply_timestamp_signals(
        self, col: ColumnProfile, candidates: dict, reasons: dict
    ):
        ts_ratio = col.timestamp_parse_success_ratio
        if ts_ratio is None:
            return

        if ts_ratio > 0.85:
            if not any(r in candidates for r in [
                SemanticRole.created_at, SemanticRole.updated_at,
                SemanticRole.resolved_at, SemanticRole.closed_at
            ]):
                candidates[SemanticRole.created_at] = max(
                    candidates.get(SemanticRole.created_at, 0.0), 0.55
                )
                reasons.setdefault(SemanticRole.created_at, []).append(
                    f"High timestamp parse ratio ({ts_ratio:.0%}) suggests datetime column"
                )
            else:
                for role in [SemanticRole.created_at, SemanticRole.updated_at,
                             SemanticRole.resolved_at, SemanticRole.closed_at]:
                    if role in candidates:
                        candidates[role] = min(0.99, candidates[role] + 0.08)
                        reasons.setdefault(role, []).append(
                            f"High timestamp parse ratio ({ts_ratio:.0%})"
                        )
