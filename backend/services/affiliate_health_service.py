"""
Affiliate activation & engagement metrics — Monthly Active Affiliates
(MAA) as the primary north-star, plus the funnel around it: activation,
retention, revenue concentration, and time-to-first-sale.

"Activated" = at least one of: downloaded a marketing asset, clicked
their own referral link (a real /r/CODE visit), or generated a sale.
"Active" (for MAA/retention) = a click or a sale within the window —
downloads alone don't count as ongoing activity, only as the initial
activation signal.
"""
from datetime import datetime, timedelta, timezone


def _ensure_utc(dt: datetime) -> datetime:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _month_bounds(now: datetime, months_ago: int):
    """UTC boundaries for monthly health metrics."""
    now_utc = _ensure_utc(now)
    year = now_utc.year
    month = now_utc.month - months_ago
    while month <= 0:
        month += 12
        year -= 1
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    end = datetime(year + 1, 1, 1, tzinfo=timezone.utc) if month == 12 else datetime(year, month + 1, 1, tzinfo=timezone.utc)
    return start, end


async def _active_codes_between(db, start, end) -> set:
    click_codes = set(await db.referral_clicks.distinct("affiliate_code", {"created_at": {"$gte": start, "$lt": end}}))
    referral_codes = set(await db.referrals.distinct("affiliate_code", {"created_at": {"$gte": start, "$lt": end}}))
    return click_codes | referral_codes


async def compute_affiliate_health(db) -> dict:
    now = datetime.now(timezone.utc)
    month_start, _ = _month_bounds(now, 0)
    thirty_days_ago = now - timedelta(days=30)

    affiliates = await db.affiliates.find({}).to_list(5000)
    total_registered = len(affiliates)
    new_this_month = sum(1 for a in affiliates if _ensure_utc(a["created_at"]) >= month_start)

    # ── Activation (ever) ──────────────────────────────────────────────
    all_click_codes = set(await db.referral_clicks.distinct("affiliate_code"))
    all_referral_codes = set(await db.referrals.distinct("affiliate_code"))
    all_download_codes = set(await db.marketing_asset_downloads.distinct("affiliate_code"))
    all_video_click_codes = set(await db.marketing_video_clicks.distinct("affiliate_code"))
    activated_codes = all_click_codes | all_referral_codes | all_download_codes | all_video_click_codes
    activation_rate = round(100 * len(activated_codes) / total_registered, 1) if total_registered else 0.0

    # ── MAA (trailing 30 days) + 6-month trend ─────────────────────────
    maa_codes = await _active_codes_between(db, thirty_days_ago, now + timedelta(seconds=1))
    maa_current = len(maa_codes)

    trend = []
    for i in range(5, -1, -1):
        m_start, m_end = _month_bounds(now, i)
        codes = await _active_codes_between(db, m_start, m_end)
        trend.append({"month": m_start.strftime("%Y-%m"), "maa": len(codes)})

    # ── Retention: active last calendar month AND active this month ────
    last_month_start, last_month_end = _month_bounds(now, 1)
    last_month_active = await _active_codes_between(db, last_month_start, last_month_end)
    this_month_active = await _active_codes_between(db, month_start, now + timedelta(seconds=1))
    retained = last_month_active & this_month_active
    retention_rate = round(100 * len(retained) / len(last_month_active), 1) if last_month_active else None

    # ── Revenue concentration: top 20% of affiliates by commission ─────
    revenue_by_affiliate = {
        row["_id"]: row["revenue"] or 0
        for row in await db.referrals.aggregate([
            {"$group": {"_id": "$affiliate_code", "revenue": {"$sum": "$commission_amount"}}}
        ]).to_list(5000)
    }
    revenue_concentration = None
    if revenue_by_affiliate:
        sorted_revenues = sorted(revenue_by_affiliate.values(), reverse=True)
        total_revenue = sum(sorted_revenues)
        top_n = max(1, round(len(sorted_revenues) * 0.2))
        top_revenue = sum(sorted_revenues[:top_n])
        revenue_concentration = round(100 * top_revenue / total_revenue, 1) if total_revenue else 0.0

    # ── Time-to-first-sale (avg, days) — only affiliates with a sale ───
    first_sale_by_code = {
        row["_id"]: row["first_sale_at"]
        for row in await db.referrals.aggregate([
            {"$sort": {"created_at": 1}},
            {"$group": {"_id": "$affiliate_code", "first_sale_at": {"$first": "$created_at"}}},
        ]).to_list(5000)
    }
    days_list = []
    for a in affiliates:
        first_sale = _ensure_utc(first_sale_by_code.get(a["code"]))
        created_at = _ensure_utc(a["created_at"])
        if first_sale and created_at:
            days_list.append(max((first_sale - created_at).days, 0))
    avg_time_to_first_sale = round(sum(days_list) / len(days_list), 1) if days_list else None

    # ── Never activated — the actionable nudge list ────────────────────
    never_activated = sorted(
        (
            {"id": str(a["_id"]), "code": a["code"], "name": a["name"], "email": a["email"], "created_at": a["created_at"]}
            for a in affiliates if a["code"] not in activated_codes
        ),
        key=lambda x: x["created_at"], reverse=True,
    )

    return {
        "total_registered": total_registered,
        "new_registrations_this_month": new_this_month,
        "activated_count": len(activated_codes),
        "activation_rate": activation_rate,
        "maa_current": maa_current,
        "maa_trend": trend,
        "retention_rate": retention_rate,
        "revenue_concentration_top20": revenue_concentration,
        "avg_time_to_first_sale_days": avg_time_to_first_sale,
        "never_activated": never_activated,
    }
