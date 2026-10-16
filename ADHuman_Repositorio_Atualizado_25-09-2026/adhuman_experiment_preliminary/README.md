# ADHuman — Preliminary 30-site homepage experiment

This folder contains the **September 25, 2026 snapshot** of the
ADHuman automated experiment infrastructure. Its active configuration is
[`experiment_config.json`](experiment_config.json):

- 30 websites × 1 homepage × 4 operational contrast profiles;
- 1 repetition per website/profile combination (**120 planned**);
- Classifier: **L0 (0–1 issues), L1 (2–3), L2 (4–7), L3 (8+)**;
- local Ollama model: `llama3.1:8b`;
- browser automation: Playwright with Chromium;
- WAVE-based pre/post AIM measurements in a separate runner.

**Caution — study version:** The bundled site list is composed of
open-data portals, universities/public institutions and international
organizations. It does **not** correspond to the later 30 high-traffic
websites in the current article.

## Requirements

Install Python 3.10+ and the dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
```

Start the API backend and Ollama as explained in
[`../ADHuman-Visual-LLM/backend/README.md`](../ADHuman-Visual-LLM/backend/README.md).

## Run the classifier and decision simulation

From this directory, while the backend and Ollama are running:

```powershell
.\.venv\Scripts\python.exe run_experiment.py --smoke-test --mode extension --fresh
.\.venv\Scripts\python.exe run_experiment.py --mode extension --fresh
.\.venv\Scripts\python.exe analyze_results.py
```

The full experiment is configured for 120 *planned* runs. Successful
runs depend on access to websites, the browser extension, and the backend.

## Run AIM measurements with WAVE

You must independently install the WAVE browser extension. The WAVE
extension's source/binaries are **not** included in this repository.

```powershell
.\.venv\Scripts\python.exe run_aim_experiment.py --smoke-test --fresh
```

On Windows, the script attempts to locate an installed WAVE extension;
otherwise pass `--wave-extension` with the directory containing its
`manifest.json`. See [`README_AIM.txt`](README_AIM.txt).

## Source-of-truth notes

- The original September snapshot is preserved in this repository.
- Archived instructions for an earlier 10-site/10-page experiment are
  in [`README_LEGACY_10SITES.md`](README_LEGACY_10SITES.md).
- The extracted snapshot contains **80 classifier run records
  (76 status=ok)** and **8 AIM run records**. They are retained under
  `preliminary_data/` for provenance only.
- The **118 valid classifier executions and 37 executed adaptations**
  reported in the current manuscript are **not present** in this archive.
  Those results require the actual later code/configuration and dataset.
- The source uses synthetic acuity labels and author-selected contrast
  targets. They must not be treated as clinical diagnoses or clinical
  recommendations.
