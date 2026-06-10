from app.services.coaching_utils import (
    INSUFFICIENT_EVIDENCE,
    best_ref,
    critical_moves,
    move_ref,
    phase_label,
)
from app.services.pattern_detector import PATTERN_WEAKNESS

POSITIVE_LABELS = {"Best", "Excellent", "Good", "Book move", "Forced"}


def _strengths_for(moves: list[dict], color: str) -> list[str]:
    color_moves = [move for move in moves if move.get("color") == color]
    positives = [move for move in color_moves if move.get("classification") in POSITIVE_LABELS]
    strengths: list[str] = []
    if positives:
        strengths.append(
            "Encontrou lances saudáveis em parte da partida e manteve decisões aceitáveis em vários momentos."
        )
    if any(
        move.get("phase") == "opening"
        and move.get("classification") in {"Book move", "Best", "Excellent"}
        for move in color_moves
    ):
        strengths.append(
            "Teve pelo menos algumas decisões de abertura compatíveis com princípios ou teoria."
        )
    if any((move.get("cp_loss") or 0) <= 35 for move in color_moves):
        strengths.append("Em lances tranquilos, conseguiu evitar perdas relevantes de avaliação.")
    return strengths[:3] or [INSUFFICIENT_EVIDENCE]


def explain_critical_move(move: dict) -> dict:
    explanation = move.get("explanation") or {}
    priorities = explanation.get("position_priorities") or []
    consequences = explanation.get("concrete_consequences") or []
    themes = move.get("themes") or []
    problem = (
        explanation.get("why_it_worsens")
        or "Não há evidência suficiente nesta partida para concluir isso."
    )
    why_best = (
        explanation.get("missed_idea")
        or "Não há evidência suficiente nesta partida para concluir isso."
    )
    attempted = "Não há evidência suficiente nesta partida para concluir isso."
    comparison = explanation.get("direct_comparison") or []
    if comparison and comparison[0].get("played"):
        attempted = f"O lance jogado tentou {comparison[0]['played']}."
    elif move.get("played_san"):
        attempted = f"O lance {move['played_san']} foi a escolha prática do jogador nesta posição."

    return {
        "move_number": move.get("move_number"),
        "move": move.get("played_san"),
        "move_ref": move_ref(move),
        "best_move": best_ref(move),
        "classification": move.get("classification"),
        "phase": move.get("phase"),
        "phase_label": phase_label(move.get("phase")),
        "problem": problem,
        "what_player_tried": attempted,
        "why_best_was_better": why_best,
        "position_priority": priorities or [INSUFFICIENT_EVIDENCE],
        "practical_consequence": consequences[0] if consequences else INSUFFICIENT_EVIDENCE,
        "study_theme": themes[0] if themes else INSUFFICIENT_EVIDENCE,
        "themes": themes,
        "cp_loss": move.get("cp_loss"),
        "pv": move.get("pv") or [],
    }


def _main_lesson(patterns: list[dict], critical: list[dict]) -> str:
    if patterns:
        top = patterns[0]
        phase = phase_label(top.get("affected_phase"))
        if top["pattern"] in {
            "rei inseguro",
            "desenvolvimento atrasado",
            "excesso de lances de peão",
        }:
            return f"Na {phase}, segurança do rei, desenvolvimento e coordenação precisavam vir antes de ameaças locais."
        if top["pattern"] == "cálculo tático insuficiente":
            return "Antes de capturas, xeques ou lances de peão, calcule as respostas forçadas do adversário por 2 a 3 lances."
        return f"O padrão mais importante foi {top['pattern']}; revise os exemplos críticos antes de estudar temas novos."
    if critical:
        return "Revise os lances críticos individualmente; não houve recorrência suficiente para apontar um único padrão dominante."
    return INSUFFICIENT_EVIDENCE


def generate_player_summary(
    metadata: dict,
    moves: list[dict],
    color: str,
    patterns: list[dict],
    phase_analysis: dict,
) -> dict:
    player = metadata.get(color) or ("Brancas" if color == "white" else "Pretas")
    critical = critical_moves(moves, color)
    weakness_texts = [
        pattern.get("weakness_text") or PATTERN_WEAKNESS.get(pattern["pattern"], pattern["pattern"])
        for pattern in patterns[:4]
    ]
    critical_moments = [explain_critical_move(move) for move in critical[:4]]
    main_weakness = weakness_texts[0] if weakness_texts else INSUFFICIENT_EVIDENCE
    phase_data = phase_analysis.get(color, {})
    worst_phase = phase_data.get("worst_phase")
    suggestion = (
        _suggestion_for_pattern(patterns[0])
        if patterns
        else "Não há evidência suficiente nesta partida para concluir isso."
    )

    return {
        "player": player,
        "color": color,
        "strengths": _strengths_for(moves, color),
        "weaknesses": weakness_texts or [INSUFFICIENT_EVIDENCE],
        "critical_moments": critical_moments,
        "recurring_patterns": patterns,
        "worst_phase": worst_phase,
        "worst_phase_label": phase_label(worst_phase),
        "critical_by_phase": phase_data.get("critical_by_phase", {}),
        "main_weakness": main_weakness,
        "practical_suggestion": suggestion,
        "main_lesson": _main_lesson(patterns, critical),
    }


def _suggestion_for_pattern(pattern: dict) -> str:
    name = pattern.get("pattern")
    if name in {"rei inseguro", "desenvolvimento atrasado", "excesso de lances de peão"}:
        return "Antes de mover peões laterais na abertura, pergunte se o lance desenvolve peça, melhora o rei ou disputa o centro."
    if name == "cálculo tático insuficiente":
        return "Treine calcular ameaças do adversário antes de escolher lances candidatos próprios."
    if name == "peça pendurada":
        return "Antes de confirmar o lance, liste quais peças suas estão atacadas e quais estão realmente defendidas."
    if name == "troca ruim":
        return "Antes de trocar, compare qual peça melhora depois da troca e se o final resultante favorece você."
    return f"Revise os exemplos de {name} e transforme esse padrão em uma pergunta antes de cada lance."


def generate_player_summaries(
    metadata: dict,
    moves: list[dict],
    patterns_by_color: dict[str, list[dict]],
    phase_analysis: dict,
) -> dict:
    return {
        color: generate_player_summary(
            metadata, moves, color, patterns_by_color.get(color, []), phase_analysis
        )
        for color in ("white", "black")
    }


def summarize_color_errors(moves: list[dict]) -> dict[str, int]:
    return {color: len(critical_moves(moves, color)) for color in ("white", "black")}
