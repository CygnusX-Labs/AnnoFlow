#!/usr/bin/env python3
# *---utf-8---*
"""
AnnoFlow Input MD5 Checker
===========================
输入蛋白序列 MD5 校验门控（Flow framework §4.5 格式）：
CheckTime  SampleName  FilePath  ExpectedMD5  ActualMD5  Status  Message

- input_dir 下用户提供 md5.txt 时逐文件比对，任一 FAIL → 退出码 1（流程中止）
- 无期望 MD5 时计算并记录基线，标记 PASS（SRA 兼容原则，§4.2）
- 输入文件缺失 → FAIL 并退出码 1（fail-fast）
"""

import argparse
import hashlib
import os
import sys
from datetime import datetime

INPUT_EXTENSIONS = (".pep", ".fa", ".fasta", ".faa", ".protein")


def find_input_file(input_dir, sample):
    for ext in INPUT_EXTENSIONS:
        if sample.endswith(ext):
            path = os.path.join(input_dir, sample)
            if os.path.exists(path):
                return path
    for ext in INPUT_EXTENSIONS:
        path = os.path.join(input_dir, f"{sample}{ext}")
        if os.path.exists(path):
            return path
    import glob

    for ext in INPUT_EXTENSIONS:
        candidates = glob.glob(os.path.join(input_dir, f"{sample}*{ext}"))
        if candidates:
            return sorted(candidates)[0]
    return os.path.join(input_dir, f"{sample}.pep")


def md5sum(path, chunk_size=1 << 20):
    h = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def load_expected_md5(md5_file, input_dir):
    expected = {}
    if not md5_file:
        return expected
    with open(md5_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            if len(parts) != 2:
                continue
            digest, name = parts[0].strip(), parts[1].strip()
            expected[os.path.basename(name)] = digest
    return expected


def main():
    parser = argparse.ArgumentParser(description="AnnoFlow input MD5 gate")
    parser.add_argument("--samples", nargs="+", required=True)
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--md5-file", default="")
    args = parser.parse_args()

    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    expected = load_expected_md5(args.md5_file, args.input_dir)

    rows = []
    failed = False

    for sample in args.samples:
        path = find_input_file(args.input_dir, sample)
        basename = os.path.basename(path)

        if not os.path.exists(path):
            rows.append((now, sample, path, expected.get(basename, ""), "", "FAIL", "input file not found"))
            failed = True
            continue

        actual = md5sum(path)
        exp = expected.get(basename)
        if exp:
            status = "PASS" if exp.lower() == actual.lower() else "FAIL"
            message = "" if status == "PASS" else "MD5 mismatch"
        else:
            status = "PASS"
            message = "no expected MD5, baseline recorded"
        if status == "FAIL":
            failed = True
        rows.append((now, sample, path, exp or "", actual, status, message))

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write("CheckTime\tSampleName\tFilePath\tExpectedMD5\tActualMD5\tStatus\tMessage\n")
        for row in rows:
            f.write("\t".join(row) + "\n")

    n_pass = sum(1 for r in rows if r[5] == "PASS")
    n_fail = sum(1 for r in rows if r[5] == "FAIL")
    print(f"[input_md5_check] PASS: {n_pass}, FAIL: {n_fail} -> {args.output}")

    if failed:
        print("[input_md5_check] ERROR: input validation failed, aborting downstream.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
