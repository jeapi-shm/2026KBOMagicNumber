import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup


URL = "https://www.koreabaseball.com/Record/TeamRank/TeamRankDaily.aspx"
ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
COLORS = {
    "LG": "#c08a00", "한화": "#f37321", "SSG": "#9a8258",
    "KT": "#111111", "삼성": "#074ca1", "롯데": "#041e42",
    "NC": "#315288", "KIA": "#ea0029", "두산": "#131230",
    "키움": "#570514",
}


def text(cell):
    return " ".join(cell.get_text(" ", strip=True).split())


response = requests.get(URL, headers={"User-Agent": "Mozilla/5.0 KBO-dashboard/1.0"}, timeout=30)
response.raise_for_status()
response.encoding = response.apparent_encoding
soup = BeautifulSoup(response.text, "html.parser")

date_match = re.search(r"(20\d{2})년\s*(\d{1,2})월\s*(\d{1,2})일\s*기준", soup.get_text(" ", strip=True))
if not date_match:
    raise RuntimeError("KBO 기준 날짜를 찾지 못했습니다.")
year, month, day = map(int, date_match.groups())
data_date = f"{year}. {month}. {day}. 경기 종료 기준"

rank_table = None
for table in soup.find_all("table"):
    headers = [text(th) for th in table.find_all("th")]
    if all(name in headers for name in ("순위", "팀명", "경기", "승", "패", "무", "승률", "게임차", "연속")):
        rank_table = table
        break
if rank_table is None:
    raise RuntimeError("KBO 순위표를 찾지 못했습니다.")

teams = []
for row in rank_table.select("tbody tr"):
    cells = [text(td) for td in row.find_all("td")]
    if len(cells) < 10 or cells[1] not in COLORS:
        continue
    teams.append({
        "name": cells[1], "g": int(cells[2]), "w": int(cells[3]),
        "l": int(cells[4]), "d": int(cells[5]), "streak": cells[9],
        "color": COLORS[cells[1]],
    })
if len(teams) != 10:
    raise RuntimeError(f"순위표에서 {len(teams)}개 팀만 읽었습니다.")

team_names = [team["name"] for team in teams]
match_table = None
for table in soup.find_all("table"):
    table_text = text(table)
    if "팀간 승패표" in table_text or ("합계" in table_text and all(name in table_text for name in team_names)):
        rows = table.select("tbody tr")
        if any(text(row.find_all("td")[0]) in team_names for row in rows if row.find_all("td")):
            match_table = table
            break
if match_table is None:
    raise RuntimeError("KBO 팀간 승패표를 찾지 못했습니다.")

played = {}
for row in match_table.select("tbody tr"):
    cells = [text(td) for td in row.find_all("td")]
    if not cells or cells[0] not in team_names:
        continue
    played[cells[0]] = cells[1:11]
if len(played) != 10:
    raise RuntimeError("팀간 승패표 10개 행을 모두 읽지 못했습니다.")

remaining = {}
for i, home in enumerate(team_names):
    for j in range(i + 1, len(team_names)):
        away = team_names[j]
        record = played[home][j]
        numbers = [int(n) for n in re.findall(r"\d+", record)]
        if len(numbers) < 2:
            raise RuntimeError(f"{home}-{away} 전적을 해석하지 못했습니다: {record!r}")
        games_left = 16 - sum(numbers[:3])
        remaining.setdefault(home, {})[away] = games_left

team_js = json.dumps(teams, ensure_ascii=False, separators=(",", ":"))
remaining_js = json.dumps(remaining, ensure_ascii=False, separators=(",", ":"))
generated = (
    "// AUTO_DATA_START — scripts/update_kbo.py가 이 구간을 갱신합니다.\n"
    f"    const DATA_DATE={json.dumps(data_date, ensure_ascii=False)};\n"
    "    // KBO 공식 홈페이지 일자별 팀 순위\n"
    f"    const teams={team_js};\n"
    "    // KBO 팀간 승패표로 계산한 잔여 맞대결 수\n"
    f"    const remainingMatchups={remaining_js};\n"
    "    // AUTO_DATA_END"
)

source = INDEX.read_text(encoding="utf-8")
updated, count = re.subn(
    r"// AUTO_DATA_START.*?// AUTO_DATA_END",
    generated,
    source,
    count=1,
    flags=re.DOTALL,
)
if count != 1:
    raise RuntimeError("index.html 자동 데이터 구간을 찾지 못했습니다.")
INDEX.write_text(updated, encoding="utf-8", newline="\n")
print(f"Updated KBO data: {data_date}")
