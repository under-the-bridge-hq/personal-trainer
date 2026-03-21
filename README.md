# personal-trainer

GLP-1受容体作動薬（マンジャロ）による減量治療から筋トレによるボディメイクまでを一貫してサポートする、Claude Code駆動のパーソナルトレーナーシステム。

## コンセプト

- 体組成計のスクリーンショットを送るだけで、データ記録・トレンド分析・栄養アドバイスを自動化
- データはCSV/JSONでgit管理し、長期トレンドの追跡と再現性を確保
- 栄養計算はPythonスクリプトで正確に実行（LLMの暗算に頼らない）

## 使い方

### 日次の体組成記録

```bash
# 体組成計のスクリーンショットを送信（--resumeで同一セッション維持）
claude -p "体組成データを記録して。添付ファイル: /path/to/image.png" --resume
```

### 栄養計算

```bash
# 現在のメニューで計算
python3 scripts/calc.py --detail

# メニュー一覧
python3 scripts/calc.py --list

# 除外・追加
python3 scripts/calc.py --exclude "夜:納豆" --add "間食:プロテインバー,15,5,10,145"
```

### トレンド分析

```bash
python3 scripts/trend.py              # 直近7日間
python3 scripts/trend.py --days 14    # 直近14日間
python3 scripts/trend.py --all        # 全期間
python3 scripts/trend.py --json       # JSON出力
```

## ディレクトリ構造

```
config/              # 設定ファイル群
  ├── profile.json       # クライアントプロファイル
  ├── phase.json         # フェーズ計画・移行トリガー
  ├── active_menu.json   # 現在有効なメニューへのポインタ
  └── menus/             # メニュー定義（エイリアス管理）
data/                # 蓄積データ
  ├── body/              # 体組成CSV（月別）
  └── meals/             # 食事変更ログ（日別）
docs/                # トレーナー人格定義
scripts/             # 計算・分析スクリプト
reports/             # 週間レポート等
```

各ディレクトリの詳細は配下の `README.md` を参照。
