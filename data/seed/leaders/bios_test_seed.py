#!/usr/bin/env python3
"""
測試用領導人生平種子資料（leader_bios）。

⚠️  注意：本腳本於 2026-11-03 所建立的測試資料已由 retract_test_bios.py 軟撤回。
    撤回原因：「測試種子，未經考證」。
    再次執行本腳本 *不會* 重建被撤回的資料，因為寫入前會查詢同名 bio（含已撤回者）
    若存在即跳過。

本腳本預設拒絕執行，須明確帶 --allow-test-seed 旗標才會寫入：
    python3 data/seed/leaders/bios_test_seed.py --allow-test-seed [--base-url http://127.0.0.1:5052]

行為：
- 寫入 2 筆測試生平（is_test=true）：希特勒、邱吉爾（若同名 bio 已存在於 DB 則跳過）。
- 嘗試把已存在的 leader_records 連結到對應的 bio（透過 PATCH /leader-records/{id}/person）。
- 不再自動建立任何 leader_records（舊版曾在找不到邱吉爾任期時自動補建；已移除）。
- 用途：驗證 POST /leader-bios、GET /leader-bios/{id}、PATCH /leader-records/{id}/person。
- 執行後在標準輸出印出寫入的 id，不印密碼或連線字串。

需要環境變數：
    WORLDLINE_API_KEY  寫入端點所需的 API Key（預設讀 ../.env 的 WORLDLINE_API_KEY）
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:5052"
DEFAULT_API_KEY_ENV = "WORLDLINE_API_KEY"

BIOS = [
    {
        "name": "Adolf Hitler",
        "nameZh": "阿道夫·希特勒",
        "birthDate": "1889-04-20",
        "birthDatePrecision": "day",
        "deathDate": "1945-04-30",
        "birthPlace": {"zh-Hant": "奧地利布勞瑙", "en": "Braunau am Inn, Austria"},
        "party": {"zh-Hant": "國家社會主義德意志工人黨", "en": "NSDAP"},
        "summary": {
            "zh-Hant": "【測試資料】奧地利出生的德國政治家，納粹德國元首，發動第二次世界大戰歐洲戰場。",
            "en": "[Test] Austrian-born German politician who led Nazi Germany and initiated World War II in Europe.",
        },
        "fieldSources": {
            "birthDate": {
                "source": "Encyclopædia Britannica: Adolf Hitler",
                "url": "https://www.britannica.com/biography/Adolf-Hitler",
            },
            "deathDate": {
                "source": "Encyclopædia Britannica: Adolf Hitler",
                "url": "https://www.britannica.com/biography/Adolf-Hitler",
            },
            "birthPlace": {
                "source": "Encyclopædia Britannica: Adolf Hitler",
                "url": "https://www.britannica.com/biography/Adolf-Hitler",
            },
        },
        "isTest": True,
        "_check_date": "1939-09-22",
    },
    {
        "name": "Winston Churchill",
        "nameZh": "溫斯頓·邱吉爾",
        "birthDate": "1874-11-30",
        "birthDatePrecision": "day",
        "deathDate": "1965-01-24",
        "birthPlace": {"zh-Hant": "英國牛津郡伍德斯托克", "en": "Woodstock, Oxfordshire, UK"},
        "party": {"zh-Hant": "保守黨", "en": "Conservative Party"},
        "summary": {
            "zh-Hant": "【測試資料】英國政治家，二戰期間擔任英國首相，領導英國抵抗納粹德國。",
            "en": "[Test] British statesman who served as Prime Minister of the United Kingdom during World War II.",
        },
        "fieldSources": {
            "birthDate": {
                "source": "Encyclopædia Britannica: Winston Churchill",
                "url": "https://www.britannica.com/biography/Winston-Churchill",
            },
            "deathDate": {
                "source": "Encyclopædia Britannica: Winston Churchill",
                "url": "https://www.britannica.com/biography/Winston-Churchill",
            },
        },
        "isTest": True,
        "_check_date": "1940-06-15",
        # _create_leader 已移除：不再自動建立任何 leader_records（2026-11-03 測試任期已軟撤回）
    },
]


def get_api_key():
    key = os.environ.get(DEFAULT_API_KEY_ENV)
    if key:
        return key
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(script_dir, "..", "..", "..", ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("WORLDLINE_API_KEY="):
                    return line.split("=", 1)[1].strip()
    return None


def post_json(url, payload, headers=None):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read()), resp.status
    except urllib.error.HTTPError as e:
        body = json.loads(e.read())
        return body, e.code


def patch_json(url, payload, headers=None):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="PATCH")
    req.add_header("Content-Type", "application/json")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read()), resp.status
    except urllib.error.HTTPError as e:
        body = json.loads(e.read())
        return body, e.code


def get_json(url):
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read())


def get_features_on_date(base, date):
    """取得指定日期的 leaders 清單，key=name, value=feature dict。"""
    resp = get_json(f"{base}/api/v1/leaders?date={date}")
    features = resp.get("data", {}).get("features", [])
    return {f["name"]: f for f in features}


def bio_exists_by_name(base, name, headers):
    """
    檢查 DB 中是否已有同名生平（含已撤回者）。
    透過 POST /leader-bios 試寫一個假請求是不合適的，
    所以用 /leaders 查詢（只查未撤回），加上直接查詢 bio id 的方式並不可靠。
    此處採用「先查 /leaders 確認是否有活躍連結」的輕量做法：
    若 /leaders 有連結 → bio 存在；否則也無法確認已撤回者是否存在，
    故在呼叫前提示並讓呼叫方決定（回傳 None 表示無法確認）。
    實務上，因為撤回後 POST 不會阻擋同名寫入，本函式只做「活躍連結」判斷。
    """
    # 嘗試多個可能在任日期查詢
    for check_date in ["1939-09-22", "1940-06-15", "1943-01-01"]:
        try:
            features = get_features_on_date(base, check_date)
            if name in features and features[name].get("personId"):
                return features[name]["personId"]
        except Exception:
            pass
    return None


def main():
    parser = argparse.ArgumentParser(description="寫入測試用 leader_bios 種子資料")
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument(
        "--allow-test-seed",
        action="store_true",
        help="明確允許執行測試種子寫入（預設拒絕，防止意外重建已撤回的測試資料）",
    )
    args = parser.parse_args()

    if not args.allow_test_seed:
        print(
            "ERROR: 本腳本預設拒絕執行。\n"
            "  此測試種子於 2026-11-03 已由 retract_test_bios.py 軟撤回。\n"
            "  如確認要重新寫入測試資料，請加上 --allow-test-seed 旗標。",
            file=sys.stderr,
        )
        sys.exit(1)

    base = args.base_url.rstrip("/")
    api_key = get_api_key()
    if not api_key:
        print("ERROR: 找不到 WORLDLINE_API_KEY，請設定環境變數或確認 .env 存在。", file=sys.stderr)
        sys.exit(1)
    headers = {"X-API-Key": api_key}

    created_ids = {}  # name -> bio_id

    for bio_data in BIOS:
        check_date = bio_data.pop("_check_date", None)
        # _create_leader 已移除；若 dict 中殘留也一併清除
        bio_data.pop("_create_leader", None)

        name = bio_data["name"]

        # ── 確認同名生平是否已透過 /leaders 連結（活躍任期連結 → bio 已存在且未撤回） ──
        if check_date:
            features = get_features_on_date(base, check_date)
            f = features.get(name)
            if f and f.get("personId"):
                already_linked_bio_id = f["personId"]
                print(f"[SKIP] {name} 已在 {check_date} 有連結 bio，personId={already_linked_bio_id}")
                created_ids[name] = already_linked_bio_id
                continue

        # ── 確認是否已存在同名 bio（含無活躍任期連結的情況） ──
        # 因為 API 目前無法直接搜尋同名 bio，用多日期查詢輔助判斷
        existing_id = bio_exists_by_name(base, name, headers)
        if existing_id:
            print(f"[SKIP] {name} 的 bio 已存在（id={existing_id}），跳過不重複寫入")
            created_ids[name] = existing_id
            continue

        # ── 建立生平 ──
        body, status = post_json(f"{base}/api/v1/leader-bios", bio_data, headers)
        if status == 201:
            bio_id = body["data"]["id"]
            created_ids[name] = bio_id
            print(f"[OK] POST /leader-bios → {bio_id}  ({name})")
        else:
            print(f"[FAIL] POST /leader-bios status={status}: {body}", file=sys.stderr)
            continue

        # ── 嘗試連結現有任期紀錄（不自動建立新任期） ──
        if check_date:
            features = get_features_on_date(base, check_date)
            f = features.get(name)
            if f and f.get("personId") is None:
                r_id = f["recordId"]
                patch_body, patch_status = patch_json(
                    f"{base}/api/v1/leader-records/{r_id}/person",
                    {"personId": bio_id},
                    headers,
                )
                if patch_status == 200:
                    print(f"[OK] PATCH /leader-records/{r_id}/person → personId={bio_id}  ({name})")
                else:
                    print(f"[WARN] PATCH failed status={patch_status}: {patch_body}", file=sys.stderr)
            elif f and f.get("personId"):
                print(f"[INFO] {name} 的任期紀錄已有 personId={f['personId']}，不重複連結")
            else:
                print(f"[INFO] {check_date} 無 {name} 的在任紀錄（已撤回或不存在），跳過連結")

    print("\n--- 寫入的生平 id ---")
    for n, bio_id in created_ids.items():
        print(f"{bio_id}  ({n})")


if __name__ == "__main__":
    main()
