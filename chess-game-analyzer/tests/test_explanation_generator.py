import chess

from app.services.explanation_generator import build_semantic_context, generate_explanation


def test_semantic_context_explains_human_priority_and_comparison():
    before = chess.Board()
    played = chess.Move.from_uci("h2h3")
    after_played = before.copy(stack=False)
    after_played.push(played)

    context = build_semantic_context(
        before=before,
        after_played=after_played,
        played_move=played,
        best_uci="e2e4",
        mover=chess.WHITE,
        phase="opening",
        eval_before_cp=35,
        cp_loss=180,
    )

    assert "prioridade" in context["situation_before"]
    assert "desenvolvimento" in context["position_priorities"]
    assert context["comparison"]
    assert context["practical_consequences"]


def test_generate_explanation_prefers_semantic_summary_over_cp_only_text():
    explanation = generate_explanation(
        {
            "classification": "Mistake",
            "played_san": "h3",
            "best_move_san": "e4",
            "cp_loss": 180,
            "themes": ["erro de abertura"],
            "pv": ["e4"],
            "material_delta": 0,
            "semantic_context": {
                "situation_before": "Antes do lance, desenvolvimento era prioridade.",
                "played_problem": "h3 não resolve a segurança do rei.",
                "best_move_value": "e4 briga pelo centro.",
                "opponent_plan": "O adversário ganha iniciativa.",
                "position_priorities": ["desenvolvimento", "controle central"],
                "comparison": [{"played": "lance lateral", "best": "ocupa o centro"}],
                "practical_consequences": ["Desenvolvimento atrasa."],
                "evaluation_human": "posição aproximadamente equilibrada",
            },
        }
    )

    assert explanation["why_it_worsens"] == "h3 não resolve a segurança do rei."
    assert "centipawns" not in explanation["human_summary"]
    assert explanation["direct_comparison"][0]["best"] == "ocupa o centro"
