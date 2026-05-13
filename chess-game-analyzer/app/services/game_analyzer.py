import chess
import chess.pgn

from app.services.explanation_generator import (
    build_semantic_context,
    detect_themes,
    generate_explanation,
    material_balance,
)
from app.services.move_classifier import classify_move, game_phase
from app.services.stockfish_engine import MATE_CP, StockfishEngine

BOOK_PLIES = 8


def _white_cp(cp_from_side_to_move: int | None, turn: chess.Color) -> int | None:
    if cp_from_side_to_move is None:
        return None
    return cp_from_side_to_move if turn == chess.WHITE else -cp_from_side_to_move


def _engine_lines(lines: list) -> list[dict]:
    return [
        {
            "move_uci": line.move,
            "move_san": line.san,
            "score_cp": line.score_cp,
            "mate": line.mate,
            "pv": line.pv,
        }
        for line in lines
    ]



def _fen_after_best_move(board: chess.Board, best_uci: str | None) -> str | None:
    if not best_uci:
        return None
    try:
        move = chess.Move.from_uci(best_uci)
    except ValueError:
        return None
    if move not in board.legal_moves:
        return None
    copy = board.copy(stack=False)
    copy.push(move)
    return copy.fen()

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
        before_player_cp = before.evaluation_cp
        material_before = material_balance(board, mover)

        board.push(move)
        after = engine.analyze_position(board, depth=depth, multipv=multipv)
        after_player_cp = -after.evaluation_cp if after.evaluation_cp is not None else None
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
        themes = detect_themes(
            before_board,
            board,
            move,
            phase,
            material_after - material_before,
            cp_loss,
        )
        semantic_context = build_semantic_context(
            before_board,
            board,
            move,
            before.best_move,
            mover,
            phase,
            before_player_cp,
            cp_loss,
        )
        item = {
            "ply": ply,
            "move_number": (ply + 1) // 2,
            "color": "white" if mover == chess.WHITE else "black",
            "phase": phase,
            "fen_before": before_board.fen(),
            "fen_after": board.fen(),
            "fen_best": _fen_after_best_move(before_board, before.best_move),
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
            "best_lines": _engine_lines(before.multipv),
            "semantic_context": semantic_context,
            "themes": themes,
            "material_delta": material_after - material_before,
        }
        item["explanation"] = generate_explanation(item)
        move_analyses.append(item)
        eval_curve.append(
            {
                "ply": ply,
                "move": played_san,
                "white_cp": _white_cp(after.evaluation_cp, board.turn),
                "mate": after.mate,
            }
        )

    return {"moves": move_analyses, "evaluation_curve": eval_curve}
