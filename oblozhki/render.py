#!/usr/bin/env python3
"""Рендер обложек FL.ru / Kwork / LinkedIn из одного исходника + проверка геометрии.

Проверка обязана уметь упасть: она сравнивает РЕАЛЬНЫЕ прямоугольники строк
(Range.getClientRects после вёрстки) с рамками площадки —
  · холст — за край не вылезать;
  · запретная зона аватара (левые av_w × нижние av_h) — там ничего значимого;
  · для Kwork — центральные 65 % ширины, площадка режет по бокам;
  · воздух между соседними блоками макета.
Любое нарушение = КРАСНОЕ, код возврата 1.

Пробы, доказывающие, что проверка не зелёная по построению:
    python3 render.py --proba 1   # текст загнан в зону аватара
    python3 render.py --proba 2   # кегль тезиса вздут, блоки слипаются
"""
import sys, json, argparse
from pathlib import Path
from playwright.sync_api import sync_playwright

TUT = Path(__file__).parent
ISHODNIK = TUT / "oblozhka.html"
SCALE = 2

# площадка → (CSS-ширина, CSS-высота, av_w, av_h, держать в центральных 65 %)
PLOSHCHADKI = {
    "fl":       (960, 200, 190, 110, False),
    "kwork":    (960, 113,   0,   0, True),
    "linkedin": (792, 198, 200, 100, False),
}
IMENA = {
    "fl":       "cover_fl_tenchat.png",
    "kwork":    "cover_kwork_tenchat.png",
    "linkedin": "cover_linkedin.png",
}

ELEMENTY = {
    ".metka":    "метка (кто)",
    ".tezis":    "тезис",
    ".niz":      "нижняя строка",
    ".delo":     "что делает",
    ".masshtab": "масштаб (цифры)",
}
POLE_MEZHDU = 6   # минимальный воздух между соседними блоками макета


def zamer(page):
    """Мерим не рамку блока, а реальные строки текста.

    ⚠️ getBoundingClientRect() у блочного элемента — ложное зелёное: блок всегда
    шириной с колонку, и текст, вылезший за него, в замер не попадёт.
    Range.getClientRects() отдаёт прямоугольник НА СТРОКУ, то есть настоящие чернила.
    """
    return page.evaluate(
        """(sel) => Object.fromEntries(Object.entries(sel).map(([s, imya]) => {
             const el = document.querySelector(s);
             if (!el) return [s, null];
             const st = getComputedStyle(el);
             if (st.display === 'none') return [s, null];
             const rng = document.createRange();
             rng.selectNodeContents(el);
             const rects = [...rng.getClientRects()].filter(r => r.width > 1 && r.height > 1);
             if (!rects.length) return [s, null];
             return [s, {
               imya,
               x:      Math.min(...rects.map(r => r.x)),
               y:      Math.min(...rects.map(r => r.y)),
               right:  Math.max(...rects.map(r => r.right)),
               bottom: Math.max(...rects.map(r => r.bottom)),
               text: (el.innerText || '').replace(/\\s+/g, ' ').trim()
             }];
           }))""",
        ELEMENTY,
    )


def proverit(zamery, W, H, av_w, av_h, tsentr65):
    bedy = []
    for sel, d in zamery.items():
        if d is None:
            continue
        imya = d["imya"]

        # 1. выход за холст
        if d["x"] < -0.5 or d["y"] < -0.5 or d["right"] > W + 0.5 or d["bottom"] > H + 0.5:
            bedy.append(f"{imya}: вышел за холст — "
                        f"x{d['x']:.0f}..{d['right']:.0f} y{d['y']:.0f}..{d['bottom']:.0f}, "
                        f"холст {W}×{H}")

        # 2. запретная зона аватара: левые av_w × нижние av_h
        if av_w and av_h:
            if d["x"] < av_w and d["bottom"] > H - av_h:
                bedy.append(f"{imya}: заехал в зону аватара "
                            f"(левые {av_w} × нижние {av_h}) — "
                            f"x{d['x']:.0f}, bottom {d['bottom']:.0f}")

        # 3. Kwork режет по бокам: значимое в центральных 65 %
        if tsentr65:
            L, R = W * 0.175, W * 0.825
            if d["x"] < L - 0.5 or d["right"] > R + 0.5:
                bedy.append(f"{imya}: вне центральных 65 % — "
                            f"x{d['x']:.0f}..{d['right']:.0f}, "
                            f"безопасно {L:.0f}..{R:.0f}")

    # 4. воздух между соседними блоками по вертикали
    poryadok = [".metka", ".tezis", ".niz"]
    vidimye = [(s, zamery[s]) for s in poryadok if zamery.get(s)]
    for (s1, a), (s2, b) in zip(vidimye, vidimye[1:]):
        prosvet = b["y"] - a["bottom"]
        if prosvet < POLE_MEZHDU:
            bedy.append(f"{a['imya']} и {b['imya']}: просвет {prosvet:.1f} px "
                        f"при минимуме {POLE_MEZHDU}")
    return bedy


def prognat(pw, ploshchadka, proba=0):
    W, H, av_w, av_h, tsentr65 = PLOSHCHADKI[ploshchadka]
    brauzer = pw.chromium.launch()
    stranitsa = brauzer.new_page(viewport={"width": W, "height": H},
                                 device_scale_factor=SCALE)
    stranitsa.goto(f"file://{ISHODNIK}?p={ploshchadka}")

    if proba == 1:   # красная проба: загнать метку в зону аватара
        stranitsa.evaluate("""() => {
            const k = document.querySelector('.kolonka');
            k.style.left = '0px'; k.style.bottom = '0px';
        }""")
    if proba == 2:   # красная проба: вздуть кегль, блоки слипнутся
        stranitsa.evaluate("""() => {
            document.querySelector('.tezis').style.fontSize = '80px';
        }""")

    stranitsa.wait_for_timeout(350)
    zamery = zamer(stranitsa)
    bedy = proverit(zamery, W, H, av_w, av_h, tsentr65)

    put = TUT / IMENA[ploshchadka]
    if not proba:
        stranitsa.locator(".holst").screenshot(path=str(put))
    brauzer.close()
    return put, W * SCALE, H * SCALE, zamery, bedy


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proba", type=int, default=0, help="1 или 2 — красная проба")
    ap.add_argument("--tolko", default=None, help="одна площадка")
    args = ap.parse_args()

    ploshchadki = [args.tolko] if args.tolko else list(PLOSHCHADKI)
    vsego_bed = 0
    with sync_playwright() as pw:
        for pl in ploshchadki:
            put, w, h, zamery, bedy = prognat(pw, pl, args.proba)
            print(f"\n── {pl}  →  {w}×{h}")
            for sel, d in zamery.items():
                if d:
                    print(f"   {d['imya']:<18} x{d['x']:6.1f}..{d['right']:6.1f}  "
                          f"y{d['y']:6.1f}..{d['bottom']:6.1f}   {d['text'][:44]}")
            if bedy:
                vsego_bed += len(bedy)
                print("   🔴 НАРУШЕНИЯ:")
                for b in bedy:
                    print(f"      · {b}")
            else:
                print(f"   🟢 геометрия чистая" + ("" if args.proba else f" → {put.name}"))

    print()
    if vsego_bed:
        print(f"ИТОГ: 🔴 нарушений {vsego_bed}")
        sys.exit(1)
    print("ИТОГ: 🟢 все площадки чистые")


if __name__ == "__main__":
    main()
