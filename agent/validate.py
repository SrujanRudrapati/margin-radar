"""Grounding checker: every number in a brief must be a cited fact, copied exactly.

Numbers that need no citation: ISO dates, week numbers ("week 38", "weeks 30–40"), scope names (M02, B2,
M02-B2-cash), quarter names and the sample-scale label. Any other number must be immediately followed by
[q:<fact id>] and match that fact's display string exactly (a leading "+" is optional). Numbers written as words
are rejected. Every reference must exist. check_structure() enforces the SPEC's required content. Fails loudly:
callers get the full list of problems. Synthetic data — not Opendoor data.
"""
import re

from agent.facts import _NUMBER, Fact
from common.business import SAMPLE_SCALE_LABEL

CITE = re.compile(r"\[q:([A-Za-z0-9]+)\]")
MAX_GAP = 40  # characters allowed between a number and its citation
_WEEK_END = r"(?![\d%]|[.,]\d)"
CONTEXT = [
    re.compile(re.escape(SAMPLE_SCALE_LABEL)),
    re.compile(r"~?\$1\.6B(?:/yr| a year| per year)"),
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    re.compile(rf"\bweeks\s+\d+\s*(?:–|-|to|and)\s*\d+{_WEEK_END}", re.IGNORECASE),
    re.compile(rf"\bweeks?\s+\d+{_WEEK_END}", re.IGNORECASE),
    re.compile(r"\b(?:per|each|every)\s+100\s+bps\b", re.IGNORECASE),
    re.compile(r"\bM0[1-6](?:-B[1-3](?:-(?:cash|CNML))?)?\b"),
    re.compile(r"\bB[1-3]\b"),
    re.compile(r"\bQ[1-4]\b"),
]
NUMBER_WORDS = re.compile(
    r"\b(zero|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|"
    r"seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|"
    r"billion|half|double|doubled|triple|tripled|twice|thrice|quadruple|quadrupled)\b", re.IGNORECASE)
NOT_SURE = re.compile(r"^##\s+what we.re not sure about", re.IGNORECASE | re.MULTILINE)
SCENARIO_PHRASES = ("scenario estimate", "unconfirmed until resales", "midpoint")


def check(body: str, facts: dict[str, Fact], known_refs: set[str] | None = None) -> list[str]:
    return check_detailed(body, facts, known_refs)[0]


def check_detailed(body: str, facts: dict[str, Fact], known_refs: set[str] | None = None) -> tuple[list[str], int]:
    errors: list[str] = []
    cites = [(m.start(), m.end(), m.group(1)) for m in CITE.finditer(body)]
    for _, _, ref in cites:
        if ref not in facts and not (known_refs is not None and ref in known_refs):
            errors.append(f"unknown reference [q:{ref}]")
    masked = _mask(body, [(s, e) for s, e, _ in cites])
    errors += [f"number written as a word: {m.group(0)!r}; use a cited figure or describe it without a number"
               for m in NUMBER_WORDS.finditer(masked)]
    numbers = [m for m in _NUMBER.finditer(masked) if m.group("num")]
    for i, m in enumerate(numbers):
        token = m.group(0).strip()
        nxt = numbers[i + 1].start() if i + 1 < len(numbers) else len(body)
        cite = next((c for c in cites if m.end() <= c[0] <= m.end() + MAX_GAP and c[0] < nxt), None)
        where = body[max(0, m.start() - 30): m.end() + 15].replace("\n", " ")
        if cite is None:
            errors.append(f"uncited number {token!r} in: ...{where}...")
        elif cite[2] not in facts:
            errors.append(f"{token!r} cites [q:{cite[2]}], which is not a fact; numbers must cite a fact (q:D...)")
        elif _norm(token) != _norm(facts[cite[2]].display):
            fact = facts[cite[2]]
            errors.append(f"{token!r} does not match [q:{cite[2]}], which displays {fact.display} ({fact.label}); "
                          "copy the display exactly")
    return errors, len(numbers)


def check_structure(body: str, actions: list[dict]) -> list[str]:
    """Required content: every ranked action, in rank order; scenario labels and range; the uncertainty section."""
    errors = []
    if not NOT_SURE.search(body):
        errors.append("missing the '## What we're not sure about' section")
    headings = [(m.start(), m.group(0)) for m in re.finditer(r"^###\s.*$", body, re.MULTILINE)]
    positions = []
    for rank, action in enumerate(actions, start=1):
        scope = action["scope"]
        found = next((i for i, (_, h) in enumerate(headings) if re.search(rf"\b{re.escape(scope)}\b", h)), None)
        if found is None:
            errors.append(f"ranked action {rank} ({scope}) has no '### {scope} — ...' section")
            continue
        positions.append(found)
        start = headings[found][0]
        end = headings[found + 1][0] if found + 1 < len(headings) else len(body)
        section = body[start:end]
        if action["impact"]["basis"] == "scenario_estimate":
            lower = section.lower()
            errors += [f"{scope}: scenario estimate must say '{p}'" for p in SCENARIO_PHRASES if p not in lower]
            for name in ("usd_low", "usd_mid", "usd_high"):
                ref = action["impact"][name]["ref"]
                if f"[{ref}]" not in section:
                    errors.append(f"{scope}: cite the scenario {name.split('_')[1]} figure [{ref}]")
    if positions != sorted(positions):
        errors.append("actions must appear in rank order (highest $ at risk first)")
    return errors


def _mask(text: str, spans: list[tuple[int, int]]) -> str:
    chars = list(text)
    for pattern in CONTEXT:
        spans = spans + [(m.start(), m.end()) for m in pattern.finditer(text)]
    for start, end in spans:
        chars[start:end] = " " * (end - start)
    return "".join(chars)


def _norm(s: str) -> str:
    return s.replace("−", "-").replace(" ", "").lower().lstrip("+")
