#!/usr/bin/env python3
"""Два контрольных изображения к обложке TenChat.

1) proverka-1-avatar.png — реальная геометрия: обложка 972×240 с НАСТОЯЩИМ аватаром
   160×160, который накрывает нижний левый угол (съедает 180 слева, 116 снизу),
   плюс пунктиром показана запретная зона 220×140, внутри которой ничего быть не должно.

2) proverka-2-mobile.png — мобильная обрезка object-cover в двух прочтениях `max-mobile:h-30`:
   120 px (обрезка по бокам) и 60 px (обрезка сверху и снизу).

Всё считается в системе координат макета 972×240 и умножается на МАСШТАБ=2,
потому что исходный PNG уже 1944×480 — пережимать его вниз незачем.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

TUT = Path(__file__).parent
ISHODNIK = TUT / "tenchat-oblozhka-1944x480.png"
M = 2                                   # макет 972×240 → PNG 1944×480
W, H = 972 * M, 240 * M

SHRIFT = "/System/Library/Fonts/Supplemental/PTSans.ttc"
def sh(n, jirniy=False):
    try:
        return ImageFont.truetype(SHRIFT, n, index=1 if jirniy else 0)
    except Exception:
        return ImageFont.load_default()

FON   = (238, 238, 234)
CHERN = (26, 30, 36)
SEDOY = (110, 118, 130)
KRASN = (200, 60, 55)


def punktir(d, xy, cvet, shag=14, tolsh=3):
    """Пунктирный прямоугольник — сплошной слишком похож на элемент дизайна."""
    x1, y1, x2, y2 = xy
    for x in range(int(x1), int(x2), shag * 2):
        d.line([x, y1, min(x + shag, x2), y1], fill=cvet, width=tolsh)
        d.line([x, y2, min(x + shag, x2), y2], fill=cvet, width=tolsh)
    for y in range(int(y1), int(y2), shag * 2):
        d.line([x1, y, x1, min(y + shag, y2)], fill=cvet, width=tolsh)
        d.line([x2, y, x2, min(y + shag, y2)], fill=cvet, width=tolsh)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Реальная геометрия: аватар на месте
# ─────────────────────────────────────────────────────────────────────────────
def avatar_proverka():
    oblozhka = Image.open(ISHODNIK).convert("RGB")
    assert oblozhka.size == (W, H), f"ожидал {W}×{H}, получил {oblozhka.size}"

    POLE, VERH, NIZ = 80, 150, 300      # поля холста и место под «страницу профиля»
    holst = Image.new("RGB", (W + POLE * 2, VERH + H + NIZ), FON)
    d = ImageDraw.Draw(holst)

    d.text((POLE, 46), "КОНТРОЛЬ 1 · реальная геометрия профиля TenChat",
           font=sh(40, True), fill=CHERN)
    d.text((POLE, 100),
           "обложка 972×240 · аватар 160×160 накрывает нижний левый угол "
           "(съедает 180 слева, 116 снизу)",
           font=sh(28), fill=SEDOY)

    # «страница профиля» под обложкой — белая, чтобы было видно, как аватар свисает
    d.rectangle([POLE, VERH + H, POLE + W, VERH + H + NIZ - 90], fill=(255, 255, 255))
    holst.paste(oblozhka, (POLE, VERH))

    # запретная зона: левые 220 × нижние 140 (в координатах макета)
    zx, zy = 220 * M, 140 * M
    punktir(d, (POLE, VERH + H - zy, POLE + zx, VERH + H), KRASN)
    d.text((POLE, VERH + H + 120),
           "- - -  запретная зона 220×140 (пунктир): тут ничего быть не должно",
           font=sh(28, True), fill=KRASN)

    # аватар: 160×160, правый край на x=180, верх на y=240−116=124 (координаты макета)
    ax2, ay1 = 180 * M, (240 - 116) * M
    ax1, ay2 = ax2 - 160 * M, ay1 + 160 * M
    box = [POLE + ax1, VERH + ay1, POLE + ax2, VERH + ay2]
    d.ellipse([box[0] - 8, box[1] - 8, box[2] + 8, box[3] + 8], fill=(255, 255, 255))
    d.ellipse(box, fill=(198, 202, 208))
    d.text(((box[0] + box[2]) // 2, (box[1] + box[3]) // 2), "ФОТО",
           font=sh(34, True), fill=(120, 126, 136), anchor="mm")

    d.text((POLE, VERH + H + 210),
           "OK · тезис, метка и нижняя строка целиком правее аватара — ничего не потеряно",
           font=sh(30, True), fill=(30, 110, 80))
    kuda = TUT / "proverka-1-avatar.png"
    holst.save(kuda)
    return kuda


# ─────────────────────────────────────────────────────────────────────────────
# 2. Мобильная обрезка
# ─────────────────────────────────────────────────────────────────────────────
def mobilnaya_proverka():
    oblozhka = Image.open(ISHODNIK).convert("RGB")

    def obrezat(cw, ch):
        """object-cover: вписать 972×240 в контейнер cw×ch с обрезкой по центру."""
        s = max(cw / 972, ch / 240)
        vid_w, vid_h = cw / s, ch / s              # видимая область в координатах макета
        x1, y1 = (972 - vid_w) / 2, (240 - vid_h) / 2
        kadr = oblozhka.crop((int(x1 * M), int(y1 * M),
                              int((x1 + vid_w) * M), int((y1 + vid_h) * M)))
        return kadr.resize((cw * 2, ch * 2), Image.LANCZOS), (x1, y1, vid_w, vid_h)

    sluchai = [
        (375, 120, "h-30 = 120 px", "срез по бокам: видно x 111…861, по высоте — всё"),
        (375, 60,  "h-30 = 60 px  («высота падает вчетверо»)",
                   "срез сверху и снизу: видно y 42…198"),
    ]

    POLE = 80
    kadry = [obrezat(cw, ch) for cw, ch, _, _ in sluchai]
    zagolovki = ["КОНТРОЛЬ 2 · мобильная обрезка TenChat (object-cover)",
                 "h-30 = 60 px  («высота падает вчетверо»)  —  контейнер 375×60",
                 "OK · заголовок читается в обоих случаях. При 60 px теряются метка сверху "
                 "и нижняя строка с цифрами."]
    proba_d = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    nuzhno = max(proba_d.textlength(z, font=sh(40, True)) for z in zagolovki)
    shirina = int(max(max(k.width for k, _ in kadry), nuzhno)) + POLE * 2
    vysota = 150 + sum(k.height + 150 for k, _ in kadry) + 120
    holst = Image.new("RGB", (shirina, vysota), FON)
    d = ImageDraw.Draw(holst)

    d.text((POLE, 46), "КОНТРОЛЬ 2 · мобильная обрезка TenChat (object-cover)",
           font=sh(40, True), fill=CHERN)
    d.text((POLE, 100), "показано в двойном размере — на экране телефона это 375 px в ширину",
           font=sh(28), fill=SEDOY)

    y = 170
    for (kadr, (x1, y1, vw, vh)), (cw, ch, imya, poyasn) in zip(kadry, sluchai):
        d.text((POLE, y), f"{imya}  —  контейнер {cw}×{ch}", font=sh(32, True), fill=CHERN)
        d.text((POLE, y + 42), poyasn, font=sh(26), fill=SEDOY)
        holst.paste(kadr, (POLE, y + 86))
        d.rectangle([POLE, y + 86, POLE + kadr.width, y + 86 + kadr.height],
                    outline=(200, 200, 196), width=2)
        y += 86 + kadr.height + 64

    d.text((POLE, y + 10),
           "OK · заголовок читается в обоих случаях. При 60 px теряются метка сверху "
           "и нижняя строка с цифрами.",
           font=sh(30, True), fill=(30, 110, 80))
    kuda = TUT / "proverka-2-mobile.png"
    holst.save(kuda)
    return kuda


if __name__ == "__main__":
    for f in (avatar_proverka(), mobilnaya_proverka()):
        print("готово:", f)
