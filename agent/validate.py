"""Grounding checker: every number in a brief must match the cited fact after normalization.

Numbers that need no citation: ISO dates, week numbers, scope names (M02, B2, M02-B2-cash), list markers and the
sample-scale label. Anything else must be followed by [q:<fact id>] and match that fact's value within its
displayed precision. Fails loudly: callers get the full list of problems. Synthetic data — not Opendoor data.
"""
import re

from agent.facts import _NUMBER, Fact, parse_number
from common.business import SAMPLE_SCALE_LABEL

CITE = re.compile(r"\[q:([A-Za-z0-9]+)\]")
MAX_GAP = 40  # characters allowed between a number and its citation
CONTEXT = [
    re.compile(re.escape(SAMPLE_SCALE_LABEL)),
    re.compile(r"~?\$1\.6B(?:/yr| a year| per year)?"),
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    re.compile(r"\bweeks?\s+\d+(?:\s*(?:–|-|to|and)\s*(?:week\s+)?\d+)?", re.IGNORECASE),
    re.compile(r"\bM0[1-6](?:-B[1-3](?:-(?:cash|CNML))?)?\b"),
    re.compile(r"\bB[1-3]\b"),
    re.compile(r"\bQ[1-4]\b"),
    re.compile(r"^\s*\d+\.\s", re.MULTILINE),
]
UNIT_MARK = {"usd": ("$",), "pct": ("%",), "pct_points": ("pts",), "bps": ("bps",), "days": ("days", "")}


def check(body: str, facts: dict[str, Fact]) -> list[str]:
    return check_detailed(body, facts)[0]


def check_detailed(body: str, facts: dict[str, Fact]) -> tuple[list[str], int]:
    errors: list[str] = []
    cites = [(m.start(), m.end(), m.group(1)) for m in CITE.finditer(body)]
    errors += [f"unknown reference [q:{ref}]" for _, _, ref in cites if ref not in facts and not ref.startswith("Q")]
    masked = _mask(body, [(s, e) for s, e, _ in cites])
    numbers = [m for m in _NUMBER.finditer(masked) if m.group("num")]
    for i, m in enumerate(numbers):
        token = m.group(0).strip()
        nxt = numbers[i + 1].start() if i + 1 < len(numbers) else len(body)
        cite = next((c for c in cites if m.end() <= c[0] <= m.end() + MAX_GAP and c[0] < nxt), None)
        where = body[max(0, m.start() - 30): m.end() + 15].replace("\n", " ")
        if cite is None:
            errors.append(f"uncited number {token!r} in: ...{where}...")
            continue
        ref = cite[2]
        if ref.startswith("Q"):
            errors.append(f"{token!r} cites a query [q:{ref}]; numbers must cite a fact (q:D...)")
        elif ref in facts and not _matches(token, facts[ref]):
            errors.append(f"{token!r} does not match [q:{ref}] = {facts[ref].display} ({facts[ref].label})")
    return errors, len(numbers)


def _mask(text: str, spans: list[tuple[int, int]]) -> str:
    chars = list(text)
    for pattern in CONTEXT:
        spans = spans + [(m.start(), m.end()) for m in pattern.finditer(text)]
    for start, end in spans:
        chars[start:end] = " " * (end - start)
    return "".join(chars)


def _norm(s: str) -> str:
    return s.replace("−", "-").replace(" ", "").lower()


def _matches(token: str, fact: Fact) -> bool:
    if _norm(token) == _norm(fact.display):
        return True
    marks = UNIT_MARK.get(fact.kind)
    if marks is not None and not any(mark in token for mark in marks if mark) and "" not in marks:
        return False
    if marks is None and any(mark in token for mark in ("$", "%", "pts", "bps")):
        return False
    try:
        value = parse_number(token)
    except ValueError:
        return False
    return abs(value - fact.value) <= max(abs(fact.value) * 0.01, _half_step(token))


def _half_step(token: str) -> float:
    m = _NUMBER.search(token)
    decimals = len(m["num"].split(".")[1]) if "." in m["num"] else 0
    scale = {"K": 1e3, "M": 1e6, "B": 1e9, "%": 0.01, "pts": 0.01}.get(m["suffix"], 1.0)
    return 0.5 * 10 ** (-decimals) * scale
