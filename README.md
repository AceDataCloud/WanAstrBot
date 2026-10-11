# Wan video for AstrBot

Generate one Wan 3 video in an AstrBot conversation through your own Ace Data Cloud account. `wan_generate_video` submits one text or first-frame video job; `wan_get_task` queries the same task until its final video is ready.

[简体中文指南](readme/README_zh_Hans.md) · [Wan Videos API](https://platform.acedata.cloud/documents/wan-videos) · [Wan Tasks API](https://platform.acedata.cloud/documents/wan-tasks) · [Current prices](https://platform.acedata.cloud/services/wan)

## Find and install

In AstrBot WebUI, open **Extensions → Plugins → AstrBot Plugin Market** and search **Wan**. Confirm the card says **Wan by Ace Data Cloud**, the author is **acedatacloud**, and the logo matches the [current Wan service icon](https://cdn.acedata.cloud/a033884259.png). Install it, then check **Installed** for load errors.

The official AstrBot Cloud listing is pending. After the source release is merged, **Installed → Install (+) → Install from URL** with `https://github.com/AceDataCloud/WanAstrBot` can preview it. A URL installation does not prove market publication.

## Configure your key

In [Ace Data Cloud Applications](https://platform.acedata.cloud/console/applications), copy a generation API key from your General application or create a key that permits both `/wan/videos` and `/wan/tasks`. Check current per-second pricing, duration, resolution, and balance before submitting. Paste the key into the plugin's **Ace Data Cloud generation API key with Wan access** setting. Do not add `Bearer ` or use a `platform-...` management token. AstrBot masks the field in WebUI but stores the original value in its data directory, which should be protected.

Select a chat model that supports tool calling. Allow both Wan tools in the conversation's profile and persona.

## Generate once, then query

Ask the bot:

> Use `wan_generate_video` exactly once to make a yellow paper kite rising over a calm green meadow. Use 2 seconds, 480P, 16:9. Show me the task ID.

The tool sends one asynchronous `POST /wan/videos` request for `wan3.0-video` with `audio: false` and returns `status: submitted` with a task ID. Keep the ID and ask:

> Use `wan_get_task` with the exact task ID `<task_id>`. Tell me its status and final video URL. Do not generate another video.

If pending, query the same ID later. Only `status: succeeded`, `success: true`, and a final HTTPS video URL indicate completion. The plugin never retries a paid submission automatically.

The first version supports Wan 3 text-to-video and one authorized HTTPS first-frame `image_url`. Duration is 2–30 seconds; resolution is `480P`, `720P`, or `1080P`. The plugin explicitly disables audio and automatic prompt expansion to keep the request predictable. First-frame input uses Wan 3 `media`; reference video/audio, multiple images, and the older Wan 2.6 models are outside this version.

## Verify and troubleshoot

Match a returned trace ID in Ace Data Cloud usage when available. A finished task may include public `cost` amounts in Credits; confirm the live usage row before treating an estimate as a charge. Task lookup reads an existing job and does not submit another generation.

| Symptom | Check |
| --- | --- |
| Plugin fails to load | AstrBot version, **Failed to Load Plugins**, and **Data & Logs → Logs**. |
| Tools are missing | Plugin enabled, both tools allowed in the active profile and persona, chat model supports tool calling. |
| HTTP 401/403 | Key type, both allowed API paths, and account access. |
| Network error after submission | Inspect request history before generating again; a timeout may already have created a paid task. |
| Pending task | Query the same task ID later. |
| Failed task | Use the task or trace ID to inspect request history. |

The key goes only to `https://api.acedata.cloud`; redirects are rejected. The plugin exposes the final video URL and public cost fields to the model, without raw internal data. It uses Python's standard library and needs no runtime package installation.

## Validation and brand asset

On official AstrBot `v4.28.2`, an isolated editable installation registered both tools. ChatUI submitted one `wan3.0-video` 2-second 480P silent text video and queried the same task ID twice; the first lookup was pending and the second returned success, with no second generation. The final MP4 responded HTTP 200, `video/mp4`, and decoded as H.264, 854×480, 2 seconds, with no audio track. The exact generation trace matched one successful `/wan/videos` usage row with 1.0512367491166077 Credits original and 0.946113074204947 Credits deducted. See the [sanitized evidence](tests/e2e-results.json). First-frame image and other settings were validated structurally but not generated. This is a local editable installation; official Cloud review, market installation, and a first call from a market installation remain open.

`logo.png` is the unmodified 200×200 [current Wan service icon](https://cdn.acedata.cloud/a033884259.png), SHA-256 `32d9897f4315f7f57456a47943e9f4567abe55dba10dd2e443617c89062a4aa4`.
