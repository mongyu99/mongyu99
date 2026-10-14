"""시간대별 배경(새벽/낮/노을/밤/야밤) 픽셀 애니메이션 GIF.
make_barley.py 와 같은 크기(64x40 → 4배), 60프레임 30fps.
실행: make_barley.py 뒤에 이어 붙여 실행 (draw_frame 재사용)."""
import math, random, os
from make_barley import *
from PIL import Image

SKIES = {
    # 이름: (하늘 위, 하늘 아래, 해/달 색, 해/달 위치(x,y), 별 개수, 구름 색, 언덕 색, 보리 조명 색, 조명 세기)
    "dawn":      ((70, 80, 140), (240, 170, 150), (255, 220, 190), (12, 30), 8,  (200, 150, 170), (70, 60, 90),  (255, 190, 200), 0.15),
    "day":       ((90, 160, 230), (190, 225, 245), (255, 250, 210), (48, 8),  0,  (250, 252, 255), (90, 140, 90), (255, 255, 255), 0.0),
    "sunset":    ((60, 50, 100), (250, 160, 90),  (255, 225, 150), (48, 28), 0,  (240, 150, 120), (110, 70, 70), (255, 170, 90),  0.2),
    "night":     ((20, 30, 70),  (60, 70, 130),   (240, 240, 210), (50, 9),  25, (70, 80, 130),  (30, 35, 60),  (110, 130, 200), 0.35),
    "midnight":  ((5, 6, 20),    (20, 22, 50),    (220, 220, 200), (10, 6),  60, (30, 32, 60),   (12, 12, 25),  (60, 70, 140),   0.55),
}

def sky_frame(name, f):
    top, low, orb, (ox0, oy), nstars, cloud, hill, _, _ = SKIES[name]
    ox = ox0 * W // 64
    img = Image.new("RGBA", (W, H))
    px = img.load()
    t = f / FRAMES
    for y in range(H):
        c = lerp(top, low, y / (H - 1))
        c = tuple((v // 10) * 10 for v in c)           # 밴딩으로 픽셀 느낌
        for x in range(W):
            px[x, y] = c + (255,)
    srnd = random.Random(5)
    for i in range(nstars * 3):
        sx, sy = srnd.randrange(W), srnd.randrange(0, 22)
        tw = math.sin(2 * math.pi * (t * srnd.choice((1, 2)) + srnd.random()))
        if tw > -0.3:
            b = 255 if tw > 0.6 else 170
            px[sx, sy] = (b, b, min(255, b + 20), 255)
    r2 = 6 if name in ("night", "midnight") else 10
    for y in range(max(0, oy - 4), oy + 5):
        for x in range(ox - 4, ox + 5):
            if 0 <= x < W and y < H and (x - ox) ** 2 + (y - oy) ** 2 <= r2:
                px[x, y] = orb + (255,)
    if name in ("night", "midnight"):                   # 초승달
        for y in range(oy - 3, oy + 4):
            for x in range(ox - 3, ox + 4):
                if 0 <= x < W and 0 <= y < H and (x - ox - 1) ** 2 + (y - oy + 1) ** 2 <= 5:
                    px[x, y] = lerp(top, low, y / (H - 1)) + (255,)
    for cx0, cy, ln in ((6, 12, 12), (38, 6, 9), (24, 18, 7), (90, 10, 14), (130, 5, 10), (170, 15, 12)):
        cx = int(cx0 + t * W) % (W + 16) - 16
        for x in range(cx, cx + ln):
            if 0 <= x < W:
                px[x, cy] = cloud + (255,)
                if cx + 2 <= x < cx + ln - 2:
                    px[x, cy - 1] = lerp(cloud, (255, 255, 255), 0.3) + (255,)
    for x in range(W):
        top_y = 26 + int(2 * math.sin(x / 9) + 1.5 * math.sin(x / 4 + 1))
        for y in range(top_y, H):
            px[x, y] = hill + (255,)
    return img.resize((W * SCALE, H * SCALE), Image.NEAREST)

def tint(img, name):
    *_, light, k = SKIES[name]
    if k == 0:
        return img
    r, g, b, a = img.split()
    rgb = Image.merge("RGB", (r, g, b))
    over = Image.new("RGB", img.size, light)
    mul = Image.blend(Image.new("RGB", img.size, (255, 255, 255)), over, k)
    from PIL import ImageChops
    rgb = ImageChops.multiply(rgb, mul)
    return Image.merge("RGBA", (*rgb.split(), a))

def save_rgb_gif(frames, path):
    pal = [fr.convert("RGB").quantize(colors=256, method=Image.Quantize.MEDIANCUT) for fr in frames]
    pal[0].save(path, save_all=True, append_images=pal[1:], duration=1000 // FPS, loop=0)

def main():
    os.makedirs("sky", exist_ok=True)
    for name in SKIES:
        save_rgb_gif([sky_frame(name, f) for f in range(FRAMES)], f"sky/sky_{name}.gif")
        print("sky", name)

    # 합성 예시: 시간대 × 레벨(0,4,8) 미리보기
    cw, ch = W * 2, H * 2
    sheet = Image.new("RGBA", (cw * 3, ch * len(SKIES)))
    for r, name in enumerate(SKIES):
        for c, level in enumerate((0, 4, 8)):
            tile = sky_frame(name, 10)
            tile.alpha_composite(tint(draw_frame(level, 10), name))
            sheet.paste(tile.resize((cw, ch), Image.NEAREST), (c * cw, r * ch))
    sheet.save("sky/preview_times.png")
    # 합성 GIF 예시: 노을 + 레벨 8
    save_rgb_gif([Image.alpha_composite(sky_frame("sunset", f), tint(draw_frame(8, f), "sunset")) for f in range(FRAMES)],
                 "sky/example_sunset_8.gif")


if __name__ == "__main__":
    main()


