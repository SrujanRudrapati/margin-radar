"""Model selection (CLAUDE.md API KEY AND BUDGET RULES 2). Synthetic data — not Opendoor data."""
import os
from typing import Literal

Purpose = Literal["dev", "final"]
DEFAULT_MODELS = {"dev": "claude-haiku-5-5", "final": "claude-sonnet-5-5"}
ENV = {"dev": "CLAUDE_MODEL_DEV", "final": "CLAUDE_MODEL_FINAL"}


def model_for(purpose: Purpose) -> str:
    return os.environ.get(ENV[purpose], DEFAULT_MODELS[purpose])
