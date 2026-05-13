from typing import Annotated, NoReturn

import httpx

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.init_db import init_db
from app.db.session import get_db
from app.models.game import Game
from app.schemas.api import (
    AnalyzeResponse,
    ChessComAnalyzeRequest,
    ChessComSingleGameAnalyzeRequest,
    GameSummary,
    PgnAnalyzeRequest,
)
from app.services.chesscom_client import (
    ChessComClient,
    chesscom_game_to_pgn,
    filter_games,
    summarize_game,
)
from app.services.game_analyzer import analyze_game
from app.services.pgn_parser import PgnValidationError, export_pgn, parse_pgn
from app.services.report_generator import generate_report
from app.services.storage import create_game_record, game_to_dict

app = FastAPI(title="Chess Game Analyzer", version="0.1.0")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


def _analyze_and_store(
    db: Session,
    pgn: str,
    source: str,
    username: str | None = None,
    url: str | None = None,
    depth: int | None = None,
    multipv: int | None = None,
    max_moves: int | None = None,
) -> AnalyzeResponse:
    try:
        parsed = parse_pgn(pgn)
    except PgnValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    analysis = analyze_game(parsed.game, depth=depth, multipv=multipv, max_moves=max_moves)
    report = generate_report(parsed.metadata, analysis)
    stored = create_game_record(
        db,
        export_pgn(parsed.game),
        parsed.metadata,
        source=source,
        username=username,
        url=url,
        analysis=analysis,
        report=report,
    )
    return AnalyzeResponse(game_id=stored.id, metadata=parsed.metadata, report=report)


@app.post("/analyze/pgn", response_model=AnalyzeResponse)
def analyze_pgn(
    payload: PgnAnalyzeRequest, db: Annotated[Session, Depends(get_db)]
) -> AnalyzeResponse:
    return _analyze_and_store(
        db,
        payload.pgn,
        source="manual",
        depth=payload.depth,
        multipv=payload.multipv,
        max_moves=payload.max_moves,
    )


@app.post("/analyze/pgn/upload", response_model=AnalyzeResponse)
async def analyze_pgn_upload(
    db: Annotated[Session, Depends(get_db)],
    pgn_file: UploadFile | None = File(default=None),
    pgn_text: str | None = Form(default=None),
    depth: int | None = Form(default=None),
    multipv: int | None = Form(default=None),
    max_moves: int | None = Form(default=None),
) -> AnalyzeResponse:
    pgn = pgn_text
    if pgn_file is not None:
        pgn = (await pgn_file.read()).decode("utf-8")
    if not pgn:
        raise HTTPException(status_code=400, detail="Envie um arquivo PGN ou cole o texto PGN.")
    return _analyze_and_store(
        db, pgn, source="manual", depth=depth, multipv=multipv, max_moves=max_moves
    )


def _raise_chesscom_http_error(exc: httpx.HTTPStatusError) -> NoReturn:
    status = exc.response.status_code
    if status == 404:
        raise HTTPException(
            status_code=404, detail="Jogador ou partidas públicas não encontrados no Chess.com."
        ) from exc
    raise HTTPException(
        status_code=502,
        detail=f"Chess.com respondeu com status {status} ao buscar partidas públicas.",
    ) from exc


def _raise_chesscom_request_error(exc: httpx.RequestError) -> NoReturn:
    raise HTTPException(
        status_code=502,
        detail="Não foi possível conectar à API pública do Chess.com.",
    ) from exc


@app.get("/players/{username}/chesscom-public-games")
async def chesscom_public_games(username: str, limit: int = 20) -> dict:
    client = ChessComClient()
    try:
        raw_games = await client.fetch_games(username, limit=min(max(limit, 1), 50))
    except httpx.HTTPStatusError as exc:
        _raise_chesscom_http_error(exc)
    except httpx.RequestError as exc:
        _raise_chesscom_request_error(exc)
    raw_games = sorted(raw_games, key=lambda game: game.get("end_time") or 0, reverse=True)
    games = [summarize_game(game, username) for game in raw_games if game.get("pgn")]
    return {"username": username, "games": games}


@app.post("/analyze/chesscom/game", response_model=AnalyzeResponse)
def analyze_single_chesscom_game(
    payload: ChessComSingleGameAnalyzeRequest,
    db: Annotated[Session, Depends(get_db)],
) -> AnalyzeResponse:
    return _analyze_and_store(
        db,
        payload.pgn,
        source="chesscom",
        username=payload.username,
        url=payload.url,
        depth=payload.depth,
        multipv=payload.multipv,
        max_moves=payload.max_moves,
    )


@app.post("/analyze/chesscom")
async def analyze_chesscom(
    payload: ChessComAnalyzeRequest,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    client = ChessComClient()
    try:
        raw_games = await client.fetch_games(
            payload.username, payload.year, payload.month, limit=max(payload.limit * 3, 20)
        )
    except httpx.HTTPStatusError as exc:
        _raise_chesscom_http_error(exc)
    except httpx.RequestError as exc:
        _raise_chesscom_request_error(exc)
    selected = filter_games(
        raw_games,
        payload.username,
        time_control=payload.time_control,
        color=payload.color,
        result=payload.result,
        rating_min=payload.rating_min,
        rating_max=payload.rating_max,
    )[: payload.limit]
    if not selected:
        raise HTTPException(
            status_code=404, detail="Nenhuma partida pública encontrada para os filtros."
        )

    analyzed = []
    for raw in selected:
        pgn = chesscom_game_to_pgn(raw)
        if not pgn:
            continue
        analyzed.append(
            _analyze_and_store(
                db,
                pgn,
                source="chesscom",
                username=payload.username,
                url=raw.get("url"),
                depth=payload.depth,
                multipv=payload.multipv,
                max_moves=payload.max_moves,
            ).model_dump()
        )
    return {"username": payload.username, "analyzed": analyzed}


@app.get("/games/{game_id}")
def get_game(game_id: int, db: Annotated[Session, Depends(get_db)]) -> dict:
    game = db.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Partida não encontrada.")
    return game_to_dict(game)


@app.get("/games/{game_id}/report")
def get_report(game_id: int, db: Annotated[Session, Depends(get_db)]) -> dict:
    game = db.get(Game, game_id)
    if not game or not game.report_json:
        raise HTTPException(status_code=404, detail="Relatório não encontrado.")
    return game_to_dict(game)["report"]


@app.get("/games/{game_id}/coaching-report")
def get_coaching_report(game_id: int, db: Annotated[Session, Depends(get_db)]) -> dict:
    report = get_report(game_id, db)
    return {
        "player_summaries": report.get("player_summaries", {}),
        "coaching_summary": report.get("coaching_summary", {}),
        "study_plan": report.get("study_plan", {}),
        "critical_moments": report.get("critical_moments", []),
        "patterns": report.get("patterns", {}),
        "phase_analysis": report.get("phase_analysis", {}),
    }


@app.get("/players/{username}/games", response_model=list[GameSummary])
def player_games(username: str, db: Annotated[Session, Depends(get_db)]) -> list[Game]:
    stmt = (
        select(Game)
        .where(or_(Game.username == username, Game.white == username, Game.black == username))
        .order_by(Game.created_at.desc())
    )
    return list(db.scalars(stmt).all())


@app.get("/players/{username}/study-plan")
def player_study_plan(username: str, db: Annotated[Session, Depends(get_db)]) -> dict:
    stmt = (
        select(Game)
        .where(or_(Game.username == username, Game.white == username, Game.black == username))
        .order_by(Game.created_at.desc())
        .limit(10)
    )
    games = list(db.scalars(stmt).all())
    if not games:
        raise HTTPException(status_code=404, detail="Nenhuma partida armazenada para o jogador.")
    plans = [game_to_dict(game)["report"].get("study_plan") for game in games if game.report_json]
    priorities: dict[str, int] = {}
    for plan in plans:
        if not plan:
            continue
        for item in plan.get("priorities", []):
            theme = item.get("theme") if isinstance(item, dict) else item
            if not theme:
                continue
            priorities[theme] = priorities.get(theme, 0) + 1
    ordered = sorted(priorities, key=priorities.get, reverse=True)[:5]
    return {
        "username": username,
        "priorities": ordered,
        "source_games": [game.id for game in games],
    }


@app.get("/", response_class=HTMLResponse)
def simple_ui() -> str:
    return """
    <html><body>
      <h1>Chess Game Analyzer</h1>
      <p>Use <code>/docs</code> para testar a API FastAPI.</p>
      <p>Endpoints principais: /analyze/pgn, /analyze/chesscom, /games/{id}/report.</p>
    </body></html>
    """
