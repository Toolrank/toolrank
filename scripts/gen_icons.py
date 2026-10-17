#!/usr/bin/env python3
"""One-off: render PWA / home-screen icons from the ToolRank mark (assets/favicon.svg geometry) on navy #0b1220.
Outputs assets/icons/icon-192.png, icon-512.png, icon-512-maskable.png, assets/apple-touch-icon.png (+ root copy).
Needs cairosvg. Not run by build.py; re-run only if the logo changes."""
import pathlib, re, shutil, cairosvg
ROOT = pathlib.Path(__file__).resolve().parent.parent
src = (ROOT/"assets/favicon.svg").read_text()
defs = re.search(r"<defs>.*?</defs>", src, re.S).group(0)
mark = re.search(r'<g transform="skewX\(-17\)".*?</g>', src, re.S).group(0)
def svg(scale):
    # mark artwork spans roughly x -190..670, y -81..481 around centre (239,200); scale sets its share of the canvas
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">{defs}<rect width="512" height="512" fill="#0b1220"/>'
            f'<g transform="translate(256,256) scale({scale}) translate(-239,-200)">{mark}</g></svg>')
def out(name, size, scale):
    cairosvg.svg2png(bytestring=svg(scale).encode(), write_to=str(ROOT/name), output_width=size, output_height=size)
out("assets/icons/icon-192.png", 192, 0.50)
out("assets/icons/icon-512.png", 512, 0.50)
out("assets/icons/icon-512-maskable.png", 512, 0.36)  # mark fits inside the 80% safe-zone circle
out("assets/apple-touch-icon.png", 180, 0.46)
shutil.copy(ROOT/"assets/apple-touch-icon.png", ROOT/"apple-touch-icon.png")  # iOS probes /apple-touch-icon.png directly
print("icons written")
