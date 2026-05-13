from collections import Counter, defaultdict

from app.services.coaching_utils import COLOR_LABELS_PT, critical_moves, phase_label

PHASE_ORDER = ["opening", "middlegame", "endgame"]


def analyze_game_phases(moves: list[dict]) -> dict:
    by_color: dict[str, Counter[str]] = {"white": Counter(), "black": Counter()}
    cp_by_color_phase: dict[str, dict[str, int]] = {
        "white": defaultdict(int),
        "black": defaultdict(int),
    }
    examples: dict[str, dict[str, list[str]]] = {
        "white": defaultdict(list),
        "black": defaultdict(list),
    }

    for move in critical_moves(moves):
        color = move.get("color") or "white"
        phase = move.get("phase") or "unknown"
        by_color[color][phase] += 1
        cp_by_color_phase[color][phase] += move.get("cp_loss") or 0
        if len(examples[color][phase]) < 3:
            prefix = (
                f"{move.get('move_number')}."
                if color == "white"
                else f"{move.get('move_number')}..."
            )
            examples[color][phase].append(
                f"{prefix} {move.get('played_san')} em vez de {move.get('best_move_san') or 'melhor lance'}"
            )

    result: dict[str, dict] = {}
    for color in ("white", "black"):
        phase_counts = dict(by_color[color])
        worst_phase = None
        if phase_counts:
            worst_phase = max(
                phase_counts,
                key=lambda phase: (phase_counts[phase], cp_by_color_phase[color].get(phase, 0)),
            )
        result[color] = {
            "player_color": COLOR_LABELS_PT[color],
            "critical_by_phase": {phase: phase_counts.get(phase, 0) for phase in PHASE_ORDER},
            "cp_loss_by_phase": {
                phase: cp_by_color_phase[color].get(phase, 0) for phase in PHASE_ORDER
            },
            "worst_phase": worst_phase,
            "worst_phase_label": phase_label(worst_phase),
            "evidence": {phase: examples[color].get(phase, []) for phase in PHASE_ORDER},
        }

    totals = Counter()
    for color_data in result.values():
        totals.update(color_data["critical_by_phase"])
    result["overall"] = {
        "critical_by_phase": {phase: totals.get(phase, 0) for phase in PHASE_ORDER},
        "main_phase": max(totals, key=totals.get) if totals else None,
        "main_phase_label": phase_label(max(totals, key=totals.get)) if totals else None,
    }
    return result
