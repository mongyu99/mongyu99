"""최근 7일(오늘 포함, 한국 시간) 기여 합계 → 보리 레벨, 현재 시각 → 배경 시간대로 barley.gif 생성.
환경변수: GH_USER(깃허브 아이디), GITHUB_TOKEN(Actions가 자동 제공)
로컬 테스트: python generate.py --level 5 --time sunset"""
import os, sys, json, urllib.request
from datetime import datetime, timezone, timedelta
from make_barley import draw_frame, FRAMES, save_gif, W, H, SCALE
from make_sky import sky_frame, tint, save_rgb_gif
from PIL import Image

KST = timezone(timedelta(hours=9))

# 최근 7일 기여 합계가 이 값 이상이면 해당 레벨 (1~8). 원하는 대로 조절
THRESHOLDS = [1, 2, 3, 4, 5, 6, 7, 8]

def to_level(total):
    return sum(total >= t for t in THRESHOLDS)

def fetch_stats(user, token):
    """최근 7일 [(날짜, 기여 수)] 와 지난 1년 총 기여 수"""
    now = datetime.now(KST)
    start = (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
    query = """query($u:String!,$f:DateTime!,$t:DateTime!){user(login:$u){
      week:contributionsCollection(from:$f,to:$t){contributionCalendar{weeks{contributionDays{date contributionCount}}}}
      year:contributionsCollection{contributionCalendar{totalContributions}}}}"""
    body = json.dumps({"query": query, "variables": {
        "u": user, "f": start.isoformat(), "t": now.isoformat()}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", body,
                                 {"Authorization": f"bearer {token}", "Content-Type": "application/json"})
    data = json.load(urllib.request.urlopen(req))["data"]["user"]
    counts = {d["date"]: d["contributionCount"]
              for w in data["week"]["contributionCalendar"]["weeks"] for d in w["contributionDays"]}
    days = [(start + timedelta(days=i)).date() for i in range(7)]
    week = [(d, counts.get(d.isoformat(), 0)) for d in days]
    return week, data["year"]["contributionCalendar"]["totalContributions"]

def stats_svg(week, year_total, level):
    """보리밭 아래에 붙일 수치 카드 (832px 폭)"""
    total = sum(c for _, c in week)
    streak = 0
    for _, c in reversed(week):
        if c == 0:
            break
        streak += 1
    names = "월화수목금토일"
    peak = max([c for _, c in week] + [1])
    bars = []
    for i, (d, c) in enumerate(week):
        x = 520 + i * 42
        h = 4 + int(56 * c / peak)
        color = "#f2c35a" if c else "#3a4356"
        bars.append(f'<rect x="{x}" y="{96 - h}" width="26" height="{h}" rx="2" fill="{color}"/>'
                    f'<text x="{x + 13}" y="{90 - h}" class="s" text-anchor="middle">{c or ""}</text>'
                    f'<text x="{x + 13}" y="116" class="s" text-anchor="middle">{names[d.weekday()]}</text>')
    seg = "".join(f'<rect x="{24 + i * 54}" y="96" width="48" height="14" rx="2" fill="{"#f2c35a" if i < level else "#3a4356"}"/>'
                  for i in range(8))
    stage = ["빈 밭", "싹이 틈", "이삭이 남", "알이 맺힘", "알이 차오름", "누렇게 물듦", "고개를 숙임", "거의 다 익음", "수확 준비 완료"][level]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="832" height="136" viewBox="0 0 832 136">
<style>
  text{{font-family:"DungGeunMo","Galmuri11",ui-monospace,"Consolas",monospace;fill:#e8dcc0}}
  .b{{font-size:30px;font-weight:bold;fill:#f2c35a}} .m{{font-size:14px}} .s{{font-size:12px;fill:#a8a08c}}
</style>
<defs><linearGradient id="g"><stop offset="0" stop-color="#1b2130" stop-opacity="0"/><stop offset=".15" stop-color="#1b2130" stop-opacity=".85"/><stop offset=".85" stop-color="#1b2130" stop-opacity=".85"/><stop offset="1" stop-color="#1b2130" stop-opacity="0"/></linearGradient></defs>
<rect width="832" height="136" fill="url(#g)"/>
<text x="24" y="30" class="m">🌾 이번 주 보리밭 · {stage}</text>
<text x="24" y="72" class="b">{total}</text><text x="{34 + 18 * len(str(total))}" y="72" class="m">커밋 / 7일</text>
<text x="200" y="56" class="s">연속</text><text x="200" y="76" class="m">{streak}일째</text>
<text x="290" y="56" class="s">1년 동안</text><text x="290" y="76" class="m">{year_total}개</text>
<text x="462" y="108" class="s">{level}/8</text>
{seg}
{"".join(bars)}
</svg>'''
def edge_mask(left=22, right=22, top=10, bottom=3):
    """가장자리를 픽셀 디더링으로 투명하게 흩어서 배경(다크/라이트 모두)에 녹아들게 함"""
    bayer = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
    m = Image.new("L", (W, H))
    px = m.load()
    for y in range(H):
        for x in range(W):
            k = min(1, x / left, (W - 1 - x) / right, y / top, (H - 1 - y) / bottom)
            px[x, y] = 255 if k * 16 > bayer[y % 4][x % 4] + 0.5 else 0
    return m.resize((W * SCALE, H * SCALE), Image.NEAREST)

def time_of_day(hour):
    if 4 <= hour < 7:   return "dawn"
    if 7 <= hour < 17:  return "day"
    if 17 <= hour < 20: return "sunset"
    if 20 <= hour < 24: return "night"
    return "midnight"

def main():
    args = dict(zip(sys.argv[1::2], sys.argv[2::2]))
    if "--level" in args:
        level = int(args["--level"])
    else:
        week, year_total = fetch_stats(os.environ["GH_USER"], os.environ["GITHUB_TOKEN"])
        count = sum(c for _, c in week)
        level = to_level(count)
        print("last 7 days contributions:", count, week)
        with open("stats.svg", "w", encoding="utf-8") as fp:
            fp.write(stats_svg(week, year_total, level))
    name = args.get("--time") or time_of_day(datetime.now(KST).hour)
    print("level", level, "time", name)
    mask = edge_mask()
    frames = []
    for f in range(FRAMES):
        fr = Image.alpha_composite(sky_frame(name, f), tint(draw_frame(level, f), name))
        fr.putalpha(mask)
        frames.append(fr)
    save_gif(frames, args.get("--out", "barley.gif"))

if __name__ == "__main__":
    main()


