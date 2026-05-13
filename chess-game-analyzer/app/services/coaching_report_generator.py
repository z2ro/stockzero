from app.services.coaching_utils import INSUFFICIENT_EVIDENCE, critical_moves
from app.services.game_phase_analyzer import analyze_game_phases
from app.services.pattern_detector import detect_patterns_by_color
from app.services.player_summary_generator import explain_critical_move, generate_player_summaries
from app.services.study_plan_generator import generate_study_plan


def _overall_lesson(player_summaries: dict, study_plan: dict) -> str:
    priorities = study_plan.get("priorities") or []
    if priorities:
        return (
            priorities[0].get("daily_exercise")
            or study_plan.get("summary")
            or INSUFFICIENT_EVIDENCE
        )
    lessons = [
        summary.get("main_lesson")
        for summary in player_summaries.values()
        if summary.get("main_lesson")
    ]
    return lessons[0] if lessons else INSUFFICIENT_EVIDENCE


def _headline(player_summaries: dict) -> str:
    white = player_summaries.get("white", {})
    black = player_summaries.get("black", {})
    white_problem = white.get("main_weakness") or INSUFFICIENT_EVIDENCE
    black_problem = black.get("main_weakness") or INSUFFICIENT_EVIDENCE
    return f"Principal problema das brancas: {white_problem} Principal problema das pretas: {black_problem}"


def generate_coaching_report(metadata: dict, analysis: dict) -> dict:
    moves = analysis.get("moves") or []
    phase_analysis = analyze_game_phases(moves)
    patterns_by_color = detect_patterns_by_color(moves)
    player_summaries = generate_player_summaries(metadata, moves, patterns_by_color, phase_analysis)
    critical = [explain_critical_move(move) for move in critical_moves(moves)[:8]]
    study_plan = generate_study_plan(patterns_by_color, critical)

    if critical:
        critical_summary = f"Foram encontrados {len(critical)} momentos críticos; comece por {critical[0]['move_ref']}."
    else:
        critical_summary = INSUFFICIENT_EVIDENCE

    coaching_summary = {
        "headline": _headline(player_summaries),
        "game_summary": study_plan.get("summary") or INSUFFICIENT_EVIDENCE,
        "critical_summary": critical_summary,
        "main_lesson": _overall_lesson(player_summaries, study_plan),
        "white_focus": player_summaries["white"].get("main_weakness"),
        "black_focus": player_summaries["black"].get("main_weakness"),
    }

    return {
        "player_summaries": player_summaries,
        "coaching_summary": coaching_summary,
        "study_plan": study_plan,
        "critical_moments": critical,
        "patterns": patterns_by_color,
        "phase_analysis": phase_analysis,
    }
