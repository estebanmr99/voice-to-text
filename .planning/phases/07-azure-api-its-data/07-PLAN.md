# Phase 7 Plan: Azure API & ITS Data

**Phase:** 07
**Goal:** Support paid cloud-hosted models (Azure OpenAI) with secure ITS data handling, user-friendly model setup UI.
**Depends on:** Phase 6
**Mode:** Interactive (decisions locked in 07-CONTEXT.md)
**Research:** 07-RESEARCH.md (cloud APIs, key storage, codebase integration map)

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────┐
│  TranscriberInterface (common contract)              │
│  transcribe(audio, sr, lang) -> str                  │
├──────────────────────┬──────────────────────────────┤
│  Transcriber (local) │  CloudTranscriber (new)       │
│  multiprocessing +   │  httpx + provider plugins     │
│  pywhispercpp        │  ├─ AzureOpenAIProvider       │
│                      │  └─ AWSTranscribeProvider     │
└──────────────────────┴──────────────────────────────┘
```

Profile routing: `model_manager.Profile.mode` → `profile_resolver` → `main._apply_profile_change()` → sets `dictation_loop._active_transcriber` + calls `privacy_guard.whitelist_endpoints()` / `revoke_whitelist()`.

---

## Wave 1: Foundation — Privacy & Profiles
**No dependencies. These can run in parallel.**

### Task 1.1: PrivacyGuard Whitelist
**Files:** `src/privacy_guard.py`
**Action:** Add `whitelist_endpoints(urls: list[str])` and `revoke_whitelist()` methods. Modify `_patch_socket()`, `_patch_urllib()`, `_patch_ssl()` to check whitelist before raising `NetworkBlockedError`. Thread-safe access via `threading.Lock`.
**Verify:** `tests/test_privacy_guard.py` — test that whitelisted host is allowed, non-whitelisted still blocked.

### Task 1.2: Model Manager Cloud Profiles
**Files:** `src/model_manager.py`
**Action:** Add `mode: str = "local"` field to `Profile` dataclass. Add `CloudProviderConfig` dataclass (provider_type, endpoint_url, api_key_id, model_name, region). Add `_DEFAULT_CLOUD_PROFILES` with Azure template. Extend `list_profiles()` to include cloud profiles. Cloud profiles skip file validation.
**Verify:** `tests/test_model_manager.py` — test that cloud profiles list correctly, don't need file validation.

### Task 1.3: Settings Store Cloud Config
**Files:** `src/settings_store.py`
**Action:** Add settings keys: `cloud_provider` (str), `cloud_endpoint_url` (str), `cloud_model_name` (str), `cloud_profiles` (list[dict] for saved profiles). Add `keyring` integration: `store_api_key(profile_id, key)`, `get_api_key(profile_id) -> str|None`, `delete_api_key(profile_id)`. API key NEVER stored in JSON.
**Verify:** `tests/test_settings_store.py` — test cloud settings save/load, keyring integration mocked.

---

## Wave 2: Cloud Transcriber Implementation
**Depends on:** Wave 1

### Task 2.1: Transcriber Interface Extraction
**Files:** `src/transcriber.py`, `src/transcriber_worker.py`
**Action:** Extract abstract `TranscriberInterface` with `transcribe(audio: np.ndarray, sample_rate: int, language: str) -> str`. Current `Transcriber` becomes local implementation. No behavior change for local mode.
**Verify:** All existing transcription tests pass. No regression.

### Task 2.2: Cloud Transcriber + Azure Provider
**Files:** `src/cloud_transcriber.py`, `src/cloud_providers/__init__.py`, `src/cloud_providers/azure.py`
**Action:** `CloudTranscriber` implements `TranscriberInterface`. Uses `httpx` for HTTP POST. Azure provider: `AzureOpenAIProvider.transcribe(audio_bytes, filename, language) -> TranscriptionResult`. Authentication via `api-key` header fetched from keyring. Handles errors (429, 500, timeout).
**Verify:** `tests/test_cloud_transcriber.py` — mock httpx, test Azure provider calls correct endpoint, handles errors.

### Task 2.3: AWS Transcribe Provider
**Files:** `src/cloud_providers/aws.py`
**Action:** `AWSTranscribeProvider.transcribe()` — uploads audio to S3, starts transcription job, polls, downloads transcript. Uses boto3 credential chain. Handles S3 bucket config from settings.
**Verify:** `tests/test_cloud_transcriber.py` — mock boto3, test S3 upload + polling flow.

---

## Wave 3: UI & Wiring
**Depends on:** Wave 2

### Task 3.1: Profile Resolver Cloud Path
**Files:** `src/profile_resolver.py`
**Action:** Extend `resolve_profile()` to detect `mode="cloud"` profiles. Return `CloudProviderConfig` in `ProfileResolutionResult`. Cloud profiles skip hardware detection. Add `resolve_cloud_profile()` helper.
**Verify:** `tests/test_profile_resolver.py` — test local vs cloud resolution.

### Task 3.2: Dictation Loop Routing
**Files:** `src/dictation_loop.py`
**Action:** Add `set_active_transcriber(transcriber: TranscriberInterface)`. Modify `_handle_speech_end()` to route through `self._active_transcriber.transcribe()`. Backward compatible — defaults to local.
**Verify:** `tests/test_dictation_loop.py` — test that both local and mock cloud transcriber work.

### Task 3.3: Main Wiring
**Files:** `src/main.py`
**Action:** Create `CloudTranscriber` instance. Modify `_apply_profile_change()` to detect cloud mode → call `privacy_guard.whitelist_endpoints([url])`, start `CloudTranscriber`, set `dictation_loop._active_transcriber`. On local mode → call `privacy_guard.revoke_whitelist()`, start `Transcriber`.
**Verify:** `tests/test_main.py` — test profile change switches transcriber + privacy mode.

### Task 3.4: Settings Dialog Cloud UI
**Files:** `src/settings_dialog.py`
**Action:** Add "Cloud Providers" section with: provider selector (Azure/AWS), endpoint URL field, API key password field (masked), model name, "Test Connection" button, saved profiles list with add/delete. Local/Cloud toggle integrates with existing model profile selector.
**Verify:** `tests/test_settings_dialog.py` — test cloud UI fields, key masking, profile CRUD.

### Task 3.5: Shell Integration Mode Display
**Files:** `src/shell_integration.py`
**Action:** Profile menu shows "Local - {name}" and "Cloud - {name}". Status panel uses different colors for cloud (blue) vs local (green). Tooltip shows mode. Tray icon badge/indicator for cloud mode.
**Verify:** `tests/test_shell_integration.py` — test menu prefixes, status colors.

---

## Success Criteria

1. User creates a cloud profile with endpoint + API key → key stored securely in Windows Credential Manager
2. User selects cloud profile → PrivacyGuard whitelists only the provider endpoint
3. Audio captured → sent to Azure/AWS → transcript returned and pasted
4. User switches back to local profile → PrivacyGuard blocks all network again
5. Local dictation continues working exactly as before
6. API key is NEVER visible in settings.json or logs
7. Cloud mode indicator visible in tray and status panel
