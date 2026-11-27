#!/usr/bin/env python3
"""PDF / PPTX が拡大しても掠れないかを検査する（dotfiles ADR-0080）。

不合格（exit 1）:
  - PDF の Type 3 フォント・未埋め込みフォント（Acrobat / Chrome / Drive プレビューで文字が細く掠れる）
  - 文字を持たず画像だけのページ・スライド（文字ごと画像化されている。背景画像として貼った形を含む）
  - 配置サイズに対して解像度が足りない画像。写真（JPEG）は既定 200ppi 未満、
    スクリーンショットや図版に使う可逆形式（PNG など）は既定 288ppi 未満
    （16:9 スライド全面で横 3,840px。4K 画面の全画面表示で等倍になる解像度）
PDF は poppler の pdffonts / pdfimages を使う。PPTX は標準ライブラリだけで読む。
写真や図版そのものが主役のページは --allow-image-only で画像だけのページを許す。

この検査が見るのはファイルだけ。Google Drive のプレビューは PDF を 1 ページ横 3,200px までの
画像に変換して表示するので、合格した PDF でも Drive のプレビューでは拡大すると掠れる。
拡大して確かめるときは PDF ビューア（ブラウザの PDF 表示、macOS のプレビュー、Acrobat）で開く。
"""
import argparse
import re
import struct
import subprocess
import sys
import zipfile
from posixpath import dirname, join, normpath

EMU_PER_INCH = 914400


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


LOSSY_ENC = {"jpeg", "jpx", "jp2"}
RASTER_FIX = "2 倍以上の倍率で撮り直すか小さく配置する。図解は SVG / HTML で組む"


def check_pdf(path, min_ppi, min_ppi_lossless, allow_image_only):
    fails, notes = [], []
    pages = int(re.search(r"Pages:\s*(\d+)", run(["pdfinfo", path])).group(1))
    fonts = run(["pdffonts", path]).splitlines()[2:]
    type3, not_embedded = set(), set()
    for line in fonts:
        col = line.split()
        if len(col) < 7:
            continue
        name = col[0].split("+")[-1]
        if " ".join(col[1:-6]).startswith("Type 3"):
            type3.add(name)
        if col[-5] != "yes":
            not_embedded.add(name)
    if type3:
        fails.append("Type 3 フォント: " + ", ".join(sorted(type3)) + "（静的 TrueType を @font-face で埋め込み、太字は Bold の実体を使う）")
    if not_embedded:
        fails.append("未埋め込みフォント: " + ", ".join(sorted(not_embedded)))
    image_pages = set()
    for line in run(["pdfimages", "-list", path]).splitlines()[2:]:
        col = line.split()
        if len(col) < 14 or col[2] != "image":
            continue
        image_pages.add(int(col[0]))
        ppi = min(float(col[12]), float(col[13]))
        if col[8] in LOSSY_ENC:
            if ppi < min_ppi:
                fails.append(f"p{col[0]}: 画像 {col[3]}x{col[4]}px が {ppi:.0f}ppi（{min_ppi}ppi 未満）")
        elif ppi < min_ppi_lossless:
            fails.append(f"p{col[0]}: 可逆形式の画像 {col[3]}x{col[4]}px が {ppi:.0f}ppi（{min_ppi_lossless}ppi 未満。{RASTER_FIX}）")
    if not allow_image_only:
        for page in sorted(image_pages):
            text = run(["pdftotext", "-f", str(page), "-l", str(page), path, "-"])
            if not text.strip():
                fails.append(f"p{page}: 文字が無く画像だけのページ")
    return pages, fails, notes


def image_size(data):
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", data[16:24])
    if data[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(data):
            marker, length = data[i + 1], struct.unpack(">H", data[i + 2:i + 4])[0]
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                height, width = struct.unpack(">HH", data[i + 5:i + 9])
                return width, height
            i += 2 + length
    return None


def check_pptx(path, min_ppi, min_ppi_lossless, allow_image_only):
    fails, notes = [], []
    with zipfile.ZipFile(path) as z:
        slides = sorted(
            (n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
            key=lambda n: int(re.search(r"\d+", n.rsplit("/", 1)[1]).group()),
        )
        pres = z.read("ppt/presentation.xml").decode("utf-8", "replace")
        slide_cx = int(re.search(r'<p:sldSz[^>]*cx="(\d+)"', pres).group(1))
        for name in slides:
            no = re.search(r"\d+", name.rsplit("/", 1)[1]).group()
            xml = z.read(name).decode("utf-8", "replace")
            pics = re.findall(r"<p:pic>.*?</p:pic>", xml, re.S)
            bg = re.search(r"<p:bg>.*?</p:bg>", xml, re.S)
            bg_rid = re.search(r'r:embed="([^"]+)"', bg.group(0)) if bg else None
            if (pics or bg_rid) and "<a:t>" not in xml and not allow_image_only:
                fails.append(f"slide{no}: 文字が無く画像だけのスライド")
            rels_name = f"ppt/slides/_rels/slide{no}.xml.rels"
            rels = z.read(rels_name).decode() if rels_name in z.namelist() else ""
            targets = dict(re.findall(r'Id="([^"]+)"[^>]*?Target="([^"]+)"', rels))
            targets.update({i: t for t, i in re.findall(r'Target="([^"]+)"[^>]*?Id="([^"]+)"', rels)})
            placed = [(re.search(r'r:embed="([^"]+)"', pic), re.search(r'<a:ext cx="(\d+)" cy="(\d+)"', pic)) for pic in pics]
            if bg_rid:
                placed.append((bg_rid, re.match(r"(\d+)", str(slide_cx))))
            for rid, ext in placed:
                if not rid or not ext or rid.group(1) not in targets:
                    continue
                media = normpath(join(dirname(name), targets[rid.group(1)]))
                if media.lower().endswith((".svg", ".emf", ".wmf")) or media not in z.namelist():
                    continue
                data = z.read(media)
                size = image_size(data)
                if not size or not int(ext.group(1)):
                    notes.append(f"slide{no}: {media} の大きさを読めず未検査")
                    continue
                ppi = size[0] / (int(ext.group(1)) / EMU_PER_INCH)
                if data[:2] == b"\xff\xd8":
                    if ppi < min_ppi:
                        fails.append(f"slide{no}: 画像 {size[0]}x{size[1]}px が {ppi:.0f}ppi（{min_ppi}ppi 未満）")
                elif ppi < min_ppi_lossless:
                    fails.append(f"slide{no}: 可逆形式の画像 {size[0]}x{size[1]}px が {ppi:.0f}ppi（{min_ppi_lossless}ppi 未満。{RASTER_FIX}）")
    return len(slides), fails, notes


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--min-ppi", type=int, default=200, help="写真（JPEG）の下限")
    ap.add_argument("--min-ppi-lossless", type=int, default=288, help="可逆形式（PNG など。スクリーンショット・図版）の下限")
    ap.add_argument("--allow-image-only", action="store_true")
    args = ap.parse_args()
    failed = False
    for path in args.files:
        lower = path.lower()
        try:
            if lower.endswith(".pdf"):
                count, fails, notes = check_pdf(path, args.min_ppi, args.min_ppi_lossless, args.allow_image_only)
            elif lower.endswith(".pptx"):
                count, fails, notes = check_pptx(path, args.min_ppi, args.min_ppi_lossless, args.allow_image_only)
            else:
                print(f"SKIP {path}: pdf / pptx 以外")
                continue
        except (OSError, subprocess.CalledProcessError, zipfile.BadZipFile) as err:
            print(f"ERROR {path}: 検査できない（{err}）")
            failed = True
            continue
        print(f"{'FAIL' if fails else 'OK'} {path}（{count} ページ）")
        for line in fails:
            print(f"  NG   {line}")
        for line in notes:
            print(f"  NOTE {line}")
        failed = failed or bool(fails)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
