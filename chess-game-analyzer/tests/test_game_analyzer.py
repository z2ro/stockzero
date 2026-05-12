from io import StringIO

import chess
import chess.pgn

from app.services.game_analyzer import analyze_game
from app.services.stockfish_engine import EngineLine, PositionAnalysis


def _line(move_uci: str, board: chess.Board, score_cp: int) -> EngineLine:
    move_san = board.san(chess.Move.from_uci(move_uci))
    return EngineLine(move_uci, move_san, score_cp, None, [move_san])


class FakeEngine:
    def analyze_position(self, board: chess.Board, **kwargs) -> PositionAnalysis:
        if board.turn == chess.WHITE:
            line = _line("e2e4", board, 50)
            return PositionAnalysis(
                fen=board.fen(),
                best_move=line.move,
                best_move_san=line.san,
                evaluation_cp=50,
                mate=None,
                pv=line.pv,
                multipv=[line],
            )

        line = _line("e7e5", board, -50)
        return PositionAnalysis(
            fen=board.fen(),
            best_move=line.move,
            best_move_san=line.san,
            evaluation_cp=-50,
            mate=None,
            pv=line.pv,
            multipv=[line],
        )


def test_cp_loss_uses_mover_perspective_after_move():
    game = chess.pgn.read_game(StringIO("1. e4 *"))

    analysis = analyze_game(game, max_moves=1, engine=FakeEngine())

    first_move = analysis["moves"][0]
    assert first_move["cp_loss"] == 0
    assert first_move["eval_before_cp"] == 50
    assert first_move["eval_after_cp"] == 50
    assert first_move["best_lines"][0]["move_uci"] == "e2e4"
    assert analysis["evaluation_curve"][0]["white_cp"] == 50
