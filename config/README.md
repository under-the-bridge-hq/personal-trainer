# config/

プロジェクトの設定ファイル群。

## ファイル

| ファイル | 用途 |
|----------|------|
| `profile.json` | クライアントプロファイル（身長・年齢・TDEE・ベースラインデータ・投薬情報） |
| `phase.json` | フェーズ計画（現在フェーズ・移行トリガー・モニタリング設定） |
| `active_menu.json` | 現在有効なメニューへのポインタ。`menus/` 内のエイリアスを指定 |

## menus/

食事メニュー定義。`{状況}_{フェーズ}_{カロリー}kcal.json` の命名規則。

各メニューの構造:

```json
{
  "name": "エイリアス名",
  "daily_target": { "calories": N, "protein_g": N, "fat_g": N, "carbs_g": N },
  "items": [
    {
      "id": "meal_アイテム名",
      "meal": "朝|昼|夜|間食",
      "name": "表示名",
      "unit": "1単位の説明",
      "quantity": 1.0,
      "per_unit": { "calories": N, "protein": N, "fat": N, "carbs": N }
    }
  ]
}
```

- `per_unit × quantity` で1日の摂取量を算出
- `scripts/calc.py` がこの構造を読み込んで計算する
- 除外キーは `meal:name`（例: `夜:納豆`）またはID（例: `間食3_プロテイン`）
