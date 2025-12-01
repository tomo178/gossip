#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ツール4: コンテンツ生成ツール (generate.py)

機能:
- Gemini APIでサイトタイトルとX投稿文を生成
"""

import json
import time
import google.generativeai as genai


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


def init_gemini_api(config):
    """Gemini APIを初期化"""
    genai.configure(api_key=config['gemini_api']['api_key'])
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    return model


def generate_content(model, celebrities, topic, article_summary, article_content="", max_retries=3):
    """
    サイトタイトルとX投稿文を生成
    
    Returns:
        dict: {
            'title': str,
            'post_text': str
        }
    """
    celebrity_names = '、'.join(celebrities)
    
    # 記事内容がある場合は使用
    content_text = article_content if article_content else article_summary
    
    prompt = f"""
以下の炎上情報について、OneLinkサイトのタイトルとX投稿文を生成してください。

芸能人: {celebrity_names}
トピック: {topic}
記事内容: {content_text}

生成条件:
1. サイトタイトル:
   - 興味を引く魅力的なタイトル
   - 「まとめ」「画像まとめ」などの言葉を含める
   - 例: 「山田太郎 不倫画像まとめ」

2. X投稿文:
   - TikTokのコメント風の文体で書く
   - カジュアルで話し言葉調
   - 「まじ」「やばい」「びっくり」などの表現を使用
   - 驚きや感想を表現する
   - 芸能人の名前を必ず含める
   - 80文字以内
   - URLや顔文字は使わない
   
   参考例:
   - 「まじ！？ 山田太郎のツーショット流出してる これネタバレだよね？やめてほしい」
   - 「山田太郎の暴行動画がtiktokに出回ってる… 想像より酷すぎてまじで閲覧注意…」
   - 「山田太郎、来年3月で解散発表 解散の真相、これってまじ… 超びびった これはやばいのでは」

以下のJSON形式で返してください:
{{
  "title": "サイトタイトル",
  "post_text": "X投稿文"
}}
"""
    
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            result_text = response.text.strip()
            
            # JSON部分を抽出
            if result_text.startswith('```'):
                result_text = result_text.split('```')[1]
                if result_text.startswith('json'):
                    result_text = result_text[4:]
                result_text = result_text.strip()
            
            result = json.loads(result_text)
            return result
        
        except Exception as e:
            error_str = str(e)
            print(f"    ⚠ コンテンツ生成エラー (試行{attempt + 1}/{max_retries}): {e}")
            
            # Quota制限の場合
            if "429" in error_str or "quota" in error_str.lower():
                if "retry_delay" in error_str:
                    # retry_delayを抽出
                    import re
                    delay_match = re.search(r'retry in (\d+(?:\.\d+)?)s', error_str)
                    if delay_match:
                        delay_time = float(delay_match.group(1))
                        print(f"    ⏱ API制限のため {delay_time:.1f}秒待機中...")
                        time.sleep(delay_time + 1)  # +1秒のバッファ
                    else:
                        print(f"    ⏱ API制限のため 30秒待機中...")
                        time.sleep(30)
                else:
                    print(f"    ⏱ API制限のため 60秒待機中...")
                    time.sleep(60)
            else:
                # その他のエラーの場合
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 10
                    print(f"    ⏱ {wait_time}秒待機後リトライ...")
                    time.sleep(wait_time)
    
    return None


def generate_for_topic(model, topic):
    """トピックのコンテンツを生成"""
    topic_id = topic['id']
    celebrities = topic['celebrities']
    topic_text = topic['topic']
    # 記事本文がある場合は使用、なければ要約を使用
    article_content = topic.get('article_content', '')
    article_summary = topic.get('article_summary', '')
    
    print(f"\n  トピックID: {topic_id}")
    print(f"  芸能人: {', '.join(celebrities)}")
    
    # 記事内容の表示
    if article_content:
        print(f"  記事本文: {len(article_content)}文字")
        content_preview = article_content[:100] + "..." if len(article_content) > 100 else article_content
    else:
        print(f"  記事要約: {len(article_summary)}文字")
        content_preview = article_summary[:100] + "..." if len(article_summary) > 100 else article_summary
    
    print(f"  内容: {content_preview}")
    
    # コンテンツ生成
    print(f"  AIでコンテンツ生成中...")
    content = generate_content(model, celebrities, topic_text, article_summary, article_content)
    
    if content:
        print(f"  ✓ タイトル: {content['title']}")
        print(f"  ✓ 投稿文: {content['post_text']}")
        return content
    else:
        print(f"  ✗ 生成失敗")
        return None


def main():
    print("=" * 60)
    print("コンテンツ生成ツール 起動")
    print("=" * 60)
    
    # 設定とデータ読み込み
    config = load_config()
    data = load_data()
    
    # 未処理のトピックを抽出（status='image_downloaded' かつ generated_titleが空）
    pending_topics = [t for t in data if t['status'] == 'image_downloaded' and not t.get('generated_title')]
    
    if not pending_topics:
        print("\n処理対象のトピックがありません")
        print("すべてのトピックが処理済みか、画像ダウンロードツール を先に実行してください")
        return
    
    print(f"\n処理対象: {len(pending_topics)}件のトピック（未処理のみ）")
    
    # API初期化
    print("\n[1] API初期化中...")
    gemini_model = init_gemini_api(config)
    print("✓ 初期化完了")
    
    # 各トピックのコンテンツを生成
    print("\n[2] コンテンツ生成開始...")
    
    for topic in pending_topics:
        content = generate_for_topic(gemini_model, topic)
        
        if content:
            # トピック情報を更新
            topic['generated_title'] = content['title']
            topic['generated_post_text'] = content['post_text']
            topic['status'] = 'content_generated'
            print(f"  ✓ 完了")
        else:
            print(f"  ✗ スキップ")
    
    # データ保存
    print("\n[3] データ保存中...")
    save_data(data)
    
    print("\n" + "=" * 60)
    print(f"コンテンツ生成完了: {len(pending_topics)}件のトピックを処理")
    print("=" * 60)


if __name__ == '__main__':
    main()