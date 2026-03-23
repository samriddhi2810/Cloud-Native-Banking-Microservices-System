from fastapi import APIRouter, HTTPException
from app.database import SessionLocal
from app.models import Transaction
import requests

router = APIRouter()

USER_SERVICE_URL = "http://localhost:8000"

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

        # 🔥 update balance in user-service
        update_response = requests.post(
            f"{USER_SERVICE_URL}/update-balance",
            params={"user_id": user_id, "amount": amount}
        )

        # 🔥 save transaction
        txn = Transaction(user_id=user_id, amount=amount, type="deposit")
        db.add(txn)
        db.commit()

        return {
            "message": f"Deposited {amount}",
            "transaction_id": txn.id,
            "balance": update_response.json()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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

        # 🔥 save transaction
        txn = Transaction(user_id=user_id, amount=-amount, type="withdrawal")
        db.add(txn)
        db.commit()

        # 🔥 update balance in user-service
        requests.post(
            f"{USER_SERVICE_URL}/update-balance",
            params={"user_id": user_id, "amount": -amount}
        )

        return {
            "message": f"Withdrawn {amount}",
            "transaction_id": txn.id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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

        # 🔥 deduct from sender
        requests.post(
            f"{USER_SERVICE_URL}/update-balance",
            params={"user_id": sender_id, "amount": -amount}
        )

        # 🔥 add to receiver
        requests.post(
            f"{USER_SERVICE_URL}/update-balance",
            params={"user_id": receiver_id, "amount": amount}
        )

        # 🔥 sender transaction (money going out)
        txn1 = Transaction(
            user_id=sender_id,
            amount=amount,
            type="transfer_sent"
        )

        # 🔥 receiver transaction (money coming in)
        txn2 = Transaction(
            user_id=receiver_id,
            amount=amount,
            type="transfer_received"
        )

        db.add(txn1)
        db.add(txn2)
        db.commit()

        return {
            "message": f"Transferred {amount} from {sender_id} to {receiver_id}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/transactions/{user_id}")
def get_transactions(user_id: int):
    db = SessionLocal()

    transactions = db.query(Transaction).filter(Transaction.user_id == user_id).all()

    return transactions