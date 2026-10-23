import pytest


@pytest.fixture(autouse=True, scope="session")
def _no_live_llm_calls():
    """pytest never makes live API calls: force replay mode and hide the key."""
    mp = pytest.MonkeyPatch()
    mp.setenv("REPLAY", "1")
    mp.delenv("MARGIN_RADAR_API_KEY", raising=False)
    yield
    mp.undo()
