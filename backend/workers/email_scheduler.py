"""
APScheduler-based email worker.
Runs inside FastAPI process — processes email queue every 5 minutes.
"""
import asyncio
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from .. import database
from ..services.email_service import send_sequence_email

scheduler = AsyncIOScheduler()

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


async def process_email_queue():
    """
    Process pending emails from the queue.
    Called every 5 minutes by the scheduler.
    """
    db = database.get_db()
    if db is None:
        return
    now = datetime.now(timezone.utc)
    pending = await db.email_queue.find({
        "status": {"$in": ["pending", "retry"]},
        "scheduled_at": {"$lte": now},
        "retry_count": {"$lt": 3},
    }).limit(50).to_list(50)

    for item in pending:
        try:
            subscriber = await db.subscribers.find_one({"_id": item["subscriber_id"]})
            if not subscriber or not subscriber.get("is_active"):
                await db.email_queue.update_one(
                    {"_id": item["_id"]},
                    {"$set": {"status": "skipped"}}
                )
                continue

            success = await send_sequence_email(
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
                # Advance subscriber position
                await db.subscribers.update_one(
                    {"_id": subscriber["_id"]},
                    {"$inc": {"sequence_position": 1}}
                )
            else:
                next_retry = item.get("retry_count", 0) + 1
                next_status = "failed" if next_retry >= 3 else "retry"
                await db.email_queue.update_one(
                    {"_id": item["_id"]},
                    {"$inc": {"retry_count": 1}, "$set": {"status": next_status}}
                )
        except Exception as e:
            print(f"Email worker error for {item.get('email')}: {e}")
            next_retry = item.get("retry_count", 0) + 1
            next_status = "failed" if next_retry >= 3 else "retry"
            await db.email_queue.update_one(
                {"_id": item["_id"]},
                {"$inc": {"retry_count": 1}, "$set": {"error": str(e), "status": next_status}}
            )


async def enqueue_sequence_for_subscriber(subscriber_id, subscribed_at: datetime):
    """
    Queue all 52 sequence emails for a new subscriber,
    spaced correctly from their subscription date.
    Every subscriber gets the exact same fixed order.
    """
    db = database.get_db()
    if db is None:
        return
    from bson import ObjectId
    sub = await db.subscribers.find_one({"_id": ObjectId(str(subscriber_id))})
    if not sub:
        return

    queue_items = []
    for position, (day_offset, subject, template) in enumerate(EMAIL_SEQUENCE, 1):
        from datetime import timedelta
        scheduled = subscribed_at + timedelta(days=day_offset)
        queue_items.append({
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
        # The first email (day_offset=0) is due immediately — send it now
        # instead of waiting for the next 5-minute scheduler tick. Fire and
        # forget: this scans/sends for ALL due subscribers, not just this
        # one, so awaiting it here would block the caller's HTTP response
        # (the customer's "payment confirmed" moment) on other people's
        # SMTP sends.
        asyncio.create_task(process_email_queue())


def start_scheduler():
    scheduler.add_job(
        process_email_queue,
        "interval",
        minutes=5,
        id="email_queue_processor",
        replace_existing=True,
    )
    scheduler.start()
    print("⏰ Email scheduler started")


def stop_scheduler():
    scheduler.shutdown()
