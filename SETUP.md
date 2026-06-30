# Cross-platform setup (macOS + Windows)

Clone this repo on **any machine** with the same workflow. Video rendering uses the
bundled `ae_template/`. Audio generation needs a separate
[ACE-Step 1.5](https://github.com/ace-step/ACE-Step-1.5) checkout (CUDA on Windows,
MPS/MLX on Apple Silicon Mac).

## Recommended folder layout

```
projects/
  happy-birthday-batch/    ← this repo (any folder name works)
  ACE-Step-1.5/            ← clone separately for song generation
```

Or nest this repo inside ACE-Step (Mac dev layout):

```
ACE-Step-1.5/
  batch_birthday/          ← this repo contents
```

Set `ACESTEP_ROOT` if ACE-Step lives elsewhere (see `.env.example`).

---

## macOS (Apple Silicon / Intel)

### 1. One-time setup

```bash
git clone git@github-personal:arkhaminferno/happy-birthday-batch.git
cd happy-birthday-batch
bash scripts/setup_macos.sh
```

### 2. ACE-Step (audio)

```bash
git clone https://github.com/ace-step/ACE-Step-1.5.git ../ACE-Step-1.5
cd ../ACE-Step-1.5 && uv sync
```

### 3. Terminal A — API server

```bash
cd happy-birthday-batch
bash scripts/start_acestep_api.sh
```

### 4. Terminal B — batch commands

```bash
cd happy-birthday-batch
./scripts/batch.sh init-api          # first time only (~1 min)
./scripts/batch.sh doctor            # verify ffmpeg, AE, API
./scripts/batch.sh generic-intro --force --video
./scripts/batch.sh ae-batch --slug rahul-in-birthday-edm-party --limit 1
```

**Legacy Mac layout** (repo inside ACE-Step-1.5):

```bash
cd /path/to/ACE-Step-1.5
PYTHONPATH="$PWD" python_embeded/bin/python3.11 -m batch_birthday doctor
```

Or after `uv sync` inside `batch_birthday/`: `./scripts/batch.sh doctor`

---

## Windows 11 (NVIDIA RTX 5070)

### 1. Prerequisites

| Tool | Install |
|------|---------|
| Git + Git LFS | [git-scm.com](https://git-scm.com/download/win) + `winget install GitHub.GitLFS` |
| ffmpeg | `winget install Gyan.FFmpeg` (add to PATH) |
| After Effects 2024/2025 | Adobe Creative Cloud |
| Python 3.11+ | Via `uv` (setup script installs it) |

### 2. One-time setup

```powershell
git clone git@github-personal:arkhaminferno/happy-birthday-batch.git
cd happy-birthday-batch
powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
```

### 3. ACE-Step (audio, CUDA)

```powershell
git clone https://github.com/ace-step/ACE-Step-1.5.git ..\ACE-Step-1.5
cd ..\ACE-Step-1.5
uv sync
```

First run downloads models (~several GB). RTX 5070 has plenty of VRAM for
`acestep-5Hz-lm-1.7B` vocals.

### 4. Terminal A — API server

```bat
cd happy-birthday-batch
scripts\start_acestep_api.bat
```

Sets `ACESTEP_INIT_LLM=true` automatically.

### 5. Terminal B — batch commands

```bat
cd happy-birthday-batch
scripts\batch.cmd init-api
scripts\batch.cmd doctor
scripts\batch.cmd generic-intro --force --video
scripts\batch.cmd ae-batch --slug rahul-in-birthday-edm-party --limit 1
scripts\batch.cmd release-status --sync
```

---

## Universal CLI (`celebratevibes`)

After `uv sync` in this repo:

```bash
celebratevibes doctor
celebratevibes init-api
celebratevibes generic-intro --force --video
celebratevibes ae-batch --limit 5
celebratevibes release-status --mark youtube SLUG --note "https://youtu.be/..."
```

Works regardless of clone folder name (`happy-birthday-batch` or `batch_birthday`).

---

## Video-only on Windows (MP3s copied from Mac)

If songs are already generated on Mac, copy the `output/` folder to Windows and skip
ACE-Step setup:

```bat
scripts\batch.cmd ae-batch --slug rahul-in-birthday-edm-party --limit 1
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `Unknown slug` in release tracker | Run `release-status --sync` or add row manually |
| `LLM is not loaded` | API running? Run `celebratevibes init-api` |
| `aerender not found` | Install AE 2024/2025 or set `AERENDER_PATH` |
| `ffmpeg metadata embed failed` | Install ffmpeg, restart terminal |
| Git LFS files missing | `git lfs install && git lfs pull` |
| ACE-Step not found | Clone sibling repo or set `ACESTEP_ROOT` |

Run **`celebratevibes doctor`** anytime for a quick status report.
