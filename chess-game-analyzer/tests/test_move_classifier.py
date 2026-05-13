from app.services.move_classifier import classify_move


def test_classifies_by_centipawn_loss():
    assert classify_move(5, 20, 15, "middlegame") == "Best"
    assert classify_move(120, 20, -100, "middlegame") == "Inaccuracy"
    assert classify_move(260, 100, -160, "middlegame") == "Mistake"


def test_detects_blunder_but_not_when_already_lost():
    assert classify_move(500, 50, -450, "middlegame") == "Blunder"
    assert classify_move(500, -800, -1300, "middlegame") == "Mistake"


def test_detects_missed_win():
    assert classify_move(350, 420, 40, "middlegame") == "Missed Win"
