"""Wan video tools for AstrBot through Ace Data Cloud."""

from __future__ import annotations

import json

from astrbot.api import AstrBotConfig
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star

from .client import WanClient, WanError


class WanPlugin(Star):
    """Expose one video submission and one existing-task lookup tool."""

    def __init__(self, context: Context, config: AstrBotConfig) -> None:
        super().__init__(context)
        self.config = config

    @filter.llm_tool(name="wan_generate_video")
    async def wan_generate_video(
        self,
        event: AstrMessageEvent,
        prompt: str,
        duration: int = 2,
        resolution: str = "480P",
        ratio: str = "16:9",
        image_url: str = "",
    ) -> str:
        """Submit one billable Wan 3 text or first-frame video job.

        Args:
            prompt(string): Description of the desired video.
            duration(number): 2–30 output seconds.
            resolution(string): 480P, 720P, or 1080P.
            ratio(string): Output ratio such as 16:9 or 9:16.
            image_url(string): Optional authorized HTTPS first-frame image.

        Returns:
            JSON submission status and task ID, never a finished-video claim.
        """
        try:
            result = await WanClient(self.config.get("api_key", "")).submit(
                prompt, duration, resolution, ratio, image_url
            )
        except WanError as exc:
            result = {"status": "error", "message": str(exc)}
        return json.dumps(result, ensure_ascii=False)

    @filter.llm_tool(name="wan_get_task")
    async def wan_get_task(self, event: AstrMessageEvent, task_id: str) -> str:
        """Query an existing Wan task without generating another video.

        Args:
            task_id(string): Exact task ID from wan_generate_video.

        Returns:
            JSON task status and final video URL only after terminal success.
        """
        try:
            result = await WanClient(self.config.get("api_key", "")).query(task_id)
        except WanError as exc:
            result = {"status": "error", "message": str(exc), "task_id": task_id}
        return json.dumps(result, ensure_ascii=False)
