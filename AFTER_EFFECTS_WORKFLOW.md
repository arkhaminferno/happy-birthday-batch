# After Effects → YouTube workflow (CelebrateVibes)

Manual or automated video workflow from the editor template + batch MP3s.

## Automated batch (recommended)

Template path:
`adobe after effect template/Adobe after effect files/Happy birthday.aep`

Comps used:
- `EDIT HERE` — name text layer `RAJESH` → personalized name
- `Main 2Min+` — final 1080p YouTube render comp

### Commands

```bash
# 1) Inspect template comps/layers (run once after template changes)
PYTHONPATH="$PWD" python_embeded/bin/python3.11 -m batch_birthday ae-batch --inspect

# 2) Dry-run one job (writes JSON only)
PYTHONPATH="$PWD" python_embeded/bin/python3.11 -m batch_birthday ae-batch --dry-run --slug aarav-in-birthday-edm-party

# 3) Test one full render (close AE GUI first)
PYTHONPATH="$PWD" python_embeded/bin/python3.11 -m batch_birthday ae-batch --slug aarav-in-birthday-edm-party --limit 1

# 4) Batch all songs missing video
PYTHONPATH="$PWD" python_embeded/bin/python3.11 -m batch_birthday ae-batch --limit 5
PYTHONPATH="$PWD" python_embeded/bin/python3.11 -m batch_birthday ae-batch
```

Each render:
1. Opens template via ExtendScript (`ae_scripts/render_job.jsx`)
2. Sets name, subtle hue/sat + speed variation (excludes Rajesh/Cake layers)
3. Imports MP3 into `Main 2Min+`, matches comp length to audio
4. Saves per-slug project under `batch_birthday/ae_work/projects/`
5. Renders with `aerender` → `output/{slug}/{slug}-youtube.mp4`
6. Embeds YouTube title/artist metadata via ffmpeg

Requires **After Effects 2025** installed (Mac paths auto-detected).

### Headless mode (no Home screen)

By default scripts run with **`-noui`** (no visible UI). The **MP4 export** always uses
**`aerender`**, which is fully headless.

```bash
# default: -noui (no Home screen)
PYTHONPATH="$PWD" python_embeded/bin/python3.11 -m batch_birthday ae-batch --smoke

# alternative: JXA background scripting (AE 24+)
AE_UI_MODE=jxa PYTHONPATH="$PWD" python_embeded/bin/python3.11 -m batch_birthday ae-batch --smoke

# last resort: visible UI
AE_UI_MODE=gui PYTHONPATH="$PWD" python_embeded/bin/python3.11 -m batch_birthday ae-batch --smoke
```

**Mac limitation:** Adobe does not provide `AfterFX.com` on Mac (unlike Windows). Editing the
`.aep` (name, colors, audio) still requires the AE scripting engine briefly. Rendering is
100% headless via `aerender`.

### If AE opens to the Home screen and nothing happens

1. **Quit After Effects fully** (`Cmd+Q`) — do not just close the window.
2. Run the smoke test first:
   ```bash
   PYTHONPATH="$PWD" python_embeded/bin/python3.11 -m batch_birthday ae-batch --smoke
   ```
   AE should flash open, then close by itself. If `SMOKE TEST PASSED` prints, scripting works.
3. Then inspect, then one render.

Logs are written to `batch_birthday/ae_work/script_log.txt` and `script_status.txt`.

## Manual workflow (fallback)

## One folder per name

```
output/aarav-in-birthday-edm-party/
  aarav-in-birthday-edm-party.mp3           ← drag into After Effects
  aarav-in-birthday-edm-party.youtube.json  ← title, description, tags
  aarav-in-birthday-edm-party.json          ← full lyrics (optional on-screen text)
  aarav-in-birthday-edm-party-youtube.mp4   ← YOU export this from AE (YouTube 16:9)
  aarav-in-birthday-edm-party-reel.mp4      ← optional 9:16 for Instagram/FB
```

## Step-by-step (repeat per name)

1. **Pick next name** from your queue:
   ```bash
   PYTHONPATH="$PWD" python_embeded/bin/python3.11 -m batch_birthday release-status --needs-video --list
   ```

2. **Get paths** for one slug:
   ```bash
   PYTHONPATH="$PWD" python_embeded/bin/python3.11 -m batch_birthday release-status --show aarav-in-birthday-edm-party
   ```

3. **After Effects**
   - New comp (1920×1080, 30fps, ~2:45 duration)
   - File → Import → `{slug}.mp3`
   - Build template: waveform, name text, lyrics (optional)
   - Composition → Add to Render Queue → export as `{slug}-youtube.mp4` in the same folder

4. **Optional Reel** — duplicate comp 1080×1920 → export `{slug}-reel.mp4`

5. **Refresh tracker** (auto-detects your AE export):
   ```bash
   PYTHONPATH="$PWD" python_embeded/bin/python3.11 -m batch_birthday release-status --sync
   ```

6. **Upload** to YouTube / post Reels, then mark:
   ```bash
   PYTHONPATH="$PWD" python_embeded/bin/python3.11 -m batch_birthday release-status --mark youtube aarav-in-birthday-edm-party
   PYTHONPATH="$PWD" python_embeded/bin/python3.11 -m batch_birthday release-status --mark instagram aarav-in-birthday-edm-party
   ```

7. **Save progress on GitHub** (tracker only):
   ```bash
   cd batch_birthday
   git add state/release_status.csv
   git commit -m "Aarav video uploaded"
   git push
   ```

## What to track (release_status.csv)

| Column | When you set it |
|--------|-----------------|
| `mp3_ready` | Auto — song exists |
| `video_ready` | Auto — `-youtube.mp4` or `-reel.mp4` exists |
| `youtube` | After YouTube upload |
| `instagram` | After Reel posted |
| `facebook` | After FB Reel posted |
| `notes` | Paste YouTube URL or date |

## Tips

- **One AE template** — duplicate per name, only change audio + name text.
- **Work in name order** from `--needs-video --list` so you never lose track.
- **Do not put MP3/MP4 on GitHub** — too large. Tracker CSV is enough.
- **Backup** all `output/` to Google Drive/iCloud once: `zip -r ~/Desktop/celebratevibes-songs.zip batch_birthday/output/*/*.mp3`
