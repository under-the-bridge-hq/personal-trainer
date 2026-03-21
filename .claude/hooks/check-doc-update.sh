#!/bin/bash
# ドキュメント変更検知hook
# ファイル編集時に関連ドキュメントの更新を促す
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# プロジェクトルートからの相対パスに変換
REL_PATH="${FILE_PATH#$CLAUDE_PROJECT_DIR/}"

case "$REL_PATH" in
  # --- ドキュメント ---
  CLAUDE.md)
    echo "📝 CLAUDE.md が変更されました。以下の確認を推奨します："
    echo "  - docs/system_prompt.md のフェーズ記述との整合性"
    echo "  - README.md のディレクトリ構造・使い方セクション"
    ;;
  docs/system_prompt.md)
    echo "📝 トレーナー人格定義が変更されました。以下の確認を推奨します："
    echo "  - config/phase.json のフェーズ定義との整合性"
    echo "  - CLAUDE.md の日次ワークフローセクション"
    ;;
  README.md)
    echo "📝 README.md が変更されました。以下の確認を推奨します："
    echo "  - CLAUDE.md のリポジトリ構造セクション"
    echo "  - 各ディレクトリの README.md"
    ;;

  # --- 設定ファイル ---
  config/phase.json)
    echo "📝 フェーズ設定が変更されました。以下の確認を推奨します："
    echo "  - docs/system_prompt.md のフェーズ記述"
    echo "  - config/active_menu.json が正しいメニューを指しているか"
    echo "  - scripts/trend.py のアラート条件"
    ;;
  config/active_menu.json)
    echo "📝 アクティブメニューが変更されました。以下の確認を推奨します："
    echo "  - config/phase.json の現在フェーズとの整合性"
    ;;
  config/menus/*.json)
    echo "📝 メニュー定義が変更されました。以下の確認を推奨します："
    echo "  - python3 scripts/calc.py --detail で計算結果を検証"
    echo "  - daily_target と items の合計値の整合性"
    ;;
  config/profile.json)
    echo "📝 クライアントプロファイルが変更されました。以下の確認を推奨します："
    echo "  - config/phase.json のTDEE・カロリー設定との整合性"
    ;;

  # --- スクリプト ---
  scripts/calc.py)
    echo "📝 計算エンジンが変更されました。以下の確認を推奨します："
    echo "  - python3 scripts/calc.py --detail で全メニューの計算結果を検証"
    echo "  - scripts/README.md の使用例"
    ;;
  scripts/trend.py)
    echo "📝 トレンド分析が変更されました。以下の確認を推奨します："
    echo "  - python3 scripts/trend.py --days 7 で動作確認"
    echo "  - config/phase.json のモニタリング設定との整合性"
    ;;
  scripts/append_body_data.py)
    echo "📝 データ追記スクリプトが変更されました。以下の確認を推奨します："
    echo "  - data/README.md のCSVフォーマット定義"
    echo "  - CLAUDE.md の日次ワークフロー"
    ;;

  # --- データ ---
  data/body/*.csv)
    echo "📝 体組成データが変更されました。以下の確認を推奨します："
    echo "  - python3 scripts/trend.py --days 7 でトレンド確認"
    ;;
esac

exit 0
