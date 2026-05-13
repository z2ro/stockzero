from collections import Counter, defaultdict

CRITICAL = {"Inaccuracy", "Mistake", "Blunder", "Missed Win"}
CLASS_LABELS_PT = {
    "Best": "Melhor lance",
    "Excellent": "Excelente",
    "Good": "Bom",
    "Inaccuracy": "Imprecisão",
    "Mistake": "Erro",
    "Blunder": "Erro grave",
    "Missed Win": "Vitória desperdiçada",
    "Forced": "Forçado",
    "Book move": "Lance teórico",
}
PHASE_LABELS_PT = {
    "opening": "abertura",
    "middlegame": "meio-jogo",
    "endgame": "final",
}


def _accuracy(losses: list[int]) -> float:
    if not losses:
        return 100.0
    avg = sum(min(loss, 1000) for loss in losses) / len(losses)
    return round(max(0.0, 100.0 - avg / 10.0), 1)


def _move_title(item: dict) -> str:
    color = "Brancas" if item.get("color") == "white" else "Pretas"
    return f"{color}, lance {item.get('move_number')}: {item.get('played_san')}"


def _friendly_cp(cp_loss: int | None) -> str:
    if cp_loss is None:
        return "mudança decisiva de mate"
    if cp_loss < 100:
        return f"perda pequena ({cp_loss} cp)"
    if cp_loss < 250:
        return f"perda relevante ({cp_loss} cp)"
    if cp_loss < 500:
        return f"perda grande ({cp_loss} cp)"
    return f"perda muito grande ({cp_loss} cp)"


def _critical_card(item: dict) -> dict:
    explanation = item.get("explanation") or {}
    best = item.get("best_move_san") or "não encontrado"
    themes = item.get("themes") or []
    return {
        "title": _move_title(item),
        "classification": item.get("classification"),
        "classification_label": CLASS_LABELS_PT.get(
            item.get("classification"), item.get("classification")
        ),
        "phase": item.get("phase"),
        "phase_label": PHASE_LABELS_PT.get(item.get("phase"), item.get("phase")),
        "played": item.get("played_san"),
        "best_move": best,
        "loss": _friendly_cp(item.get("cp_loss")),
        "themes": themes,
        "situation_before": explanation.get("situation_before"),
        "short_reason": explanation.get("why_it_worsens")
        or f"O lance {item.get('played_san')} piorou a avaliação em relação a {best}.",
        "coach_tip": explanation.get("missed_idea")
        or "Revise a posição no tabuleiro e compare com a melhor linha.",
        "direct_comparison": explanation.get("direct_comparison") or [],
        "opponent_plan": explanation.get("opponent_plan"),
        "position_priorities": explanation.get("position_priorities") or [],
        "priority_explanation": explanation.get("priority_explanation"),
        "concrete_consequences": explanation.get("concrete_consequences") or [],
        "human_evaluation": explanation.get("human_evaluation"),
        "fen_after_played": explanation.get("fen_after_played"),
        "fen_after_best": explanation.get("fen_after_best"),
        "pv": item.get("pv") or [],
        "ply": item.get("ply"),
        "move_number": item.get("move_number"),
        "color": item.get("color"),
        "cp_loss": item.get("cp_loss"),
    }


def generate_report(metadata: dict, analysis: dict) -> dict:
    moves = analysis.get("moves", [])
    by_color = {"white": [], "black": []}
    counts = {"white": Counter(), "black": Counter()}
    phase_errors = defaultdict(int)
    critical = []

    for item in moves:
        color = item["color"]
        loss = item.get("cp_loss") or 0
        by_color[color].append(loss)
        counts[color][item["classification"]] += 1
        if item["classification"] in CRITICAL:
            critical.append(item)
            phase_errors[item["phase"]] += 1

    biggest = max(critical, key=lambda item: item.get("cp_loss") or 0, default=None)
    critical_moment = biggest
    worst_phase = max(phase_errors.items(), key=lambda pair: pair[1], default=(None, 0))[0]
    critical_cards = [
        _critical_card(item)
        for item in sorted(critical, key=lambda item: item.get("cp_loss") or 0, reverse=True)[:5]
    ]

    white_name = metadata.get("white") or "Brancas"
    black_name = metadata.get("black") or "Pretas"
    opening = metadata.get("opening") or "desconhecida"
    summary = (
        f"{white_name} vs {black_name}. A abertura registrada foi {opening}. "
        f"O ponto principal para revisar é {_move_title(biggest)}: "
        f"{CLASS_LABELS_PT.get(biggest['classification'], biggest['classification'])} com "
        f"{_friendly_cp(biggest.get('cp_loss'))}. Compare no tabuleiro com "
        f"{biggest.get('best_move_san') or 'a melhor linha sugerida'}."
        if biggest
        else f"{white_name} vs {black_name}: partida sem erros críticos no trecho analisado."
    )

    return {
        "metadata": metadata,
        "accuracy": {
            "white": _accuracy(by_color["white"]),
            "black": _accuracy(by_color["black"]),
        },
        "counts": {
            "white": dict(counts["white"]),
            "black": dict(counts["black"]),
        },
        "critical_moment": critical_moment,
        "biggest_error": biggest,
        "critical_cards": critical_cards,
        "opening": metadata.get("opening"),
        "worst_phase": worst_phase,
        "worst_phase_label": PHASE_LABELS_PT.get(worst_phase, worst_phase),
        "evaluation_curve": analysis.get("evaluation_curve", []),
        "natural_summary": summary,
        "coach_summary": {
            "headline": "Revise primeiro os lances críticos no tabuleiro.",
            "main_takeaway": summary,
            "top_cards": critical_cards,
        },
    }
