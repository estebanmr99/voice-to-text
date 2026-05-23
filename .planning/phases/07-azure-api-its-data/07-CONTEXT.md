# Phase 7: Azure API & ITS Data - Context

**Gathered:** 2026-05-23
**Status:** Ready for planning

<domain>
## Task Boundary

Phase 7: Azure API & ITS Data
Goal: Support paid cloud-hosted models (Azure OpenAI) with secure ITS data handling, user-friendly model setup UI.

The current app is fully offline via PrivacyGuard. Adding cloud transcription is a
fundamental privacy model change — cloud mode must coexist with local mode and must
never weaken local-mode guarantees.
</domain>

<decisions>
## Implementation Decisions

### 1. Cloud Backend Architecture
- REST API abstraction layer — endpoints + API keys
- User provides endpoint URL + key. App POSTs audio, receives text.
- Investigate Azure OpenAI Whisper API AND AWS Transcribe as initial providers.
- Common abstraction so adding providers later is trivial (endpoint + auth + response parser).
- Fallback: when cloud unreachable, show error (do NOT fallback to local — user chose cloud explicitly).
- Local models remain unchanged — they continue using whisper.cpp via pywhispercpp.

### 2. ITS Data Handling & Network Security
- "ITS" = Internal Top Secret data. High sensitivity.
- **Local mode**: PrivacyGuard blocks ALL network (current behavior — unchanged).
- **Cloud mode**: PrivacyGuard whitelists ONLY the configured provider endpoint(s).
  - All other outbound calls blocked (no telemetry, no analytics, no crash uploads).
  - Whitelist derived from the endpoint URL configured in the cloud profile.
- **Key storage**: API keys stored securely.
  - At minimum: obfuscated on disk (not plaintext in settings JSON).
  - Consider OS-native credential store (Windows Credential Manager via `keyring` or `win32cred`).
  - Keys never logged, never displayed in UI after entry.
- Data-in-motion: audio sent to cloud endpoint over HTTPS. No local audio retention (consistent with current policy).
- Transcript content: handled same as local — data-in-motion only, pasted and forgotten.

### 3. Model Setup UX — Profile Switcher
- User sees a "Local / Cloud" toggle in the model settings UI.
- **Local profiles**: existing behavior — select from side-loaded Whisper models, hardware profiles (CPU Portable, CPU High Accuracy, etc.). Naming: "Local - CPU Portable", "Local - CPU High Accuracy".
- **Cloud profiles**: user creates named profiles. Each profile stores:
  - Profile name (user-chosen, e.g., "Azure Prod", "AWS Dev")
  - Provider type (Azure OpenAI, AWS Transcribe)
  - Endpoint URL
  - API key (masked after save)
  - Optional: model name (e.g., "whisper-1" for Azure)
- Profile naming convention in tray/UI:
  - Local: "Local - {profile_name}" (e.g., "Local - CPU Portable")
  - Cloud: "Cloud - {profile_name}" (e.g., "Cloud - Azure Prod")
- First-run cloud setup: modal guides user through creating first cloud profile.

### 4. Privacy Boundary & Mode Separation
- **Two operating modes**, tied to profile type:
  - Selecting a Local profile → PrivacyGuard blocks all network (current).
  - Selecting a Cloud profile → PrivacyGuard whitelists only the configured endpoint(s).
- Mode switch on profile change in tray (existing `profile_changed` signal).
- Cloud mode requires explicit opt-in during profile setup — user is warned that audio will leave the device.
- Status panel shows current mode prominently: "Local" (green) vs "Cloud" (blue/orange).
- No way to accidentally send data to cloud — you must select a Cloud profile.
</decisions>

<specifics>
## Specific Ideas

- Abstraction layer: `CloudTranscriber` class with provider plugins (Azure, AWS).
- Key storage: `keyring` library for Windows Credential Manager integration.
- Profile schema extension: add `mode: "local" | "cloud"` and `provider_config` fields.
- Settings dialog gets a "Cloud Providers" tab/section.
- PrivacyGuard: add `whitelist_endpoints(endpoints: list[str])` method.
- Consider adding a `requirements-cloud.txt` extra for cloud dependencies.

No specific external specs — requirements fully captured in decisions above.
</specifics>

<deferred>
## Deferred Ideas

- Other cloud providers (GCP, custom endpoints) — after Azure + AWS.
- Streaming transcription (real-time cloud) — Phase 7 focuses on batch/hold-to-talk.
- Cloud model fallback chain (try Azure, then AWS) — deferred, single provider per profile.
</deferred>
