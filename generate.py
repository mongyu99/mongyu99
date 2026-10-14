"""최근 7일(오늘 포함, 한국 시간) 기여 합계 → 보리 레벨, 현재 시각 → 배경 시간대로 barley.gif 생성.
환경변수: GH_USER(깃허브 아이디), GITHUB_TOKEN(Actions가 자동 제공)
로컬 테스트: python generate.py --level 5 --time sunset"""
import os, sys, json, urllib.request
from datetime import datetime, timezone, timedelta
from make_barley import draw_frame, FRAMES
from make_sky import sky_frame, tint, save_rgb_gif
from PIL import Image

KST = timezone(timedelta(hours=9))

# 최근 7일 기여 합계가 이 값 이상이면 해당 레벨 (1~8). 원하는 대로 조절
THRESHOLDS = [1, 2, 3, 4, 5, 6, 7, 8]

def to_level(total):
    return sum(total >= t for t in THRESHOLDS)

def week_contributions(user, token):
    now = datetime.now(KST)
    start = (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
    query = """query($u:String!,$f:DateTime!,$t:DateTime!){user(login:$u){
      contributionsCollection(from:$f,to:$t){contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}"""
    body = json.dumps({"query": query, "variables": {
        "u": user, "f": start.isoformat(), "t": now.isoformat()}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", body,
                                 {"Authorization": f"bearer {token}", "Content-Type": "application/json"})
    data = json.load(urllib.request.urlopen(req))
    days = [d for w in data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
            for d in w["contributionDays"]]
    first = start.date().isoformat()
    return sum(d["contributionCount"] for d in days if d["date"] >= first)

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
        count = week_contributions(os.environ["GH_USER"], os.environ["GITHUB_TOKEN"])
        level = to_level(count)
        print("last 7 days contributions:", count)
    name = args.get("--time") or time_of_day(datetime.now(KST).hour)
    print("level", level, "time", name)
    frames = [Image.alpha_composite(sky_frame(name, f), tint(draw_frame(level, f), name)) for f in range(FRAMES)]
    save_rgb_gif(frames, args.get("--out", "barley.gif"))

if __name__ == "__main__":
    main()
