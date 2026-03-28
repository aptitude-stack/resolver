from __future__ import annotations

import pytest

from aptitude_client.domain.policy import SelectionPreferences


def test_selection_preferences_defaults_are_explicit() -> None:
    preferences = SelectionPreferences()

    assert preferences.profile == "balanced"
    assert preferences.interaction_mode == "auto"


def test_selection_preferences_reject_unknown_profile() -> None:
    with pytest.raises(ValueError, match="Unknown selection profile"):
        SelectionPreferences(profile="latest")


def test_selection_preferences_reject_unknown_interaction_mode() -> None:
    with pytest.raises(ValueError, match="Unknown interaction mode"):
        SelectionPreferences(interaction_mode="sometimes")
