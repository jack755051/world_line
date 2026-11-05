#!/usr/bin/env python3
"""ARCHITECTURE.md §9 遷移步驟 2 驗收：boundary_periods／label_points 與第 1 層 API 比對。

日期：/timeline/change-points 的全部變動日，加 50 個隨機日（固定種子，範圍＝最早變動日到最晚變動日）。
每個日期比對：
  1. 政權集合（regime_id）：boundary_periods（start_day <= d AND end_day > d）＝ API /sovereignty?date=d
  2. 主權紀錄集合（record_id）也要一致（更嚴格）
  3. label_points：每個政權在該日恰好一個國名點，且政權集合同上
用法：python3 tools/tiles/compare.py [--api http://127.0.0.1:5052] [--container worldline-borders-dev-db] [--random 50] [--seed 20261104]
資料庫只讀（docker exec psql）；結果寫到 tools/tiles/out/compare.json。
"""
import argparse, datetime as dt, json, os, random, subprocess, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
EPOCH = dt.date(1900, 1, 1)


def psql(container, sql):
    env = lambda k: subprocess.check_output(['docker', 'exec', container, 'printenv', k], text=True).strip()
    u, d = env('POSTGRES_USER'), env('POSTGRES_DB')
    out = subprocess.run(['docker', 'exec', '-i', container, 'psql', '-U', u, '-d', d, '-v', 'ON_ERROR_STOP=1', '-At', '-F', '\t'],
                         input=sql, capture_output=True, text=True)
    if out.returncode: sys.exit(out.stderr)
    return [l.split('\t') for l in out.stdout.splitlines() if l]


def get(url):
    with urllib.request.urlopen(url, timeout=120) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--api', default='http://127.0.0.1:5052')
    ap.add_argument('--container', default='worldline-borders-dev-db')
    ap.add_argument('--random', type=int, default=50)
    ap.add_argument('--seed', type=int, default=20261104)
    a = ap.parse_args()

    points = get(f'{a.api}/api/v1/timeline/change-points')['data']['points']
    lo, hi = dt.date.fromisoformat(points[0]), dt.date.fromisoformat(points[-1])
    rnd = random.Random(a.seed)
    extra = set()
    while len(extra) < a.random:
        d = lo + dt.timedelta(days=rnd.randrange((hi - lo).days + 1))
        if d.isoformat() not in points: extra.add(d.isoformat())
    dates = [(d, 'change') for d in points] + [(d, 'random') for d in sorted(extra)]
    days = {d: (dt.date.fromisoformat(d) - EPOCH).days for d, _ in dates}

    label_sql = open(os.path.join(HERE, 'sql', 'label_points.sql')).read()
    vals = ','.join(f"('{d}',{n})" for d, n in days.items())
    rows = psql(a.container, f"""
        CREATE TEMP TABLE q(d text, day int); INSERT INTO q VALUES {vals};
        CREATE TEMP TABLE lp AS {label_sql};
        SELECT 'bp', q.d, b.regime_id, b.record_id FROM q JOIN boundary_periods b ON b.start_day <= q.day AND b.end_day > q.day;
        SELECT 'lp', q.d, l.regime_id, l.record_id FROM q JOIN lp l ON l.start_day <= q.day AND l.end_day > q.day;
        SELECT 'lpn', count(*), count(*) FILTER (WHERE name IS NULL), count(*) FILTER (WHERE geom IS NULL OR ST_IsEmpty(geom)) FROM lp;
    """)
    view, labels = {}, {}
    lp_stats = None
    for r in rows:
        if r[0] == 'bp': view.setdefault(r[1], []).append((r[2], r[3]))
        elif r[0] == 'lp': labels.setdefault(r[1], []).append(r[2])
        elif r[0] == 'lpn': lp_stats = dict(total=int(r[1]), no_name=int(r[2]), no_point=int(r[3]))

    bad = []
    for d, kind in dates:
        feats = get(f'{a.api}/api/v1/sovereignty?date={d}&zoom=3')['data']['featureCollection']['features']
        api_reg = sorted(f['properties']['regimeId'] for f in feats)
        api_rec = sorted(f['properties']['recordId'] for f in feats)
        v = view.get(d, [])
        v_reg, v_rec = sorted(x[0] for x in v), sorted(x[1] for x in v)
        l_reg = sorted(labels.get(d, []))
        problems = []
        if set(api_reg) != set(v_reg): problems.append(dict(regimes_only_api=sorted(set(api_reg) - set(v_reg)), regimes_only_view=sorted(set(v_reg) - set(api_reg))))
        if api_rec != v_rec: problems.append('record set differs')
        if len(set(v_reg)) != len(v_reg): problems.append('same regime twice in view')
        if l_reg != sorted(set(api_reg)): problems.append(dict(labels=len(l_reg), regimes=len(set(api_reg))))
        if problems: bad.append(dict(date=d, kind=kind, problems=problems))

    res = dict(checked=len(dates), change_days=len(points), random_days=len(extra), seed=a.seed, mismatches=len(bad),
               label_points=lp_stats, first_mismatches=bad[:20],
               at=dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec='seconds'))
    os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
    json.dump(res, open(os.path.join(HERE, 'out', 'compare.json'), 'w'), ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
