"""
Nyaypath — backend.py
=====================
All data fetching, filtering, profiling and scoring logic.
Called by app.py via analyze_lawyer().

Changes from previous version:
- No composite trust score
- No complexity score (iaCount removed)
- No court_codes parameter exposed in UI
- Petitioner-only filter
- Full courts list (no cap)
- Current year + last year case counts
- Case type decoded throughout
"""

import re
import time
import requests
import numpy as np
import pandas as pd
from datetime import datetime
from collections import Counter

# ── Case type lookup ──────────────────────────────────────────────────

CASE_TYPES = {
    # Family
    "DV":    {"full_name": "Domestic Violence",                "domain": "Family",         "act": "PWDV Act, 2005"},
    "DIV":   {"full_name": "Divorce Petition",                 "domain": "Family",         "act": "Hindu Marriage Act"},
    "HMA":   {"full_name": "Hindu Marriage Act Petition",      "domain": "Family",         "act": "Hindu Marriage Act, 1955"},
    "MA":    {"full_name": "Matrimonial Appeal / Maintenance", "domain": "Family",         "act": "HMA / CrPC Sec 125"},
    "MNT":   {"full_name": "Maintenance Application",          "domain": "Family",         "act": "CrPC Section 125"},
    "GD":    {"full_name": "Guardianship / Custody",           "domain": "Family",         "act": "Hindu Minority & Guardianship Act"},
    "CA":    {"full_name": "Child Adoption / Custody",         "domain": "Family",         "act": "Hindu Adoption Act / JJ Act"},
    "DIS":   {"full_name": "Dissolution of Marriage",          "domain": "Family",         "act": "Hindu Marriage Act"},
    "RES":   {"full_name": "Restitution of Conjugal Rights",   "domain": "Family",         "act": "HMA Section 9"},
    "VOID":  {"full_name": "Void / Voidable Marriage",         "domain": "Family",         "act": "HMA Section 11/12"},
    "DPA":   {"full_name": "Dowry Prohibition Act Case",       "domain": "Family",         "act": "Dowry Prohibition Act, 1961"},
    "SMA":   {"full_name": "Special Marriage Act Petition",    "domain": "Family",         "act": "Special Marriage Act, 1954"},
    "498A":  {"full_name": "Cruelty by Husband / Relatives",   "domain": "Criminal",       "act": "IPC Section 498A"},
    # Criminal
    "BA":    {"full_name": "Bail Application",                 "domain": "Criminal",       "act": "CrPC Section 437/439"},
    "ABP":   {"full_name": "Anticipatory Bail Petition",       "domain": "Criminal",       "act": "CrPC Section 438"},
    "SC":    {"full_name": "Sessions Case",                    "domain": "Criminal",       "act": "CrPC / IPC"},
    "CC":    {"full_name": "Criminal Complaint Case",          "domain": "Criminal",       "act": "CrPC / IPC"},
    "CR":    {"full_name": "Criminal Revision",                "domain": "Criminal",       "act": "CrPC Section 397"},
    "CRL":   {"full_name": "Criminal Appeal",                  "domain": "Criminal",       "act": "CrPC Section 374"},
    "ST":    {"full_name": "Sessions Trial",                   "domain": "Criminal",       "act": "CrPC / IPC"},
    "FIR":   {"full_name": "FIR / Police Complaint",           "domain": "Criminal",       "act": "CrPC Section 154"},
    # Civil
    "CS":    {"full_name": "Civil Suit",                       "domain": "Civil",          "act": "CPC"},
    "OP":    {"full_name": "Original Petition",                "domain": "Civil",          "act": "CPC"},
    "EP":    {"full_name": "Execution Petition",               "domain": "Civil",          "act": "CPC Order 21"},
    "IA":    {"full_name": "Interlocutory Application",        "domain": "Civil",          "act": "CPC Order 39"},
    "RCA":   {"full_name": "Regular Civil Appeal",             "domain": "Civil",          "act": "CPC Section 96"},
    "SA":    {"full_name": "Second Appeal",                    "domain": "Civil",          "act": "CPC Section 100"},
    "ARB":   {"full_name": "Arbitration Case",                 "domain": "Civil",          "act": "Arbitration Act, 1996"},
    "MACT":  {"full_name": "Motor Accident Claim",             "domain": "Civil",          "act": "Motor Vehicles Act, 1988"},
    # Constitutional
    "WP":    {"full_name": "Writ Petition",                    "domain": "Constitutional", "act": "Constitution Article 226"},
    "PIL":   {"full_name": "Public Interest Litigation",       "domain": "Constitutional", "act": "Constitution Article 32/226"},
    "SLP":   {"full_name": "Special Leave Petition",           "domain": "Constitutional", "act": "Constitution Article 136"},
    # Property
    "TP":    {"full_name": "Transfer / Property Dispute",      "domain": "Property",       "act": "Transfer of Property Act"},
    "LAC":   {"full_name": "Land Acquisition Case",            "domain": "Property",       "act": "Land Acquisition Act"},
    # Misc
    "MC":    {"full_name": "Miscellaneous Case",               "domain": "Miscellaneous",  "act": "Various"},
    "CON":   {"full_name": "Consumer Complaint",               "domain": "Consumer",       "act": "Consumer Protection Act, 2019"},
}

COURT_TIER = {
    "SUPREME COURT":           5,
    "HIGH COURT":              4,
    "DISTRICT COURT":          3,
    "SESSIONS COURT":          3,
    "CITY CIVIL":              3,
    "FAMILY COURT":            2,
    "CONSUMER FORUM":          2,
    "TRIBUNAL":                2,
    "MAGISTRATE":              1,
    "CHIEF JUDICIAL MAGISTRATE": 1,
    "JUDICIAL MAGISTRATE":     1,
}

TIER_LABELS = {
    5: "Supreme Court",
    4: "High Court",
    3: "District / Sessions Court",
    2: "Family / Consumer Court",
    1: "Magistrate Court",
}


# ── Utility helpers ───────────────────────────────────────────────────

def as_list(value):
    """Safely convert any value to a list."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    try:
        if pd.isna(value):
            return []
    except Exception:
        pass
    return [value]

def to_joined_text(value):
    return ", ".join(str(x) for x in as_list(value) if str(x).strip())

def normalise_name(raw):
    """Strip ADV., MR., MS. etc. and normalise whitespace."""
    cleaned = re.sub(
        r"\b(ADV\.?|MR\.?|MS\.?|MRS\.?|DR\.?|ADVOCATE\.?)\s*",
        "", str(raw), flags=re.IGNORECASE
    )
    cleaned = re.sub(r"[^\w\s]", "", cleaned)
    return " ".join(cleaned.upper().split())

def name_in_field(raw_field, target_norm):
    """Check if target name is in comma-separated advocate field."""
    names = [normalise_name(x) for x in as_list(raw_field)]
    return target_norm in names

def decode_case_type(abbr):
    key  = str(abbr).strip().upper()
    info = CASE_TYPES.get(key)
    if info:
        return {"abbr": key, **info}
    return {"abbr": key, "full_name": f"Other ({key})", "domain": "Other", "act": "—"}

def get_court_tier(court_name):
    if pd.isna(court_name):
        return 1
    upper = str(court_name).upper()
    for kw, tier in COURT_TIER.items():
        if kw in upper:
            return tier
    return 2

def build_case_title(row):
    pet = as_list(row.get("petitioners"))
    res = as_list(row.get("respondents"))
    return f"{pet[0] if pet else 'Unknown'} vs {res[0] if res else 'Unknown'}"


# ── API fetch (paginated) ─────────────────────────────────────────────

def fetch_cases(
    advocate_name: str,
    api_key: str,
    api_url: str,
    date_from: str,
    date_to: str,
    page_size: int = 100,
    max_pages: int = 200,
    court_codes: str | None = None,
    retry_limit: int = 3,
    retry_delay: int = 2,
) -> pd.DataFrame:
    """
    Fetch all cases for an advocate from eCourts API with pagination.
    Returns raw DataFrame (petitioner + respondent appearances combined).
    """
    headers  = {"Authorization": f"Bearer {api_key}"}
    all_rows = []
    page     = 1

    while page <= max_pages:
        params = {
            "advocates":      advocate_name,
            "filingDateFrom": date_from,
            "filingDateTo":   date_to,
            "sortBy":         "filingDate",
            "sortOrder":      "desc",
            "page":           page,
            "pageSize":       page_size,
        }
        if court_codes:
            params["courtCodes"] = court_codes

        resp = None
        for attempt in range(1, retry_limit + 1):
            try:
                resp = requests.get(api_url, headers=headers,
                                    params=params, timeout=30)
                break
            except requests.RequestException:
                if attempt == retry_limit:
                    raise
                time.sleep(retry_delay)

        if resp is None:
            break

        resp.raise_for_status()
        payload      = resp.json()
        data         = payload.get("data", {})
        results      = data.get("results", [])
        has_next     = data.get("hasNextPage", False)

        if not results:
            break

        all_rows.extend(results)

        if not has_next:
            break

        page += 1
        time.sleep(0.2)

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)
    df["case_title"] = df.apply(build_case_title, axis=1)
    return df


# ── Petitioner filter ─────────────────────────────────────────────────

def filter_petitioner_cases(df: pd.DataFrame, advocate_name: str) -> pd.DataFrame:
    """
    Keep ONLY cases where advocate appears in petitionerAdvocates.
    Profile = cases the lawyer INITIATED, not cases they defended.
    """
    if df.empty or "petitionerAdvocates" not in df.columns:
        return pd.DataFrame()

    target = normalise_name(advocate_name)
    mask   = df["petitionerAdvocates"].apply(lambda x: name_in_field(x, target))
    return df[mask].copy().reset_index(drop=True)


# ── Prepare / decode ──────────────────────────────────────────────────

def prepare(df: pd.DataFrame) -> pd.DataFrame:
    """Cast columns, decode case types, add derived fields."""
    df = df.copy()

    # Dates
    for col in ["filingDate", "registrationDate", "decisionDate",
                "firstHearingDate", "lastHearingDate", "nextHearingDate"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Numerics
    for col in ["caseDurationDays", "filingToFirstHearingDays",
                "hearingCount", "orderCount", "interimOrderCount", "judgmentCount"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Booleans
    for col in ["hasJudgments", "hasOrders"]:
        if col in df.columns:
            df[col] = df[col].astype(bool, errors="ignore")

    # Decode case type → adds case_type_full, domain, governing_act
    if "caseType" in df.columns:
        decoded          = df["caseType"].apply(decode_case_type).apply(pd.Series)
        df["case_type_full"] = decoded["full_name"]
        df["domain"]         = decoded["domain"]
        df["governing_act"]  = decoded["act"]

    # Court tier
    df["court_tier"] = df["courtName"].apply(get_court_tier) \
        if "courtName" in df.columns else 2

    # Filing year
    if "filingDate" in df.columns:
        df["filing_year"] = df["filingDate"].dt.year

    # Text versions of list columns (for display)
    for col in ["judges", "petitioners", "respondents",
                "actsAndSections", "petitionerAdvocates"]:
        if col in df.columns:
            df[f"{col}_text"] = df[col].apply(to_joined_text)

    return df


# ── Build profile ─────────────────────────────────────────────────────

def build_profile(
    advocate_name: str,
    df: pd.DataFrame,
    date_from: str,
    date_to: str,
) -> dict:
    """
    Build structured profile from petitioner-only prepared dataframe.
    Returns dict with 5 sections: identity, volume, outcomes, case_types, activity.
    """
    total = len(df)
    if total == 0:
        return {}

    today        = pd.Timestamp(datetime.today().date())
    current_year = datetime.today().year
    last_year    = current_year - 1

    disposed = df[df["caseStatus"].astype(str).str.upper() == "DISPOSED"] \
        if "caseStatus" in df.columns else pd.DataFrame()
    pending  = df[df["caseStatus"].astype(str).str.upper() == "PENDING"] \
        if "caseStatus" in df.columns else pd.DataFrame()

    # ── Section 1: Identity ───────────────────────────────────────
    all_courts    = sorted(df["courtName"].dropna().astype(str).unique().tolist()) \
        if "courtName" in df.columns else []
    all_states    = sorted(df["stateCode"].dropna().astype(str).unique().tolist()) \
        if "stateCode" in df.columns else []
    all_districts = sorted(df["districtCode"].dropna().astype(str).unique().tolist()) \
        if "districtCode" in df.columns else []

    max_tier        = int(df["court_tier"].max()) if "court_tier" in df.columns else 2
    first_case_date = str(df["filingDate"].min().date()) \
        if "filingDate" in df.columns and df["filingDate"].notna().any() else None

    identity = {
        "advocate_name":      advocate_name,
        "normalised_name":    normalise_name(advocate_name),
        "all_courts":         all_courts,
        "total_courts":       len(all_courts),
        "states_covered":     all_states,
        "districts_covered":  all_districts,
        "highest_court_tier": TIER_LABELS.get(max_tier, "Unknown"),
        "first_case_on_record": first_case_date,
    }

    # ── Section 2: Volume ────────────────────────────────────────
    year_counts = {}
    if "filing_year" in df.columns:
        yc = df["filing_year"].value_counts().sort_index()
        year_counts = {int(k): int(v) for k, v in yc.items() if pd.notna(k)}

    current_yr_count = int(df[df["filing_year"] == current_year].shape[0]) \
        if "filing_year" in df.columns else 0
    last_yr_count    = int(df[df["filing_year"] == last_year].shape[0]) \
        if "filing_year" in df.columns else 0
    last_12m_count   = int(
        df[df["filingDate"] >= today - pd.DateOffset(years=1)].shape[0]
    ) if "filingDate" in df.columns else 0

    volume = {
        "total_petitioner_cases": total,
        "current_year_count":     current_yr_count,
        "last_year_count":        last_yr_count,
        "last_12_months_count":   last_12m_count,
        "year_by_year":           year_counts,
    }

    # ── Section 3: Outcomes ───────────────────────────────────────
    disposed_count = len(disposed)
    pending_count  = len(pending)
    disposed_pct   = round(disposed_count / total * 100, 1) if total else 0
    pending_pct    = round(pending_count  / total * 100, 1) if total else 0

    with_judgments = int(df["hasJudgments"].sum()) \
        if "hasJudgments" in df.columns else 0
    judgment_pct   = round(with_judgments / total * 100, 1) if total else 0

    with_orders    = int(df["hasOrders"].sum()) \
        if "hasOrders" in df.columns else 0
    orders_pct     = round(with_orders / total * 100, 1) if total else 0

    median_duration = mean_duration = None
    if "caseDurationDays" in df.columns and disposed_count > 0:
        dur             = disposed["caseDurationDays"].dropna()
        median_duration = round(dur.median(), 0) if len(dur) else None
        mean_duration   = round(dur.mean(),   0) if len(dur) else None

    median_filing_to_first = None
    if "filingToFirstHearingDays" in df.columns:
        ftf = df["filingToFirstHearingDays"].dropna()
        median_filing_to_first = round(ftf.median(), 0) if len(ftf) else None

    avg_hearings = None
    if "hearingCount" in df.columns:
        hc           = df["hearingCount"].dropna()
        avg_hearings = round(hc.mean(), 1) if len(hc) else None

    # Court avg duration for same top case type
    court_avg_duration = None
    if "caseType" in df.columns and "caseDurationDays" in df.columns \
            and disposed_count > 0:
        top_type = df["caseType"].value_counts().index[0] \
            if len(df["caseType"].value_counts()) else None
        if top_type is not None:
            same = disposed[disposed["caseType"] == top_type]["caseDurationDays"].dropna()
            if len(same) > 1:
                court_avg_duration = round(same.median(), 0)

    outcomes = {
        "disposed_count":                    disposed_count,
        "disposed_pct":                      disposed_pct,
        "pending_count":                     pending_count,
        "pending_pct":                       pending_pct,
        "with_judgments_count":              with_judgments,
        "with_judgments_pct":                judgment_pct,
        "with_orders_count":                 with_orders,
        "with_orders_pct":                   orders_pct,
        "median_case_duration_days":         median_duration,
        "mean_case_duration_days":           mean_duration,
        "court_avg_duration_days":           court_avg_duration,
        "median_filing_to_first_hearing_days": median_filing_to_first,
        "avg_hearings_per_case":             avg_hearings,
    }

    # ── Section 4: Case types ─────────────────────────────────────
    case_type_breakdown = []
    if "caseType" in df.columns:
        ct_counts = df["caseType"].value_counts()
        for abbr, count in ct_counts.items():
            info = decode_case_type(abbr)
            case_type_breakdown.append({
                "abbreviation": abbr,
                "full_name":    info["full_name"],
                "domain":       info["domain"],
                "act":          info["act"],
                "count":        int(count),
                "pct":          round(count / total * 100, 1),
            })

    domain_breakdown = {}
    if "domain" in df.columns:
        dc = df["domain"].value_counts()
        domain_breakdown = {
            k: {"count": int(v), "pct": round(v / total * 100, 1)}
            for k, v in dc.items()
        }

    case_types = {
        "case_type_breakdown": case_type_breakdown,
        "domain_breakdown":    domain_breakdown,
    }

    # ── Section 5: Activity & availability ───────────────────────
    last_hearing_date = days_since = None
    if "lastHearingDate" in df.columns:
        lh = df["lastHearingDate"].max()
        if pd.notna(lh):
            last_hearing_date = str(lh.date())
            days_since        = int((today - lh).days)

    next_hearing_date = None
    if "nextHearingDate" in df.columns:
        future = df["nextHearingDate"].dropna()
        future = future[future > today]
        if len(future):
            next_hearing_date = str(future.min().date())

    last_filing_date = None
    if "filingDate" in df.columns:
        lf = df["filingDate"].max()
        if pd.notna(lf):
            last_filing_date = str(lf.date())

    activity = {
        "last_court_appearance":      last_hearing_date,
        "days_since_last_appearance": days_since,
        "next_scheduled_hearing":     next_hearing_date,
        "current_open_caseload":      pending_count,
        "last_filing_date":           last_filing_date,
    }

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "date_from":    date_from,
        "date_to":      date_to,
        "identity":     identity,
        "volume":       volume,
        "outcomes":     outcomes,
        "case_types":   case_types,
        "activity":     activity,
        "raw_df":       df,
    }


# ── Compute 4 scores ──────────────────────────────────────────────────

def compute_scores(profile: dict) -> dict:
    """
    4 independent scores (0–100). No composite. No domain weighting.

    1. Competence  — disposal rate + judgment rate + court tier
    2. Availability — pending caseload + calendar density
    3. Case speed  — median duration vs court avg + hearing frequency
    4. Activity    — recency of last appearance + recent filing count
    """
    outcomes = profile["outcomes"]
    activity = profile["activity"]
    volume   = profile["volume"]
    df       = profile["raw_df"]
    total    = volume["total_petitioner_cases"]
    today    = pd.Timestamp(datetime.today().date())

    scores = {}

    # ── 1. Competence ─────────────────────────────────────────────
    disposal_pts = min(outcomes["disposed_pct"] / 100 * 50, 50)
    judgment_pts = min(outcomes["with_judgments_pct"] / 100 * 50, 30)
    max_tier_val = int(df["court_tier"].max()) if "court_tier" in df.columns else 2
    court_pts    = min(max_tier_val * 4, 20)

    scores["competence"] = min(round(disposal_pts + judgment_pts + court_pts), 100)

    # ── 2. Availability ───────────────────────────────────────────
    PLATFORM_P95 = 20
    pending      = outcomes["pending_count"]
    load_ratio   = pending / PLATFORM_P95 if PLATFORM_P95 > 0 else 0
    load_pts     = max(0, (1 - load_ratio) * 70)

    next7 = 0
    if "nextHearingDate" in df.columns:
        future  = df["nextHearingDate"].dropna()
        days_to = (future - today).dt.days
        next7   = int(days_to.between(0, 7).sum())

    cal_penalty = min(max(0, (next7 - 5) * 3), 30)
    scores["availability"] = min(round(load_pts + (30 - cal_penalty)), 100)

    # ── 3. Case speed ─────────────────────────────────────────────
    lawyer_median = outcomes["median_case_duration_days"]
    court_avg     = outcomes["court_avg_duration_days"]

    if lawyer_median and court_avg and court_avg > 0:
        ratio     = lawyer_median / court_avg
        speed_pts = min(50 + (1 - ratio) * 50, 100) if ratio <= 1 \
                    else max(0, 50 - (ratio - 1) * 50)
    else:
        speed_pts = 50

    avg_h = outcomes["avg_hearings_per_case"] or 0
    if avg_h > 0:
        if avg_h < 5:
            speed_pts = min(speed_pts + 10, 100)
        elif avg_h > 15:
            speed_pts = max(speed_pts - 15, 0)

    scores["case_speed"] = round(speed_pts)

    # ── 4. Activity ───────────────────────────────────────────────
    days = activity["days_since_last_appearance"]
    if days is None:         activity_pts = 0
    elif days <= 30:         activity_pts = 100
    elif days <= 90:         activity_pts = 80
    elif days <= 180:        activity_pts = 60
    elif days <= 365:        activity_pts = 30
    else:                    activity_pts = 0

    filed_12m = volume["last_12_months_count"]
    if filed_12m >= 10:
        activity_pts = min(activity_pts + 10, 100)
    elif filed_12m == 0:
        activity_pts = max(activity_pts - 20, 0)

    scores["activity"] = round(activity_pts)

    # ── Data quality flag ─────────────────────────────────────────
    if total < 5:    scores["data_quality"] = "Insufficient data (< 5 cases)"
    elif total < 20: scores["data_quality"] = "Limited data (< 20 cases)"
    else:            scores["data_quality"] = "Good data quality"

    return scores


# ── Main entry point ──────────────────────────────────────────────────

def analyze_lawyer(
    advocate_name: str,
    api_key: str,
    api_url: str,
    date_from: str,
    date_to: str,
    page_size: int,
    max_pages: int,
    court_codes: str | None = None,
):
    """
    Full pipeline: fetch → filter → prepare → profile → score.
    Returns (profile, scores, petitioner_df).
    """
    raw_df = fetch_cases(
        advocate_name=advocate_name,
        api_key=api_key,
        api_url=api_url,
        date_from=date_from,
        date_to=date_to,
        page_size=page_size,
        max_pages=max_pages,
        court_codes=court_codes,
    )

    if raw_df.empty:
        return {}, {}, pd.DataFrame()

    pet_df = filter_petitioner_cases(raw_df, advocate_name)
    if pet_df.empty:
        return {}, {}, pd.DataFrame()

    pet_df  = prepare(pet_df)
    profile = build_profile(advocate_name, pet_df, date_from, date_to)
    scores  = compute_scores(profile)

    return profile, scores, pet_df