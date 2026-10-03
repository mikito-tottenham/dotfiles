#!/usr/bin/env python3
"""List the children of a Drive folder (to confirm folder conventions before planning). Read-only.

usage: drive_ls.py --profile <gws-profile> --folder-id <id|root> [--drive-id <shared-drive-id>] [--filter <substring>]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gws_common import gws  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", required=True)
    ap.add_argument("--folder-id", required=True)
    ap.add_argument("--drive-id")
    ap.add_argument("--filter")
    args = ap.parse_args()

    params = {"includeItemsFromAllDrives": True, "supportsAllDrives": True, "pageSize": 200,
              "q": f"'{args.folder_id}' in parents and trashed=false",
              "fields": "files(id,name,mimeType,modifiedTime,webViewLink)"}
    if args.drive_id:
        params.update(corpora="drive", driveId=args.drive_id)
    for x in gws(args.profile, ["drive", "files", "list", "--params", json.dumps(params)]).get("files", []):
        if args.filter and args.filter not in x["name"]:
            continue
        kind = "DIR" if x["mimeType"].endswith("folder") else x["mimeType"].split("/")[-1].split(".")[-1][:10]
        print(kind.ljust(10), x["modifiedTime"][:10], x["id"], x["name"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
