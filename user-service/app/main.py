from fastapi import FastAPI
from app.routes import router
from app.database import engine
from app.models import Base

app = FastAPI()

# 🔥 this creates tables automatically
Base.metadata.create_all(bind=engine)

app.include_router(router)

@app.get("/")
def home():
    return {"message": "User Service Running 🚀"}