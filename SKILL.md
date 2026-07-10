---
name: generate-video
description: "Generate a video from a text prompt and save it to a file using Azure AI Foundry (Sora 2). Use when the user asks to 'generate a video', 'create a video', 'make a clip', 'animate', or 'render a video' and wants it saved to a filename. Requires a prompt and an output filename; optional size and duration. Backed by the paul-ai-models Foundry deployment. Generation is async and takes ~1-5 minutes."
---

# generate-video

Generate a video from a text prompt and write it to a file, using the `sora-2`
deployment on the `paul-ai-models` Azure AI Foundry account. Sora 2 generation is
**asynchronous** — the script submits a job, polls until it finishes, then downloads
the MP4. Expect ~1-5 minutes per clip.

## When to use

The user wants a short video created from a description and saved locally — e.g.
"generate a video of a drone flyover of a canyon at sunrise and save it as canyon.mp4",
"make a 8-second clip of rain on a window".

Two things are always needed: **a prompt** and **an output filename**.

## Prerequisites

- `AZURE_OPENAI_API_KEY` in the environment. It is auto-loaded from
  `~/ai-models-out/foundry.env` if not already set, so this normally just works.
- The `sora-2` deployment on `paul-ai-models` (already provisioned).

## How to run

```bash
python3 ~/.config/opencode/skills/generate-video/scripts/generate_video.py \
  --prompt "PROMPT TEXT" --out FILENAME.mp4
```

Positional shorthand also works:

```bash
python3 ~/.config/opencode/skills/generate-video/scripts/generate_video.py "PROMPT TEXT" FILENAME.mp4
```

The script prints job status to stderr as it progresses (`queued` → `preprocessing`
→ `running` → `processing` → `succeeded`), then `OK: saved <size> <seconds>s video ->
<absolute path> (<KB>)` on success. If the filename has no extension, `.mp4` is
appended.

### Options

- `--prompt`, `-p` — the video description (required)
- `--out`, `-o` — output file path (required; `.mp4` added if missing)
- `--size`, `-s` — `720x1280` (portrait, default) or `1280x720` (landscape)
- `--seconds`, `-n` — clip length: `4` (default), `8`, or `12`
- `--timeout`, `-t` — max seconds to wait for the job (default `900`)

### Config overrides (env)

- `AZURE_OPENAI_VIDEO_ENDPOINT` — default `https://paul-ai-models.openai.azure.com/` (Sora lives on the `openai.azure.com` host; if only `AZURE_OPENAI_ENDPOINT` is set, its host is swapped in automatically)
- `AZURE_OPENAI_VIDEO_DEPLOYMENT` — default `sora-2`
- `AZURE_OPENAI_VIDEO_API_VERSION` — default `preview`

## Examples

```bash
# Landscape establishing shot, 8 seconds
python3 ~/.config/opencode/skills/generate-video/scripts/generate_video.py \
  -p "wide aerial shot of a misty pine forest at dawn, slow push in, cinematic" \
  -o ~/Videos/forest.mp4 -s 1280x720 -n 8

# Quick square clip
python3 ~/.config/opencode/skills/generate-video/scripts/generate_video.py \
  "a paper boat floating down a rain gutter, close up" boat.mp4 -s 720x1280 -n 4
```

## Notes

- After generating, report the saved path back to the user. Do not print raw bytes.
- Generation is async; the script blocks (polling every ~6s) until the job reaches a
  terminal state, up to `--timeout`.
- Sora 2 content rules (preview): no real/public people, no copyrighted characters or
  music, input images with human faces are rejected, and content must be suitable for
  under-18 audiences. A `failed` status usually means a content-policy hit — check the
  reported `failure_reason` and adjust the prompt.
- Sibling skill: [generate-image](../generate-image/SKILL.md) (synchronous image generation via gpt-image-2).
