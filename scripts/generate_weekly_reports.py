#!/usr/bin/env python3
"""過去の体組成データから週間レポートを一括生成する。

週の区切りは土曜日始まり（phase.json の weekly_review_day: saturday に準拠）。
"""

import csv
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "body"
REPORT_DIR = BASE_DIR / "reports" / "weekly"
PROFILE_PATH = BASE_DIR / "config" / "profile.json"
PHASE_PATH = BASE_DIR / "config" / "phase.json"

LBM_DANGER_LINE = 70.0
FAT_LOSS_RATIO_TARGET = 0.75


def load_all_data():
    """全CSVを読み込み、日付順にソートして返す。"""
    rows = []
    for csv_file in sorted(DATA_DIR.glob("*.csv")):
        with open(csv_file) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row["date"]:
                    continue
                row["date"] = datetime.strptime(row["date"], "%Y-%m-%d").date()
                for key in ["weight", "bf_pct", "fat_mass", "lbm", "water_pct", "bmi"]:
                    val = row.get(key, "")
                    row[key] = float(val) if val else None
                row["note"] = row.get("note", "").strip()
                rows.append(row)
    rows.sort(key=lambda r: r["date"])
    return rows


def load_baseline():
    with open(PROFILE_PATH) as f:
        profile = json.load(f)
    b = profile["baseline"]
    return {
        "date": b["date"],
        "weight": b["weight_kg"],
        "bf_pct": b["bf_pct"],
        "fat_mass": b["fat_mass_kg"],
        "lbm": b["lbm_kg"],
    }


def get_saturday(d):
    """与えられた日付が属する週の土曜日（週の開始日）を返す。"""
    # weekday(): Mon=0 ... Sun=6, Sat=5
    days_since_sat = (d.weekday() - 5) % 7
    return d - timedelta(days=days_since_sat)


def group_by_week(rows):
    """土曜始まりの週ごとにグループ化。"""
    weeks = {}
    for row in rows:
        sat = get_saturday(row["date"])
        weeks.setdefault(sat, []).append(row)
    return dict(sorted(weeks.items()))


def safe_avg(values):
    valid = [v for v in values if v is not None]
    return sum(valid) / len(valid) if valid else None


def fmt(val, decimals=2):
    if val is None:
        return "-"
    return f"{val:.{decimals}f}"


def sign(val):
    if val is None:
        return "-"
    return f"+{val:.2f}" if val >= 0 else f"{val:.2f}"


def evaluate_week(weight_delta, fat_delta, lbm_delta, lbm_avg):
    """週の一言評価を生成。"""
    parts = []

    if weight_delta is not None and fat_delta is not None and weight_delta < 0:
        total_loss = abs(weight_delta)
        fat_loss = abs(fat_delta) if fat_delta < 0 else 0
        ratio = fat_loss / total_loss if total_loss > 0 else 0
        if ratio >= FAT_LOSS_RATIO_TARGET:
            parts.append(f"脂肪減少比率 {ratio:.0%} — 目標達成")
        else:
            parts.append(f"脂肪減少比率 {ratio:.0%} — 目標75%未達")

    if lbm_delta is not None:
        if lbm_delta >= 0:
            parts.append("LBM維持・増加")
        elif lbm_delta > -0.3:
            parts.append("LBM微減（許容範囲）")
        else:
            parts.append(f"LBM減少 {lbm_delta:.2f}kg — 要注意")

    if lbm_avg is not None and lbm_avg < LBM_DANGER_LINE:
        parts.append(f"⚠ LBM {fmt(lbm_avg)}kg — 危険ライン({LBM_DANGER_LINE}kg)割れ")

    if not parts:
        parts.append("データ不足のため評価保留")

    return " / ".join(parts)


def generate_report(week_start, week_data, prev_week_data, baseline):
    """1週間分のレポートmarkdownを生成。"""
    week_end = week_start + timedelta(days=6)
    lines = []

    # ヘッダー
    lines.append(f"# Weekly Report: {week_start} 〜 {week_end}")
    lines.append("")

    # --- 数値取得 ---
    weights = [r["weight"] for r in week_data]
    bf_pcts = [r["bf_pct"] for r in week_data]
    fat_masses = [r["fat_mass"] for r in week_data]
    lbms = [r["lbm"] for r in week_data]
    water_pcts = [r["water_pct"] for r in week_data]
    bmis = [r["bmi"] for r in week_data]

    avg_w = safe_avg(weights)
    avg_bf = safe_avg(bf_pcts)
    avg_fm = safe_avg(fat_masses)
    avg_lbm = safe_avg(lbms)
    avg_wp = safe_avg(water_pcts)
    avg_bmi = safe_avg(bmis)

    first = week_data[0]
    last = week_data[-1]

    # 前週平均
    prev_avg_w = safe_avg([r["weight"] for r in prev_week_data]) if prev_week_data else None
    prev_avg_bf = safe_avg([r["bf_pct"] for r in prev_week_data]) if prev_week_data else None
    prev_avg_fm = safe_avg([r["fat_mass"] for r in prev_week_data]) if prev_week_data else None
    prev_avg_lbm = safe_avg([r["lbm"] for r in prev_week_data]) if prev_week_data else None

    # 週間変化（週平均の前週比）
    w_delta = avg_w - prev_avg_w if avg_w and prev_avg_w else None
    fm_delta = avg_fm - prev_avg_fm if avg_fm and prev_avg_fm else None
    lbm_delta = avg_lbm - prev_avg_lbm if avg_lbm and prev_avg_lbm else None

    # --- 1. サマリー ---
    evaluation = evaluate_week(w_delta, fm_delta, lbm_delta, avg_lbm)
    lines.append("## 1. サマリー")
    lines.append("")
    lines.append(f"**{evaluation}**")
    lines.append("")

    # --- 2. 数値推移 ---
    lines.append("## 2. 数値推移")
    lines.append("")
    lines.append("| 日付 | 体重 | 体脂肪率 | Fat Mass | LBM | 体水分率 | BMI | 備考 |")
    lines.append("|------|------|----------|----------|-----|----------|-----|------|")
    for r in week_data:
        lines.append(
            f"| {r['date']} "
            f"| {fmt(r['weight'])} "
            f"| {fmt(r['bf_pct'], 1)} "
            f"| {fmt(r['fat_mass'])} "
            f"| {fmt(r['lbm'])} "
            f"| {fmt(r['water_pct'], 1)} "
            f"| {fmt(r['bmi'], 1)} "
            f"| {r['note']} |"
        )
    lines.append("")

    # 週初→週末
    if first["weight"] is not None and last["weight"] is not None:
        lines.append(
            f"**週初→週末**: 体重 {fmt(first['weight'])}→{fmt(last['weight'])} "
            f"({sign(last['weight'] - first['weight'])}), "
            f"LBM {fmt(first['lbm'])}→{fmt(last['lbm'])} "
            f"({sign((last['lbm'] or 0) - (first['lbm'] or 0))})"
        )
        lines.append("")

    # --- 3. 週間トレンド分析 ---
    lines.append("## 3. 週間トレンド分析")
    lines.append("")

    valid_weights = [w for w in weights if w is not None]
    if valid_weights:
        lines.append(f"- **体重**: 週平均 {fmt(avg_w)}, "
                     f"最小 {fmt(min(valid_weights))}, "
                     f"最大 {fmt(max(valid_weights))}, "
                     f"変動幅 {fmt(max(valid_weights) - min(valid_weights))}")
    if avg_lbm is not None:
        lbm_line = f"- **LBM**: 週平均 {fmt(avg_lbm)}"
        if prev_avg_lbm:
            lbm_line += f" (前週比 {sign(lbm_delta)})"
        lbm_line += f", 危険ライン({LBM_DANGER_LINE}kg)まで {fmt(avg_lbm - LBM_DANGER_LINE)}"
        lines.append(lbm_line)
    if avg_fm is not None:
        fm_line = f"- **Fat Mass**: 週平均 {fmt(avg_fm)}"
        if prev_avg_fm:
            fm_line += f" (前週比 {sign(fm_delta)})"
        lines.append(fm_line)
    if w_delta is not None and w_delta < 0 and fm_delta is not None:
        total_loss = abs(w_delta)
        fat_loss = abs(fm_delta) if fm_delta < 0 else 0
        ratio = fat_loss / total_loss if total_loss > 0 else 0
        mark = "✓" if ratio >= FAT_LOSS_RATIO_TARGET else "✗"
        lines.append(f"- **減量の質**: 体重減 {fmt(abs(w_delta))} のうち脂肪 {fmt(fat_loss)} "
                     f"({ratio:.0%}) {mark} 目標75%")
    lines.append("")

    # --- 4. ノイズ・イベント ---
    events = [r for r in week_data if r["note"]]
    lines.append("## 4. ノイズ・イベント")
    lines.append("")
    if events:
        for r in events:
            lines.append(f"- **{r['date']}**: {r['note']}")
    else:
        lines.append("- 特になし")
    lines.append("")

    # --- 5. フェーズ進捗 ---
    lines.append("## 5. フェーズ進捗")
    lines.append("")
    if last["weight"] is not None:
        cum_w = last["weight"] - baseline["weight"]
        cum_fm = (last["fat_mass"] or 0) - baseline["fat_mass"]
        cum_lbm = (last["lbm"] or 0) - baseline["lbm"]
        lines.append(f"- **開始時({baseline['date']})からの累計変化**:")
        lines.append(f"  - 体重: {sign(cum_w)} ({baseline['weight']}→{fmt(last['weight'])})")
        lines.append(f"  - Fat Mass: {sign(cum_fm)} ({baseline['fat_mass']}→{fmt(last['fat_mass'])})")
        lines.append(f"  - LBM: {sign(cum_lbm)} ({baseline['lbm']}→{fmt(last['lbm'])})")
        if cum_w < 0:
            total_loss = abs(cum_w)
            fat_loss = abs(cum_fm) if cum_fm < 0 else 0
            ratio = fat_loss / total_loss if total_loss > 0 else 0
            lines.append(f"  - 累計減量の質: 脂肪比率 {ratio:.0%} (目標75%)")
    lines.append("")

    # --- 6. 来週の注目ポイント ---
    lines.append("## 6. 来週の注目ポイント")
    lines.append("")
    points = []
    if lbm_delta is not None and lbm_delta < -0.3:
        points.append("- LBM減少傾向 — タンパク質摂取量の確認と増量を検討")
    if avg_lbm and avg_lbm - LBM_DANGER_LINE < 3.0:
        points.append(f"- LBMが危険ラインに接近中（残り{fmt(avg_lbm - LBM_DANGER_LINE)}kg）— 慎重にモニタリング")
    if w_delta is not None and abs(w_delta) < 0.1:
        points.append("- 体重停滞気味 — 食事内容と水分摂取の見直し")
    if not points:
        points.append("- 現在のペースを維持")
    for p in points:
        lines.append(p)
    lines.append("")

    return "\n".join(lines)


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    rows = load_all_data()
    baseline = load_baseline()
    weeks = group_by_week(rows)
    week_keys = list(weeks.keys())

    generated = []
    for i, sat in enumerate(week_keys):
        week_data = weeks[sat]
        prev_data = weeks[week_keys[i - 1]] if i > 0 else None
        week_end = sat + timedelta(days=6)

        report = generate_report(sat, week_data, prev_data, baseline)
        filename = f"{sat}_to_{week_end}.md"
        filepath = REPORT_DIR / filename
        with open(filepath, "w") as f:
            f.write(report)
        generated.append(filename)

    print(f"{len(generated)} 件の週間レポートを生成しました:")
    for name in generated:
        print(f"  reports/weekly/{name}")


if __name__ == "__main__":
    main()
