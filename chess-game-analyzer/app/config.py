from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Chess Game Analyzer"
    database_url: str = Field(default="sqlite:///./data/chess_analyzer.db", alias="DATABASE_URL")
    stockfish_path: str = Field(default="stockfish", alias="STOCKFISH_PATH")
    stockfish_depth: int = Field(default=16, alias="STOCKFISH_DEPTH")
    stockfish_multipv: int = Field(default=3, alias="STOCKFISH_MULTIPV")
    stockfish_move_time_ms: int | None = Field(default=None, alias="STOCKFISH_MOVE_TIME_MS")
    chesscom_user_agent: str = Field(
        default="chess-game-analyzer/0.1 contact: local@example.com",
        alias="CHESSCOM_USER_AGENT",
    )
    data_dir: Path = Field(default=Path("data"), alias="DATA_DIR")

    model_config = SettingsConfigDict(env_file=".env", populate_by_name=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    (settings.data_dir / "pgn").mkdir(parents=True, exist_ok=True)
    return settings
