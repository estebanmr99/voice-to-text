"""Profile-to-model resolution with safe local fallbacks."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from hardware_detector import HardwareInfo
from model_manager import CloudProviderConfig, ModelInfo, ModelManager
from settings_store import SettingsStore

logger = logging.getLogger(__name__)


@dataclass
class ProfileResolutionResult:
    model_info: ModelInfo | None
    profile_used: str
    fallback_applied: bool
    advisory_message: str = ""
    error_message: str = ""
    provider_config: CloudProviderConfig | None = None
    is_cloud: bool = False


def _find_best_model(
    profile,
    model_manager: ModelManager,
) -> tuple[ModelInfo | None, str, bool]:
    """Iterate preferred+fallback models and return the first valid one.

    Returns (model_info, selected_name, fallback_applied).
    Returns early with (None, "", False) for cloud profiles.
    """
    if profile.mode == "cloud":
        return None, "", False

    ordered_models = [profile.preferred_model, *profile.fallback_order]
    selected: ModelInfo | None = None
    selected_name = ""
    for model_name in ordered_models:
        try:
            info = model_manager.get_model(model_name)
        except KeyError:
            continue
        if model_manager.validate_model(info):
            selected = info
            selected_name = model_name
            break
    return selected, selected_name, selected_name != profile.preferred_model


def resolve_profile(
    settings: SettingsStore,
    model_manager: ModelManager,
    hardware_info: HardwareInfo,
) -> ProfileResolutionResult:
    """Resolve the best available local or cloud model for a preferred profile.

    Never mutates settings and never raises.
    """
    preferred_profile_name = settings.model_profile
    profile_used = preferred_profile_name

    try:
        profile = model_manager.get_profile(preferred_profile_name)
    except KeyError:
        logger.warning(
            "Unknown profile '%s'; falling back to shipping default", preferred_profile_name
        )
        try:
            profile = model_manager.get_shipping_default_profile()
            profile_used = profile.canonical_name
        except KeyError:
            return ProfileResolutionResult(
                model_info=None,
                profile_used=preferred_profile_name,
                fallback_applied=False,
                error_message="No shipping default profile configured.",
            )

    # Cloud profile — skip hardware detection and file validation
    if profile.mode == "cloud":
        return ProfileResolutionResult(
            model_info=None,
            profile_used=profile_used,
            fallback_applied=False,
            is_cloud=True,
            provider_config=profile.provider_config,
        )

    selected, selected_name, fallback_applied = _find_best_model(profile, model_manager)

    if selected is None:
        return ProfileResolutionResult(
            model_info=None,
            profile_used=profile_used,
            fallback_applied=False,
            error_message=model_manager.get_missing_model_error(profile.preferred_model),
        )

    advisory = ""
    if preferred_profile_name == "nvidia-dev" and not hardware_info.has_nvidia_gpu:
        advisory = "NVIDIA profile selected but no NVIDIA GPU detected. Using CPU model."
    elif (
        preferred_profile_name == "nvidia-dev"
        and hardware_info.has_nvidia_gpu
        and fallback_applied
    ):
        advisory = (
            "NVIDIA GPU detected but faster-whisper dependencies or model "
            "missing. Using CPU fallback. See setup guide."
        )

    return ProfileResolutionResult(
        model_info=selected,
        profile_used=profile_used,
        fallback_applied=fallback_applied,
        advisory_message=advisory,
    )
