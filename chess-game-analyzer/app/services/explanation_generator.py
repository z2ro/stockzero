import chess

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}
PIECE_NAMES = {
    chess.PAWN: "peão",
    chess.KNIGHT: "cavalo",
    chess.BISHOP: "bispo",
    chess.ROOK: "torre",
    chess.QUEEN: "dama",
    chess.KING: "rei",
}
CENTER = [chess.D4, chess.E4, chess.D5, chess.E5]
CRITICAL_CLASSES = {"Inaccuracy", "Mistake", "Blunder", "Missed Win"}


def material_balance(board: chess.Board, color: chess.Color) -> int:
    total = 0
    for piece_type, value in PIECE_VALUES.items():
        total += len(board.pieces(piece_type, color)) * value
        total -= len(board.pieces(piece_type, not color)) * value
    return total


def _piece_label(piece: chess.Piece | None, square: chess.Square) -> str:
    if piece is None:
        return chess.square_name(square)
    return f"{PIECE_NAMES[piece.piece_type]} em {chess.square_name(square)}"


def _undeveloped_minors(board: chess.Board, color: chess.Color) -> list[str]:
    home = {
        chess.WHITE: {chess.B1, chess.C1, chess.F1, chess.G1},
        chess.BLACK: {chess.B8, chess.C8, chess.F8, chess.G8},
    }[color]
    return [
        _piece_label(board.piece_at(square), square)
        for square in home
        if (piece := board.piece_at(square))
        and piece.color == color
        and piece.piece_type in {chess.KNIGHT, chess.BISHOP}
    ]


def _king_status(board: chess.Board, color: chess.Color) -> dict:
    king_square = board.king(color)
    if king_square is None:
        return {"central": False, "attackers": 0, "description": "rei não localizado"}
    central_files = {chess.FILE_NAMES.index("d"), chess.FILE_NAMES.index("e")}
    central = chess.square_file(king_square) in central_files
    enemy = not color
    zone = chess.SquareSet(chess.BB_KING_ATTACKS[king_square]) | chess.SquareSet([king_square])
    attackers = sum(len(board.attackers(enemy, square)) for square in zone)
    description = f"rei em {chess.square_name(king_square)}"
    if central:
        description += ", ainda em coluna central"
    if attackers:
        description += f", com {attackers} ataque(s) na zona do rei"
    return {"central": central, "attackers": attackers, "description": description}


def _hanging_or_attacked(board: chess.Board, color: chess.Color) -> list[str]:
    enemy = not color
    vulnerable: list[tuple[int, str]] = []
    for square, piece in board.piece_map().items():
        if piece.color != color or piece.piece_type == chess.KING:
            continue
        attackers = board.attackers(enemy, square)
        if not attackers:
            continue
        defenders = board.attackers(color, square)
        value = PIECE_VALUES[piece.piece_type]
        if not defenders or any(PIECE_VALUES[board.piece_at(att).piece_type] < value for att in attackers):
            vulnerable.append((value, _piece_label(piece, square)))
    vulnerable.sort(reverse=True)
    return [label for _, label in vulnerable[:3]]


def _center_control(board: chess.Board, color: chess.Color) -> int:
    return sum(len(board.attackers(color, square)) for square in CENTER)


def _legal_mobility(board: chess.Board, color: chess.Color) -> int:
    copy = board.copy(stack=False)
    copy.turn = color
    return copy.legal_moves.count()


def _development_count(board: chess.Board, color: chess.Color) -> int:
    home = {
        chess.WHITE: {chess.B1, chess.C1, chess.F1, chess.G1},
        chess.BLACK: {chess.B8, chess.C8, chess.F8, chess.G8},
    }[color]
    developed = 0
    for square, piece in board.piece_map().items():
        if piece.color == color and piece.piece_type in {chess.KNIGHT, chess.BISHOP} and square not in home:
            developed += 1
    return developed


def _move_effect_points(
    before: chess.Board,
    after: chess.Board | None,
    move: chess.Move | None,
    mover: chess.Color,
    phase: str,
) -> list[str]:
    if after is None or move is None:
        return []
    points: list[str] = []
    piece = before.piece_at(move.from_square)
    if piece is None:
        return points

    if piece.piece_type == chess.KING:
        if chess.square_file(move.from_square) in {3, 4} and chess.square_file(move.to_square) not in {3, 4}:
            points.append("melhora a segurança do rei saindo da coluna central")
        else:
            points.append("reorganiza a segurança do rei")
    if piece.piece_type in {chess.KNIGHT, chess.BISHOP} and phase == "opening":
        home = {
            chess.WHITE: {chess.B1, chess.C1, chess.F1, chess.G1},
            chess.BLACK: {chess.B8, chess.C8, chess.F8, chess.G8},
        }[mover]
        if move.from_square in home and move.to_square not in home:
            points.append("desenvolve uma peça menor e aproxima as torres da conexão")
    if before.is_capture(move):
        captured = before.piece_at(move.to_square)
        if captured:
            points.append(f"remove a peça adversária em {chess.square_name(move.to_square)}")
    if move.to_square in CENTER:
        points.append("aumenta presença no centro")
    if after.is_check():
        points.append("cria uma ameaça direta de xeque")
    if _development_count(after, mover) > _development_count(before, mover):
        points.append("melhora desenvolvimento")
    if _center_control(after, mover) > _center_control(before, mover):
        points.append("briga melhor pelo centro")
    return list(dict.fromkeys(points))[:3]


def _candidate_threats(board: chess.Board, attacker: chess.Color, victim: chess.Color) -> list[str]:
    copy = board.copy(stack=False)
    copy.turn = attacker
    threats: list[tuple[int, str]] = []
    for move in copy.legal_moves:
        if copy.gives_check(move):
            threats.append((10_000, f"xeque com {copy.san(move)}"))
            continue
        if not copy.is_capture(move):
            continue
        captured = copy.piece_at(move.to_square)
        if captured and captured.color == victim:
            threats.append((PIECE_VALUES[captured.piece_type], f"capturar {_piece_label(captured, move.to_square)} com {copy.san(move)}"))
    threats.sort(reverse=True)
    return [text for _, text in threats[:3]]


def _side_name(color: chess.Color) -> str:
    return "Brancas" if color == chess.WHITE else "Pretas"


def _evaluation_text(cp: int | None, mover: chess.Color) -> str:
    if cp is None:
        return "posição tática com avaliação de mate possível"
    better_side = mover if cp >= 0 else not mover
    abs_cp = abs(cp)
    if abs_cp < 80:
        return "posição aproximadamente equilibrada"
    if abs_cp < 250:
        return f"{_side_name(better_side)} ligeiramente melhores"
    if abs_cp < 600:
        return f"{_side_name(better_side)} claramente melhores"
    return f"{_side_name(better_side)} dominando a posição"


def _best_board(before: chess.Board, best_uci: str | None) -> chess.Board | None:
    if not best_uci:
        return None
    try:
        move = chess.Move.from_uci(best_uci)
    except ValueError:
        return None
    if move not in before.legal_moves:
        return None
    board = before.copy(stack=False)
    board.push(move)
    return board


def _priority(before: chess.Board, after: chess.Board, mover: chess.Color, phase: str) -> list[str]:
    priorities: list[str] = []
    king = _king_status(before, mover)
    undeveloped = _undeveloped_minors(before, mover)
    vulnerable = _hanging_or_attacked(before, mover)
    if king["central"] or king["attackers"] >= 2:
        priorities.append("segurança do rei")
    if phase == "opening" and undeveloped:
        priorities.append("desenvolvimento")
    if vulnerable:
        priorities.append("proteger peças vulneráveis")
    if _center_control(before, mover) < _center_control(before, not mover):
        priorities.append("controle central")
    if not priorities:
        priorities.append("melhorar atividade e coordenação das peças")
    return priorities[:3]


def build_semantic_context(
    before: chess.Board,
    after_played: chess.Board,
    played_move: chess.Move,
    best_uci: str | None,
    mover: chess.Color,
    phase: str,
    eval_before_cp: int | None,
    cp_loss: int | None,
) -> dict:
    best_move = None
    if best_uci:
        try:
            candidate = chess.Move.from_uci(best_uci)
        except ValueError:
            candidate = None
        if candidate is not None and candidate in before.legal_moves:
            best_move = candidate
    best_after = _best_board(before, best_uci)
    priorities = _priority(before, after_played, mover, phase)
    vulnerable_before = _hanging_or_attacked(before, mover)
    vulnerable_played = _hanging_or_attacked(after_played, mover)
    vulnerable_best = _hanging_or_attacked(best_after, mover) if best_after else []
    king_before = _king_status(before, mover)
    king_played = _king_status(after_played, mover)
    king_best = _king_status(best_after, mover) if best_after else {}
    threats_after = _candidate_threats(after_played, after_played.turn, mover)
    center_played = _center_control(after_played, mover)
    center_best = _center_control(best_after, mover) if best_after else center_played
    mobility_played = _legal_mobility(after_played, mover)
    mobility_best = _legal_mobility(best_after, mover) if best_after else mobility_played

    played_piece = before.piece_at(played_move.from_square)
    played_description = f"{before.san(played_move)} move {_piece_label(played_piece, played_move.from_square)}"
    played_description += f" para {chess.square_name(played_move.to_square)}"

    played_points: list[str] = []
    best_points = _move_effect_points(before, best_after, best_move, mover, phase)
    played_effects = _move_effect_points(before, after_played, played_move, mover, phase)
    best_points = best_points or []
    if played_effects and not best_points:
        best_points.append("resolve a prioridade da posição com mais urgência")
    if played_effects:
        played_points.append("ganha algo secundário: " + ", ".join(played_effects[:2]))
    if king_played.get("central") and "segurança do rei" in priorities:
        played_points.append("não resolve a segurança do rei")
    if king_best and not king_best.get("central") and king_before.get("central"):
        best_points.append("tira o rei da zona central")
    if vulnerable_played:
        played_points.append(f"mantém vulnerável: {', '.join(vulnerable_played[:2])}")
    if vulnerable_before and len(vulnerable_best) < len(vulnerable_played):
        best_points.append("reduz peças vulneráveis")
    if center_played < center_best:
        played_points.append("cede controle central")
        best_points.append("melhora controle central")
    if mobility_played < mobility_best:
        played_points.append("deixa as peças com menos mobilidade")
        best_points.append("aumenta atividade das peças")
    if phase == "opening" and _undeveloped_minors(after_played, mover):
        played_points.append("atrasa desenvolvimento")
    if phase == "opening" and best_after and len(_undeveloped_minors(best_after, mover)) < len(_undeveloped_minors(after_played, mover)):
        best_points.append("desenvolve ou prepara desenvolvimento")
    if not played_points:
        played_points.append("não enfrenta a prioridade principal da posição")
    if not best_points:
        best_points.append("mantém mais recursos defensivos e coordenação")

    comparison_rows = []
    max_rows = max(len(played_points), len(best_points), 1)
    for index in range(min(max_rows, 4)):
        comparison_rows.append(
            {
                "played": played_points[min(index, len(played_points) - 1)],
                "best": best_points[min(index, len(best_points) - 1)],
            }
        )

    consequences = []
    if threats_after:
        consequences.append(f"O adversário pode {threats_after[0]}.")
    if king_played.get("attackers", 0) > king_before.get("attackers", 0):
        consequences.append("A zona do rei passa a receber mais pressão.")
    if vulnerable_played and len(vulnerable_played) >= len(vulnerable_before):
        consequences.append(f"A peça vulnerável continua sendo {vulnerable_played[0]}.")
    if not consequences:
        consequences.append("O adversário ganha tempo para melhorar atividade e iniciativa.")

    return {
        "evaluation_human": _evaluation_text(eval_before_cp, mover),
        "situation_before": (
            f"Antes do lance, a avaliação indica {_evaluation_text(eval_before_cp, mover)}. "
            f"A prioridade era {', '.join(priorities)}. "
            f"No tabuleiro: {king_before['description']}. "
            f"Controle central: {_side_name(mover)} {_center_control(before, mover)} contra "
            f"{_side_name(not mover)} {_center_control(before, not mover)}."
            + (f" Peças vulneráveis: {', '.join(vulnerable_before)}." if vulnerable_before else "")
        ),
        "played_problem": (
            f"{played_description}. O problema prático é que o lance {played_points[0]}"
            + (f" e {played_points[1]}" if len(played_points) > 1 else "")
            + "."
        ),
        "best_move_value": (
            f"O melhor lance resolvia algo concreto: {best_points[0]}"
            + (f" e {best_points[1]}" if len(best_points) > 1 else "")
            + "."
        ),
        "comparison": comparison_rows,
        "opponent_plan": " ".join(consequences),
        "position_priorities": priorities,
        "practical_consequences": consequences,
    }


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
            and sq
            not in (chess.B1, chess.C1, chess.F1, chess.G1, chess.B8, chess.C8, chess.F8, chess.G8)
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
    semantic = move_analysis.get("semantic_context") or {}

    loss_text = f"perde cerca de {cp_loss} centipawns" if cp_loss is not None else "altera uma sequência de mate"
    reason = semantic.get("played_problem") or (
        f"{played} {loss_text} em relação a {best}. "
        "A conclusão vem da avaliação do Stockfish, da melhor linha sugerida e dos sinais objetivos "
        "detectados no tabuleiro."
    )
    if move_analysis.get("material_delta", 0) < 0 and "material" not in reason:
        reason += " Após o lance, o balanço material do jogador piorou."
    if "rei exposto" in themes and "rei" not in reason:
        reason += " O lance também deixa o rei sujeito a ameaças diretas."

    human_summary = " ".join(
        part
        for part in [
            semantic.get("situation_before"),
            semantic.get("played_problem"),
            semantic.get("best_move_value"),
            semantic.get("opponent_plan"),
            (
                "Nesta posição, "
                + ", ".join(semantic.get("position_priorities", []))
                + " era mais importante do que jogar sem resolver esses pontos."
                if semantic.get("position_priorities")
                else None
            ),
        ]
        if part
    )

    return {
        "played": played,
        "best_move": best,
        "situation_before": semantic.get("situation_before"),
        "why_it_worsens": reason,
        "best_move_value": semantic.get("best_move_value"),
        "direct_comparison": semantic.get("comparison", []),
        "opponent_plan": semantic.get("opponent_plan"),
        "position_priorities": semantic.get("position_priorities", []),
        "practical_consequences": semantic.get("practical_consequences", []),
        "evaluation_human": semantic.get("evaluation_human"),
        "human_summary": human_summary,
        "missed_idea": f"Tema principal: {themes[0]}." + (f" Linha crítica: {' '.join(pv[:6])}." if pv else ""),
        "themes": themes,
    }
