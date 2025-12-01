#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ツール6: X投稿ツール (post_to_x.py) [修正版]

機能:
- LP生成済み(content_generated)のトピックを対象
- GitHub PagesのURLを自動生成
- X APIで投稿を実行
"""

import json
from datetime import datetime
import tweepy


def load_config():
    """設定ファイルを読み込む"""
    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def load_data():
    """データファイルを読み込む"""
    config = load_config()
    data_file = config['paths']['data_file']
    
    with open(data_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_data(data):
    """データファイルに保存"""
    config = load_config()
    data_file = config['paths']['data_file']
    
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✓ データを保存しました")


def init_x_api(config):
    """X API v2クライアントを初期化"""
    # config.jsonのキーに合わせて x_post_api を使用
    api_config = config['x_post_api']
    
    client = tweepy.Client(
        bearer_token=api_config['bearer_token'],
        consumer_key=api_config['api_key'],
        consumer_secret=api_config['api_secret'],
        access_token=api_config['access_token'],
        access_token_secret=api_config['access_token_secret']
    )
    return client


def generate_page_url(base_url, topic_id):
    """トピックIDからGitHub PagesのURLを生成"""
    if not base_url.endswith('/'):
        base_url += '/'
    return f"{base_url}{topic_id}.html"


def post_to_twitter(client, topic, base_url):
    """
    Xに投稿
    """
    topic_id = topic['id']
    post_text = topic['generated_post_text']
    
    # サイトURLを生成
    site_url = generate_page_url(base_url, topic_id)
    
    print(f"\n  トピックID: {topic_id}")
    print(f"  投稿文: {post_text}")
    print(f"  URL: {site_url}")
    
    # 投稿テキストを作成
    full_text = f"{post_text}\n\n{site_url}"
    
    # 文字数チェック (URLは23文字換算されるが、余裕を見て判定)
    if len(full_text) > 280:
        print(f"  ⚠ 文字数調整中...")
        max_text_len = 280 - 25 - 5  # URL分 + 改行分余裕
        full_text = f"{post_text[:max_text_len]}...\n\n{site_url}"
    
    try:
        print(f"  🚀 投稿中...")
        response = client.create_tweet(text=full_text)
        
        tweet_id = response.data['id']
        tweet_url = f"https://x.com/i/status/{tweet_id}"
        
        print(f"  ✓ 投稿成功: {tweet_url}")
        return tweet_id
    
    except Exception as e:
        print(f"  ✗ 投稿エラー: {e}")
        return None


def approve_topic_interactive(topic, base_url):
    """対話的にトピックを確認・承認"""
    site_url = generate_page_url(base_url, topic['id'])
    
    print("\n" + "=" * 60)
    print(f"トピックID: {topic['id']}")
    print(f"タイトル: {topic.get('generated_title', 'タイトルなし')}")
    print(f"投稿文: {topic.get('generated_post_text', 'テキストなし')}")
    print(f"リンク先: {site_url}")
    print("=" * 60)
    
    while True:
        choice = input("\n投稿しますか? (y=はい / n=スキップ / q=終了): ").lower()
        if choice == 'y':
            return True
        elif choice == 'n':
            return False
        elif choice == 'q':
            return None
        else:
            print("y, n, qのいずれかを入力してください")


def main():
    print("=" * 60)
    print("X投稿ツール (GitHub Pages版) 起動")
    print("=" * 60)
    
    config = load_config()
    data = load_data()
    
    # GitHub PagesのURL設定チェック
    if 'github_pages' not in config or 'base_url' not in config['github_pages']:
        print("\n[エラー] config.json に 'github_pages.base_url' が設定されていません。")
        print("例: \"github_pages\": { \"base_url\": \"https://user.github.io/repo/\" } を追加してください。")
        return

    base_url = config['github_pages']['base_url']

    # 投稿対象: 'content_generated' (LP作成済) かつ 未投稿のもの
    # ※ generate_lp.py でstatus更新していない場合は content_generated のままなのでこれを対象にする
    ready_topics = [
        t for t in data 
        if t['status'] == 'content_generated' 
        and not t.get('posted_tweet_id')
    ]
    
    if not ready_topics:
        print("\n投稿可能な新しいトピックがありません。")
        print("※ generate.py でコンテンツ生成済みか確認してください。")
        return
    
    print(f"\n投稿候補: {len(ready_topics)}件のトピック")
    
    # API初期化
    print("\n[1] X API初期化中...")
    try:
        x_client = init_x_api(config)
        print("✓ 初期化完了")
    except Exception as e:
        print(f"✗ API初期化エラー: {e}")
        return
    
    # 各トピックを確認して投稿
    print("\n[2] 投稿処理開始...")
    
    posted_count = 0
    
    for topic in ready_topics:
        # 手動確認
        approval = approve_topic_interactive(topic, base_url)
        
        if approval is None:
            print("\n処理を中断します")
            break
        elif not approval:
            print("スキップしました")
            continue
        
        # 投稿実行
        tweet_id = post_to_twitter(x_client, topic, base_url)
        
        if tweet_id:
            # データ更新
            topic['posted_tweet_id'] = tweet_id
            topic['status'] = 'posted'
            topic['posted_at'] = datetime.now().isoformat()
            topic['final_url'] = generate_page_url(base_url, topic['id'])
            posted_count += 1
            
            # 1件ごとに保存（安全のため）
            save_data(data)
    
    print("\n" + "=" * 60)
    print(f"処理完了: {posted_count}件を投稿しました")
    print("=" * 60)


if __name__ == '__main__':
    main()