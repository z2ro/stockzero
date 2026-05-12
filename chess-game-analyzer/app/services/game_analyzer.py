import chess
import chess.pgn

from app.services.explanation_generator import (
    detect_themes,
    generate_explanation,
    material_balance,
)
from app.services.move_classifier import classify_move, game_phase
from app.services.stockfish_engine import MATE_CP, StockfishEngine

BOOK_PLIES = 8


def _perspective_cp(cp: int | None, color: chess.Color) -> int | None:
    if cp is None:
        return None
    return cp if color == chess.WHITE else -cp


def _piece_count(board: chess.Board) -> int:
    return sum(1 for square in chess.SQUARES if board.piece_at(square))


def analyze_game(
    game: chess.pgn.Game,
    depth: int | None = None,
    multipv: int | None = None,
    max_moves: int | None = None,
    engine: StockfishEngine | None = None,
) -> dict:
    engine = engine or StockfishEngine()
    board = game.board()
    moves = list(game.mainline_moves())
    if max_moves is not None:
        moves = moves[:max_moves]

    move_analyses: list[dict] = []
    eval_curve: list[dict] = []

    for ply, move in enumerate(moves, start=1):
        mover = board.turn
        phase = game_phase(board.fullmove_number, _piece_count(board))
        legal_count = board.legal_moves.count()
        before_board = board.copy(stack=False)
        played_san = board.san(move)
        before = engine.analyze_position(board, depth=depth, multipv=multipv)
        before_player_cp = _perspective_cp(before.evaluation_cp, mover)
        material_before = material_balance(board, mover)

        board.push(move)
        after = engine.analyze_position(board, depth=depth, multipv=multipv)
        after_player_cp = _perspective_cp(after.evaluation_cp, mover)
        material_after = material_balance(board, mover)
        cp_loss = None
        mate_swing = False
        if before_player_cp is not None and after_player_cp is not None:
            cp_loss = max(0, before_player_cp - after_player_cp)
            mate_swing = abs(before_player_cp) >= MATE_CP or abs(after_player_cp) >= MATE_CP

        classification = classify_move(
            cp_loss=cp_loss,
            before_cp=before_player_cp,
            after_cp=after_player_cp,
            phase=phase,
            is_forced=legal_count == 1,
            is_book=ply <= BOOK_PLIES and cp_loss is not None and cp_loss <= 35,
            mate_swing=mate_swing,
        )
        themes = detect_themes(before_board, board, move, phase, material_after - material_before, cp_loss)
        item = {
            "ply": ply,
            "move_number": (ply + 1) // 2,
            "color": "white" if mover == chess.WHITE else "black",
            "phase": phase,
            "fen_before": before_board.fen(),
            "played_uci": move.uci(),
            "played_san": played_san,
            "best_move_uci": before.best_move,
            "best_move_san": before.best_move_san,
            "eval_before_cp": before_player_cp,
            "eval_after_cp": after_player_cp,
            "mate_before": before.mate,
            "mate_after": after.mate,
            "cp_loss": cp_loss,
            "classification": classification,
            "pv": before.pv,
            "themes": themes,
            "material_delta": material_after - material_before,
        }
        item["explanation"] = generate_explanation(item)
        move_analyses.append(item)
        eval_curve.append(
            {
                "ply": ply,
                "move": played_san,
                "white_cp": after.evaluation_cp,
                "mate": after.mate,
            }
        )

    return {"moves": move_analyses, "evaluation_curve": eval_curve}
