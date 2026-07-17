import html
import secrets
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .. import database
from ..config import get_settings
from ..services.email_service import send_email
from ..services.flutterwave import get_flw_token, charge_token

scheduler = AsyncIOScheduler()
settings = get_settings()

async def run_daily_subscription_billing():
    db = database.get_db()
    if db is None:
        print("❌ Subscription billing: Database connection unavailable")
        return

    now = datetime.now(timezone.utc)
    # Check all active subscriptions whose next charge date is due
    due_subs = await db.subscriptions.find({
        "status": "active",
        "next_charge_date": {"$lte": now}
    }).to_list(200)

    if not due_subs:
        print("⏰ Subscription billing: No subscriptions due today")
        return

    print(f"⏰ Subscription billing: Processing {len(due_subs)} due renewals...")
    flw_token = await get_flw_token()

    offer_ids = list({s["offer_id"] for s in due_subs if "offer_id" in s})
    offers = await db.offers.find({"_id": {"$in": offer_ids}}).to_list(len(offer_ids) or 1)
    offer_map = {o["_id"]: o for o in offers}

    for sub in due_subs:
        # Atomic claim of the current billing period before attempting payment
        claimed = await db.subscriptions.find_one_and_update(
            {
                "_id": sub["_id"],
                "status": "active",
                "next_charge_date": sub["next_charge_date"],
                "billing_in_progress": {"$ne": True}
            },
            {"$set": {"billing_in_progress": True}}
        )
        if not claimed:
            # Another worker claimed this subscription or period was already advanced
            continue

        offer = offer_map.get(sub.get("offer_id"))
        if not offer:
            print(f"❌ Offer not found for subscription {sub['_id']}, skipping")
            await db.subscriptions.update_one({"_id": sub["_id"]}, {"$unset": {"billing_in_progress": ""}})
            continue

        # Deterministic reference derived from sub ID + due charge date (e.g. SUB-REN-5f8a...-20260717)
        due_date_str = sub["next_charge_date"].strftime("%Y%m%d")
        reference = f"SUB-REN-{str(sub['_id'])}-{due_date_str}"
        print(f"🔄 Billing sub {sub['_id']} (amount: ₦{offer['price']}) - ref: {reference}")

        try:
            # Call Flutterwave tokenized charge
            # Handle mock tokens in sandbox/test environments only — never in production,
            # regardless of what card_token a subscription record happens to hold.
            if sub["card_token"] == "mock-card-token-12345" and settings.APP_ENV == "development":
                # Simulated successful sandbox tokenized charge
                chg_res = {
                    "status": "success",
                    "data": {
                        "status": "succeeded",
                        "amount": offer["price"]
                    }
                }
            else:
                chg_res = await charge_token(
                    token=flw_token,
                    card_token=sub["card_token"],
                    amount_naira=offer["price"],
                    email=sub["customer_email"],
                    reference=reference
                )

            flw_status = chg_res.get("status")
            charge_data = chg_res.get("data", {})
            charge_status = charge_data.get("status") if isinstance(charge_data, dict) else ""

            if flw_status == "success" and charge_status == "succeeded":
                # ── Renewal Success ──
                # 1. Update subscription status & next_charge_date (30 days from now) and release claim
                await db.subscriptions.update_one(
                    {"_id": sub["_id"]},
                    {
                        "$set": {
                            "next_charge_date": now + timedelta(days=30),
                            "status": "active",
                            "updated_at": now
                        },
                        "$unset": {"billing_in_progress": ""}
                    }
                )

                # 2. Log billing success
                await db.subscription_billing_logs.insert_one({
                    "subscription_id": sub["_id"],
                    "reference": reference,
                    "amount": offer["price"],
                    "status": "success",
                    "gateway_response": chg_res,
                    "created_at": now
                })

                # 3. Send Success Email
                email_html = f"""
                <h2>Renewal Payment Successful!</h2>
                <p>Hello {html.escape(sub['customer_name'])},</p>
                <p>Your monthly subscription renewal for <strong>{html.escape(offer['name'])}</strong> has been processed successfully.</p>
                <p><strong>Amount:</strong> ₦{offer['price']:,.2f}</p>
                <p><strong>Next Renewal Date:</strong> {(now + timedelta(days=30)).strftime('%B %d, %Y')}</p>
                <p>Thank you for choosing us!</p>
                """
                await send_email(sub["customer_email"], f"Subscription Renewed: {offer['name']}", email_html)
                print(f"✅ Renewal succeeded for sub {sub['_id']}")

            else:
                # Charge declined or authentication/OTP required (NOAUTH fallback)
                await db.subscriptions.update_one({"_id": sub["_id"]}, {"$unset": {"billing_in_progress": ""}})
                await handle_billing_failure(db, sub, offer, reference, chg_res, now)

        except Exception as e:
            print(f"❌ Exception renewing sub {sub['_id']}: {e}")
            await db.subscriptions.update_one({"_id": sub["_id"]}, {"$unset": {"billing_in_progress": ""}})
            await handle_billing_failure(db, sub, offer, reference, {"error": str(e)}, now)

async def handle_billing_failure(db, sub, offer, reference, response, now):
    # ── Renewal Failure Fallback (NOAUTH / OTP manual checkout trigger) ──
    fallback_token = secrets.token_urlsafe(24)
    
    # 1. Create a new lead in sales_leads for the prospect to manually checkout
    await db.sales_leads.insert_one({
        "sales_rep_id": sub["sales_rep_id"],
        "offer_id": sub["offer_id"],
        "prospect_name": sub["customer_name"],
        "prospect_email": sub["customer_email"].lower(),
        "prospect_phone": sub["customer_phone"],
        "generated_link_token": fallback_token,
        "status": "link_generated",
        "created_at": now
    })

    checkout_url = f"{settings.APP_URL}/sales/checkout?token={fallback_token}"

    # 2. Update subscription status to past_due
    await db.subscriptions.update_one(
        {"_id": sub["_id"]},
        {"$set": {
            "status": "past_due",
            "updated_at": now
        }}
    )

    # 3. Log billing failure
    await db.subscription_billing_logs.insert_one({
        "subscription_id": sub["_id"],
        "reference": reference,
        "amount": offer["price"],
        "status": "failed",
        "gateway_response": response,
        "created_at": now
    })

    # 4. Send Fallback Email Alert with Manual Checkout URL
    email_html = f"""
    <h2 style="color:#dc2626">Action Required: Renewal Payment Declined</h2>
    <p>Hello {html.escape(sub['customer_name'])},</p>
    <p>Your automatic subscription renewal payment for <strong>{html.escape(offer['name'])}</strong> of ₦{offer['price']:,.2f} failed or requires manual authorization.</p>
    <p>To prevent disruption of your subscription access, please manually complete your payment using the link below:</p>
    <p><a href="{checkout_url}" style="display:inline-block;background-color:#d4a63a;color:#0d0f14;padding:12px 24px;border-radius:30px;text-decoration:none;font-weight:bold">Complete Renewal Payment &rarr;</a></p>
    <br>
    <p><em>If you have any questions, please contact support.</em></p>
    """
    await send_email(sub["customer_email"], f"Action Required: Subscription Renewal Failed", email_html)
    print(f"⚠️ Renewal failed for sub {sub['_id']} - sent manual checkout url: {checkout_url}")

def start_subscription_scheduler():
    # Runs daily at 1:00 AM
    scheduler.add_job(
        run_daily_subscription_billing,
        CronTrigger(hour=1, minute=0),
        id="subscription_billing_job",
        replace_existing=True
    )
    scheduler.start()
    print("⏰ Subscription billing scheduler started")

def stop_subscription_scheduler():
    scheduler.shutdown()
