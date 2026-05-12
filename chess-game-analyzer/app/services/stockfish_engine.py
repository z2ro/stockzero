from dataclasses import dataclass

import chess
import chess.engine

from app.config import get_settings

MATE_CP = 100_000


@dataclass(frozen=True)
class EngineLine:
    move: str | None
    san: str | None
    score_cp: int | None
    mate: int | None
    pv: list[str]


@dataclass(frozen=True)
class PositionAnalysis:
    fen: str
    best_move: str | None
    best_move_san: str | None
    evaluation_cp: int | None
    mate: int | None
    pv: list[str]
    multipv: list[EngineLine]


class StockfishEngine:
    def __init__(self, path: str | None = None):
        settings = get_settings()
        self.path = path or settings.stockfish_path

    def _limit(self, depth: int | None = None, time_ms: int | None = None) -> chess.engine.Limit:
        settings = get_settings()
        if time_ms is None:
            time_ms = settings.stockfish_move_time_ms
        if time_ms:
            return chess.engine.Limit(time=time_ms / 1000)
        return chess.engine.Limit(depth=depth or settings.stockfish_depth)

    def _score(self, info: dict, turn: chess.Color) -> tuple[int | None, int | None]:
        score = info.get("score")
        if score is None:
            return None, None
        pov = score.pov(turn)
        mate = pov.mate()
        if mate is not None:
            return (MATE_CP if mate > 0 else -MATE_CP), mate
        return pov.score(mate_score=MATE_CP), None

    def _pv_san(self, board: chess.Board, pv: list[chess.Move]) -> list[str]:
        temp = board.copy(stack=False)
        san_moves: list[str] = []
        for move in pv:
            if move not in temp.legal_moves:
                break
            san_moves.append(temp.san(move))
            temp.push(move)
        return san_moves

    def analyze_position(
        self,
        board: chess.Board,
        depth: int | None = None,
        multipv: int | None = None,
        time_ms: int | None = None,
    ) -> PositionAnalysis:
        settings = get_settings()
        requested_multipv = multipv or settings.stockfish_multipv
        with chess.engine.SimpleEngine.popen_uci(self.path) as engine:
            infos = engine.analyse(
                board,
                self._limit(depth=depth, time_ms=time_ms),
                multipv=requested_multipv,
            )
        if isinstance(infos, dict):
            infos = [infos]

        lines: list[EngineLine] = []
        for info in infos:
            pv = info.get("pv", [])
            move = pv[0] if pv else None
            score_cp, mate = self._score(info, board.turn)
            lines.append(
                EngineLine(
                    move=move.uci() if move else None,
                    san=board.san(move) if move and move in board.legal_moves else None,
                    score_cp=score_cp,
                    mate=mate,
                    pv=self._pv_san(board, pv),
                )
            )
        first = lines[0] if lines else EngineLine(None, None, None, None, [])
        return PositionAnalysis(
            fen=board.fen(),
            best_move=first.move,
            best_move_san=first.san,
            evaluation_cp=first.score_cp,
            mate=first.mate,
            pv=first.pv,
            multipv=lines,
        )
