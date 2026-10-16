# ADHuman — Web Accessibility Exemplar

**Source snapshot:** 25 September 2026 · **Chrome extension:** v3.3.0

ADHuman is a human-in-the-loop architecture for self-adaptive systems.
This repository contains a *web accessibility exemplar*: a Chrome
extension, a local FastAPI/Ollama backend that simulates responses at
human decision points, and automation scripts for preliminary
accessibility experiments.

> **Research version warning.** This is the most complete implementation
> found in the `ADHuman_25.09.2026.rar` archive, but it is **not the
> final October evaluation artifact**. In particular, the bundled
> website list and preliminary results do not match the 30 high-traffic
> sites / 118 valid executions / 37 applied adaptations in the manuscript.
> See [ARTIFACT_STATUS.md](ARTIFACT_STATUS.md).

## Repository contents

```text
ADHuman-Visual-LLM/
  plugin/                   Chrome Manifest V3 extension
  backend/                  FastAPI + local Ollama decision simulator
    app/                    API, profiles, prompt, validation and planning support
    profiles/profiles.json  Four experimental visual configurations
    tests/                  Seven unit tests
  docs/                     Architecture and methodological notes
  Portal-Cidadao-Demo.html  Offline demonstration page

adhuman_experiment_preliminary/
  experiment_config.json    30-site × 4-profile September experiment
  sites.csv                 September site set
  run_experiment.py         Playwright automation
  run_aim_experiment.py     WAVE / AIM pre-post measurement
  analyze_results.py       Participation analysis
  analyze_aim_results.py   AIM analysis
  README.md                 Detailed experiment instructions

preliminary_data/
  2026-09-25/               Historical partial results, clearly labeled
```

## Architecture and participation levels

The extension monitors page content, calculates text/background contrast
issues relative to a configured synthetic visual profile, and maps the
number of issues to one of four levels:

| Level | Count of detected issues | Interaction |
| --- | ---: | --- |
| L0 | 0–1 | Autonomous / no human participation |
| L1 | 2–3 | Validation of a recommended plan |
| L2 | 4–7 | Human selection or adjustment |
| L3 | 8 or more | Decision support |

These **prototype-specific** thresholds are not defined by WCAG.
In this implementation, the **Classifier** chooses the participation
level. The LLM is used **only to simulate a human response** when a
level requires participation; it does not determine the level.

The synthetic visual configurations use contrast targets **4.5:1,
7:1, 10:1, and 15:1**. The last two values are author-defined
experimental parameters and none of these configurations should be
interpreted as clinical classifications of individual users.

## Requirements

- Windows 10/11 or equivalent environment supporting Python, Chrome,
  Ollama and Playwright; the included launch scripts target Windows.
- Python 3.10 or newer.
- Google Chrome / Chromium with support for unpacked extensions.
- [Ollama](https://ollama.com/) and the locally installed
  `llama3.1:8b` model.
- For the separate AIM experiment only, the
  [WAVE browser extension](https://wave.webaim.org/extension/).
  WAVE is **not redistributed** here.

## Quick start on Windows

**1. Install and start the model:**

```powershell
ollama pull llama3.1:8b
```

**2. Set up the backend:**

```powershell
cd ADHuman-Visual-LLM\backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The backend expects Ollama at `http://127.0.0.1:11434`. Once the API
is running, check `http://127.0.0.1:8000/health` and
`http://127.0.0.1:8000/docs`.

**3. Load the extension:**

1. Open `chrome://extensions` in Google Chrome.
2. Enable **Developer mode**, then select **Load unpacked**.
3. Select **`ADHuman-Visual-LLM/plugin/`** (not the repository root).
4. Open a website and use the extension's toolbar popup.

**4. Optional preliminary experiment:**

```powershell
cd adhuman_experiment_preliminary
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe run_experiment.py --smoke-test --mode extension --fresh
```

See [the experiment README](adhuman_experiment_preliminary/README.md)
for the full run, analysis, and WAVE/AIM instructions.

## Tests

From `ADHuman-Visual-LLM/backend`:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The seven available backend tests pass in the prepared snapshot.
Static syntax checks passed for all five JavaScript files. These
checks do not validate an integrated end-to-end run against external
websites and a running Ollama instance.

## Anonymized submission and scope

If this source is linked in an anonymized paper submission, verify that
the repository, release metadata, commit authors, issue history,
outbound links and associated artifacts do not reveal the authors'
identities. Hosting the source in an anonymous mirror does not
automatically anonymize the contents of files.

This snapshot is **not** sufficient to reproduce the latest manuscript
evaluation. The exact October configuration and results must be
added from the actual evaluation run before making that claim.
