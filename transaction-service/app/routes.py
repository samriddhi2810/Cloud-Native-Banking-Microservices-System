import os
from fastapi import APIRouter, HTTPException
from app.database import SessionLocal
from app.models import Transaction
import requests

router = APIRouter()

# Docker-compose service names resolve inside the Docker network; env vars
# let this still work for local (non-docker) runs.
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user-service:8000")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8000")


def notify(user_id: int, message: str):
    """Best-effort notification call — a failed notification should never
    break the underlying transaction, so this swallows its own errors."""
    try:
        requests.post(
            f"{NOTIFICATION_SERVICE_URL}/notify",
            json={"user_id": user_id, "message": message},
            timeout=3,
        )
    except requests.RequestException:
        pass

@router.post("/deposit")
def deposit(user_id: int, amount: float):
    db = SessionLocal()

    try:
        # check user exists
        response = requests.get(f"{USER_SERVICE_URL}/users")
        users = response.json()

        user_exists = any(user["id"] == user_id for user in users)

        if not user_exists:
            raise HTTPException(status_code=404, detail="User not found")

        # update balance in user-service
        update_response = requests.post(
            f"{USER_SERVICE_URL}/update-balance",
            json={"user_id": user_id, "amount": amount}
        )
        update_response.raise_for_status()

        # save transaction
        txn = Transaction(user_id=user_id, amount=amount, type="deposit")
        db.add(txn)
        db.commit()

        notify(user_id, f"Deposit of {amount} successful.")

        return {
            "message": f"Deposited {amount}",
            "transaction_id": txn.id,
            "balance": update_response.json()
        }

    except HTTPException:
        raise
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"user-service unavailable: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.post("/withdrawal")
def withdrawal(user_id: int, amount: float):
    db = SessionLocal()

    try:
        # check user exists
        response = requests.get(f"{USER_SERVICE_URL}/users")
        users = response.json()

        user = next((u for u in users if u["id"] == user_id), None)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # 🔥 check balance
        if user["balance"] < amount:
            raise HTTPException(status_code=400, detail="Insufficient balance")

        # save transaction
        txn = Transaction(user_id=user_id, amount=-amount, type="withdrawal")
        db.add(txn)
        db.commit()

        # update balance in user-service
        update_response = requests.post(
            f"{USER_SERVICE_URL}/update-balance",
            json={"user_id": user_id, "amount": -amount}
        )
        update_response.raise_for_status()

        notify(user_id, f"Withdrawal of {amount} successful.")

        return {
            "message": f"Withdrawn {amount}",
            "transaction_id": txn.id
        }

    except HTTPException:
        raise
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"user-service unavailable: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.post("/transfer")
def transfer(sender_id: int, receiver_id: int, amount: float):
    db = SessionLocal()

    try:
        # 🔥 get all users
        response = requests.get(f"{USER_SERVICE_URL}/users")
        users = response.json()

        sender = next((u for u in users if u["id"] == sender_id), None)
        receiver = next((u for u in users if u["id"] == receiver_id), None)

        # ❌ validation
        if not sender:
            raise HTTPException(status_code=404, detail="Sender not found")

        if not receiver:
            raise HTTPException(status_code=404, detail="Receiver not found")

        if sender["balance"] < amount:
            raise HTTPException(status_code=400, detail="Insufficient balance")

        # deduct from sender
        deduct_response = requests.post(
            f"{USER_SERVICE_URL}/update-balance",
            json={"user_id": sender_id, "amount": -amount}
        )
        deduct_response.raise_for_status()

        # add to receiver
        # NOTE: if this call fails after the deduction above already
        # succeeded, the sender's money is gone with nothing credited to the
        # receiver and no automatic rollback. A production version of this
        # needs a saga/compensating-transaction pattern; flagging this here
        # rather than silently pretending it's handled.
        add_response = requests.post(
            f"{USER_SERVICE_URL}/update-balance",
            json={"user_id": receiver_id, "amount": amount}
        )
        add_response.raise_for_status()

        # sender transaction (money going out)
        txn1 = Transaction(
            user_id=sender_id,
            amount=amount,
            type="transfer_sent"
        )

        # receiver transaction (money coming in)
        txn2 = Transaction(
            user_id=receiver_id,
            amount=amount,
            type="transfer_received"
        )

        db.add(txn1)
        db.add(txn2)
        db.commit()

        notify(sender_id, f"You sent {amount} to user {receiver_id}.")
        notify(receiver_id, f"You received {amount} from user {sender_id}.")

        return {
            "message": f"Transferred {amount} from {sender_id} to {receiver_id}"
        }

    except HTTPException:
        raise
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"user-service unavailable: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.get("/transactions/{user_id}")
def get_transactions(user_id: int):
    db = SessionLocal()
    try:
        return db.query(Transaction).filter(Transaction.user_id == user_id).all()
    finally:
        db.close()