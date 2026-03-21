#!/usr/bin/env python3
"""食事PFC/カロリー計算エンジン

ベースラインメニュー(config/menu_and_nutrition.json)をもとに、
除外・追加・数量変更を反映した1日の摂取量を正確に計算する。

使用例:
  # ベースラインそのまま
  python3 scripts/calc.py

  # 除外指定（meal:name 形式）
  python3 scripts/calc.py --exclude "夜:納豆"

  # ID指定で除外（間食プロテイン1回分だけ除外）
  python3 scripts/calc.py --exclude-id "間食3_プロテイン"

  # 追加指定 (meal:名前,P,F,C,kcal)
  python3 scripts/calc.py --add "間食:プロテインバー,15,5,10,145"

  # 数量変更（ささみを2.0単位に変更）
  python3 scripts/calc.py --qty "夜_ささみ=2.0"

  # 全項目表示
  python3 scripts/calc.py --detail

  # JSON出力
  python3 scripts/calc.py --json
"""

import json
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MENUS_DIR = PROJECT_ROOT / "config" / "menus"
ACTIVE_MENU_PATH = PROJECT_ROOT / "config" / "active_menu.json"

NUTRIENTS = ["calories", "protein", "fat", "carbs"]


def get_active_menu_name() -> str:
    """active_menu.json から現在有効なメニュー名を取得"""
    with open(ACTIVE_MENU_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["active"]


def list_menus() -> list[str]:
    """利用可能なメニュー一覧を返す"""
    return [p.stem for p in sorted(MENUS_DIR.glob("*.json"))]


def load_menu(menu_name: str | None = None) -> dict:
    """メニューを読み込む。未指定時はactive_menuを使用。"""
    if menu_name is None:
        menu_name = get_active_menu_name()
    menu_path = MENUS_DIR / f"{menu_name}.json"
    if not menu_path.exists():
        available = ", ".join(list_menus())
        raise FileNotFoundError(
            f"メニュー '{menu_name}' が見つかりません。利用可能: {available}"
        )
    with open(menu_path, "r", encoding="utf-8") as f:
        return json.load(f)


def item_total(item: dict) -> dict:
    """per_unit × quantity で合計を計算"""
    qty = item.get("quantity", 1.0)
    pu = item["per_unit"]
    return {k: round(pu[k] * qty, 1) for k in NUTRIENTS}


def calculate_daily(
    exclude: list[str] | None = None,
    exclude_ids: list[str] | None = None,
    add: list[dict] | None = None,
    qty_overrides: dict[str, float] | None = None,
    menu_name: str | None = None,
) -> dict:
    """1日の摂取量を計算する。

    Args:
        exclude: 除外する項目 ["meal:name", ...] — 同名の全アイテムを除外
        exclude_ids: IDで除外 ["間食3_プロテイン", ...]
        add: 追加する項目 [{"name": str, "meal": str, "protein": float, ...}, ...]
        qty_overrides: 数量変更 {"item_id": new_qty, ...}

    Returns:
        {"total": {calories, protein, fat, carbs},
         "by_meal": {meal: {items: [...], subtotal: {...}}},
         "vs_target": {各項目の差分},
         "excluded": [...],
         "items_detail": [...]}
    """
    menu = load_menu(menu_name)
    exclude = exclude or []
    exclude_ids = set(exclude_ids or [])
    add = add or []
    qty_overrides = qty_overrides or {}

    # meal:name の除外セット
    exclude_set = {e.strip() for e in exclude}

    totals = {k: 0 for k in NUTRIENTS}
    by_meal: dict[str, dict] = {}
    excluded_items = []
    items_detail = []

    for item in menu.get("items", []):
        item_id = item["id"]
        meal = item["meal"]
        name = item["name"]
        key = f"{meal}:{name}"

        # 除外チェック
        if key in exclude_set or item_id in exclude_ids:
            excluded_items.append({"id": item_id, "meal": meal, "name": name})
            continue

        # 数量オーバーライド
        working_item = dict(item)
        if item_id in qty_overrides:
            working_item["quantity"] = qty_overrides[item_id]

        # 合計計算
        t = item_total(working_item)

        detail = {
            "id": item_id,
            "meal": meal,
            "name": name,
            "unit": working_item.get("unit", ""),
            "quantity": working_item.get("quantity", 1.0),
            **t,
        }
        items_detail.append(detail)

        # meal別集計
        if meal not in by_meal:
            by_meal[meal] = {
                "items": [],
                "subtotal": {k: 0 for k in NUTRIENTS},
            }
        by_meal[meal]["items"].append(detail)
        for k in NUTRIENTS:
            by_meal[meal]["subtotal"][k] = round(by_meal[meal]["subtotal"][k] + t[k], 1)
            totals[k] = round(totals[k] + t[k], 1)

    # 追加アイテム
    for item in add:
        meal = item.get("meal", "間食")
        t = {k: item.get(k, 0) for k in NUTRIENTS}
        detail = {
            "id": f"add_{meal}_{item['name']}",
            "meal": meal,
            "name": item["name"],
            "unit": item.get("unit", ""),
            "quantity": 1.0,
            "added": True,
            **t,
        }
        items_detail.append(detail)

        if meal not in by_meal:
            by_meal[meal] = {
                "items": [],
                "subtotal": {k: 0 for k in NUTRIENTS},
            }
        by_meal[meal]["items"].append(detail)
        for k in NUTRIENTS:
            by_meal[meal]["subtotal"][k] = round(by_meal[meal]["subtotal"][k] + t[k], 1)
            totals[k] = round(totals[k] + t[k], 1)

    # ターゲットとの差分
    target = menu.get("daily_target", {})
    vs_target = {}
    for k in NUTRIENTS:
        target_key = f"{k}_g" if k != "calories" else k
        vs_target[k] = round(totals[k] - target.get(target_key, 0), 1)

    return {
        "total": totals,
        "by_meal": by_meal,
        "vs_target": vs_target,
        "target": target,
        "excluded": excluded_items,
        "items_detail": items_detail,
    }


def parse_add_arg(arg: str) -> dict:
    """'meal:名前,P,F,C,kcal' 形式をパース"""
    parts = arg.split(",")
    meal_item = parts[0].split(":")
    meal = meal_item[0] if len(meal_item) > 1 else "間食"
    name = meal_item[-1]
    return {
        "meal": meal,
        "name": name,
        "protein": float(parts[1]),
        "fat": float(parts[2]),
        "carbs": float(parts[3]),
        "calories": float(parts[4]) if len(parts) > 4 else 0,
    }


def parse_qty_arg(arg: str) -> tuple[str, float]:
    """'item_id=qty' 形式をパース"""
    item_id, qty = arg.split("=")
    return item_id.strip(), float(qty.strip())


def format_detail(result: dict) -> str:
    """全項目を含む詳細レポート"""
    lines = []
    lines.append("=" * 70)
    lines.append("  日次栄養サマリー（詳細）")
    lines.append("=" * 70)

    meal_order = ["朝", "昼", "夜", "間食"]
    by_meal = result["by_meal"]

    for meal in meal_order:
        if meal not in by_meal:
            continue
        data = by_meal[meal]
        lines.append(f"\n  【{meal}】")
        for item in data["items"]:
            qty_str = f"×{item['quantity']}" if item["quantity"] != 1.0 else ""
            added = " [追加]" if item.get("added") else ""
            lines.append(
                f"    {item['name']:20s} {qty_str:>5s}  "
                f"{item['calories']:>6.1f}kcal  "
                f"P:{item['protein']:>5.1f}  F:{item['fat']:>5.1f}  C:{item['carbs']:>5.1f}"
                f"{added}"
            )
        st = data["subtotal"]
        lines.append(
            f"    {'小計':20s}       "
            f"{st['calories']:>6.1f}kcal  "
            f"P:{st['protein']:>5.1f}  F:{st['fat']:>5.1f}  C:{st['carbs']:>5.1f}"
        )

    if result["excluded"]:
        lines.append(f"\n  【除外】")
        for ex in result["excluded"]:
            lines.append(f"    {ex['meal']}:{ex['name']} ({ex['id']})")

    t = result["total"]
    tgt = result["target"]
    diff = result["vs_target"]
    lines.append(f"\n{'=' * 70}")
    lines.append(f"  {'合計':10s}  {t['calories']:>7.1f} kcal  (目標: {tgt.get('calories', '?'):>5} / 差: {diff['calories']:+.1f})")
    lines.append(f"  {'タンパク質':10s}  {t['protein']:>7.1f} g     (目標: {tgt.get('protein_g', '?'):>5} / 差: {diff['protein']:+.1f})")
    lines.append(f"  {'脂質':10s}  {t['fat']:>7.1f} g     (目標: {tgt.get('fat_g', '?'):>5} / 差: {diff['fat']:+.1f})")
    lines.append(f"  {'炭水化物':10s}  {t['carbs']:>7.1f} g     (目標: {tgt.get('carbs_g', '?'):>5} / 差: {diff['carbs']:+.1f})")
    lines.append("=" * 70)
    return "\n".join(lines)


def format_summary(result: dict) -> str:
    """サマリーのみのレポート"""
    t = result["total"]
    tgt = result["target"]
    diff = result["vs_target"]
    lines = []
    lines.append("=" * 50)
    lines.append("  日次栄養サマリー")
    lines.append("=" * 50)
    lines.append(f"  カロリー:   {t['calories']:>7.1f} kcal  (目標: {tgt.get('calories', '?')} / 差: {diff['calories']:+.1f})")
    lines.append(f"  タンパク質: {t['protein']:>7.1f} g     (目標: {tgt.get('protein_g', '?')} / 差: {diff['protein']:+.1f})")
    lines.append(f"  脂質:       {t['fat']:>7.1f} g     (目標: {tgt.get('fat_g', '?')} / 差: {diff['fat']:+.1f})")
    lines.append(f"  炭水化物:   {t['carbs']:>7.1f} g     (目標: {tgt.get('carbs_g', '?')} / 差: {diff['carbs']:+.1f})")

    if result["excluded"]:
        lines.append(f"\n  除外: {', '.join(f'{e['meal']}:{e['name']}' for e in result['excluded'])}")

    lines.append("=" * 50)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="食事PFC計算")
    parser.add_argument("--menu", default=None, help="メニュー名（エイリアス）")
    parser.add_argument("--list", action="store_true", dest="list_menus", help="利用可能なメニュー一覧")
    parser.add_argument("--exclude", nargs="*", default=[], help="除外項目 (meal:name)")
    parser.add_argument("--exclude-id", nargs="*", default=[], help="IDで除外")
    parser.add_argument("--add", nargs="*", default=[], help="追加項目 (meal:名前,P,F,C,kcal)")
    parser.add_argument("--qty", nargs="*", default=[], help="数量変更 (item_id=qty)")
    parser.add_argument("--detail", action="store_true", help="全項目表示")
    parser.add_argument("--json", action="store_true", help="JSON形式で出力")
    args = parser.parse_args()

    if args.list_menus:
        active = get_active_menu_name()
        for name in list_menus():
            marker = " ← active" if name == active else ""
            print(f"  {name}{marker}")
        return

    add_items = [parse_add_arg(a) for a in args.add]
    qty_overrides = dict(parse_qty_arg(q) for q in args.qty)

    result = calculate_daily(
        exclude=args.exclude,
        exclude_ids=args.exclude_id,
        add=add_items,
        qty_overrides=qty_overrides,
        menu_name=args.menu,
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.detail:
        print(format_detail(result))
    else:
        print(format_summary(result))


if __name__ == "__main__":
    main()
