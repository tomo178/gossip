#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ツール2: 画像ダウンロードツール（記事本文取得版）

機能:
- detected_topics.json から記事URLを取得
- 記事ページから画像を取得
- 記事本文を取得
- Gemini APIで画像を判定
"""

import json
import os
import re
import time
import base64
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import google.generativeai as genai


def load_config():
    """設定ファイルを読み込む"""
    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def load_data():
    """データファイルを読み込む"""
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


def get_og_image(soup, url):
    """og:imageを取得"""
    og_image = soup.find('meta', property='og:image')
    if og_image and og_image.get('content'):
        image_url = og_image['content']
        if image_url.startswith('http'):
            return image_url
        else:
            return urljoin(url, image_url)
    return None


def get_article_content(soup):
    """記事本文を取得"""
    try:
        # 記事本文のセレクター（複数パターンを試行）
        selectors = [
            '.entry-content',
            '.article-content', 
            '.post-content',
            '.content',
            'article',
            '.article',
            '.main-content',
            '.post-body'
        ]
        
        for selector in selectors:
            content = soup.select_one(selector)
            if content:
                # テキストを取得
                text = content.get_text(strip=True, separator='\n')
                if len(text) > 100:  # 最小文字数チェック
                    return text
        
        # フォールバック: body内のテキストを取得
        body = soup.find('body')
        if body:
            # スクリプトとスタイルタグを除去
            for script in body(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            return body.get_text(strip=True, separator='\n')
        
        return ""
    except Exception as e:
        print(f"    ✗ 記事本文取得エラー: {e}")
        return ""


def get_article_images(soup, url):
    """記事内の画像URLを取得"""
    try:
        selectors = [
            '.article img',
            'article img',
            '.entry-content img',
            '.post-content img',
            '.content img',
            '.article-content img'
        ]
        
        for selector in selectors:
            imgs = soup.select(selector)
            if imgs:
                image_urls = []
                for img in imgs:
                    src = img.get('src') or img.get('data-src')
                    if src:
                        # Base64画像をスキップ
                        if src.startswith('data:'):
                            continue
                        
                        if src.startswith('http'):
                            image_urls.append(src)
                        else:
                            image_urls.append(urljoin(url, src))
                
                return image_urls[:3]  # 最大3枚
        
        return []
    except Exception as e:
        print(f"    ✗ 記事画像取得エラー: {e}")
        return []


def download_image(image_url, save_path):
    """画像をダウンロード"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(image_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # 画像サイズチェック（最小10KB）
        if len(response.content) < 10240:
            return False
            
        # ディレクトリ作成
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        with open(save_path, 'wb') as f:
            f.write(response.content)
            
        return True
    except Exception as e:
        print(f"    ✗ ダウンロードエラー: {e}")
        return False


def init_gemini_api(config):
    """Gemini APIを初期化"""
    genai.configure(api_key=config['gemini_api']['api_key'])
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    return model


def judge_image_with_gemini(model, image_path, max_retries=3):
    """Gemini APIで画像を判定"""
    for attempt in range(max_retries):
        try:
            # 画像をbase64エンコード
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode()
            
            # Gemini APIに送信
            prompt = """この画像を見て、以下の基準で判定してください：

✅ OK: 人物の顔がはっきり写っている（芸能人・有名人・著名人）
❌ NG: 顔が小さい（10%以下）、集合写真、風景・建物のみ、顔が見えない

「OK」または「NG」のみで答えてください。"""

            image_part = {
                "mime_type": "image/jpeg",
                "data": image_data
            }
            
            response = model.generate_content([prompt, image_part], 
                request_options={"timeout": 30})
            
            result = response.text.strip().upper()
            
            if "OK" in result:
                return True
            else:
                return False
                
        except Exception as e:
            print(f"    ⚠ Gemini判定エラー (試行{attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5
                print(f"    ⏱ {wait_time}秒待機中...")
                time.sleep(wait_time)
    
    return False  # 全てのリトライが失敗した場合


def process_topic(topic, config, gemini_model):
    """トピックの画像を処理"""
    topic_id = topic['id']
    celebrities = topic['celebrities']
    article_url = topic['source_article_url']
    
    print(f"\n  トピックID: {topic_id}")
    print(f"  芸能人: {', '.join(celebrities)}")
    print(f"  記事URL: {article_url}")
    
    # 記事ページを取得
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(article_url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        print(f"  ✓ 記事ページ取得完了")
    except Exception as e:
        print(f"  ✗ 記事取得エラー: {e}")
        return False
    
    # 記事本文を取得
    article_content = get_article_content(soup)
    if article_content:
        topic['article_content'] = article_content
        print(f"  ✓ 記事本文取得: {len(article_content)}文字")
    else:
        print(f"  ⚠ 記事本文が見つかりませんでした")
    
    # og:imageを取得
    og_image_url = get_og_image(soup, article_url)
    
    # 記事内画像を取得
    article_images = get_article_images(soup, article_url)
    
    all_images = []
    if og_image_url:
        all_images.append(('og_image', og_image_url))
    
    for i, img_url in enumerate(article_images, 1):
        all_images.append((f'article_{i}', img_url))
    
    if not all_images:
        print(f"  ⚠ 画像が見つかりませんでした")
        return False
    
    print(f"  📸 発見した画像: {len(all_images)}枚")
    
    # 画像をダウンロード・判定
    approved_images = []
    
    for img_type, image_url in all_images:
        print(f"    🔍 {img_type}: {image_url}")
        
        # ファイル名生成
        celebrity_names = '_'.join(celebrities)
        safe_names = re.sub(r'[^\w\s-]', '', celebrity_names)
        img_number = len(approved_images) + 2  # 2から開始
        
        save_path = f"./images/{topic_id}_{safe_names}_{img_number}.jpg"
        
        # ダウンロード
        if download_image(image_url, save_path):
            print(f"    ✓ ダウンロード完了")
            
            # Gemini判定
            print(f"    🤖 Gemini判定中...")
            if judge_image_with_gemini(gemini_model, save_path):
                print(f"    ✅ 承認")
                approved_images.append(save_path)
            else:
                print(f"    ❌ 却下 - 削除")
                os.remove(save_path)
            
            # レート制限対策
            time.sleep(3)
        else:
            print(f"    ✗ ダウンロード失敗")
    
    # 結果を保存
    if approved_images:
        topic['downloaded_image'] = approved_images[0]
        if len(approved_images) > 1:
            topic['additional_images'] = approved_images[1:]
        topic['status'] = 'image_downloaded'
        
        # 重複画像削除（承認が2枚以上の場合、1枚目を削除）
        if len(approved_images) >= 2:
            first_image_path = approved_images[0]
            if os.path.exists(first_image_path):
                os.remove(first_image_path)
                print(f"    🗑️ 重複画像を削除: {os.path.basename(first_image_path)}")
                approved_images = approved_images[1:]
                topic['downloaded_image'] = approved_images[0]
                if len(approved_images) > 1:
                    topic['additional_images'] = approved_images[1:]
                else:
                    topic.pop('additional_images', None)
        
        print(f"  ✅ 完了: {len(approved_images)}枚の画像を保存")
        return True
    else:
        print(f"  ❌ 承認された画像がありません")
        return False


def main():
    print("=" * 60)
    print("画像ダウンロード＆記事本文取得ツール 起動")
    print("=" * 60)
    
    # 設定とデータ読み込み
    config = load_config()
    data = load_data()
    
    # 検出済みトピックを抽出
    detected_topics = [t for t in data if t['status'] == 'detected']
    
    if not detected_topics:
        print("\n処理対象のトピックがありません")
        return
    
    print(f"\n処理対象: {len(detected_topics)}件のトピック")
    
    # API初期化
    print("\n[1] API初期化中...")
    gemini_model = init_gemini_api(config)
    print("✓ 初期化完了")
    
    # 画像フォルダ作成
    os.makedirs('./images', exist_ok=True)
    
    # 各トピックを処理
    print("\n[2] 画像ダウンロード＆判定開始...")
    
    success_count = 0
    for topic in detected_topics:
        if process_topic(topic, config, gemini_model):
            success_count += 1
    
    # データ保存
    print("\n[3] データ保存中...")
    save_data(data)
    
    print("\n" + "=" * 60)
    print(f"処理完了: {success_count}/{len(detected_topics)}件成功")
    print("=" * 60)


if __name__ == '__main__':
    main()