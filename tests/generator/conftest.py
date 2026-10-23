import pytest

from generator.scenarios import default_scenarios
from generator.simulate import simulate

SEED = 42


@pytest.fixture(scope="session")
def control():
    return simulate(SEED)


@pytest.fixture(scope="session")
def injected():
    return simulate(SEED, default_scenarios())
