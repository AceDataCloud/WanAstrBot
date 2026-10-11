"""Wan 3 video submission and existing-task lookup for AstrBot."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

API_BASE = "https://api.acedata.cloud"
RESOLUTIONS = {"480P", "720P", "1080P"}
RATIOS = {"16:9", "4:3", "1:1", "3:4", "9:16"}
FAILED = {"failed", "error", "cancelled", "canceled", "rejected"}


class _NoRedirect(HTTPRedirectHandler):
    """Never forward the configured key to another host."""

    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


OPENER = build_opener(_NoRedirect)


class WanError(RuntimeError):
    """An error safe to return to an AstrBot conversation."""


def _valid_https_url(url: str) -> bool:
    try:
        parsed = urlsplit(url)
    except ValueError:
        return False
    return bool(
        parsed.scheme == "https"
        and parsed.netloc
        and not parsed.username
        and not parsed.password
    )


class WanClient:
    """Submit one Wan 3 video or query an existing task."""

    def __init__(self, api_key: str) -> None:
        token = api_key.strip()
        if (
            not token
            or token.lower().startswith("bearer ")
            or token.startswith("platform-")
        ):
            raise WanError(
                "Set an Ace Data Cloud generation API key in plugin settings."
            )
        self._api_key = token

    def _post(self, path: str, payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
        request = Request(
            API_BASE + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": "Bearer " + self._api_key,
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "AceDataCloudAstrBot/0.1.0",
            },
            method="POST",
        )
        try:
            with OPENER.open(request, timeout=90) as response:
                body = json.load(response)
                header_trace = response.headers.get(
                    "x-trace-id", ""
                ) or response.headers.get("x-request-id", "")
        except HTTPError as exc:
            raise WanError(
                f"Ace Data Cloud returned HTTP {exc.code}. Check service access and request history."
            ) from None
        except (URLError, TimeoutError, OSError):
            raise WanError(
                "The API connection failed. Check request history before submitting another video."
            ) from None
        except (ValueError, UnicodeError):
            raise WanError(
                "The API returned invalid JSON. Check request history before retrying."
            ) from None
        if not isinstance(body, dict):
            raise WanError("The API returned an unexpected response format.")
        return body, str(body.get("trace_id") or header_trace)

    async def submit(
        self,
        prompt: str,
        duration: int = 2,
        resolution: str = "480P",
        ratio: str = "16:9",
        image_url: str = "",
    ) -> dict[str, Any]:
        """Submit one asynchronous silent Wan 3 video without a paid retry."""
        prompt = prompt.strip()
        if not prompt or len(prompt) > 4000:
            raise WanError("Provide a video prompt of 1–4000 characters.")
        if (
            not isinstance(duration, int)
            or isinstance(duration, bool)
            or not 2 <= duration <= 30
        ):
            raise WanError("Duration must be 2–30 seconds.")
        if resolution not in RESOLUTIONS:
            raise WanError("Resolution must be 480P, 720P, or 1080P.")
        if ratio not in RATIOS | ({"adaptive"} if image_url else set()):
            raise WanError("Choose a model-supported aspect ratio.")
        if image_url and not _valid_https_url(image_url):
            raise WanError("Provide an authorized HTTPS first-frame image URL.")
        payload: dict[str, Any] = {
            "action": "image2video" if image_url else "text2video",
            "model": "wan3.0-video",
            "prompt": prompt,
            "duration": duration,
            "resolution": resolution,
            "ratio": ratio,
            "audio": False,
            "prompt_extend": False,
            "async": True,
        }
        if image_url:
            payload["media"] = [{"type": "first_frame", "url": image_url}]
        body, trace_id = await asyncio.to_thread(self._post, "/wan/videos", payload)
        if body.get("success") is False or body.get("error"):
            raise WanError(
                "Video submission was rejected. Check request history before trying again."
            )
        task_id = body.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            raise WanError(
                "No task ID was returned. Check request history before submitting again."
            )
        return {
            "status": "submitted",
            "task_id": task_id,
            "trace_id": trace_id,
            "next_step": "Query this same task ID; do not submit another video while it is pending.",
        }

    async def query(self, task_id: str) -> dict[str, Any]:
        """Return the final video URL only after terminal task success."""
        task_id = task_id.strip()
        if not task_id or len(task_id) > 128:
            raise WanError("Pass the exact task ID from Wan submission.")
        body, trace_id = await asyncio.to_thread(
            self._post, "/wan/tasks", {"id": task_id, "action": "retrieve"}
        )
        if body.get("success") is False or body.get("error"):
            raise WanError("Task lookup failed. Check request history.")
        response = body.get("response")
        if isinstance(response, str):
            try:
                response = json.loads(response)
            except ValueError:
                response = None
        if not isinstance(response, dict):
            response = {}
        data = response.get("data")
        if not isinstance(data, dict):
            data = {}
        trace_id = str(response.get("trace_id") or body.get("trace_id") or trace_id)
        state = str(data.get("status") or response.get("status") or "").lower()
        if state in FAILED or response.get("success") is False or response.get("error"):
            return {
                "task_id": task_id,
                "trace_id": trace_id,
                "status": "failed",
                "success": False,
                "video_url": "",
            }
        video_url = data.get("video_url")
        if (
            not body.get("finished_at")
            or response.get("success") is not True
            or state != "succeeded"
        ):
            return {
                "task_id": task_id,
                "trace_id": trace_id,
                "status": "pending",
                "success": False,
                "video_url": "",
            }
        if not isinstance(video_url, str) or not _valid_https_url(video_url):
            return {
                "task_id": task_id,
                "trace_id": trace_id,
                "status": "failed",
                "success": False,
                "video_url": "",
            }
        cost = response.get("cost")
        public_cost = (
            {
                key: cost[key]
                for key in ("amount", "list_amount", "currency")
                if key in cost
            }
            if isinstance(cost, dict)
            else {}
        )
        return {
            "task_id": task_id,
            "trace_id": trace_id,
            "status": "succeeded",
            "success": True,
            "video_url": video_url,
            "model": str(data.get("model") or ""),
            "cost": public_cost,
        }
