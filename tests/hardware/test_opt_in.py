from __future__ import annotations

import os

import pytest


@pytest.mark.hardware
def test_hardware_tests_require_explicit_opt_in() -> None:
    if os.environ.get("VAYDEER_HARDWARE_TESTS") != "1":
        pytest.skip("Set VAYDEER_HARDWARE_TESTS=1 to enable read-only hardware checks")
    # Intentional placeholder: future checks must only inspect or read configuration.
    assert os.environ["VAYDEER_HARDWARE_TESTS"] == "1"
