import os
import time
import re
import json
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup

# =========================
# 認証スコープ設定
# =========================
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

# credentials.json 読み込みデバッグ
try:
    with open("credentials.json", "r", encoding="utf-8") as f:
        credentials_data = json.load(f)
        print("✅ credentials.json 読み込み成功")
        print(f"client_email: {credentials_data.get('client_email')}")
except Exception as e:
    print(f"❌ credentials.json 読み込みエラー: {e}")
    exit(1)

# Google Sheets 認証
try:
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    print("✅ Google Sheets 認証成功")
except Exception as e:
    print(f"❌ Google Sheets 認証エラー: {e}")
    exit(2)

# =========================
# 定数設定
# =========================
SPREADSHEET_ID = '1ZqRekcKkUUoVxZuO8hrWRWwTauyEk8kD_NmV5IZy02w'
INPUT_SHEET_NAME = 'input'
BASE_SHEET_NAME = 'Base'
TODAY_SHEET_NAME = datetime.now().strftime("%y%m%d")

# =========================
# WebDriverの初期化
# =========================
options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
driver = webdriver.Chrome(options=options)

# =========================
# スプレッドシート操作
# =========================
try:
    sheet = client.open_by_key(SPREADSHEET_ID)
    input_ws = sheet.worksheet(INPUT_SHEET_NAME)
    urls = input_ws.col_values(3)[1:]  # C2以降
except Exception as e:
    print(f"❌ スプレッドシート読み込みエラー: {e}")
    exit(3)

# 出力用のシート作成
try:
    sheet.duplicate_sheet(source_sheet_id=sheet.worksheet(BASE_SHEET_NAME).id, new_sheet_name=TODAY_SHEET_NAME)
    out_ws = sheet.worksheet(TODAY_SHEET_NAME)
    print(f"✅ シート「{TODAY_SHEET_NAME}」作成完了")
except Exception as e:
    print(f"⚠️ シート作成エラー（既に存在？）: {e}")
    out_ws = sheet.worksheet(TODAY_SHEET_NAME)

# =========================
# ニュース記事・コメント取得
# =========================
def extract_article_and_comments(url):
    driver.get(url)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # タイトル
    title_tag = soup.find('title')
    title = title_tag.text.strip() if title_tag else '（タイトル取得失敗）'

    # 本文
    body_area = soup.find('article') or soup.find('div', class_='article_body')
    body = body_area.get_text(separator='\n').strip() if body_area else '（本文取得失敗）'

    # コメント
    comments = []
    comment_tags = soup.find_all('p', class_='sc-169yn8p-10 hYFULX')
    for tag in comment_tags:
        text = tag.get_text(strip=True)
        if text:
            comments.append(text)

    return title, body, comments

# =========================
# 処理ループ
# =========================
for idx, url in enumerate(urls):
    row = idx + 2  # 行番号（2から始まる）

    if not url.startswith("http"):
        print(f"⚠️ 無効なURL（スキップ）: {url}")
        continue

    print(f"🔍 [{row}] 処理中: {url}")

    try:
        title, body, comments = extract_article_and_comments(url)

        # 結果を出力シートに書き込み
        out_ws.update(f'A{row}', str(idx + 1))  # 番号
        out_ws.update(f'B{row}', title)
        out_ws.update(f'C{row}', url)
        out_ws.update(f'D{row}', body)
        out_ws.update(f'E{row}', '\n'.join(comments[:30]))  # 最大30件
        out_ws.update(f'F{row}', len(comments))  # コメント件数

        # inputシートにもコメント件数を記入
        input_ws.update(f'F{row}', len(comments))

    except Exception as e:
        print(f"❌ [{row}] エラー: {e}")
        out_ws.update(f'B{row}', '（取得失敗）_
