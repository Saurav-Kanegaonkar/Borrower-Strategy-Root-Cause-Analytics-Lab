import csv
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTPUTS = ROOT / "analysis" / "outputs"
SRC = ROOT / "src"

RAW_CFPB = DATA / "cfpb_student_loan_complaints_sample.csv"

random.seed(42)

SEGMENTS = [
    {
        "segment_id": "REFI_HIGH_BAL_GRAD",
        "segment": "Graduate refinance, high balance",
        "product": "Student loan refinance",
        "borrowers": 28400,
        "avg_balance": 82200,
        "base_delinquency": 0.071,
        "autopay": 0.72,
        "income_pressure": 0.41,
        "channel": "Direct web",
        "owner": "Product",
    },
    {
        "segment_id": "REFI_MED_BAL_PRO",
        "segment": "Professional refinance, medium balance",
        "product": "Student loan refinance",
        "borrowers": 36300,
        "avg_balance": 51600,
        "base_delinquency": 0.044,
        "autopay": 0.81,
        "income_pressure": 0.27,
        "channel": "Partner marketplace",
        "owner": "Business Analytics",
    },
    {
        "segment_id": "INSCHOOL_PARENT",
        "segment": "In-school parent borrower",
        "product": "Private student loan",
        "borrowers": 21900,
        "avg_balance": 27800,
        "base_delinquency": 0.083,
        "autopay": 0.61,
        "income_pressure": 0.49,
        "channel": "School referral",
        "owner": "Operations",
    },
    {
        "segment_id": "INSCHOOL_STUDENT",
        "segment": "In-school student borrower",
        "product": "Private student loan",
        "borrowers": 41800,
        "avg_balance": 18300,
        "base_delinquency": 0.096,
        "autopay": 0.55,
        "income_pressure": 0.58,
        "channel": "Direct web",
        "owner": "Product",
    },
    {
        "segment_id": "PL_DEBT_CONSOLIDATION",
        "segment": "Personal loan, debt consolidation",
        "product": "Personal loan",
        "borrowers": 16700,
        "avg_balance": 14600,
        "base_delinquency": 0.118,
        "autopay": 0.64,
        "income_pressure": 0.66,
        "channel": "Direct web",
        "owner": "Credit Strategy",
    },
    {
        "segment_id": "PL_LIFE_EVENT",
        "segment": "Personal loan, life event",
        "product": "Personal loan",
        "borrowers": 11200,
        "avg_balance": 9700,
        "base_delinquency": 0.092,
        "autopay": 0.58,
        "income_pressure": 0.62,
        "channel": "Partner marketplace",
        "owner": "Operations",
    },
]

THEME_FALLBACK = [
    ("Struggling to repay your loan", 0.31),
    ("Dealing with your lender or servicer", 0.27),
    ("Problem with customer service", 0.16),
    ("Incorrect information on your report", 0.11),
    ("Trouble during payment process", 0.09),
    ("Issue where my lender is my school", 0.06),
]

ROOT_CAUSES = [
    {
        "cause": "Repayment plan mismatch",
        "driver": "income pressure",
        "fix": "Pre-delinquency outreach with plan-fit script",
        "weight": 0.34,
    },
    {
        "cause": "Autopay and payment friction",
        "driver": "autopay gap",
        "fix": "Payment retry and autopay enrollment experiment",
        "weight": 0.22,
    },
    {
        "cause": "Servicing clarity gap",
        "driver": "complaint theme concentration",
        "fix": "Rewrite top servicing flows and QA response macros",
        "weight": 0.19,
    },
    {
        "cause": "Credit-policy edge case",
        "driver": "segment volatility",
        "fix": "Credit strategy review for stressed micro-segments",
        "weight": 0.15,
    },
    {
        "cause": "Metric definition drift",
        "driver": "data quality",
        "fix": "Lock metric owner, grain, and reconciliation check",
        "weight": 0.10,
    },
]


def pct(value):
    return round(value * 100, 1)


def money(value):
    return int(round(value, 0))


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def complaint_themes():
    issue_counts = Counter()
    subproduct_counts = Counter()
    states = Counter()
    total = 0

    if RAW_CFPB.exists():
        with RAW_CFPB.open(newline="", errors="ignore") as f:
            for row in csv.DictReader(f):
                if row.get("Product") != "Student loan":
                    continue
                issue = row.get("Issue") or "Unknown"
                issue_counts[issue] += 1
                subproduct_counts[row.get("Sub-product") or "Unknown"] += 1
                state = row.get("State") or "Unknown"
                states[state] += 1
                total += 1

    if not issue_counts:
        total = 1000
        for issue, share in THEME_FALLBACK:
            issue_counts[issue] = int(total * share)
        subproduct_counts["Private student loan"] = 520
        subproduct_counts["Federal student loan servicing"] = 300
        subproduct_counts["Unknown"] = 180

    rows = []
    for issue, count in issue_counts.most_common(8):
        rows.append(
            {
                "issue": issue,
                "complaints": count,
                "share": round(count / total, 4),
                "borrower_signal": issue_to_signal(issue),
            }
        )

    write_csv(
        DATA / "public_complaint_themes.csv",
        rows,
        ["issue", "complaints", "share", "borrower_signal"],
    )

    return rows, total, subproduct_counts, states


def issue_to_signal(issue):
    text = issue.lower()
    if "repay" in text or "payment" in text or "default" in text:
        return "Repayment friction"
    if "servicer" in text or "customer" in text or "lender" in text:
        return "Servicing clarity"
    if "credit" in text or "report" in text or "incorrect" in text:
        return "Credit reporting risk"
    if "school" in text:
        return "School-channel issue"
    return "Borrower support demand"


def build_daily_metrics():
    rows = []
    for day in range(1, 121):
        seasonality = math.sin(day / 13) * 0.009
        for item in SEGMENTS:
            stress = item["income_pressure"] * 0.038 + (1 - item["autopay"]) * 0.025
            noise = random.uniform(-0.012, 0.012)
            delinquency = max(0.01, item["base_delinquency"] + stress + seasonality + noise)
            application_completion = min(
                0.98,
                0.78
                + item["autopay"] * 0.08
                - item["income_pressure"] * 0.06
                + random.uniform(-0.03, 0.03),
            )
            contact_rate = min(0.42, 0.07 + delinquency * 1.25 + random.uniform(-0.015, 0.025))
            first_resolution = max(
                0.48,
                0.86 - contact_rate * 0.42 - item["income_pressure"] * 0.05 + random.uniform(-0.025, 0.02),
            )
            approval_rate = max(
                0.34,
                0.72
                - item["income_pressure"] * 0.18
                + item["autopay"] * 0.04
                + random.uniform(-0.035, 0.025),
            )
            rows.append(
                {
                    "period": f"2026-W{math.ceil(day / 7):02d}",
                    "day_index": day,
                    "segment_id": item["segment_id"],
                    "delinquency_rate": round(delinquency, 4),
                    "application_completion_rate": round(application_completion, 4),
                    "contact_rate": round(contact_rate, 4),
                    "first_contact_resolution_rate": round(first_resolution, 4),
                    "approval_rate": round(approval_rate, 4),
                    "autopay_rate": round(item["autopay"] + random.uniform(-0.012, 0.012), 4),
                }
            )

    write_csv(
        DATA / "daily_borrower_metrics.csv",
        rows,
        [
            "period",
            "day_index",
            "segment_id",
            "delinquency_rate",
            "application_completion_rate",
            "contact_rate",
            "first_contact_resolution_rate",
            "approval_rate",
            "autopay_rate",
        ],
    )
    return rows


def segment_rows():
    rows = []
    for item in SEGMENTS:
        row = {
            "segment_id": item["segment_id"],
            "segment": item["segment"],
            "product": item["product"],
            "borrowers": item["borrowers"],
            "avg_balance": item["avg_balance"],
            "annualized_balance": money(item["borrowers"] * item["avg_balance"]),
            "base_delinquency": item["base_delinquency"],
            "autopay_rate": item["autopay"],
            "income_pressure_index": item["income_pressure"],
            "channel": item["channel"],
            "owner": item["owner"],
        }
        rows.append(row)

    write_csv(
        DATA / "borrower_segments.csv",
        rows,
        [
            "segment_id",
            "segment",
            "product",
            "borrowers",
            "avg_balance",
            "annualized_balance",
            "base_delinquency",
            "autopay_rate",
            "income_pressure_index",
            "channel",
            "owner",
        ],
    )
    return rows


def quality_rows():
    checks = [
        ("DQ001", "Delinquency denominator reconciles to servicing extract", "daily_borrower_metrics", 0.982, "Pass"),
        ("DQ002", "Application funnel event grain matches borrower application id", "application_events", 0.941, "Watch"),
        ("DQ003", "Complaint issue taxonomy mapped to borrower support themes", "public_complaint_themes", 0.915, "Watch"),
        ("DQ004", "Autopay enrollment feed lands before weekly review cutoff", "payments_feed", 0.887, "Fix"),
        ("DQ005", "Scenario assumptions have named owner and date", "scenario_forecast", 0.971, "Pass"),
        ("DQ006", "Segment ownership is complete for top action queue", "cohort_action_plan", 0.963, "Pass"),
    ]
    rows = [
        {
            "check_id": check_id,
            "check_name": name,
            "dataset": dataset,
            "confidence": confidence,
            "status": status,
        }
        for check_id, name, dataset, confidence, status in checks
    ]
    write_csv(DATA / "data_quality_checks.csv", rows, ["check_id", "check_name", "dataset", "confidence", "status"])
    return rows


def intervention_rows():
    rows = [
        {
            "intervention_id": "INT001",
            "intervention": "Pre-delinquency repayment-fit outreach",
            "target_root_cause": "Repayment plan mismatch",
            "expected_delinquency_lift": 0.018,
            "expected_contact_reduction": 0.022,
            "effort_score": 3,
            "owner": "Operations",
        },
        {
            "intervention_id": "INT002",
            "intervention": "Autopay retry and enrollment experiment",
            "target_root_cause": "Autopay and payment friction",
            "expected_delinquency_lift": 0.011,
            "expected_contact_reduction": 0.016,
            "effort_score": 2,
            "owner": "Product",
        },
        {
            "intervention_id": "INT003",
            "intervention": "Servicing clarity rewrite for top complaint flows",
            "target_root_cause": "Servicing clarity gap",
            "expected_delinquency_lift": 0.006,
            "expected_contact_reduction": 0.031,
            "effort_score": 2,
            "owner": "Customer",
        },
        {
            "intervention_id": "INT004",
            "intervention": "Credit policy edge-case review",
            "target_root_cause": "Credit-policy edge case",
            "expected_delinquency_lift": 0.009,
            "expected_contact_reduction": 0.008,
            "effort_score": 4,
            "owner": "Credit Strategy",
        },
        {
            "intervention_id": "INT005",
            "intervention": "Metric definition lock and reconciliation automation",
            "target_root_cause": "Metric definition drift",
            "expected_delinquency_lift": 0.003,
            "expected_contact_reduction": 0.012,
            "effort_score": 1,
            "owner": "Business Analytics",
        },
    ]
    write_csv(
        DATA / "intervention_playbook.csv",
        rows,
        [
            "intervention_id",
            "intervention",
            "target_root_cause",
            "expected_delinquency_lift",
            "expected_contact_reduction",
            "effort_score",
            "owner",
        ],
    )
    return rows


def aggregate(daily, themes, quality, interventions):
    by_segment = defaultdict(list)
    for row in daily:
        by_segment[row["segment_id"]].append(row)

    theme_cycle = themes or [{"issue": issue, "share": share, "borrower_signal": issue_to_signal(issue)} for issue, share in THEME_FALLBACK]
    quality_confidence = sum(float(row["confidence"]) for row in quality) / len(quality)
    intervention_by_cause = {row["target_root_cause"]: row for row in interventions}

    root_rows = []
    scenario_rows = []
    action_rows = []

    for index, segment in enumerate(SEGMENTS):
        history = by_segment[segment["segment_id"]]
        avg_delinq = sum(float(row["delinquency_rate"]) for row in history) / len(history)
        avg_contact = sum(float(row["contact_rate"]) for row in history) / len(history)
        avg_completion = sum(float(row["application_completion_rate"]) for row in history) / len(history)
        avg_resolution = sum(float(row["first_contact_resolution_rate"]) for row in history) / len(history)
        avg_approval = sum(float(row["approval_rate"]) for row in history) / len(history)
        autopay_gap = 1 - segment["autopay"]
        volatility = max(float(row["delinquency_rate"]) for row in history) - min(float(row["delinquency_rate"]) for row in history)
        theme = theme_cycle[index % len(theme_cycle)]

        cause_scores = {
            "Repayment plan mismatch": segment["income_pressure"] * 45 + avg_delinq * 160,
            "Autopay and payment friction": autopay_gap * 52 + avg_contact * 80,
            "Servicing clarity gap": float(theme["share"]) * 120 + avg_contact * 60 + (1 - avg_resolution) * 55,
            "Credit-policy edge case": volatility * 380 + (1 - avg_approval) * 45,
            "Metric definition drift": (1 - quality_confidence) * 120 + (1 - avg_completion) * 22,
        }
        primary_cause = max(cause_scores, key=cause_scores.get)
        cause_score = cause_scores[primary_cause]
        confidence = min(0.96, 0.72 + quality_confidence * 0.18 - volatility * 0.7)
        exposed_balance = segment["borrowers"] * segment["avg_balance"]
        expected_loss_risk = exposed_balance * avg_delinq * 0.035
        priority_score = (
            avg_delinq * 360
            + avg_contact * 120
            + segment["income_pressure"] * 28
            + autopay_gap * 16
            + cause_score * 0.38
        )
        intervention = intervention_by_cause[primary_cause]
        modeled_lift = float(intervention["expected_delinquency_lift"])
        annualized_value = expected_loss_risk * (modeled_lift / max(avg_delinq, 0.01))
        implementation_cost = int(intervention["effort_score"]) * 18500 + segment["borrowers"] * 0.18
        net_value = annualized_value - implementation_cost

        root_rows.append(
            {
                "segment_id": segment["segment_id"],
                "segment": segment["segment"],
                "product": segment["product"],
                "primary_root_cause": primary_cause,
                "public_theme_signal": theme["borrower_signal"],
                "avg_delinquency_rate": round(avg_delinq, 4),
                "avg_contact_rate": round(avg_contact, 4),
                "avg_application_completion_rate": round(avg_completion, 4),
                "avg_first_resolution_rate": round(avg_resolution, 4),
                "autopay_gap": round(autopay_gap, 4),
                "confidence": round(confidence, 4),
                "priority_score": round(priority_score, 1),
                "expected_loss_risk": money(expected_loss_risk),
                "recommended_action": intervention["intervention"],
                "action_owner": intervention["owner"],
                "modeled_net_value": money(net_value),
            }
        )

        for scenario, lift_mult, contact_mult in [
            ("Control", 0.0, 0.0),
            ("Focused outreach", modeled_lift * 0.65, float(intervention["expected_contact_reduction"]) * 0.55),
            ("Full playbook", modeled_lift, float(intervention["expected_contact_reduction"])),
        ]:
            new_delinq = max(0.01, avg_delinq - lift_mult)
            new_contact = max(0.02, avg_contact - contact_mult)
            scenario_value = expected_loss_risk * ((avg_delinq - new_delinq) / max(avg_delinq, 0.01))
            scenario_rows.append(
                {
                    "segment_id": segment["segment_id"],
                    "segment": segment["segment"],
                    "scenario": scenario,
                    "forecast_delinquency_rate": round(new_delinq, 4),
                    "forecast_contact_rate": round(new_contact, 4),
                    "annualized_value": money(scenario_value),
                    "operating_cost": money(implementation_cost if scenario == "Full playbook" else implementation_cost * 0.55 if scenario == "Focused outreach" else 0),
                }
            )

        action_rows.append(
            {
                "rank": 0,
                "segment_id": segment["segment_id"],
                "segment": segment["segment"],
                "recommendation": intervention["intervention"],
                "decision_reason": f"{primary_cause} is driving {pct(avg_delinq)} percent delinquency and {pct(avg_contact)} percent contact demand.",
                "owner": intervention["owner"],
                "confidence": round(confidence, 4),
                "modeled_net_value": money(net_value),
                "first_30_days": first_30_days(primary_cause),
            }
        )

    root_rows.sort(key=lambda row: row["priority_score"], reverse=True)
    action_rows.sort(key=lambda row: row["modeled_net_value"], reverse=True)
    for rank, row in enumerate(action_rows, start=1):
        row["rank"] = rank

    write_csv(
        OUTPUTS / "root_cause_queue.csv",
        root_rows,
        [
            "segment_id",
            "segment",
            "product",
            "primary_root_cause",
            "public_theme_signal",
            "avg_delinquency_rate",
            "avg_contact_rate",
            "avg_application_completion_rate",
            "avg_first_resolution_rate",
            "autopay_gap",
            "confidence",
            "priority_score",
            "expected_loss_risk",
            "recommended_action",
            "action_owner",
            "modeled_net_value",
        ],
    )
    write_csv(
        OUTPUTS / "scenario_forecast.csv",
        scenario_rows,
        [
            "segment_id",
            "segment",
            "scenario",
            "forecast_delinquency_rate",
            "forecast_contact_rate",
            "annualized_value",
            "operating_cost",
        ],
    )
    write_csv(
        OUTPUTS / "cohort_action_plan.csv",
        action_rows,
        [
            "rank",
            "segment_id",
            "segment",
            "recommendation",
            "decision_reason",
            "owner",
            "confidence",
            "modeled_net_value",
            "first_30_days",
        ],
    )

    return root_rows, scenario_rows, action_rows


def first_30_days(cause):
    return {
        "Repayment plan mismatch": "Flag borrowers 21 days before risk threshold, route plan-fit script, measure cure lift weekly.",
        "Autopay and payment friction": "Launch retry logic holdout, monitor successful payment recovery, publish owner readout.",
        "Servicing clarity gap": "Rewrite two highest-volume help flows, QA response macros, track avoidable repeat contacts.",
        "Credit-policy edge case": "Review declined edge cases, isolate policy variables, size conversion versus risk tradeoff.",
        "Metric definition drift": "Assign metric owner, freeze grain, add reconciliation query to weekly operating review.",
    }[cause]


def build_summary(segments, daily, themes, complaint_total, root_rows, scenario_rows, action_rows, quality):
    total_borrowers = sum(int(row["borrowers"]) for row in segments)
    avg_delinq = sum(float(row["avg_delinquency_rate"]) for row in root_rows) / len(root_rows)
    weighted_autopay = sum(float(row["autopay_rate"]) * int(row["borrowers"]) for row in segments) / total_borrowers
    total_balance = sum(int(row["annualized_balance"]) for row in segments)
    top_action = action_rows[0]
    full_playbook_value = sum(
        int(row["annualized_value"]) - int(row["operating_cost"])
        for row in scenario_rows
        if row["scenario"] == "Full playbook"
    )
    data_trust = sum(float(row["confidence"]) for row in quality) / len(quality)

    summary = {
        "metrics": [
            {"label": "Modeled borrowers", "value": f"{total_borrowers:,}", "note": "six strategy cohorts"},
            {"label": "Avg delinquency", "value": f"{pct(avg_delinq)}%", "note": "120-day modeled window"},
            {"label": "Autopay coverage", "value": f"{pct(weighted_autopay)}%", "note": "portfolio weighted"},
            {"label": "Net scenario value", "value": f"${full_playbook_value/1000000:.1f}M", "note": "full playbook model"},
        ],
        "portfolio": {
            "borrowers": total_borrowers,
            "annualized_balance": total_balance,
            "complaint_rows_profiled": complaint_total,
            "data_trust_score": round(data_trust, 3),
            "top_recommendation": top_action["recommendation"],
            "top_segment": top_action["segment"],
        },
        "themeRollup": themes,
        "rootCauseQueue": root_rows,
        "scenarioForecast": scenario_rows,
        "actionPlan": action_rows,
        "qualityChecks": quality,
    }
    (OUTPUTS / "summary.json").write_text(json.dumps(summary, indent=2))

    js_payload = "export const dashboardData = " + json.dumps(summary, indent=2) + ";\n"
    (SRC / "data.js").write_text(js_payload)
    return summary


def write_docs(summary, root_rows, action_rows):
    top = root_rows[0]
    action = action_rows[0]
    findings = f"""# Executive Findings

## What I Analyzed

I combined a public CFPB student-loan complaint sample with a synthetic borrower portfolio, daily performance metrics, intervention assumptions, and data-quality checks. The goal was to turn borrower strategy signals into a decision artifact for product, operations, and leadership.

## Findings

- The highest-priority cohort is {top["segment"]}, with a {pct(float(top["avg_delinquency_rate"]))}% modeled delinquency rate and {pct(float(top["avg_contact_rate"]))}% contact demand.
- The strongest root-cause signal is {top["primary_root_cause"]}, linked to {top["public_theme_signal"]} in the public complaint taxonomy.
- The modeled full-playbook scenario creates ${summary["portfolio"]["annualized_balance"] / 1000000000:.1f}B of portfolio context and ${sum(int(row["modeled_net_value"]) for row in action_rows) / 1000000:.1f}M of ranked net-value opportunity.
- Data trust is {pct(summary["portfolio"]["data_trust_score"])}%, with the largest watch item tied to source timing and taxonomy mapping.

## Recommendation

Start with {action["recommendation"]} for {action["segment"]}. Run it as a 30-day operating pilot with named owners, weekly SQL checks, and a holdout readout before scaling.
"""
    (ROOT / "analysis" / "executive_findings.md").write_text(findings)

    plan = """# Analysis Plan

1. Profile public student-loan complaint issues to identify external borrower-friction themes.
2. Generate protected internal-style borrower cohorts with repayment, application, contact, and payment signals.
3. Score each cohort with an explainable root-cause model using delinquency, contact demand, autopay gap, application completion, complaint theme, and data confidence.
4. Convert the root-cause queue into recommendations with owners, first-30-day actions, and modeled value.
5. Forecast control, focused outreach, and full-playbook scenarios to support a leadership tradeoff discussion.
6. Maintain SQL-style checks so every recommendation can be traced back to grain, owner, and source quality.
"""
    (ROOT / "analysis" / "analysis_plan.md").write_text(plan)

    methodology = """# Methodology

The workbench uses a transparent scoring model rather than an opaque machine-learning model. That choice matches a business analyst workflow where leaders need to understand the recommendation, challenge the assumptions, and assign owners quickly.

## Data Sources

- Public complaint themes come from a CFPB student-loan complaint download. The raw public file is used locally for issue taxonomy and is summarized into `data/public_complaint_themes.csv`.
- Borrower segments, daily metrics, intervention effects, and quality checks are synthetic. They are modeled on common lending operations structures: product type, channel, borrower count, average balance, delinquency, contact demand, application conversion, payment behavior, and servicing quality.

## Scoring Logic

The root-cause score combines delinquency rate, contact demand, income-pressure proxy, autopay gap, complaint theme concentration, metric confidence, approval rate, and volatility. Each cohort receives a primary root cause and a recommended intervention. Scenario value estimates the avoided loss risk from reducing delinquency, net of implementation effort.

## Why This Is Defensible

The artifact separates public external evidence from synthetic protected portfolio data. It does not claim to represent any lender's actual performance. It is designed to demonstrate how a borrower strategy analyst would structure ambiguity, check data quality, quantify tradeoffs, and recommend action.
"""
    (ROOT / "analysis" / "methodology.md").write_text(methodology)

    sql = """-- Borrower strategy root-cause SQL appendix
-- These examples are written in warehouse-style SQL for interview discussion.

-- 1. Cohort-level borrower health rollup.
with cohort_daily as (
  select
    segment_id,
    avg(delinquency_rate) as avg_delinquency_rate,
    avg(contact_rate) as avg_contact_rate,
    avg(application_completion_rate) as avg_application_completion_rate,
    avg(first_contact_resolution_rate) as avg_first_resolution_rate,
    avg(autopay_rate) as avg_autopay_rate
  from daily_borrower_metrics
  group by 1
)
select
  s.product,
  s.segment,
  c.avg_delinquency_rate,
  c.avg_contact_rate,
  c.avg_application_completion_rate,
  c.avg_first_resolution_rate,
  1 - c.avg_autopay_rate as autopay_gap
from cohort_daily c
join borrower_segments s
  on s.segment_id = c.segment_id
order by c.avg_delinquency_rate desc;

-- 2. Metric confidence gate before a recommendation is promoted.
select
  dataset,
  min(confidence) as lowest_confidence,
  sum(case when status = 'Fix' then 1 else 0 end) as fix_count,
  sum(case when status = 'Watch' then 1 else 0 end) as watch_count
from data_quality_checks
group by 1
having min(confidence) < 0.92
   or sum(case when status = 'Fix' then 1 else 0 end) > 0;

-- 3. Scenario economics for leadership tradeoff review.
select
  segment,
  scenario,
  forecast_delinquency_rate,
  annualized_value - operating_cost as modeled_net_value
from scenario_forecast
where scenario in ('Focused outreach', 'Full playbook')
order by modeled_net_value desc;
"""
    (ROOT / "analysis" / "sql_checks.sql").write_text(sql)


def main():
    DATA.mkdir(exist_ok=True)
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    SRC.mkdir(exist_ok=True)

    themes, complaint_total, _, _ = complaint_themes()
    segments = segment_rows()
    daily = build_daily_metrics()
    quality = quality_rows()
    interventions = intervention_rows()
    root_rows, scenario_rows, action_rows = aggregate(daily, themes, quality, interventions)
    summary = build_summary(segments, daily, themes, complaint_total, root_rows, scenario_rows, action_rows, quality)
    write_docs(summary, root_rows, action_rows)

    print("Borrower strategy workbench generated")
    print(f"Public complaint rows profiled: {complaint_total:,}")
    print(f"Top cohort: {summary['portfolio']['top_segment']}")
    print(f"Top recommendation: {summary['portfolio']['top_recommendation']}")


if __name__ == "__main__":
    main()
