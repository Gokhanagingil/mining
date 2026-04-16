# Insight Engine Design

## Overview

The Insight Candidate Engine generates evidence-backed findings programmatically, before any LLM is called.

## Insight Families

### 1. Temporal Spike (`temporal_spike`)
**Detection**: Weekday with `relative_to_mean > 1.4` (40% above average)
**Evidence**: weekday count, mean count, ratio
**Use case**: Monday password resets, Friday incident surges, month-end peaks

### 2. Workload Imbalance (`workload_imbalance`)
**Detection**: Assignees with significantly higher case load relative to peers
**Evidence**: case counts per assignee, distribution stats
**Use case**: Single-point-of-failure experts, unfair queue assignment

### 3. Customer-Specific Delay (`customer_specific_delay`)
**Detection**: Customers with avg duration > 1.6x customer group mean (min 5 cases)
**Evidence**: customer avg duration, group mean, ratio
**Use case**: VIP customer neglect, complexity concentration, account routing issues

### 4. Assignee Performance Gap (`assignee_performance_gap`)
**Detection**: Assignees with |Z-score| > 1.5 on median duration (min 10 cases)
**Evidence**: median duration, group mean, Z-score, satisfaction if available
**Use case**: Skill gaps, overload, training needs, quality issues

### 5. Category Recurrence (`category_recurrence`)
**Detection**: 
- Category with > 25% of total volume
- Category with avg duration > 1.5x overall average (min 10 cases)
**Evidence**: category count, pct, duration ratios
**Use case**: Systematic recurring issues, self-service candidates, root cause analysis

### 6. Satisfaction Degradation (`satisfaction_degradation`)
**Detection**:
- Overall mean satisfaction < 65% of scale max
- Specific assignees with satisfaction > 15% below group mean
**Evidence**: mean, scale, ratio, group comparison
**Use case**: Service quality issues, customer churn risk

### 7. Self-Service Opportunity (`self_service_opportunity`)
**Detection**: Category containing self-service keywords with > 3% of volume
**Keywords**: password, reset, unlock, access, login, vpn, wifi, printer, how to, etc.
**Evidence**: category count, pct, keyword matches
**Use case**: Automation candidates, knowledge base gaps

### 8. Routing Problem (`routing_problem`)
**Detection**: Customer routed to 4+ assignees with max/mean duration ratio > 2.0
**Evidence**: assignee count, duration range, variance
**Use case**: Skill-based routing gaps, escalation path issues

### 9. Queue Bottleneck (`queue_bottleneck`)
**Detection**: Groups with P95 duration > 1.5x group P95 mean (min 10 cases)
**Evidence**: P95 duration, group mean P95, overall median ratio
**Use case**: Team capacity issues, triage bottlenecks, priority misclassification

### 10. Rework Loop (`rework_loop_pattern`)
**Detection**: Reopen rate > 3%
**Evidence**: reopened count, rate, total cases
**Use case**: First-contact resolution quality, premature closure, unclear criteria

### 11. Backlog Aging (`backlog_aging`)
**Detection**: Open cases older than 30 days as meaningful % of total
**Evidence**: aging breakdown by bucket
**Use case**: Blocked dependencies, capacity constraints, prioritization failures

## Ranking Algorithm

```python
rank_score = log(max(1, support_count)) × effect_size × confidence × actionability

# Actionability weights by type (domain knowledge):
ACTIONABILITY = {
    "satisfaction_degradation": 0.90,   # Direct customer impact, clear action
    "self_service_opportunity": 0.85,   # High ROI, clear implementation path
    "queue_bottleneck": 0.85,           # Capacity is actionable
    "workload_imbalance": 0.85,
    "assignee_performance_gap": 0.80,
    "routing_problem": 0.80,
    "temporal_spike": 0.80,
    "customer_specific_delay": 0.75,
    "category_recurrence": 0.70,
    "rework_loop_pattern": 0.70,
    "backlog_aging": 0.80,
    "outlier_case": 0.50,               # Low — individual cases less actionable at system level
}
```

## Top-N Selection

After ranking, the top 15 insights are returned. The LLM receives the top 8 for commentary generation.

This ensures:
- High-value findings are always prominent
- LLM prompt stays within token limits
- Low-confidence/low-impact findings are visible but de-emphasized

## Evidence Pack Format

Each insight carries:

```json
{
  "insight_id": "uuid",
  "insight_type": "temporal_spike",
  "title": "Volume Spike on Mondays",
  "description_seed": "Monday accounts for 450 incidents (2.1x daily average of 214)...",
  "support_count": 450,
  "impacted_population_pct": 10.2,
  "comparison_baseline": "Daily average: 214 incidents",
  "effect_size": 1.1,
  "confidence": 0.83,
  "evidence_refs": {
    "weekday": "Monday",
    "weekday_count": 450,
    "mean_count": 214.0,
    "ratio": 2.1
  },
  "recommended_action_seed": "Investigate demand drivers on this day...",
  "rank_score": 3.42
}
```

The `evidence_refs` field is displayed verbatim in the UI's "Evidence" panel for full transparency.
