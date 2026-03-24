"""
database.py - SQLAlchemy database setup with PostgreSQL support
Falls back to SQLite for local development if DATABASE_URL is not set.
"""
import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./stutter_app.db")

# Fix for psycopg2 on Render (postgres:// -> postgresql://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    sessions = relationship("Session", back_populates="user")
    progress = relationship("Progress", back_populates="user", uselist=False)


class Session(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    audio_path = Column(String, nullable=True)
    duration = Column(Float, default=0.0)
    predicted_class = Column(String, nullable=True)
    label_counts = Column(JSON, nullable=True)
    probabilities = Column(JSON, nullable=True)
    fluent_ratio = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="sessions")


class Progress(Base):
    __tablename__ = "progress"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    total_time = Column(Float, default=0.0)       # total speaking time in seconds
    session_count = Column(Integer, default=0)
    improvement_score = Column(Float, default=0.0)
    streak = Column(Integer, default=0)
    last_session_date = Column(String, nullable=True)
    points = Column(Integer, default=0)
    stutter_history = Column(JSON, default=list)  # list of {date, label_counts, fluent_ratio}

    user = relationship("User", back_populates="progress")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    Base.metadata.create_all(bind=engine)
