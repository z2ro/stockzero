import chess

from app.services.explanation_generator import generate_explanation


def test_generate_explanation_uses_human_coaching_sections():
    board = chess.Board()
    move = chess.Move.from_uci("h2h3")
    item = {
        "classification": "Mistake",
        "played_san": board.san(move),
        "played_uci": move.uci(),
        "best_move_uci": "g1f3",
        "best_move_san": "Nf3",
        "fen_before": board.fen(),
        "phase": "opening",
        "color": "white",
        "cp_loss": 180,
        "eval_before_cp": 20,
        "eval_after_cp": -160,
        "themes": ["erro de abertura"],
        "pv": ["Nf3", "Nf6"],
    }

    explanation = generate_explanation(item)

    assert explanation is not None
    assert "Antes do lance" in explanation["situation_before"]
    assert "segurança do rei" in explanation["position_priorities"]
    assert explanation["direct_comparison"]
    assert explanation["opponent_plan"]
    assert explanation["fen_after_played"]
    assert explanation["fen_after_best"]
