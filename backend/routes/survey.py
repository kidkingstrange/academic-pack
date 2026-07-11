"""
Post-purchase survey — optional, never blocks library access. Identifies
the customer via their library_access_token (the same durable token
already used for /api/library), not a separate auth mechanism.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from ..database import get_db
from ..schemas.schemas import SurveyResponseRequest

router = APIRouter(prefix="/api/survey", tags=["survey"])


@router.post("/respond")
async def submit_survey_response(body: SurveyResponseRequest, db=Depends(get_db)):
    user = await db.users.find_one({"library_access_token": body.token})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid access token")

    await db.survey_responses.insert_one({
        "user_id": user["_id"],
        "email": user["email"],
        "name": user.get("name"),
        "answers": body.answers or {},
        "submitted_at": datetime.now(timezone.utc),
    })
    return {"success": True}
