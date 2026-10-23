from pathlib import Path

from common.banner import SYNTHETIC_BANNER

ROOT = Path(__file__).resolve().parents[1]


def test_web_banner_matches_python_constant():
    assert f'"{SYNTHETIC_BANNER}"' in (ROOT / "web" / "src" / "banner.ts").read_text()


def test_every_screen_shows_the_banner_through_the_shell():
    app = (ROOT / "web" / "src" / "App.tsx").read_text()
    assert "SYNTHETIC_BANNER" in app and 'data-testid="banner"' in app


def test_readme_carries_the_disclaimer():
    assert SYNTHETIC_BANNER in (ROOT / "README.md").read_text()
