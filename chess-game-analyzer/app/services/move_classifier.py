from typing import Literal

MoveClass = Literal[
    "Best",
    "Excellent",
    "Good",
    "Inaccuracy",
    "Mistake",
    "Blunder",
    "Missed Win",
    "Forced",
    "Book move",
]


def game_phase(fullmove_number: int, piece_count: int) -> str:
    if fullmove_number <= 10:
        return "opening"
    if piece_count <= 12:
        return "endgame"
    return "middlegame"


def classify_move(
    cp_loss: int | None,
    before_cp: int | None,
    after_cp: int | None,
    phase: str,
    is_forced: bool = False,
    is_book: bool = False,
    mate_swing: bool = False,
) -> MoveClass:
    if is_book:
        return "Book move"
    if is_forced:
        return "Forced"
    if cp_loss is None:
        return "Blunder" if mate_swing else "Good"

    loss = max(0, cp_loss)
    already_lost = before_cp is not None and before_cp <= -700
    had_winning_edge = before_cp is not None and before_cp >= 300
    lost_win = had_winning_edge and after_cp is not None and after_cp < 80 and loss >= 220

    if lost_win:
        return "Missed Win"

    modifier = 0
    if phase == "opening":
        modifier = 20
    elif phase == "endgame":
        modifier = -15

    if loss <= 15:
        return "Best"
    if loss <= 45 + modifier:
        return "Excellent"
    if loss <= 90 + modifier:
        return "Good"
    if loss <= 180 + modifier:
        return "Inaccuracy"
    if loss <= 350 + modifier:
        return "Mistake"
    if already_lost:
        return "Mistake"
    return "Blunder"
