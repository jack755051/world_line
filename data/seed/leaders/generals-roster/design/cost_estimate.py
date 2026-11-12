#!/usr/bin/env python3
"""人物事實分層（ARCHITECTURE §20.10）費用估算。唯讀：只讀 stats.json、../bios/selection.json，結果印到 stdout，不寫任何檔。
用法：python3 -I cost_estimate.py
所有「比例」是假設（見 §20.10 表），金額一律由 stats.json 的實際數字乘出。"""
import json, os, collections

HERE = os.path.dirname(os.path.abspath(__file__))
st = json.load(open(os.path.join(HERE, "stats.json"), encoding="utf-8"))
sel = json.load(open(os.path.join(HERE, "..", "bios", "selection.json"), encoding="utf-8"))
cost = st["cost"]
AVG = {"S": cost["S_usdPerPerson"], "A": cost["A_usdPerPerson"]}          # 整人（主迴圈 sonnet＋retry）平均
cat = cost["byCategory"]
RETRY_SHARE = {"S": cat["S-retry"]["usd"] / (cat["S-sonnet"]["usd"] + cat["S-retry"]["usd"]),
               "A": cat["A-retry"]["usd"] / (cat["A-sonnet"]["usd"] + cat["A-retry"]["usd"])}

# 未達標原因 → 互斥類別（優先序 C4 > C2 > C1 > C3 > C5）
def klass(reasons):
    r = set(reasons)
    if r & {"段落<3", "字數<300"}:
        return "C4 段落／字數不足"
    if "職位缺起訖" in r and "無戰役" in r and "無指揮職" not in r:
        return "C2 缺任期＋缺戰役"
    if r == {"職位缺起訖"}:
        return "C1 只缺任期"
    if r == {"無戰役"}:
        return "C3 只缺戰役"
    return "C5 含無指揮職（其餘為任期／戰役）"

# 相對「整人重跑」的成本比例（假設，理由見 §20.10）：低／中／高
RATIO = {
    "C1 只缺任期": (0.15, 0.30, 0.50),
    "C2 缺任期＋缺戰役": (0.25, 0.45, 0.65),
    "C3 只缺戰役": (0.15, 0.30, 0.50),
    "C4 段落／字數不足": (0.60, 0.85, 1.00),
    "C5 含無指揮職（其餘為任期／戰役）": (0.05, 0.25, 0.50),
}

cnt = {t: collections.Counter() for t in "SA"}
for f in st["failing"]:
    cnt[f["tier"]][klass(f["reasons"])] += 1

print("## 未達標分類（stats.json failing，%d 人）" % len(st["failing"]))
print("| 類別 | S | A | 合計 |\n|---|---|---|---|")
for k in RATIO:
    print(f"| {k} | {cnt['S'][k]} | {cnt['A'][k]} | {cnt['S'][k]+cnt['A'][k]} |")
print(f"| 合計 | {sum(cnt['S'].values())} | {sum(cnt['A'].values())} | {sum(cnt['S'].values())+sum(cnt['A'].values())} |")

print("\n## 103 人按欄位補跑（元）\n| 檔 | 公式 | USD |\n|---|---|---|")
base_full = sum(cnt[t][k] * AVG[t] for t in "SA" for k in RATIO)
print(f"| 整人重跑（對照） | Σ 人數×每人平均（S {AVG['S']}、A {AVG['A']}） | {base_full:.2f} |")
for i, name in enumerate(("低", "中", "高")):
    tot = sum(cnt[t][k] * AVG[t] * RATIO[k][i] for t in "SA" for k in RATIO)
    print(f"| {name} | Σ 人數×每人平均×比例 | {tot:.2f} |")
print("\n（含已有舊補跑成本者＝不計；insuff-S 補跑 2 檔 $%.4f 已在累計內）" % cat["insuff-S-sonnet"]["usd"])

# 尚未跑的 A
a_run = collections.Counter(p["country"] for b in sel["A"] for p in b["people"])
n_run = sum(a_run.values())
done = 75
rem = n_run - done
print(f"\n## 尚未跑的 A：selection.json A_run {n_run} − min-check 已跑 {done} = {rem}")
fp = AVG["A"] * (1 - RETRY_SHARE["A"])
print(f"A retry 占比 = {cat['A-retry']['usd']}/({cat['A-sonnet']['usd']}+{cat['A-retry']['usd']}) = {RETRY_SHARE['A']:.3f}；首跑估每人 {fp:.3f}")
print(f"舊規則：{rem}×{AVG['A']} = {rem*AVG['A']:.2f}（累計 {cost['totalUsd']} → {cost['totalUsd']+rem*AVG['A']:.2f}，上限 340）")
dist = {k: cnt["A"][k] / done for k in RATIO}
# 新規則下哪些類別仍需補（低：只補 C2、C3、C4；中：再補 C1 與 C5；高：全補且比例取高檔）
need = {0: ["C2 缺任期＋缺戰役", "C3 只缺戰役", "C4 段落／字數不足"],
        1: list(RATIO), 2: list(RATIO)}
L1_EXTRA = (0.0, 0.03, 0.06)   # L1 典據 ID 查詢額外成本（每人，假設）
print("| 檔 | 首跑 | 補跑 | L1 典據（假設） | 合計 | 累計後 |\n|---|---|---|---|---|---|")
for i, name in enumerate(("低", "中", "高")):
    patch = sum(dist[k] * RATIO[k][i] * AVG["A"] for k in need[i])
    tot = rem * (fp + patch + L1_EXTRA[i])
    print(f"| {name} | {rem*fp:.2f} | {rem*patch:.2f} | {rem*L1_EXTRA[i]:.2f} | {tot:.2f} | {cost['totalUsd']+tot:.2f} |")
print("\n剩餘 A 的國別（A_run 減 stats.json persons 的 A 已跑）：")
d = collections.Counter(p["country"] for p in st["persons"] if p["tier"] == "A")
print({c: a_run[c] - d.get(c, 0) for c in a_run if a_run[c] - d.get(c, 0)})
print("stats.json persons 的 A 筆數 =", sum(d.values()), "（與 min-check 75 差 %d）" % (sum(d.values()) - done))
