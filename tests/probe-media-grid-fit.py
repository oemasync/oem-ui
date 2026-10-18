#!/usr/bin/env python3
"""Does a 6:1 source LETTERBOX in a 4:3 well, or is it cropped?

The distinguishing signal between `object-fit: contain` and `cover` is not
the <img> BOX — both fill the well — but WHICH PIXELS are painted. A 6:1
source (640x200) in a 4:3 well:

  contain -> the whole width survives, painted as a horizontal band with
             background above and below. The band's height is
             well.width / 6, so for a 308px well the band is ~51px in a
             231px box: 78% of the well is background.
  cover   -> the band fills the whole box and the source is cropped by
             ~4.5x horizontally (only the middle ~22% of the width shows).

So: screenshot the well, count rows that are not the well's background,
and compare that to the arithmetic. This is the falsifiable check the
first version of the probe lacked — it compared the BOX to the well and
reported a false failure on correct CSS.
"""
import os
import sys
import io
from playwright.sync_api import sync_playwright
from PIL import Image

# The host environment sets PLAYWRIGHT_BROWSERS_PATH at an NFS location that
# no longer exists (pve-host-offload/playwright was removed on the NAS), and
# playwright then hunts for webkit under the dead path and refuses to launch.
# Fall back to the local cache ONLY when the configured one is gone.
if os.environ.get("PLAYWRIGHT_BROWSERS_PATH") and not os.path.isdir(os.environ["PLAYWRIGHT_BROWSERS_PATH"]):
    del os.environ["PLAYWRIGHT_BROWSERS_PATH"]

URL = "http://192.168.1.68:4321/"
WELL = ".cm-media-grid__thumb"


def band_rows(img: Image.Image, bg, tol=12) -> int:
    """Count pixel ROWS that contain anything other than the background.

    Sample ONLY the interior columns. The element's own 1px border sits at
    x=0/x=w-1 and differs from the fill by ~16 levels, so a sampler that
    touches the edge counts EVERY row as band and always reports full
    height (a false `cover`). Skip a 2px inset on each side.
    """
    px = img.convert("RGB").load()
    w, h = img.size
    inset = max(2, w // 40)
    rows = 0
    for y in range(h):
        for x in range(inset, w - inset, max(1, (w - 2 * inset) // 40)):
            r, g, b = px[x, y]
            if abs(r - bg[0]) > tol or abs(g - bg[1]) > tol or abs(b - bg[2]) > tol:
                rows += 1
                break
    return rows


def main() -> int:
    fails = []
    with sync_playwright() as pw:
        b = pw.webkit.launch()
        for w, h in [(390, 844), (860, 900)]:
            ctx = b.new_context(viewport={"width": w, "height": h},
                                device_scale_factor=2, is_mobile=w < 700, has_touch=w < 700)
            pg = ctx.new_page()
            pg.emulate_media(reduced_motion="reduce")
            pg.goto(URL, wait_until="domcontentloaded")
            pg.wait_for_function("() => document.documentElement.classList.contains('cm-js')", timeout=15000)
            pg.wait_for_timeout(300)
            well = pg.locator(WELL).first
            well.scroll_into_view_if_needed()
            pg.wait_for_timeout(200)
            data = pg.evaluate(
                """() => { const t = document.querySelector('.cm-media-grid__thumb');
                   const i = t.querySelector('img'); const tr = t.getBoundingClientRect();
                   const ir = i.getBoundingClientRect();
                   return { well: [tr.width, tr.height], img: [ir.width, ir.height],
                            natural: [i.naturalWidth, i.naturalHeight],
                            bg: getComputedStyle(t).backgroundColor,
                            fit: getComputedStyle(i).objectFit, imgSrc: i.src.slice(0, 60) }; }""")
            shot = well.screenshot()
            im = Image.open(io.BytesIO(shot))
            bgcss = data["bg"]
            nums = [int(x) for x in bgcss.replace("rgb(", "").replace(")", "").split(",")[:3]]
            # device_scale_factor 2 => the screenshot is 2x the CSS box
            scale = im.size[1] / data["well"][1]
            band_px = band_rows(im, tuple(nums))
            band_css = band_px / scale
            well_w, well_h = data["well"]
            nat_w, nat_h = data["natural"]
            if not nat_w or not nat_h:
                fails.append(f"{w}: the panorama has no natural size ({nat_w}x{nat_h}); "
                             "the specimen did not load, so contain/cover is unmeasurable")
                ctx.close()
                continue
            src_ratio = nat_w / nat_h
            # contain arithmetic: the painted band is well_w / ratio tall, centred
            expect_contain = well_w / src_ratio
            expect_cover = well_h
            print(f"\n=== {w}x{h}  well {well_w:.1f}x{well_h:.1f}  box {data['img']}  "
                  f"natural {data['natural']}  fit={data['fit']}  bg={bgcss}")
            print(f"    painted band (CSS px): {band_css:.1f}")
            print(f"    contain arithmetic:    {expect_contain:.1f}  (source {nat_w}x{nat_h}, ratio {src_ratio:.2f})")
            print(f"    cover would paint:     {expect_cover:.1f}")
            if data["fit"] != "contain":
                fails.append(f"{w}: object-fit is {data['fit']}")
            # The band must be near the contain arithmetic and FAR from cover.
            if abs(band_css - expect_contain) > max(6, expect_contain * 0.18):
                fails.append(f"{w}: painted band {band_css:.1f}px does not match the contain "
                             f"arithmetic {expect_contain:.1f}px")
            if abs(band_css - expect_cover) < 6:
                fails.append(f"{w}: the band fills the well ({band_css:.1f}px) — that is COVER, "
                             "so the preview is cropped")
            ctx.close()
        b.close()
    print("\n" + ("FAILURES:\n  " + "\n  ".join(fails) if fails else "the preview letterboxes: contain holds"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
