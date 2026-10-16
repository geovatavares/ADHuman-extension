from __future__ import annotations

import argparse
import csv
import json
import random
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "experiment_config.json"
SITES_PATH = ROOT / "sites.csv"
SCANNER_PATH = ROOT / "contrast_scanner.js"
TRIGGER_PATH = ROOT / "extension_trigger.js"

FIELDS = [
    "run_id", "timestamp_utc", "site_id", "site_name", "group", "country", "site_url",
    "page_id", "page_order", "page_depth", "page_title", "page_url",
    "requested_url", "final_url", "profile_id", "profile_label", "profile_short_label",
    "profile_target_contrast_ratio", "repetition", "status", "error", "http_status",
    "page_load_ms", "decision_latency_ms", "llm_inference_time_ms", "adhuman_ok",
    "adhuman_integration", "classified_level", "human_assistance", "classifier_basis",
    "classifier_issue_count", "classifier_checked_elements", "classifier_affected_pct",
    "classifier_lowest_ratio", "classifier_target_contrast_ratio", "classifier_rationale",
    "adhuman_decision", "adhuman_plan", "adhuman_confidence", "adhuman_perceived_fit",
    "adhuman_reason_codes", "adhuman_rationale", "backend_run_id", "adhuman_remaining_issues",
    "pre_assessed_text_elements", "pre_contrast_failures", "pre_contrast_ratio_min",
    "pre_contrast_ratio_mean", "pre_contrast_ratio_median", "pre_skipped_background_image",
    "post_assessed_text_elements", "post_contrast_failures", "post_contrast_ratio_min",
    "post_contrast_ratio_mean", "post_contrast_ratio_median", "post_skipped_background_image",
    "failure_delta", "failure_improvement_pct"
]


def load_config() -> Dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def load_sites() -> List[Dict[str, str]]:
    with open(SITES_PATH, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def selected_sites(config: Dict[str, Any], sites: List[Dict[str, str]]) -> List[Dict[str, str]]:
    requested = [str(x) for x in config.get("site_ids", [])]
    if not requested:
        return sites[:30]
    by_id = {site["id"]: site for site in sites}
    missing = [site_id for site_id in requested if site_id not in by_id]
    if missing:
        raise SystemExit(f"Sites configurados nao encontrados em sites.csv: {missing}")
    return [by_id[site_id] for site_id in requested]


def homepage_pages(sites: List[Dict[str, str]]) -> List[Dict[str, str]]:
    pages: List[Dict[str, str]] = []
    for site in sites:
        pages.append({
            "site_id": site["id"],
            "page_id": f"{site['id']}-HOME",
            "page_order": "1",
            "page_depth": "0",
            "page_title": "Homepage",
            "page_url": site["url"],
        })
    return pages

def load_js(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_done_ids(results_file: Path) -> set[str]:
    if not results_file.exists():
        return set()
    with open(results_file, "r", encoding="utf-8-sig", newline="") as f:
        return {row["run_id"] for row in csv.DictReader(f) if row.get("run_id")}


def append_result(results_file: Path, row: Dict[str, Any]) -> None:
    results_file.parent.mkdir(parents=True, exist_ok=True)
    exists = results_file.exists() and results_file.stat().st_size > 0
    normalized = {k: row.get(k, "") for k in FIELDS}
    with open(results_file, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow(normalized)


def stable_run_id(site_id: str, page_url: str, profile_id: str, repetition: int) -> str:
    key = f"homepage-experiment|{site_id}|{page_url}|{profile_id}|{repetition}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, key))


def build_plan(config: Dict[str, Any], sites: List[Dict[str, str]], pages: List[Dict[str, str]], smoke_test: bool) -> List[Dict[str, Any]]:
    reps = int(config.get("repetitions_per_page_profile", 1))
    profiles = config.get("profiles", [])
    sites_by_id = {s["id"]: s for s in sites}
    plan: List[Dict[str, Any]] = []

    for page_info in pages:
        site = sites_by_id[page_info["site_id"]]
        for profile in profiles:
            for rep in range(1, reps + 1):
                plan.append({
                    "site": site,
                    "page": page_info,
                    "profile": profile,
                    "repetition": rep,
                    "run_id": stable_run_id(site["id"], page_info["page_url"], profile["id"], rep),
                })

    if smoke_test:
        # 2 sites x homepage (PG01) x 4 perfis = 8 execucoes.
        smoke_sites = [s["id"] for s in sites[:2]]
        return [
            item for item in plan
            if item["site"]["id"] in smoke_sites
            and int(item["page"].get("page_order") or 0) == 1
            and item["repetition"] == 1
        ]

    rng = random.Random(int(config.get("seed", 20260923)))
    rng.shuffle(plan)
    return plan


def scan_page(page, scanner_js: str) -> Dict[str, Any]:
    return page.evaluate(scanner_js)


def scan_fields(prefix: str, scan: Dict[str, Any]) -> Dict[str, Any]:
    return {
        f"{prefix}_assessed_text_elements": scan.get("assessed_text_elements", ""),
        f"{prefix}_contrast_failures": scan.get("contrast_failures", ""),
        f"{prefix}_contrast_ratio_min": scan.get("contrast_ratio_min", ""),
        f"{prefix}_contrast_ratio_mean": scan.get("contrast_ratio_mean", ""),
        f"{prefix}_contrast_ratio_median": scan.get("contrast_ratio_median", ""),
        f"{prefix}_skipped_background_image": scan.get("skipped_background_image", ""),
    }


def result_base(item: Dict[str, Any]) -> Dict[str, Any]:
    site = item["site"]
    p = item["page"]
    profile = item["profile"]
    return {
        "run_id": item["run_id"],
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "site_id": site["id"],
        "site_name": site["name"],
        "group": site["group"],
        "country": site["country"],
        "site_url": site["url"],
        "page_id": p.get("page_id", ""),
        "page_order": p.get("page_order", ""),
        "page_depth": p.get("page_depth", ""),
        "page_title": p.get("page_title", ""),
        "page_url": p["page_url"],
        "requested_url": p["page_url"],
        "profile_id": profile["id"],
        "profile_label": profile.get("label", profile["id"]),
        "profile_short_label": profile.get("short_label", profile.get("label", profile["id"])),
        "profile_target_contrast_ratio": profile.get("target_contrast_ratio", ""),
        "repetition": item["repetition"],
        "status": "started",
        "error": "",
    }


def perform_run(page, item: Dict[str, Any], config: Dict[str, Any], scanner_js: str, trigger_js: str) -> Dict[str, Any]:
    row = result_base(item)
    timeout = max(int(config.get("navigation_timeout_ms", 120000)), 120000)
    post_wait = int(config.get("post_load_wait_ms", 2500))
    adaptation_wait = max(int(config.get("adaptation_wait_ms", 360000)), 360000)
    page.set_default_timeout(timeout)
    page.set_default_navigation_timeout(timeout)

    try:
        t0 = time.perf_counter()
        response = None
        last_nav_error = None
        for nav_attempt in range(1, 3):
            try:
                response = page.goto(
                    item["page"]["page_url"],
                    wait_until="domcontentloaded",
                    timeout=timeout,
                )
                last_nav_error = None
                break
            except PlaywrightTimeoutError as exc:
                last_nav_error = exc
                if nav_attempt >= 2:
                    raise
                try:
                    page.evaluate("window.stop()")
                except Exception:
                    pass
                page.wait_for_timeout(3000)

        if last_nav_error is not None:
            raise last_nav_error

        page.wait_for_timeout(post_wait)
        row["page_load_ms"] = round((time.perf_counter() - t0) * 1000, 2)
        row["http_status"] = response.status if response else ""
        row["final_url"] = page.url

        pre = scan_page(page, scanner_js)
        row.update(scan_fields("pre", pre))

        website_context = dict(item["site"])
        website_context["site_url"] = item["site"]["url"]
        website_context["url"] = item["page"]["page_url"]
        website_context["page_id"] = item["page"].get("page_id", "")
        website_context["page_title"] = item["page"].get("page_title", "")

        experiment_context = {
            "run_id": item["run_id"],
            "profile": item["profile"],
            "website": website_context,
            "page": item["page"],
            "classifier": config.get("classifier", {}),
            "model": config.get("ollama_model", "llama3.1:8b"),
            "adaptation_wait_ms": adaptation_wait,
        }
        page.evaluate("ctx => { window.__ADHUMAN_EXPERIMENT__ = ctx; }", experiment_context)
        d0 = time.perf_counter()
        adhuman_result = page.evaluate(trigger_js)
        row["decision_latency_ms"] = round((time.perf_counter() - d0) * 1000, 2)
        if not isinstance(adhuman_result, dict):
            adhuman_result = {"ok": False, "error": f"Unexpected trigger result: {type(adhuman_result).__name__}"}

        row["adhuman_ok"] = adhuman_result.get("ok", "")
        row["adhuman_integration"] = adhuman_result.get("integration", "")
        row["classified_level"] = adhuman_result.get("level", "")
        row["human_assistance"] = adhuman_result.get("human_assistance", "")
        row["classifier_basis"] = adhuman_result.get("classifier_basis", "")
        row["classifier_issue_count"] = adhuman_result.get("classifier_issue_count", "")
        row["classifier_checked_elements"] = adhuman_result.get("classifier_checked_elements", "")
        row["classifier_affected_pct"] = adhuman_result.get("classifier_affected_pct", "")
        row["classifier_lowest_ratio"] = adhuman_result.get("classifier_lowest_ratio", "")
        row["classifier_target_contrast_ratio"] = adhuman_result.get("classifier_target_contrast_ratio", "")
        row["classifier_rationale"] = adhuman_result.get("classifier_rationale", "")
        row["adhuman_decision"] = adhuman_result.get("decision", "")
        row["adhuman_plan"] = adhuman_result.get("plan", "")
        row["adhuman_confidence"] = adhuman_result.get("confidence", "")
        row["adhuman_perceived_fit"] = adhuman_result.get("perceived_accessibility_fit", "")
        row["adhuman_reason_codes"] = json.dumps(adhuman_result.get("reason_codes", []), ensure_ascii=False)
        row["adhuman_rationale"] = adhuman_result.get("rationale", "")
        row["backend_run_id"] = adhuman_result.get("backend_run_id", "")
        row["llm_inference_time_ms"] = adhuman_result.get("llm_inference_time_ms", "")
        row["adhuman_remaining_issues"] = adhuman_result.get("remaining_issues", "")

        if adhuman_result.get("error"):
            row["error"] = str(adhuman_result.get("error"))

        page.wait_for_timeout(post_wait)
        post = scan_page(page, scanner_js)
        row.update(scan_fields("post", post))

        pre_f, post_f = pre.get("contrast_failures"), post.get("contrast_failures")
        if isinstance(pre_f, (int, float)) and isinstance(post_f, (int, float)):
            row["failure_delta"] = pre_f - post_f
            row["failure_improvement_pct"] = round(((pre_f - post_f) / pre_f) * 100, 3) if pre_f else 0.0

        row["status"] = "integration_error" if adhuman_result.get("ok") is False else "ok"
        return row

    except PlaywrightTimeoutError as e:
        row["status"] = "timeout"
        row["error"] = str(e).replace("\n", " ")[:1000]
        try:
            row["final_url"] = page.url
        except Exception:
            pass
        return row
    except Exception as e:
        row["status"] = "error"
        row["error"] = f"{type(e).__name__}: {e}".replace("\n", " ")[:1000]
        try:
            row["final_url"] = page.url
        except Exception:
            pass
        return row


def validate_extension_path(config: Dict[str, Any]) -> Path:
    raw = str(config.get("extension_path", "")).strip()
    path = Path(raw)
    if raw and not path.is_absolute():
        path = (ROOT / path).resolve()
    if not raw or not path.exists():
        raise SystemExit("'extension_path' nao aponta para uma pasta existente.")
    if not (path / "manifest.json").exists():
        raise SystemExit(f"manifest.json nao encontrado em: {path}")
    return path.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="ADHuman 30 sites x homepage x 4 profiles experiment")
    parser.add_argument("--mode", choices=["extension"], default="extension")
    parser.add_argument("--smoke-test", action="store_true", help="2 sites x homepage x 4 perfis = 8 runs")
    parser.add_argument("--fresh", action="store_true", help="Apaga results/raw_runs.csv e reinicia")
    args = parser.parse_args()

    config = load_config()
    sites = selected_sites(config, load_sites())
    pages = homepage_pages(sites)
    print(f"Homepages fixadas para o experimento: {len(pages)}/{len(sites)}")

    scanner_js, trigger_js = load_js(SCANNER_PATH), load_js(TRIGGER_PATH)
    results_file = ROOT / config.get("results_file", "results/raw_runs.csv")
    if args.fresh and results_file.exists():
        results_file.unlink()

    plan = build_plan(config, sites, pages, args.smoke_test)
    done = read_done_ids(results_file)
    pending = [x for x in plan if x["run_id"] not in done]

    print(f"Experiment: {config.get('experiment_name')}")
    print(
        f"Sites: {len(sites)} | Pages/site: 1 (homepage) | "
        f"Profiles: {len(config.get('profiles', []))} | Repetitions/page-profile: {config.get('repetitions_per_page_profile')}"
    )
    print(f"Planned runs: {len(plan)} | already done: {len(plan)-len(pending)} | pending: {len(pending)}")
    if not pending:
        print("Nothing to do.")
        return 0

    extension_path = validate_extension_path(config)
    viewport = config.get("viewport", {"width": 1440, "height": 1000})
    profile_dir = ROOT / config.get("browser_user_data_dir", "results/playwright-profile")
    profile_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        extension_context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=False,
            viewport=viewport,
            ignore_https_errors=True,
            args=[f"--disable-extensions-except={extension_path}", f"--load-extension={extension_path}"],
        )
        try:
            for idx, item in enumerate(pending, start=1):
                page = extension_context.new_page()
                profile = item["profile"]
                pinfo = item["page"]
                print(
                    f"[{idx}/{len(pending)}] {item['site']['id']} {pinfo.get('page_id','')} "
                    f"{profile['id']} rep={item['repetition']}"
                )
                row = perform_run(page, item, config, scanner_js, trigger_js)
                append_result(results_file, row)
                try:
                    page.close()
                except Exception:
                    pass
                print(
                    "    status={} level=L{} assisted={} issues={} decision={} plan={}".format(
                        row.get("status", ""), row.get("classified_level", ""),
                        row.get("human_assistance", ""), row.get("classifier_issue_count", ""),
                        row.get("adhuman_decision", ""), row.get("adhuman_plan", ""),
                    )
                )
        finally:
            try:
                extension_context.close()
            except Exception:
                pass

    print(f"Results: {results_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
