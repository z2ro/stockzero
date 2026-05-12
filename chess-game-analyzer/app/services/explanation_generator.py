import chess

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}

CRITICAL_CLASSES = {"Inaccuracy", "Mistake", "Blunder", "Missed Win"}


def material_balance(board: chess.Board, color: chess.Color) -> int:
    total = 0
    for piece_type, value in PIECE_VALUES.items():
        total += len(board.pieces(piece_type, color)) * value
        total -= len(board.pieces(piece_type, not color)) * value
    return total


def detect_themes(
    before: chess.Board,
    after: chess.Board,
    played_move: chess.Move,
    phase: str,
    material_delta: int,
    cp_loss: int | None,
) -> list[str]:
    themes: list[str] = []
    mover = not after.turn
    opponent = after.turn

    if material_delta <= -250:
        themes.append("peça pendurada")
    if after.is_check():
        themes.append("rei exposto")
    if before.is_capture(played_move) and material_delta < -100:
        themes.append("troca ruim")
    if phase == "opening" and cp_loss and cp_loss >= 120:
        themes.append("erro de abertura")
        minor_developed = sum(
            1
            for sq in chess.SQUARES
            if (piece := after.piece_at(sq))
            and piece.color == mover
            and piece.piece_type in {chess.KNIGHT, chess.BISHOP}
            and sq not in (chess.B1, chess.C1, chess.F1, chess.G1, chess.B8, chess.C8, chess.F8, chess.G8)
        )
        if minor_developed < 2:
            themes.append("desenvolvimento atrasado")
    if cp_loss and cp_loss >= 180 and not themes:
        themes.append("cálculo insuficiente")

    attackers_on_king_zone = 0
    king_sq = after.king(opponent)
    if king_sq is not None:
        for sq in chess.SquareSet(chess.BB_KING_ATTACKS[king_sq]):
            attackers_on_king_zone += len(after.attackers(mover, sq))
    if attackers_on_king_zone >= 3:
        themes.append("ataque duplo")

    if phase == "endgame" and len(after.pieces(chess.PAWN, chess.WHITE)) + len(after.pieces(chess.PAWN, chess.BLACK)) >= 4:
        themes.append("final de peões")

    return list(dict.fromkeys(themes or ["cálculo insuficiente"]))


def generate_explanation(move_analysis: dict) -> dict | None:
    classification = move_analysis["classification"]
    if classification not in CRITICAL_CLASSES:
        return None

    played = move_analysis["played_san"]
    best = move_analysis.get("best_move_san") or "não disponível"
    cp_loss = move_analysis.get("cp_loss")
    themes = move_analysis.get("themes") or ["cálculo insuficiente"]
    pv = move_analysis.get("pv") or []

    loss_text = f"perde cerca de {cp_loss} centipawns" if cp_loss is not None else "altera uma sequência de mate"
    reason = (
        f"{played} {loss_text} em relação a {best}. "
        "A conclusão vem da avaliação do Stockfish, da melhor linha sugerida e dos sinais objetivos "
        "detectados no tabuleiro."
    )
    if move_analysis.get("material_delta", 0) < 0:
        reason += " Após o lance, o balanço material do jogador piorou."
    if "rei exposto" in themes:
        reason += " O lance também deixa o rei sujeito a ameaças diretas."

    return {
        "played": played,
        "best_move": best,
        "why_it_worsens": reason,
        "missed_idea": f"Tema principal: {themes[0]}." + (f" Linha crítica: {' '.join(pv[:6])}." if pv else ""),
        "themes": themes,
    }
