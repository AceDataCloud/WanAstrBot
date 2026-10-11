"""Wan 3 request and terminal-result boundaries."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from client import WanClient, WanError


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.headers = {"x-trace-id": "trace-wan"}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, *_):
        return json.dumps(self.payload).encode()


@pytest.mark.asyncio
async def test_submit_sends_one_async_silent_video_request():
    calls = []

    def fake_open(request, timeout):
        calls.append((request.full_url, json.loads(request.data), timeout))
        return FakeResponse({"task_id": "task-123"})

    with patch("client.OPENER.open", side_effect=fake_open):
        result = await WanClient("test-key").submit("A paper kite rises")
    assert calls == [
        (
            "https://api.acedata.cloud/wan/videos",
            {
                "action": "text2video",
                "model": "wan3.0-video",
                "prompt": "A paper kite rises",
                "duration": 2,
                "resolution": "480P",
                "ratio": "16:9",
                "audio": False,
                "prompt_extend": False,
                "async": True,
            },
            90,
        )
    ]
    assert result["status"] == "submitted"
    assert result["task_id"] == "task-123"
    assert "video_url" not in result


@pytest.mark.asyncio
async def test_first_frame_uses_wan3_media_contract():
    with patch(
        "client.OPENER.open", return_value=FakeResponse({"task_id": "task-456"})
    ) as opening:
        await WanClient("test-key").submit(
            "A kite rises", image_url="https://example.org/kite.png"
        )
    payload = json.loads(opening.call_args.args[0].data)
    assert payload["action"] == "image2video"
    assert payload["media"] == [
        {"type": "first_frame", "url": "https://example.org/kite.png"}
    ]


@pytest.mark.asyncio
async def test_lookup_withholds_preview_and_internal_fields():
    pending = {"id": "task-123", "finished_at": None, "response": None}
    preview = {
        "finished_at": None,
        "response": {
            "success": True,
            "data": {
                "status": "succeeded",
                "video_url": "https://cdn.example.org/preview.mp4",
            },
        },
    }
    finished = {
        "finished_at": 123.0,
        "response": {
            "success": True,
            "data": {
                "status": "succeeded",
                "video_url": "https://cdn.example.org/final.mp4",
                "model": "wan3.0-video",
                "supplier": "internal-only",
            },
            "cost": {
                "amount": 0.946,
                "list_amount": 1.051,
                "currency": "credit",
                "supplier": "internal-only",
            },
        },
    }
    failed = {
        "finished_at": 123.0,
        "response": {
            "success": False,
            "data": {
                "status": "failed",
                "video_url": "https://cdn.example.org/preview.mp4",
            },
        },
    }
    with patch(
        "client.OPENER.open",
        side_effect=[
            FakeResponse(pending),
            FakeResponse(preview),
            FakeResponse(finished),
            FakeResponse(failed),
        ],
    ) as opening:
        first = await WanClient("test-key").query("task-123")
        second = await WanClient("test-key").query("task-123")
        last = await WanClient("test-key").query("task-123")
        unsuccessful = await WanClient("test-key").query("task-123")
    assert opening.call_count == 4
    assert first["status"] == second["status"] == "pending"
    assert first["video_url"] == second["video_url"] == ""
    assert last["status"] == "succeeded"
    assert last["video_url"] == "https://cdn.example.org/final.mp4"
    assert last["cost"] == {
        "amount": 0.946,
        "list_amount": 1.051,
        "currency": "credit",
    }
    assert "supplier" not in str(last)
    assert unsuccessful["status"] == "failed"
    assert unsuccessful["video_url"] == ""


@pytest.mark.asyncio
async def test_invalid_inputs_never_submit_a_paid_job():
    client = WanClient("test-key")
    for kwargs in (
        {"prompt": " "},
        {"prompt": "A kite", "duration": 1},
        {"prompt": "A kite", "resolution": "2K"},
        {"prompt": "A kite", "ratio": "adaptive"},
        {"prompt": "A kite", "image_url": "http://example.org/kite.png"},
    ):
        with patch("client.OPENER.open") as opening, pytest.raises(WanError):
            await client.submit(**kwargs)
        assert opening.call_count == 0
