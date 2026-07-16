from __future__ import annotations

import pytest

from vaydeer_studio.core.models import ProfileTargetPlatform
from vaydeer_studio.core.templates import create_profile_from_template, profile_template_summaries


def test_application_templates_cover_requested_common_workflows() -> None:
    summaries = {item["id"]: item for item in profile_template_summaries()}

    assert set(summaries) == {"codex", "chatgpt", "photoshop", "illustrator"}
    assert summaries["photoshop"]["application"] == "Adobe Photoshop"


@pytest.mark.parametrize(
    ("platform", "primary_modifier"),
    [
        (ProfileTargetPlatform.LINUX, 17),
        (ProfileTargetPlatform.WINDOWS, 17),
        (ProfileTargetPlatform.MACOS, 91),
    ],
)
def test_templates_adapt_primary_shortcuts_for_the_target_platform(
    platform: ProfileTargetPlatform, primary_modifier: int
) -> None:
    profile = create_profile_from_template("illustrator", platform)

    assert profile.schema_version == 2
    assert profile.target_platform == platform
    assert profile.target_application == "Adobe Illustrator"
    assert len(profile.layers[0].assignments) == 9
    assert profile.layers[0].assignment_for(6).key_codes == [primary_modifier, ord("S")]
    assert profile.layers[0].assignment_for(8).key_codes == [primary_modifier, 16, ord("Z")]


def test_unknown_template_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown profile preset"):
        create_profile_from_template("unknown", ProfileTargetPlatform.LINUX)
