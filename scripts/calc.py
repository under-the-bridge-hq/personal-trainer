#!/usr/bin/env python3
"""食事PFC/カロリー計算エンジン

ベースラインメニュー(config/menu_and_nutrition.json)をもとに、
除外・追加項目を反映した1日の摂取量を計算する。

使用例:
  # ベースラインそのまま
  python3 scripts/calc.py

  # 除外指定
  python3 scripts/calc.py --exclude "夜:納豆"

  # 追加指定 (名前,P,F,C,kcal)
  python3 scripts/calc.py --add "間食:プロテインバー,15,5,10,145"

  # Pythonから呼び出し
  from scripts.calc import calculate_daily
  result = calculate_daily(exclude=["夜:納豆"], add=[...])
"""

import json
import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MENU_PATH = PROJECT_ROOT / "config" / "menu_and_nutrition.json"
PHASE_PATH = PROJECT_ROOT / "config" / "phase.json"


def load_menu() -> dict:
    with open(MENU_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_phase() -> dict:
    with open(PHASE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def calculate_daily(
    exclude: list[str] | None = None,
    add: list[dict] | None = None,
) -> dict:
    """1日の摂取量を計算する。

    Args:
        exclude: 除外する項目 ["食事名:アイテム名", ...]
        add: 追加する項目 [{"name": str, "meal": str, "protein": float,
             "fat": float, "carbs": float, "calories": float}, ...]

    Returns:
        {"total": {calories, protein, fat, carbs},
         "by_meal": {...},
         "vs_target": {各項目の差分}}
    """
    menu = load_menu()
    phase = load_phase()

    exclude = exclude or []
    add = add or []

    # 除外セットを作成
    exclude_set = set()
    for item in exclude:
        exclude_set.add(item.strip())

    totals = {"calories": 0, "protein": 0, "fat": 0, "carbs": 0}
    by_meal = {}

    # ベースラインメニューから計算
    for meal_name, items in menu.get("meals", {}).items():
        meal_totals = {"calories": 0, "protein": 0, "fat": 0, "carbs": 0}
        meal_items = []

        for item in items:
            key = f"{meal_name}:{item['name']}"
            if key in exclude_set:
                continue
            meal_totals["calories"] += item.get("calories", 0)
            meal_totals["protein"] += item.get("protein", 0)
            meal_totals["fat"] += item.get("fat", 0)
            meal_totals["carbs"] += item.get("carbs", 0)
            meal_items.append(item)

        by_meal[meal_name] = {
            "items": meal_items,
            "subtotal": meal_totals,
        }

        for k in totals:
            totals[k] += meal_totals[k]

    # 追加アイテムを反映
    for item in add:
        meal_name = item.get("meal", "snacks")
        if meal_name not in by_meal:
            by_meal[meal_name] = {
                "items": [],
                "subtotal": {"calories": 0, "protein": 0, "fat": 0, "carbs": 0},
            }
        by_meal[meal_name]["items"].append(item)
        for k in ["calories", "protein", "fat", "carbs"]:
            by_meal[meal_name]["subtotal"][k] += item.get(k, 0)
            totals[k] += item.get(k, 0)

    # ターゲットとの差分
    target = menu.get("daily_target", {})
    vs_target = {}
    for k in ["calories", "protein", "fat", "carbs"]:
        target_val = target.get(f"{k}_g" if k != "calories" else k, 0)
        vs_target[k] = round(totals[k] - target_val, 1)

    return {
        "total": {k: round(v, 1) for k, v in totals.items()},
        "by_meal": by_meal,
        "vs_target": vs_target,
        "target": target,
    }


def parse_add_arg(arg: str) -> dict:
    """'食事:名前,P,F,C,kcal' 形式をパース"""
    parts = arg.split(",")
    meal_item = parts[0].split(":")
    meal = meal_item[0] if len(meal_item) > 1 else "snacks"
    name = meal_item[-1]
    return {
        "meal": meal,
        "name": name,
        "protein": float(parts[1]),
        "fat": float(parts[2]),
        "carbs": float(parts[3]),
        "calories": float(parts[4]) if len(parts) > 4 else 0,
    }


def main():
    parser = argparse.ArgumentParser(description="食事PFC計算")
    parser.add_argument("--exclude", nargs="*", default=[], help="除外項目 (食事名:アイテム名)")
    parser.add_argument("--add", nargs="*", default=[], help="追加項目 (食事:名前,P,F,C,kcal)")
    parser.add_argument("--json", action="store_true", help="JSON形式で出力")
    args = parser.parse_args()

    add_items = [parse_add_arg(a) for a in args.add]
    result = calculate_daily(exclude=args.exclude, add=add_items)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        t = result["total"]
        tgt = result["target"]
        diff = result["vs_target"]
        print("=" * 50)
        print("  日次栄養サマリー")
        print("=" * 50)
        print(f"  カロリー:  {t['calories']:>7.1f} kcal  (目標: {tgt.get('calories', '?')} / 差: {diff['calories']:+.1f})")
        print(f"  タンパク質: {t['protein']:>7.1f} g     (目標: {tgt.get('protein_g', '?')} / 差: {diff['protein']:+.1f})")
        print(f"  脂質:      {t['fat']:>7.1f} g     (目標: {tgt.get('fat_g', '?')} / 差: {diff['fat']:+.1f})")
        print(f"  炭水化物:  {t['carbs']:>7.1f} g     (目標: {tgt.get('carbs_g', '?')} / 差: {diff['carbs']:+.1f})")
        print("=" * 50)


if __name__ == "__main__":
    main()
