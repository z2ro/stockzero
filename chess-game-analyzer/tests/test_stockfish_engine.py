import chess

from app.services.stockfish_engine import PositionAnalysis, StockfishEngine


def test_position_analysis_shape_with_mock(monkeypatch):
    expected = PositionAnalysis(
        fen=chess.STARTING_FEN,
        best_move="e2e4",
        best_move_san="e4",
        evaluation_cp=30,
        mate=None,
        pv=["e4", "e5"],
        multipv=[],
    )

    monkeypatch.setattr(StockfishEngine, "analyze_position", lambda self, board, **kwargs: expected)
    result = StockfishEngine(path="unused").analyze_position(chess.Board())

    assert result.best_move_san == "e4"
    assert result.evaluation_cp == 30
