"""Shared term normalization for annotation exports and KO comparison."""

import re

MISSING = {"", "-", "na", "n/a", "none", "nan", "null"}
GO_RE = re.compile(r"GO:\d{7}", re.IGNORECASE)
KO_RE = re.compile(r"(?:ko:)?(K\d{5})", re.IGNORECASE)


def clean_terms(value, pattern):
    if value is None or str(value).strip().lower() in MISSING:
        return []
    terms = re.split(r"[,;|\s]+", str(value))
    return sorted({match.group(1).upper() if pattern is KO_RE else match.group().upper()
                   for term in terms if (match := pattern.fullmatch(term))})


def split_kos(value):
    return set(clean_terms(value, KO_RE))
