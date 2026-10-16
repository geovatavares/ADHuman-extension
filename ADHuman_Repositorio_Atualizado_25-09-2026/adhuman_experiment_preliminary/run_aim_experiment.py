from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "experiment_config.json"
SITES_PATH = ROOT / "sites.csv"
TRIGGER_PATH = ROOT / "extension_trigger.js"
RESULTS_DIR = ROOT / "results_aim"
RESULTS_FILE = RESULTS_DIR / "raw_aim_runs.csv"
PROFILE_DIR = RESULTS_DIR / "playwright-profile-aim"
DEBUG_DIR = RESULTS_DIR / "debug"

WAVE_EXTENSION_ID = "jbbplnpkjmmeebjpijfedlgcdilocofh"

FIELDS = [
    "run_id", "timestamp_utc", "site_id", "site_name", "group", "country", "site_url",
    "page_id", "page_title", "page_url", "profile_id", "profile_label", "profile_short_label",
    "profile_target_contrast_ratio", "repetition", "status", "error", "http_status",
    "page_load_ms", "decision_latency_ms", "llm_inference_time_ms", "adhuman_ok",
    "adhuman_integration", "classified_level", "human_assistance", "adhuman_decision",
    "adhuman_plan", "adhuman_confidence", "pre_aim_score", "post_aim_score",
    "aim_delta", "aim_improvement_pct",
]


def load_config() -> Dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def load_sites() -> List[Dict[str, str]]:
    with open(SITES_PATH, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def resolve_path(raw: str | None) -> Path | None:
    if not raw:
        return None
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = (ROOT / path).resolve()
    return path


def validate_adhuman_extension(config: Dict[str, Any]) -> Path:
    path = resolve_path(str(config.get("extension_path", "")).strip())
    if not path or not path.exists():
        raise SystemExit("'extension_path' do ADHuman não aponta para uma pasta existente.")
    if not (path / "manifest.json").exists():
        raise SystemExit(f"manifest.json do ADHuman não encontrado em: {path}")
    return path.resolve()


def version_key(path: Path) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", path.name))


def auto_detect_wave_extension() -> Path | None:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        return None

    root = Path(local_app_data) / "Google" / "Chrome" / "User Data"
    if not root.exists():
        return None

    candidates: list[Path] = []
    for profile in root.iterdir():
        if not profile.is_dir():
            continue
        ext_root = profile / "Extensions" / WAVE_EXTENSION_ID
        if not ext_root.exists():
            continue
        for version in ext_root.iterdir():
            if version.is_dir() and (version / "manifest.json").exists():
                candidates.append(version.resolve())

    if not candidates:
        return None
    candidates.sort(key=version_key, reverse=True)
    return candidates[0]


def resolve_wave_extension(cli_path: str | None) -> Path:
    raw = cli_path or os.environ.get("WAVE_EXTENSION_PATH")
    path = resolve_path(raw) if raw else auto_detect_wave_extension()
    if not path or not path.exists():
        raise SystemExit(
            "Extensão WAVE não encontrada. Informe com --wave-extension \"C:\\...\\3.3.1.0_0\""
        )
    if not (path / "manifest.json").exists():
        raise SystemExit(f"manifest.json do WAVE não encontrado em: {path}")
    return path.resolve()


def selected_sites(config: Dict[str, Any], sites: List[Dict[str, str]]) -> List[Dict[str, str]]:
    requested = [str(x) for x in config.get("site_ids", [])]
    if not requested:
        return sites[:30]
    by_id = {site["id"]: site for site in sites}
    missing = [sid for sid in requested if sid not in by_id]
    if missing:
        raise SystemExit(f"Sites configurados não encontrados em sites.csv: {missing}")
    return [by_id[sid] for sid in requested]


def homepage_pages(sites: List[Dict[str, str]]) -> List[Dict[str, str]]:
    return [
        {
            "site_id": site["id"],
            "page_id": f"{site['id']}-HOME",
            "page_title": "Homepage",
            "page_url": site["url"],
        }
        for site in sites
    ]


def stable_run_id(site_id: str, url: str, profile_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"adhuman-aim-120|{site_id}|{url}|{profile_id}|1"))


def build_plan(config: Dict[str, Any], sites: List[Dict[str, str]], pages: List[Dict[str, str]], smoke: bool) -> List[Dict[str, Any]]:
    profiles = config.get("profiles", [])
    if not profiles:
        raise SystemExit("Nenhum perfil encontrado em experiment_config.json.")

    sites_by_id = {s["id"]: s for s in sites}
    plan: list[dict] = []
    for page in pages:
        site = sites_by_id[page["site_id"]]
        for profile in profiles:
            plan.append({
                "site": site,
                "page": page,
                "profile": profile,
                "repetition": 1,
                "run_id": stable_run_id(site["id"], page["page_url"], profile["id"]),
            })

    if smoke:
        first_two = {s["id"] for s in sites[:2]}
        return [x for x in plan if x["site"]["id"] in first_two]

    random.Random(int(config.get("seed", 20260924))).shuffle(plan)
    return plan


def read_done_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return {
            row["run_id"] for row in csv.DictReader(f)
            if row.get("run_id") and str(row.get("status", "")).lower() == "ok"
        }


def append_result(path: Path, row: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists() and path.stat().st_size > 0
    normalized = {k: row.get(k, "") for k in FIELDS}
    with open(path, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow(normalized)


def base_row(item: Dict[str, Any]) -> Dict[str, Any]:
    site, page, profile = item["site"], item["page"], item["profile"]
    return {
        "run_id": item["run_id"],
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "site_id": site["id"],
        "site_name": site.get("name", site["id"]),
        "group": site.get("group", ""),
        "country": site.get("country", ""),
        "site_url": site["url"],
        "page_id": page["page_id"],
        "page_title": page["page_title"],
        "page_url": page["page_url"],
        "profile_id": profile["id"],
        "profile_label": profile.get("label", profile["id"]),
        "profile_short_label": profile.get("short_label", profile.get("label", profile["id"])),
        "profile_target_contrast_ratio": profile.get("target_contrast_ratio", ""),
        "repetition": 1,
        "status": "started",
        "error": "",
    }


def find_wave_frame(page):
    handle = page.query_selector("iframe#wave_sidebar_container")
    if handle:
        try:
            return handle.content_frame()
        except Exception:
            pass

    for frame in page.frames:
        try:
            if "chrome-extension://" not in (frame.url or "").lower():
                continue
            text = frame.locator("body").inner_text(timeout=800)
            if "aim" in text.lower():
                return frame
        except Exception:
            pass
    return None


def parse_aim_from_text(text: str) -> float:
    text = text.replace("\xa0", " ")
    patterns = [
        r"AIM\s*Score[\s\S]{0,100}?([0-9]+(?:[.,][0-9]+)?)\s*(?:/|out\s+of)\s*10",
        r"Automated\s+AIM\s+Score[\s\S]{0,80}?([0-9]+(?:[.,][0-9]+)?)",
        r"AIM\s*Score[\s:=\-]*([0-9]+(?:[.,][0-9]+)?)",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            value = float(m.group(1).replace(",", "."))
            if 0 <= value <= 10:
                return value

    pos = text.lower().find("aim")
    if pos >= 0:
        nearby = text[pos:pos + 220]
        for token in re.findall(r"(?<!\d)(\d+(?:[.,]\d+)?)(?!\d)", nearby):
            value = float(token.replace(",", "."))
            if 0 <= value <= 10:
                return value

    raise RuntimeError("Não foi possível extrair o AIM Score do painel WAVE.")


def save_debug(page, label: str) -> None:
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", label)
    try:
        page.screenshot(path=str(DEBUG_DIR / f"{safe}.png"), full_page=False)
    except Exception:
        pass
    try:
        blocks = []
        for idx, frame in enumerate(page.frames):
            try:
                body = frame.locator("body").inner_text(timeout=800)
                blocks.append(f"--- FRAME {idx} ---\nURL: {frame.url}\n{body}\n")
            except Exception:
                pass
        (DEBUG_DIR / f"{safe}.txt").write_text("\n".join(blocks), encoding="utf-8")
    except Exception:
        pass


def open_wave_control_page(context):
    """
    Abre uma página interna da própria extensão WAVE.

    Ela funciona como ponte privilegiada para chrome.tabs/chrome.scripting,
    permitindo acionar o WAVE diretamente na aba do site.
    """
    url = f"chrome-extension://{WAVE_EXTENSION_ID}/sidebar.html"
    control = context.new_page()
    control.goto(url, wait_until="domcontentloaded", timeout=15000)
    control.wait_for_timeout(500)

    info = control.evaluate(
        """() => ({
            id: chrome.runtime.id,
            version: chrome.runtime.getManifest().version,
            hasTabs: !!chrome.tabs,
            hasScripting: !!chrome.scripting
        })"""
    )

    if info.get("id") != WAVE_EXTENSION_ID:
        raise RuntimeError(
            f"Página de controle WAVE abriu com ID inesperado: {info}"
        )

    if not info.get("hasTabs") or not info.get("hasScripting"):
        raise RuntimeError(
            "A página interna do WAVE não expôs chrome.tabs/chrome.scripting."
        )

    print(
        f"WAVE control ready: id={info.get('id')} "
        f"version={info.get('version')}"
    )

    return control


def activate_wave_on_page(wave_control_page, target_page) -> dict:
    """
    Injeta o WAVE na aba correta e corrige o src relativo do sidebar.

    Diagnóstico observado na versão 3.3.1.0:
      inject.js sozinho criou:
        https://SITE/sidebar.html

    O sidebar correto precisa apontar para:
      chrome-extension://<WAVE_ID>/sidebar.html

    Como sidebar.html é declarado em web_accessible_resources,
    podemos usar chrome.runtime.getURL("sidebar.html") e substituir o src.
    """
    target_page.bring_to_front()
    target_url = target_page.url

    return wave_control_page.evaluate(
        """async ({targetUrl}) => {
            const tabs = await chrome.tabs.query({});

            let candidates = tabs.filter(t => t.url === targetUrl);

            if (!candidates.length) {
                const normalized = (targetUrl || "").split("#")[0];
                candidates = tabs.filter(
                    t => ((t.url || "").split("#")[0] === normalized)
                );
            }

            let tab =
                candidates.find(t => t.active) ||
                candidates[candidates.length - 1];

            if (!tab || !tab.id) {
                const active = await chrome.tabs.query({
                    active: true,
                    currentWindow: true
                });
                tab = active[0];
            }

            if (!tab || !tab.id) {
                throw new Error(
                    "Não foi possível localizar a aba alvo para injetar o WAVE."
                );
            }

            const sidebarUrl = chrome.runtime.getURL("sidebar.html");

            const probe = await chrome.scripting.executeScript({
                target: {tabId: tab.id},
                func: () => {
                    const el = document.getElementById("wave_sidebar_container");
                    return el ? {
                        exists: true,
                        src: el.getAttribute("src") || "",
                        absoluteSrc: el.src || ""
                    } : {
                        exists: false,
                        src: "",
                        absoluteSrc: ""
                    };
                }
            });

            const existing = (
                probe &&
                probe[0] &&
                probe[0].result
            ) ? probe[0].result : {
                exists: false,
                src: "",
                absoluteSrc: ""
            };

            if (!existing.exists) {
                await chrome.scripting.executeScript({
                    target: {tabId: tab.id},
                    files: ["inject.js"]
                });
            }

            // Aguarda brevemente o inject.js criar o iframe.
            let iframeInfo = null;

            for (let attempt = 0; attempt < 20; attempt++) {
                const result = await chrome.scripting.executeScript({
                    target: {tabId: tab.id},
                    func: (correctSidebarUrl) => {
                        const iframe = document.getElementById(
                            "wave_sidebar_container"
                        );

                        if (!iframe) {
                            return {
                                found: false,
                                corrected: false,
                                src: "",
                                absoluteSrc: ""
                            };
                        }

                        const before = iframe.src || "";
                        let corrected = false;

                        if (
                            !before.startsWith("chrome-extension://")
                        ) {
                            iframe.src = correctSidebarUrl;
                            corrected = true;
                        }

                        return {
                            found: true,
                            corrected,
                            before,
                            src: iframe.getAttribute("src") || "",
                            absoluteSrc: iframe.src || ""
                        };
                    },
                    args: [sidebarUrl]
                });

                iframeInfo = (
                    result &&
                    result[0] &&
                    result[0].result
                ) ? result[0].result : null;

                if (iframeInfo && iframeInfo.found) {
                    break;
                }

                await new Promise(resolve => setTimeout(resolve, 100));
            }

            if (!iframeInfo || !iframeInfo.found) {
                throw new Error(
                    "inject.js executou, mas wave_sidebar_container não foi criado."
                );
            }

            return {
                tabId: tab.id,
                tabUrl: tab.url || "",
                sidebarUrl,
                iframe: iframeInfo
            };
        }""",
        {"targetUrl": target_url},
    )


def measure_aim_with_wave(
    page,
    wave_control_page,
    timeout_ms: int,
    label: str,
) -> float:
    """
    Ativa o WAVE diretamente pela API da extensão e lê o AIM
    no iframe wave_sidebar_container.
    """
    activation = activate_wave_on_page(
        wave_control_page,
        page,
    )

    deadline = time.time() + timeout_ms / 1000.0

    while time.time() < deadline:
        frame = find_wave_frame(page)

        if frame is not None:
            try:
                text = frame.locator("body").inner_text(timeout=1500)

                if "aim" in text.lower():
                    try:
                        return parse_aim_from_text(text)
                    except RuntimeError:
                        pass
            except Exception:
                pass

        page.wait_for_timeout(500)

    save_debug(page, f"{label}_wave_timeout")

    frame_urls = [frame.url for frame in page.frames]

    raise TimeoutError(
        "WAVE foi acionado e o sidebar foi corrigido, mas o AIM Score não apareceu "
        f"no tempo esperado. Activation={activation}. "
        f"Frames={frame_urls}. "
        "Veja results_aim/debug/ para screenshot e texto dos frames."
    )


def load_page(page, url: str, timeout_ms: int, wait_ms: int):
    page.set_default_timeout(timeout_ms)
    t0 = time.perf_counter()
    response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
    page.wait_for_timeout(wait_ms)
    return response, (time.perf_counter() - t0) * 1000


def perform_run(context, wave_control_page, item: Dict[str, Any], config: Dict[str, Any], trigger_js: str) -> Dict[str, Any]:
    row = base_row(item)
    nav_timeout = int(config.get("navigation_timeout_ms", 120000))
    wait_ms = int(config.get("post_load_wait_ms", 2500))
    adaptation_wait = int(config.get("adaptation_wait_ms", 180000))
    wave_timeout = int(config.get("wave_timeout_ms", 30000))

    baseline_page = None
    adapted_page = None

    try:
        # PRE: página sem disparar o ADHuman.
        baseline_page = context.new_page()
        response, load_ms = load_page(baseline_page, item["page"]["page_url"], nav_timeout, wait_ms)
        row["page_load_ms"] = round(load_ms, 2)
        row["http_status"] = response.status if response else ""
        row["pre_aim_score"] = round(
            measure_aim_with_wave(
                baseline_page,
                wave_control_page,
                wave_timeout,
                f"{item['site']['id']}_{item['profile']['id']}_pre",
            ),
            4,
        )
        baseline_page.close()
        baseline_page = None

        # POST: mesma URL, agora com ADHuman e o perfil correspondente.
        adapted_page = context.new_page()
        response2, _ = load_page(adapted_page, item["page"]["page_url"], nav_timeout, wait_ms)
        if response2:
            row["http_status"] = response2.status

        site, page_info, profile = item["site"], item["page"], item["profile"]
        website_context = dict(site)
        website_context.update({
            "site_url": site["url"],
            "url": page_info["page_url"],
            "page_id": page_info["page_id"],
            "page_title": page_info["page_title"],
        })
        experiment_context = {
            "run_id": item["run_id"],
            "profile": profile,
            "website": website_context,
            "page": page_info,
            "classifier": config.get("classifier", {}),
            "model": config.get("ollama_model", "llama3.1:8b"),
            "adaptation_wait_ms": adaptation_wait,
        }
        adapted_page.evaluate("ctx => { window.__ADHUMAN_EXPERIMENT__ = ctx; }", experiment_context)

        d0 = time.perf_counter()
        adhuman_result = adapted_page.evaluate(trigger_js)
        row["decision_latency_ms"] = round((time.perf_counter() - d0) * 1000, 2)

        if not isinstance(adhuman_result, dict):
            adhuman_result = {"ok": False, "error": f"Unexpected trigger result: {type(adhuman_result).__name__}"}

        row["adhuman_ok"] = adhuman_result.get("ok", "")
        row["adhuman_integration"] = adhuman_result.get("integration", "")
        row["classified_level"] = adhuman_result.get("level", "")
        row["human_assistance"] = adhuman_result.get("human_assistance", "")
        row["adhuman_decision"] = adhuman_result.get("decision", "")
        row["adhuman_plan"] = adhuman_result.get("plan", "")
        row["adhuman_confidence"] = adhuman_result.get("confidence", "")
        row["llm_inference_time_ms"] = adhuman_result.get("llm_inference_time_ms", "")
        if adhuman_result.get("error"):
            row["error"] = str(adhuman_result["error"])

        adapted_page.wait_for_timeout(wait_ms)
        row["post_aim_score"] = round(
            measure_aim_with_wave(
                adapted_page,
                wave_control_page,
                wave_timeout,
                f"{item['site']['id']}_{item['profile']['id']}_post",
            ),
            4,
        )

        pre = float(row["pre_aim_score"])
        post = float(row["post_aim_score"])
        row["aim_delta"] = round(post - pre, 4)
        row["aim_improvement_pct"] = round(((post - pre) / pre) * 100.0, 4) if pre else ""
        row["status"] = "integration_error" if adhuman_result.get("ok") is False else "ok"
        return row

    except PlaywrightTimeoutError as e:
        row["status"] = "timeout"
        row["error"] = str(e).replace("\n", " ")[:1500]
        return row
    except Exception as e:
        row["status"] = "error"
        row["error"] = f"{type(e).__name__}: {e}".replace("\n", " ")[:1500]
        return row
    finally:
        for page in (baseline_page, adapted_page):
            if page is not None:
                try:
                    page.close()
                except Exception:
                    pass


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ADHuman AIM: 30 sites x 4 perfis x 1 execução = 120 runs, usando a extensão WAVE gratuita."
    )
    parser.add_argument("--fresh", action="store_true", help="Apaga somente results_aim/raw_aim_runs.csv.")
    parser.add_argument("--smoke-test", action="store_true", help="2 sites x 4 perfis = 8 runs.")
    parser.add_argument(
        "--wave-extension",
        default=None,
        help="Pasta da extensão WAVE. Se omitida, autodetecta a instalação do Chrome no Windows.",
    )
    args = parser.parse_args()

    config = load_config()
    sites = selected_sites(config, load_sites())
    pages = homepage_pages(sites)
    adhuman_extension = validate_adhuman_extension(config)
    wave_extension = resolve_wave_extension(args.wave_extension)
    trigger_js = TRIGGER_PATH.read_text(encoding="utf-8")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    if args.fresh and RESULTS_FILE.exists():
        RESULTS_FILE.unlink()

    plan = build_plan(config, sites, pages, args.smoke_test)
    done = read_done_ids(RESULTS_FILE)
    pending = [x for x in plan if x["run_id"] not in done]

    print("Experiment: ADHuman-AIM-Improvement")
    print(f"ADHuman extension: {adhuman_extension}")
    print(f"WAVE extension: {wave_extension}")
    print(f"Sites: {len(sites)}")
    print(f"Profiles: {len(config.get('profiles', []))}")
    print("Repetitions/site-profile: 1")
    print("Official AIM design: 30 sites x 4 profiles x 1 run = 120 executions")
    print(f"Planned runs: {len(plan)} | already OK: {len(plan)-len(pending)} | pending: {len(pending)}")
    print(f"Results: {RESULTS_FILE}\n")

    if not pending:
        print("Nothing to do.")
        return 0

    viewport = config.get("viewport", {"width": 1440, "height": 1000})
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    extensions = f"{adhuman_extension},{wave_extension}"

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            viewport=viewport,
            ignore_https_errors=True,
            args=[
                f"--disable-extensions-except={extensions}",
                f"--load-extension={extensions}",
            ],
        )
        wave_control_page = None
        try:
            wave_control_page = open_wave_control_page(context)

            for idx, item in enumerate(pending, start=1):
                print(f"[{idx}/{len(pending)}] {item['site']['id']} {item['profile']['id']} rep=1")
                row = perform_run(
                    context,
                    wave_control_page,
                    item,
                    config,
                    trigger_js,
                )
                append_result(RESULTS_FILE, row)
                print(
                    "    status={} L{} preAIM={} postAIM={} delta={} improvement={}%".format(
                        row.get("status", ""), row.get("classified_level", ""),
                        row.get("pre_aim_score", ""), row.get("post_aim_score", ""),
                        row.get("aim_delta", ""), row.get("aim_improvement_pct", ""),
                    )
                )
                if row.get("error"):
                    print(f"    error={row['error'][:500]}")
        finally:
            try:
                context.close()
            except Exception:
                pass

    print(f"\nFinished. Results: {RESULTS_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
