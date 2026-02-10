import requests
import json
import re
import io
import zipfile
import os

# --- 設定 ---
# 本家のZIPダウンロードURL（mainブランチ）
SOURCE_ZIP_URL = "https://github.com/Cybroad/TUT-Syllabus-API/archive/refs/heads/main.zip"
# ZIP内のデータが入っているディレクトリのパス（GitHubの仕様で リポジトリ名-main/パス になる）
DATA_PATH_PREFIX = "TUT-Syllabus-API-main/api/v1/all/"
OUTPUT_FILE = "search_index.json"

def fetch_and_index():
    print("Downloading source repository as ZIP...")
    # 1. ZIPファイルをダウンロード
    res = requests.get(SOURCE_ZIP_URL)
    res.raise_for_status()
    
    search_index = []
    
    # 2. ZIPをメモリ上で展開
    with zipfile.ZipFile(io.BytesIO(res.content)) as z:
        # ZIP内の全ファイルリストから、api/v1/all/ 配下のJSONのみを抽出
        json_files = [f for f in z.namelist() if f.startswith(DATA_PATH_PREFIX) and f.endswith(".json")]
        
        if not json_files:
            print("Error: No JSON files found in the specified path.")
            return

        print(f"Processing {len(json_files)} classes...")
        
        for i, file_path in enumerate(json_files):
            with z.open(file_path) as f:
                data = json.load(f)
                
                # 曜日・時限のパース (例: "月1" -> {"day": "月", "period": 1})
                formatted_periods = []
                for p_str in data.get("classPeriod", []):
                    # 「月1」「火2」のような形式を想定
                    match = re.match(r"([月火水木金土日])(\d+)", p_str)
                    if match:
                        formatted_periods.append({"day": match.group(1), "period": int(match.group(2))})

                # あなたがSwiftで使いたい7項目を抽出
                entry = {
                    "id": data.get("lectureCode"),         # 時間割コード
                    "name": data.get("courseName"),        # 講義名
                    "teacher": data.get("lecturer", []),   # 担当教員
                    "dept": data.get("targetDepartment"),  # 学部
                    "grade": data.get("targetGrade", []),  # 対象学年
                    "term": data.get("courseStart"),       # 開講時期
                    "times": formatted_periods,            # 曜日・時限（検索用）
                    "raw_times": data.get("classPeriod")   # 曜日・時限（原文）
                }
                search_index.append(entry)
            
            if (i + 1) % 500 == 0:
                print(f"Progress: {i + 1}/{len(json_files)}")

    # 3. JSONとして保存
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(search_index, f, ensure_ascii=False, indent=2)
    
    print(f"Successfully created {OUTPUT_FILE} with {len(search_index)} entries.")

if __name__ == "__main__":
    fetch_and_index()