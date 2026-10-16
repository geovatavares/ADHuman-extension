# Artifact status and fidelity to the manuscript

## What was extracted

Archive supplied by the user: `ADHuman_25.09.2026.rar`.

Included source:
- Chrome MV3 extension v3.3.0 (popup, content and background scripts).
- FastAPI backend with Ollama simulator and four synthetic profiles.
- Classifier logic assigning L0–L3 from contrast-issue counts.
- Playwright scripts for browser automation.
- WAVE AIM pre/post script requiring the separately installed WAVE extension.
- Preliminary execution records from 24–25 September 2026.

Excluded from the public-source package:
- Python virtual environments and installed third-party packages.
- Browser profiles, session storage, cache, cookies, WAVE caches.
- Runtime logs, `.env` with local values, and generated debug output.
- Large binary artifacts not required by the source release.

## Major differences versus the current manuscript

| Item | September snapshot | Manuscript |
|---|---|---|
| Website set | Open data, university/public, international domains | Popular high-traffic websites |
| Classifier planned combos | 30 × 4 = 120 | 30 × 4 = 120 |
| Valid classifier executions included | 76 | 118 |
| Human participation included | 65 of 76 successful rows | 101 of 118 |
| AIM records included | 8 | 37 executed-adaptation cases |
| Contrast profiles | 4.5:1, 7:1, 10:1, 15:1 | Same numerical contrast targets |
| Classifier mapping | L0 0–1, L1 2–3, L2 4–7, L3 8+ | Same prototype heuristic |

**Do not** present the September CSV files as the empirical dataset
behind the final paper. The source also retains early synthetic
acuity-range terminology in configuration and profile metadata; the
paper correctly treats contrast configurations as experimental rather
than clinical classifications.

## Requirements for exact reproduction of the submitted evaluation

1. Provide the **actual October experiment revision**, including the
   thirty high-traffic website IDs and their exact URLs.
2. Provide logs or sanitized tabular results showing the 120 planned
   combinations, 118 valid classifier outcomes and 2 exclusions.
3. Provide the AIM pre/post dataset for the 37 executed adaptations.
4. Confirm that the installed extension/backend versions correspond
   exactly to the runs and document the WAVE version and setup.
5. Verify that sensitive or identifying information has been removed.

This is a source release of the **latest code in the user-provided
September archive**, not a reconstruction of missing October data.
