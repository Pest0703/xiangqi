from xiangqi_tutor.board import START_FEN
from xiangqi_tutor.services import RepetitionAdjudicator


def test_repetition_ignores_clock_fields_but_not_side_to_move() -> None:
    detector = RepetitionAdjudicator()
    same = START_FEN.rsplit(" ", 2)[0]
    assert detector.repeated((START_FEN, same + " 4 3", same + " 8 5"))
    black = START_FEN.replace(" w ", " b ")
    assert not detector.repeated((START_FEN, START_FEN, black))
