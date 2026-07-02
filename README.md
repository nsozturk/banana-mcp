# 🍌 banana-mcp

An MCP server (+ standalone Python scripts) that generates images with your own
Google **Gemini** session — the "Nano Banana" image model — driven straight over
Gemini's web HTTP flow. **No browser, no headful Chrome: it's headless by
nature.**

You bring your **own** Google account cookies (exported with a browser
extension). The server signs requests as *you*, running your *own* prompts
against your *own* Gemini access.

---

## ⚠️ Personal use — read first

- This is a **bring-your-own-credentials** tool for **personal use**. It uses
  **your own** Google/Gemini session, which **you** supply locally. The project
  ships **no** tokens and stores nothing remotely.
- Automating a web product may be restricted by Google's Terms of Service. **You
  are solely responsible** for how you use it, for the prompts you run, and for
  the images you generate — including compliance with Google's policies and all
  **applicable laws** in your jurisdiction.
- Do **not** use it to impersonate real people, produce content depicting
  minors, or generate anything illegal. All example prompts are of **fictional
  adults**.
- Your cookies are a **live login**. Never commit `secrets/`, storage dumps, or
  HAR files. The repo's `.gitignore` blocks them by default — keep it that way.

---

## How it works

Gemini's web UI generates images via an HTTP RPC endpoint
(`.../BardFrontendService/StreamGenerate`) — **not** a WebSocket. `banana-mcp`
replays that flow with your session cookies:

1. Auth = your Google cookies (`__Secure-1PSID`, optionally `__Secure-1PSIDTS`,
   plus the standard `SID`/`SAPISID`/… set), captured once with a browser
   extension.
2. The prompt (plain text *or* a structured JSON "Nano Banana" object) is sent
   as the message body, with an image-capable model header.
3. The response returns the generated image URL(s); the tool downloads them to
   `output/`.

Under the hood it uses the excellent
[`gemini_webapi`](https://github.com/HanaokaYuzu/Gemini-API) library, which
handles the XSRF (`SNlM0e`) token and `__Secure-1PSIDTS` rotation.

---

## Setup

### 1. Requirements

- **Python 3.11+** (the library needs `enum.StrEnum`).
- Install dependencies:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

### 2. Get your Gemini cookies (bring your own)

1. Sign in to <https://gemini.google.com> in Chrome with the Google account you
   want to use, and confirm you can generate an image there.
2. Install the **StorageDump** Chrome extension:
   <https://chromewebstore.google.com/detail/storagedump/kihoghfekemdccfnpjefmggehpgnjnab>
3. On the Gemini tab, use StorageDump to export the site's storage. It saves a
   folder like `storagedump_gemini.google.com_<timestamp>/` containing
   `cookies.json`.
4. Extract just the cookies this tool needs into `secrets/cookies.json`
   (values are never printed):

```bash
.venv/bin/python scripts/extract_cookies.py path/to/storagedump_gemini.google.com_<timestamp>
```

> Gemini session cookies rotate and go stale. If generations start returning
> "signed out", re-export a **fresh** dump and re-run the command above.

### 3. Verify auth

```bash
.venv/bin/python -c "import asyncio; from banana.client import get_client; \
  asyncio.run(get_client()).__await__ and print('ok')" 2>/dev/null || true
```

or just run a quick generation (below).

---

## Usage — standalone scripts

```bash
# First 3 prompts of a file -> output/<file-stem>/
.venv/bin/python scripts/generate.py examples/example-image-prompts.json --limit 3

# Specific prompt ids
.venv/bin/python scripts/generate.py examples/example-image-prompts.json \
    --ids example_001_bosphorus_sunrise

# By index, custom output dir
.venv/bin/python scripts/generate.py examples/example-image-prompts.json \
    --index 0 1 2 --out output/run1
```

Each run writes the images plus a `results.json` manifest into the output dir.

### Prompt file format

```json
{
  "prompt_set": { "title": "...", "global_constraints": ["..."] },
  "prompts": [
    { "id": "unique_id", "scene": { "...": "any nested JSON is serialized as the prompt" } }
  ]
}
```

The whole prompt object is serialized to text and sent to Gemini. See
[`examples/example-image-prompts.json`](examples/example-image-prompts.json).

---

## Usage — as an MCP server

`mcp_server.py` speaks MCP over stdio and exposes four tools:

| Tool | What it does |
|---|---|
| `banana_account_status` | Check the session is authenticated / image-capable |
| `banana_generate_image` | Generate from a free-form prompt string |
| `banana_list_prompts` | List prompt ids/titles inside a prompt JSON file |
| `banana_generate_from_file` | Batch-generate from a `*-image-prompts.json` file |

### Register with an MCP client

**Claude Code** (`~/.claude.json` or project `.mcp.json`):

```json
{
  "mcpServers": {
    "banana": {
      "command": "/absolute/path/to/banana-mcp/.venv/bin/python",
      "args": ["/absolute/path/to/banana-mcp/mcp_server.py"],
      "cwd": "/absolute/path/to/banana-mcp"
    }
  }
}
```

The same shape works for Claude Desktop (`claude_desktop_config.json`) and other
MCP hosts. Restart the client, then ask it to run `banana_account_status` or
generate an image.

---

## Project layout

```
banana-mcp/
├── mcp_server.py            # MCP entrypoint (stdio)
├── banana/
│   ├── config.py            # loads secrets/cookies.json
│   ├── client.py            # authenticated GeminiClient singleton
│   ├── prompts.py           # load/serialize structured prompt files
│   └── generator.py         # generate + download images
├── scripts/
│   ├── extract_cookies.py   # storage dump -> secrets/cookies.json
│   └── generate.py          # CLI batch generator
├── examples/                # neutral sample prompt file
├── secrets/                 # your cookies (gitignored — never commit)
└── output/                  # generated images (gitignored)
```

---

## Troubleshooting

- **"signed out" / no image returned** → cookies are stale. Re-export a fresh
  StorageDump and re-run `scripts/extract_cookies.py`.
- **`ImportError: cannot import name 'StrEnum'`** → you're on Python < 3.11. Use
  3.11+.
- **Rate limited** → space out large batches; you're using a normal account.

---

## License

MIT — see [LICENSE](LICENSE). This project is not affiliated with, endorsed by,
or connected to Google. "Gemini" is a trademark of Google LLC.
