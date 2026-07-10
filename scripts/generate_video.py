#!/usr/bin/env python3
"""Generate a video with Azure AI Foundry (Sora 2) and save it to a file.

Usage:
  generate_video.py --prompt "PROMPT" --out FILE.mp4 [--size WxH] [--seconds N]
  generate_video.py "PROMPT" FILE.mp4              # positional shorthand

Options:
  --prompt, -p    Text prompt describing the video (required)
  --out, -o       Output file path. Extension .mp4 is added if missing (required)
  --size, -s      WxH resolution: 720x1280 (portrait, default) or 1280x720 (landscape)
  --seconds, -n   Clip length in seconds: 4 (default), 8, or 12
  --timeout, -t   Max seconds to wait for the job (default 900)

Credentials/config (env, with sensible defaults):
  AZURE_OPENAI_API_KEY               required (auto-sourced from ~/ai-models-out/foundry.env)
  AZURE_OPENAI_VIDEO_ENDPOINT        default https://paul-ai-models.openai.azure.com/
                                     (Sora lives on the openai.azure.com host; if only
                                     AZURE_OPENAI_ENDPOINT is set, its host is swapped in)
  AZURE_OPENAI_VIDEO_DEPLOYMENT      default sora-2
  AZURE_OPENAI_VIDEO_API_VERSION     default preview
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error

FOUNDRY_ENV = os.path.expanduser("~/ai-models-out/foundry.env")
TERMINAL = ("succeeded", "completed", "failed", "cancelled")


def load_env_file(path):
    if not os.path.isfile(path):
        return
    pat = re.compile(r'^\s*(?:export\s+)?([A-Z0-9_]+)\s*=\s*"?([^"\n]*)"?\s*$')
    with open(path) as fh:
        for line in fh:
            m = pat.match(line)
            if m and m.group(1) not in os.environ:
                os.environ[m.group(1)] = m.group(2)


def parse_args(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--prompt", "-p")
    ap.add_argument("--out", "-o", "--output")
    ap.add_argument("--size", "-s", default="720x1280")
    ap.add_argument("--seconds", "-n", type=int, default=4)
    ap.add_argument("--timeout", "-t", type=int, default=900)
    ap.add_argument("pos", nargs="*", help="positional: PROMPT OUTFILE")
    a = ap.parse_args(argv)
    if not a.prompt and len(a.pos) >= 1:
        a.prompt = a.pos[0]
    if not a.out and len(a.pos) >= 2:
        a.out = a.pos[1]
    if not a.prompt or not a.out:
        ap.error("both a prompt and an output filename are required")
    if not os.path.splitext(a.out)[1]:
        a.out += ".mp4"
    m = re.fullmatch(r"(\d+)\s*[xX]\s*(\d+)", a.size.strip())
    if not m:
        ap.error("--size must be WxH, e.g. 720x1280")
    a.width, a.height = int(m.group(1)), int(m.group(2))
    return a


def http_json(url, key, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url, data=data,
        headers={"api-key": key, "Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"ERROR: HTTP {e.code} from {method} {url}\n{e.read().decode(errors='replace')}")
    except urllib.error.URLError as e:
        sys.exit(f"ERROR: could not reach endpoint: {e.reason}")


def http_bytes(url, key):
    req = urllib.request.Request(url, headers={"api-key": key})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        sys.exit(f"ERROR: HTTP {e.code} downloading video\n{e.read().decode(errors='replace')}")
    except urllib.error.URLError as e:
        sys.exit(f"ERROR: could not download video: {e.reason}")


def main(argv):
    args = parse_args(argv)
    load_env_file(FOUNDRY_ENV)

    key = os.environ.get("AZURE_OPENAI_API_KEY")
    if not key:
        sys.exit("ERROR: AZURE_OPENAI_API_KEY not set (and not found in %s)" % FOUNDRY_ENV)

    video_endpoint = os.environ.get("AZURE_OPENAI_VIDEO_ENDPOINT")
    if not video_endpoint:
        base = os.environ.get("AZURE_OPENAI_ENDPOINT", "https://paul-ai-models.openai.azure.com/")
        video_endpoint = base.replace(".cognitiveservices.azure.com", ".openai.azure.com") \
                             .replace(".services.ai.azure.com", ".openai.azure.com")
    endpoint = video_endpoint.rstrip("/")
    deployment = os.environ.get("AZURE_OPENAI_VIDEO_DEPLOYMENT", "sora-2")
    api_version = os.environ.get("AZURE_OPENAI_VIDEO_API_VERSION", "preview")

    create_url = f"{endpoint}/openai/v1/videos?api-version={api_version}"
    job = http_json(create_url, key, method="POST", body={
        "model": deployment,
        "prompt": args.prompt,
        "seconds": str(args.seconds),
        "size": f"{args.width}x{args.height}",
    })
    job_id = job.get("id")
    if not job_id:
        sys.exit("ERROR: no job id in response:\n" + json.dumps(job)[:800])
    print(f"job {job_id} created ({args.width}x{args.height}, {args.seconds}s); waiting...", file=sys.stderr)

    status_url = f"{endpoint}/openai/v1/videos/{job_id}?api-version={api_version}"
    deadline = time.time() + args.timeout
    status = None
    info = {}
    while status not in TERMINAL:
        if time.time() > deadline:
            sys.exit(f"ERROR: timed out after {args.timeout}s (last status: {status})")
        time.sleep(6)
        info = http_json(status_url, key)
        new = info.get("status")
        if new != status:
            extra = f" ({info.get('progress')}%)" if info.get("progress") else ""
            print(f"  status: {new}{extra}", file=sys.stderr)
        status = new

    if status not in ("succeeded", "completed"):
        err = info.get("error") or info.get("failure_reason") or json.dumps(info)[:600]
        sys.exit(f"ERROR: job {status}: {err}")

    video_url = f"{endpoint}/openai/v1/videos/{job_id}/content?api-version={api_version}"
    content = http_bytes(video_url, key)

    out = os.path.abspath(os.path.expanduser(args.out))
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "wb") as fh:
        fh.write(content)

    size_kb = os.path.getsize(out) // 1024
    print(f"OK: saved {args.width}x{args.height} {args.seconds}s video -> {out} ({size_kb} KB)")


if __name__ == "__main__":
    main(sys.argv[1:])
