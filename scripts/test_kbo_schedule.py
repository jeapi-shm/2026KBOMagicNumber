import unittest
from datetime import date

from kbo_schedule import parse_games


def row(day=None, status="-"):
    cells = [{"Class": "day", "Text": day}] if day else []
    cells += [
        {"Class": "time", "Text": "<b>17:00</b>"},
        {"Class": "play", "Text": '<span>삼성</span><em><span>3</span>vs<span>1</span></em><span>LG</span>'},
        *[{"Text": ""} for _ in range(4)],
        {"Text": "잠실"}, {"Text": status},
    ]
    return {"row": cells}


class ScheduleTests(unittest.TestCase):
    def test_date_rowspan_scores_and_cancellation(self):
        games = parse_games({"rows": [row("09.05(토)"), row("09.06(일)"),
                                       row(status="우천취소"), row("09.07(월)")]}, date(2026, 9, 6))
        self.assertEqual(len(games), 2)
        self.assertEqual(games[0], dict(time="17:00", away="삼성", home="LG", place="잠실", status=""))
        self.assertEqual(games[1]["status"], "우천취소")

    def test_off_day(self):
        self.assertEqual(parse_games({"rows": [row("09.06(일)")]}, date(2026, 9, 7)), [])

    def test_invalid_response_fails(self):
        with self.assertRaises(KeyError):
            parse_games({}, date(2026, 9, 6))


if __name__ == "__main__":
    unittest.main()
