# scripts/

計算・分析スクリプト群。Python 3.10+、外部依存なし（標準ライブラリのみ）。

## calc.py

食事PFC/カロリー計算エンジン。`config/menus/` のメニュー定義をもとに正確に計算する。

```bash
python3 scripts/calc.py                              # activeメニューで計算
python3 scripts/calc.py --detail                     # 全項目表示
python3 scripts/calc.py --menu マンジャロ_超減量期_1700kcal  # メニュー指定
python3 scripts/calc.py --list                       # メニュー一覧
python3 scripts/calc.py --exclude "夜:納豆"           # 除外
python3 scripts/calc.py --exclude-id "間食3_プロテイン" # ID指定で除外
python3 scripts/calc.py --add "間食:プロテインバー,15,5,10,145"  # 追加
python3 scripts/calc.py --qty "夜_ささみ=2.0"         # 数量変更
python3 scripts/calc.py --json                       # JSON出力
```

## trend.py

体組成トレンド分析。`data/body/*.csv` からデータを読み込んで分析する。

```bash
python3 scripts/trend.py              # 直近7日間
python3 scripts/trend.py --days 14    # 直近14日間
python3 scripts/trend.py --weekly     # 週間レポート（7日間）
python3 scripts/trend.py --all        # 全期間
python3 scripts/trend.py --json       # JSON出力
```

出力:
- 各指標のトレンド（変化量・日平均変化率）
- 減量の質（脂肪/LBM減少比率）
- アラート（LBM危険ライン、フェーズ移行トリガー）

## append_body_data.py

体組成データをCSVに追記する。月別ファイルに自動振り分け。重複チェックあり。

```bash
python3 scripts/append_body_data.py \
  --date 2026-03-21 --weight 97.20 --bf_pct 26.8 \
  --water_pct 48.3 --bmi 30.0 --note "備考"
```

`fat_mass` と `lbm` は `weight` と `bf_pct` から自動計算される。
