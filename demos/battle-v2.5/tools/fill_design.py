import json
d=json.load(open('fps.json'))
SC={'playback':'播放','zoompan':'縮放／平移'}
rows=['| 裝置 | 情境 | CPU 降速 | 平均 fps | 1% low（p99 幀時間） | 最差 1% 平均 | 最低 | >20ms 幀數 | 自動降級 |','|---|---|---|---|---|---|---|---|---|']
runs=sorted([r for r in d['runs'] if r.get('mode','headed-xvfb')!='headless'],key=lambda r:(r['name'],r['scenario'],r['cpu_throttle']))
for r in runs:
    fb='、'.join(x for x in [('毛玻璃' if r.get('blur_fallback_triggered') else ''),(f"解析度×{r['pixel_ratio_fallback']}" if r.get('pixel_ratio_fallback') else '')] if x) or '無'
    rows.append(f"| {r['name']} {r['viewport']['width']}×{r['viewport']['height']}（DPR {r['device_scale_factor']}） | {SC.get(r['scenario'],r['scenario'])} | {r['cpu_throttle']}x | {r['avg_fps']} | {r['p1_low_fps']} | {r['one_percent_low_avg_fps']} | {r['min_fps']} | {r['frames_over_20ms']}／{r['frames']} | {fb} |")
cs=d.get('cold_start',{})
extra=f"\n\n  瀏覽器：Chrome {d['browser']}；模式：{d.get('mode')}；WebGL：{runs[0].get('webgl_renderer') if runs else '?'}；時間軸標籤重疊：{'有' if any(r.get('timeline_label_overlap') for r in runs) else '無'}。"
if cs: extra+="\n  冷啟動（暖機那 6 秒，不算進上表）："+'；'.join(f"{k} {v['first_6s_over_20ms']}／{v['first_6s_frames']} 幀 >20ms" for k,v in cs.items())+'。'
rr=d.get('repeat_runs',[])
if rr: extra+="\n  桌機播放 1x 重跑（同一台共用 box，結果差很多）："+'；'.join(f"{r['note']}：平均 {r['avg_fps']}、1% low {r['p1_low_fps']}、{r['frames_over_20ms']}／{r['frames']} 幀 >20ms" for r in rr)+'。'
js=d.get('js_render_ms')
if js: extra+=f"\n  兩個 custom layer 每幀的 JS 時間（p50／p99 ms）：全戰區 battle {js['overview_battle_p50_p99']}、terr {js['overview_terr_p50_p99']}；9 級 battle {js['z9_battle_p50_p99']}、terr {js['z9_terr_p50_p99']}。瓶頸在軟體點陣化（llvmpipe 用 CPU 畫像素，和其他程式搶 CPU），不在 JS。"
t=open('design.md.tmpl').read().replace('{FPS_TABLE}','\n'.join('  '+x for x in rows)+extra)
open('design.md','w').write(t)
print('\n'.join(rows)+extra)
