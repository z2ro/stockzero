from app.services.chesscom_client import filter_games, summarize_game


def test_filter_games_by_color_result_and_rating():
    games = [
        {
            "white": {"username": "Alice", "rating": 1500, "result": "win"},
            "black": {"username": "Bob", "rating": 1400},
            "time_control": "600",
        },
        {
            "white": {"username": "Carol", "rating": 1300},
            "black": {"username": "Alice", "rating": 1200, "result": "checkmated"},
            "time_control": "300",
        },
    ]

    selected = filter_games(games, "alice", color="white", result="win", rating_min=1400)

    assert len(selected) == 1
    assert selected[0]["time_control"] == "600"


def test_summarize_game_for_review_panel():
    game = {
        "uuid": "abc",
        "url": "https://www.chess.com/game/live/abc",
        "pgn": '[Event "Test"]\n\n1. e4 1-0',
        "time_class": "rapid",
        "end_time": 1710000000,
        "white": {"username": "Alice", "rating": 1500, "result": "win"},
        "black": {"username": "Bob", "rating": 1400, "result": "checkmated"},
    }

    summary = summarize_game(game, "alice")

    assert summary["id"] == "abc"
    assert summary["result"] == "1-0"
    assert summary["user_color"] == "white"
    assert summary["white"]["rating"] == 1500


def test_normalize_username_lowercases_strips_and_escapes():
    from app.services.chesscom_client import normalize_username

    assert normalize_username(" VKRyuji ") == "vkryuji"
    assert normalize_username("Name/With Slash") == "name%2Fwith%20slash"


def test_client_uses_normalized_username_in_chesscom_urls():
    import asyncio

    from app.services.chesscom_client import API_BASE, ChessComClient

    class RecordingClient(ChessComClient):
        def __init__(self):
            super().__init__()
            self.urls = []

        async def _get_json(self, url: str) -> dict:
            self.urls.append(url)
            if url.endswith("/archives"):
                return {"archives": [f"{API_BASE}/player/vkryuji/games/2026/05"]}
            return {"games": [{"uuid": "game-1"}]}

    client = RecordingClient()

    games = asyncio.run(client.fetch_games(" VKRyuji ", limit=1))

    assert games == [{"uuid": "game-1"}]
    assert client.urls == [
        f"{API_BASE}/player/vkryuji/games/archives",
        f"{API_BASE}/player/vkryuji/games/2026/05",
    ]
