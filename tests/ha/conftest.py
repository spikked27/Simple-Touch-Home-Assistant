from pathlib import Path

import pytest

pytest_plugins = ["pytest_homeassistant_custom_component"]


@pytest.fixture
def hass_config_dir():
    """Load this repository's custom_components, not the harness's sample ones."""
    return str(Path(__file__).resolve().parents[2])
