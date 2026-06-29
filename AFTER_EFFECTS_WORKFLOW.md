# After Effects → YouTube workflow (CelebrateVibes)

Manual video workflow: import MP3 in AE, export MP4, upload, track in CSV.

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
