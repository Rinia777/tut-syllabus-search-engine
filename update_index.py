import requests
import json
import re
import os

# 設定：取得元と保存先
SOURCE_REPO = "Cybroad/TUT-Syllabus-API"
SOURCE_PATH = "api/v1/all"
OUTPUT_FILE = "search_index.json"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def fetch_and_index():
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    
    # 1. ファイルリストの取得
    api_url = f"https://api.github.com/repos/{SOURCE_REPO}/contents/{SOURCE_PATH}"
    print("Fetching file list...")
    res = requests.get(api_url, headers=headers)
    res.raise_for_status()
    file_list = res.json()

    search_index = []

    # 2. 各ファイルのデータを取得して加工
    print(f"Processing {len(file_list)} classes...")
    for i, file_info in enumerate(file_list):
        if not file_info["name"].endswith(".json"): continue
            
        raw_res = requests.get(file_info["download_url"], headers=headers)
        data = raw_res.json()

        # 曜日・時限の検索をしやすく分解 (例: "月1" -> {"day": "月", "period": 1})
        formatted_periods = []
        for p_str in data.get("classPeriod", []):
            match = re.match(r"([月火水木金土日])(\d+)", p_str)
            if match:
                formatted_periods.append({"day": match.group(1), "period": int(match.group(2))})

        # 必要な7項目 + 予備を抽出
        entry = {
            "id": data.get("lectureCode"),         # 時間割コード
            "name": data.get("courseName"),        # 講義名
            "teacher": data.get("lecturer", []),   # 担当教員
            "dept": data.get("targetDepartment"), # 学部
            "grade": data.get("targetGrade", []),  # 学年
            "term": data.get("courseStart"),       # 開講時期
            "times": formatted_periods,            # 曜日・時限（分解済）
            "raw_times": data.get("classPeriod")   # 曜日・時限（原文）
        }
        search_index.append(entry)
        
        # 進捗表示（100件ごと）
        if i % 100 == 0: print(f"Progress: {i}/{len(file_list)}")

    # 3. 1つのJSONファイルに保存
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(search_index, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    fetch_and_index()
