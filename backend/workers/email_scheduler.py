"""
APScheduler-based email worker.
Runs inside FastAPI process — processes email queue every 5 minutes.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from .. import database
from ..services.email_service import (
    send_sequence_email, send_welcome_email, send_affiliate_welcome_email, send_affiliate_nudge_email,
)

scheduler = AsyncIOScheduler()


async def rescue_stuck_sending_items():
    """
    Reset any items left in 'sending' status back to 'pending'.

    'sending' is a transient, in-flight status set atomically as the scheduler
    claims an item. If the server process is killed or restarted mid-send (Render
    deploy, crash, OOM kill), those items are stranded in 'sending' forever —
    the next scheduler run only queries for 'pending'/'retry', so they become
    permanently invisible without this rescue. This function MUST run before the
    scheduler starts processing, and is safe to re-run at any time (if an item
    was genuinely mid-send, the actual send likely failed anyway and the retry
    system will handle it normally from 'pending').
    """
    db = database.get_db()
    if db is None:
        return
    from datetime import datetime, timezone
    result = await db.email_queue.update_many(
        {"status": "sending"},
        {"$set": {
            "status": "pending",
            "error": "rescued_from_sending_on_server_restart",
            "last_attempt_at": datetime.now(timezone.utc)
        }}
    )
    if result.modified_count:
        print(f"⚠️ Email scheduler: rescued {result.modified_count} items stuck in 'sending' state — server was restarted mid-send")
    else:
        print("✅ Email scheduler: no stuck 'sending' items found on startup")


async def check_email_health():
    """
    Periodic health check: logs a warning if no emails have been sent in the
    last 2 hours. Runs every hour via the scheduler. This is a lightweight
    early-warning system — if the scheduler silently stops, you'll see this
    alert in your server logs within 1 hour rather than days later.
    """
    db = database.get_db()
    if db is None:
        return
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    two_hours_ago = now - timedelta(hours=2)

    # Count pending items that are due but haven't been processed
    overdue_count = await db.email_queue.count_documents({
        "status": {"$in": ["pending", "retry"]},
        "scheduled_at": {"$lte": now}
    })

    # Count recently sent items
    recent_sent = await db.email_queue.count_documents({
        "status": "sent",
        "sent_at": {"$gte": two_hours_ago}
    })

    # Count items stuck in sending (another server-restart symptom)
    stuck_sending = await db.email_queue.count_documents({"status": "sending"})

    if stuck_sending > 0:
        print(f"🚨 EMAIL HEALTH: {stuck_sending} items STUCK IN SENDING — possible server restart mid-send. Run rescue_stuck_sending_items().")
    elif overdue_count > 0 and recent_sent == 0:
        print(f"🚨 EMAIL HEALTH WARNING: {overdue_count} emails are due but NONE sent in last 2 hours. Scheduler may be dead or SMTP is down.")
    elif overdue_count > 10:
        print(f"⚠️ EMAIL HEALTH: {overdue_count} overdue emails in queue. Recent sent: {recent_sent} in last 2h.")
    else:
        print(f"✅ EMAIL HEALTH OK: {recent_sent} sent in last 2h, {overdue_count} overdue")


def _backoff_minutes(retry_count: int) -> int:
    """
    Exponential backoff between retry attempts, capped at 24h. Before
    this, a failed item just got re-tried on the very next 5-minute
    scheduler tick regardless of how many times it had already failed —
    fine for a one-off blip, but it means all 10 retries burn through in
    under an hour. On 2026-07-13/15, delivery broke for ~40 hours
    straight and every email caught in that window permanently failed
    within its first ~50 minutes, long before the underlying problem
    had any real chance to clear. Formula: 10, 20, 40, 80, 160, 320,
    640, 1280, 1440(capped), 1440(capped) minutes across 10 retries —
    spreads them across roughly 3.75 days instead of ~50 minutes.
    """
    return min(5 * (2 ** retry_count), 24 * 60)

# Serializes process_email_queue() across overlapping trigger sources — the
# 5-minute scheduler tick and the immediate asyncio.create_task() fired on
# every payment/affiliate-registration completion. Without this, two
# invocations can each open their own SMTP connection at the same instant;
# confirmed in production via pairs of "sequence"/"welcome" failures sharing
# the exact same last_attempt_at millisecond (PrivateEmail rejecting/stalling
# concurrent connections from the same account). This lock makes an
# overlapping call wait for the current run to finish rather than racing it.
#
# Built lazily (not as a bare module-level asyncio.Lock()) because a Lock
# binds permanently to whichever event loop first acquires it. That's a
# no-op in production (one event loop for the app's entire lifetime), but
# pytest-asyncio gives each test its own event loop, so a second test
# reusing the same Lock object raises "bound to a different event loop".
_email_queue_lock = None
_email_queue_lock_loop = None


def _get_email_queue_lock() -> asyncio.Lock:
    global _email_queue_lock, _email_queue_lock_loop
    loop = asyncio.get_running_loop()
    if _email_queue_lock is None or _email_queue_lock_loop is not loop:
        _email_queue_lock = asyncio.Lock()
        _email_queue_lock_loop = loop
    return _email_queue_lock

# ─── 52-Email Curriculum Sequence ─────────────────────────────────────────────
# Organised as a structured transformation journey across 9 phases.
# Schedule: 2 emails/week — Monday (offset +0) and Thursday (offset +3)
# Total: 26 weeks × 2 = 52 emails
# Format: (days_offset, subject, template_file)
#
# Every subscriber receives these in the EXACT same fixed order,
# starting from their subscription date.
#
# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1 — MINDSET RESET (Weeks 1–3)
#   "Before we change how you study, we change how you think."
# PHASE 2 — HOW YOUR BRAIN LEARNS (Weeks 4–6)
#   "The science behind why you forget, struggle, and plateau."
# PHASE 3 — STUDY TECHNIQUES THAT WORK (Weeks 7–9)
#   "Replace broken habits with proven methods."
# PHASE 4 — MASTERING FOCUS & ATTENTION (Weeks 10–12)
#   "Your attention is your most valuable academic asset."
# PHASE 5 — DISCIPLINE & CONSISTENCY (Weeks 13–16)
#   "Motivation fades. Systems endure."
# PHASE 6 — STRATEGY & SYSTEMS THINKING (Weeks 17–19)
#   "Work smarter. Think like a top performer."
# PHASE 7 — EXAM PREPARATION & PRESSURE (Weeks 20–21)
#   "When stakes are highest, preparation beats panic."
# PHASE 8 — GROWTH, VISION & IDENTITY (Weeks 22–23)
#   "The deeper transformation beyond grades."
# PHASE 9 — MENTORSHIP, TRUST & DECISION (Weeks 24–26)
#   "The invitation. Social proof. Final call."
# ═══════════════════════════════════════════════════════════════════════════════

EMAIL_SEQUENCE = [
    # ── PHASE 1: MINDSET RESET ────────────────────────────────────────────────
    (0,   "You're not lazy — you just don't have the right system yet",                        "email_01.html"),
    (3,   "The top student in your class isn't smarter than you",                               "email_03.html"),
    (7,   "Your grades reflect your habits — not your potential",                               "email_07.html"),
    (10,  "Two students. Same exam. The only difference is what they believe about it.",         "email_38.html"),
    (14,  "Every great performer you admire was once a beginner who found the right method",    "email_31.html"),
    (17,  "The curiosity you had as a child didn't disappear — it was buried",                  "email_29.html"),

    # ── PHASE 2: HOW YOUR BRAIN ACTUALLY LEARNS ──────────────────────────────
    (21,  "Your brain doesn't record like a camera — it builds like a scaffold",                "email_10.html"),
    (24,  "Barbara Oakley couldn't do maths. Then she learned how the brain actually changes.",  "email_36.html"),
    (28,  "You've been studying the wrong way (and it feels productive)",                       "email_04.html"),
    (31,  "If studying feels comfortable, something is probably wrong.",                         "email_37.html"),
    (35,  "Your brain processes visuals 60,000x faster than text. You're studying the slow way.","email_25.html"),
    (38,  "You're not bad at remembering. You're bad at reviewing. Different problem.",          "email_30.html"),

    # ── PHASE 3: STUDY TECHNIQUES THAT ACTUALLY WORK ─────────────────────────
    (42,  "The most powerful study technique has been proven for 100+ years. You're not using it.", "email_14.html"),
    (45,  "One technique mastered beats ten techniques practised",                               "email_16.html"),
    (49,  "Your notes aren't the problem — what you do after is",                                "email_17.html"),
    (52,  "The real reason you can't focus when you study",                                      "email_02.html"),
    (56,  "This student studied 4 hours a day and outscored the 12-hour grinders",               "email_09.html"),
    (59,  "There's a point where more studying actively destroys your performance.",              "email_43.html"),

    # ── PHASE 4: MASTERING FOCUS & ATTENTION ──────────────────────────────────
    (63,  "You're not multitasking — you're just switching fast and paying the cost",            "email_19.html"),
    (66,  "Your mind wanders 47% of the time. Here's what to do about it.",                     "email_32.html"),
    (70,  "Every unfinished task in your head is quietly draining your focus",                   "email_33.html"),
    (73,  "Flow is not luck. It has trigger conditions — and you can set them.",                 "email_28.html"),
    (77,  "You have the same 24 hours as every top student. Here's what they do differently.",   "email_21.html"),
    (80,  "The world's smartest people use checklists. Here's why you should too.",              "email_22.html"),

    # ── PHASE 5: BUILDING DISCIPLINE & CONSISTENCY ────────────────────────────
    (84,  "Motivation is the spark. You can't run an engine on sparks.",                         "email_11.html"),
    (87,  "You don't need more discipline — you need a smaller starting point",                  "email_05.html"),
    (91,  "It's not a discipline problem. It's a design problem.",                               "email_15.html"),
    (94,  "The gap between average and excellent isn't talent — it's one habit",                  "email_13.html"),
    (98,  "One habit. Twenty minutes. Every week. The results are remarkable.",                   "email_42.html"),
    (101, 'Every Monday is "the new start." At what point does the pattern become the problem?',  "email_40.html"),
    (105, "You already know what you should be doing. That's not the problem.",                   "email_23.html"),
    (108, "Your grades are built in the moments nobody sees",                                    "email_24.html"),

    # ── PHASE 6: STRATEGY & SYSTEMS THINKING ─────────────────────────────────
    (112, "Working hard on the wrong things is worse than not working at all",                   "email_06.html"),
    (115, "Stop blaming yourself for your grades. Fix the system upstream.",                     "email_35.html"),
    (119, "The best student in the room isn't the hardest worker — they're the most strategic",  "email_39.html"),
    (122, "MIT in 12 months — and what it reveals about how you're wasting yours",               "email_34.html"),
    (126, "The most powerful career question applies to your academic life right now",            "email_26.html"),
    (129, '"Balance" is not about doing everything equally. Here\'s what it actually means.',     "email_46.html"),

    # ── PHASE 7: EXAM PREPARATION & PERFORMING UNDER PRESSURE ────────────────
    (133, "Exam anxiety has nothing to do with the exam",                                        "email_08.html"),
    (136, "The most pressure-proof students aren't fearless — they're prepared differently",      "email_27.html"),

    # ── PHASE 8: GROWTH, VISION & IDENTITY ───────────────────────────────────
    (140, "There's a kind of suffering nobody talks about — slow, invisible progress",           "email_18.html"),
    (143, "You won't notice it happening. Then one day you'll be unrecognisable.",               "email_20.html"),
    (147, "The most powerful motivation isn't external. It's a clear picture of who you're becoming.", "email_44.html"),
    (150, "What you do in the next 90 days will still matter in 2031.",                          "email_49.html"),

    # ── PHASE 9: MENTORSHIP, TRUST & DECISION ────────────────────────────────
    (154, "A mentor doesn't do the work for you — they show you which work matters",             "email_12.html"),
    (157, "Michael Jordan had a coach. What makes you think you should do this alone?",          "email_41.html"),
    (161, "He was three failed courses in and considering dropping out. Six months later:",       "email_45.html"),
    (164, "The decision to not decide is itself a decision. And it has a price.",                 "email_47.html"),
    (168, "I'm not going to sell you. I'm going to tell you the truth about why this exists.",    "email_48.html"),
    (171, "Let me show you what the before and after actually looks like.",                       "email_50.html"),
    (175, "The argument against investing in yourself is made by the version of you that benefits least.", "email_51.html"),
    (178, "One question left.",                                                                  "email_52.html"),
]


# ── Free community nurture sequence ──────────────────────────────────────────
# Free WhatsApp community joiners are not paying customers and must not get
# the full 52-email paid curriculum above (which builds toward a sales pitch
# for the product itself, e.g. email_48/email_52). This is a short,
# standalone welcome/value sequence instead, reusing a handful of the
# general-audience "mindset reset" emails from PHASE 1.
COMMUNITY_EMAIL_SEQUENCE = [
    (0,  "You're not lazy — you just don't have the right system yet",              "email_01.html"),
    (3,  "The top student in your class isn't smarter than you",                    "email_03.html"),
    (7,  "Your grades reflect your habits — not your potential",                    "email_07.html"),
    (14, "Your brain doesn't record like a camera — it builds like a scaffold",     "email_10.html"),
    (21, "You've been studying the wrong way (and it feels productive)",            "email_04.html"),
]


async def process_email_queue():
    """
    Process pending emails from the queue.
    Called every 5 minutes by the scheduler.

    Serialized by _email_queue_lock (see module docstring above it) — an
    overlapping call blocks here until the current run finishes, instead of
    opening a second concurrent batch of SMTP connections.
    """
    async with _get_email_queue_lock():
        db = database.get_db()
        if db is None:
            return
        now = datetime.now(timezone.utc)

        # Atomically claim each item before processing (status -> "sending").
        # A plain find() here would let two overlapping calls to this function
        # (the immediate on-signup trigger racing the 5-minute scheduler tick,
        # or two manual invocations) both read the same "pending"/"retry" item
        # before either finishes its await on the SMTP send, double-processing
        # it — real, observed symptom: sequence_position incremented twice for
        # one actually-sent email. find_one_and_update is atomic at the DB
        # level, so only one caller can ever claim a given item. The lock
        # above now also prevents two runs' items from being sent concurrently
        # in the first place.
        pending = []
        TRANSACTIONAL_KINDS = ("welcome", "affiliate_welcome", "affiliate_nudge")

        # Step 1: Claim high-priority transactional emails first
        while len(pending) < 50:
            item = await db.email_queue.find_one_and_update(
                {
                    "status": {"$in": ["pending", "retry"]},
                    "scheduled_at": {"$lte": now},
                    "retry_count": {"$lt": 10},
                    "kind": {"$in": TRANSACTIONAL_KINDS}
                },
                {"$set": {"status": "sending"}},
                sort=[("scheduled_at", 1)],
            )
            if not item:
                break
            pending.append(item)

        # Step 2: Fill remaining batch budget with bulk sequence emails
        while len(pending) < 50:
            item = await db.email_queue.find_one_and_update(
                {
                    "status": {"$in": ["pending", "retry"]},
                    "scheduled_at": {"$lte": now},
                    "retry_count": {"$lt": 10},
                    "kind": {"$nin": TRANSACTIONAL_KINDS}
                },
                {"$set": {"status": "sending"}},
                sort=[("scheduled_at", 1)],
            )
            if not item:
                break
            pending.append(item)

        for idx, item in enumerate(pending):
            if idx > 0:
                # Pace sends to prevent PrivateEmail connection bursts
                await asyncio.sleep(0.2)
            try:
                kind = item.get("kind", "sequence")
                error_msg = None

                if kind == "welcome":
                    success, error_msg = await send_welcome_email(
                        name=item["name"],
                        email=item["email"],
                        token=item.get("access_token") or item.get("magic_token"),
                        unsubscribe_token=item.get("unsubscribe_token", ""),
                        delayed=item.get("delayed_resend", False),
                    )
                elif kind == "affiliate_welcome":
                    success, error_msg = await send_affiliate_welcome_email(
                        name=item["name"],
                        email=item["email"],
                        code=item["code"],
                        referral_link=item["referral_link"],
                        dashboard_link=item.get("dashboard_link", ""),
                    )
                elif kind == "affiliate_nudge":
                    success, error_msg = await send_affiliate_nudge_email(
                        name=item["name"],
                        email=item["email"],
                        referral_link=item["referral_link"],
                    )
                else:
                    subscriber = await db.subscribers.find_one({"_id": item["subscriber_id"]})
                    if not subscriber or not subscriber.get("is_active"):
                        await db.email_queue.update_one(
                            {"_id": item["_id"]},
                            {"$set": {"status": "skipped"}}
                        )
                        continue

                    success, error_msg = await send_sequence_email(
                        name=subscriber["name"],
                        email=subscriber["email"],
                        template_name=item["template"],
                        subject=item["subject"],
                        unsubscribe_token=subscriber.get("unsubscribe_token", ""),
                    )

                if success:
                    await db.email_queue.update_one(
                        {"_id": item["_id"]},
                        {"$set": {"status": "sent", "sent_at": now}}
                    )
                    if kind not in ("welcome", "affiliate_welcome", "affiliate_nudge"):
                        # Advance subscriber position
                        await db.subscribers.update_one(
                            {"_id": item["subscriber_id"]},
                            {"$inc": {"sequence_position": 1}}
                        )
                else:
                    next_retry = item.get("retry_count", 0) + 1
                    max_retries = 10
                    next_status = "failed" if next_retry >= max_retries else "retry"
                    update_fields = {"status": next_status, "error": error_msg, "last_attempt_at": now}
                    if next_status == "retry":
                        update_fields["scheduled_at"] = now + timedelta(minutes=_backoff_minutes(next_retry))
                    await db.email_queue.update_one(
                        {"_id": item["_id"]},
                        {"$inc": {"retry_count": 1}, "$set": update_fields}
                    )
                    if next_status == "failed" and kind in ("welcome", "affiliate_welcome"):
                        try:
                            st = get_settings()
                            target_email = item.get("email") or "customer"
                            alert_subject = f"⚠️ [DEAD LETTER] Access email failed for {target_email}"
                            alert_body = (
                                f"Transactional access email ({kind}) for {target_email} has reached max retries and failed.\n\n"
                                f"Error: {error_msg}\n"
                                f"Please use the admin dashboard to resend access."
                            )
                            await send_email(st.ADMIN_EMAIL, alert_subject, alert_body)
                        except Exception as alert_err:
                            print(f"❌ Failed to send dead-letter alert to admin: {alert_err}")
            except Exception as e:
                print(f"Email worker error for {item.get('email')}: {e}")
                next_retry = item.get("retry_count", 0) + 1
                max_retries = 10
                next_status = "failed" if next_retry >= max_retries else "retry"
                update_fields = {"error": str(e), "status": next_status, "last_attempt_at": now}
                if next_status == "retry":
                    update_fields["scheduled_at"] = now + timedelta(minutes=_backoff_minutes(next_retry))
                await db.email_queue.update_one(
                    {"_id": item["_id"]},
                    {"$inc": {"retry_count": 1}, "$set": update_fields}
                )
                if next_status == "failed" and item.get("kind") in ("welcome", "affiliate_welcome"):
                    try:
                        st = get_settings()
                        target_email = item.get("email") or "customer"
                        alert_subject = f"⚠️ [DEAD LETTER] Access email failed for {target_email}"
                        alert_body = (
                            f"Transactional access email ({item.get('kind')}) for {target_email} has reached max retries and failed.\n\n"
                            f"Error: {e}\n"
                            f"Please use the admin dashboard to resend access."
                        )
                        await send_email(st.ADMIN_EMAIL, alert_subject, alert_body)
                    except Exception as alert_err:
                        print(f"❌ Failed to send dead-letter alert to admin: {alert_err}")


async def enqueue_sequence_for_subscriber(subscriber_id, subscribed_at: datetime, sequence=None):
    """
    Queue sequence emails for a new subscriber, spaced correctly from their
    subscription date. Defaults to the full 52-email paid curriculum — pass
    sequence=COMMUNITY_EMAIL_SEQUENCE for free (non-purchasing) subscribers
    so they get the short welcome/value sequence instead.
    """
    db = database.get_db()
    if db is None:
        return
    from bson import ObjectId
    sub = await db.subscribers.find_one({"_id": ObjectId(str(subscriber_id))})
    if not sub:
        return

    queue_items = []
    for position, (day_offset, subject, template) in enumerate(sequence or EMAIL_SEQUENCE, 1):
        scheduled = subscribed_at + timedelta(days=day_offset)
        queue_items.append({
            "kind": "sequence",
            "subscriber_id": sub["_id"],
            "email": sub["email"],
            "subject": subject,
            "template": template,
            "sequence_number": position,
            "scheduled_at": scheduled,
            "status": "pending",
            "retry_count": 0,
            "sent_at": None,
            "error": None,
        })

    if queue_items:
        await db.email_queue.insert_many(queue_items)
        print(f"📧 Queued {len(queue_items)} emails for {sub['email']}")
        # The first email (day_offset=0) is due immediately. The caller
        # (complete_payment) triggers one process_email_queue() pass after
        # this AND the welcome email are both queued, so it isn't done here.


def start_scheduler():
    # Process email queue every 5 minutes
    scheduler.add_job(
        process_email_queue,
        "interval",
        minutes=5,
        id="email_queue_processor",
        replace_existing=True,
    )
    # Hourly health check: logs warning if emails are overdue or stuck
    scheduler.add_job(
        check_email_health,
        "interval",
        hours=1,
        id="email_health_check",
        replace_existing=True,
    )
    # Startup dead-letter rescue: reset any 'sending' items orphaned by server restart
    scheduler.add_job(
        rescue_stuck_sending_items,
        "date",  # run once, immediately on startup
        id="startup_rescue",
        replace_existing=True,
    )
    scheduler.start()
    print("⏰ Email scheduler started (with startup rescue + hourly health check)")


def stop_scheduler():
    scheduler.shutdown()
