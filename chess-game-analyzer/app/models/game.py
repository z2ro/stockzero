from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(32), default="manual", index=True)
    username: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    pgn: Mapped[str] = mapped_column(Text)
    white: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    black: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    white_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    black_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    played_at: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    result: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    opening: Mapped[str | None] = mapped_column(String(255), nullable=True)
    eco: Mapped[str | None] = mapped_column(String(8), nullable=True)
    time_control: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    analysis_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
