from collections import Counter, defaultdict

CRITICAL = {"Inaccuracy", "Mistake", "Blunder", "Missed Win"}


def _accuracy(losses: list[int]) -> float:
    if not losses:
        return 100.0
    avg = sum(min(loss, 1000) for loss in losses) / len(losses)
    return round(max(0.0, 100.0 - avg / 10.0), 1)


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

    white_name = metadata.get("white") or "Brancas"
    black_name = metadata.get("black") or "Pretas"
    summary = (
        f"{white_name} vs {black_name}. A abertura registrada foi "
        f"{metadata.get('opening') or 'desconhecida'}. "
        f"O maior erro ocorreu no lance {biggest['move_number']} com {biggest['played_san']} "
        f"({biggest['classification']}) e perda estimada de {biggest.get('cp_loss')} cp."
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
        "opening": metadata.get("opening"),
        "worst_phase": worst_phase,
        "evaluation_curve": analysis.get("evaluation_curve", []),
        "natural_summary": summary,
    }
