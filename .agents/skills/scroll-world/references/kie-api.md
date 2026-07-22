# Kie.ai API reference for Scroll World

Use this reference when modifying the helper, adding models, or diagnosing authentication,
uploads, task polling, credits, or downloads. Confirm the live official schema before
adding a new model; Kie.ai’s catalogue evolves.

Official documentation home: https://docs.kie.ai/

## Authentication and security

- Generation API base: `https://api.kie.ai`
- Upload API base: `https://kieai.redpandaai.co`
- Header: `Authorization: Bearer <API key>`
- Skill environment variable: `KIE_API_KEY`
- Never accept the key through a CLI argument because it can enter shell history/process
  listings.
- Never write the key into metadata, frontend code, prompts, `.env` files in a project,
  or generated pages.

Official documentation:

- Integration and security overview: https://docs.kie.ai/
- Common API and authentication: https://docs.kie.ai/common-api/quickstart
- File uploads: https://docs.kie.ai/file-upload-api/quickstart

## Codex cloud network policy

Kie.ai calls from a Codex cloud task require agent internet access. Use the narrowest
practical allowlist:

- `api.kie.ai` for credits, task creation, task polling, and download-link conversion;
- `kieai.redpandaai.co` for local media uploads and uploaded-file downloads;
- GET, POST, HEAD, and OPTIONS methods. POST is required for uploads, task creation, and
  download-link conversion.

Generated download URLs can use a temporary host returned at runtime. If that download
is blocked, add only the exact host shown in the task log, or retrieve the authenticated
download URL through `/api/v1/common/download-url` first. A proxy/tunnel `CONNECT 403`
occurs before the request reaches Kie.ai. Fix the cloud environment policy before
rotating or debugging the API key.

## Common endpoints

| Purpose | Method | Endpoint |
|---|---|---|
| Credits | GET | `/api/v1/chat/credit` |
| Create market task | POST | `/api/v1/jobs/createTask` |
| Query task | GET | `/api/v1/jobs/recordInfo?taskId=<id>` |
| Obtain temporary download URL | POST | `/api/v1/common/download-url` |
| Stream upload | POST | `https://kieai.redpandaai.co/api/file-stream-upload` |

Task states documented by Kie.ai: `waiting`, `queuing`, `generating`, `success`, `fail`.
Poll with exponential backoff and stop after 10–20 minutes depending on the model. Result
records return `resultJson` as a JSON string; common outputs contain `resultUrls`.

Official task query: https://docs.kie.ai/market/common/get-task-detail

## Temporary asset rules

- Upload and generated-result URLs are temporary; use the response `expiresAt` when
  present and download every accepted result immediately. Kie.ai's general retention
  policy is not a substitute for local storage.
- Use unique uploaded filenames to avoid Kie.ai cache/overwrite confusion.
- Local images/videos are uploaded before they are referenced in a generation request.
- Use stream upload for local binary files. Avoid Base64 for large files.
- Production websites must use locally stored/deployed media, never Kie.ai temporary URLs.

## Approved image models

### GPT Image 2 — default

- Model: `gpt-image-2-text-to-image`
- Endpoint: market task create
- Inputs used: `prompt`, `aspect_ratio`
- Purpose: cohesive scene stills and premium environmental renders.
- Docs: https://docs.kie.ai/market/gpt/gpt-image-2-text-to-image

### Nano Banana 2 — character/playful alternate

- Model: `nano-banana-2`
- Inputs used: `prompt`, `image_input`, `aspect_ratio`, `resolution`, `output_format`
- Purpose: character-forward or playful art direction.
- Use for the complete still set, not isolated scenes, to avoid style drift.
- Docs: https://docs.kie.ai/market/google/nanobanana2

## Approved video models

### Seedance 2.0 — final default

- Model: `bytedance/seedance-2`
- Inputs used: `prompt`, `first_frame_url`, optional `last_frame_url`,
  `return_last_frame`, `generate_audio`, `resolution`, `aspect_ratio`, `duration`,
  `web_search`.
- First-frame, first-and-last-frame, and multimodal modes are mutually exclusive. The
  Scroll World helper uses only first-frame or first-and-last-frame modes.
- Kie.ai explicitly recommends first-and-last-frame mode when exact frame identity is
  required.
- Docs: https://docs.kie.ai/market/bytedance/seedance-2

### Seedance 2.0 Fast — fast preview

- Model: `bytedance/seedance-2-fast`
- Same first/last-frame payload shape as standard.
- Use for journey/prompt validation, not mixed into the final chain.
- Docs: https://docs.kie.ai/market/bytedance/seedance-2-fast

### Seedance 2.0 Mini — cheap previz

- Model: `bytedance/seedance-2-mini`
- Same first/last-frame payload shape as standard.
- Use to test pacing and seam logic before final spend.
- Docs: https://docs.kie.ai/market/bytedance/seedance-2-mini

### Wan 2.7 image-to-video — continuation/fallback

- Model: `wan/2-7-image-to-video`
- Modes:
  - first frame: `first_frame_url`
  - first and last: `first_frame_url` + `last_frame_url`
  - video continuation: `first_clip_url`
- Inputs used: `prompt`, `negative_prompt`, `resolution`, `duration`, `prompt_extend`,
  `watermark`, optional `seed`.
- Use at 1080p for a Wan-native chain or as an explicitly accepted fallback.
- Do not mix continuation with frame inputs in one request.
- Docs: https://docs.kie.ai/market/wan/2-7-image-to-video

## Paid-task retry policy

Task creation can consume credits. Do not automatically retry a creation request after an
ambiguous network timeout: the server may have accepted it even when the client did not
receive the task ID. Check Kie.ai task history first.

Safe to retry with backoff:

- credit checks;
- task status queries;
- download-link conversion;
- uploads that use unique filenames, after confirming the first upload did not return a
  usable URL.

Require human review before retrying:

- generation task creation with an ambiguous outcome;
- any failed task where the failure reason suggests policy, malformed input, or depleted
  credits;
- an expired result that would require a new paid generation.

## Adding another model

1. Confirm current official Kie.ai documentation.
2. Confirm it supports the required first/last frames or video continuation.
3. Add a model-specific payload adapter to `scripts/kie_api.py`; never assume another
   model accepts Seedance/Wan field names.
4. Add offline payload assertions to `run_self_test()`.
5. Run `self-test`, `--dry-run`, and one paid calibration clip after user approval.
6. Keep one model across a complete chain unless the user explicitly accepts drift.
