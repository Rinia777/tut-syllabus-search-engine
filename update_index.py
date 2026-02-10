import requests
import json
import re
import io
import zipfile

# 設定
SOURCE_ZIP_URL = "https://github.com/Cybroad/TUT-Syllabus-API/archive/refs/heads/main.zip"
# ターゲットとなるパスの一部
TARGET_PATH_PART = "/api/v1/all/"
OUTPUT_FILE = "search_index.json"

def fetch_and_index():
    print(f"Downloading ZIP from {SOURCE_ZIP_URL}...")
    res = requests.get(SOURCE_ZIP_URL)
    res.raise_for_status()
    
    search_index = []
    
    with zipfile.ZipFile(io.BytesIO(res.content)) as z:
        # ZIP内の全ファイルから「/api/v1/all/」を含み「.json」で終わるものを自動検索
        json_files = [f for f in z.namelist() if TARGET_PATH_PART in f and f.endswith(".json")]
        
        if not json_files:
            print("【警告】対象のJSONファイルが見つかりませんでした。")
            # 空のリストでもファイルだけは作成するようにし、Gitエラーを防ぐ
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)
            return

        print(f"Found {len(json_files)} classes. Processing...")
        
        for i, file_path in enumerate(json_files):
            with z.open(file_path) as f:
                try:
                    data = json.load(f)
                    
                    # 曜日・時限のパース
                    formatted_periods = []
                    for p_str in data.get("classPeriod", []):
                        match = re.match(r"([月火水木金土日])(\d+)", p_str)
                        if match:
                            formatted_periods.append({"day": match.group(1), "period": int(match.group(2))})

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
                except Exception as e:
                    print(f"Skip file {file_path} due to error: {e}")
            
            if (i + 1) % 500 == 0:
                print(f"Progress: {i + 1}/{len(json_files)}")

    # 最後に必ずファイルを作成する
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(search_index, f, ensure_ascii=False, indent=2)
    
    print(f"Successfully created {OUTPUT_FILE} with {len(search_index)} entries.")

if __name__ == "__main__":
    fetch_and_index()