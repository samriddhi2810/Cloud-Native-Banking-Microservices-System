import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.database import SessionLocal
from app.models import User
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Secret is read from an env var (set in docker-compose); only this service
# holds it, so tokens can only be issued/verified here.
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your_secret_key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class ResetPasswordRequest(BaseModel):
    username: str
    old_password: str
    new_password: str


class UpdateBalanceRequest(BaseModel):
    user_id: int
    amount: float


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except jwt.JWTError:
        return None


def user_public(user: User) -> dict:
    """Serialize a user WITHOUT the password hash — used everywhere a user
    is returned so credential material never leaves this service."""
    return {"id": user.id, "username": user.username, "balance": user.balance}


@router.post("/register")
def register(payload: RegisterRequest):
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == payload.username).first()
        if existing:
            raise HTTPException(status_code=409, detail="Username already taken")

        user = User(username=payload.username, password=pwd_context.hash(payload.password))
        db.add(user)
        db.commit()
        db.refresh(user)

        return {"message": "User registered", "user_id": user.id}
    finally:
        db.close()


@router.get("/users")
def get_users():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        # Password hashes are stripped before this ever leaves the service.
        return [user_public(u) for u in users]
    finally:
        db.close()


@router.post("/update-balance")
def update_balance(payload: UpdateBalanceRequest):
    db = SessionLocal()
    try:
        # with_for_update() takes a row-level lock in MySQL (SELECT ... FOR
        # UPDATE), so if two requests hit this endpoint for the same user at
        # the same time, the second one blocks until the first commits
        # instead of both reading the same balance concurrently.
        user = (
            db.query(User)
            .filter(User.id == payload.user_id)
            .with_for_update()
            .first()
        )

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        new_balance = user.balance + payload.amount
        if new_balance < 0:
            raise HTTPException(status_code=400, detail="Insufficient balance")

        user.balance = new_balance
        db.commit()

        return {"message": "Balance updated", "new_balance": user.balance}
    except HTTPException:
        db.rollback()
        raise
    finally:
        db.close()


@router.post("/login")
def login(payload: LoginRequest):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == payload.username).first()

        if not user or not pwd_context.verify(payload.password, user.password):
            # Same error for "no such user" and "wrong password" so the
            # response doesn't leak which usernames exist.
            raise HTTPException(status_code=401, detail="Invalid username or password")

        token = create_access_token({"sub": str(user.id)})

        return {
            "message": "Login successful",
            "access_token": token,
            "token_type": "bearer",
        }
    finally:
        db.close()


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest):
    """Requires the account's current password to change it, keeping the flow
    usable pre-login (no JWT needed) while still proving the caller owns the
    account."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == payload.username).first()
        if not user or not pwd_context.verify(payload.old_password, user.password):
            raise HTTPException(status_code=401, detail="Invalid username or password")

        user.password = pwd_context.hash(payload.new_password)
        db.commit()

        return {"message": "Password updated successfully"}
    finally:
        db.close()


@router.get("/me")
def get_current_user(token: str):
    user_id = verify_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return user_public(user)
    finally:
        db.close()
