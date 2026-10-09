#!/usr/bin/env python3
# *---utf-8---*
"""
AnnoFlow Delivery Tool
======================
copy 模式交付（Flow framework §6.4）：
- 复制 workflow 内分析产物到 data_deliver/annotation/<相对路径>
- 生成 delivery_manifest.json（含 source / delivered_path / size_bytes / md5 / action）
- 生成 delivery_manifest.md5 与 delivery_details.log
- 目录型产物计入 manifest（禁止静默跳过，§6.4）
"""

import argparse
import datetime
import hashlib
import json
import os
import shutil
import sys


def md5sum(path, chunk_size=1 << 20):
    h = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description="AnnoFlow deliver (copy mode)")
    parser.add_argument("--inputs", nargs="+", required=True, help="workflow-relative deliverable paths")
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--target-dir", required=True)
    parser.add_argument("--pipeline", default="AnnoFlow")
    parser.add_argument("--project", default="unknown_project")
    args = parser.parse_args()

    deliver_root = os.path.join(args.target_dir, "annotation")
    os.makedirs(deliver_root, exist_ok=True)

    files = []
    skipped = []

    for rel in args.inputs:
        rel = str(rel)
        src = rel if os.path.isabs(rel) else os.path.join(args.source_dir, rel)

        if not os.path.exists(src):
            skipped.append((rel, "not found"))
            continue

        if os.path.isdir(src):
            for dirpath, _, filenames in os.walk(src):
                for name in filenames:
                    files.append(os.path.join(dirpath, name))
            continue

        files.append(src)

    manifest_files = []
    details_lines = []

    for src in files:
        rel = os.path.relpath(src, args.source_dir)
        dst = os.path.join(deliver_root, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        digest = md5sum(dst)
        size = os.path.getsize(dst)
        manifest_files.append(
            {
                "source": rel,
                "delivered_path": os.path.relpath(dst, args.target_dir),
                "size_bytes": size,
                "md5": digest,
                "action": "copy",
            }
        )
        details_lines.append(f"{digest}  {dst}")
        print(f"[deliver] {rel} -> {dst} ({size} bytes)")

    manifest = {
        "pipeline": args.pipeline,
        "project_name": args.project,
        "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "mode": "copy",
        "files": manifest_files,
    }

    manifest_path = os.path.join(args.target_dir, "delivery_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    md5_path = os.path.join(args.target_dir, "delivery_manifest.md5")
    with open(md5_path, "w", encoding="utf-8") as f:
        f.write("\n".join(details_lines) + "\n")

    log_path = os.path.join(args.target_dir, "delivery_details.log")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"AnnoFlow delivery log - {manifest['created_at']}\n")
        f.write(f"source: {args.source_dir}\n")
        f.write(f"target: {args.target_dir}\n")
        f.write(f"delivered: {len(manifest_files)} files\n")
        for rel, reason in skipped:
            f.write(f"SKIPPED {rel}: {reason}\n")

    if skipped:
        print(f"[deliver] WARNING: {len(skipped)} inputs skipped (see delivery_details.log)", file=sys.stderr)

    print(f"[deliver] {len(manifest_files)} files delivered. manifest: {manifest_path}")


if __name__ == "__main__":
    main()
