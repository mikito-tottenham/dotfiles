#!/bin/sh
# PPTX を PDF に書き出し、pdftoppm で slide-NN.jpg を作る（検品用）。
#
# usage: render_pptx.sh <deck.pptx> [keynote|soffice]
#   出力: <deck のディレクトリ>/render/deck.pdf と slide-NN.jpg
#   engine の既定は macOS で keynote、それ以外で soffice。
#
# - keynote: 書体・行送りは Keynote の近似。Keynote はサンドボックス外のパスを開けないため、
#   Keynote のコンテナ内にコピーしてから開く（macOS 専用）。PowerPoint の AppleScript open は
#   ファイルアクセス許可ダイアログで止まるので使わない（2026-09-11 実測）。
# - soffice: LibreOffice の headless 変換。日本語フォントが無い環境では代替フォントで描画される。
#
# 取り込み元: 業務 repo の bin/pptx-render-keynote.sh。
set -eu

if [ "$#" -lt 1 ]; then
  echo "usage: render_pptx.sh <deck.pptx> [keynote|soffice]" >&2
  exit 64
fi

IN="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
OUTDIR="$(dirname "$IN")/render"
if [ "$(uname)" = "Darwin" ]; then default_engine=keynote; else default_engine=soffice; fi
ENGINE="${2:-$default_engine}"

command -v pdftoppm >/dev/null 2>&1 || { echo "pdftoppm がありません（poppler を導入）" >&2; exit 127; }
mkdir -p "$OUTDIR"
rm -f "$OUTDIR"/deck.pdf "$OUTDIR"/slide-*.jpg
echo "[start] engine=$ENGINE in=$IN"

case "$ENGINE" in
  keynote)
    KBOX="$HOME/Library/Containers/com.apple.iWork.Keynote/Data/tmp/render"
    mkdir -p "$KBOX"
    rm -f "$KBOX"/deck.pptx "$KBOX"/deck.pdf
    cp "$IN" "$KBOX/deck.pptx"
    osascript - "$KBOX/deck.pptx" "$KBOX/deck.pdf" <<'AS'
on run argv
  set inPath to item 1 of argv
  set outPath to item 2 of argv
  with timeout of 180 seconds
    tell application "Keynote"
      set d to open (POSIX file inPath)
      export d to (POSIX file outPath) as PDF
      close d saving no
    end tell
  end timeout
end run
AS
    cp "$KBOX/deck.pdf" "$OUTDIR/deck.pdf"
    ;;
  soffice)
    SOFFICE="$(command -v soffice || command -v libreoffice || true)"
    [ -z "$SOFFICE" ] && [ -x /Applications/LibreOffice.app/Contents/MacOS/soffice ] && SOFFICE=/Applications/LibreOffice.app/Contents/MacOS/soffice
    [ -n "$SOFFICE" ] || { echo "soffice がありません（LibreOffice を導入）" >&2; exit 127; }
    "$SOFFICE" --headless --convert-to pdf --outdir "$OUTDIR" "$IN" >/dev/null
    mv "$OUTDIR/$(basename "${IN%.*}").pdf" "$OUTDIR/deck.pdf"
    ;;
  *)
    echo "unknown engine: $ENGINE" >&2
    exit 64
    ;;
esac

echo "[pdf] $OUTDIR/deck.pdf ($(wc -c <"$OUTDIR/deck.pdf" | tr -d ' ') bytes)"
pdftoppm -jpeg -r 110 "$OUTDIR/deck.pdf" "$OUTDIR/slide"
ls -1 "$OUTDIR"/slide-*.jpg
echo "[done]"
