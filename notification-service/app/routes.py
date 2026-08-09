from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

# In-memory store is fine for a portfolio project — a real system would
# persist these (e.g. its own MySQL table) and likely push over
# WebSockets/email/SMS instead of just storing them.
_notifications: dict[int, list[dict]] = {}


class NotificationRequest(BaseModel):
    user_id: int
    message: str


@router.post("/notify")
def notify(payload: NotificationRequest):
    entry = {"message": payload.message, "timestamp": datetime.utcnow().isoformat()}
    _notifications.setdefault(payload.user_id, []).append(entry)
    return {"status": "queued", "user_id": payload.user_id}


@router.get("/notifications/{user_id}")
def get_notifications(user_id: int):
    return _notifications.get(user_id, [])
