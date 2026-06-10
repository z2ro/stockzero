from app.services.report_generator import generate_report


def test_report_includes_counts_biggest_error_and_curve():
    analysis = {
        "moves": [
            {
                "color": "white",
                "classification": "Best",
                "cp_loss": 0,
                "phase": "opening",
                "move_number": 1,
                "played_san": "e4",
            },
            {
                "color": "black",
                "classification": "Blunder",
                "cp_loss": 450,
                "phase": "middlegame",
                "move_number": 8,
                "played_san": "Qh4",
                "themes": ["peça pendurada"],
            },
        ],
        "evaluation_curve": [{"ply": 1, "white_cp": 20}],
    }

    report = generate_report({"white": "Alice", "black": "Bob", "opening": "Test"}, analysis)

    assert report["counts"]["black"]["Blunder"] == 1
    assert report["biggest_error"]["played_san"] == "Qh4"
    assert report["worst_phase"] == "middlegame"
    assert report["worst_phase_label"] == "meio-jogo"
    assert report["critical_cards"][0]["classification_label"] == "Erro grave"
    assert "Principal problema" in report["coach_summary"]["headline"]
    assert "player_summaries" in report
    assert "coaching_summary" in report
    assert "study_plan" in report
    assert "critical_moments" in report


def test_report_card_preserves_human_explanation_sections():
    analysis = {
        "moves": [
            {
                "color": "white",
                "classification": "Blunder",
                "cp_loss": 320,
                "phase": "opening",
                "move_number": 5,
                "played_san": "h3",
                "best_move_san": "Kc2",
                "themes": ["erro de abertura", "desenvolvimento atrasado"],
                "explanation": {
                    "situation_before": "O rei branco ainda está no centro.",
                    "why_it_worsens": "h3 não resolve a segurança do rei.",
                    "missed_idea": "Kc2 tira o rei da coluna central.",
                    "direct_comparison": [{"played": "peão lateral", "best": "rei sai do centro"}],
                    "opponent_plan": "As pretas podem abrir linhas.",
                    "position_priorities": ["segurança do rei", "desenvolvimento"],
                    "concrete_consequences": ["Rei continua vulnerável"],
                    "human_evaluation": "pretas claramente melhores",
                },
            }
        ],
        "evaluation_curve": [],
    }

    report = generate_report({"white": "Alice", "black": "Bob"}, analysis)

    card = report["critical_cards"][0]
    assert card["situation_before"] == "O rei branco ainda está no centro."
    assert card["direct_comparison"][0]["played"] == "peão lateral"
    assert card["position_priorities"] == ["segurança do rei", "desenvolvimento"]
    assert card["human_evaluation"] == "pretas claramente melhores"
