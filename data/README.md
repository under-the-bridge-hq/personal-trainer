# data/

蓄積データ。git管理対象。

## body/

体組成データ。月別CSV（`YYYY-MM.csv`）。

```csv
date,weight,bf_pct,fat_mass,lbm,water_pct,bmi,note
2026-03-21,97.20,26.8,26.05,71.15,48.3,30.0,
```

| カラム | 説明 |
|--------|------|
| `date` | ISO 8601 (YYYY-MM-DD) |
| `weight` | 体重 (kg) |
| `bf_pct` | 体脂肪率 (%) |
| `fat_mass` | 脂肪量 (kg) = weight × bf_pct / 100 |
| `lbm` | 除脂肪体重 (kg) = weight - fat_mass |
| `water_pct` | 体水分率 (%) |
| `bmi` | BMI |
| `note` | 備考（任意） |

追記: `scripts/append_body_data.py` を使用。重複チェックあり。

## meals/

食事変更ログ。日別markdown（`YYYY-MM-DD.md`）。ベースラインメニューからの差分のみ記録。

```markdown
# 2026-03-21 食事変更
- 夜: 納豆なし
- 間食: プロテインバー追加 (P:15g, F:5g, C:10g, 145kcal)
```

## baseline_menu_1700kcal.csv

超減量期メニューの元データ（参照用）。構造化データは `config/menus/` に格納。
