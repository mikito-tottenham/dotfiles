#!/usr/bin/env python3
"""認証経路の読み取り専用 preflight。

1Password / GitHub (ghrun) / Google Workspace (gws-account) / Slack (slack-account) の
状態だけを確認し、秘密値・メールアドレス・op:// reference は出力しない。

既定では 1Password の認可（Touch ID）を誘発しうる操作を実行しない:
  - `op` サブコマンド（`op whoami` を含む。2026-10-03 に応答待ちで 15 秒 timeout した実測がある）
  - `oprun ...`（`op run` 経由の token 解決）
これらは `--with-op` を付けたときだけ実行する。

既定で実行するもの（いずれも Touch ID を伴わない）:
  - コマンドの存在確認、ファイルの存在と permission 確認、`ssh -G` の設定解決
  - `ghrun gh api user`（materialize 済み token を読むだけ）
  - `gws-account <profile> auth status`（ネットワークで token の有効性を確認する）
ネットワークも避けたいときは `--offline` を付ける。

usage:
  auth_preflight.py [--only op,gh,gws,slack] [--profile <gws-profile> ...]
                    [--with-op] [--offline] [--json-out <path>]
exit code: 0 = FAIL なし / 1 = FAIL あり / 2 = 使い方エラー
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path

HOME = Path.home()
OP_ENV_FILE = Path(os.environ.get("OP_DOTFILES_ENV_FILE", HOME / ".config/op/dotfiles.env"))
GH_ENV_FILE = Path(os.environ.get("GH_TOKEN_ENV_FILE", HOME / ".config/op/injected/github.env"))
GWS_ACCOUNTS_DIR = HOME / ".config/gws/accounts"
OP_SSH_SOCK = HOME / "Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock"
AREAS = ("op", "gh", "gws", "slack")

# 出力前に必ず通す伏せ字ルール（メール・token 形式・op:// reference）
REDACTIONS = [
    (re.compile(r"op://\S+"), "op://<redacted>"),
    (re.compile(r"\b(xox[abposr]-[A-Za-z0-9-]+)"), "<slack-token>"),
    (re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{10,}|github_pat_[A-Za-z0-9_]{10,})"), "<github-token>"),
    (re.compile(r"\bya29\.[A-Za-z0-9._-]+"), "<google-token>"),
    (re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})"), r"<user>@\1"),
]

T0 = time.monotonic()
RESULTS: list[dict] = []


def redact(text: str) -> str:
    for pattern, repl in REDACTIONS:
        text = pattern.sub(repl, text)
    return text


def log(msg: str) -> None:
    print(f"[{time.monotonic() - T0:6.1f}s] {redact(msg)}", flush=True)


def record(area: str, check: str, status: str, detail: str, action: str = "") -> None:
    item = {"area": area, "check": check, "status": status, "detail": redact(detail), "action": redact(action)}
    RESULTS.append(item)
    log(f"{status:<4} {area}/{check}: {item['detail']}" + (f" -> {item['action']}" if action else ""))


def run(cmd: list[str], timeout: int) -> tuple[int | None, str, str]:
    """コマンドを実行し (rc, stdout, stderr) を返す。timeout は rc=None。出力は呼び出し側で解析し、生では表示しない。"""
    try:
        cp = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
        return cp.returncode, cp.stdout, cp.stderr
    except subprocess.TimeoutExpired:
        return None, "", f"timeout after {timeout}s"
    except FileNotFoundError:
        return 127, "", "command not found"


def first_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip() and not line.startswith(("gws-account:", "Using keyring", "slack-account:")):
            return line.strip()[:160]
    return ""


def env_keys(path: Path) -> dict[str, bool]:
    """KEY=VALUE のキー名と「値が op:// reference か」だけを返す。値そのものは保持しない。"""
    keys: dict[str, bool] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        keys[key.strip()] = value.strip().strip("'\"").startswith("op://")
    return keys


# ---------------------------------------------------------------- 1Password
def check_op(with_op: bool) -> None:
    log("start area=op")
    if shutil.which("op"):
        rc, out, _ = run(["op", "--version"], 10)
        record("op", "cli", "OK" if rc == 0 else "WARN", f"op {out.strip() or '(version 不明)'}")
    else:
        record("op", "cli", "FAIL", "op が PATH に無い", "1Password CLI を導入する（brew install 1password-cli）")

    if sys.platform == "darwin":
        rc, _, _ = run(["pgrep", "-x", "1Password"], 5)
        if rc == 0:
            record("op", "app", "OK", "1Password アプリが起動している（ロック状態はこの検査では判別しない）")
        else:
            record("op", "app", "WARN", "1Password アプリのプロセスが見つからない", "ユーザーに 1Password アプリの起動とロック解除を依頼する")

    if OP_ENV_FILE.is_file():
        keys = env_keys(OP_ENV_FILE)
        non_ref = sorted(k for k, is_ref in keys.items() if not is_ref)
        if non_ref:
            record("op", "dotfiles.env", "FAIL", f"op:// 以外の値を持つキー: {', '.join(non_ref)}",
                   "実値をファイルから除き op:// reference だけにする（ユーザー作業）")
        else:
            record("op", "dotfiles.env", "OK", f"{len(keys)} キー、すべて op:// reference")
    else:
        record("op", "dotfiles.env", "WARN", f"{OP_ENV_FILE} が無い",
               "dot_config/private_op/dotfiles.env.example を元にユーザーが作成する（oprun / slack-account が使えない）")

    if sys.platform == "darwin":
        sock = "present" if OP_SSH_SOCK.exists() else "absent"
        rc, out, _ = run(["ssh", "-G", "github.com"], 10)
        agent = next((l.split(None, 1)[1] for l in out.splitlines() if l.lower().startswith("identityagent ")), "")
        uses_op_agent = "1password" in agent.lower()
        if sock == "present" and uses_op_agent:
            record("op", "ssh-agent", "OK", "1Password SSH agent の socket があり、ssh 設定が参照している")
        else:
            record("op", "ssh-agent", "WARN",
                   f"agent.sock={sock}, ssh -G github.com の identityagent={'1Password' if uses_op_agent else (agent or 'なし')}",
                   "SSH が必要な作業だけ問題になる。1Password 設定の SSH エージェント有効化と ~/.ssh/config の chezmoi 適用をユーザーに確認する（ADR-0055）")

    if not with_op:
        record("op", "signin", "SKIP", "op whoami は既定で実行しない（--with-op で実行）")
        return
    rc, out, err = run(["op", "whoami"], 15)
    if rc == 0:
        record("op", "signin", "OK", "op whoami 成功（アカウント情報は表示しない）")
    elif rc is None:
        record("op", "signin", "WARN", "op whoami が 15 秒で応答しない",
               "1Password アプリのロック解除と CLI 統合の有効化をユーザーに確認する")
    else:
        msg = first_line(err) or first_line(out)
        record("op", "signin", "WARN", f"op whoami rc={rc}: {msg}",
               "デスクトップ統合では未認可の間 not signed in になる。認証が必要な操作の直前に op-cli-runner 経由で確認する")


# ---------------------------------------------------------------- GitHub
def check_gh(offline: bool) -> None:
    log("start area=gh")
    if not shutil.which("ghrun"):
        record("gh", "ghrun", "FAIL", "ghrun が PATH に無い", "dotfiles の dot_local/bin/ghrun を chezmoi apply する（ユーザー作業）")
        return
    if not GH_ENV_FILE.is_file():
        record("gh", "token-file", "FAIL", f"{GH_ENV_FILE} が無い", "ユーザーに通常のターミナルで `ghrun --refresh` を実行してもらう")
        return
    mode = stat.S_IMODE(GH_ENV_FILE.stat().st_mode)
    age_days = (time.time() - GH_ENV_FILE.stat().st_mtime) / 86400
    record("gh", "token-file", "OK" if mode == 0o600 else "WARN",
           f"materialize 済み（mode={oct(mode)}, 更新 {age_days:.0f} 日前）",
           "" if mode == 0o600 else "chmod 600 にする")
    if offline:
        record("gh", "api", "SKIP", "--offline のため API 確認を省略")
        return
    rc, out, err = run(["ghrun", "gh", "api", "user", "--jq", ".login"], 20)
    if rc == 0 and out.strip():
        record("gh", "api", "OK", f"GitHub API 認証 OK（login={out.strip()}）")
    elif rc is None:
        record("gh", "api", "WARN", "GitHub API が 20 秒で応答しない", "ネットワークを確認する")
    elif "401" in err or "Bad credentials" in err:
        record("gh", "api", "FAIL", "401 Bad credentials（token 失効またはローテーション後）",
               "Agent から再生成しない。ユーザーに通常のターミナルで `ghrun --refresh` を依頼する")
    else:
        record("gh", "api", "WARN", f"rc={rc}: {first_line(err)}")


# ---------------------------------------------------------------- Google Workspace
def gws_profiles(selected: list[str]) -> list[str]:
    if selected:
        return selected
    if not GWS_ACCOUNTS_DIR.is_dir():
        return []
    names = []
    for d in sorted(GWS_ACCOUNTS_DIR.iterdir()):
        if not d.is_dir() or "." in d.name:
            continue
        has_cred = (d / "credentials.enc").is_file() or (d / "credentials.json").is_file()
        if has_cred and (d / "client_secret.json").is_file():
            names.append(d.name)
    return names


def check_gws(selected: list[str], offline: bool) -> None:
    log("start area=gws")
    if not shutil.which("gws-account"):
        record("gws", "wrapper", "FAIL", "gws-account が PATH に無い", "dotfiles の dot_local/bin/gws-account を chezmoi apply する（ユーザー作業）")
        return
    for var in ("GOOGLE_WORKSPACE_CLI_TOKEN", "GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE"):
        if os.environ.get(var):
            record("gws", "ambient-env", "FAIL", f"{var} が設定されている（wrapper が exit 78 で拒否する）", f"unset {var}")
    profiles = gws_profiles(selected)
    if not profiles:
        record("gws", "profiles", "WARN", "認証情報のそろったプロファイルが無い", "gws-cli-runner の account-profiles を参照し、ユーザーに auth login を依頼する")
        return
    log(f"gws profiles={len(profiles)}: {', '.join(profiles)}")
    for i, p in enumerate(profiles, 1):
        if offline:
            record("gws", p, "SKIP", "--offline のため auth status を省略")
            continue
        log(f"gws {i}/{len(profiles)} auth status profile={p}")
        rc, out, err = run(["gws-account", p, "auth", "status"], 30)
        if rc is None:
            record("gws", p, "WARN", "auth status が 30 秒で応答しない", "ネットワークを確認する")
            continue
        if rc == 66:
            record("gws", p, "FAIL", "認証情報が無い（wrapper exit 66）", f"ユーザーに `gws-account {p} auth login` を依頼する")
            continue
        try:
            data = json.loads(out[out.index("{"):])
        except (ValueError, json.JSONDecodeError):
            record("gws", p, "WARN", f"auth status を解析できない rc={rc}: {first_line(err)}")
            continue
        domain = str(data.get("user", "")).rpartition("@")[2] or "不明"
        if data.get("token_valid"):
            record("gws", p, "OK", f"token_valid=true domain={domain}")
        else:
            reason = str(data.get("token_error") or data.get("error") or "")
            hint = "invalid_rapt" if "invalid_rapt" in json.dumps(data) else (reason[:80] or "token_valid=false")
            record("gws", p, "FAIL", f"token 無効 domain={domain} ({hint})",
                   f"ユーザーに `gws-account {p} auth login` をフォアグラウンドで依頼し、選ぶアカウントのドメインが {domain} であることを伝える")


# ---------------------------------------------------------------- Slack
def check_slack(with_op: bool) -> None:
    log("start area=slack")
    if not shutil.which("slack-account"):
        record("slack", "cli", "FAIL", "slack-account が PATH に無い", "dotfiles の dot_local/bin/slack-account を chezmoi apply する（ユーザー作業）")
        return
    if not OP_ENV_FILE.is_file():
        record("slack", "profiles", "WARN", "dotfiles.env が無いため slack-account のプロファイルを解決できない")
        return
    keys = env_keys(OP_ENV_FILE)
    profiles = sorted({m.group(1).lower().replace("_", "-") for k in keys
                       if (m := re.fullmatch(r"SLACK_([A-Z0-9_]+?)_TOKEN", k)) and not m.group(1).endswith("_BOT")})
    record("slack", "profiles", "OK" if profiles else "WARN",
           f"dotfiles.env に定義された slack-account プロファイル: {', '.join(profiles) or 'なし'}"
           "（MCP コネクタ経由のワークスペースはこの script では検査しない）")
    for p in profiles:
        if not with_op:
            record("slack", p, "SKIP", "oprun は Touch ID を伴うため既定で実行しない（--with-op で auth status を実行）")
            continue
        log(f"slack auth status profile={p} (oprun)")
        rc, out, err = run(["oprun", "slack-account", p, "auth", "status", "--json"], 60)
        if rc == 0:
            try:
                data = json.loads(out)
                record("slack", p, "OK", f"auth.test ok team={data.get('team', '?')} token_type={data.get('token_type', '?')}")
            except json.JSONDecodeError:
                record("slack", p, "OK", "auth status exit 0")
        elif rc is None:
            record("slack", p, "WARN", "60 秒で応答しない（Touch ID 待ちの可能性）", "ユーザーに 1Password の承認状況を確認する")
        elif rc == 1:
            record("slack", p, "FAIL", f"設定エラー exit 1: {first_line(err)}", "dotfiles.env の当該キーと 1Password 項目をユーザーに確認する")
        elif rc == 2:
            record("slack", p, "FAIL", f"Slack API ok:false: {first_line(err) or first_line(out)}",
                   "invalid_auth / token_revoked なら Slack App の token 再発行と 1Password 更新をユーザーに依頼する")
        else:
            record("slack", p, "WARN", f"rc={rc}: {first_line(err)}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", default=",".join(AREAS), help="検査対象（カンマ区切り: op,gh,gws,slack）")
    ap.add_argument("--profile", action="append", default=[], help="gws プロファイルを限定する（複数指定可）")
    ap.add_argument("--with-op", action="store_true", help="op whoami と oprun slack-account auth status も実行する（Touch ID を伴いうる）")
    ap.add_argument("--offline", action="store_true", help="ネットワークを使う確認（gh api / gws auth status）を省略する")
    ap.add_argument("--json-out", help="結果 JSON の保存先（.context/ 配下を推奨）")
    args = ap.parse_args()

    areas = [a.strip() for a in args.only.split(",") if a.strip()]
    unknown = [a for a in areas if a not in AREAS]
    if unknown:
        print(f"unknown area: {', '.join(unknown)}", file=sys.stderr)
        return 2

    log(f"auth-preflight start areas={','.join(areas)} with_op={args.with_op} offline={args.offline}")
    if "op" in areas:
        check_op(args.with_op)
    if "gh" in areas:
        check_gh(args.offline)
    if "gws" in areas:
        check_gws(args.profile, args.offline)
    if "slack" in areas:
        check_slack(args.with_op)

    counts = {s: sum(r["status"] == s for r in RESULTS) for s in ("OK", "WARN", "FAIL", "SKIP")}
    print("\n== summary ==")
    for r in RESULTS:
        if r["status"] in ("WARN", "FAIL"):
            print(f"{r['status']:<4} {r['area']}/{r['check']}: {r['detail']}")
            if r["action"]:
                print(f"     対処: {r['action']}")
    print("MCP コネクタ（Gmail / Calendar / Drive / Slack / Chatwork / MoneyForward）はこの script の対象外。"
          "SKILL.md の「MCP コネクタの確認」に従い、エージェントが読み取りツールで確認する。")
    log(f"done OK={counts['OK']} WARN={counts['WARN']} FAIL={counts['FAIL']} SKIP={counts['SKIP']}")

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"counts": counts, "results": RESULTS}, ensure_ascii=False, indent=1), encoding="utf-8")
        log(f"wrote {out}")
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
