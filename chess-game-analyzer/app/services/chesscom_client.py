from datetime import UTC, datetime
from urllib.parse import quote

import httpx

from app.config import get_settings

API_BASE = "https://api.chess.com/pub"


def normalize_username(username: str) -> str:
    return quote(username.strip().lower(), safe="")


class ChessComClient:
    def __init__(self, timeout: float = 20.0):
        settings = get_settings()
        self.headers = {"User-Agent": settings.chesscom_user_agent}
        self.timeout = timeout

    async def _get_json(self, url: str) -> dict:
        async with httpx.AsyncClient(
            headers=self.headers, timeout=self.timeout, follow_redirects=True
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()

    async def archives(self, username: str) -> list[str]:
        normalized = normalize_username(username)
        data = await self._get_json(f"{API_BASE}/player/{normalized}/games/archives")
        return data.get("archives", [])

    async def games_for_month(self, username: str, year: int, month: int) -> list[dict]:
        normalized = normalize_username(username)
        data = await self._get_json(f"{API_BASE}/player/{normalized}/games/{year:04d}/{month:02d}")
        return data.get("games", [])

    async def fetch_games(
        self,
        username: str,
        year: int | None = None,
        month: int | None = None,
        limit: int = 20,
    ) -> list[dict]:
        if year and month:
            return (await self.games_for_month(username, year, month))[:limit]

        archives = await self.archives(username)
        selected = archives[-3:]
        games: list[dict] = []
        for archive in reversed(selected):
            parts = archive.rstrip("/").split("/")
            archive_year = int(parts[-2])
            archive_month = int(parts[-1])
            games.extend(await self.games_for_month(username, archive_year, archive_month))
            if len(games) >= limit:
                break
        return games[:limit]


def _player_result(game: dict, username: str) -> str | None:
    lower = username.strip().lower()
    for color in ("white", "black"):
        player = game.get(color, {})
        if player.get("username", "").lower() == lower:
            return player.get("result")
    return None


def _player_color(game: dict, username: str) -> str | None:
    lower = username.strip().lower()
    for color in ("white", "black"):
        if game.get(color, {}).get("username", "").lower() == lower:
            return color
    return None


def filter_games(
    games: list[dict],
    username: str,
    time_control: str | None = None,
    color: str | None = None,
    result: str | None = None,
    rating_min: int | None = None,
    rating_max: int | None = None,
) -> list[dict]:
    filtered: list[dict] = []
    for game in games:
        player_color = _player_color(game, username)
        if color and player_color != color:
            continue
        if result and _player_result(game, username) != result:
            continue
        if time_control and game.get("time_control") != time_control:
            continue
        if player_color:
            rating = game.get(player_color, {}).get("rating")
            if rating_min is not None and (rating is None or rating < rating_min):
                continue
            if rating_max is not None and (rating is None or rating > rating_max):
                continue
        filtered.append(game)
    return filtered


def chesscom_game_to_pgn(game: dict) -> str | None:
    return game.get("pgn")


def played_date_from_timestamp(timestamp: int | None) -> str | None:
    if not timestamp:
        return None
    return datetime.fromtimestamp(timestamp, UTC).date().isoformat()


def _score_from_result(result: str | None) -> str:
    if result in {"win"}:
        return "1"
    draw_results = {
        "agreed",
        "repetition",
        "stalemate",
        "insufficient",
        "50move",
        "timevsinsufficient",
    }
    if result in draw_results:
        return "½"
    if result is None:
        return "?"
    return "0"


def summarize_game(game: dict, username: str | None = None) -> dict:
    white = game.get("white", {})
    black = game.get("black", {})
    white_score = _score_from_result(white.get("result"))
    black_score = _score_from_result(black.get("result"))
    return {
        "id": game.get("uuid") or game.get("url"),
        "url": game.get("url"),
        "pgn": game.get("pgn"),
        "time_control": game.get("time_control"),
        "time_class": game.get("time_class"),
        "rated": game.get("rated"),
        "end_time": game.get("end_time"),
        "played_at": played_date_from_timestamp(game.get("end_time")),
        "white": {
            "username": white.get("username"),
            "rating": white.get("rating"),
            "result": white.get("result"),
            "score": white_score,
        },
        "black": {
            "username": black.get("username"),
            "rating": black.get("rating"),
            "result": black.get("result"),
            "score": black_score,
        },
        "result": f"{white_score}-{black_score}",
        "user_color": _player_color(game, username) if username else None,
        "user_result": _player_result(game, username) if username else None,
    }
