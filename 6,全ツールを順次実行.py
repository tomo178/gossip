#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
メインスクリプト (main.py)

全ツールを順次実行する自動化スクリプト
"""

import subprocess
import sys


def run_script(script_name, description):
    """スクリプトを実行"""
    print("\n" + "=" * 80)
    print(f"実行: {description}")
    print("=" * 80)
    
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            check=True,
            capture_output=False
        )
        print(f"\n✓ {description} 完了")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n✗ {description} 失敗")
        print(f"エラー: {e}")
        return False


def main():
    print("=" * 80)
    print("炎上監視・自動投稿システム 起動")
    print("=" * 80)
    
    # ツール実行順序
    tools = [
        ("monitor_rss.py", "ツール1: RSS監視 - 芸能人ゴシップ検出"),
        ("download_images.py", "ツール2: 画像ダウンロード"),
        ("upscale.py", "ツール3: 画像高解像度化"),
        ("generate.py", "ツール4: コンテンツ生成"),
        ("onelink.py", "ツール5: OneLinkサイト作成"),
    ]
    
    # 各ツールを順次実行
    for script, description in tools:
        success = run_script(script, description)
        
        if not success:
            print(f"\n処理を中断します: {description} でエラーが発生しました")
            return
    
    print("\n" + "=" * 80)
    print("自動処理完了")
    print("=" * 80)
    print("\n次のステップ:")
    print("1. detected_topics.json を確認してください")
    print("2. 各トピックの内容を目視でチェック")
    print("3. 問題なければ post_to_x.py を実行して投稿")
    print("\nコマンド:")
    print("  python post_to_x.py")
    print("=" * 80)


if __name__ == '__main__':
    main()