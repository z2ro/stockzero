from typing import Literal

from pydantic import BaseModel, Field


class PgnAnalyzeRequest(BaseModel):
    pgn: str = Field(..., min_length=10)
    depth: int | None = Field(default=None, ge=1, le=40)
    multipv: int | None = Field(default=None, ge=1, le=5)
    max_moves: int | None = Field(default=None, ge=1)


class ChessComAnalyzeRequest(BaseModel):
    username: str
    year: int | None = Field(default=None, ge=2007)
    month: int | None = Field(default=None, ge=1, le=12)
    time_control: str | None = None
    color: Literal["white", "black"] | None = None
    result: str | None = None
    rating_min: int | None = None
    rating_max: int | None = None
    limit: int = Field(default=1, ge=1, le=20)
    depth: int | None = Field(default=None, ge=1, le=40)
    multipv: int | None = Field(default=None, ge=1, le=5)
    max_moves: int | None = Field(default=None, ge=1)


class ChessComSingleGameAnalyzeRequest(BaseModel):
    username: str
    pgn: str = Field(..., min_length=10)
    url: str | None = None
    depth: int | None = Field(default=None, ge=1, le=40)
    multipv: int | None = Field(default=None, ge=1, le=5)
    max_moves: int | None = Field(default=None, ge=1)


class GameSummary(BaseModel):
    id: int
    source: str
    username: str | None
    white: str | None
    black: str | None
    white_rating: int | None
    black_rating: int | None
    played_at: str | None
    result: str | None
    opening: str | None
    eco: str | None
    time_control: str | None

    model_config = {"from_attributes": True}


class AnalyzeResponse(BaseModel):
    game_id: int
    metadata: dict
    report: dict
