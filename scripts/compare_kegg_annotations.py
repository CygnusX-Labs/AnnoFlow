#!/usr/bin/env python3
"""Compare per-protein KEGG KO assignments from eggNOG-mapper and KofamScan."""

import argparse
from pathlib import Path
import pandas as pd

EMPTY = {"", "-", "nan", "none", "na"}


def split_kos(value):
    if pd.isna(value):
        return set()
    parts = [part.strip() for part in str(value).replace(";", ",").split(",")]
    return {part[3:] if part.startswith("ko:") else part for part in parts
            if part.lower() not in EMPTY}


def read_table(path):
    return pd.read_csv(path, sep="\t", comment="#", dtype=str).fillna("")


def compare_sample(sample, eggnog_path, kofam_path, eggnog_high_path, kofam_high_path):
    eggnog = read_table(eggnog_path)
    kofam = read_table(kofam_path)
    eggnog_high = read_table(eggnog_high_path) if Path(eggnog_high_path).exists() else eggnog.iloc[0:0]
    kofam_high = read_table(kofam_high_path) if Path(kofam_high_path).exists() else kofam.iloc[0:0]

    def ko_map(frame, column):
        mapping = {}
        for row in frame.itertuples(index=False):
            query = getattr(row, "query", "")
            if query:
                mapping.setdefault(query, set()).update(split_kos(getattr(row, column, "")))
        return mapping

    egg_map = ko_map(eggnog, "kegg_ko")
    kof_map = ko_map(kofam, "KO")
    egg_high_map = ko_map(eggnog_high, "kegg_ko")
    kof_high_map = ko_map(kofam_high, "KO")

    rows = []
    for query in sorted(set(egg_map) | set(kof_map)):
        egg_kos = egg_map.get(query, set())
        kof_kos = kof_map.get(query, set())
        shared = egg_kos & kof_kos
        if shared:
            status = "一致"
        elif egg_kos and kof_kos:
            status = "冲突"
        elif egg_kos:
            status = "仅eggNOG"
        elif kof_kos:
            status = "仅KofamScan"
        else:
            status = "均无KO"
        rows.append({
            "sample": sample, "query": query,
            "eggnog_kegg_ko": ",".join(sorted(egg_kos)) or "-",
            "kofamscan_ko": ",".join(sorted(kof_kos)) or "-",
            "shared_ko": ",".join(sorted(shared)) or "-",
            "status": status,
            "eggnog_high_conf": query in egg_high_map,
            "kofamscan_high_conf": query in kof_high_map,
        })

    comparison = pd.DataFrame(rows, columns=["sample", "query", "eggnog_kegg_ko", "kofamscan_ko", "shared_ko", "status", "eggnog_high_conf", "kofamscan_high_conf"])
    both = comparison[comparison["eggnog_kegg_ko"] != "-"]
    both = both[both["kofamscan_ko"] != "-"]
    high = comparison.loc[comparison["eggnog_high_conf"].eq(True) & comparison["kofamscan_high_conf"].eq(True)]
    high_both = high[(high["eggnog_kegg_ko"] != "-") & (high["kofamscan_ko"] != "-")]
    stats = {
        "sample": sample,
        "eggnog_proteins": len(egg_map),
        "kofamscan_proteins": len(kof_map),
        "eggnog_with_kegg": sum(bool(v) for v in egg_map.values()),
        "kofamscan_with_kegg": sum(bool(v) for v in kof_map.values()),
        "shared_proteins_with_kegg": len(both),
        "same_ko": int((both["status"] == "一致").sum()),
        "conflicting_ko": int((both["status"] == "冲突").sum()),
        "same_ko_rate_shared": (int((both["status"] == "一致").sum()) / len(both) if len(both) else 0),
        "high_conf_shared_proteins": len(high_both),
        "high_conf_same_ko": int((high_both["status"] == "一致").sum()),
    }
    return comparison, stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", nargs="+", required=True)
    parser.add_argument("--input-dir", default=".")
    parser.add_argument("--output", required=True)
    parser.add_argument("--stats", required=True)
    args = parser.parse_args()

    all_rows, all_stats = [], []
    for sample in args.samples:
        base = Path(args.input_dir)
        comparison, stats = compare_sample(
            sample,
            base / "01.eggnog" / f"{sample}_eggnog.tsv",
            base / "02.kofam" / f"{sample}_kofam.tsv",
            base / "01.eggnog" / f"{sample}_eggnog_highconf.tsv",
            base / "02.kofam" / f"{sample}_kofam_highconf.tsv",
        )
        all_rows.append(comparison)
        all_stats.append(stats)

    result = pd.concat(all_rows, ignore_index=True) if all_rows else pd.DataFrame()
    result.to_csv(args.output, sep="\t", index=False)
    stats_df = pd.DataFrame(all_stats)
    with open(args.stats, "w") as handle:
        handle.write("KEGG KO 一致性统计（按唯一蛋白 query 统计）\n")
        handle.write("说明：一致 = 两个软件均有 KO 且 KO 集合有交集；冲突 = 均有 KO 但无交集。\n\n")
        handle.write("样本\tEGGNOG蛋白数\tKofamScan蛋白数\tEGGNOG有KEGG\tKofamScan有KEGG\t共同有KEGG\tKO一致\tKO冲突\t共同有KEGG中的一致率\t双方高置信共同蛋白\t双方高置信KO一致\n")
        for stat in all_stats:
            handle.write("\t".join(str(stat[key]) if not isinstance(stat[key], float) else f"{stat[key]:.4f}" for key in (
                "sample", "eggnog_proteins", "kofamscan_proteins", "eggnog_with_kegg", "kofamscan_with_kegg",
                "shared_proteins_with_kegg", "same_ko", "conflicting_ko", "same_ko_rate_shared",
                "high_conf_shared_proteins", "high_conf_same_ko")) + "\n")
        if len(stats_df) > 1:
            shared = stats_df["shared_proteins_with_kegg"].sum()
            same = stats_df["same_ko"].sum()
            handle.write(f"TOTAL\t{stats_df.eggnog_proteins.sum()}\t{stats_df.kofamscan_proteins.sum()}\t{stats_df.eggnog_with_kegg.sum()}\t{stats_df.kofamscan_with_kegg.sum()}\t{shared}\t{same}\t{stats_df.conflicting_ko.sum()}\t{same / shared if shared else 0:.4f}\t{stats_df.high_conf_shared_proteins.sum()}\t{stats_df.high_conf_same_ko.sum()}\n")


if __name__ == "__main__":
    main()
