# Happy Birthday Batch (CelebrateVibes)

CSV-driven pipeline to generate **Happy Birthday [Name]** EDM party songs via the
local ACE-Step API, render After Effects YouTube videos, and track uploads.

## Cross-platform setup (macOS + Windows)

**→ [HOW_TO_USE.md](HOW_TO_USE.md)** — daily commands (Mac + Windows scripts)  
**→ [SETUP.md](SETUP.md)** — first-time install

Quick start after setup:

```bash
./scripts/batch.sh doctor
./scripts/batch.sh init-api
./scripts/batch.sh generic-intro --force --video
./scripts/batch.sh ae-batch --slug rahul-in-birthday-edm-party --limit 1
```

Windows: use `scripts\batch.cmd` instead of `scripts/batch.sh`.

## Prerequisites

- [ACE-Step 1.5](https://github.com/ace-step/ACE-Step-1.5) checked out locally (audio)
- After Effects 2024/2025 (video)
- ffmpeg on PATH
- API server running (see `scripts/start_acestep_api.sh` or `.bat`)

## Legacy Mac layout (inside ACE-Step-1.5)

```bash
cd /path/to/ACE-Step-1.5
PYTHONPATH="$PWD" ./start_api_server_macos.sh   # separate terminal

# Generate songs
PYTHONPATH="$PWD" python_embeded/bin/python3.11 -m batch_birthday --force --limit 1

# Deliver (master + humanize + verify)
PYTHONPATH="$PWD" python_embeded/bin/python3.11 -m batch_birthday deliver \
  batch_birthday/output/<slug>/<slug>_raw.mp3
```

## Song structure rules (v6 template)

| Section | Rule |
|---------|------|
| **[Intro]** | Always English: `3! 2! 1! Go!` |
| **[Opening]** | Traditional HB melody **once** — performance score with explicit constraints |
| **[Build → Drop]** | Transition into original festival EDM |
| **Verse 2–4, Chorus, Outro** | Original melody only — English or Hindi per CSV |

**Important:** Text prompts cannot guarantee the famous Happy Birthday melody. For
100% consistency, use reference-audio cover or Gradio Repaint on the Opening (see
`MELODY_CONDITIONED_NOTE` in `lyrics_builder.py`).

## Approval workflow

1. **Generate raw** — outputs `<slug>_raw.mp3` + `<slug>.json` only  
2. **Listen & approve** — tweak lyrics in `lyrics_builder.py` if needed, regen with `--force`  
3. **Deliver** — `python -m batch_birthday deliver …_raw.mp3` → humanize + verify + upload copy  

Skip humanize/verify on first pass unless you pass `--deliver`.

## Template genre

| Field | Value |
|-------|--------|
| `genre_variant` | `birthday_edm_party_v6_restore` |
| BPM | 128 |
| Duration | 150s |
| Reference audio | None (pure text2music) |

Preset JSON: `templates/presets/sarah-birthday-edm-party-v6-restore.json`

## CLI commands

| Command | Purpose |
|---------|---------|
| `python -m batch_birthday` | Batch generate from `input/names.csv` |
| `python -m batch_birthday verify <mp3> --harden` | Distribute master + full upload gate |
| `python -m batch_birthday humanize <mp3> --style distribute` | Harden only |
| `python -m batch_birthday world-batch` | Generate all countries from `input/world_names.csv` |
| `python -m batch_birthday release-status` | Dashboard: MP3 ready + upload tracking |
| `python -m batch_birthday release-status --sync` | Refresh local MP3 flags from `output/` |
| `python -m batch_birthday release-status --mark youtube <slug>` | Mark one platform uploaded |

## Release tracking (what to follow)

Track every song in **`state/release_status.csv`** (committed to git — no MP3s).

| Column | Meaning |
|--------|---------|
| `mp3_ready` | Local upload MP3 exists in `output/<slug>/` |
| `youtube` | Published on YouTube |
| `instagram` | Posted Reel on Instagram |
| `facebook` | Posted Reel on Facebook |
| `notes` | Optional URL or release date |

**Daily workflow:**

```bash
# 1. After batch or manual regen — refresh local MP3 flags
PYTHONPATH="$PWD" python_embeded/bin/python3.11 -m batch_birthday release-status --sync

# 2. Dashboard
PYTHONPATH="$PWD" python_embeded/bin/python3.11 -m batch_birthday release-status

# 3. See what's ready but not on YouTube yet
PYTHONPATH="$PWD" python_embeded/bin/python3.11 -m batch_birthday release-status --pending youtube --mp3-only

# 4. After you upload Aarav to YouTube + Reels
PYTHONPATH="$PWD" python_embeded/bin/python3.11 -m batch_birthday release-status --mark youtube aarav-in-birthday-edm-party
PYTHONPATH="$PWD" python_embeded/bin/python3.11 -m batch_birthday release-status --mark instagram aarav-in-birthday-edm-party --note "2026-06-29"
PYTHONPATH="$PWD" python_embeded/bin/python3.11 -m batch_birthday release-status --mark facebook aarav-in-birthday-edm-party

# 5. List India songs still pending Instagram
PYTHONPATH="$PWD" python_embeded/bin/python3.11 -m batch_birthday release-status --country India --pending instagram --list
```

Commit `state/release_status.csv` after marking uploads so your team can see progress on GitHub.


After verify, keep only:

```
output/<slug>/
  <slug>.mp3    # verified upload-ready audio
  <slug>.json   # generation sidecar (local only — do not upload to DSPs)
```

## Mass batch (Indian names)

Generate many names from a text file with **unique seed + mastering fingerprint** per person
(same template sound, different audio hash):

```bash
# Test with 3 names (API server must be running)
PYTHONPATH="$PWD" python_embeded/bin/python3.11 -m batch_birthday mass-batch \
  --names batch_birthday/input/indian_names.txt --limit 3 --force

# Resume a larger run
PYTHONPATH="$PWD" python_embeded/bin/python3.11 -m batch_birthday mass-batch \
  --offset 10 --limit 10
```

Each output folder keeps only `<slug>.mp3` + `<slug>.json` + `<slug>.youtube.json`.

Add names to `input/indian_names.txt` (one per line).

Per-name variation (deterministic from name):

| Parameter | Effect |
|-----------|--------|
| ACE-Step seed | Different generation fingerprint |
| Micro pitch shift | ±~20 cents |
| EQ / stereo / loudness | Unique mastering hash |
| Outro lyrics | 1 of 6 variants per name |

## CelebrateVibes brand

- **Brand:** CelebrateVibes
- **YouTube title format:** `{NAME} Happy Birthday Song – Happy Birthday to You`
- **Website:** `website/` — static HTML for `celebratevibes.com`
- **SEO metadata:** each mass-batch run writes `<slug>.youtube.json` with title, description, tags

Deploy website to any static host (GitHub Pages, Cloudflare Pages, Netlify):

```bash
# Example: upload batch_birthday/website/ to your domain root
```

