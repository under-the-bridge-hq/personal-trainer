#!/usr/bin/env python3
"""体組成データをCSVに追記する

使用例:
  python3 scripts/append_body_data.py \
    --date 2026-03-19 \
    --weight 96.75 \
    --bf_pct 25.0 \
    --fat_mass 24.19 \
    --lbm 72.50 \
    --water_pct 48.6 \
    --bmi 29.9 \
    --note "ベースライン復帰2日目"

  # fat_mass/lbm は weight と bf_pct から自動計算も可能
  python3 scripts/append_body_data.py \
    --date 2026-03-19 --weight 96.75 --bf_pct 25.0 --water_pct 48.6 --bmi 29.9
"""

import argparse
import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "body"

HEADER = ["date", "weight", "bf_pct", "fat_mass", "lbm", "water_pct", "bmi", "note"]


def append_data(
    date: str,
    weight: float,
    bf_pct: float,
    fat_mass: float | None = None,
    lbm: float | None = None,
    water_pct: float | None = None,
    bmi: float | None = None,
    note: str = "",
) -> Path:
    """CSVにデータを追記する。月別ファイルに自動振り分け。"""
    # fat_mass / lbm を自動計算（未指定時）
    if fat_mass is None:
        fat_mass = round(weight * bf_pct / 100, 2)
    if lbm is None:
        lbm = round(weight - fat_mass, 2)

    month = date[:7]  # YYYY-MM
    csv_path = DATA_DIR / f"{month}.csv"

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 重複チェック
    if csv_path.exists():
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["date"] == date:
                    print(f"警告: {date} のデータは既に存在します。上書きはスキップします。", file=sys.stderr)
                    return csv_path

    # ヘッダー書き込み（新規ファイルの場合）
    write_header = not csv_path.exists()

    with open(csv_path, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADER)
        if write_header:
            writer.writeheader()
        writer.writerow({
            "date": date,
            "weight": weight,
            "bf_pct": bf_pct,
            "fat_mass": fat_mass,
            "lbm": lbm,
            "water_pct": water_pct if water_pct is not None else "",
            "bmi": bmi if bmi is not None else "",
            "note": note,
        })

    print(f"追記完了: {csv_path} ({date})")
    return csv_path


def main():
    parser = argparse.ArgumentParser(description="体組成データ追記")
    parser.add_argument("--date", required=True, help="日付 (YYYY-MM-DD)")
    parser.add_argument("--weight", required=True, type=float, help="体重 (kg)")
    parser.add_argument("--bf_pct", required=True, type=float, help="体脂肪率 (%)")
    parser.add_argument("--fat_mass", type=float, help="脂肪量 (kg) ※未指定時は自動計算")
    parser.add_argument("--lbm", type=float, help="除脂肪体重 (kg) ※未指定時は自動計算")
    parser.add_argument("--water_pct", type=float, help="体水分率 (%)")
    parser.add_argument("--bmi", type=float, help="BMI")
    parser.add_argument("--note", default="", help="備考")
    args = parser.parse_args()

    append_data(
        date=args.date,
        weight=args.weight,
        bf_pct=args.bf_pct,
        fat_mass=args.fat_mass,
        lbm=args.lbm,
        water_pct=args.water_pct,
        bmi=args.bmi,
        note=args.note,
    )


if __name__ == "__main__":
    main()
