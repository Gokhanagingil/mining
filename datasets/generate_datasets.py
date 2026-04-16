"""
Generate demo CSV datasets for ProcessMiner Phase 1 MVP.

Dataset 1: IT Helpdesk - Password Reset Spike (Monday morning pattern)
Dataset 2: Customer Support - Assignee Performance Gap

These are designed to produce strong, evidence-backed insights.
"""
import csv
import random
import math
from datetime import datetime, timedelta

random.seed(42)


def rand_dt(start: datetime, end: datetime) -> datetime:
    delta = end - start
    secs = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=secs)


def business_hours_dt(base_date: datetime, weekday_weight: list[float], hour_weight: list[float]) -> datetime:
    """Generate a datetime weighted by weekday and hour distributions."""
    # Pick weekday
    weekday = random.choices(range(7), weights=weekday_weight, k=1)[0]
    # Find next occurrence of that weekday from base
    days_ahead = weekday - base_date.weekday()
    if days_ahead < 0:
        days_ahead += 7
    date = base_date + timedelta(days=days_ahead + random.randint(0, 3) * 7)

    # Pick hour
    hour = random.choices(range(24), weights=hour_weight, k=1)[0]
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return date.replace(hour=hour, minute=minute, second=second)


# ─── Dataset 1: IT Helpdesk with Password Reset Spike ────────────────────────

def generate_helpdesk_dataset(filename: str, n_rows: int = 5000):
    categories = [
        ("Password Reset", 0.25),       # Dominant category with Monday spike
        ("Software Installation", 0.12),
        ("Hardware Issue", 0.10),
        ("Network Connectivity", 0.09),
        ("Email / Outlook", 0.08),
        ("VPN Access", 0.07),
        ("Account Unlock", 0.06),
        ("Printer Issue", 0.05),
        ("System Performance", 0.05),
        ("Security Alert", 0.04),
        ("Other", 0.09),
    ]
    cat_names = [c[0] for c in categories]
    cat_weights = [c[1] for c in categories]

    priorities = [("P1 - Critical", 0.05), ("P2 - High", 0.15), ("P3 - Medium", 0.50), ("P4 - Low", 0.30)]
    p_names = [p[0] for p in priorities]
    p_weights = [p[1] for p in priorities]

    assignees = [
        ("john.smith", 0.18),
        ("sarah.jones", 0.15),
        ("mike.wilson", 0.14),
        ("lisa.taylor", 0.12),
        ("david.brown", 0.10),
        ("emma.white", 0.09),
        ("james.harris", 0.08),
        ("anna.clark", 0.07),
        ("robert.lewis", 0.07),
    ]
    asgn_names = [a[0] for a in assignees]
    asgn_weights = [a[1] for a in assignees]

    groups = ["Service Desk L1", "Service Desk L2", "Network Team", "Security Team", "Hardware Team"]

    channels = ["Phone", "Email", "Self-Service Portal", "Chat", "Walk-in"]
    channel_weights = [0.30, 0.35, 0.20, 0.10, 0.05]

    start_date = datetime(2024, 1, 1, 8, 0, 0)

    # Weekday weights: Monday gets 2.2x spike (especially for password reset)
    base_weekday = [1.0, 0.85, 0.82, 0.80, 0.78, 0.25, 0.10]  # Mon-Sun
    # Hour weights: morning peak 8-11am (24 values)
    base_hour = [0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.02, 0.05, 0.12, 0.15, 0.14, 0.10, 0.10, 0.09, 0.09, 0.08, 0.07, 0.05, 0.02, 0.01, 0.01, 0.01, 0.01, 0.01]

    rows = []
    for i in range(n_rows):
        category = random.choices(cat_names, weights=cat_weights, k=1)[0]

        # Password reset: heavier Monday + morning bias
        if category == "Password Reset":
            ww = [2.2, 0.75, 0.70, 0.68, 0.65, 0.15, 0.05]
            hw = [0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.03, 0.10, 0.18, 0.20, 0.15, 0.10, 0.08, 0.06, 0.05, 0.03, 0.02, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01]
        elif category == "Account Unlock":
            ww = [1.8, 0.80, 0.78, 0.76, 0.73, 0.20, 0.08]
            hw = base_hour
        else:
            ww = base_weekday
            hw = base_hour

        # Normalize
        ww_sum = sum(ww)
        ww = [w / ww_sum for w in ww]
        hw_sum = sum(hw)
        hw = [w / hw_sum for w in hw]

        created = business_hours_dt(start_date, ww, hw)

        # Resolution time depends on priority and category
        priority = random.choices(p_names, weights=p_weights, k=1)[0]
        if "P1" in priority:
            base_minutes = random.lognormvariate(math.log(45), 0.5)
        elif "P2" in priority:
            base_minutes = random.lognormvariate(math.log(120), 0.6)
        elif "P3" in priority:
            base_minutes = random.lognormvariate(math.log(480), 0.8)
        else:
            base_minutes = random.lognormvariate(math.log(1440), 0.9)

        # Password reset takes much less time usually
        if category == "Password Reset":
            base_minutes *= 0.3
        elif category == "Hardware Issue":
            base_minutes *= 2.5  # Hardware takes longer

        assignee = random.choices(asgn_names, weights=asgn_weights, k=1)[0]

        # Some assignees are slower (james.harris and robert.lewis)
        if assignee in ("james.harris", "robert.lewis"):
            base_minutes *= random.uniform(1.8, 2.5)
        elif assignee in ("sarah.jones", "lisa.taylor"):
            base_minutes *= random.uniform(0.7, 0.9)  # Faster

        resolved = created + timedelta(minutes=base_minutes)

        # Status
        if random.random() < 0.05:  # 5% still open
            status = random.choice(["Open", "In Progress", "Pending"])
            resolved_str = ""
            closed_str = ""
        elif random.random() < 0.07:  # 7% reopened
            status = "Reopened"
            resolved_str = resolved.strftime("%Y-%m-%d %H:%M:%S")
            closed_str = ""
        else:
            status = "Closed"
            resolved_str = resolved.strftime("%Y-%m-%d %H:%M:%S")
            closed_at = resolved + timedelta(minutes=random.randint(15, 120))
            closed_str = closed_at.strftime("%Y-%m-%d %H:%M:%S")

        # SLA breach (higher priority = stricter SLA)
        sla_minutes = {"P1 - Critical": 60, "P2 - High": 240, "P3 - Medium": 1440, "P4 - Low": 4320}
        sla_limit = sla_minutes.get(priority, 1440)
        sla_breached = base_minutes > sla_limit and status == "Closed"

        # Satisfaction (1-5, lower for slow resolution)
        if status == "Closed":
            sat_base = 5.0 - (base_minutes / sla_limit) * 2.5
            sat_base = max(1.0, min(5.0, sat_base + random.gauss(0, 0.8)))
            satisfaction = round(sat_base, 1) if random.random() > 0.30 else ""  # 30% no response
        else:
            satisfaction = ""

        group = random.choices(groups, weights=[0.45, 0.25, 0.12, 0.10, 0.08], k=1)[0]
        channel = random.choices(channels, weights=channel_weights, k=1)[0]

        rows.append({
            "incident_number": f"INC{1000000 + i}",
            "short_description": f"{category} - User request",
            "category": category,
            "subcategory": _helpdesk_subcategory(category),
            "priority": priority,
            "state": status,
            "opened_at": created.strftime("%Y-%m-%d %H:%M:%S"),
            "resolved_at": resolved_str,
            "closed_at": closed_str,
            "assigned_to": assignee,
            "assignment_group": group,
            "opened_by": _random_customer(),
            "contact_type": channel,
            "sla_breach": str(sla_breached).lower(),
            "satisfaction_score": satisfaction,
        })

    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {filename}: {n_rows} rows")


def _helpdesk_subcategory(category: str) -> str:
    subs = {
        "Password Reset": random.choice(["AD Password", "Email Password", "VPN Password", "Application Password"]),
        "Software Installation": random.choice(["Microsoft Office", "Adobe Suite", "Development Tools", "Business App"]),
        "Hardware Issue": random.choice(["Laptop", "Desktop", "Monitor", "Keyboard/Mouse", "Docking Station"]),
        "Network Connectivity": random.choice(["WiFi", "Ethernet", "VPN", "Firewall"]),
        "Email / Outlook": random.choice(["Cannot send/receive", "Calendar issue", "Mailbox full", "Configuration"]),
    }
    return subs.get(category, "General")


def _random_customer() -> str:
    first = ["Alice", "Bob", "Carol", "David", "Eve", "Frank", "Grace", "Henry", "Iris", "Jack",
             "Karen", "Leo", "Maria", "Nathan", "Olivia", "Peter", "Quinn", "Rachel", "Sam", "Tina",
             "Uma", "Victor", "Wendy", "Xander", "Yuki", "Zara"]
    last = ["Anderson", "Baker", "Chen", "Davis", "Evans", "Foster", "Garcia", "Hall",
            "Ingram", "Johnson", "Kim", "Lopez", "Martin", "Nelson", "O'Brien", "Park",
            "Quinn", "Roberts", "Scott", "Thomas", "Upton", "Vance", "Walsh", "Xu", "Young", "Zhang"]
    return f"{random.choice(first)}.{random.choice(last)}"


# ─── Dataset 2: Customer Support with Performance Gaps ────────────────────────

def generate_support_dataset(filename: str, n_rows: int = 4000):
    customers = [
        ("Acme Corp", 0.18),         # Large enterprise, complex cases
        ("TechStart Inc", 0.15),
        ("Global Finance", 0.13),     # High satisfaction expectations
        ("RetailCo", 0.12),
        ("MedGroup", 0.10),           # Complex compliance requirements
        ("StartupXYZ", 0.09),
        ("CityCouncil", 0.08),
        ("UniServices", 0.08),
        ("Individual", 0.07),
    ]
    cust_names = [c[0] for c in customers]
    cust_weights = [c[1] for c in customers]

    # Assignees with deliberately different performance profiles
    assignees = [
        {
            "name": "alex.chen",
            "weight": 0.16,
            "speed": 0.75,      # Fast
            "quality": 0.90,    # High quality
            "sat_modifier": 0.3,
        },
        {
            "name": "maya.patel",
            "weight": 0.14,
            "speed": 0.80,
            "quality": 0.85,
            "sat_modifier": 0.2,
        },
        {
            "name": "carlos.silva",
            "weight": 0.13,
            "speed": 1.20,      # Slower
            "quality": 0.78,
            "sat_modifier": -0.1,
        },
        {
            "name": "jennifer.wu",
            "weight": 0.12,
            "speed": 0.90,
            "quality": 0.88,
            "sat_modifier": 0.1,
        },
        {
            "name": "thomas.berg",
            "weight": 0.11,
            "speed": 1.60,      # Significantly slower
            "quality": 0.65,    # Lower quality
            "sat_modifier": -0.5,
        },
        {
            "name": "sofia.moreau",
            "weight": 0.10,
            "speed": 0.95,
            "quality": 0.82,
            "sat_modifier": 0.0,
        },
        {
            "name": "ryan.kim",
            "weight": 0.09,
            "speed": 1.10,
            "quality": 0.75,
            "sat_modifier": -0.2,
        },
        {
            "name": "laura.smith",
            "weight": 0.15,
            "speed": 0.85,
            "quality": 0.87,
            "sat_modifier": 0.15,
        },
    ]

    categories = [
        ("Billing Issue", 0.22),
        ("Technical Support", 0.20),
        ("Feature Request", 0.15),
        ("Account Management", 0.13),
        ("Integration Problem", 0.12),
        ("Performance Issue", 0.10),
        ("Data Export/Import", 0.08),
    ]
    cat_names = [c[0] for c in categories]
    cat_weights = [c[1] for c in categories]

    priorities = [("Critical", 0.08), ("High", 0.22), ("Medium", 0.45), ("Low", 0.25)]
    p_names = [p[0] for p in priorities]
    p_weights = [p[1] for p in priorities]

    start_date = datetime(2024, 1, 1, 8, 0, 0)
    base_weekday = [1.0, 0.90, 0.88, 0.85, 0.82, 0.20, 0.05]
    base_hour = [0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.11, 0.14, 0.14, 0.12, 0.11, 0.11, 0.10, 0.09, 0.06, 0.02, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01]

    # Normalize
    bw_sum = sum(base_weekday)
    base_weekday = [w/bw_sum for w in base_weekday]
    bh_sum = sum(base_hour)
    base_hour = [w/bh_sum for w in base_hour]

    asgn_weights = [a["weight"] for a in assignees]
    rows = []

    for i in range(n_rows):
        customer = random.choices(cust_names, weights=cust_weights, k=1)[0]
        category = random.choices(cat_names, weights=cat_weights, k=1)[0]
        priority = random.choices(p_names, weights=p_weights, k=1)[0]
        created = business_hours_dt(start_date, base_weekday, base_hour)
        assignee_data = random.choices(assignees, weights=asgn_weights, k=1)[0]

        # Base resolution time in minutes
        base_minutes_map = {
            "Critical": random.lognormvariate(math.log(120), 0.5),
            "High": random.lognormvariate(math.log(480), 0.6),
            "Medium": random.lognormvariate(math.log(1440), 0.7),
            "Low": random.lognormvariate(math.log(4320), 0.8),
        }
        base_minutes = base_minutes_map[priority]

        # Customer complexity modifier
        customer_modifier = {
            "Acme Corp": 1.4,        # Complex, long cases
            "MedGroup": 1.6,         # Compliance overhead
            "Global Finance": 1.3,
            "Individual": 0.7,
            "StartupXYZ": 0.8,
        }.get(customer, 1.0)

        # Category modifier
        cat_modifier = {
            "Integration Problem": 1.8,
            "Performance Issue": 1.4,
            "Technical Support": 1.2,
            "Feature Request": 2.0,
            "Billing Issue": 0.8,
        }.get(category, 1.0)

        final_minutes = (
            base_minutes * assignee_data["speed"] * customer_modifier * cat_modifier
        )

        resolved = created + timedelta(minutes=final_minutes)

        # Quality check: thomas.berg has higher reopen rate
        status = "Closed"
        if random.random() > assignee_data["quality"]:
            status = random.choice(["Reopened", "Escalated"])

        resolved_str = resolved.strftime("%Y-%m-%d %H:%M:%S") if status != "Open" else ""
        closed_str = ""
        if status == "Closed":
            closed_at = resolved + timedelta(minutes=random.randint(5, 60))
            closed_str = closed_at.strftime("%Y-%m-%d %H:%M:%S")

        # Satisfaction score (1-10)
        if status == "Closed" and random.random() > 0.25:
            sat = 8.0 + assignee_data["sat_modifier"]
            sat -= (final_minutes / (base_minutes_map[priority] * 1.5)) * 1.5
            sat += random.gauss(0, 0.7)
            # Customer expectations
            if customer in ("Global Finance", "Acme Corp"):
                sat -= 0.3  # Higher expectations
            sat = round(max(1.0, min(10.0, sat)), 1)
        else:
            sat = ""

        # SLA breach
        sla_limits = {"Critical": 240, "High": 1440, "Medium": 5760, "Low": 14400}
        sla_breached = final_minutes > sla_limits.get(priority, 5760) and status == "Closed"

        rows.append({
            "ticket_id": f"SUP-{2000000 + i}",
            "subject": f"{category} - {customer}",
            "category": category,
            "priority": priority,
            "status": status,
            "created_at": created.strftime("%Y-%m-%d %H:%M:%S"),
            "resolved_at": resolved_str,
            "closed_at": closed_str,
            "assignee": assignee_data["name"],
            "team": _support_team(category),
            "customer": customer,
            "contact_channel": random.choice(["Email", "Portal", "Phone", "Chat"]),
            "sla_breached": str(sla_breached).lower(),
            "satisfaction_score": sat,
        })

    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {filename}: {n_rows} rows")


def _support_team(category: str) -> str:
    mapping = {
        "Billing Issue": "Finance Support",
        "Technical Support": "Technical Team",
        "Feature Request": "Product Team",
        "Account Management": "Account Team",
        "Integration Problem": "Integration Team",
        "Performance Issue": "Engineering",
        "Data Export/Import": "Technical Team",
    }
    return mapping.get(category, "General Support")


if __name__ == "__main__":
    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    generate_helpdesk_dataset("password-reset-spike.csv", 5000)
    generate_support_dataset("customer-assignee-performance.csv", 4000)

    print("\n✓ Demo datasets generated successfully!")
    print("  - password-reset-spike.csv: 5,000 rows, Monday morning password reset pattern")
    print("  - customer-assignee-performance.csv: 4,000 rows, assignee performance gaps")
