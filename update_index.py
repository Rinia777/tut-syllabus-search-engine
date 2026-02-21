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

    # all のデータ（新規ダウンロード分）
    new_all = dept_data.pop("all", [])

    # 最新年度を特定
    years = set()
    for e in new_all:
        y = get_year(e.get("courseStart", ""))
        if y:
            years.add(y)
    latest_year = max(years) if years else None
    print(f"Latest year in new data: {latest_year}")
    print(f"All years in new data: {sorted(years)}")

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

    all_merged = []
    campus_meta = {}

    for dept_code, new_entries in sorted(dept_data.items()):
        campus, level = CAMPUS_MAP.get(dept_code, ("other", "other"))
        dept_dir = os.path.join(API_DIR, campus, level, dept_code)
        os.makedirs(dept_dir, exist_ok=True)

        existing_path = os.path.join(dept_dir, "all.json")
        existing = load_existing(existing_path)

        if existing:
            # 増分更新: 既存から古い年度を保持 + 新データから最新年度のみ採用
            old_entries = [e for e in existing if get_year(e.get("courseStart", "")) != latest_year]
            latest_entries = [e for e in new_entries if get_year(e.get("courseStart", "")) == latest_year]
            merged = old_entries + latest_entries
            print(f"  {dept_code}: {len(old_entries)} old + {len(latest_entries)} new = {len(merged)} total")
        else:
            # 初回: 全年度のデータを保存
            merged = new_entries
            print(f"  {dept_code}: {len(merged)} entries (initial)")

        write_json(existing_path, merged)
        all_merged.extend(merged)

        dept_info = {"code": dept_code, "count": len(merged)}
        campus_meta.setdefault(campus, {}).setdefault(level, []).append(dept_info)

    # search_index.json と api/all.json を更新
    write_json(OUTPUT_FILE, all_merged)
    write_json(os.path.join(API_DIR, "all.json"), all_merged)
    write_json(os.path.join(API_DIR, "departments.json"), campus_meta)
    print(f"\nDone! {len(all_merged)} total entries, {len(dept_data)} departments")


def write_json(path, data):
    """JSON ファイルを書き出す"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_year(course_start):
    """'2025年度前期' → '2025' を返す"""
    match = re.match(r"(\d+)年度", course_start)
    return match.group(1) if match else None


def load_existing(path):
    """既存の JSON ファイルを読み込む。ファイルがなければ空リストを返す"""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


if __name__ == "__main__":
    fetch_and_index()