#!/usr/bin/env python3
"""Два контрольных изображения к обложке TenChat.

1) proverka-1-avatar.png — весь холст 972×400 с пунктирной десктопной полосой
   (центральные 240 px — то, что видно на компьютере), запретной зоной аватара
   220×140 от нижнего левого угла полосы и НАСТОЯЩИМ аватаром 160×160.

2) proverka-2-mobile.png — что видит компьютер (одна полоса) против того,
   что видит телефон (весь холст): на телефоне видно БОЛЬШЕ, а не меньше.

⛔ Переписано 10.08.2026 вместе с моделью геометрии: прежняя версия рисовала
мобильную обрезку по бокам, которой не существует. Разбор — в render.py.

Всё считается в системе координат макета 972×400 и умножается на МАСШТАБ=2,
потому что исходный PNG уже 1944×800.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

TUT = Path(__file__).parent
ISHODNIK = TUT / "tenchat-oblozhka-1944x800.png"
M = 2                                   # макет 972×400 → PNG 1944×800
W, H = 972 * M, 400 * M
POLOSA_Y1, POLOSA_Y2 = 80 * M, 320 * M   # десктопная полоса: центральные 240 px

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
# 1. Весь холст: где полоса, где аватар
# ─────────────────────────────────────────────────────────────────────────────
def avatar_proverka():
    oblozhka = Image.open(ISHODNIK).convert("RGB")
    assert oblozhka.size == (W, H), f"ожидал {W}×{H}, получил {oblozhka.size}"

    POLE, VERH, NIZ = 80, 160, 190
    holst = Image.new("RGB", (W + POLE * 2, VERH + H + NIZ), FON)
    d = ImageDraw.Draw(holst)

    d.text((POLE, 46), "КОНТРОЛЬ 1 · холст целиком и что из него видно",
           font=sh(40, True), fill=CHERN)
    d.text((POLE, 100),
           "исходник 972×400 (пропорция кадрирующей рамки) · на компьютере видна только "
           "центральная полоса 972×240",
           font=sh(28), fill=SEDOY)

    holst.paste(oblozhka, (POLE, VERH))

    # десктопная полоса
    punktir(d, (POLE, VERH + POLOSA_Y1, POLE + W, VERH + POLOSA_Y2), (60, 130, 200))
    d.text((POLE, VERH + H + 34),
           "- - -  синим: десктопная полоса. Всё вне её видно только на телефоне",
           font=sh(28, True), fill=(60, 130, 200))

    # запретная зона аватара — от НИЖНЕГО края полосы
    zx, zy = 220 * M, 140 * M
    punktir(d, (POLE, VERH + POLOSA_Y2 - zy, POLE + zx, VERH + POLOSA_Y2), KRASN)
    d.text((POLE, VERH + H + 82),
           "- - -  красным: запретная зона аватара 220×140 от низа полосы",
           font=sh(28, True), fill=KRASN)

    # аватар: 160×160, правый край x=180, низ на 116 выше низа полосы
    ax2 = 180 * M
    ay2 = VERH + POLOSA_Y2 + 44 * M
    ax1, ay1 = ax2 - 160 * M, ay2 - 160 * M
    box = [POLE + ax1, ay1, POLE + ax2, ay2]
    d.ellipse([box[0] - 8, box[1] - 8, box[2] + 8, box[3] + 8], fill=(255, 255, 255))
    d.ellipse(box, fill=(198, 202, 208))
    d.text(((box[0] + box[2]) // 2, (box[1] + box[3]) // 2), "ФОТО",
           font=sh(34, True), fill=(120, 126, 136), anchor="mm")

    d.text((POLE, VERH + H + 134),
           "OK · метка, тезис и нижняя строка внутри полосы и правее аватара",
           font=sh(30, True), fill=(30, 110, 80))
    kuda = TUT / "proverka-1-avatar.png"
    holst.save(kuda)
    return kuda


# ─────────────────────────────────────────────────────────────────────────────
# 2. Компьютер против телефона
# ─────────────────────────────────────────────────────────────────────────────
def mobilnaya_proverka():
    oblozhka = Image.open(ISHODNIK).convert("RGB")
    desktop = oblozhka.crop((0, POLOSA_Y1, W, POLOSA_Y2))
    mobile = oblozhka.copy()
    mobile.thumbnail((W // 2, H), Image.LANCZOS)

    POLE = 80
    holst = Image.new("RGB", (W + POLE * 2, 170 + desktop.height + 150 + mobile.height + 120), FON)
    d = ImageDraw.Draw(holst)
    d.text((POLE, 46), "КОНТРОЛЬ 2 · компьютер против телефона", font=sh(40, True), fill=CHERN)
    d.text((POLE, 100), "на телефоне видно БОЛЬШЕ холста, чем на компьютере, а не меньше",
           font=sh(28), fill=SEDOY)

    y = 170
    d.text((POLE, y), "компьютер — центральная полоса 972×240", font=sh(32, True), fill=CHERN)
    holst.paste(desktop, (POLE, y + 50))
    d.rectangle([POLE, y + 50, POLE + desktop.width, y + 50 + desktop.height],
                outline=(200, 200, 196), width=2)
    y += 50 + desktop.height + 80

    d.text((POLE, y), "телефон — весь холст 972×400 (показан в половину размера)",
           font=sh(32, True), fill=CHERN)
    holst.paste(mobile, (POLE, y + 50))
    d.rectangle([POLE, y + 50, POLE + mobile.width, y + 50 + mobile.height],
                outline=(200, 200, 196), width=2)
    y += 50 + mobile.height + 40

    d.text((POLE, y), "OK · тезис читается в обоих случаях", font=sh(30, True), fill=(30, 110, 80))
    kuda = TUT / "proverka-2-mobile.png"
    holst.save(kuda)
    return kuda


if __name__ == "__main__":
    for f in (avatar_proverka(), mobilnaya_proverka()):
        print("готово:", f)
