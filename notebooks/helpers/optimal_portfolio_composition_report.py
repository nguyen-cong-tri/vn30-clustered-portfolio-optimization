from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


def load_weights(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"ticker", "cluster_id", "weight"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in {path}: {sorted(missing)}")
    return df.loc[:, ["ticker", "cluster_id", "weight"]].copy()


def filter_positive_weights(df: pd.DataFrame) -> pd.DataFrame:
    positive = df[df["weight"] > 0].copy()
    if positive.empty:
        raise ValueError("No positive portfolio weights available for report generation")
    return positive.sort_values("weight", ascending=False, kind="mergesort").reset_index(drop=True)


def build_top_n_with_remainder(
    df: pd.DataFrame,
    top_n: int = 8,
    remainder_label: str = "Còn lại",
) -> pd.DataFrame:
    positive = filter_positive_weights(df)
    top = positive.head(top_n).copy()
    remainder = positive.iloc[top_n:]["weight"].sum()
    if remainder > 0:
        top.loc[len(top)] = {"ticker": remainder_label, "cluster_id": "", "weight": remainder}
    return top.reset_index(drop=True)


def has_remainder_bucket(summary: pd.DataFrame, remainder_label: str = "Còn lại") -> bool:
    return remainder_label in summary["ticker"].tolist()


def build_scope_label(summary: pd.DataFrame, top_n: int, remainder_label: str = "Còn lại") -> str:
    if has_remainder_bucket(summary, remainder_label=remainder_label):
        return f"Top {top_n} + {remainder_label}"
    return f"{len(summary)} mã có tỷ trọng dương"


def build_chart_title(strategy_label: str, summary: pd.DataFrame, top_n: int) -> str:
    return f"Danh mục {strategy_label} - {build_scope_label(summary, top_n=top_n)}"


def render_composition_chart(summary: pd.DataFrame, title: str, output_path: Path, color: str) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plot_df = summary.copy().sort_values("weight", ascending=True)
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.barh(plot_df["ticker"], plot_df["weight"] * 100, color=color, alpha=0.9)
    ax.set_title(title)
    ax.set_xlabel("Tỷ trọng (%)")
    ax.set_ylabel("Mã cổ phiếu")
    ax.grid(axis="x", alpha=0.25)
    for index, value in enumerate(plot_df["weight"] * 100):
        ax.text(value + 0.15, index, f"{value:.2f}%", va="center", fontsize=9)
    plt.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return output_path


def summarize_top_holdings_for_markdown(df: pd.DataFrame, top_n: int) -> str:
    positive = filter_positive_weights(df)
    tickers = positive.head(top_n)["ticker"].tolist()
    return ", ".join(tickers)


def write_markdown_report(
    output_path: Path,
    gmv_df: pd.DataFrame,
    aggressive_df: pd.DataFrame,
    gmv_figure: Path,
    aggressive_figure: Path,
    top_n: int,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    gmv_scope_label = build_scope_label(build_top_n_with_remainder(gmv_df, top_n=top_n), top_n=top_n)
    aggressive_scope_label = build_scope_label(
        build_top_n_with_remainder(aggressive_df, top_n=top_n),
        top_n=top_n,
    )
    gmv_link = (Path("figures") / gmv_figure.name).as_posix()
    aggressive_link = (Path("figures") / aggressive_figure.name).as_posix()
    text = f"""# Danh mục tối ưu đại diện trong đề tài

## 1. Danh mục tối ưu được hiểu như thế nào trong đề tài

Trong đề tài này, danh mục tối ưu không được hiểu là một danh mục duy nhất cho mọi nhà đầu tư. Thay vào đó, tính tối ưu được xác định theo mục tiêu tối ưu hóa cụ thể. Danh mục `GMV Defensive` là danh mục tối ưu theo mục tiêu giảm rủi ro, trong khi danh mục `Aggressive` là danh mục tối ưu theo mục tiêu theo đuổi mức sinh lợi cao hơn trong cùng khung ràng buộc hiện tại.

## 2. Thành phần hai danh mục tối ưu đại diện

Danh mục `GMV Defensive` hiện có các mã chiếm tỷ trọng lớn nhất như: {summarize_top_holdings_for_markdown(gmv_df, top_n=top_n)}. Phần còn lại được phân tán trên nhiều mã với tỷ trọng nhỏ.

Danh mục `Aggressive` hiện có các mã chiếm tỷ trọng lớn nhất như: {summarize_top_holdings_for_markdown(aggressive_df, top_n=top_n)}.

Biểu đồ thành phần:

- [GMV Defensive {gmv_scope_label}]({gmv_link})
- [Aggressive {aggressive_scope_label}]({aggressive_link})

## 3. Ghi chú về vai trò của rolling

Các tỷ trọng trình bày trong tài liệu này được lấy từ artifact tĩnh (static) vì đây là nguồn phù hợp để trả lời câu hỏi “danh mục tối ưu gồm những mã nào”. Phần rolling đóng vai trò kiểm định ngoài mẫu theo thời gian và không đại diện cho một danh mục cố định duy nhất.
"""
    output_path.write_text(text, encoding="utf-8")
    return output_path


def generate_optimal_portfolio_report(
    gmv_path: Path,
    aggressive_path: Path,
    output_dir: Path,
    top_n: int = 8,
    write_markdown: bool = True,
):
    gmv_df = load_weights(gmv_path)
    aggressive_df = load_weights(aggressive_path)

    figures_dir = output_dir / "figures"
    gmv_summary = build_top_n_with_remainder(gmv_df, top_n=top_n)
    aggressive_summary = build_top_n_with_remainder(aggressive_df, top_n=top_n)

    gmv_figure = render_composition_chart(
        gmv_summary,
        title=build_chart_title("GMV Defensive", gmv_summary, top_n=top_n),
        output_path=figures_dir / f"optimal_gmv_defensive_top{top_n}.png",
        color="steelblue",
    )
    aggressive_figure = render_composition_chart(
        aggressive_summary,
        title=build_chart_title("Aggressive", aggressive_summary, top_n=top_n),
        output_path=figures_dir / f"optimal_aggressive_top{top_n}.png",
        color="firebrick",
    )

    markdown_path = None
    if write_markdown:
        markdown_path = write_markdown_report(
            output_path=output_dir / "optimal_portfolio_composition.md",
            gmv_df=gmv_df,
            aggressive_df=aggressive_df,
            gmv_figure=gmv_figure,
            aggressive_figure=aggressive_figure,
            top_n=top_n,
        )
    return markdown_path, [gmv_figure, aggressive_figure]


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    generate_optimal_portfolio_report(
        gmv_path=root / "data" / "processed" / "portfolio_weights_static.csv",
        aggressive_path=root / "data" / "processed" / "portfolio_weights_aggressive.csv",
        output_dir=root / "reports" / "report_draft" / "chapter_5",
        top_n=8,
        write_markdown=False,
    )


if __name__ == "__main__":
    main()
