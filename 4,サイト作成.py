#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ツール5(改3): シンプルLP生成ツール + URL自動設定

機能:
- 初回実行時にGitHub情報を聞いて config.json にURLを自動保存
- detected_topics.json から画像メインのシンプルLPを生成
- スマホ・モバイルファーストなデザイン
"""

import json
import os
import shutil
import html

CONFIG_FILE = 'config.json'

def load_config():
    """設定ファイルを読み込む"""
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(config):
    """設定ファイルを保存する"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def check_and_setup_github_url(config):
    """
    GitHub PagesのURL設定を確認し、未設定ならユーザーに入力させて保存する
    """
    # github_pagesキーがない、またはbase_urlが空の場合
    if 'github_pages' not in config or not config['github_pages'].get('base_url'):
        print("\n" + "!" * 60)
        print("【初期設定】GitHub PagesのURLを設定します")
        print("X投稿用に、あなたのGitHub PagesのURLを特定する必要があります。")
        print("!" * 60 + "\n")

        username = input("GitHubのユーザー名を入力してください (例: user123): ").strip()
        repo_name = input("このリポジトリ名を入力してください (例: gossip-news): ").strip()

        if username and repo_name:
            # URLを生成 (末尾にスラッシュをつける)
            base_url = f"https://{username}.github.io/{repo_name}/"
            
            # configを更新
            if 'github_pages' not in config:
                config['github_pages'] = {}
            config['github_pages']['base_url'] = base_url
            
            # 保存
            save_config(config)
            print(f"\n✓ 設定を保存しました: {base_url}")
            print("※ config.json が更新されました\n")
            return base_url
        else:
            print("⚠ 入力が正しくありません。今回はスキップします。")
            return ""
    
    return config['github_pages']['base_url']

def load_data():
    """データファイルを読み込む"""
    config = load_config()
    data_file = config['paths']['data_file']
    
    if os.path.exists(data_file):
        with open(data_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def setup_docs_dir():
    """docsディレクトリの初期化"""
    docs_dir = './docs'
    images_dir = './docs/images'
    
    os.makedirs(docs_dir, exist_ok=True)
    os.makedirs(images_dir, exist_ok=True)
    
    return docs_dir

def copy_image(src_path, dest_folder):
    """画像をdocs用フォルダにコピー"""
    if not src_path or not os.path.exists(src_path):
        return None
    
    filename = os.path.basename(src_path)
    dest_path = os.path.join(dest_folder, 'images', filename)
    
    shutil.copy2(src_path, dest_path)
    return f"./images/{filename}"

def generate_lp_html(topic, affiliate_link, dest_folder):
    """画像メインのシンプルLP HTMLを生成"""
    
    title = html.escape(topic.get('generated_title', topic['article_title']))
    
    # 画像リスト準備
    image_paths = []
    if topic.get('downloaded_image'):
        image_paths.append(topic['downloaded_image'])
    if topic.get('additional_images'):
        image_paths.extend(topic['additional_images'])
    
    # 画像コピー処理
    html_images = []
    for img in image_paths:
        new_path = copy_image(img, dest_folder)
        if new_path:
            html_images.append(new_path)

    if not html_images:
        return None

    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>{title}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #000000;
            color: #ffffff;
            line-height: 1.5;
        }}
        .container {{
            max-width: 480px;
            margin: 0 auto;
            background-color: #1a1a1a;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            padding-bottom: 80px;
        }}
        .header {{
            padding: 15px 15px 10px 15px;
            background: #000;
            text-align: center;
            border-bottom: 1px solid #333;
        }}
        h1 {{
            font-size: 1.3rem;
            font-weight: 800;
            color: #ffeb3b;
            line-height: 1.4;
            margin: 0;
            text-shadow: 0 2px 4px rgba(0,0,0,0.5);
        }}
        .gallery {{
            padding: 15px 10px;
            flex-grow: 1;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }}
        .image-card {{
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 10px rgba(0,0,0,0.5);
            position: relative;
        }}
        .image-card img {{
            width: 100%;
            height: auto;
            display: block;
        }}
        .click-hint {{
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            background: rgba(0,0,0,0.7);
            color: white;
            text-align: center;
            font-size: 0.8rem;
            padding: 8px;
            pointer-events: none;
            font-weight: bold;
        }}
        .action-area {{
            position: fixed;
            bottom: 20px;
            left: 0;
            right: 0;
            padding: 0 20px;
            z-index: 1000;
            max-width: 480px;
            margin: 0 auto;
        }}
        .cta-button {{
            display: flex;
            justify-content: center;
            align-items: center;
            width: 100%;
            height: 60px;
            background: linear-gradient(90deg, #ff0050, #00f2ea);
            color: white;
            font-size: 1.3rem;
            font-weight: bold;
            text-decoration: none;
            border-radius: 30px;
            box-shadow: 0 5px 20px rgba(0, 0, 0, 0.7);
            animation: pulse 1.5s infinite;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
        }}
        @keyframes pulse {{
            0% {{ transform: scale(1); box-shadow: 0 0 0 0 rgba(255, 0, 80, 0.7); }}
            70% {{ transform: scale(1.03); box-shadow: 0 0 0 10px rgba(255, 0, 80, 0); }}
            100% {{ transform: scale(1); box-shadow: 0 0 0 0 rgba(255, 0, 80, 0); }}
        }}
        a {{ text-decoration: none; display: block; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
        </div>
        <div class="gallery">
"""
    for img_src in html_images:
        html_content += f"""
            <div class="image-card">
                <a href="{affiliate_link}" target="_blank">
                    <img src="{img_src}" alt="画像">
                    <div class="click-hint">画像をタップして続きを見る ▶</div>
                </a>
            </div>
"""
    html_content += f"""
        </div>
        <div class="action-area">
            <a href="{affiliate_link}" target="_blank" class="cta-button">
                ここをタップして開く
            </a>
        </div>
    </div>
</body>
</html>
"""
    return html_content

def generate_admin_list(pages, base_url):
    """自分用管理画面"""
    html = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>生成されたページ一覧</title>
<style>body{font-family:sans-serif;padding:20px;background:#f0f0f0} li{background:white;margin:10px 0;padding:15px;list-style:none;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,0.1)} a{text-decoration:none;color:#007bff;font-weight:bold;font-size:1.1em;display:block} span{display:block;color:#666;font-size:0.8em;margin-top:5px;word-break:break-all;}</style>
</head><body>
<h2>生成されたページ一覧 (Admin用)</h2>
<ul>"""
    for p in pages:
        full_url = f"{base_url}{p['filename']}" if base_url else "URL設定未完了"
        html += f'<li><a href="{p["filename"]}">{p["title"]}</a><span>Public URL: {full_url}</span></li>'
    html += "</ul></body></html>"
    return html

def main():
    print("=" * 60)
    print("シンプルLP生成ツール (URL自動設定版) 起動")
    print("=" * 60)
    
    # 設定読み込み & URL自動設定ウィザード
    config = load_config()
    base_url = check_and_setup_github_url(config)
    
    affiliate_link = config['tiktok_lite']['invite_link']
    if not affiliate_link:
        print("Error: config.jsonにtiktok_lite.invite_linkが設定されていません")
        return

    data = load_data()
    docs_dir = setup_docs_dir()
    
    generated_pages = []
    
    print("\n[1] 各トピックのLPを生成中...")
    
    for topic in data:
        if not topic.get('generated_title') or not topic.get('downloaded_image'):
            continue
            
        filename = f"{topic['id']}.html"
        file_path = os.path.join(docs_dir, filename)
        
        print(f"  Generating: {filename} ...")
        
        html_content = generate_lp_html(topic, affiliate_link, docs_dir)
        
        if html_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            generated_pages.append({
                'title': topic['generated_title'],
                'filename': filename
            })

    # 管理用インデックス作成
    with open(os.path.join(docs_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(generate_admin_list(generated_pages, base_url))
    
    print(f"\n✓ 完了: {len(generated_pages)}個のサイトを作成しました")
    print(f"  出力先: ./docs/")
    
    if base_url:
        print("-" * 60)
        print("【公開予定のURL】")
        for page in generated_pages:
            print(f"  - {base_url}{page['filename']}")
        print("\n※ GitHubにプッシュすると、上記のURLでアクセスできるようになります")
    else:
        print("\n⚠ 注意: GitHub PagesのURLが設定されていません。config.jsonを確認してください。")
    print("-" * 60)

if __name__ == '__main__':
    main()