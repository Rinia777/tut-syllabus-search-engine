import requests
import json
import re
import io
import zipfile

SOURCE_ZIP_URL = "https://github.com/Cybroad/TUT-Syllabus-API/archive/refs/heads/main.zip"
TARGET_PATH_PART = "/api/v1/all/"
OUTPUT_FILE = "search_index.json"

def fetch_and_index():
    print(f"Downloading ZIP...")
    res = requests.get(SOURCE_ZIP_URL)
    res.raise_for_status()
    
    search_index = []
    
    with zipfile.ZipFile(io.BytesIO(res.content)) as z:
        json_files = [f for f in z.namelist() if TARGET_PATH_PART in f and f.endswith(".json")]
        print(f"Processing {len(json_files)} classes (Full Data Mode)...")
        
        for i, file_path in enumerate(json_files):
            with z.open(file_path) as f:
                try:
                    data = json.load(f)
                    
                    # 検索の利便性のために「times」のみパースして追加
                    formatted_periods = []
                    for p_str in data.get("classPeriod", []):
                        match = re.match(r"([月火水木金土日])(\d+)", p_str)
                        if match:
                            formatted_periods.append({"day": match.group(1), "period": int(match.group(2))})

                    # 元のJSONの全フィールドを維持して構築
                    entry = {
                        "lectureCode": data.get("lectureCode"),
                        "courseName": data.get("courseName"),
                        "lecturer": data.get("lecturer", []),
                        "regularOrIntensive": data.get("regularOrIntensive"),
                        "courseType": data.get("courseType"),
                        "courseStart": data.get("courseStart"),
                        "classPeriod": data.get("classPeriod", []),
                        "targetDepartment": data.get("targetDepartment"),
                        "targetGrade": data.get("targetGrade", []),
                        "numberOfCredits": data.get("numberOfCredits"),
                        "classroom": data.get("classroom", []),
                        # 講義詳細（ネスト構造）もすべて取得
 
                        "updateAt": data.get("updateAt"),
                        # 検索用に追加したカスタムフィールド
                        "search_times": formatted_periods 
                    }
                    search_index.append(entry)
                except Exception as e:
                    print(f"Error in {file_path}: {e}")
            
            if (i + 1) % 500 == 0:
                print(f"Progress: {i + 1}/{len(json_files)}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(search_index, f, ensure_ascii=False, indent=2)
    
    print(f"Done! Created {OUTPUT_FILE}")

if __name__ == "__main__":
    fetch_and_index()