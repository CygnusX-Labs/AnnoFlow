#!/usr/bin/env python3
"""Export AnnoFlow merged eggNOG annotations into an RNAFlow-ready table.

Outputs:
  - rnaflow_annotation.tsv: one row per query with the columns RNAFlow's
    annotation_to_enrichment.py consumes (query / gos / kegg_pathway),
    plus description / ec / kegg_ko / confidence for interpretation.
  - kegg_pathway_names.tsv: ko##### pathway id -> KEGG pathway name.
    Resolved from a local cache file first, then the KEGG REST API
    (https://rest.kegg.jp/list/pathway/ko); when both are unavailable the
    file is still written with an empty mapping and a warning is emitted.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import urllib.request
from pathlib import Path

KEGG_REST_PATHWAY_KO = "https://rest.kegg.jp/list/pathway/ko"
KEGG_REST_PATHWAY_MAP = "https://rest.kegg.jp/list/pathway"
PATHWAY_RE = re.compile(r"^ko\d{5}$")

# ko 通路已被 KEGG 官方删除/合并（见 https://www.genome.jp/kegg/docs/upd_map.html），
# 但旧版 eggNOG 数据库仍会注释到这些 ID；保留历史名称以便解读。
RETIRED_PATHWAYS = {
    "ko00072": "Synthesis and degradation of ketone bodies (retired by KEGG, merged into ko00650)",
    "ko00281": "Geraniol degradation (retired by KEGG, merged into ko00907)",
    "ko00471": "D-Glutamine and D-glutamate metabolism (retired by KEGG, merged into ko00470)",
    "ko01058": "Acridone alkaloid biosynthesis (retired by KEGG, merged into ko00996)",
    "ko01130": "Biosynthesis of antibiotics (retired by KEGG, merged into ko01110)",
}
OUT_COLUMNS = [
    "query", "description", "ec", "gos", "kegg_ko", "kegg_pathway",
    "confidence_level", "confidence_score",
]


def parse_name_list(text: str) -> dict:
    mapping = {}
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) == 2 and parts[0].strip():
            mapping[parts[0].strip().removeprefix("path:")] = parts[1].strip()
    return mapping


def load_pathway_names(cache: Path | None, timeout: int = 15) -> tuple[dict, str]:
    mapping: dict = {}
    source = "unavailable"
    if cache is not None and cache.exists():
        mapping = parse_name_list(cache.read_text(encoding="utf-8"))
        if mapping:
            source = f"cache: {cache}"
    if not mapping:
        try:
            # ko 级为主，map 级补充（部分通路仅有 map 条目，如 ko01062）
            texts = []
            for url in (KEGG_REST_PATHWAY_KO, KEGG_REST_PATHWAY_MAP):
                with urllib.request.urlopen(url, timeout=timeout) as resp:
                    texts.append(resp.read().decode("utf-8"))
            mapping = parse_name_list(texts[0])
            for pid, name in parse_name_list(texts[1]).items():
                mapping.setdefault(pid.replace("map", "ko", 1), name)
            if mapping:
                source = f"KEGG REST: {KEGG_REST_PATHWAY_KO}"
        except Exception as exc:  # noqa: BLE001 - offline environments must not fail the run
            print(f"[warn] cannot fetch KEGG pathway list: {exc}", file=sys.stderr)
    for pid, name in RETIRED_PATHWAYS.items():
        mapping.setdefault(pid, name)
    if mapping and source.startswith("KEGG REST") and cache is not None:
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            with cache.open("w", encoding="utf-8") as handle:
                for pid in sorted(mapping):
                    handle.write(f"{pid}\t{mapping[pid]}\n")
        except OSError as exc:
            print(f"[warn] cannot write names cache {cache}: {exc}", file=sys.stderr)
    return mapping, source


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="03.merge/eggnog_all_samples.tsv")
    parser.add_argument("--output-annotation", required=True, help="rnaflow_annotation.tsv")
    parser.add_argument("--output-names", required=True, help="kegg_pathway_names.tsv")
    parser.add_argument("--names-cache", default="", help="cached KEGG pathway name list")
    args = parser.parse_args()

    cache = Path(args.names_cache) if args.names_cache else None
    names, names_source = load_pathway_names(cache)
    print(f"pathway name source: {names_source} ({len(names)} entries)")

    rows = 0
    observed_pathways: set[str] = set()
    out_path = Path(args.output_annotation)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(args.input, newline="", encoding="utf-8-sig") as fin, \
            out_path.open("w", newline="", encoding="utf-8") as fout:
        reader = csv.DictReader(fin, delimiter="\t")
        missing = [c for c in ("query", "gos", "kegg_pathway")
                   if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"input missing required columns: {', '.join(missing)}")
        writer = csv.DictWriter(fout, fieldnames=OUT_COLUMNS, delimiter="\t",
                                extrasaction="ignore")
        writer.writeheader()
        for row in reader:
            query = (row.get("query") or "").strip()
            if not query:
                continue
            for value in re.split(r"[,;|]", row.get("kegg_pathway") or ""):
                value = value.strip()
                if PATHWAY_RE.fullmatch(value):
                    observed_pathways.add(value)
            writer.writerow(row)
            rows += 1

    names_path = Path(args.output_names)
    names_path.parent.mkdir(parents=True, exist_ok=True)
    with names_path.open("w", encoding="utf-8") as handle:
        for pid in sorted(names):
            handle.write(f"{pid}\t{names[pid]}\n")

    unnamed = sorted(observed_pathways - set(names))
    if unnamed:
        print(f"[warn] {len(unnamed)} observed pathway ids have no current KEGG name "
              f"(retired or stale database): {', '.join(unnamed)}", file=sys.stderr)
    print(f"exported {rows} queries -> {out_path}")
    print(f"pathways observed in annotation: {len(observed_pathways)}; "
          f"names written -> {names_path}")


if __name__ == "__main__":
    main()
