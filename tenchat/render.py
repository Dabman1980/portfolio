#!/usr/bin/env python3
"""Рендер обложки TenChat в PNG 1944×480 + машинная проверка геометрии.

Проверка обязана уметь упасть: она сравнивает РЕАЛЬНЫЕ bounding box'ы текста
(getBoundingClientRect после вёрстки) с двумя рамками —
  · безопасное поле  0..972 × 0..240 (ничего не должно вылезать за край),
  · запретная зона   левые 220 × нижние 140 (там аватар).
Пересечение с запретной зоной или выход за край = КРАСНОЕ, код возврата 1.
"""
import sys, json
from pathlib import Path
from playwright.sync_api import sync_playwright

TUT = Path(__file__).parent
ISHODNIK = TUT / "oblozhka-tenchat.html"

W, H = 972, 240          # система координат макета
SCALE = 2                # retina → PNG 1944×480
AV_W, AV_H = 220, 140    # запретная зона: левые AV_W × нижние AV_H

# Мобильная обрезка TenChat (object-cover), посчитана от замеров:
#   контейнер ~375×120 → срез по 111 px слева и справа   → жёсткая рамка
#   контейнер  375×60  → срез по  42 px сверху и снизу   → мягкое предупреждение
MOB_X1, MOB_X2 = 111, 861
MOB_Y1, MOB_Y2 = 42, 198
POLE_MOB = 12            # обязательный воздух до линии среза
POLE_MEZHDU = 8          # минимальный воздух между соседними блоками макета

# Что меряем: селектор → человеческое имя
ELEMENTY = {
    ".metka":    "метка (кто)",
    ".tezis":    "тезис (весь блок)",
    ".niz":      "нижняя строка",
    ".delo":     "что делает",
    ".masshtab": "масштаб (цифры)",
}


def zamer(page):
    """Мерим НЕ рамку блока, а реальные строки текста.

    ⚠️ Первая версия брала getBoundingClientRect() у блочного элемента — это ложное
    зелёное: блок всегда шириной с колонку, и текст, вылезший за него (white-space:nowrap),
    в замер не попадал. Range.getClientRects() отдаёт по прямоугольнику НА СТРОКУ,
    то есть настоящие чернила. Проверено красной пробой (proba=1).
    """
    return page.evaluate(
        """(sel) => Object.fromEntries(Object.entries(sel).map(([s, imya]) => {
             const el = document.querySelector(s);
             if (!el) return [s, null];
             const rng = document.createRange();
             rng.selectNodeContents(el);
             const rects = [...rng.getClientRects()].filter(r => r.width > 1 && r.height > 1);
             if (!rects.length) return [s, null];
             return [s, {
               imya,
               stroki: rects.map(r => ({x: r.x, y: r.y, w: r.width,
                                        right: r.right, bottom: r.bottom})),
               x:      Math.min(...rects.map(r => r.x)),
               y:      Math.min(...rects.map(r => r.y)),
               right:  Math.max(...rects.map(r => r.right)),
               bottom: Math.max(...rects.map(r => r.bottom)),
               text: (el.innerText || '').replace(/\\s+/g, ' ').trim()
             }];
           }))""",
        ELEMENTY,
    )


def proverit(zamery):
    """Возвращает список нарушений. Пустой список = зелёное."""
    bedy = []
    for sel, d in zamery.items():
        if d is None:
            bedy.append(f"{sel}: элемент не найден в DOM")
            continue
        imya = d["imya"]
        # 1. выход за край холста
        if d["x"] < 0 or d["y"] < 0 or d["right"] > W + 0.5 or d["bottom"] > H + 0.5:
            bedy.append(
                f"{imya}: вышел за холст — "
                f"x={d['x']:.1f} y={d['y']:.1f} право={d['right']:.1f} низ={d['bottom']:.1f} "
                f"(холст {W}×{H})"
            )
        # 2. пересечение с запретной зоной аватара (левые AV_W × нижние AV_H)
        peresech_x = max(0, min(d["right"], AV_W) - max(d["x"], 0))
        peresech_y = max(0, min(d["bottom"], H) - max(d["y"], H - AV_H))
        if peresech_x > 0.5 and peresech_y > 0.5:
            bedy.append(
                f"{imya}: залез под аватар на {peresech_x:.0f}×{peresech_y:.0f} px "
                f"(зона: x<{AV_W}, y>{H - AV_H})"
            )
        # 3. мобильная обрезка по горизонтали (контейнер ~375×120, object-cover):
        #    всё правее MOB_X2 и левее MOB_X1 на телефоне не существует. Это жёстко.
        if d["right"] > MOB_X2 - POLE_MOB:
            bedy.append(
                f"{imya}: ближе {POLE_MOB} px к мобильному срезу "
                f"(правый край {d['right']:.0f}, срез на x={MOB_X2})"
            )
        if d["x"] < MOB_X1 - 0.5:
            bedy.append(f"{imya}: левее мобильной обрезки (видно от x={MOB_X1})")

    # 4. столкновение блоков между собой.
    # ⚠️ Добавлено 10.08.2026 по ложному зелёному: длинный тезис разросся на три строки,
    # налез на нижнюю строку вплотную — а проверка отрапортовала «геометрия чистая»,
    # потому что мерила только холст, аватар и мобильный срез. Отношения соседей
    # не проверял никто. Смотреть надо на картинку, но картинка должна быть последней
    # инстанцией, а не единственной.
    poryadok = [".metka", ".tezis", ".niz"]
    for verhniy, nizhniy in zip(poryadok, poryadok[1:]):
        v, n = zamery.get(verhniy), zamery.get(nizhniy)
        if not v or not n:
            continue
        vozduh = n["y"] - v["bottom"]
        if vozduh < POLE_MEZHDU:
            bedy.append(
                f"{v['imya']} и {n['imya']}: между ними {vozduh:.0f} px "
                f"(норма {POLE_MEZHDU}) — блоки слиплись"
            )
    return bedy


def predupredit(zamery):
    """Мягкий слой: что теряется при САМОЙ жёсткой вертикальной обрезке (контейнер 375×60).
    Это не отказ — это то, о чём надо сказать вслух."""
    slova = []
    for sel, d in zamery.items():
        if d and (d["y"] < MOB_Y1 - 0.5 or d["bottom"] > MOB_Y2 + 0.5):
            slova.append(f"{d['imya']}: обрежется при высоте 60 px "
                         f"(видно y {MOB_Y1}…{MOB_Y2}, элемент y {d['y']:.0f}…{d['bottom']:.0f})")
    return slova


def main() -> int:
    # Красная проба: заведомо ломаем макет и убеждаемся, что проверка это ЛОВИТ.
    # Без неё зелёный вердикт ничего не доказывает.
    proba = "--proba" in sys.argv
    kuda = TUT / ("proba-krasnaya.png" if proba else "tenchat-oblozhka-1944x480.png")

    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=SCALE)
        page.goto(ISHODNIK.as_uri())
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(400)          # дать шрифтам примениться
        if proba:
            # сдвигаем колонку в зону аватара и раздуваем кегль — должно покраснеть дважды
            page.evaluate("""() => {
                document.documentElement.style.setProperty('--hrebet', '0px');
                document.querySelector('.tezis').style.fontSize = '70px';
            }""")
            page.wait_for_timeout(150)

        zamery = zamer(page)
        page.screenshot(path=str(kuda))
        b.close()

    print(f"PNG: {kuda}" + ("   ⚠️ КРАСНАЯ ПРОБА, не рабочий файл" if proba else ""))
    print(f"\n{'элемент':<22} {'строк':>6} {'x':>7} {'y':>7} {'право':>8} {'низ':>7}")
    print("-" * 62)
    for sel, d in zamery.items():
        if d:
            print(f"{d['imya']:<22} {len(d['stroki']):>6} {d['x']:>7.1f} {d['y']:>7.1f} "
                  f"{d['right']:>8.1f} {d['bottom']:>7.1f}")

    print("\nстроки тезиса (реальные чернила):")
    if zamery.get(".tezis"):
        for i, r in enumerate(zamery[".tezis"]["stroki"], 1):
            print(f"  строка {i}: x={r['x']:.0f} ширина={r['w']:.0f} правый край={r['right']:.0f}")

    print("\nтексты:")
    for sel, d in zamery.items():
        if d and d["text"]:
            print(f"  {d['imya']}: {d['text']}")

    bedy = proverit(zamery)
    print()
    if bedy:
        print("🔴 ГЕОМЕТРИЯ НЕ ПРОШЛА:")
        for b_ in bedy:
            print("   ·", b_)
        return 1
    zapas = MOB_X2 - max(d["right"] for d in zamery.values() if d)
    print("🟢 геометрия чистая: за холст никто не вышел, под аватар никто не залез,")
    print(f"   в мобильную обрезку по горизонтали всё влезло (запас {zapas:.0f} px).")
    slova = predupredit(zamery)
    if slova:
        print("\n🟡 при самой жёсткой вертикальной обрезке (высота 60 px) потеряется:")
        for s_ in slova:
            print("   ·", s_)
    return 0


if __name__ == "__main__":
    sys.exit(main())
