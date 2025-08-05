import os
import time
import re
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup

# =========================
# 設定項目
# =========================
SPREADSHEET_ID = '1ZqRekcKkUUoVxZuO8hrWRWwTauyEk8kD_NmV5IZy02w'
INPUT_SHEET_NAME = 'input'
BASE_SHEET_NAME = 'Base'
TODAY_SHEET_NAME = datetime.now().strftime("%y%m%d")

# =========================
# Google Sheets認証
# =========================
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SPREADSHEET_ID)

# =========================
# WebDriverのセットアップ
# =========================
options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
driver = webdriver.Chrome(options=options)

# =========================
# URLリストの取得
# =========================
input_ws = sheet.worksheet(INPUT_SHEET_NAME)
urls = input_ws.col_values(3)[1:]  # C2以降

# =========================
# 新しい日付シートを作成（Baseをコピー）
# =========================
try:
    sheet.duplicate_sheet(source_sheet_id=sheet.worksheet(BASE_SHEET_NAME).id, new_sheet_name=TODAY_SHEET_NAME)
except Exception as e:
    print("❗シート複製エラー:", e)

out_ws = sheet.worksheet(TODAY_SHEET_NAME)

# =========================
# 本文・コメント取得処理
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
    comment_divs = soup.find_all('p', class_='sc-169yn8p-10 hYFULX')
    for div in comment_divs:
        text = div.text.strip()
        if text:
            comments.append(text)

    return title, body, comments

# =========================
# 各URLに対する処理
# =========================
for idx, url in enumerate(urls):
    if not url.startswith("http"):
        continue

    print(f"🔍 {idx+1}: {url}")
    try:
        title, body, comments = extract_article_and_comments(url)

        # 出力
        out_ws.update(f'A{2 + idx}', str(idx + 1))  # No
        out_ws.update(f'B{2 + idx}', title)
        out_ws.update(f'C{2 + idx}', url)
        out_ws.update(f'D{2 + idx}', body)
        out_ws.update(f'E{2 + idx}', '\n'.join(comments[:30]))  # 最大30件
        out_ws.update(f'F{2 + idx}', len(comments))  # コメント件数

        # コメント件数をinputシートのF列にも反映
        input_ws.update(f'F{2 + idx}', len(comments))

    except Exception as e:
        print(f"⚠️ エラー: {url} → {e}")
        out_ws.update(f'B{2 + idx}', '（取得失敗）')
        input_ws.update(f'F{2 + idx}', 'NG')

driver.quit()
print("✅ 完了")
