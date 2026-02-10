import requests
import json
import re
import io
import zipfile

# 設定
SOURCE_ZIP_URL = "https://github.com/Cybroad/TUT-Syllabus-API/archive/refs/heads/main.zip"
# ZIP解凍後のデータがあるパス（リポジトリ名-ブランチ名/パス）
DATA_PATH_PREFIX = "TUT-Syllabus-API-main/api/v1/all/"
OUTPUT_FILE = "search_index.json"

def fetch_and_index():
    print("Downloading source repository as ZIP...")
    res = requests.get(SOURCE_ZIP_URL)
    res.raise_for_status()
    
    search_index = []
    
    # ZIPをメモリ上で展開
    with zipfile.ZipFile(io.BytesIO(res.content)) as z:
        # ZIP内のファイルリストを取得
        json_files = [f for f in z.namelist() if f.startswith(DATA_PATH_PREFIX) and f.endswith(".json")]
        
        print(f"Processing {len(json_files)} classes...")
        
        for i, file_path in enumerate(json_files):
            with z.open(file_path) as f:
                data = json.load(f)
                
                # 曜日・時限のパース
                formatted_periods = []
                for p_str in data.get("classPeriod", []):
                    match = re.match(r"([月火水木金土日])(\d+)", p_str)
                    if match:
                        formatted_periods.append({"day": match.group(1), "period": int(match.group(2))})

                # 必要な項目を抽出
                entry = {
                    "id": data.get("lectureCode"),
                    "name": data.get("courseName"),
                    "teacher": data.get("lecturer", []),
                    "dept": data.get("targetDepartment"),
                    "grade": data.get("targetGrade", []),
                    "term": data.get("courseStart"),
                    "times": formatted_periods,
                    "raw_times": data.get("classPeriod")
                }
                search_index.append(entry)
            
            if i % 500 == 0:
                print(f"Progress: {i}/{len(json_files)}")

    # 保存
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(search_index, f, ensure_ascii=False, indent=2)
    print(f"Successfully created {OUTPUT_FILE}")

if __name__ == "__main__":
    fetch_and_index()