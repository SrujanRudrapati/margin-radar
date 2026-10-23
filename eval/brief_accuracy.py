"""Brief accuracy (user gate: >= 90% of sections accurate AND zero direction errors). Synthetic data — not Opendoor data.

A section (one '### ' heading per ranked action, ending at the next '##' or '###' heading) is accurate when its
heading names its action's scope, it names no other action's scope, and the first direction verb in its "What changed"
line matches the signal's direction. A direction error is a first verb pointing the opposite way (e.g. "fell" for a
conversion rise); a line with no direction verb is inaccurate but not a direction error. A brief with no actions (or
one that never finished) scores 0.
"""
import re
from dataclasses import dataclass

UP = r"rose|rise|rising|increased?|higher|climb(?:ed|ing)?|jump(?:ed)?|grew|widen(?:ed|ing)?|up"
DOWN = r"fell|fall|falling|declined?|lower|slow(?:ed|ing)?|decreased?|drop(?:ped)?|shrank|narrow(?:ed)?|down"
DIRECTION = re.compile(rf"\b(?:(?P<up>{UP})|(?P<down>{DOWN}))\b", re.IGNORECASE)


@dataclass(frozen=True)
class BriefAccuracy:
    section_accuracy: float
    direction_errors: int
    sections: int


def brief_accuracy(body: str, actions: list[dict]) -> BriefAccuracy:
    heads = list(re.finditer(r"^###\s.*$", body, re.MULTILINE))
    boundaries = [m.start() for m in re.finditer(r"^#{2,3}\s", body, re.MULTILINE)] + [len(body)]
    ends = [next(b for b in boundaries if b > h.start()) for h in heads]
    accurate, direction_errors = 0, 0
    scopes = [a["scope"] for a in actions]
    for action in actions:
        idx = next((i for i, h in enumerate(heads) if re.search(rf"\b{re.escape(action['scope'])}\b", h.group(0))), None)
        if idx is None:
            continue
        section = body[heads[idx].start(): ends[idx]]
        others = [s for s in scopes if s != action["scope"] and re.search(rf"\b{re.escape(s)}\b", section)]
        changed = next((l for l in section.splitlines() if "what changed" in l.lower()), "")
        first = DIRECTION.search(changed.split(":", 1)[-1])
        said = None if first is None else ("+" if first.group("up") else "-")
        wrong_direction = said is not None and said != action["direction"]
        direction_errors += wrong_direction
        accurate += not others and said == action["direction"]
    n = max(len(actions), len(heads))
    return BriefAccuracy(accurate / n if n else 0.0, direction_errors, len(heads))
