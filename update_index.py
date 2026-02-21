import requests
import json
import re
import io
import os
import zipfile

SOURCE_ZIP_URL = "https://github.com/Cybroad/TUT-Syllabus-API/archive/refs/heads/main.zip"
TARGET_PATH_PART = "/api/v1/"
OUTPUT_FILE = "search_index.json"
API_DIR = "api"

def parse_entry(data):
    """講義データを加工してエントリを生成する"""
    formatted_periods = []
    for p_str in data.get("classPeriod", []):
        match = re.match(r"([月火水木金土日])(\d+)", p_str)
        if match:
            formatted_periods.append({"day": match.group(1), "period": int(match.group(2))})

    return {
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
        "updateAt": data.get("updateAt"),
        "search_times": formatted_periods,
    }


def fetch_and_index():
    print("Downloading ZIP...")
    res = requests.get(SOURCE_ZIP_URL)
    res.raise_for_status()

# 学部コードごとのデータを格納
    dept_data = {}
    all_entries = []

    # 統合する学部コードのマッピング
    DEPT_MERGE = {
        "ESE5": "ES", "ESE6": "ES", "ESE7": "ES",  # 工学部
        "HSH1": "HS", "HSH2": "HS", "HSH5": "HS", "HSH6": "HS",  # 医療保健学部
    }

    with zipfile.ZipFile(io.BytesIO(res.content)) as z:
        json_files = [f for f in z.namelist() if TARGET_PATH_PART in f and f.endswith(".json")]
        print(f"Processing {len(json_files)} files...")

        for i, file_path in enumerate(json_files):
            # パスから学部コードを抽出: .../api/v1/{dept_code}/{lecture}.json
            path_after_api = file_path.split(TARGET_PATH_PART)[1]
            parts = path_after_api.split("/")
            if len(parts) < 2:
                continue
            dept_code = parts[0]
            # 統合対象なら親コードに変換
            dept_code = DEPT_MERGE.get(dept_code, dept_code)

            with z.open(file_path) as f:
                try:
                    data = json.load(f)
                    entry = parse_entry(data)

                    # 学部別に振り分け
                    if dept_code not in dept_data:
                        dept_data[dept_code] = []
                    dept_data[dept_code].append(entry)
                except Exception as e:
                    print(f"Error in {file_path}: {e}")

            if (i + 1) % 500 == 0:
                print(f"Progress: {i + 1}/{len(json_files)}")

    # all のデータを search_index.json として出力（後方互換）
    all_entries = dept_data.pop("all", [])
    write_json(OUTPUT_FILE, all_entries)
    print(f"Created {OUTPUT_FILE} ({len(all_entries)} entries)")

    # キャンパス → 課程 → 学部 のマッピング
    CAMPUS_MAP = {
        # 八王子キャンパス - 大学
        "CS": ("hachioji", "university"),
        "MS": ("hachioji", "university"),
        "BT": ("hachioji", "university"),
        "ES": ("hachioji", "university"),
        "X1": ("hachioji", "university"),
        # 八王子キャンパス - 大学院
        "GF": ("hachioji", "graduate"),
        # 蒲田キャンパス - 大学
        "DS": ("kamata", "university"),
        "HS": ("kamata", "university"),
        "X3": ("kamata", "university"),
        # 蒲田キャンパス - 大学院
        "GH": ("kamata", "graduate"),
    }

    # api/ ディレクトリ構造を出力
    os.makedirs(API_DIR, exist_ok=True)
    write_json(os.path.join(API_DIR, "all.json"), all_entries)

    campus_meta = {}  # {campus: {level: [dept_info]}}
    for dept_code, entries in sorted(dept_data.items()):
        campus, level = CAMPUS_MAP.get(dept_code, ("other", "other"))
        dept_dir = os.path.join(API_DIR, campus, level, dept_code)
        os.makedirs(dept_dir, exist_ok=True)

        write_json(os.path.join(dept_dir, "all.json"), entries)
        dept_info = {"code": dept_code, "count": len(entries)}
        campus_meta.setdefault(campus, {}).setdefault(level, []).append(dept_info)
        print(f"  {dept_code}: {len(entries)} entries")

    # departments.json（全体のメタデータ）
    write_json(os.path.join(API_DIR, "departments.json"), campus_meta)
    print(f"\nDone! {len(all_entries)} total entries, {len(dept_data)} departments")


def write_json(path, data):
    """JSON ファイルを書き出す"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    fetch_and_index()