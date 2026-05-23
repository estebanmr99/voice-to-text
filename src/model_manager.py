"""Local model registry and validation.

ModelManager tracks available whisper.cpp GGML/GGUF models on the local
filesystem.  It validates paths, optional checksums, and provides clear
error messages when a model is missing — **never downloading automatically**.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# URLs for manual side-loading guidance (never fetched at runtime)
_SIDeload_URLS: dict[str, str] = {
    "tiny": (
        "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/"
        "ggml-tiny.bin"
    ),
    "base": (
        "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/"
        "ggml-base.bin"
    ),
    "small": (
        "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/"
        "ggml-small.bin"
    ),
    "large-v3": (
        "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/"
        "ggml-large-v3.bin"
    ),
}


@dataclass
class ModelInfo:
    """Metadata for a single local whisper.cpp model."""

    name: str
    path: Path
    size_mb: int
    checksum_sha256: str | None = None
    language: str = "auto"
    parameters: dict[str, Any] = field(default_factory=dict)
    backend: str = "whisper.cpp"
    profile_compatibility: list[str] = field(default_factory=list)
    source_url: str = ""
    license_status: str = "candidate"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (path stored as string)."""
        d = asdict(self)
        d["path"] = str(self.path)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelInfo:
        """Reconstruct from a plain dict."""
        profile_compatibility = data.get("profile_compatibility")
        if not profile_compatibility:
            profile_compatibility = [
                "cpu-portable",
                "cpu-high-accuracy",
                "nvidia-dev",
            ]

        source_url = data.get("source_url")
        if not source_url:
            source_url = _SIDeload_URLS.get(data["name"], "")

        return cls(
            name=data["name"],
            path=Path(data["path"]),
            size_mb=data["size_mb"],
            checksum_sha256=data.get("checksum_sha256"),
            language=data.get("language", "auto"),
            parameters=data.get("parameters", {}),
            backend=data.get("backend", "whisper.cpp"),
            profile_compatibility=list(profile_compatibility),
            source_url=source_url,
            license_status=data.get("license_status", "candidate"),
        )


@dataclass
class CloudProviderConfig:
    """Cloud provider connection configuration.

    Stored alongside a Profile when ``mode == "cloud"``.  Never contains the
    raw API key — only an opaque keyring identifier (``api_key_id``).
    """

    provider_type: str  # "azure", "aws", etc.
    endpoint_url: str
    api_key_id: str  # keyring identifier, never the key itself
    model_name: str
    region: str = ""


@dataclass
class Profile:
    """Hardware profile metadata and model preference order.

    ``mode`` distinguishes local (whisper.cpp / pywhispercpp) from cloud
    (Azure OpenAI, AWS Transcribe, …).  Local profiles use
    ``preferred_model`` + ``fallback_order`` for file-based resolution;
    cloud profiles carry a ``provider_config`` instead.
    """

    canonical_name: str
    display_name: str
    description: str
    preferred_model: str
    fallback_order: list[str]
    backend_hint: str
    shipping_default: bool = False
    mode: str = "local"
    provider_config: CloudProviderConfig | None = None


class ModelManager:
    """Registry of local whisper.cpp models with validation.

    The registry is persisted as JSON in *models_dir / "registry.json"*.
    Pre-populated slots (``base``, ``small``) point to expected filenames
    inside *models_dir*; users must side-load the actual GGML/GGUF files.
    """

    _DEFAULT_MODELS: list[dict[str, Any]] = [
        {
            "name": "tiny",
            "filename": "ggml-tiny.bin",
            "size_mb": 75,
            "checksum_sha256": None,
            "language": "auto",
            "parameters": {"n_threads": 2},
            "backend": "whisper.cpp",
            "profile_compatibility": [
                "cpu-laptop",
                "cpu-portable",
            ],
            "source_url": _SIDeload_URLS["tiny"],
            "license_status": "candidate",
        },
        {
            "name": "base",
            "filename": "ggml-base.bin",
            "size_mb": 141,
            "checksum_sha256": None,
            "language": "auto",
            "parameters": {"n_threads": 4},
            "backend": "whisper.cpp",
            "profile_compatibility": [
                "cpu-portable",
                "cpu-high-accuracy",
                "nvidia-dev",
            ],
            "source_url": _SIDeload_URLS["base"],
            "license_status": "candidate",
        },
        {
            "name": "small",
            "filename": "ggml-small.bin",
            "size_mb": 465,
            "checksum_sha256": None,
            "language": "auto",
            "parameters": {"n_threads": 4},
            "backend": "whisper.cpp",
            "profile_compatibility": [
                "cpu-portable",
                "cpu-high-accuracy",
                "nvidia-dev",
                "cpu-max-accuracy",
            ],
            "source_url": _SIDeload_URLS["small"],
            "license_status": "candidate",
        },
        {
            "name": "large-v3",
            "filename": "ggml-large-v3.bin",
            "size_mb": 3000,
            "checksum_sha256": None,
            "language": "auto",
            "parameters": {"n_threads": 8},
            "backend": "whisper.cpp",
            "profile_compatibility": [
                "cpu-max-accuracy",
                "cpu-high-accuracy",
            ],
            "source_url": _SIDeload_URLS["large-v3"],
            "license_status": "candidate",
        },
    ]

    _DEFAULT_PROFILES: list[dict[str, Any]] = [
        {
            "canonical_name": "cpu-laptop",
            "display_name": "CPU Laptop",
            "description": (
                "Ultra-light whisper.cpp tiny model for low-RAM laptops "
                "(4-8 GB). Fast but lower accuracy."
            ),
            "preferred_model": "tiny",
            "fallback_order": ["base", "small"],
            "backend_hint": "whisper.cpp",
            "shipping_default": False,
        },
        {
            "canonical_name": "cpu-portable",
            "display_name": "CPU Portable",
            "description": (
                "Fast, low-memory whisper.cpp model for Intel/AMD laptops "
                "without GPU"
            ),
            "preferred_model": "base",
            "fallback_order": ["tiny", "small"],
            "backend_hint": "whisper.cpp",
            "shipping_default": True,
        },
        {
            "canonical_name": "cpu-high-accuracy",
            "display_name": "CPU High Accuracy",
            "description": (
                "Larger whisper.cpp model with better accuracy, slower on CPU"
            ),
            "preferred_model": "small",
            "fallback_order": ["base", "large-v3", "tiny"],
            "backend_hint": "whisper.cpp",
            "shipping_default": False,
        },
        {
            "canonical_name": "cpu-max-accuracy",
            "display_name": "CPU Max Accuracy",
            "description": (
                "Largest whisper.cpp large-v3 model for desktop workstations "
                "(16+ GB RAM). Best accuracy for technical Spanglish, slowest."
            ),
            "preferred_model": "large-v3",
            "fallback_order": ["small", "base"],
            "backend_hint": "whisper.cpp",
            "shipping_default": False,
        },
        {
            "canonical_name": "nvidia-dev",
            "display_name": "NVIDIA Dev",
            "description": (
                "Development/benchmark profile for faster-whisper on "
                "NVIDIA RTX (dev only)"
            ),
            "preferred_model": "small",
            "fallback_order": ["large-v3", "base", "tiny"],
            "backend_hint": "faster-whisper",
            "shipping_default": False,
        },
    ]

    _DEFAULT_CLOUD_PROFILES: list[dict[str, Any]] = [
        {
            "canonical_name": "cloud-azure-default",
            "display_name": "Cloud - Azure Whisper",
            "description": (
                "Azure OpenAI Whisper API — cloud transcription via HTTPS. "
                "Requires a valid endpoint URL and API key."
            ),
            "preferred_model": "",
            "fallback_order": [],
            "backend_hint": "cloud",
            "shipping_default": False,
            "mode": "cloud",
            "provider_config": {
                "provider_type": "azure",
                "endpoint_url": "",
                "api_key_id": "cloud-azure-default",
                "model_name": "whisper-1",
                "region": "",
            },
        },
    ]

    def __init__(self, models_dir: Path | None = None) -> None:
        self._models_dir = (
            models_dir or Path.home() / ".spanglish-dictation" / "models"
        )
        self._registry_path = self._models_dir / "registry.json"
        self._models: dict[str, ModelInfo] = {}
        self._profiles: dict[str, Profile] = {}
        self._load_registry()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_dir(self) -> None:
        """Create the models directory if it does not exist."""
        self._models_dir.mkdir(parents=True, exist_ok=True)

    def _load_registry(self) -> None:
        """Load registry from disk, or seed with default slots."""
        if self._registry_path.exists():
            try:
                with self._registry_path.open("r", encoding="utf-8") as fh:
                    payload = json.load(fh)
                for entry in payload.get("models", []):
                    info = ModelInfo.from_dict(entry)
                    self._models[info.name] = info
                self._load_profiles(payload.get("profiles"))
                logger.debug(
                    "Loaded %d model(s) from registry", len(self._models)
                )
                return
            except (json.JSONDecodeError, OSError, KeyError) as exc:
                logger.warning("Failed to load registry: %s", exc)
                self._models.clear()

        # Seed with default slots
        for slot in self._DEFAULT_MODELS:
            info = ModelInfo(
                name=slot["name"],
                path=self._models_dir / slot["filename"],
                size_mb=slot["size_mb"],
                checksum_sha256=slot["checksum_sha256"],
                language=slot["language"],
                parameters=dict(slot["parameters"]),
                backend=slot.get("backend", "whisper.cpp"),
                profile_compatibility=list(
                    slot.get(
                        "profile_compatibility",
                        [
                            "cpu-portable",
                            "cpu-high-accuracy",
                            "nvidia-dev",
                        ],
                    )
                ),
                source_url=slot.get(
                    "source_url", _SIDeload_URLS.get(slot["name"], "")
                ),
                license_status=slot.get("license_status", "candidate"),
            )
            self._models[info.name] = info

        self._load_profiles(None)

        self._save_registry()

    def _save_registry(self) -> None:
        """Persist the current registry to disk."""
        self._ensure_dir()
        payload = {
            "models": [m.to_dict() for m in self._models.values()],
            "profiles": [asdict(p) for p in self._profiles.values()],
        }
        with self._registry_path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
            fh.write("\n")

    @staticmethod
    def _sha256_of_file(path: Path) -> str:
        """Compute the SHA-256 hex digest of *path*."""
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def _profile_from_dict(entry: dict[str, Any]) -> Profile:
        """Construct a :class:`Profile` from a plain dict (local or cloud).

        Handles the ``mode`` and ``provider_config`` fields introduced for
        cloud profile support.  Legacy entries without these fields default
        to ``mode="local"`` and ``provider_config=None``.
        """
        mode = entry.get("mode", "local")
        provider_config: CloudProviderConfig | None = None
        if mode == "cloud":
            pc = entry.get("provider_config", {}) or {}
            provider_config = CloudProviderConfig(
                provider_type=pc.get("provider_type", ""),
                endpoint_url=pc.get("endpoint_url", ""),
                api_key_id=pc.get("api_key_id", ""),
                model_name=pc.get("model_name", ""),
                region=pc.get("region", ""),
            )
        return Profile(
            canonical_name=entry["canonical_name"],
            display_name=entry["display_name"],
            description=entry["description"],
            preferred_model=entry.get("preferred_model", ""),
            fallback_order=list(entry.get("fallback_order", [])),
            backend_hint=entry["backend_hint"],
            shipping_default=bool(entry.get("shipping_default", False)),
            mode=mode,
            provider_config=provider_config,
        )

    def _load_profiles(self, profiles_payload: Any) -> None:
        """Load profile registry from payload or seed defaults.

        Local profiles are loaded from the persisted registry or from
        :attr:`_DEFAULT_PROFILES`.  Cloud profile templates are always seeded
        from :attr:`_DEFAULT_CLOUD_PROFILES` (they have no model files to
        validate and should never silently disappear).
        """
        self._profiles.clear()
        source = profiles_payload or self._DEFAULT_PROFILES
        for entry in source:
            profile = self._profile_from_dict(entry)
            self._profiles[profile.canonical_name] = profile

        # Always seed default cloud profiles — they're templates, not
        # model-bound, so they should never go missing.
        for entry in self._DEFAULT_CLOUD_PROFILES:
            if entry["canonical_name"] not in self._profiles:
                profile = self._profile_from_dict(entry)
                self._profiles[profile.canonical_name] = profile

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register_model(self, info: ModelInfo) -> None:
        """Add or update a model in the registry."""
        self._models[info.name] = info
        self._save_registry()
        logger.info("Registered model '%s' at %s", info.name, info.path)

    def get_model(self, profile: str) -> ModelInfo:
        """Resolve *profile* name to a :class:`ModelInfo`.

        Raises:
            KeyError: If the profile is not known.
        """
        try:
            return self._models[profile]
        except KeyError as exc:
            raise KeyError(f"Unknown model profile: {profile}") from exc

    def list_models(self) -> list[ModelInfo]:
        """Return all registered models."""
        return list(self._models.values())

    def list_profiles(self) -> list[Profile]:
        """Return all defined profiles."""
        return list(self._profiles.values())

    def get_profile(self, canonical_name: str) -> Profile:
        """Return profile by canonical name."""
        try:
            return self._profiles[canonical_name]
        except KeyError as exc:
            raise KeyError(f"Unknown profile: {canonical_name}") from exc

    def get_shipping_default_profile(self) -> Profile:
        """Return the profile marked as shipping default."""
        for profile in self._profiles.values():
            if profile.shipping_default:
                return profile
        raise KeyError("No shipping default profile configured")

    def validate_model_metadata(self, info: ModelInfo) -> tuple[bool, list[str]]:
        """Validate model metadata completeness.

        Missing checksum is advisory only and does not make metadata incomplete.
        """
        warnings: list[str] = []
        is_complete = True

        if not info.name:
            warnings.append("Missing model name")
            is_complete = False
        if not str(info.path):
            warnings.append("Missing model path")
            is_complete = False
        if info.size_mb <= 0:
            warnings.append("Missing or invalid model size_mb")
            is_complete = False
        if not info.backend:
            warnings.append("Missing backend")
            is_complete = False
        if not info.profile_compatibility:
            warnings.append("Missing profile compatibility")
            is_complete = False
        if not info.checksum_sha256:
            warnings.append("Missing checksum_sha256 (optional but recommended)")
        if not info.source_url:
            warnings.append("Missing source_url")
        if not info.license_status:
            warnings.append("Missing license_status")
            is_complete = False
        elif info.license_status == "candidate":
            warnings.append("license_status is candidate; verify before release")
        elif info.license_status == "blocked":
            warnings.append("license_status is blocked")

        return is_complete, warnings

    def validate_model(self, info: ModelInfo) -> bool:
        """Check whether *info* points to a readable model file.

        If *info.checksum_sha256* is set, it is verified against the file.
        """
        if not info.path.exists():
            logger.debug("Model file missing: %s", info.path)
            return False

        if not info.path.is_file():
            logger.debug("Model path is not a file: %s", info.path)
            return False

        if info.checksum_sha256:
            actual = self._sha256_of_file(info.path)
            if actual.lower() != info.checksum_sha256.lower():
                logger.warning(
                    "Checksum mismatch for %s: expected %s, got %s",
                    info.name,
                    info.checksum_sha256,
                    actual,
                )
                return False

        return True

    def get_default_model(self) -> ModelInfo | None:
        """Return the first registered model whose file exists.

        Returns ``None`` if no models are valid.
        """
        for info in self._models.values():
            if self.validate_model(info):
                return info
        return None

    def get_missing_model_error(self, profile: str) -> str:
        """Return a human-readable error with side-load guidance.

        **No network request is made.**  The message contains a URL that
        the user can visit manually to download the model.
        """
        try:
            info = self.get_model(profile)
        except KeyError:
            return (
                f"Model profile '{profile}' is not registered. "
                "Run the app once to seed the registry, or check your settings."
            )

        url = info.source_url or _SIDeload_URLS.get(
            profile,
            (
                "https://huggingface.co/ggerganov/whisper.cpp/tree/main "
                "(find the matching GGML/GGUF file)"
            ),
        )

        blocked_prefix = ""
        if info.license_status == "blocked":
            blocked_prefix = (
                "WARNING: This model is marked as blocked by license policy. "
                "Do not use it in release builds.\n\n"
            )

        return (
            f"{blocked_prefix}"
            f"Model '{profile}' is not available locally.\n\n"
            f"Expected file: {info.path}\n"
            f"Expected size: ~{info.size_mb} MB\n\n"
            f"Download the model manually from:\n  {url}\n\n"
            f"Place the downloaded file at the expected path and restart the app.\n"
            "No automatic download will be attempted (offline-first design)."
        )
