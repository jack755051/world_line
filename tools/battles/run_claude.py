"""claude -p 包裝：撞到 5 小時用量上限時等到重置時間，再 --resume 接續（不中斷）。由 .dev/battle/poland/run_cc.py 複製一般化。
用法：python3 -I tools/battles/run_claude.py <task.md> <out-prefix> <budget-usd> [--cwd 目錄] [--map-reader]
  --cwd        claude 工作目錄（預設 repo 根；獨立判讀時給隔離資料夾）
  --map-reader 只給讀圖工具（Read/Write/Edit/Glob、sips、swift、python3、mkdir、ls），禁網路
輸出 <out-prefix>.N.json（每段）、<out-prefix>.final.json（累計花費、段數、session）。
"""
import datetime, json, re, subprocess, sys, time
from pathlib import Path
task, pref, budget = sys.argv[1], sys.argv[2], float(sys.argv[3])
CWD = sys.argv[sys.argv.index("--cwd") + 1] if "--cwd" in sys.argv else str(Path(__file__).resolve().parents[2])
TOOLS = "Read,Write,Edit,Glob,Bash(sips:*),Bash(swift:*),Bash(python3:*),Bash(mkdir:*),Bash(ls:*)" if "--map-reader" in sys.argv else "Read,Write,Edit,Glob,Grep,Bash(python3:*),Bash(ls:*),Bash(mkdir:*),Bash(sips:*),Bash(swift:*),Bash(grep:*),Bash(curl -s:*),Bash(pdftotext:*),WebFetch"
DENY = (["Bash(rm:*)", "Bash(mv:*)", "WebFetch", "WebSearch"] if "--map-reader" in sys.argv else None) or ["Bash(rm:*)", "Bash(git:*)", "Bash(curl -k:*)", "Bash(mv:*)", "WebSearch"]
spent, sid, n = 0.0, None, 0
prompt = open(task).read()
while True:
    n += 1
    cmd = ["claude", "-p", prompt if sid is None else "上一段因用量上限中斷。請從中斷處接續完成原任務（先檢查已寫出的檔案，不要重做已完成的部分）。",
           "--max-budget-usd", f"{max(budget - spent, 0.3):.2f}", "--output-format", "json", "--permission-mode", "acceptEdits",
           "--allowedTools", TOOLS, "--disallowedTools", *DENY]
    if sid: cmd += ["--resume", sid]
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=CWD)
    open(f"{pref}.{n}.json", "w").write(p.stdout); open(f"{pref}.{n}.err", "w").write(p.stderr)
    try:
        d = json.loads(p.stdout)
    except Exception:
        print("無法解析輸出", p.stdout[:300], p.stderr[:300]); break
    spent += d.get("total_cost_usd") or 0; sid = d.get("session_id") or sid
    res = str(d.get("result") or "")
    m = re.search(r"hit your .*?limit.*?resets\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)", res, re.I | re.S)
    print(f"[{datetime.datetime.now():%H:%M}] 第 {n} 段 花費累計 ${spent:.2f}；{res[:120]!r}", flush=True)
    if m and spent < budget:
        h = int(m.group(1)) % 12 + (12 if m.group(3).lower() == "pm" else 0); mi = int(m.group(2) or 0)
        now = datetime.datetime.now(); t = now.replace(hour=h, minute=mi, second=0, microsecond=0)
        if t <= now: t += datetime.timedelta(days=1)
        wait = (t - now).total_seconds() + 120
        print(f"等用量重置到 {t:%H:%M}（{wait/60:.0f} 分）", flush=True); time.sleep(wait); continue
    break
json.dump({"spent": spent, "segments": n, "session": sid, "result": res}, open(f"{pref}.final.json", "w"), ensure_ascii=False, indent=1)
print(f"完成：${spent:.2f}")
