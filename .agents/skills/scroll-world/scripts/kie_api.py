#!/usr/bin/env python3
"""Small, dependency-free Kie.ai client for the Scroll World production pipeline.

The API key is read only from KIE_API_KEY. It is never accepted as a CLI argument,
written to metadata, or printed. Use ``self-test`` and ``--dry-run`` without a key.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any


API_BASE = os.environ.get("KIE_API_BASE", "https://api.kie.ai").rstrip("/")
UPLOAD_BASE = os.environ.get(
    "KIE_UPLOAD_BASE", "https://kieai.redpandaai.co"
).rstrip("/")
OFFICIAL_DOCS = "https://docs.kie.ai/"

VIDEO_ALIASES = {
    "standard": "bytedance/seedance-2",
    "fast": "bytedance/seedance-2-fast",
    "preview": "bytedance/seedance-2-mini",
    "continuation": "wan/2-7-image-to-video",
    "fallback": "wan/2-7-image-to-video",
}
IMAGE_ALIASES = {
    "standard": "gpt-image-2-text-to-image",
    "character": "nano-banana-2",
}
PENDING_STATES = {"waiting", "queuing", "generating"}
SUCCESS_STATES = {"success"}
FAIL_STATES = {"fail", "failed", "error"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}


class KieError(RuntimeError):
    """A safe, user-facing Kie.ai client error."""


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def pretty_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def resolve_model(name: str, kind: str) -> str:
    aliases = IMAGE_ALIASES if kind == "image" else VIDEO_ALIASES
    return aliases.get(name, name)


def load_prompt(args: argparse.Namespace) -> str:
    if getattr(args, "prompt_file", None):
        prompt = pathlib.Path(args.prompt_file).read_text(encoding="utf-8").strip()
    else:
        prompt = (getattr(args, "prompt", None) or "").strip()
    if not prompt:
        raise KieError("Prompt is empty.")
    return prompt


def validate_local_media(value: str | None, allowed: set[str], label: str) -> None:
    if not value or value.startswith(("https://", "http://")):
        return
    path = pathlib.Path(value)
    if not path.is_file():
        raise KieError(f"{label} file not found: {path}")
    if path.suffix.lower() not in allowed:
        supported = ", ".join(sorted(allowed))
        raise KieError(f"{label} must use one of: {supported}")


def extract_result_urls(record: dict[str, Any]) -> list[str]:
    raw: Any = record.get("resultJson")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            raw = {"resultUrl": raw}
    if raw is None:
        raw = record.get("result") or record.get("output") or {}

    urls: list[str] = []

    def visit(value: Any, key: str = "") -> None:
        if isinstance(value, str):
            if value.startswith(("https://", "http://")) and (
                "url" in key.lower() or not key
            ):
                urls.append(value)
            return
        if isinstance(value, list):
            for item in value:
                visit(item, key)
            return
        if isinstance(value, dict):
            for child_key, child in value.items():
                visit(child, child_key)

    visit(raw)
    return list(dict.fromkeys(urls))


def build_image_payload(
    model: str,
    prompt: str,
    aspect_ratio: str,
    resolution: str,
    output_format: str,
) -> dict[str, Any]:
    model = resolve_model(model, "image")
    inputs: dict[str, Any] = {"prompt": prompt, "aspect_ratio": aspect_ratio}
    if model == "nano-banana-2":
        inputs.update(
            {
                "image_input": [],
                "resolution": resolution,
                "output_format": output_format,
            }
        )
    return {"model": model, "input": inputs}


def build_video_payload(
    model: str,
    prompt: str,
    first_frame_url: str | None,
    last_frame_url: str | None,
    first_clip_url: str | None,
    aspect_ratio: str,
    resolution: str,
    duration: int,
    negative_prompt: str,
    seed: int | None,
) -> dict[str, Any]:
    model = resolve_model(model, "video")
    if first_clip_url and (first_frame_url or last_frame_url):
        raise KieError("Use either --first-clip or frame inputs, not both.")
    if last_frame_url and not first_frame_url:
        raise KieError("--last-frame requires --first-frame.")

    if model == "wan/2-7-image-to-video":
        inputs: dict[str, Any] = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "resolution": resolution,
            "duration": duration,
            "prompt_extend": True,
            "watermark": False,
        }
        if first_clip_url:
            inputs["first_clip_url"] = first_clip_url
        else:
            if first_frame_url:
                inputs["first_frame_url"] = first_frame_url
            if last_frame_url:
                inputs["last_frame_url"] = last_frame_url
        if seed is not None:
            inputs["seed"] = seed
    elif model.startswith("bytedance/seedance-2"):
        if first_clip_url:
            raise KieError("Seedance aliases do not accept --first-clip; use Wan 2.7.")
        inputs = {
            "prompt": prompt,
            "return_last_frame": False,
            "generate_audio": False,
            "resolution": resolution,
            "aspect_ratio": aspect_ratio,
            "duration": duration,
            "web_search": False,
        }
        if first_frame_url:
            inputs["first_frame_url"] = first_frame_url
        if last_frame_url:
            inputs["last_frame_url"] = last_frame_url
    else:
        raise KieError(
            f"Unsupported video model '{model}'. Add an explicit payload adapter before use."
        )
    return {"model": model, "input": inputs}


class KieClient:
    def __init__(self, *, dry_run: bool = False) -> None:
        self.dry_run = dry_run
        self.api_key = os.environ.get("KIE_API_KEY", "")
        if not self.api_key and not dry_run:
            raise KieError(
                "KIE_API_KEY is not set. Configure it in your environment; do not pass it in chat or on the command line."
            )

    def _headers(self, *, json_body: bool = False) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if json_body:
            headers["Content-Type"] = "application/json"
        return headers

    def request_json(
        self,
        method: str,
        url: str,
        payload: dict[str, Any] | None = None,
        *,
        retries: int = 3,
        timeout: int = 60,
    ) -> dict[str, Any]:
        body = compact_json(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            url,
            data=body,
            method=method,
            headers=self._headers(json_body=payload is not None),
        )
        delay = 2.0
        for attempt in range(retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    raw = response.read().decode("utf-8")
                parsed = json.loads(raw)
                if not isinstance(parsed, dict):
                    raise KieError("Kie.ai returned an unexpected non-object response.")
                return parsed
            except urllib.error.HTTPError as exc:
                raw = exc.read().decode("utf-8", errors="replace")
                retryable = exc.code == 429 or 500 <= exc.code < 600
                if retryable and attempt < retries:
                    retry_after = exc.headers.get("Retry-After")
                    wait_for = float(retry_after) if retry_after else delay
                    time.sleep(min(wait_for, 30.0))
                    delay = min(delay * 2, 30.0)
                    continue
                message = raw[:500] if raw else exc.reason
                raise KieError(f"Kie.ai HTTP {exc.code}: {message}") from None
            except urllib.error.URLError as exc:
                if attempt < retries:
                    time.sleep(delay)
                    delay = min(delay * 2, 30.0)
                    continue
                raise KieError(f"Kie.ai network error: {exc.reason}") from None
            except json.JSONDecodeError as exc:
                raise KieError(f"Kie.ai returned invalid JSON: {exc}") from None
        raise KieError("Kie.ai request failed.")

    def credits(self) -> dict[str, Any]:
        if self.dry_run:
            return {"method": "GET", "url": f"{API_BASE}/api/v1/chat/credit"}
        response = self.request_json("GET", f"{API_BASE}/api/v1/chat/credit")
        if response.get("code") != 200:
            code = response.get("code", "unknown")
            message = response.get("msg") or "unexpected response"
            raise KieError(f"Kie.ai credit/auth check failed ({code}): {message}")
        balance = response.get("data")
        if not isinstance(balance, (int, float)) or isinstance(balance, bool):
            raise KieError("Kie.ai authenticated but returned an invalid credit balance.")
        return response

    def upload_file(self, file_path: str, upload_path: str = "scroll-world") -> str:
        path = pathlib.Path(file_path)
        if not path.is_file():
            raise KieError(f"Upload file not found: {path}")
        if path.stat().st_size > 120 * 1024 * 1024:
            raise KieError("Upload exceeds the helper's 120 MB safety limit.")
        unique_name = f"{uuid.uuid4().hex[:10]}-{path.name}"
        if self.dry_run:
            return f"https://example.invalid/{upload_path}/{unique_name}"

        boundary = f"----scrollworld{uuid.uuid4().hex}"
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        prefix = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{unique_name}"\r\n'
            f"Content-Type: {mime}\r\n\r\n"
        ).encode("utf-8")
        middle = (
            f"\r\n--{boundary}\r\n"
            f'Content-Disposition: form-data; name="uploadPath"\r\n\r\n'
            f"{upload_path}\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="fileName"\r\n\r\n'
            f"{unique_name}\r\n"
            f"--{boundary}--\r\n"
        ).encode("utf-8")
        data = prefix + path.read_bytes() + middle
        headers = self._headers()
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        request = urllib.request.Request(
            f"{UPLOAD_BASE}/api/file-stream-upload",
            data=data,
            method="POST",
            headers=headers,
        )
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            raise KieError(f"Kie.ai upload HTTP {exc.code}: {raw[:500]}") from None
        except (urllib.error.URLError, json.JSONDecodeError) as exc:
            raise KieError(f"Kie.ai upload failed: {exc}") from None
        if result.get("success") is False or result.get("code") != 200:
            code = result.get("code", "unknown")
            message = result.get("msg") or "unexpected response"
            raise KieError(f"Kie.ai upload failed ({code}): {message}")
        data_obj = result.get("data") or {}
        url = data_obj.get("downloadUrl") or data_obj.get("fileUrl")
        if not url:
            raise KieError(f"Upload succeeded but no usable URL was returned: {result}")
        return str(url)

    def source_url(self, value: str | None, upload_path: str) -> str | None:
        if not value:
            return None
        if value.startswith(("https://", "http://")):
            return value
        return self.upload_file(value, upload_path)

    def create_task(self, payload: dict[str, Any]) -> str:
        if self.dry_run:
            print(pretty_json({"request": payload, "url": f"{API_BASE}/api/v1/jobs/createTask"}))
            return "dry_run_task"
        # Paid create calls are intentionally not retried automatically. A timeout can
        # be ambiguous; blind retrying could create and charge for a duplicate task.
        response = self.request_json(
            "POST", f"{API_BASE}/api/v1/jobs/createTask", payload, retries=0
        )
        task_id = ((response.get("data") or {}).get("taskId"))
        if not task_id:
            raise KieError(f"Kie.ai did not return a taskId: {response}")
        return str(task_id)

    def task(self, task_id: str) -> dict[str, Any]:
        query = urllib.parse.urlencode({"taskId": task_id})
        response = self.request_json(
            "GET", f"{API_BASE}/api/v1/jobs/recordInfo?{query}"
        )
        data = response.get("data")
        if not isinstance(data, dict):
            raise KieError(f"Kie.ai returned no task record for {task_id}: {response}")
        return data

    def wait(self, task_id: str, *, timeout: int = 1200) -> dict[str, Any]:
        started = time.monotonic()
        delay = 3.0
        last_line = ""
        while True:
            record = self.task(task_id)
            state = str(record.get("state", "")).lower()
            progress = record.get("progress")
            line = f"{task_id}: {state or 'unknown'}"
            if progress is not None:
                line += f" ({progress}%)"
            if line != last_line:
                print(line, file=sys.stderr, flush=True)
                last_line = line
            if state in SUCCESS_STATES:
                return record
            if state in FAIL_STATES:
                code = record.get("failCode") or "generation_failed"
                message = record.get("failMsg") or "Kie.ai generation failed."
                raise KieError(f"{code}: {message}")
            if state and state not in PENDING_STATES:
                raise KieError(f"Unknown Kie.ai task state '{state}' for {task_id}.")
            if time.monotonic() - started > timeout:
                raise KieError(
                    f"Timed out waiting for {task_id}. Check it with the 'task' command before resubmitting."
                )
            time.sleep(delay)
            delay = min(delay * 1.45, 20.0)

    def direct_download_url(self, generated_url: str) -> str:
        response = self.request_json(
            "POST",
            f"{API_BASE}/api/v1/common/download-url",
            {"url": generated_url},
            retries=2,
        )
        url = response.get("data")
        return str(url) if url else generated_url

    def download(self, generated_url: str, output_path: str) -> None:
        output = pathlib.Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        urls = [generated_url]
        try:
            urls.append(self.direct_download_url(generated_url))
        except KieError:
            pass
        last_error: Exception | None = None
        for url in list(dict.fromkeys(urls)):
            try:
                with urllib.request.urlopen(url, timeout=180) as response:
                    with output.open("wb") as handle:
                        while True:
                            chunk = response.read(1024 * 1024)
                            if not chunk:
                                break
                            handle.write(chunk)
                if output.stat().st_size == 0:
                    raise KieError("Downloaded file is empty.")
                return
            except (urllib.error.URLError, OSError, KieError) as exc:
                last_error = exc
        raise KieError(f"Could not download generated asset: {last_error}")


def attach_callback(payload: dict[str, Any], callback_url: str | None) -> None:
    if callback_url:
        payload["callBackUrl"] = callback_url


def finish_generation(
    client: KieClient,
    payload: dict[str, Any],
    *,
    output: str | None,
    metadata: str | None,
    timeout: int,
) -> None:
    task_id = client.create_task(payload)
    if client.dry_run:
        return
    record = client.wait(task_id, timeout=timeout)
    urls = extract_result_urls(record)
    if output:
        if not urls:
            raise KieError(f"Task {task_id} succeeded but returned no result URL.")
        client.download(urls[0], output)
    summary = {
        "taskId": task_id,
        "state": record.get("state"),
        "model": record.get("model"),
        "creditsConsumed": record.get("creditsConsumed"),
        "resultUrls": urls,
        "output": output,
    }
    if metadata:
        meta_path = pathlib.Path(metadata)
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(pretty_json({"summary": summary, "record": record}) + "\n", encoding="utf-8")
    print(pretty_json(summary))


def run_self_test() -> None:
    assert OFFICIAL_DOCS == "https://docs.kie.ai/"
    assert resolve_model("standard", "video") == "bytedance/seedance-2"
    assert resolve_model("preview", "video") == "bytedance/seedance-2-mini"
    assert resolve_model("character", "image") == "nano-banana-2"
    payload = build_video_payload(
        "standard",
        "test",
        "https://example.com/a.png",
        "https://example.com/b.png",
        None,
        "16:9",
        "720p",
        5,
        "flicker",
        None,
    )
    assert payload["input"]["generate_audio"] is False
    assert payload["input"]["last_frame_url"].endswith("b.png")
    wan = build_video_payload(
        "continuation",
        "test",
        None,
        None,
        "https://example.com/clip.mp4",
        "16:9",
        "1080p",
        5,
        "flicker",
        42,
    )
    assert wan["input"]["first_clip_url"].endswith("clip.mp4")
    urls = extract_result_urls(
        {"resultJson": '{"resultUrls":["https://example.com/out.mp4"]}'}
    )
    assert urls == ["https://example.com/out.mp4"]
    print("Kie API helper self-test passed.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true", help="Print generation payloads without API calls."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("self-test", help="Run offline payload and parser checks.")
    sub.add_parser("credits", help="Check remaining Kie.ai credits.")

    upload = sub.add_parser("upload", help="Upload a local file and print its temporary URL.")
    upload.add_argument("file")
    upload.add_argument("--path", default="scroll-world")

    task = sub.add_parser("task", help="Print one Kie.ai task record.")
    task.add_argument("task_id")

    wait = sub.add_parser("wait", help="Wait for an existing task and optionally download it.")
    wait.add_argument("task_id")
    wait.add_argument("--out")
    wait.add_argument("--meta")
    wait.add_argument("--timeout", type=int, default=1200)

    image = sub.add_parser("image", help="Generate and download one Kie.ai image.")
    image_prompt = image.add_mutually_exclusive_group(required=True)
    image_prompt.add_argument("--prompt")
    image_prompt.add_argument("--prompt-file")
    image.add_argument("--model", default="standard")
    image.add_argument("--aspect", default="3:2")
    image.add_argument("--resolution", default="2K")
    image.add_argument("--format", default="png", choices=["png", "jpg"])
    image.add_argument("--out", required=True)
    image.add_argument("--meta")
    image.add_argument("--callback-url")
    image.add_argument("--timeout", type=int, default=1200)

    video = sub.add_parser("video", help="Generate and download one frame-locked video.")
    video_prompt = video.add_mutually_exclusive_group(required=True)
    video_prompt.add_argument("--prompt")
    video_prompt.add_argument("--prompt-file")
    video.add_argument("--model", default="standard")
    video.add_argument("--first-frame")
    video.add_argument("--last-frame")
    video.add_argument("--first-clip")
    video.add_argument("--aspect", default="16:9")
    video.add_argument("--resolution", default="720p")
    video.add_argument("--duration", type=int, default=5, choices=[5, 10, 15])
    video.add_argument("--negative-prompt", default="flicker, jitter, blur, distortion, text, watermark")
    video.add_argument("--seed", type=int)
    video.add_argument("--out", required=True)
    video.add_argument("--meta")
    video.add_argument("--callback-url")
    video.add_argument("--timeout", type=int, default=1200)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "self-test":
            run_self_test()
            return 0
        client = KieClient(dry_run=args.dry_run)
        if args.command == "credits":
            print(pretty_json(client.credits()))
        elif args.command == "upload":
            print(client.upload_file(args.file, args.path))
        elif args.command == "task":
            print(pretty_json(client.task(args.task_id)))
        elif args.command == "wait":
            record = client.wait(args.task_id, timeout=args.timeout)
            urls = extract_result_urls(record)
            if args.out:
                if not urls:
                    raise KieError("Task succeeded but returned no result URL.")
                client.download(urls[0], args.out)
            if args.meta:
                pathlib.Path(args.meta).write_text(pretty_json(record) + "\n", encoding="utf-8")
            print(pretty_json(record))
        elif args.command == "image":
            payload = build_image_payload(
                args.model,
                load_prompt(args),
                args.aspect,
                args.resolution,
                args.format,
            )
            attach_callback(payload, args.callback_url)
            finish_generation(
                client,
                payload,
                output=args.out,
                metadata=args.meta,
                timeout=args.timeout,
            )
        elif args.command == "video":
            model = resolve_model(args.model, "video")
            validate_local_media(args.first_frame, IMAGE_EXTENSIONS, "First frame")
            validate_local_media(args.last_frame, IMAGE_EXTENSIONS, "Last frame")
            validate_local_media(args.first_clip, VIDEO_EXTENSIONS, "First clip")
            upload_path = f"scroll-world/{int(time.time())}"
            first = client.source_url(args.first_frame, upload_path)
            last = client.source_url(args.last_frame, upload_path)
            first_clip = client.source_url(args.first_clip, upload_path)
            resolution = args.resolution
            if model == "wan/2-7-image-to-video" and resolution == "720p":
                resolution = "1080p"
            payload = build_video_payload(
                model,
                load_prompt(args),
                first,
                last,
                first_clip,
                args.aspect,
                resolution,
                args.duration,
                args.negative_prompt,
                args.seed,
            )
            attach_callback(payload, args.callback_url)
            finish_generation(
                client,
                payload,
                output=args.out,
                metadata=args.meta,
                timeout=args.timeout,
            )
        return 0
    except KieError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
