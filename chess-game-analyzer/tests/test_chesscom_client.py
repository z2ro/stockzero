from app.services.chesscom_client import filter_games


def test_filter_games_by_color_result_and_rating():
    games = [
        {"white": {"username": "Alice", "rating": 1500, "result": "win"}, "black": {"username": "Bob", "rating": 1400}, "time_control": "600"},
        {"white": {"username": "Carol", "rating": 1300}, "black": {"username": "Alice", "rating": 1200, "result": "checkmated"}, "time_control": "300"},
    ]

    selected = filter_games(games, "alice", color="white", result="win", rating_min=1400)

    assert len(selected) == 1
    assert selected[0]["time_control"] == "600"
