from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


PROFILE_ORDER = [
    ("acuity_reference", "Padrão"),
    ("acuity_mild", "Leve"),
    ("acuity_moderate", "Moderado"),
    ("acuity_severe", "Severo"),
]

PROFILE_IDS = [p[0] for p in PROFILE_ORDER]
PROFILE_LABELS = dict(PROFILE_ORDER)


def first_existing(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for column in candidates:
        if column in df.columns:
            return column
    return None


def load_results(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {csv_path}")

    df = pd.read_csv(csv_path)

    required = ["site_id", "profile_id", "status"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            "O CSV não possui as colunas obrigatórias: " + ", ".join(missing)
        )

    level_col = first_existing(
        df,
        ["classified_level", "adhuman_level", "level", "final_level"],
    )
    if not level_col:
        raise ValueError(
            "Não encontrei a coluna do nível classificado. "
            "Esperado: classified_level, adhuman_level, level ou final_level."
        )

    df["_classified_level"] = pd.to_numeric(df[level_col], errors="coerce")

    valid = df[df["status"].astype(str).str.lower().eq("ok")].copy()
    valid = valid[valid["profile_id"].isin(PROFILE_IDS)].copy()

    if valid.empty:
        raise ValueError("Não há execuções válidas para analisar.")

    return valid


def build_site_summary(df: pd.DataFrame) -> pd.DataFrame:
    site_name_col = first_existing(df, ["site_name", "site"])
    country_col = first_existing(df, ["country"])

    rows = []
    site_ids = list(dict.fromkeys(df["site_id"].astype(str).tolist()))

    for site_id in site_ids:
        site_df = df[df["site_id"].astype(str) == str(site_id)]

        for profile_id, profile_label in PROFILE_ORDER:
            g = site_df[site_df["profile_id"] == profile_id].copy()
            if g.empty:
                continue

            levels = pd.to_numeric(g["_classified_level"], errors="coerce")

            l0 = int((levels == 0).sum())
            l1 = int((levels == 1).sum())
            l2 = int((levels == 2).sum())
            l3 = int((levels == 3).sum())

            successful_runs = int(len(g))
            human_assistance_count = l1 + l2 + l3
            human_assistance_pct = (
                human_assistance_count / successful_runs * 100
                if successful_runs
                else 0
            )

            site_name = (
                str(g[site_name_col].dropna().iloc[0])
                if site_name_col and not g[site_name_col].dropna().empty
                else str(site_id)
            )

            country = (
                str(g[country_col].dropna().iloc[0])
                if country_col and not g[country_col].dropna().empty
                else ""
            )

            rows.append(
                {
                    "site_id": site_id,
                    "site_name": site_name,
                    "country": country,
                    "profile_id": profile_id,
                    "profile_label": profile_label,
                    "successful_runs": successful_runs,
                    "level_0_count": l0,
                    "level_1_count": l1,
                    "level_2_count": l2,
                    "level_3_count": l3,
                    "human_assistance_count": human_assistance_count,
                    "human_assistance_pct": round(human_assistance_pct, 2),
                }
            )

    summary = pd.DataFrame(rows)

    if summary.empty:
        raise ValueError("Não foi possível montar o resumo por site.")

    order_map = {profile_id: i for i, profile_id in enumerate(PROFILE_IDS)}
    summary["_order"] = summary["profile_id"].map(order_map)
    summary = summary.sort_values(
        ["site_id", "_order"], kind="stable"
    ).drop(columns="_order").reset_index(drop=True)

    return summary


def build_global_summary(site_summary: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for profile_id, profile_label in PROFILE_ORDER:
        g = site_summary[site_summary["profile_id"] == profile_id].copy()
        if g.empty:
            continue

        total_runs = int(g["successful_runs"].sum())
        l0 = int(g["level_0_count"].sum())
        l1 = int(g["level_1_count"].sum())
        l2 = int(g["level_2_count"].sum())
        l3 = int(g["level_3_count"].sum())
        human_assistance_count = int(g["human_assistance_count"].sum())
        human_assistance_pct = (
            human_assistance_count / total_runs * 100 if total_runs else 0
        )

        rows.append(
            {
                "profile_id": profile_id,
                "profile_label": profile_label,
                "sites_count": int(g["site_id"].nunique()),
                "successful_runs": total_runs,
                "level_0_count": l0,
                "level_1_count": l1,
                "level_2_count": l2,
                "level_3_count": l3,
                "human_assistance_count": human_assistance_count,
                "human_assistance_pct": round(human_assistance_pct, 2),
            }
        )

    global_summary = pd.DataFrame(rows)

    if global_summary.empty:
        raise ValueError("Não foi possível montar o resumo global.")

    order_map = {profile_id: i for i, profile_id in enumerate(PROFILE_IDS)}
    global_summary["_order"] = global_summary["profile_id"].map(order_map)
    global_summary = global_summary.sort_values("_order").drop(columns="_order").reset_index(drop=True)

    return global_summary


def make_global_chart(global_summary: pd.DataFrame, output_dir: Path) -> Path:
    x_labels = global_summary["profile_label"].tolist()
    values = global_summary["human_assistance_count"].astype(int).tolist()
    total_runs = int(global_summary["successful_runs"].max())

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(x_labels, values)

    upper = max(values) if values else 0
    ax.set_ylim(0, upper + max(1, int(upper * 0.08)))

    ax.set_title("Participação humana por perfil — 25 sites")
    ax.set_xlabel("Perfil de acuidade visual")
    ax.set_ylabel("Quantidade de vezes que houve participação humana")
    ax.grid(axis="y", alpha=0.25)

    ax.bar_label(bars, labels=[str(v) for v in values], padding=3)

    if total_runs > 0:
        ax.axhline(total_runs, linewidth=1, linestyle="--", alpha=0.4)
        ax.text(
            0.99,
            0.98,
            f"Máximo por perfil = {total_runs}",
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=9,
        )

    fig.tight_layout()

    path = output_dir / "human_participation_all_sites.png"
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)

    return path


def write_outputs(site_summary: pd.DataFrame, global_summary: pd.DataFrame, output_dir: Path) -> tuple[Path, Path]:
    site_path = output_dir / "assistance_summary_by_site.csv"
    site_summary.to_csv(site_path, index=False, encoding="utf-8-sig")

    global_path = output_dir / "assistance_summary_global.csv"
    global_summary.to_csv(global_path, index=False, encoding="utf-8-sig")

    return site_path, global_path


def write_report(site_summary: pd.DataFrame, global_summary: pd.DataFrame, output_dir: Path, source_rows: int) -> Path:
    path = output_dir / "experiment_report.md"

    repetitions = int(site_summary["successful_runs"].max())
    total_assistance = int(site_summary["human_assistance_count"].sum())
    total_valid = int(site_summary["successful_runs"].sum())
    assistance_pct = (
        total_assistance / total_valid * 100 if total_valid else 0
    )

    lines = [
        "# ADHuman — Relatório do Experimento",
        "",
        "## Desenho experimental",
        "",
        "- Fatores: **perfil visual** e **site**.",
        "- Perfis: **Padrão, Leve, Moderado e Severo**.",
        f"- Execuções por combinação [perfil, site]: **{repetitions}**.",
        "- O nível de participação é uma **variável de resposta do Classifier**.",
        "- Métrica principal: **quantidade de vezes em que houve participação humana**.",
        "- Uma execução conta como participação humana quando o nível classificado é **L1, L2 ou L3**.",
        "- Level 0 representa ausência de participação humana.",
        "",
        "## Execução observada",
        "",
        f"- Linhas válidas consideradas na análise: **{source_rows}**.",
        f"- Participações humanas observadas no total: **{total_assistance}**.",
        f"- Taxa global de participação humana: **{assistance_pct:.2f}%**.",
        "",
        "## Resumo global por perfil",
        "",
        "| Perfil | Sites | Execuções | L0 | L1 | L2 | L3 | Participação humana | % |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for _, row in global_summary.iterrows():
        lines.append(
            f"| {row['profile_label']} | "
            f"{int(row['sites_count'])} | "
            f"{int(row['successful_runs'])} | "
            f"{int(row['level_0_count'])} | "
            f"{int(row['level_1_count'])} | "
            f"{int(row['level_2_count'])} | "
            f"{int(row['level_3_count'])} | "
            f"{int(row['human_assistance_count'])} | "
            f"{float(row['human_assistance_pct']):.2f}% |"
        )

    lines += [
        "",
        "## Interpretação da métrica",
        "",
        "`human_assistance_count = level_1_count + level_2_count + level_3_count`",
        "",
        "O gráfico principal agrega a ocorrência de participação humana em **todos os sites**. "
        "Assim, existe apenas um gráfico: no eixo X estão os níveis do fator Perfil "
        "(Padrão, Leve, Moderado e Severo), e no eixo Y está a quantidade total de vezes "
        "em que houve participação humana somando todos os sites.",
        "",
    ]

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analisa os resultados do experimento ADHuman."
    )
    parser.add_argument(
        "--input",
        default="results/raw_runs.csv",
        help="CSV de execuções (padrão: results/raw_runs.csv)",
    )
    parser.add_argument(
        "--output-dir",
        default="results/analysis",
        help="Diretório de saída (padrão: results/analysis)",
    )
    args = parser.parse_args()

    csv_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    valid = load_results(csv_path)
    site_summary = build_site_summary(valid)
    global_summary = build_global_summary(site_summary)

    site_summary_path, global_summary_path = write_outputs(site_summary, global_summary, output_dir)
    chart_path = make_global_chart(global_summary, output_dir)
    report_path = write_report(site_summary, global_summary, output_dir, len(valid))

    print("Análise concluída.")
    print(f"Resumo por site: {site_summary_path}")
    print(f"Resumo global: {global_summary_path}")
    print(f"Relatório: {report_path}")
    print(f"Gráfico consolidado: {chart_path}")

    return 0



if __name__ == "__main__":
    raise SystemExit(main())
