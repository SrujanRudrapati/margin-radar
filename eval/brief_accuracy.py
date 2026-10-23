"""Brief accuracy (user gate: >= 90% of sections accurate AND zero direction errors). Synthetic data — not Opendoor data.

A section (one '### ' heading per ranked action) is accurate when its heading names its action's scope, it names no
other action's scope, and its "What changed" line has no direction error. A direction error is a "What changed"
line that only uses words for the opposite of the signal's direction (e.g. "fell" for a conversion rise).
"""
import re
from dataclasses import dataclass

UP = re.compile(r"\b(rose|rise|rising|increased?|up|higher|climb(?:ed|ing)?|jump(?:ed)?|grew|widen(?:ed|ing)?|above)\b", re.I)
DOWN = re.compile(r"\b(fell|fall|falling|declined?|down|lower|slow(?:ed|ing)?|decreased?|drop(?:ped)?|shrank|narrow(?:ed)?|below)\b", re.I)


@dataclass(frozen=True)
class BriefAccuracy:
    section_accuracy: float
    direction_errors: int
    sections: int


def brief_accuracy(body: str, actions: list[dict]) -> BriefAccuracy:
    heads = list(re.finditer(r"^###\s.*$", body, re.MULTILINE))
    ends = [h.start() for h in heads[1:]] + [len(body)]
    accurate, direction_errors = 0, 0
    scopes = [a["scope"] for a in actions]
    for action in actions:
        idx = next((i for i, h in enumerate(heads) if re.search(rf"\b{re.escape(action['scope'])}\b", h.group(0))), None)
        if idx is None:
            continue
        section = body[heads[idx].start(): ends[idx]]
        others = [s for s in scopes if s != action["scope"] and re.search(rf"\b{re.escape(s)}\b", section)]
        changed = next((l for l in section.splitlines() if "what changed" in l.lower()), "")
        up, down = bool(UP.search(changed)), bool(DOWN.search(changed))
        wrong_direction = (action["direction"] == "+" and down and not up) or (action["direction"] == "-" and up and not down)
        direction_errors += wrong_direction
        accurate += not others and not wrong_direction
    n = max(len(actions), len(heads))
    return BriefAccuracy(accurate / n if n else 1.0, direction_errors, len(heads))
