from app.services.report_generator import generate_report


def test_report_includes_counts_biggest_error_and_curve():
    analysis = {
        "moves": [
            {"color": "white", "classification": "Best", "cp_loss": 0, "phase": "opening", "move_number": 1, "played_san": "e4"},
            {"color": "black", "classification": "Blunder", "cp_loss": 450, "phase": "middlegame", "move_number": 8, "played_san": "Qh4", "themes": ["peça pendurada"]},
        ],
        "evaluation_curve": [{"ply": 1, "white_cp": 20}],
    }

    report = generate_report({"white": "Alice", "black": "Bob", "opening": "Test"}, analysis)

    assert report["counts"]["black"]["Blunder"] == 1
    assert report["biggest_error"]["played_san"] == "Qh4"
    assert report["worst_phase"] == "middlegame"
