from app.services.pgn_parser import parse_pgn

SAMPLE_PGN = """[Event "Test"]
[Site "Local"]
[Date "2024.01.01"]
[Round "-"]
[White "Alice"]
[Black "Bob"]
[Result "1-0"]
[WhiteElo "1500"]
[BlackElo "1450"]
[ECO "C20"]
[Opening "King's Pawn Game"]
[TimeControl "600"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0
"""


def test_parse_pgn_extracts_metadata_and_moves():
    parsed = parse_pgn(SAMPLE_PGN)

    assert parsed.metadata["white"] == "Alice"
    assert parsed.metadata["black_rating"] == 1450
    assert parsed.metadata["eco"] == "C20"
    assert parsed.moves_san[:3] == ["e4", "e5", "Nf3"]
