# How to Use CelebrateVibes Batch Pipeline

Step-by-step guide for **macOS** and **Windows 11**. The After Effects template ships
inside this repo at `ae_template/` — no separate download needed.

For install prerequisites, see [SETUP.md](SETUP.md).

---

## 1. Clone the repo (both OS)

### macOS

```bash
git lfs install
git clone git@github-personal:arkhaminferno/happy-birthday-batch.git
cd happy-birthday-batch
git lfs pull
bash scripts/setup_macos.sh
```

### Windows

```powershell
git lfs install
git clone git@github-personal:arkhaminferno/happy-birthday-batch.git
cd happy-birthday-batch
git lfs pull
powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
```

---

## 2. ACE-Step (audio generation only)

Clone **once** next to this repo (sibling folder):

```text
projects/
  happy-birthday-batch/    ← this repo
  ACE-Step-1.5/            ← song generation API
```

```bash
git clone https://github.com/ace-step/ACE-Step-1.5.git ../ACE-Step-1.5
cd ../ACE-Step-1.5
uv sync
```

Set `ACESTEP_ROOT` in `.env` if your ACE-Step folder is elsewhere (see `.env.example`).

**Video-only workflow:** skip ACE-Step if you copy `output/` MP3s from another machine.

---

## 3. Start the API (Terminal A — keep open)

| macOS | Windows |
|-------|---------|
| `bash scripts/start_acestep_api.sh` | `scripts\start_acestep_api.bat` |

First time after API is up:

| macOS | Windows |
|-------|---------|
| `./scripts/batch.sh init-api` | `scripts\batch.cmd init-api` |

---

## 4. Health check (Terminal B)

| macOS | Windows |
|-------|---------|
| `./scripts/batch.sh doctor` | `scripts\batch.cmd doctor` |

Expect: ffmpeg OK, AE template OK, aerender OK, API up, `llm_initialized=True`.

---

## 5. Generate a song + YouTube video

### Generic “Happy Birthday to You” (no name)

| macOS | Windows |
|-------|---------|
| `./scripts/batch.sh generic-intro --force --video` | `scripts\batch.cmd generic-intro --force --video` |

Output:

```text
output/happy-birthday-to-you-party/
  happy-birthday-to-you-party.mp3
  happy-birthday-to-you-party-youtube.mp4
  happy-birthday-to-you-party.youtube.json
```

### Named birthday song (one person)

| macOS | Windows |
|-------|---------|
| `./scripts/batch.sh --force --limit 1` | `scripts\batch.cmd --force --limit 1` |

Edit `input/world_names.csv` first, or pass a specific row via mass-batch (see README).

Then render video:

| macOS | Windows |
|-------|---------|
| `./scripts/batch.sh ae-batch --slug rahul-in-birthday-edm-party --force` | `scripts\batch.cmd ae-batch --slug rahul-in-birthday-edm-party --force` |

### Batch many videos (MP3s already exist)

| macOS | Windows |
|-------|---------|
| `./scripts/batch.sh ae-batch --limit 5` | `scripts\batch.cmd ae-batch --limit 5` |
| `./scripts/batch.sh ae-batch` | `scripts\batch.cmd ae-batch` |

Renders all songs missing `-youtube.mp4` in `output/`.

---

## 6. Track uploads (YouTube / Instagram / Facebook)

Sync local file status:

| macOS | Windows |
|-------|---------|
| `./scripts/batch.sh release-status --sync` | `scripts\batch.cmd release-status --sync` |

Dashboard:

| macOS | Windows |
|-------|---------|
| `./scripts/batch.sh release-status` | `scripts\batch.cmd release-status` |

Mark YouTube uploaded:

| macOS | Windows |
|-------|---------|
| `./scripts/batch.sh release-status --mark youtube SLUG --note "https://youtu.be/ID"` | `scripts\batch.cmd release-status --mark youtube SLUG --note "https://youtu.be/ID"` |

Example:

```bash
./scripts/batch.sh release-status --mark youtube happy-birthday-to-you-party --note "https://youtu.be/BG7-4F66La4"
```

List songs waiting for video:

| macOS | Windows |
|-------|---------|
| `./scripts/batch.sh release-status --needs-video --list` | `scripts\batch.cmd release-status --needs-video --list` |

---

## 7. YouTube upload checklist

1. Upload `output/{slug}/{slug}-youtube.mp4`
2. Copy title / description / tags from `{slug}.youtube.json`
3. **Made for kids:** No
4. **AI disclosure:** Yes for synthetic audio; No for the 3 photorealistic video options
5. Add to playlists: **All Birthday Songs** (+ country/gender playlists for named songs)
6. Mark `release_status.csv` via `--mark youtube` (above)

**Pace:** 2–3 YouTube uploads per week (not all 80 at once).

---

## 8. Script reference

| Script | macOS | Windows |
|--------|-------|---------|
| Run any command | `./scripts/batch.sh COMMAND` | `scripts\batch.cmd COMMAND` |
| One-time setup | `bash scripts/setup_macos.sh` | `powershell -File scripts\setup_windows.ps1` |
| Start ACE-Step API | `bash scripts/start_acestep_api.sh` | `scripts\start_acestep_api.bat` |

Equivalent after `uv sync` (any OS):

```bash
celebratevibes doctor
celebratevibes init-api
celebratevibes ae-batch --slug NAME --limit 1
```

---

## 9. Legacy macOS layout (inside ACE-Step-1.5)

If this repo lives at `ACE-Step-1.5/batch_birthday/`:

```bash
cd /path/to/ACE-Step-1.5
PYTHONPATH="$PWD" ./start_api_server_macos.sh          # Terminal A
PYTHONPATH="$PWD" python_embeded/bin/python3.11 -m batch_birthday doctor
PYTHONPATH="$PWD" python_embeded/bin/python3.11 -m batch_birthday ae-batch --limit 1
```

Or use `./scripts/batch.sh` from inside `batch_birthday/`.

---

## 10. Troubleshooting

| Problem | Fix |
|---------|-----|
| AE template missing | `git lfs pull` |
| `LLM is not loaded` | API running? Run `init-api` |
| `aerender not found` | Install AE 2024/2025 |
| `ffmpeg` missing | `brew install ffmpeg` / `winget install Gyan.FFmpeg` |
| `ACE-Step not found` | Clone sibling repo or set `ACESTEP_ROOT` |
| Video renders, audio silent | Regenerate MP3 with API + LLM |

Run **`doctor`** again after any fix.
