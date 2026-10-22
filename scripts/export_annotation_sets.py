#!/usr/bin/env python3
"""Export independent GO annotations and strict eggNOG/Kofam KO intersections."""
import argparse
import csv
from collections import defaultdict
from pathlib import Path

if __package__:
    from .annotation_terms import GO_RE, KO_RE, MISSING, clean_terms
    from .eggnog_processor import (
        AnnotationRecord, FilterThresholds, calculate_confidence_score,
        filter_record, parse_header,
    )
else:
    from annotation_terms import GO_RE, KO_RE, MISSING, clean_terms
    from eggnog_processor import (
        AnnotationRecord, FilterThresholds, calculate_confidence_score,
        filter_record, parse_header,
    )


def read_tsv(path):
    with open(path, newline="", encoding="utf-8", errors="replace") as handle:
        lines = [
            line for line in handle
            if line.strip() and not line.startswith("##")
            and (not line.startswith("#") or line.startswith("#query\t"))
        ]
    if not lines:
        return [], []
    reader = csv.DictReader(lines, delimiter="\t")
    fieldnames = [name.lstrip("#") for name in (reader.fieldnames or [])]
    rows = []
    for row in reader:
        rows.append({fieldnames[i]: value for i, value in enumerate(row.values()) if i < len(fieldnames)})
    return fieldnames, rows


def value(row, *names):
    for name in names:
        if name in row:
            return row[name]
    return ""


def parse_float(value_text, default=None):
    try:
        return float(value_text)
    except (TypeError, ValueError):
        return default


def read_eggnog_raw(path, evalue_limit, bitscore_limit):
    fields, rows = read_tsv(path)
    header_map = parse_header("\t".join(fields))
    thresholds = FilterThresholds(evalue=evalue_limit, bitscore=bitscore_limit)
    records = []
    raw_ko = defaultdict(set)
    for row in rows:
        query = value(row, "query")
        if not query:
            continue
        raw_ko[query].update(clean_terms(value(row, "KEGG_ko", "kegg_ko"), KO_RE))
        gos = clean_terms(value(row, "GOs", "gos", "GO"), GO_RE)
        if not gos:
            continue
        parsed = AnnotationRecord.from_line("\t".join(row.get(field, "") or "" for field in fields), header_map)
        for field in ("gos", "kegg_ko", "ec", "pfams", "cazy"):
            if getattr(parsed, field).strip().lower() in MISSING:
                setattr(parsed, field, "")
        parsed.confidence_level, parsed.confidence_score, _ = calculate_confidence_score(parsed, thresholds)
        records.append({
            "query": query, "gos": gos, "evalue": value(row, "evalue"),
            "bitscore": value(row, "score"), "confidence": parsed.confidence_level,
            "high": filter_record(parsed, thresholds, min_confidence="High"),
        })
    return records, raw_ko


def read_processed(path, term_column, term_pattern):
    _, rows = read_tsv(path)
    result = defaultdict(set)
    evidence = {}
    for row in rows:
        query = value(row, "query")
        if not query:
            continue
        terms = clean_terms(value(row, term_column), term_pattern)
        result[query].update(terms)
        for term in terms:
            key = (query, term)
            if key not in evidence or evidence_rank(row) < evidence_rank(evidence[key]):
                evidence[key] = row
    return result, evidence


def evidence_rank(row):
    return (parse_float(value(row, "evalue"), float("inf")),
            -parse_float(value(row, "score", "bitscore"), 0))


def write_tsv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default=".")
    parser.add_argument("--samples", nargs="+", required=True)
    parser.add_argument("--evalue", type=float, required=True)
    parser.add_argument("--bitscore", type=float, required=True)
    parser.add_argument("--output-dir", default="03.merge")
    args = parser.parse_args()
    base, out = Path(args.input_dir), Path(args.output_dir)
    go_rows, go_high_rows, go_long, go_high_long = [], [], [], []
    shared_rows, shared_high_rows, shared_long, shared_high_long = [], [], [], []
    stats = []

    for sample in args.samples:
        raw, raw_ko = read_eggnog_raw(base / "01.eggnog" / f"{sample}.emapper.annotations", args.evalue, args.bitscore)
        go_map = defaultdict(set)
        best = {}
        best_high = {}
        high_map = defaultdict(set)
        for record in raw:
            query = record["query"]
            go_map[query].update(record["gos"])
            if record["high"]:
                high_map[query].update(record["gos"])
            for term in record["gos"]:
                key = (query, term)
                if key not in best or evidence_rank(record) < evidence_rank(best[key]):
                    best[key] = record
                if record["high"] and (key not in best_high or evidence_rank(record) < evidence_rank(best_high[key])):
                    best_high[key] = record
        for query in sorted(go_map):
            terms = sorted(go_map[query])
            go_rows.append({"sample": sample, "query": query, "go_terms": ";".join(terms), "source": "eggNOG-mapper raw annotations"})
            for term in terms:
                record = best[(query, term)]
                go_long.append({"sample": sample, "query": query, "go_term": term, "source": "eggNOG-mapper raw annotations", "evalue": record["evalue"], "bitscore": record["bitscore"], "confidence": record["confidence"]})
        for query in sorted(high_map):
            terms = sorted(high_map[query])
            go_high_rows.append({"sample": sample, "query": query, "go_terms": ";".join(terms), "source": "eggNOG-mapper raw annotations"})
            for term in terms:
                record = best_high[(query, term)]
                go_high_long.append({"sample": sample, "query": query, "go_term": term, "source": "eggNOG-mapper raw annotations", "evalue": record["evalue"], "bitscore": record["bitscore"], "confidence": record["confidence"]})

        egg, egg_ev = read_processed(base / "01.eggnog" / f"{sample}_eggnog.tsv", "kegg_ko", KO_RE)
        kof, kof_ev = read_processed(base / "02.kofam" / f"{sample}_kofam.tsv", "KO", KO_RE)
        egg_high, egg_high_ev = read_processed(base / "01.eggnog" / f"{sample}_eggnog_highconf.tsv", "kegg_ko", KO_RE)
        kof_high, kof_high_ev = read_processed(base / "02.kofam" / f"{sample}_kofam_highconf.tsv", "KO", KO_RE)
        queries = sorted(set(egg) | set(kof))
        for query in queries:
            shared = sorted(egg[query] & kof[query])
            high_shared = sorted(egg_high[query] & kof_high[query])
            for terms, target, long_target, egg_evidence, kof_evidence in (
                (shared, shared_rows, shared_long, egg_ev, kof_ev),
                (high_shared, shared_high_rows, shared_high_long, egg_high_ev, kof_high_ev),
            ):
                if terms:
                    target.append({"sample": sample, "query": query, "shared_ko": ";".join(terms), "eggnog_ko": ";".join(sorted(egg[query])), "kofam_ko": ";".join(sorted(kof[query]))})
                for ko in terms:
                    erow, krow = egg_evidence[(query, ko)], kof_evidence[(query, ko)]
                    long_target.append({"sample": sample, "query": query, "shared_ko": ko, "eggnog_ko": ";".join(sorted(egg[query])), "kofam_ko": ";".join(sorted(kof[query])), "eggnog_confidence": value(erow, "confidence_level"), "kofam_confidence": value(krow, "confidence_level"), "eggnog_evalue": value(erow, "evalue"), "eggnog_bitscore": value(erow, "score", "bitscore"), "kofam_score": value(krow, "score"), "kofam_threshold": value(krow, "kofam_threshold", "threshold")})
        both = {q for q in queries if egg[q] and kof[q]}
        shared_proteins = {q for q in queries if egg[q] & kof[q]}
        high_pairs = sum(len(egg_high[q] & kof_high[q]) for q in queries)
        stats.append({"sample": sample, "go_proteins": len(go_map), "go_highconf_proteins": len(high_map), "go_terms": len({t for terms in go_map.values() for t in terms}), "go_pairs": sum(len(v) for v in go_map.values()), "go_only_no_kegg_proteins": len({q for q in go_map if not raw_ko[q]}), "eggnog_ko_proteins": sum(bool(v) for v in egg.values()), "kofam_ko_proteins": sum(bool(v) for v in kof.values()), "both_ko_proteins": len(both), "shared_ko_proteins": len(shared_proteins), "both_ko_empty_intersection": len(both - shared_proteins), "shared_pairs": sum(len(egg[q] & kof[q]) for q in queries), "shared_kos": len({ko for q in queries for ko in egg[q] & kof[q]}), "high_shared_proteins": len({q for q in queries if egg_high[q] & kof_high[q]}), "high_shared_pairs": high_pairs})

    go_fields = ["sample", "query", "go_terms", "source"]
    go_long_fields = ["sample", "query", "go_term", "source", "evalue", "bitscore", "confidence"]
    shared_fields = ["sample", "query", "shared_ko", "eggnog_ko", "kofam_ko"]
    shared_long_fields = shared_fields + ["eggnog_confidence", "kofam_confidence", "eggnog_evalue", "eggnog_bitscore", "kofam_score", "kofam_threshold"]
    write_tsv(out / "go_annotations.tsv", go_fields, go_rows); write_tsv(out / "go_annotations_highconf.tsv", go_fields, go_high_rows)
    write_tsv(out / "gene2go.tsv", go_long_fields, go_long); write_tsv(out / "gene2go_highconf.tsv", go_long_fields, go_high_long)
    write_tsv(out / "kegg_shared.tsv", shared_fields, shared_rows); write_tsv(out / "kegg_shared_highconf.tsv", shared_fields, shared_high_rows)
    write_tsv(out / "gene2ko_shared.tsv", shared_long_fields, shared_long); write_tsv(out / "gene2ko_shared_highconf.tsv", shared_long_fields, shared_high_long)
    go_stat_fields = ["sample", "go_proteins", "go_highconf_proteins", "go_terms", "go_pairs", "go_only_no_kegg_proteins"]
    ko_stat_fields = ["sample", "eggnog_ko_proteins", "kofam_ko_proteins", "both_ko_proteins", "shared_ko_proteins", "both_ko_empty_intersection", "shared_pairs", "shared_kos", "high_shared_proteins", "high_shared_pairs"]
    if len(stats) > 1:
        totals = {key: sum(row[key] for row in stats) for key in stats[0] if key not in {"sample", "go_terms", "shared_kos"}}
        totals.update(sample="TOTAL", go_terms=len({row["go_term"] for row in go_long}),
                      shared_kos=len({row["shared_ko"] for row in shared_long}))
        stats.append(totals)
    with open(out / "go_annotation_stats.txt", "w", encoding="utf-8") as handle:
        handle.write("GO 注释统计（按 sample + query 去重；GO 导出不是 GO 富集分析）\n")
        handle.write("完整：原始 eggNOG 中所有有效 GO；高可信：原始 eggNOG 的 E-value / Bit-score 达配置阈值且蛋白可信度 High，不要求 KEGG。无 KO 数基于原始 eggNOG 的 KEGG_ko 列。\n")
        handle.write("\t".join(go_stat_fields) + "\n")
        for row in stats:
            handle.write("\t".join(str(row[key]) for key in go_stat_fields) + "\n")
    with open(out / "kegg_shared_stats.txt", "w", encoding="utf-8") as handle:
        handle.write("共同 KEGG KO 统计（按 sample + query 去重；两个方法 KO 集合交集，不是共同 pathway）\n")
        handle.write("基本版本使用各工具已经过滤的主表；高可信版本取双方高可信表中同一个 KO 的交集，可信度为上游蛋白/最佳 hit 等级，并非逐 KO 实验验证。\n")
        handle.write("\t".join(ko_stat_fields) + "\n")
        for row in stats:
            handle.write("\t".join(str(row[key]) for key in ko_stat_fields) + "\n")


if __name__ == "__main__":
    main()
