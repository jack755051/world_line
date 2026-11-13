"""已移到共用工具 tools/battles/georef.py（Tai 2026-11-13 13:39 流程修正第 2 項）；本檔只是轉呼叫的薄包裝，不再含配準程式。
規則禁刪檔，故保留此檔名以免舊指令失效。設定在 ../georef.config.json。

用法（與舊版相容）：python3 -I georef_ellis.py ../digitized/<mapKey>.readings.json [--frame-km N]
       或直接：    python3 -I tools/battles/georef.py dunkirk_1940 [mapKey ...]
"""
import runpy, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0].endswith(".readings.json"):
        key = Path(args[0]).name[:-len(".readings.json")]
        args = ["dunkirk_1940", key]  # frame-km 改由 georef.config.json 決定
    sys.argv = [str(REPO / "tools/battles/georef.py")] + args
    runpy.run_path(sys.argv[0], run_name="__main__")
