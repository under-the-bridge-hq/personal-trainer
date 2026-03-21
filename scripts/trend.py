#!/usr/bin/env python3
"""体組成トレンド分析

data/body/*.csv からデータを読み込み、トレンドを分析する。

使用例:
  # 直近7日間のトレンド
  python3 scripts/trend.py

  # 直近N日間
  python3 scripts/trend.py --days 14

  # 週間レポート
  python3 scripts/trend.py --weekly

  # JSON出力
  python3 scripts/trend.py --json
"""

import csv
import json
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean, stdev

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "body"
PHASE_PATH = PROJECT_ROOT / "config" / "phase.json"

FIELDS = ["date", "weight", "bf_pct", "fat_mass", "lbm", "water_pct", "bmi", "note"]
NUMERIC_FIELDS = ["weight", "bf_pct", "fat_mass", "lbm", "water_pct", "bmi"]


def load_all_data() -> list[dict]:
    """全CSVファイルからデータを読み込み、日付順にソート"""
    rows = []
    if not DATA_DIR.exists():
        return rows

    for csv_file in sorted(DATA_DIR.glob("*.csv")):
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                for field in NUMERIC_FIELDS:
                    if row.get(field):
                        row[field] = float(row[field])
                    else:
                        row[field] = None
                rows.append(row)

    rows.sort(key=lambda r: r["date"])
    return rows


def filter_recent(data: list[dict], days: int) -> list[dict]:
    """直近N日間のデータをフィルタ"""
    if not data:
        return []
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    return [r for r in data if r["date"] >= cutoff]


def calc_trend(data: list[dict], field: str) -> dict | None:
    """指定フィールドのトレンドを計算"""
    values = [r[field] for r in data if r.get(field) is not None]
    if len(values) < 2:
        return None

    first = values[0]
    last = values[-1]
    change = last - first
    avg = mean(values)
    daily_rate = change / (len(values) - 1) if len(values) > 1 else 0

    result = {
        "first": round(first, 2),
        "last": round(last, 2),
        "change": round(change, 2),
        "avg": round(avg, 2),
        "daily_rate": round(daily_rate, 3),
        "count": len(values),
    }
    if len(values) >= 3:
        result["stdev"] = round(stdev(values), 3)

    return result


def calc_composition_quality(data: list[dict]) -> dict | None:
    """体重減少の質を評価（脂肪/筋肉の減少比率）"""
    valid = [r for r in data if r.get("weight") and r.get("bf_pct") and r.get("lbm")]
    if len(valid) < 2:
        return None

    first, last = valid[0], valid[-1]

    weight_change = last["weight"] - first["weight"]
    fat_first = first.get("fat_mass") or (first["weight"] * first["bf_pct"] / 100)
    fat_last = last.get("fat_mass") or (last["weight"] * last["bf_pct"] / 100)
    fat_change = fat_last - fat_first
    muscle_change = last["lbm"] - first["lbm"]

    fat_ratio = abs(fat_change / weight_change) if weight_change != 0 else 0

    return {
        "weight_change": round(weight_change, 2),
        "fat_change": round(fat_change, 2),
        "muscle_change": round(muscle_change, 2),
        "fat_loss_ratio": round(fat_ratio, 3),
        "quality": "良好" if fat_ratio >= 0.75 else "要注意",
    }


def check_alerts(data: list[dict]) -> list[str]:
    """警告チェック"""
    alerts = []
    if not data:
        return alerts

    with open(PHASE_PATH, "r", encoding="utf-8") as f:
        phase = json.load(f)

    current = phase["phases"][str(phase["current_phase"])]
    danger_line = current.get("monitoring", {}).get("muscle_danger_line_kg", 70.0)

    # 直近のLBMチェック
    recent_muscle = [r["lbm"] for r in data[-3:] if r.get("lbm")]
    if recent_muscle and min(recent_muscle) < danger_line:
        alerts.append(f"⚠️ 筋肉量が危険ライン({danger_line}kg)を下回っています: {min(recent_muscle):.1f}kg")

    if len(recent_muscle) >= 3 and all(
        recent_muscle[i] < recent_muscle[i - 1] for i in range(1, len(recent_muscle))
    ):
        alerts.append("⚠️ 筋肉量が3日連続で減少傾向です。タンパク質摂取を+20g検討してください。")

    # フェーズ移行チェック
    latest = data[-1]
    trigger = current.get("transition_trigger", {})
    if latest.get("weight") and latest["weight"] <= trigger.get("weight_kg", 0):
        alerts.append(f"🎯 体重が{trigger['weight_kg']}kgに到達！フェーズ2移行を検討してください。")
    if latest.get("bf_pct") and latest["bf_pct"] <= trigger.get("bf_pct", 0):
        alerts.append(f"🎯 体脂肪率が{trigger['bf_pct']}%に到達！フェーズ2移行を検討してください。")

    return alerts


def format_report(data: list[dict], days: int) -> str:
    """テキスト形式のトレンドレポート"""
    lines = []
    lines.append(f"{'=' * 55}")
    lines.append(f"  体組成トレンドレポート（直近 {days} 日間 / {len(data)} データポイント）")
    lines.append(f"{'=' * 55}")

    if not data:
        lines.append("  データがありません。")
        return "\n".join(lines)

    field_labels = {
        "weight": ("体重", "kg"),
        "bf_pct": ("体脂肪率", "%"),
        "fat_mass": ("脂肪量", "kg"),
        "lbm": ("LBM", "kg"),
        "water_pct": ("体水分率", "%"),
        "bmi": ("BMI", ""),
    }

    for field, (label, unit) in field_labels.items():
        trend = calc_trend(data, field)
        if trend:
            direction = "↗" if trend["change"] > 0 else "↘" if trend["change"] < 0 else "→"
            lines.append(
                f"  {label:8s}: {trend['last']:>7.2f}{unit} "
                f"({trend['change']:+.2f} {direction} / 日平均: {trend['daily_rate']:+.3f})"
            )

    # 体重減少の質
    quality = calc_composition_quality(data)
    if quality:
        lines.append(f"\n  --- 減量の質 ---")
        lines.append(f"  体重変化: {quality['weight_change']:+.2f}kg")
        lines.append(f"  脂肪変化: {quality['fat_change']:+.2f}kg")
        lines.append(f"  筋肉変化: {quality['muscle_change']:+.2f}kg")
        lines.append(f"  脂肪率:   {quality['fat_loss_ratio']:.1%} → {quality['quality']}")

    # アラート
    alerts = check_alerts(data)
    if alerts:
        lines.append(f"\n  --- アラート ---")
        for alert in alerts:
            lines.append(f"  {alert}")

    lines.append(f"{'=' * 55}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="体組成トレンド分析")
    parser.add_argument("--days", type=int, default=7, help="分析期間（日数）")
    parser.add_argument("--weekly", action="store_true", help="週間レポート")
    parser.add_argument("--json", action="store_true", help="JSON形式で出力")
    parser.add_argument("--all", action="store_true", help="全期間を分析")
    args = parser.parse_args()

    all_data = load_all_data()

    if args.all:
        data = all_data
        days = len(data)
    else:
        days = 7 if args.weekly else args.days
        data = filter_recent(all_data, days)

    if args.json:
        result = {
            "period_days": days,
            "data_points": len(data),
            "trends": {},
            "composition_quality": calc_composition_quality(data),
            "alerts": check_alerts(data),
        }
        for field in NUMERIC_FIELDS:
            trend = calc_trend(data, field)
            if trend:
                result["trends"][field] = trend
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_report(data, days))


if __name__ == "__main__":
    main()
