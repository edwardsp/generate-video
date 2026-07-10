# generate-video

An [OpenCode](https://opencode.ai) **skill** that generates a short video from a text
prompt using Azure AI Foundry (**Sora 2**) and saves it to an MP4 file.

Generation is **asynchronous** — the helper submits a job, polls until it finishes
(~1–5 minutes), then downloads the MP4.

## Install

Clone into your OpenCode skills directory (folder must be `generate-video`):

```bash
git clone https://github.com/edwardsp/generate-video \
  ~/.config/opencode/skills/generate-video
```

Update later with `git -C ~/.config/opencode/skills/generate-video pull`.

## Configure

Needs an Azure AI Foundry / Azure OpenAI **Sora 2** deployment. Provide via env:

| Variable | Required | Default |
|---|---|---|
| `AZURE_OPENAI_API_KEY` | ✅ | — |
| `AZURE_OPENAI_VIDEO_ENDPOINT` | — | `https://<your-resource>.openai.azure.com/` |
| `AZURE_OPENAI_VIDEO_DEPLOYMENT` | — | `sora-2` |
| `AZURE_OPENAI_VIDEO_API_VERSION` | — | `preview` |

The script also auto-loads variables from `~/ai-models-out/foundry.env` if present.
Note: Sora is served on the **`*.openai.azure.com`** host, not `*.cognitiveservices.azure.com`
— if you only set `AZURE_OPENAI_ENDPOINT`, its host is swapped automatically.
**Never commit your API key**; this repo contains no credentials.

## Usage

```bash
python3 scripts/generate_video.py --prompt "PROMPT" --out FILE.mp4 [--size WxH] [--seconds N]
# positional shorthand:
python3 scripts/generate_video.py "PROMPT" FILE.mp4
```

Options: `--size` `720x1280` (portrait, default) or `1280x720` (landscape) ·
`--seconds` `4` (default) / `8` / `12` · `--image PATH` (image→video, must match
`--size`) · `--remix video_...` (remix a prior generation) · `--timeout` (default 900).
If the filename has no extension, `.mp4` is appended.

Three input modes: **text→video** (default), **image→video** (`--image`, a first-frame
anchor matching `--size`; faces are rejected), and **remix/video→video** (`--remix`,
re-render a previous generation — inherits its size/duration).

See [`SKILL.md`](SKILL.md) for full details and examples.

## Notes

Sora 2 (preview) content rules: no real/public people, no copyrighted characters or
music, input images with human faces are rejected, content must be suitable for
under-18 audiences. A `failed` job status usually means a content-policy hit.

Sibling: [generate-image](https://github.com/edwardsp/generate-image) (synchronous image generation via gpt-image-2).

## License

MIT
