"""잔디(기여도) 레벨 0~8에 따라 보리밭이 익어가는 픽셀 애니메이션 GIF 생성기.
- 배경 투명 (낮/밤 배경을 따로 깔 수 있게)
- 레벨 0: 바람 없는 초록 밭, 이삭 없음
- 레벨 1~8: 줄기마다 알맹이 1~8개, 색은 초록→황금, 바람도 점점 세짐
64x40 픽셀을 4배 확대, 60프레임(30fps, 2초 루프)."""
import math, random, os, sys
from PIL import Image

W, H = 208, 40
SCALE = 4
FRAMES = 60
FPS = 30

def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

STEM_GREEN = (80, 140, 50)
STEM_GOLD = (190, 140, 55)
LEAF_GREEN = (58, 110, 40)
LEAF_GOLD = (160, 112, 45)
GRAIN_GREEN = (140, 190, 75)
GRAIN_GOLD = (248, 200, 80)
SHADE_GREEN = (90, 140, 50)
SHADE_GOLD = (180, 115, 40)
AWN_GREEN = (180, 215, 130)
AWN_GOLD = (255, 228, 160)

# 줄기 배치: (x, 높이, 깊이 0=뒤 1=앞, 위상)
rnd = random.Random(3)
STALKS = []
for row, (n, hmin, hmax, depth) in enumerate(((9, 14, 19, 0), (8, 18, 24, 1))):
    n = int(n * W / 64)
    for i in range(n):
        x = int((i + 0.5 + rnd.uniform(-0.25, 0.25)) * W / n)
        STALKS.append((x, rnd.randint(hmin, hmax), depth, rnd.uniform(0, 2 * math.pi)))

def put(px, x, y, c):
    if 0 <= x < W and 0 <= y < H:
        px[x, y] = c + (255,)

def draw_stalk(px, level, t, x0, height, depth, phase):
    ripe = level / 8
    dim = 0.75 if depth == 0 else 1.0           # 뒷줄은 살짝 어둡게
    d = lambda c: tuple(int(v * dim) for v in c)
    stem_c = d(lerp(STEM_GREEN, STEM_GOLD, ripe))
    leaf_c = d(lerp(LEAF_GREEN, LEAF_GOLD, ripe))
    grain_c = d(lerp(GRAIN_GREEN, GRAIN_GOLD, ripe))
    shade_c = d(lerp(SHADE_GREEN, SHADE_GOLD, ripe))
    awn_c = d(lerp(AWN_GREEN, AWN_GOLD, ripe))

    wind_amp = 0 if level == 0 else 1.0 + ripe * 2.5   # 레벨 0은 무풍
    wind = math.sin(2 * math.pi * t + phase * 0.4 + x0 / 10) * wind_amp
    droop = ripe * 4                                    # 익을수록 고개 숙임

    base_y = H - 1
    pts = []
    for i in range(height):
        k = i / height
        pts.append((round(x0 + wind * k * k + droop * k ** 3), base_y - i))
    for x, y in pts:
        put(px, x, y, stem_c)
    # 잎 두 장
    for side, start in ((-1, 3), (1, 7)):
        for j in range(5):
            bx, by = pts[start + j // 2]
            put(px, bx + side * (j + 1) + (round(wind * 0.3) if j > 2 else 0), by - j // 2 + (1 if j == 4 else 0), leaf_c)

    tx, ty = pts[-1]
    if level == 0:
        # 빈 이삭: 끝이 살짝 갈라진 초록 줄기
        put(px, tx, ty - 1, stem_c)
        put(px, tx - 1, ty - 2, stem_c)
        put(px, tx + 1, ty - 2, stem_c)
        return
    for g in range(level):
        row = g // 2
        side = -1 if g % 2 == 0 else 1
        cx, cy = pts[max(0, height - 1 - row * 3)]
        gx = cx - 2 if side < 0 else cx + 1
        for dx in range(2):
            for dy in range(3):
                c = grain_c if dy < 2 and (dx == 0 if side < 0 else dx == 1) else shade_c
                put(px, gx + dx, cy - dy, c)
        # 까끄라기
        for a in range(1, 4 + level // 3):
            put(px, gx + (0 if side < 0 else 1) + side * (a // 2) + round(wind * a / 6), cy - 2 - a, awn_c)
    for a in range(1, 5):
        put(px, tx + round(wind * a / 5), ty - a, awn_c)

def draw_frame(level, f):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px = img.load()
    t = f / FRAMES
    for x0, h, depth, phase in sorted(STALKS, key=lambda s: s[2]):
        draw_stalk(px, level, t, x0, h, depth, phase)
    # 높은 레벨: 날리는 낟알
    prnd = random.Random(level * 13 + 1)
    for i in range(max(0, level - 3) * 6):
        sx, sy = prnd.randrange(W), prnd.randrange(2, 20)
        put(px, int(sx + t * W) % W, int(sy + 2 * math.sin(t * 2 * math.pi + i)), (255, 236, 170))
    return img.resize((W * SCALE, H * SCALE), Image.NEAREST)

def save_gif(frames, path):
    # 투명 GIF: 알파 0인 픽셀을 팔레트 0번(투명)으로
    pal_frames = []
    for fr in frames:
        p = fr.convert("RGB").quantize(colors=255, method=Image.Quantize.MEDIANCUT)
        out = Image.new("P", fr.size, 255)
        pal = p.getpalette()[:255 * 3] + [0, 0, 0]
        out.putpalette(pal)
        alpha = fr.getchannel("A")
        out.paste(p, mask=alpha.point(lambda a: 255 if a > 0 else 0))
        pal_frames.append(out)
    pal_frames[0].save(path, save_all=True, append_images=pal_frames[1:],
                       duration=1000 // FPS, loop=0, transparency=255, disposal=2, optimize=False)

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "barley"
    os.makedirs(out, exist_ok=True)
    os.chdir(out)
    for level in range(9):
        frames = [draw_frame(level, f) for f in range(FRAMES)]
        save_gif(frames, f"barley_{level}.gif")
        print("saved", level)
    # 미리보기: 낮/밤 배경 위에 0~8 나열
    cw, ch = W * 2, H * 2
    sheet = Image.new("RGBA", (cw * 9, ch * 2))
    for row, bg in enumerate(((150, 200, 240, 255), (25, 30, 60, 255))):
        for level in range(9):
            tile = Image.new("RGBA", (cw, ch), bg)
            tile.alpha_composite(draw_frame(level, 10).resize((cw, ch), Image.NEAREST))
            sheet.paste(tile, (level * cw, row * ch))
    sheet.save("preview_sheet.png")


