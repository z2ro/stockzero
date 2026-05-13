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
        "pgn": "[Event \"Test\"]\n\n1. e4 1-0",
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
