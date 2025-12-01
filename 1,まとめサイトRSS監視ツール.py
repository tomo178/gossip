#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ツール1: まとめサイトRSS監視ツール (monitor_rss.py)

機能:
- 複数のまとめサイトRSSを巡回
- 新着記事のタイトル・URL・概要・画像URLを取得
- Gemini APIで芸能人ゴシップを判定
- 芸能人名と炎上内容を抽出してJSONに保存
"""

import json
import os
import re
import time
from datetime import datetime
import feedparser
import google.generativeai as genai


def load_config():
    """設定ファイルを読み込む"""
    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def load_data():
    """既存のデータファイルを読み込む"""
    config = load_config()
    data_file = config['paths']['data_file']
    
    if os.path.exists(data_file):
        with open(data_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_data(data):
    """データファイルに保存"""
    config = load_config()
    data_file = config['paths']['data_file']
    
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✓ データを保存しました: {data_file}")


def init_gemini_api(config):
    """Gemini APIを初期化"""
    genai.configure(api_key=config['gemini_api']['api_key'])
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    return model


def extract_image_url(description):
    """
    RSS descriptionからimg srcを抽出
    
    Args:
        description: RSS記事の概要（HTMLタグ含む）
    
    Returns:
        str or None: 画像URL
    """
    if not description:
        return None
    
    # imgタグのsrc属性を抽出
    img_match = re.search(r'<img[^>]+src=[\'"]([^\'"]+)[\'"]', description, re.IGNORECASE)
    if img_match:
        return img_match.group(1)
    
    return None


def get_rss_entries(feed_url):
    """
    RSSフィードから記事を取得
    
    Args:
        feed_url: RSSフィードのURL
    
    Returns:
        list: 記事リスト
    """
    try:
        feed = feedparser.parse(feed_url)
        
        if feed.bozo:  # パースエラー
            print(f"    ⚠ RSS解析エラー: {feed_url}")
            return []
        
        return feed.entries
    
    except Exception as e:
        print(f"    ✗ RSS取得エラー: {e}")
        return []


def check_celebrity_gossip(model, article_title, article_summary):
    """
    Gemini APIで芸能人ゴシップかどうか判定
    
    Args:
        model: Gemini model
        article_title: 記事タイトル
        article_summary: 記事概要
    
    Returns:
        dict or None: {
            'is_celebrity_gossip': bool,
            'celebrities': list,
            'topic': str
        }
    """
    prompt = f"""
以下のまとめサイト記事を分析してください。

タイトル: {article_title}
概要: {article_summary[:200]}

この記事が「芸能人・インフルエンサー・有名人の炎上・ゴシップ」に該当するか判定してください。

判定基準:
✅ 該当する: 芸能人の不倫、スキャンダル、炎上、逮捕、トラブル
❌ 該当しない: 政治、スポーツ試合結果（炎上でない）、アニメ・ゲーム（芸能人無関係）、一般ニュース

以下の情報をJSON形式で返してください:
{{
  "is_celebrity_gossip": true/false,
  "celebrities": ["芸能人名1", "芸能人名2"],
  "topic": "炎上内容の要約（20文字以内）"
}}

回答は上記JSON形式のみで返してください（説明文は不要）。
"""
    
    try:
        response = model.generate_content(prompt)
        result_text = response.text.strip()
        
        # JSON部分を抽出（マークダウンのコードブロックを除去）
        if result_text.startswith('```'):
            result_text = result_text.split('```')[1]
            if result_text.startswith('json'):
                result_text = result_text[4:]
            result_text = result_text.strip()
        
        result = json.loads(result_text)
        return result
    
    except Exception as e:
        print(f"    ✗ Gemini API エラー: {e}")
        return None


def is_already_processed(data, article_url):
    """既に処理済みの記事かチェック"""
    return any(item['source_article_url'] == article_url for item in data)


def generate_topic_id():
    """トピックIDを生成"""
    return datetime.now().strftime('%Y%m%d_%H%M%S')


def main():
    print("=" * 60)
    print("まとめサイトRSS監視ツール 起動")
    print("=" * 60)
    
    # 設定とデータ読み込み
    config = load_config()
    data = load_data()
    
    # API初期化
    print("\n[1] Gemini APIを初期化中...")
    gemini_model = init_gemini_api(config)
    print("✓ API初期化完了")
    
    # RSS監視
    print("\n[2] まとめサイトRSSを巡回中...")
    rss_sources = config['rss_feeds']['sources']
    
    new_topics_count = 0
    
    for source in rss_sources:
        source_name = source['name']
        source_url = source['url']
        
        print(f"\n  → {source_name} をチェック中...")
        
        # RSSエントリ取得
        entries = get_rss_entries(source_url)
        
        if not entries:
            print(f"    記事が見つかりません")
            continue
        
        print(f"    {len(entries)}件の記事を取得")
        
        # 各記事をチェック
        for entry in entries[:10]:  # 最新10件のみ
            article_url = entry.link
            article_title = entry.title
            
            # ★★★ 修正: 本文取得方法を改善 ★★★
            article_summary = ''
            if hasattr(entry, 'content') and entry.content:
                article_summary = entry.content[0].get('value', '')
            elif hasattr(entry, 'summary'):
                article_summary = entry.summary
            elif hasattr(entry, 'description'):
                article_summary = entry.description
            
            # 既に処理済みかチェック
            if is_already_processed(data, article_url):
                continue
            
            print(f"\n    記事をチェック: {article_title[:50]}...")
            print(f"      本文: {len(article_summary)} 文字")
            
            # 画像URL抽出
            image_url = extract_image_url(article_summary)
            if image_url:
                print(f"    ✓ 画像URL検出: {image_url[:60]}...")
            
            # Gemini APIで芸能人ゴシップ判定
            result = check_celebrity_gossip(gemini_model, article_title, article_summary)
            
            # ★★★ レート制限対策: 6秒待機 ★★★
            time.sleep(6)
            
            if not result:
                continue
            
            if result.get('is_celebrity_gossip') and result.get('celebrities'):
                print(f"    ✓ 芸能人ゴシップ検出: {', '.join(result['celebrities'])}")
                print(f"      トピック: {result['topic']}")
                
                # 新規トピックとして追加
                topic = {
                    'id': generate_topic_id(),
                    'timestamp': datetime.now().isoformat(),
                    'source_type': 'rss',
                    'source_name': source_name,
                    'source_article_url': article_url,
                    'article_title': article_title,
                    'article_summary': article_summary[:500],
                    'article_image_url': image_url or '',
                    'celebrities': result['celebrities'],
                    'topic': result['topic'],
                    'status': 'detected',
                    'downloaded_image': '',
                    'upscaled_image': '',
                    'generated_title': '',
                    'generated_post_text': '',
                    'onelink_url': '',
                    'posted_tweet_id': '',
                    'manual_approved': False
                }
                
                data.append(topic)
                new_topics_count += 1
                
                print(f"    ✓ トピックID追加: {topic['id']}")
    
    # データ保存
    if new_topics_count > 0:
        print(f"\n[3] 新規トピック {new_topics_count}件を保存中...")
        save_data(data)
        print(f"✓ 完了！")
    else:
        print(f"\n[3] 新規トピックはありませんでした")
    
    print("\n" + "=" * 60)
    print(f"監視完了: 新規トピック {new_topics_count}件")
    print("=" * 60)


if __name__ == '__main__':
    main()