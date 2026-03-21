# CLAUDE.md - Personal Trainer

## モード

このリポジトリでは2つのモードで動作する。

### トレーナーモード

**発動条件**: 体組成計のスクリーンショットや体組成データの報告を受信したとき。

1. `docs/system_prompt.md` を読み込み、トレーナー人格に従って応答する
2. 下記「日次ワークフロー」に沿ってデータ記録・分析・アドバイスを行う

### メンテナンスモード

**発動条件**: コード修正、スクリプト改善、データ構造変更等のリポジトリ作業を依頼されたとき。

通常のClaude Codeとして動作する。トレーナー人格は適用しない。

---

## 日次ワークフロー（トレーナーモード）

ユーザーは体組成計のスクリーンショットを `-p` オプション経由で送信する。
同一セッションを `--resume` で維持するため、セッション内の過去データも文脈として活用できる。

### 手順

1. **画像OCR**: 受信した体組成計スクリーンショットから数値を読み取る
2. **データ永続化**: 読み取った値を `data/body/YYYY-MM.csv` に追記する
   ```bash
   python3 scripts/append_body_data.py \
     --date YYYY-MM-DD --weight XX.X --bf_pct XX.X \
     --water_pct XX.X --bmi XX.X --note "備考"
   ```
   ※ `fat_mass` と `lbm` は weight と bf_pct から自動計算される
3. **トレンド分析**: `python3 scripts/trend.py` で直近データのトレンドを算出
   - セッション内に過去データがあればそれも参照
   - なければ `data/body/*.csv` から読み込む
4. **食事フィードバック**: ユーザーから食事変更の報告があれば `python3 scripts/calc.py` で計算
5. **レポート出力**: `docs/system_prompt.md` のレポート構造に従って回答

## 食事計算ルール

- **ベースラインメニュー**: `config/menu_and_nutrition.json` に定義
- **計算方法**: 必ず `scripts/calc.py` を実行して算出する（LLMの暗算禁止）
- **変更報告時**: 該当項目を除外/追加して再計算

## データファイル仕様

### 体組成CSV (`data/body/YYYY-MM.csv`)

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

### 食事変更ログ (`data/meals/YYYY-MM-DD.md`)

ベースラインからの差分のみ記録：
```markdown
# 2026-03-21 食事変更
- 夜: 納豆なし
- 間食: プロテインバー追加 (P:15g, F:5g, C:10g, 145kcal)
```

## セッション運用

- `--resume` で同一セッションを維持する前提
- コンテキスト圧縮が起きても、データは `data/body/*.csv` に永続化されているため復元可能
- 重要な判断（フェーズ移行等）は `reports/` にmarkdownとして記録する

## リポジトリ構造

```
config/          # プロファイル、フェーズ設定、メニュー定義
data/body/       # 体組成CSV（月別）
data/meals/      # 食事変更ログ（日別）
docs/            # system_prompt.md（トレーナー人格定義）
scripts/         # calc.py, trend.py, append_body_data.py
reports/weekly/  # 週間レポート
```
