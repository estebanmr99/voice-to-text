# Phase 7 Research: Cloud Transcription APIs — Azure OpenAI Whisper + AWS Transcribe

Date: 2026-05-23 | Status: COMPLETE

---

## 1. Azure OpenAI Whisper API

### Endpoint Format

```
https://{resource}.openai.azure.com/openai/deployments/{deployment}/audio/transcriptions?api-version={version}
```

- **Method**: POST, multipart/form-data
- **Auth**: Header `api-key: {key}`
- **API Version**: `2025-04-01-preview` (current default)
- **SDK**: `openai` Python package v1.x — same interface as standard OpenAI. Azure config via `azure_endpoint`, `azure_api_key`, `api_version` params.
- **Alternative**: Raw `httpx` client with `requests` — more control for custom needs (chunking strategy, diarization flags).

### Request/Response Format

**Request body (multipart)**:
- `file` — audio binary, field name "file" (required)
- `model` — string (e.g., `whisper-1`, `gpt-4o-transcribe`, `gpt-4o-transcribe-diarize`)
- `language` — optional BCP-47 code
- `response_format` — `json` (default), `verbose_json`, `text`, `srt`, `vtt`, `diarized_json`
- `prompt` — optional string for context/hotwords
- `temperature` — optional float (0–1)
- `timestamp_granularities[]` — `word`, `segment` (for verbose_json)

**Response (JSON)**:
```json
{
  "text": "transcribed text",
  "language": "en",
  "duration": 12.5,
  "segments": [
    { "start": 0.0, "end": 4.5, "text": "hello world" }
  ],
  "words": [...]
}
```

For `diarized_json` response format, each segment includes `speaker: "A"|"B"|"C"|"D"`.

### Audio Format Requirements

| Property | Value |
|---|---|
| Max file size | 25 MB |
| Max duration | ~1500s (whisper-1, gpt-4o-mini-transcribe) / ~1400s (diarize model) |
| Supported formats | mp3, mp4, mpeg, mpga, m4a, wav, webm |
| Sample rate | Any (Whisper auto-detects) |
| Encoding | Any supported by listed container formats |
| Chunking | Required `chunking_strategy=auto` for audio > 30s on diarize model |

### Authentication Pattern

```python
# openai SDK approach
from openai import AzureOpenAI
client = AzureOpenAI(
    azure_endpoint="https://{resource}.openai.azure.com",
    api_key="{key}",
    api_version="2025-04-01-preview"
)
# endpoint: /openai/deployments/{deployment}/audio/transcriptions
# auth header: api-key (set automatically)
```

### Pricing Model

- **whisper-1**: Pay-per-token/audio-second via Azure OpenAI (not OpenAI direct pricing)
- **gpt-4o-transcribe**: Higher quality, higher cost
- **gpt-4o-mini-transcribe**: Cost-effective option
- **gpt-4o-transcribe-diarize**: Speaker diarization, premium tier

Note: Azure pricing differs from OpenAI direct. Check Azure portal for current rates.

### Rate Limits

- Varies by tier (Standard, S0, S1, S2)
- Configurable per-resource in Azure portal
- No public per-request limit documented — check Azure quota

### Key Patterns from Real Code

From [speakr/azure_openai_transcribe.py](https://github.com/murtaza-nasir/speakr/blob/master/src/services/transcription/connectors/azure_openai_transcribe.py):
- Build URL: `f"{endpoint}/openai/deployments/{deployment}/audio/transcriptions?api-version={api_version}"`
- Pass `api-key` header via `httpx.Client(headers={"api-key": key})`
- Read audio from `request.audio_file` (bytes), send as `files={"file": (name, data, content_type)}`
- `response_format=diarized_json` + `chunking_strategy=auto` for speaker diarization
- For non-diarize models: `response_format=verbose_json` for timestamps
- Combine `prompt` + `hotwords` into single `prompt` string joined by ". "
- Timeout: 1800s (30 min) for long transcriptions

---

## 2. AWS Transcribe

### SDK Pattern

```python
import boto3
transcribe = boto3.client("transcribe")
```

Auth: boto3 credential chain (env vars → ~/.aws/credentials → IAM role → EC2 metadata). **No API key passed directly** — uses AWS auth.

### Request Format (start_transcription_job)

**Parameters**:
- `TranscriptionJobName` (required) — unique string, max 200 chars
- `LanguageCode` (required) — e.g., `en-US`, `es-US`, `en-GB`
- `Media` (required) — `{"MediaFileUri": "s3://bucket/key"}`
- `MediaFormat` — `mp3`, `mp4`, `wav`, `flac`, `ogg`, `amr`, `webm`, `m4a`
- `MediaSampleRateHertz` — optional int
- `OutputBucketName` — S3 bucket for transcript output
- `OutputKey` — S3 key prefix for output
- `IdentifyLanguage` — bool, auto-detect language
- `IdentifyMultipleLanguages` — bool, multi-language mode
- `Settings` — dict: `ShowSpeakerLabels`, `MaxSpeakerLabels`, `VocabularyName`, etc.
- `JobExecutionSettings` — dict: `AllowDeferredExecution`, `DataAccessRoleArn`

### Async vs Sync Pattern

**All jobs are async** — `start_transcription_job` returns immediately with job info. Must poll.

**Polling pattern**:
```python
# Start job
response = transcribe.start_transcription_job(
    TranscriptionJobName=job_name,
    LanguageCode="en-US",
    Media={"MediaFileUri": "s3://bucket/audio.wav"},
    MediaFormat="wav"
)
# Poll until complete
import time
max_tries = 60
while max_tries > 0:
    status = transcribe.get_transcription_job(TranscriptionJobName=job_name)
    job_status = status["TranscriptionJob"]["TranscriptionJobStatus"]
    if job_status in ["COMPLETED", "FAILED"]:
        break
    time.sleep(10)
```

**Waiter available**:
```python
waiter = transcribe.get_waiter("transcription_job_completed")
waiter.wait(TranscriptionJobName=job_name)
```

### Audio Format Requirements

| Property | Value |
|---|---|
| Supported formats | mp3, mp4, wav, flac, ogg, amr, webm, m4a |
| Sample rate | 16kHz recommended, any supported |
| Max file size | 2 GB |
| Max duration | Unlimited |
| Delivery | Via S3 bucket + `TranscriptFileUri` in response |

### Authentication

boto3 credential chain order:
1. `aws_access_key_id` + `aws_secret_access_key` env vars
2. `~/.aws/credentials` file
3. Assume role provider
4. AWS IAM Identity Center
5. ECS/EC2 IAM role

### Pricing Model

- **Pay per audio minute** — tiered by language
- Per-region pricing varies
- Speaker diarization adds cost
- PII redaction adds cost
- Check [AWS Transcribe pricing](https://aws.amazon.com/transcribe/pricing/) for current rates

### Key Gotcha — S3 Requirement

AWS Transcribe **cannot accept raw audio bytes directly** — must upload to S3 first and pass `MediaFileUri`. This is a critical architectural difference from Azure OpenAI Whisper. Requires:
1. S3 bucket (user-managed or app-managed)
2. Upload audio to S3 before starting job
3. Poll for completion
4. Download transcript JSON from returned `TranscriptFileUri`

### Key Patterns from Real Code

From [awsdocs/aws-doc-sdk-examples](https://github.com/awsdocs/aws-doc-sdk-examples/blob/6ff2068156ee2224c620bdef8941aadefad713fb/python/example_code/transcribe/transcribe_basics.py):
- Upload audio to S3 → start job → wait for completion → GET `TranscriptFileUri`
- `job_name` must be unique per account, use UUID or timestamp
- Use `TranscribeCompleteWaiter` (custom or built-in)
- For speaker labels: `Settings={'ShowSpeakerLabels': True, 'MaxSpeakerLabels': 10}`

---

## 3. Python Abstraction Layer Pattern

### Recommended Interface

```python
from abc import ABC, abstractmethod

class TranscriptionProvider(ABC):
    @abstractmethod
    def transcribe(
        self,
        audio_bytes: bytes,
        filename: str,
        language: str | None = None,
        **options
    ) -> TranscriptionResult:
        pass

class TranscriptionResult:
    text: str
    language: str | None
    segments: list[Segment] | None
    raw: dict  # provider-specific response

class Segment:
    text: str
    start: float
    end: float
    speaker: str | None = None
```

### Provider Switching

```python
class CloudTranscriber:
    def __init__(self, provider: str, config: dict):
        if provider == "azure":
            self._impl = AzureOpenAIProvider(config)
        elif provider == "aws":
            self._impl = AWSProvider(config)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def transcribe(self, audio_bytes, **kwargs) -> TranscriptionResult:
        return self._impl.transcribe(audio_bytes, **kwargs)
```

### Unified Config Schema

```python
# Azure
{
{
    "provider": "azure",
    "api_key": "...",  # from keyring
    "endpoint": "https://resource.openai.azure.com",
    "deployment_name": "whisper-1",
    "api_version": "2025-04-01-preview"
}

# AWS
{
    "provider": "aws",
    "region": "us-east-1",
    "s3_bucket": "my-audio-bucket",
    # credentials via boto3 chain (env vars / ~/.aws/credentials / IAM)
}
```

### Profile Integration

Cloud modes map to `profile_resolver.py` profiles:
- `azure-whisper-1` -> Azure OpenAI Whisper, fast, decent quality
- `azure-gpt-4o-transcribe` -> Azure OpenAI GPT-4o, high accuracy
- `aws-transcribe` -> AWS Transcribe, full AWS ecosystem integration

---

## 4. Secure API Key Storage

### Windows Credential Manager via keyring

**Package**: `keyring` — auto-selects Windows Credential Locker on Windows

```python
import keyring

# Store
keyring.set_password("SpanglishDictation", "azure_api_key", key_value)

# Retrieve
key = keyring.get_password("SpanglishDictation", "azure_api_key")

# Delete
keyring.delete_password("SpanglishDictation", "azure_api_key")
```

**Access**: Control Panel -> Credential Manager -> Windows Credentials -> SpanglishDictation

**Security model**: Protected by Windows user account. Any Python app running as same user can access (same as macOS Keychain behavior — trust model is same as installed apps).

### Alternative: DPAPI via win32crypt

```python
import win32crypt
import base64

# Encrypt (uses current user DPAPI)
encrypted = win32crypt.CryptProtectData(api_key.encode())

# Decrypt
decrypted = win32crypt.CryptUnprotectData(encrypted)
```

DPAPI ties encryption to the Windows user account — only same user can decrypt. No separate credential manager needed. More portable than keyring (no dependency on Windows Credential Locker).

### Recommended Approach for This Project

**Tiered strategy**:

1. **Primary**: `keyring` — works out-of-box on Windows, user can manage via Credential Manager UI
2. **Fallback**: DPAPI via `pywin32` — for environments without keyring backend
3. **Never store plaintext** in settings.json or config files

```python
def get_cloud_api_key(provider: str) -> str | None:
    # Try keyring first
    key = keyring.get_password("SpanglishDictation", f"{provider}_api_key")
    if key:
        return key
    # Fallback: read from encrypted config (DPAPI-wrapped)
    return get_from_dpapi_store(f"{provider}_api_key")
```

### AWS-Specific Auth

AWS does NOT use API keys in code. Use one of:
1. **Env vars** (for CI/development): `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
2. **Named profile** (for shared machines): `~/.aws/credentials` + `aws configure`
3. **IAM role** (for EC2/ECS): Instance profile with `AmazonTranscribeFullAccess` policy

**For desktop app**: Recommend using named profile — user runs `aws configure` once, app picks up credentials automatically. No keyring needed for AWS.

---

## 5. Gotchas and Edge Cases

### Azure OpenAI
- **API version required** — always include `?api-version=...` query param
- **Deployment name != model name** — URL path uses deployment name, not model name. Response format selection uses model name.
- **Diarization model > 30s**: Must set `chunking_strategy=auto`, otherwise failure
- **opus codec unsupported** — Azure does not accept opus-encoded audio. Convert to mp3/wav/flac first.
- **Timeout**: Set read timeout to 30+ minutes for long audio files
- **Concurrent jobs**: Check quota for account tier

### AWS Transcribe
- **S3 required** — cannot stream raw audio. Must upload to S3 first.
- **Job name uniqueness** — must be unique per account. Use UUID or timestamp suffix.
- **Transcript URI expires** — service-managed URIs valid 15 minutes. Re-fetch via `get_transcription_job` if expired.
- **Language codes** — use exact format (e.g., `es-US`, not `es` or `spanish`)
- **boto3 dependency** — adds ~50MB to bundle size. Consider `boto3-stubs` for type hints.
- **Region** — transcribe is not available in all regions. Check AWS region table.

### Audio Format Conversion
- App currently captures audio — need conversion pipeline for cloud providers
- Azure: mp3/wav/m4a preferred
- AWS: mp3/wav/flac/m4a
- Both support 16kHz as optimal sample rate

### PrivacyGuard Integration
- Cloud transcription requires **whitelisting specific endpoints** in PrivacyGuard
- Azure: `*.openai.azure.com` (HTTPS only)
- AWS: `*.amazonaws.com` (S3 + transcribe)
- Must bypass monkey-patch for these domains only
- Consider: domain-level allowlist, not just IP-level

### Error Handling Patterns
- Azure: HTTP status codes + JSON error body with `error.message`
- AWS: `ClientError` exception with `response['Error']['Code']` and `response['Error']['Message']`
- Both: implement retry with exponential backoff for transient errors (429, 500, 503)
- Both: timeout handling for long-running jobs

### Latency Considerations
- Azure Whisper: ~1-3x realtime for transcription (30s audio -> 30-90s processing)
- AWS Transcribe: ~0.3x realtime (30s audio -> ~10s via S3 path)
- Both: cloud processing time >> local whisper.cpp (which is ~0.1-0.5x realtime on CPU)
- User experience: cloud options are not faster, but may produce higher accuracy

---

## 6. Sources

| Source | URL |
|---|---|
| OpenAI Python SDK audio transcription | https://github.com/openai/openai-python/blob/main/src/openai/resources/audio/transcriptions.py |
| OpenAI speech_to_text example | https://github.com/openai/openai-python/blob/main/examples/speech_to_text.py |
| Azure OpenAI Transcribe connector (real impl) | https://github.com/murtaza-nasir/speakr/blob/master/src/services/transcription/connectors/azure_openai_transcribe.py |
| AWS Transcribe boto3 reference | https://docs.aws.amazon.com/boto3/latest/reference/services/transcribe/client/start_transcription_job.html |
| AWS Transcribe examples | https://github.com/awsdocs/aws-doc-sdk-examples/blob/main/python/example_code/transcribe/transcribe_basics.py |
| keyring docs | https://keyring.readthedocs.io/en/latest/ |
| keyring Windows Credential Locker | https://github.com/jaraco/keyring/ |
| boto3 credential chain | https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html |
| RAGStack TranscribeClient (async wrapper) | https://github.com/HatmanStack/RAGStack-Lambda/commit/b2ecd4cd868465b2bf4c6bb6a6f33cd3c1390175 |

---

## 7. Summary Findings

| Aspect | Azure OpenAI Whisper | AWS Transcribe |
|---|---|---|
| **SDK** | `openai` v1.x or raw `httpx` | `boto3` |
| **Auth** | `api-key` header | boto3 credential chain (no API key) |
| **Endpoint** | `https://{resource}.openai.azure.com/openai/deployments/{deploy}/audio/transcriptions?api-version={v}` | `boto3.client("transcribe")` |
| **Upload** | Direct bytes (multipart) | S3 bucket required (audio must be uploaded first) |
| **Async** | No (sync request/response) | Yes (poll with `get_transcription_job`) |
| **Max file size** | 25 MB | 2 GB |
| **Max duration** | ~1500s | Unlimited |
| **Speaker diarization** | `gpt-4o-transcribe-diarize` model | `ShowSpeakerLabels` setting |
| **Audio formats** | mp3, mp4, mpeg, mpga, m4a, wav, webm | mp3, mp4, wav, flac, ogg, amr, webm, m4a |
| **Pricing** | Per-token (Azure OpenAI tier) | Per audio-minute (tiered by language) |
| **Complexity** | Simpler (direct API) | More complex (S3 + polling) |
| **Recommended for** | Quick setup, familiar API, Spanglish fine-tuning potential | Enterprise AWS users, large audio files, PII redaction |
