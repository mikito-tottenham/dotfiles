#!/bin/sh
# opmaterialize Document → Secure Note フィールド 移行スクリプト
# ローカルマシン（個人 1Password 認証済み）で実行する
# Usage: sh .context/opmaterialize-field-migration/02-migrate-local.sh
set -eu

VAULT="${OP_DOTFILES_MATERIALIZE_VAULT:-Dotfiles Secrets}"
MANIFEST_ITEM="${OP_DOTFILES_MATERIALIZE_ITEM:-Secrets Manifest}"
WORK_DIR="${TMPDIR:-/tmp}/opmaterialize-migrate-$$"
mkdir -p "$WORK_DIR"
trap 'rm -rf "$WORK_DIR"' EXIT

log() { printf '[%s] %s\n' "$(date '+%H:%M:%S')" "$*"; }
die() { log "ERROR: $*" >&2; exit 1; }

log "=== opmaterialize 移行開始 vault=$VAULT ==="

# 1. 認証確認
log "1. 1Password 認証確認..."
op account get >/dev/null || die "op account get 失敗。eval \$(op signin) を実行してから再試行してください"
log "   OK"

# 2. 現在のマニフェストをダウンロード
log "2. マニフェストダウンロード (Document)..."
manifest_tsv="$WORK_DIR/manifest.tsv"
op document get "$MANIFEST_ITEM" --vault "$VAULT" --out-file "$manifest_tsv" --file-mode 0600 --force
log "   OK - 内容:"
cat "$manifest_tsv" | sed 's/^/     /'
echo ""

# 3. 各 document エントリを Secure Note に変換
log "3. Document → Secure Note 変換..."
new_manifest="$WORK_DIR/new-manifest.tsv"
printf '# type\titem\tout_path\tmode\tvault\n' > "$new_manifest"

while IFS="$(printf '\t')" read -r kind item out_path file_mode vault rest; do
  case "${kind:-}" in ''|'#'*) continue ;; esac

  log "   処理中: type=$kind item=$item"

  if [ "$kind" = "document" ]; then
    content_tmp="$WORK_DIR/content-$(printf '%s' "$item" | tr '/' '_').dat"
    log "   ダウンロード中: $item"
    op document get "$item" --vault "$vault" --out-file "$content_tmp" --file-mode 0600 --force

    # Secure Note が既存かチェック
    if op item get "$item" --vault "$vault" --fields "content" >/dev/null 2>&1; then
      log "   Secure Note 更新: $item"
      op item edit "$item" --vault "$vault" "content[text]=$(cat "$content_tmp")" >/dev/null
    elif op item get "$item" --vault "$vault" >/dev/null 2>&1; then
      # 既存は Document → アーカイブして Secure Note を新規作成
      log "   Document アーカイブ: $item"
      op item delete "$item" --vault "$vault" --archive >/dev/null
      log "   Secure Note 作成: $item"
      op item create --category "Secure Note" --title "$item" --vault "$vault" "content[text]=$(cat "$content_tmp")" >/dev/null
    else
      log "   Secure Note 新規作成: $item"
      op item create --category "Secure Note" --title "$item" --vault "$vault" "content[text]=$(cat "$content_tmp")" >/dev/null
    fi
    rm -f "$content_tmp"
    printf 'field\t%s\t%s\t%s\t%s\n' "$item" "$out_path" "$file_mode" "$vault" >> "$new_manifest"
  else
    printf '%s\t%s\t%s\t%s\t%s\n' "$kind" "$item" "$out_path" "$file_mode" "$vault" >> "$new_manifest"
  fi
done < "$manifest_tsv"

log "   変換後マニフェスト:"
cat "$new_manifest" | sed 's/^/     /'
echo ""

# 4. マニフェスト Secure Note を作成（既存 Document マニフェストはアーカイブ）
log "4. マニフェスト Secure Note 作成..."
notes_content="$(cat "$new_manifest")"

manifest_id=$(op item list --vault "$VAULT" --categories Document --format json 2>/dev/null \
  | python3 -c "import sys,json; items=[i for i in json.load(sys.stdin) if i['title']=='$MANIFEST_ITEM']; print(items[0]['id'] if items else '')" 2>/dev/null || echo "")

if [ -n "$manifest_id" ]; then
  log "   既存 Document マニフェストをアーカイブ: $manifest_id"
  op item delete "$manifest_id" --vault "$VAULT" --archive >/dev/null
fi

log "   Secure Note マニフェスト作成..."
op item create --category "Secure Note" --title "$MANIFEST_ITEM" --vault "$VAULT" "notesPlain=$notes_content" >/dev/null
log "   OK"

# 5. 検証
log "5. 検証..."
result=$(op read "op://${VAULT}/${MANIFEST_ITEM}/notesPlain" 2>&1)
if echo "$result" | grep -q "field"; then
  log "   op read による Secure Note マニフェスト読み取り: OK"
else
  die "Secure Note マニフェスト読み取り失敗: $result"
fi

log ""
log "=== 移行完了 ==="
log "次のステップ（Claude セッションで実行）:"
log "  opmaterialize restore"
log "  gws-as ges-claude drive files list"
