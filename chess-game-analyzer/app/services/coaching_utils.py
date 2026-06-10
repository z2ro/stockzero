CRITICAL_CLASSES = {"Inaccuracy", "Mistake", "Blunder", "Missed Win"}
INSUFFICIENT_EVIDENCE = "Não há evidência suficiente nesta partida para concluir isso."
PHASE_LABELS_PT = {
    "opening": "abertura",
    "middlegame": "meio-jogo",
    "endgame": "final",
}
COLOR_LABELS_PT = {
    "white": "brancas",
    "black": "pretas",
}


def is_critical(move: dict) -> bool:
    return move.get("classification") in CRITICAL_CLASSES


def move_ref(move: dict) -> str:
    prefix = f"{move.get('move_number')}."
    if move.get("color") == "black":
        prefix = f"{move.get('move_number')}..."
    return f"{prefix} {move.get('played_san') or '?'}"


def best_ref(move: dict) -> str:
    best = move.get("best_move_san") or (move.get("explanation") or {}).get("best_move")
    return best or "melhor lance não disponível"


def critical_moves(moves: list[dict], color: str | None = None) -> list[dict]:
    selected = [
        move
        for move in moves
        if is_critical(move) and (color is None or move.get("color") == color)
    ]
    return sorted(selected, key=lambda move: move.get("cp_loss") or 0, reverse=True)


def phase_label(phase: str | None) -> str:
    return PHASE_LABELS_PT.get(phase or "", phase or "fase não identificada")
