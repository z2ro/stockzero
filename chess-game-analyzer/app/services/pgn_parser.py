from dataclasses import dataclass
from io import StringIO

import chess.pgn


@dataclass(frozen=True)
class ParsedGame:
    game: chess.pgn.Game
    headers: dict[str, str]
    moves_san: list[str]
    metadata: dict


class PgnValidationError(ValueError):
    pass


def _int_or_none(value: str | None) -> int | None:
    if not value or value == "?":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def parse_pgn(pgn_text: str) -> ParsedGame:
    handle = StringIO(pgn_text.strip())
    game = chess.pgn.read_game(handle)
    if game is None:
        raise PgnValidationError("PGN inválido ou vazio.")
    if game.errors:
        raise PgnValidationError("PGN contém erros de sintaxe ou lances ilegais.")

    board = game.board()
    moves_san: list[str] = []
    for move in game.mainline_moves():
        moves_san.append(board.san(move))
        board.push(move)

    if not moves_san:
        raise PgnValidationError("PGN não contém lances.")

    headers = dict(game.headers)
    metadata = {
        "white": headers.get("White"),
        "black": headers.get("Black"),
        "white_rating": _int_or_none(headers.get("WhiteElo")),
        "black_rating": _int_or_none(headers.get("BlackElo")),
        "date": headers.get("UTCDate") or headers.get("Date"),
        "result": headers.get("Result"),
        "opening": headers.get("Opening") or headers.get("ECOUrl"),
        "time_control": headers.get("TimeControl"),
        "eco": headers.get("ECO"),
        "termination": headers.get("Termination"),
    }
    return ParsedGame(game=game, headers=headers, moves_san=moves_san, metadata=metadata)


def export_pgn(game: chess.pgn.Game) -> str:
    return str(game)
