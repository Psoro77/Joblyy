from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import chat, jobs, profile
from app.services.database import init_db
from app.services.memory import init_user_memory


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    init_user_memory(1)
    yield


app = FastAPI(title="Joblyy", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5500", "http://127.0.0.1:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(jobs.router)
app.include_router(profile.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
