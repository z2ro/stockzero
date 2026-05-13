from app.services.coaching_report_generator import generate_coaching_report
from app.services.game_phase_analyzer import analyze_game_phases
from app.services.pattern_detector import detect_patterns
from app.services.player_summary_generator import explain_critical_move, generate_player_summaries
from app.services.study_plan_generator import generate_study_plan


def _move(
    color="white",
    move_number=8,
    played="h3",
    best="Kc2",
    phase="opening",
    themes=None,
    cp_loss=320,
):
    themes = themes or ["erro de abertura", "desenvolvimento atrasado", "rei exposto"]
    return {
        "color": color,
        "move_number": move_number,
        "played_san": played,
        "best_move_san": best,
        "classification": "Blunder" if cp_loss >= 300 else "Mistake",
        "phase": phase,
        "themes": themes,
        "cp_loss": cp_loss,
        "pv": [best, "Nf6"],
        "explanation": {
            "why_it_worsens": f"{played} tenta resolver uma ameaça local, mas deixa o rei no centro.",
            "missed_idea": f"{best} melhorava a segurança do rei e coordenava as torres.",
            "direct_comparison": [
                {"played": "move um peão lateral", "best": "melhora a segurança do rei"}
            ],
            "position_priorities": ["segurança do rei", "desenvolvimento"],
            "concrete_consequences": ["Rei continua vulnerável"],
        },
    }


def _analysis():
    return {
        "moves": [
            {
                "color": "white",
                "move_number": 1,
                "played_san": "e4",
                "classification": "Best",
                "phase": "opening",
                "cp_loss": 0,
            },
            _move(),
            _move(
                move_number=9,
                played="a3",
                best="Nf3",
                themes=["perda de tempo", "desenvolvimento atrasado"],
                cp_loss=180,
            ),
            _move(
                color="black",
                move_number=12,
                played="Qh4",
                best="Nf6",
                phase="middlegame",
                themes=["peça pendurada", "cálculo insuficiente"],
                cp_loss=260,
            ),
        ]
    }


def test_explain_critical_move_compares_played_and_best_move():
    moment = explain_critical_move(_move())

    assert moment["what_player_tried"] == "O lance jogado tentou move um peão lateral."
    assert "deixa o rei no centro" in moment["problem"]
    assert "segurança do rei" in moment["why_best_was_better"]
    assert moment["position_priority"] == ["segurança do rei", "desenvolvimento"]
    assert moment["practical_consequence"] == "Rei continua vulnerável"


def test_detect_patterns_groups_recurrent_errors_with_phase_and_evidence():
    patterns = detect_patterns(_analysis()["moves"], "white")

    pattern_names = [pattern["pattern"] for pattern in patterns]
    assert "desenvolvimento atrasado" in pattern_names
    development = next(
        pattern for pattern in patterns if pattern["pattern"] == "desenvolvimento atrasado"
    )
    assert development["severity"] == "medium"
    assert development["affected_phase"] == "opening"
    assert development["study_priority"] == 1
    assert development["evidence"]


def test_game_phase_analyzer_separates_errors_by_phase():
    phases = analyze_game_phases(_analysis()["moves"])

    assert phases["white"]["critical_by_phase"]["opening"] == 2
    assert phases["white"]["worst_phase"] == "opening"
    assert phases["black"]["critical_by_phase"]["middlegame"] == 1


def test_player_summaries_include_weaknesses_critical_moments_and_lesson():
    analysis = _analysis()
    phases = analyze_game_phases(analysis["moves"])
    patterns_by_color = {
        "white": detect_patterns(analysis["moves"], "white"),
        "black": detect_patterns(analysis["moves"], "black"),
    }

    summaries = generate_player_summaries(
        {"white": "AdrielIGF", "black": "Rival"}, analysis["moves"], patterns_by_color, phases
    )

    assert summaries["white"]["player"] == "AdrielIGF"
    assert summaries["white"]["worst_phase"] == "opening"
    assert summaries["white"]["critical_moments"][0]["best_move"] == "Kc2"
    assert "segurança" in summaries["white"]["main_lesson"]
    assert summaries["black"]["critical_moments"]


def test_study_plan_uses_multiple_errors_and_includes_all_areas():
    analysis = _analysis()
    patterns_by_color = {
        "white": detect_patterns(analysis["moves"], "white"),
        "black": detect_patterns(analysis["moves"], "black"),
    }
    critical = [
        explain_critical_move(move)
        for move in analysis["moves"]
        if move.get("classification") in {"Mistake", "Blunder"}
    ]

    plan = generate_study_plan(patterns_by_color, critical)

    assert plan["priorities"]
    assert "Estude cálculo insuficiente" not in str(plan)
    assert set(plan["areas"]) == {"opening", "tactics", "strategy", "endgames", "time_management"}
    assert plan["areas"]["opening"]["themes"]
    assert plan["areas"]["endgames"]["diagnosis"] == "Poucos dados relevantes nesta partida."


def test_coaching_report_final_json_contains_required_sections():
    report = generate_coaching_report({"white": "AdrielIGF", "black": "Rival"}, _analysis())

    assert set(report) >= {
        "player_summaries",
        "coaching_summary",
        "study_plan",
        "critical_moments",
        "patterns",
        "phase_analysis",
    }
    assert report["player_summaries"]["white"]["main_weakness"]
    assert report["coaching_summary"]["main_lesson"]
    assert report["study_plan"]["priorities"][0]["examples_from_game"]
    assert report["critical_moments"][0]["problem"]
