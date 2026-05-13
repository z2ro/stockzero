import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.game import Game


def save_pgn_file(game_id: int, pgn: str) -> Path:
    path = get_settings().data_dir / "pgn" / f"game_{game_id}.pgn"
    path.write_text(pgn, encoding="utf-8")
    return path


def create_game_record(
    db: Session,
    pgn: str,
    metadata: dict,
    source: str,
    username: str | None = None,
    url: str | None = None,
    analysis: dict | None = None,
    report: dict | None = None,
) -> Game:
    game = Game(
        source=source,
        username=username,
        url=url,
        pgn=pgn,
        white=metadata.get("white"),
        black=metadata.get("black"),
        white_rating=metadata.get("white_rating"),
        black_rating=metadata.get("black_rating"),
        played_at=metadata.get("date"),
        result=metadata.get("result"),
        opening=metadata.get("opening"),
        eco=metadata.get("eco"),
        time_control=metadata.get("time_control"),
        analysis_json=json.dumps(analysis, ensure_ascii=False) if analysis is not None else None,
        report_json=json.dumps(report, ensure_ascii=False) if report is not None else None,
    )
    db.add(game)
    db.commit()
    db.refresh(game)
    save_pgn_file(game.id, pgn)
    return game


def game_to_dict(game: Game) -> dict:
    return {
        "id": game.id,
        "source": game.source,
        "username": game.username,
        "url": game.url,
        "white": game.white,
        "black": game.black,
        "white_rating": game.white_rating,
        "black_rating": game.black_rating,
        "played_at": game.played_at,
        "result": game.result,
        "opening": game.opening,
        "eco": game.eco,
        "time_control": game.time_control,
        "pgn": game.pgn,
        "analysis": json.loads(game.analysis_json) if game.analysis_json else None,
        "report": json.loads(game.report_json) if game.report_json else None,
    }
