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
CENTER_SQUARES = [chess.D4, chess.E4, chess.D5, chess.E5]
HOME_MINOR_SQUARES = {
    chess.WHITE: {chess.B1, chess.C1, chess.F1, chess.G1},
    chess.BLACK: {chess.B8, chess.C8, chess.F8, chess.G8},
}
HOME_KING_SQUARE = {chess.WHITE: chess.E1, chess.BLACK: chess.E8}

PIECE_NAMES_PT = {
    chess.PAWN: "peão",
    chess.KNIGHT: "cavalo",
    chess.BISHOP: "bispo",
    chess.ROOK: "torre",
    chess.QUEEN: "dama",
    chess.KING: "rei",
}


def material_balance(board: chess.Board, color: chess.Color) -> int:
    total = 0
    for piece_type, value in PIECE_VALUES.items():
        total += len(board.pieces(piece_type, color)) * value
        total -= len(board.pieces(piece_type, not color)) * value
    return total


def _color_name(color: chess.Color) -> str:
    return "brancas" if color == chess.WHITE else "pretas"


def _piece_label(piece: chess.Piece, square: chess.Square) -> str:
    return f"{PIECE_NAMES_PT[piece.piece_type]} em {chess.square_name(square)}"


def _move_goal(board: chess.Board, move: chess.Move) -> str:
    piece = board.piece_at(move.from_square)
    if not piece:
        return "lance sem peça identificada"
    if board.is_capture(move):
        captured = board.piece_at(move.to_square)
        if captured:
            return f"captura o {PIECE_NAMES_PT[captured.piece_type]} em {chess.square_name(move.to_square)}"
        return f"captura em {chess.square_name(move.to_square)}"
    if piece.piece_type == chess.KING:
        return (
            "melhora a segurança do rei"
            if move.from_square in HOME_KING_SQUARE.values()
            else "reposiciona o rei"
        )
    if (
        piece.piece_type in {chess.KNIGHT, chess.BISHOP}
        and move.from_square in HOME_MINOR_SQUARES[piece.color]
    ):
        return "desenvolve uma peça menor"
    if piece.piece_type == chess.ROOK:
        return "ativa a torre"
    if piece.piece_type == chess.PAWN:
        file_name = chess.square_file(move.from_square)
        if file_name in {0, 7}:
            return "move um peão lateral"
        if move.to_square in CENTER_SQUARES or move.from_square in CENTER_SQUARES:
            return "disputa o centro"
        return "move um peão"
    return f"reposiciona a {PIECE_NAMES_PT[piece.piece_type]}"


def _undeveloped_minors(board: chess.Board, color: chess.Color) -> list[str]:
    pieces = []
    for square in sorted(HOME_MINOR_SQUARES[color]):
        piece = board.piece_at(square)
        if piece and piece.color == color and piece.piece_type in {chess.KNIGHT, chess.BISHOP}:
            pieces.append(_piece_label(piece, square))
    return pieces


def _hanging_pieces(board: chess.Board, color: chess.Color) -> list[str]:
    hanging = []
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if not piece or piece.color != color or piece.piece_type == chess.KING:
            continue
        attacked = bool(board.attackers(not color, square))
        defended = bool(board.attackers(color, square))
        if attacked and not defended:
            hanging.append(_piece_label(piece, square))
    return hanging


def _king_zone_pressure(board: chess.Board, color: chess.Color) -> int:
    king_sq = board.king(color)
    if king_sq is None:
        return 0
    zone = chess.SquareSet(chess.BB_KING_ATTACKS[king_sq]) | chess.SquareSet([king_sq])
    return sum(len(board.attackers(not color, sq)) for sq in zone)


def _center_control(board: chess.Board, color: chess.Color) -> int:
    return sum(len(board.attackers(color, square)) for square in CENTER_SQUARES)


def _open_file_pressure(board: chess.Board, color: chess.Color) -> bool:
    king_sq = board.king(color)
    if king_sq is None:
        return False
    king_file = chess.square_file(king_sq)
    for file_index in {king_file - 1, king_file, king_file + 1}:
        if file_index < 0 or file_index > 7:
            continue
        has_pawn = any(
            (piece := board.piece_at(chess.square(file_index, rank)))
            and piece.piece_type == chess.PAWN
            for rank in range(8)
        )
        if not has_pawn:
            return True
    return False


def _snapshot(board: chess.Board, color: chess.Color) -> dict:
    undeveloped = _undeveloped_minors(board, color)
    hanging = _hanging_pieces(board, color)
    opponent_hanging = _hanging_pieces(board, not color)
    king_sq = board.king(color)
    king_home_or_center = king_sq in {
        chess.E1,
        chess.D1,
        chess.E2,
        chess.D2,
        chess.E8,
        chess.D8,
        chess.E7,
        chess.D7,
    }
    return {
        "material": material_balance(board, color),
        "undeveloped": undeveloped,
        "hanging": hanging,
        "opponent_hanging": opponent_hanging,
        "king_pressure": _king_zone_pressure(board, color),
        "opponent_king_pressure": _king_zone_pressure(board, not color),
        "center_control": _center_control(board, color),
        "opponent_center_control": _center_control(board, not color),
        "legal_moves": board.legal_moves.count(),
        "king_square": chess.square_name(king_sq) if king_sq is not None else "?",
        "king_home_or_center": king_home_or_center,
        "open_file_near_king": _open_file_pressure(board, color),
        "in_check": board.is_check() and board.turn == color,
    }


def _position_priorities(snapshot: dict, phase: str) -> list[str]:
    priorities: list[str] = []
    if (
        snapshot["in_check"]
        or snapshot["king_pressure"] >= 3
        or snapshot["king_home_or_center"]
        or snapshot["open_file_near_king"]
    ):
        priorities.append("segurança do rei")
    if phase == "opening" and snapshot["undeveloped"]:
        priorities.append("desenvolvimento")
    if snapshot["center_control"] < snapshot["opponent_center_control"]:
        priorities.append("controle central")
    if snapshot["hanging"]:
        priorities.append("defender peças vulneráveis")
    if snapshot["opponent_hanging"]:
        priorities.append("aproveitar tática concreta")
    if not priorities:
        priorities.append("atividade e coordenação das peças")
    return priorities[:3]


def _human_eval(cp: int | None, mover: chess.Color) -> str:
    if cp is None:
        return "posição taticamente decisiva"
    side = _color_name(mover) if cp >= 0 else _color_name(not mover)
    value = abs(cp)
    if value < 80:
        return "posição equilibrada"
    if value < 220:
        return f"{side} um pouco melhores"
    if value < 500:
        return f"{side} claramente melhores"
    return f"{side} com vantagem decisiva ou forte pressão"


def _situation_text(before: dict, mover: chess.Color, phase: str, before_cp: int | None) -> str:
    parts = [f"Antes do lance, a avaliação humana é: {_human_eval(before_cp, mover)}."]
    if before["king_home_or_center"]:
        parts.append(
            f"O rei das {_color_name(mover)} ainda está em {before['king_square']}, então segurança do rei é um tema real."
        )
    if before["undeveloped"]:
        parts.append(
            "Peças ainda sem entrar no jogo: " + ", ".join(before["undeveloped"][:3]) + "."
        )
    if before["hanging"]:
        parts.append("Peça vulnerável a cuidar: " + ", ".join(before["hanging"][:2]) + ".")
    if before["center_control"] < before["opponent_center_control"]:
        parts.append("O adversário controla mais casas centrais, o que facilita ganhar iniciativa.")
    if phase == "opening" and len(parts) == 1:
        parts.append(
            "A prioridade normal da abertura é desenvolver, proteger o rei e disputar o centro."
        )
    return " ".join(parts)


def _played_problem_text(
    board: chess.Board, move: chess.Move, before: dict, after: dict, cp_loss: int | None
) -> str:
    goal = _move_goal(board, move)
    problems: list[str] = []
    if after["king_pressure"] > before["king_pressure"] or after["in_check"]:
        problems.append("a pressão sobre o rei aumenta")
    if after["hanging"] and len(after["hanging"]) > len(before["hanging"]):
        problems.append("fica peça sem defesa: " + ", ".join(after["hanging"][:2]))
    if after["undeveloped"] and len(after["undeveloped"]) >= len(before["undeveloped"]):
        problems.append("não reduz o atraso de desenvolvimento")
    if after["center_control"] < before["center_control"]:
        problems.append("cede controle central")
    if after["material"] < before["material"]:
        problems.append("piora o balanço material")
    if not problems:
        problems.append("não enfrenta a prioridade principal da posição")
    loss = (
        f" A perda estimada é de {cp_loss} cp, mas o ponto prático é"
        if cp_loss is not None
        else " O ponto prático é"
    )
    return f"{board.san(move)} {goal}, porém {', e '.join(problems)}.{loss} que o adversário recebe tempo para aumentar a iniciativa."


def _best_solution_text(
    board: chess.Board, best_move: chess.Move | None, before: dict, best: dict | None
) -> str:
    if best_move is None or best is None:
        return "A melhor linha do Stockfish não pôde ser reconstruída no tabuleiro, então compare a posição com a PV sugerida."
    san = board.san(best_move)
    goal = _move_goal(board, best_move)
    improvements: list[str] = []
    if best["king_pressure"] < before["king_pressure"] or (
        before["king_home_or_center"] and not best["king_home_or_center"]
    ):
        improvements.append("reduz temas contra o rei")
    if len(best["undeveloped"]) < len(before["undeveloped"]):
        improvements.append("coloca uma peça nova em jogo")
    if best["center_control"] > before["center_control"]:
        improvements.append("aumenta o controle central")
    if len(best["hanging"]) < len(before["hanging"]):
        improvements.append("resolve uma peça vulnerável")
    if best["material"] > before["material"]:
        improvements.append("preserva ou ganha material")
    if not improvements:
        improvements.append("melhora a coordenação e limita a iniciativa adversária")
    return f"{san} era mais forte porque {goal} e {', além de '.join(improvements)}. Concretamente, muda a posição antes que o adversário transforme pressão em ameaças forçadas."


def _comparison_rows(
    board: chess.Board,
    played_move: chess.Move,
    best_move: chess.Move | None,
    before: dict,
    played: dict,
    best: dict | None,
) -> list[dict]:
    rows = [
        {
            "played": _move_goal(board, played_move),
            "best": _move_goal(board, best_move) if best_move else "segue a melhor linha",
        },
    ]
    rows.append(
        {
            "played": "rei continua vulnerável"
            if played["king_pressure"] >= before["king_pressure"]
            and (played["king_pressure"] or played["king_home_or_center"])
            else "não melhora muito a segurança",
            "best": "melhora ou estabiliza a segurança"
            if best and best["king_pressure"] <= before["king_pressure"]
            else "limita contrajogo imediato",
        }
    )
    rows.append(
        {
            "played": "desenvolvimento segue atrasado"
            if played["undeveloped"]
            else "coordenação pouco alterada",
            "best": "desenvolve/coordena melhor"
            if best and len(best["undeveloped"]) <= len(before["undeveloped"])
            else "mantém peças mais ativas",
        }
    )
    rows.append(
        {
            "played": "permite iniciativa adversária",
            "best": "reduz a pressão e preserva recursos defensivos",
        }
    )
    return rows


def _opponent_plan_text(played: dict, mover: chess.Color, pv: list[str]) -> str:
    opponent = _color_name(not mover)
    consequences = []
    if played["king_pressure"]:
        consequences.append("criar ameaças contra o rei")
    if played["hanging"]:
        consequences.append("atacar " + ", ".join(played["hanging"][:2]))
    if played["center_control"] < played["opponent_center_control"]:
        consequences.append("jogar pelo centro com ganho de tempo")
    if not consequences:
        consequences.append("desenvolver com iniciativa")
    line = f" A linha crítica começa com {' '.join(pv[:4])}." if pv else ""
    return f"Depois do erro, as {opponent} podem {', e '.join(consequences)}.{line}"


def _concrete_consequences(before: dict, played: dict) -> list[str]:
    consequences = []
    if played["king_home_or_center"] or played["king_pressure"] > before["king_pressure"]:
        consequences.append("Rei continua vulnerável")
    if len(played["undeveloped"]) >= len(before["undeveloped"]) and played["undeveloped"]:
        consequences.append("Desenvolvimento continua atrasado")
    if played["center_control"] < played["opponent_center_control"]:
        consequences.append("Adversário ganha mais liberdade no centro")
    if played["hanging"]:
        consequences.append("Peça vulnerável: " + ", ".join(played["hanging"][:2]))
    if not consequences:
        consequences.append("Adversário mantém a iniciativa prática")
    return consequences


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
    before_snapshot = _snapshot(before, mover)
    after_snapshot = _snapshot(after, mover)

    if material_delta <= -250 or len(after_snapshot["hanging"]) > len(before_snapshot["hanging"]):
        themes.append("peça pendurada")
    if after.is_check() or after_snapshot["king_pressure"] >= before_snapshot["king_pressure"] + 2:
        themes.append("rei exposto")
    if before.is_capture(played_move) and material_delta < -100:
        themes.append("troca ruim")
    if phase == "opening" and cp_loss and cp_loss >= 120:
        themes.append("erro de abertura")
        if len(after_snapshot["undeveloped"]) >= 3:
            themes.append("desenvolvimento atrasado")
        piece = before.piece_at(played_move.from_square)
        if (
            piece
            and piece.piece_type == chess.PAWN
            and chess.square_file(played_move.from_square) in {0, 7}
        ):
            themes.append("perda de tempo")
    if after_snapshot["center_control"] < before_snapshot["center_control"]:
        themes.append("controle central")
    if cp_loss and cp_loss >= 180 and not themes:
        themes.append("cálculo insuficiente")

    attackers_on_king_zone = 0
    king_sq = after.king(opponent)
    if king_sq is not None:
        for sq in chess.SquareSet(chess.BB_KING_ATTACKS[king_sq]):
            attackers_on_king_zone += len(after.attackers(mover, sq))
    if attackers_on_king_zone >= 3:
        themes.append("ataque ao rei")

    if (
        phase == "endgame"
        and len(after.pieces(chess.PAWN, chess.WHITE)) + len(after.pieces(chess.PAWN, chess.BLACK))
        >= 4
    ):
        themes.append("final de peões")

    return list(dict.fromkeys(themes or ["cálculo insuficiente"]))


def generate_explanation(move_analysis: dict) -> dict | None:
    classification = move_analysis["classification"]
    if classification not in CRITICAL_CLASSES:
        return None

    played = move_analysis["played_san"]
    best_san = move_analysis.get("best_move_san") or "não disponível"
    cp_loss = move_analysis.get("cp_loss")
    themes = move_analysis.get("themes") or ["cálculo insuficiente"]
    pv = move_analysis.get("pv") or []
    mover = chess.WHITE if move_analysis.get("color") == "white" else chess.BLACK
    phase = move_analysis.get("phase") or "middlegame"

    before_board = chess.Board(move_analysis["fen_before"])
    played_move = chess.Move.from_uci(move_analysis["played_uci"])
    played_board = before_board.copy(stack=False)
    played_board.push(played_move)

    best_move = None
    best_board = None
    if move_analysis.get("best_move_uci"):
        candidate = chess.Move.from_uci(move_analysis["best_move_uci"])
        if candidate in before_board.legal_moves:
            best_move = candidate
            best_board = before_board.copy(stack=False)
            best_board.push(candidate)

    before_snapshot = _snapshot(before_board, mover)
    played_snapshot = _snapshot(played_board, mover)
    best_snapshot = _snapshot(best_board, mover) if best_board else None
    priorities = _position_priorities(before_snapshot, phase)
    comparison = _comparison_rows(
        before_board, played_move, best_move, before_snapshot, played_snapshot, best_snapshot
    )
    consequence = _concrete_consequences(before_snapshot, played_snapshot)

    situation = _situation_text(before_snapshot, mover, phase, move_analysis.get("eval_before_cp"))
    why = _played_problem_text(before_board, played_move, before_snapshot, played_snapshot, cp_loss)
    missed = _best_solution_text(before_board, best_move, before_snapshot, best_snapshot)
    opponent_plan = _opponent_plan_text(played_snapshot, mover, pv)
    priority_text = f"Nesta posição, {' e '.join(priorities[:2])} eram mais importantes do que executar um lance que não resolve essas urgências."

    return {
        "played": played,
        "best_move": best_san,
        "situation_before": situation,
        "why_it_worsens": why,
        "missed_idea": missed,
        "direct_comparison": comparison,
        "opponent_plan": opponent_plan,
        "position_priorities": priorities,
        "priority_explanation": priority_text,
        "concrete_consequences": consequence,
        "human_evaluation": _human_eval(move_analysis.get("eval_after_cp"), mover),
        "themes": themes,
        "fen_after_played": played_board.fen(),
        "fen_after_best": best_board.fen() if best_board else None,
    }
