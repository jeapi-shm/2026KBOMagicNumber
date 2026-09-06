import re

from bs4 import BeautifulSoup


SCHEDULE_URL = "https://www.koreabaseball.com/Schedule/Schedule.aspx"


def parse_games(payload, today):
    games = []
    current_day = None
    for entry in payload["rows"]:
        cells = entry["row"]
        day_cell = next((c for c in cells if c.get("Class") == "day"), None)
        if day_cell:
            match = re.match(r"(\d{2})\.(\d{2})", day_cell["Text"])
            if not match:
                raise ValueError("KBO 경기 날짜를 해석하지 못했습니다.")
            current_day = tuple(map(int, match.groups()))
        if current_day != (today.month, today.day):
            continue
        play = next((c for c in cells if c.get("Class") == "play"), None)
        if play is None:
            if any("경기가 없습니다" in c["Text"] for c in cells):
                continue
            raise ValueError("KBO 경기 대진을 찾지 못했습니다.")
        names = BeautifulSoup(play["Text"], "html.parser").find_all("span", recursive=False)
        if len(names) != 2 or len(cells) < 8:
            raise ValueError("KBO 경기 대진 형식이 변경되었습니다.")
        time = next(c for c in cells if c.get("Class") == "time")
        clean = lambda value: BeautifulSoup(value, "html.parser").get_text(" ", strip=True)
        games.append({
            "time": clean(time["Text"]),
            "away": names[0].get_text(strip=True),
            "home": names[1].get_text(strip=True),
            "place": clean(cells[-2]["Text"]),
            "status": clean(cells[-1]["Text"]).replace("-", ""),
        })
    return games


def fetch_games(session, today):
    response = session.get(SCHEDULE_URL, timeout=30)
    response.raise_for_status()
    response = session.post(
        "https://www.koreabaseball.com/ws/Schedule.asmx/GetScheduleList",
        headers={"Referer": SCHEDULE_URL, "X-Requested-With": "XMLHttpRequest"},
        data={"leId": "1", "srIdList": "0,9,6", "seasonId": str(today.year),
              "gameMonth": f"{today.month:02d}", "teamId": ""},
        timeout=30,
    )
    response.raise_for_status()
    return parse_games(response.json(), today)
