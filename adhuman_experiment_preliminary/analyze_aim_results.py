from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import friedmanchisquare, wilcoxon


PROFILE_ORDER = [
    ("acuity_reference", "Padrão"),
    ("acuity_mild", "Leve"),
    ("acuity_moderate", "Moderado"),
    ("acuity_severe", "Severo"),
]

PROFILE_LABELS = dict(PROFILE_ORDER)
PROFILE_IDS = [x[0] for x in PROFILE_ORDER]


def safe_mean(series: pd.Series) -> float | None:
    s = pd.to_numeric(series, errors="coerce").dropna()
    return None if s.empty else float(s.mean())


def safe_median(series: pd.Series) -> float | None:
    s = pd.to_numeric(series, errors="coerce").dropna()
    return None if s.empty else float(s.median())


def safe_std(series: pd.Series) -> float | None:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if len(s) < 2:
        return None
    return float(s.std(ddof=1))


def ci95_half_width(series: pd.Series) -> float | None:
    """
    IC 95% por aproximação normal:
        mean ± 1.96 * (sd / sqrt(n))
    """
    s = pd.to_numeric(series, errors="coerce").dropna()
    if len(s) < 2:
        return None
    return float(1.96 * s.std(ddof=1) / math.sqrt(len(s)))


def load_results(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {csv_path}")

    df = pd.read_csv(csv_path)

    required = [
        "site_id",
        "profile_id",
        "status",
        "pre_aim_score",
        "post_aim_score",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            "CSV sem colunas obrigatórias: " + ", ".join(missing)
        )

    df["pre_aim_score"] = pd.to_numeric(
        df["pre_aim_score"], errors="coerce"
    )
    df["post_aim_score"] = pd.to_numeric(
        df["post_aim_score"], errors="coerce"
    )

    valid = df[
        df["status"].astype(str).str.lower().eq("ok")
        & df["pre_aim_score"].notna()
        & df["post_aim_score"].notna()
    ].copy()

    if valid.empty:
        raise ValueError(
            "Não há execuções válidas com AIM pré e pós no CSV."
        )

    # Recalcula para garantir consistência, mesmo se as colunas derivadas
    # no run tiverem sido editadas ou estiverem ausentes.
    valid["aim_delta"] = (
        valid["post_aim_score"] - valid["pre_aim_score"]
    )

    valid["aim_improvement_pct"] = np.where(
        valid["pre_aim_score"] != 0,
        (
            (valid["post_aim_score"] - valid["pre_aim_score"])
            / valid["pre_aim_score"]
        )
        * 100.0,
        np.nan,
    )

    valid["profile_label_analysis"] = valid["profile_id"].map(
        PROFILE_LABELS
    ).fillna(valid["profile_id"].astype(str))

    return valid


def summary_from_group(g: pd.DataFrame) -> dict:
    pre = g["pre_aim_score"]
    post = g["post_aim_score"]
    delta = g["aim_delta"]
    pct = g["aim_improvement_pct"]

    pct_mean = safe_mean(pct)
    ci = ci95_half_width(pct)

    return {
        "successful_runs": int(len(g)),
        "aim_pre_mean": round(safe_mean(pre), 4),
        "aim_post_mean": round(safe_mean(post), 4),
        "aim_delta_mean": round(safe_mean(delta), 4),
        "aim_delta_median": round(safe_median(delta), 4),
        "aim_improvement_pct_mean": round(pct_mean, 4),
        "aim_improvement_pct_median": round(safe_median(pct), 4),
        "aim_improvement_pct_std": (
            round(safe_std(pct), 4)
            if safe_std(pct) is not None
            else None
        ),
        "aim_improvement_pct_ci95_half_width": (
            round(ci, 4) if ci is not None else None
        ),
        "aim_improvement_pct_ci95_low": (
            round(pct_mean - ci, 4)
            if pct_mean is not None and ci is not None
            else None
        ),
        "aim_improvement_pct_ci95_high": (
            round(pct_mean + ci, 4)
            if pct_mean is not None and ci is not None
            else None
        ),
        "runs_improved": int((delta > 0).sum()),
        "runs_unchanged": int((delta == 0).sum()),
        "runs_worsened": int((delta < 0).sum()),
    }


def build_overall_summary(df: pd.DataFrame) -> pd.DataFrame:
    row = {"scope": "overall"}
    row.update(summary_from_group(df))
    return pd.DataFrame([row])


def build_profile_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    observed = list(dict.fromkeys(df["profile_id"].astype(str).tolist()))
    ordered = [p for p in PROFILE_IDS if p in observed]
    ordered += [p for p in observed if p not in ordered]

    for profile_id in ordered:
        g = df[df["profile_id"].astype(str) == str(profile_id)]
        if g.empty:
            continue

        row = {
            "profile_id": profile_id,
            "profile_label": PROFILE_LABELS.get(profile_id, profile_id),
        }
        row.update(summary_from_group(g))
        rows.append(row)

    return pd.DataFrame(rows)



def build_site_profile_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """
    Matriz pareada Site x Perfil usando AIM improvement (%).
    Cada site deve possuir uma observação válida para cada um dos quatro perfis.
    """
    matrix = df.pivot_table(
        index="site_id",
        columns="profile_id",
        values="aim_improvement_pct",
        aggfunc="mean",
    )

    available = [p for p in PROFILE_IDS if p in matrix.columns]
    matrix = matrix[available]

    # Para Friedman, mantemos somente blocos completos.
    matrix = matrix.dropna(axis=0, how="any")
    return matrix


def holm_adjust(p_values: list[float]) -> list[float]:
    """
    Correção de Holm para múltiplas comparações.
    """
    m = len(p_values)
    order = sorted(range(m), key=lambda i: p_values[i])
    adjusted = [0.0] * m
    running_max = 0.0

    for rank, idx in enumerate(order):
        adjusted_value = min(1.0, (m - rank) * p_values[idx])
        running_max = max(running_max, adjusted_value)
        adjusted[idx] = running_max

    return adjusted


def run_friedman_and_posthoc(
    df: pd.DataFrame,
    output_dir: Path,
) -> tuple[Path, Path | None]:
    """
    Friedman:
      - bloco: site
      - tratamentos: quatro perfis de acuidade
      - resposta: AIM improvement (%)

    Se p < 0.05, também executa Wilcoxon pareado entre perfis
    com correção de Holm.
    """
    matrix = build_site_profile_matrix(df)

    friedman_path = output_dir / "aim_friedman_test.csv"
    posthoc_path = output_dir / "aim_posthoc_wilcoxon_holm.csv"

    if any(p not in matrix.columns for p in PROFILE_IDS):
        pd.DataFrame([{
            "complete_sites": int(len(matrix)),
            "statistic": None,
            "p_value": None,
            "significant_0_05": None,
            "note": "Friedman não executado: nem todos os quatro perfis estão presentes.",
        }]).to_csv(friedman_path, index=False, encoding="utf-8-sig")
        return friedman_path, None

    if len(matrix) < 2:
        pd.DataFrame([{
            "complete_sites": int(len(matrix)),
            "statistic": None,
            "p_value": None,
            "significant_0_05": None,
            "note": "Friedman não executado: são necessários pelo menos 2 sites completos.",
        }]).to_csv(friedman_path, index=False, encoding="utf-8-sig")
        return friedman_path, None

    arrays = [matrix[p].astype(float).to_numpy() for p in PROFILE_IDS]
    stat, p_value = friedmanchisquare(*arrays)

    friedman_df = pd.DataFrame([{
        "complete_sites": int(len(matrix)),
        "profiles": 4,
        "statistic": float(stat),
        "p_value": float(p_value),
        "significant_0_05": bool(p_value < 0.05),
        "response": "aim_improvement_pct",
        "block": "site_id",
    }])
    friedman_df.to_csv(friedman_path, index=False, encoding="utf-8-sig")

    if p_value >= 0.05:
        if posthoc_path.exists():
            posthoc_path.unlink()
        return friedman_path, None

    pairs = []
    raw_p_values = []

    for i in range(len(PROFILE_IDS)):
        for j in range(i + 1, len(PROFILE_IDS)):
            p1 = PROFILE_IDS[i]
            p2 = PROFILE_IDS[j]

            x = matrix[p1].astype(float)
            y = matrix[p2].astype(float)

            try:
                w_stat, raw_p = wilcoxon(
                    x,
                    y,
                    alternative="two-sided",
                    zero_method="wilcox",
                )
            except ValueError:
                # Ex.: todas as diferenças são zero.
                w_stat, raw_p = 0.0, 1.0

            pairs.append({
                "profile_1": p1,
                "profile_1_label": PROFILE_LABELS.get(p1, p1),
                "profile_2": p2,
                "profile_2_label": PROFILE_LABELS.get(p2, p2),
                "n_sites": int(len(matrix)),
                "wilcoxon_statistic": float(w_stat),
                "raw_p_value": float(raw_p),
                "mean_difference_pct": float((x - y).mean()),
                "median_difference_pct": float((x - y).median()),
            })
            raw_p_values.append(float(raw_p))

    adjusted = holm_adjust(raw_p_values)

    for row, adj in zip(pairs, adjusted):
        row["holm_adjusted_p_value"] = float(adj)
        row["significant_0_05"] = bool(adj < 0.05)

    pd.DataFrame(pairs).to_csv(
        posthoc_path,
        index=False,
        encoding="utf-8-sig",
    )

    return friedman_path, posthoc_path


def build_site_profile_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    group_cols = ["site_id", "profile_id"]

    for (site_id, profile_id), g in df.groupby(
        group_cols, sort=False, dropna=False
    ):
        site_name = (
            str(g["site_name"].dropna().iloc[0])
            if "site_name" in g.columns and not g["site_name"].dropna().empty
            else str(site_id)
        )

        row = {
            "site_id": site_id,
            "site_name": site_name,
            "profile_id": profile_id,
            "profile_label": PROFILE_LABELS.get(
                str(profile_id), str(profile_id)
            ),
        }
        row.update(summary_from_group(g))
        rows.append(row)

    result = pd.DataFrame(rows)

    if result.empty:
        return result

    profile_order = {pid: i for i, pid in enumerate(PROFILE_IDS)}
    result["_profile_order"] = (
        result["profile_id"].astype(str).map(profile_order).fillna(999)
    )

    result = (
        result.sort_values(
            ["site_id", "_profile_order"],
            kind="stable",
        )
        .drop(columns=["_profile_order"])
        .reset_index(drop=True)
    )

    return result


def make_improvement_by_profile_chart(
    profile_summary: pd.DataFrame,
    output_dir: Path,
) -> Path:
    labels = profile_summary["profile_label"].tolist()
    values = profile_summary[
        "aim_improvement_pct_mean"
    ].astype(float).to_numpy()

    error = (
        pd.to_numeric(
            profile_summary["aim_improvement_pct_ci95_half_width"],
            errors="coerce",
        )
        .fillna(0)
        .to_numpy()
    )

    fig, ax = plt.subplots(figsize=(9, 6))
    x = np.arange(len(labels))

    bars = ax.bar(
        x,
        values,
        yerr=error,
        capsize=5,
    )

    ax.axhline(0, linewidth=1)
    ax.set_xticks(x, labels)
    ax.set_xlabel("Perfil de acuidade visual")
    ax.set_ylabel("Melhoria média do AIM (%)")
    ax.set_title("Melhoria do AIM Score por perfil")
    ax.grid(axis="y", alpha=0.25)

    value_labels = [f"{v:.2f}%" for v in values]
    ax.bar_label(bars, labels=value_labels, padding=3)

    fig.tight_layout()

    path = output_dir / "aim_improvement_by_profile.png"
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return path


def make_pre_post_chart(
    profile_summary: pd.DataFrame,
    output_dir: Path,
) -> Path:
    labels = profile_summary["profile_label"].tolist()
    pre = profile_summary["aim_pre_mean"].astype(float).to_numpy()
    post = profile_summary["aim_post_mean"].astype(float).to_numpy()

    x = np.arange(len(labels))
    width = 0.38

    fig, ax = plt.subplots(figsize=(10, 6))
    bars1 = ax.bar(x - width / 2, pre, width, label="Antes do ADHuman")
    bars2 = ax.bar(x + width / 2, post, width, label="Depois do ADHuman")

    ax.set_xticks(x, labels)
    ax.set_xlabel("Perfil de acuidade visual")
    ax.set_ylabel("AIM Score")
    ax.set_ylim(0, 10)
    ax.set_title("AIM Score antes e depois da atuação do ADHuman")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)

    ax.bar_label(bars1, labels=[f"{v:.2f}" for v in pre], padding=3)
    ax.bar_label(bars2, labels=[f"{v:.2f}" for v in post], padding=3)

    fig.tight_layout()

    path = output_dir / "aim_pre_post_by_profile.png"
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return path


def make_heatmap(
    site_profile_summary: pd.DataFrame,
    output_dir: Path,
) -> Path | None:
    if site_profile_summary.empty:
        return None

    table = site_profile_summary.pivot(
        index="site_id",
        columns="profile_id",
        values="aim_improvement_pct_mean",
    )

    ordered_cols = [c for c in PROFILE_IDS if c in table.columns]
    ordered_cols += [c for c in table.columns if c not in ordered_cols]
    table = table[ordered_cols]

    # Ordenação simples P01, P02, ...
    table = table.sort_index()

    data = table.to_numpy(dtype=float)

    fig_height = max(7, 0.32 * len(table.index) + 2)
    fig, ax = plt.subplots(figsize=(9, fig_height))

    image = ax.imshow(data, aspect="auto")

    ax.set_xticks(
        np.arange(len(table.columns)),
        [PROFILE_LABELS.get(c, c) for c in table.columns],
    )
    ax.set_yticks(
        np.arange(len(table.index)),
        table.index.tolist(),
    )

    ax.set_xlabel("Perfil de acuidade visual")
    ax.set_ylabel("Site")
    ax.set_title("Melhoria média do AIM (%) por site e perfil")

    # Rótulos numéricos em cada célula.
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            value = data[i, j]
            if np.isfinite(value):
                ax.text(
                    j,
                    i,
                    f"{value:.1f}",
                    ha="center",
                    va="center",
                    fontsize=8,
                )

    cbar = fig.colorbar(image, ax=ax)
    cbar.set_label("Melhoria média do AIM (%)")

    fig.tight_layout()

    path = output_dir / "aim_improvement_heatmap_site_profile.png"
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return path


def write_report(
    df: pd.DataFrame,
    overall: pd.DataFrame,
    profiles: pd.DataFrame,
    output_dir: Path,
    friedman_path: Path,
    posthoc_path: Path | None,
) -> Path:
    path = output_dir / "aim_report.md"

    o = overall.iloc[0]

    lines = [
        "# ADHuman — AIM Score Improvement",
        "",
        "## Métrica",
        "",
        "Para cada execução válida:",
        "",
        "`AIM_delta = AIM_post - AIM_pre`",
        "",
        "`AIM_improvement_pct = ((AIM_post - AIM_pre) / AIM_pre) * 100`",
        "",
        "O AIM pré é medido antes de disparar o ciclo experimental do ADHuman. "
        "O AIM pós é medido no mesmo DOM após a adaptação e estabilização.",
        "",
        "## Resultado geral",
        "",
        f"- Execuções válidas: **{int(o['successful_runs'])}**",
        f"- AIM médio pré: **{float(o['aim_pre_mean']):.4f}**",
        f"- AIM médio pós: **{float(o['aim_post_mean']):.4f}**",
        f"- ΔAIM médio: **{float(o['aim_delta_mean']):.4f}**",
        f"- Melhoria média do AIM: **{float(o['aim_improvement_pct_mean']):.2f}%**",
        f"- Execuções com melhoria: **{int(o['runs_improved'])}**",
        f"- Execuções sem mudança: **{int(o['runs_unchanged'])}**",
        f"- Execuções com piora: **{int(o['runs_worsened'])}**",
        "",
        "## Resultado por perfil",
        "",
        "| Perfil | N | AIM pré | AIM pós | ΔAIM | Melhoria média | IC95% |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]

    for _, row in profiles.iterrows():
        low = row["aim_improvement_pct_ci95_low"]
        high = row["aim_improvement_pct_ci95_high"]

        ci_text = (
            f"[{float(low):.2f}%; {float(high):.2f}%]"
            if pd.notna(low) and pd.notna(high)
            else "—"
        )

        lines.append(
            f"| {row['profile_label']} | "
            f"{int(row['successful_runs'])} | "
            f"{float(row['aim_pre_mean']):.4f} | "
            f"{float(row['aim_post_mean']):.4f} | "
            f"{float(row['aim_delta_mean']):.4f} | "
            f"{float(row['aim_improvement_pct_mean']):.2f}% | "
            f"{ci_text} |"
        )

    lines += [
        "",
        "## Arquivos gerados",
        "",
        "- `aim_overall_summary.csv`",
        "- `aim_summary_by_profile.csv`",
        "- `aim_summary_by_site_profile.csv`",
        "- `aim_improvement_by_profile.png`",
        "- `aim_pre_post_by_profile.png`",
        "- `aim_improvement_heatmap_site_profile.png`",
        "- `aim_friedman_test.csv`",
        "- `aim_posthoc_wilcoxon_holm.csv` (gerado somente se Friedman p < 0.05)",
        "",
        "## Comparação entre perfis",
        "",
        "O teste de Friedman usa **site** como bloco e os quatro perfis como tratamentos, "
        "com `aim_improvement_pct` como variável resposta. Somente sites com os quatro "
        "perfis válidos entram no teste.",
        "",
        "Quando Friedman apresenta p < 0.05, são executadas comparações pareadas de "
        "Wilcoxon entre perfis com correção de Holm.",
        "",
        "O IC95% é calculado por aproximação normal: "
        "`média ± 1.96 * erro-padrão`.",
    ]

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analisa somente a métrica de melhoria do AIM Score."
    )
    parser.add_argument(
        "--input",
        default="results_aim/raw_aim_runs.csv",
        help="CSV gerado por run_aim_experiment.py",
    )
    parser.add_argument(
        "--output-dir",
        default="results_aim/analysis",
        help="Diretório dos resultados da análise.",
    )
    args = parser.parse_args()

    csv_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = load_results(csv_path)

    overall = build_overall_summary(df)
    profiles = build_profile_summary(df)
    site_profiles = build_site_profile_summary(df)

    overall_path = output_dir / "aim_overall_summary.csv"
    profile_path = output_dir / "aim_summary_by_profile.csv"
    site_profile_path = output_dir / "aim_summary_by_site_profile.csv"

    overall.to_csv(overall_path, index=False, encoding="utf-8-sig")
    profiles.to_csv(profile_path, index=False, encoding="utf-8-sig")
    site_profiles.to_csv(
        site_profile_path,
        index=False,
        encoding="utf-8-sig",
    )

    chart1 = make_improvement_by_profile_chart(
        profiles, output_dir
    )
    chart2 = make_pre_post_chart(
        profiles, output_dir
    )
    chart3 = make_heatmap(
        site_profiles, output_dir
    )

    friedman_path, posthoc_path = run_friedman_and_posthoc(
        df=df,
        output_dir=output_dir,
    )

    report = write_report(
        df=df,
        overall=overall,
        profiles=profiles,
        output_dir=output_dir,
        friedman_path=friedman_path,
        posthoc_path=posthoc_path,
    )

    print("Análise AIM concluída.")
    print(f"Execuções válidas: {len(df)}")
    print(f"Resumo geral: {overall_path}")
    print(f"Resumo por perfil: {profile_path}")
    print(f"Resumo site x perfil: {site_profile_path}")
    print(f"Gráfico: {chart1}")
    print(f"Gráfico: {chart2}")
    if chart3:
        print(f"Heatmap: {chart3}")
    print(f"Friedman: {friedman_path}")
    if posthoc_path:
        print(f"Post-hoc Wilcoxon + Holm: {posthoc_path}")
    print(f"Relatório: {report}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
