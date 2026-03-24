"""
main.py - FastAPI application entry point.
All routes, CORS configuration, and startup logic.
"""
import os
import re
import shutil
import tempfile
from collections import Counter
from datetime import datetime, date
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session
from dotenv import load_dotenv

load_dotenv()

from database import create_tables, get_db, User, Session as DBSession, Progress
from auth import (
    hash_password, verify_password, create_access_token, get_current_user
)
from inference import run_inference
from sentences import get_practice_sentences

app = FastAPI(title="Stutter Detection API", version="1.0.0")

# CORS — allow Vercel frontend + local dev
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:3001"
).split(",")
ALLOWED_ORIGINS = [o.strip() for o in ALLOWED_ORIGINS]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    create_tables()


# ─────────────────────────────────────────────
# Pydantic Schemas
# ─────────────────────────────────────────────

class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SaveProgressRequest(BaseModel):
    duration: float
    predicted_class: str
    label_counts: dict
    probabilities: Optional[dict] = None
    fluent_ratio: float = 0.0


# ─────────────────────────────────────────────
# AUTH ROUTES
# ─────────────────────────────────────────────

@app.post("/auth/signup")
def signup(body: SignupRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        name=body.name,
        email=body.email,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create initial progress record
    progress = Progress(user_id=user.id, stutter_history=[])
    db.add(progress)
    db.commit()

    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer", "user": {"id": user.id, "name": user.name, "email": user.email}}


@app.post("/auth/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer", "user": {"id": user.id, "name": user.name, "email": user.email}}


@app.post("/auth/logout")
def logout(current_user: User = Depends(get_current_user)):
    # JWT is stateless — client drops the token
    return {"message": "Logged out successfully"}


@app.get("/auth/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "name": current_user.name, "email": current_user.email}


# ─────────────────────────────────────────────
# AUDIO + PREDICTION ROUTES
# ─────────────────────────────────────────────

@app.post("/upload-audio")
async def upload_audio(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if file.content_type not in [
        "audio/wav", "audio/wave", "audio/webm", "audio/ogg",
        "audio/mp4", "audio/mpeg", "audio/x-wav", "application/octet-stream"
    ]:
        # Accept anyway — ffmpeg will handle conversion
        pass

    audio_bytes = await file.read()
    if len(audio_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty audio file")

    result = run_inference(audio_bytes, file.filename or "audio.webm")

    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])

    # Save session
    session = DBSession(
        user_id=current_user.id,
        duration=result.get("duration", 0),
        predicted_class=result.get("predicted_class"),
        label_counts=result.get("label_counts"),
        probabilities=result.get("probabilities"),
        fluent_ratio=result.get("fluent_ratio", 0),
    )
    db.add(session)
    db.commit()

    # Update progress
    _update_progress(db, current_user.id, result)

    return result


@app.post("/predict")
async def predict(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    audio_bytes = await file.read()
    result = run_inference(audio_bytes, file.filename or "audio.webm")
    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])
    return result


# ─────────────────────────────────────────────
# SENTENCES ROUTE
# ─────────────────────────────────────────────

@app.get("/get-sentences")
def get_sentences(
    current_user: User = Depends(get_current_user),
    count: int = 3,
):
    sentences = get_practice_sentences(str(current_user.id), count)
    return {"sentences": sentences}


# ─────────────────────────────────────────────
# PROGRESS ROUTES
# ─────────────────────────────────────────────

@app.post("/save-progress")
def save_progress(
    body: SaveProgressRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = body.model_dump()
    result["fluent_ratio"] = body.fluent_ratio
    _update_progress(db, current_user.id, result)
    return {"message": "Progress saved"}


@app.get("/get-progress")
def get_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    progress = db.query(Progress).filter(Progress.user_id == current_user.id).first()
    sessions = (
        db.query(DBSession)
        .filter(DBSession.user_id == current_user.id)
        .order_by(DBSession.timestamp.desc())
        .limit(50)
        .all()
    )

    if not progress:
        return {
            "total_time": 0, "session_count": 0, "streak": 0,
            "improvement_score": 0, "points": 0,
            "stutter_history": [], "sessions": [],
        }

    sessions_data = []
    for s in sessions:
        sessions_data.append({
            "id": s.id,
            "duration": s.duration,
            "predicted_class": s.predicted_class,
            "label_counts": s.label_counts,
            "probabilities": s.probabilities,
            "fluent_ratio": s.fluent_ratio,
            "timestamp": s.timestamp.isoformat() if s.timestamp else None,
        })

    return {
        "total_time": progress.total_time,
        "session_count": progress.session_count,
        "streak": progress.streak,
        "improvement_score": progress.improvement_score,
        "points": progress.points,
        "stutter_history": progress.stutter_history or [],
        "sessions": sessions_data,
    }


# ─────────────────────────────────────────────
# Internal helper
# ─────────────────────────────────────────────

def _update_progress(db: Session, user_id: int, result: dict):
    progress = db.query(Progress).filter(Progress.user_id == user_id).first()
    if not progress:
        progress = Progress(user_id=user_id, stutter_history=[])
        db.add(progress)

    progress.total_time = (progress.total_time or 0) + result.get("duration", 0)
    progress.session_count = (progress.session_count or 0) + 1
    progress.points = (progress.points or 0) + max(10, int(result.get("duration", 0) / 3))

    today = date.today().isoformat()
    if progress.last_session_date == today:
        pass  # same day
    elif progress.last_session_date:
        from datetime import date as dt
        last = dt.fromisoformat(progress.last_session_date)
        diff = (dt.today() - last).days
        progress.streak = (progress.streak or 0) + 1 if diff == 1 else 1
    else:
        progress.streak = 1
    progress.last_session_date = today

    # Fluent ratio trend → improvement score
    history = list(progress.stutter_history or [])
    history.append({
        "date": today,
        "timestamp": datetime.utcnow().isoformat(),
        "label_counts": result.get("label_counts", {}),
        "fluent_ratio": result.get("fluent_ratio", 0),
        "predicted_class": result.get("predicted_class", ""),
        "duration": result.get("duration", 0),
    })
    # Keep last 100 entries
    progress.stutter_history = history[-100:]
    # Improvement: average fluent ratio of last 5 vs previous 5
    ratios = [h.get("fluent_ratio", 0) for h in history]
    if len(ratios) >= 6:
        recent = sum(ratios[-5:]) / 5
        older = sum(ratios[-10:-5]) / 5 if len(ratios) >= 10 else ratios[0]
        progress.improvement_score = round((recent - older) * 100, 1)
    else:
        progress.improvement_score = round((ratios[-1] if ratios else 0) * 100, 1)

    db.commit()


@app.get("/health")
def health():
    return {"status": "ok"}
