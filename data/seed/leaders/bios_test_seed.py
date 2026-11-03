#!/usr/bin/env python3
"""
測試用領導人生平種子資料（leader_bios）。
- 寫入 2 筆測試生平（is_test=true）：希特勒、邱吉爾。
- 嘗試把已存在的 leader_records 連結到對應的 bio（透過 PATCH /leader-records/{id}/person）。
- 若邱吉爾的 leader_record 不存在，自動補建（is_test=true，1940-05-10 起任 head_of_government）。
- 已存在者（同名 bio 已連結）跳過不重複寫入。
- 用途：驗證 POST /leader-bios、GET /leader-bios/{id}、PATCH /leader-records/{id}/person。
- 執行後在標準輸出印出寫入的 id，不印密碼或連線字串。

使用方式：
    python3 data/seed/leaders/bios_test_seed.py [--base-url http://127.0.0.1:5052]

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
        # 用來連結 leader_records 的比對條件
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
        # 邱吉爾任期從 1940-05-10 起（英國 PM），用此日期確認
        "_check_date": "1940-06-15",
        # 若找不到同名 leader_record，自動建立（is_test=true）
        "_create_leader": {
            "role": "head_of_government",
            "title": "Prime Minister of the United Kingdom",
            "validFrom": "1940-05-10",
            "validTo": "1945-07-26",
            "source": "Encyclopædia Britannica: Winston Churchill https://www.britannica.com/biography/Winston-Churchill（本次查閱）",
            "sourceUrl": "https://www.britannica.com/biography/Winston-Churchill",
            "verified": True,
            # regimeSlug 用於查詢 regimeId
            "_regimeSlug": "united-kingdom",
        },
    },
]


def get_api_key():
    key = os.environ.get(DEFAULT_API_KEY_ENV)
    if key:
        return key
    # Try reading from .env in project root
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


def get_regime_id_by_slug(base, slug, check_date):
    """從 leaders?date= 找到指定 slug 的 regimeId。"""
    resp = get_json(f"{base}/api/v1/leaders?date={check_date}&regime={slug}")
    features = resp.get("data", {}).get("features", [])
    if features:
        return features[0]["regimeId"]
    return None


def main():
    parser = argparse.ArgumentParser(description="寫入測試用 leader_bios 種子資料")
    parser.add_argument("--base-url", default=BASE_URL)
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    api_key = get_api_key()
    if not api_key:
        print("ERROR: 找不到 WORLDLINE_API_KEY，請設定環境變數或確認 .env 存在。", file=sys.stderr)
        sys.exit(1)
    headers = {"X-API-Key": api_key}

    created_ids = {}  # name -> bio_id

    for bio_data in BIOS:
        check_date = bio_data.pop("_check_date", None)
        create_leader_spec = bio_data.pop("_create_leader", None)

        name = bio_data["name"]

        # ── 確認同名生平是否已透過 /leaders 連結（已連結代表 bio 已存在且已連結任期） ──
        already_linked_bio_id = None
        if check_date:
            features = get_features_on_date(base, check_date)
            f = features.get(name)
            if f and f.get("personId"):
                already_linked_bio_id = f["personId"]
                print(f"[SKIP] {name} 已在 {check_date} 有連結 bio，personId={already_linked_bio_id}")
                created_ids[name] = already_linked_bio_id
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

        # ── 嘗試連結現有任期紀錄 ──
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
                # 沒找到同名任期紀錄，若有 _create_leader spec 則建立
                if create_leader_spec:
                    spec = dict(create_leader_spec)
                    regime_slug = spec.pop("_regimeSlug")
                    regime_id = get_regime_id_by_slug(base, regime_slug, spec["validFrom"])
                    if not regime_id:
                        print(f"[WARN] 找不到 {regime_slug} 的 regimeId，無法建立 leader_record for {name}", file=sys.stderr)
                    else:
                        spec["regimeId"] = regime_id
                        spec["name"] = name
                        spec["nameZh"] = bio_data.get("nameZh")
                        spec["personId"] = bio_id
                        rec_body, rec_status = post_json(f"{base}/api/v1/leader-records", spec, headers)
                        if rec_status == 201:
                            rec_id = rec_body["data"]["id"]
                            print(f"[OK] POST /leader-records → {rec_id}  ({name}, regimeId={regime_id})")
                        else:
                            print(f"[FAIL] POST /leader-records status={rec_status}: {rec_body}", file=sys.stderr)
                else:
                    print(f"[INFO] {check_date} 無 {name} 的在任紀錄，且無 _create_leader 規格，跳過連結")

    print("\n--- 寫入的生平 id ---")
    for n, bio_id in created_ids.items():
        print(f"{bio_id}  ({n})")


if __name__ == "__main__":
    main()
