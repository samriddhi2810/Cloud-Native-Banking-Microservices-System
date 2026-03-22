from fastapi import APIRouter
from app.database import SessionLocal
from app.models import User
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        return user_id
    except jwt.JWTError:
        return None

@router.post("/register")
def register(username: str, password: str):
    db = SessionLocal()

    user = User(username=username, password=pwd_context.hash(password))
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"message": "User registered", "user_id": user.id}

@router.get("/users")
def get_users():
    db = SessionLocal()
    users = db.query(User).all()

    return users

@router.post("/update-balance")
def update_balance(user_id: int, amount: int):
    db = SessionLocal()

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        return {"error": "User not found"}

    user.balance += amount
    db.commit()

    return {"message": "Balance updated", "new_balance": user.balance}

@router.post("/login")
def login(username: str, password: str):
    db = SessionLocal()

    user = db.query(User).filter(User.username == username).first()

    if not user:
        return {"error": "User not found"}

    if not pwd_context.verify(password, user.password):
        return {"error": "Invalid password"}

    token = create_access_token({"sub": str(user.id)})

    return {
        "message": "Login successful",
        "access_token": token,
        "token_type": "bearer"
    }

@router.post("/reset-password")
def reset_password(username: str, new_password: str):
    db = SessionLocal()

    user = db.query(User).filter(User.username == username).first()

    if not user:
        return {"error": "User not found"}

    hashed_password = pwd_context.hash(new_password)
    user.password = hashed_password
    db.commit()

    return {"message": "Password updated successfully"}

@router.get("/me")
def get_current_user(token: str):
    user_id = verify_token(token)
    if not user_id:
        return {"error": "Invalid token"}

    db = SessionLocal()
    user = db.query(User).filter(User.id == int(user_id)).first()

    if not user:
        return {"error": "User not found"}

    return {
        "user_id": user.id,
        "username": user.username,
        "balance": user.balance
    }