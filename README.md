# Happy Birthday Batch Template (ACE-Step 1.5)

CSV-driven pipeline to generate **Happy Birthday [Name]** EDM party songs via the
local ACE-Step API, harden them for distributor upload, and verify with local
AI-music forensic checks.

## Prerequisites

- [ACE-Step 1.5](https://github.com/ace-step/ACE-Step-1.5) checked out locally
- API server running: `./start_api_server_macos.sh` (LLM enabled for vocals)
- `PYTHONPATH` set to ACE-Step repo root

## Quick start

```bash
cd /path/to/ACE-Step-1.5
PYTHONPATH="$PWD" ./start_api_server_macos.sh   # separate terminal

# 1. Edit names.csv — set name, slug, genre_variant, seed
# 2. Generate
PYTHONPATH="$PWD" python_embeded/bin/python3.11 -m batch_birthday --force --limit 1

# 3. Harden + verify before upload
PYTHONPATH="$PWD" python_embeded/bin/python3.11 -m batch_birthday verify \
  batch_birthday/output/<slug>/<slug>.mp3 --harden --title "Happy Birthday Name"
```

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
| `python -m batch_birthday scan <mp3>` | Metadata scan only |

## Output layout (per song)

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

