"""v2.2 量測：headless Chrome 的 rAF 幀間隔。
兩種情境、分開記錄：
  playback ：從 5/10 以 1x 播到 6/4（約 30 秒），自動鏡頭。
  zoompan  ：從 5/20 播放中，腳本化縮放／平移（easeTo：放大→平移→拉遠→平移→放大，約 14 秒），自動鏡頭被打斷。
裝置：desktop 1440×900、mobile 390×844（DPR 3，地圖 pixelRatio 上限 2）；CPU 降速 1x、2x。
另錄 30 秒 webm（含縮放與平移段）。用法：python tools/measure.py [--no-video] [--only desktop|mobile] [--throttle 1,2]"""
import asyncio, json, sys, statistics, shutil, platform
from playwright.async_api import async_playwright
BASE='http://localhost:8765/index.html'
CFG=[('desktop',{'width':1440,'height':900},{'device_scale_factor':1}),
     ('mobile',{'width':390,'height':844},{'device_scale_factor':3,'is_mobile':True,'has_touch':True})]
args=sys.argv[1:]
ONLY=args[args.index('--only')+1] if '--only' in args else None
THROTTLE=[int(x) for x in (args[args.index('--throttle')+1] if '--throttle' in args else '1,2').split(',')]
HEADLESS='--headless' in args
SCEN=(args[args.index('--scen')+1] if '--scen' in args else 'playback,zoompan').split(',')
def stats(dts):
    dts=[d for d in dts if d>0]; s=sorted(dts); n=len(s)
    pct=lambda q: s[min(n-1,int(q*n))]
    worst1=s[int(n*0.99):] or s[-1:]
    return {'frames':n,'seconds':round(sum(dts)/1000,2),'avg_fps':round(1000/statistics.mean(dts),1),
            'p1_low_fps':round(1000/pct(0.99),1),'p5_low_fps':round(1000/pct(0.95),1),
            'one_percent_low_avg_fps':round(1000/statistics.mean(worst1),1),'min_fps':round(1000/s[-1],1),
            'frame_ms_p50':round(pct(0.5),2),'frame_ms_p99':round(pct(0.99),2),'frame_ms_max':round(s[-1],2),
            'frames_over_20ms':sum(1 for d in s if d>20)}
ZOOMPAN = """async (mob) => { const m = window.__map; window.__unfollow(); const w = ms => new Promise(r => setTimeout(r, ms));
  const c0 = m.getCenter(), z0 = m.getZoom(); const zs = mob ? [8.2, 6.0, 7.6] : [9.0, 6.6, 8.4];
  m.easeTo({ zoom: zs[0], center: [2.4, 50.95], duration: 2500 }); await w(2700);
  m.panBy([mob ? 160 : 380, mob ? 120 : 160], { duration: 1600 }); await w(1800);
  m.easeTo({ zoom: zs[1], duration: 2600 }); await w(2800);
  m.panBy([mob ? -140 : -420, mob ? -100 : -120], { duration: 1600 }); await w(1800);
  m.easeTo({ zoom: zs[2], center: [4.9, 49.9], duration: 2400 }); await w(2600);
  m.easeTo({ zoom: z0, center: c0, duration: 1800 }); await w(2000); return [m.getZoom()]; }"""
async def run(video):
    out={'method':'requestAnimationFrame 間隔取樣（頁面主迴圈），有視窗的 Google Chrome（私有 Xvfb）；地圖為 MapLibre GL JS（WebGL）。這台 box 沒有 GPU，WebGL 由 Mesa llvmpipe 軟體模擬，數字偏保守，不代表一般有 GPU 的電腦或手機。',
         'scenarios':{'playback':'從 5/10 以 1x 播到 6/4（約 30 秒），自動鏡頭','zoompan':'5/20 起播放中，腳本化 easeTo 放大／平移／拉遠／平移／放大（約 14 秒）'},
         'browser':None,'warmup':'每種裝置量測前先在同一瀏覽器暖機播放 6 秒（冷啟動數字見 cold_start）','mode':'headed Chrome on private Xvfb (GPU compositing via Mesa llvmpipe)','host':platform.platform(),'runs':[]}
    try: old=json.load(open('fps.json'))
    except Exception: old=None
    async with async_playwright() as p:
        # 用「有視窗」的 Chrome 跑在私有 Xvfb 上：合成走 GPU 路徑（SwiftShader），和一般桌機瀏覽器相同；
        # headless 模式的軟體合成器每幀要把 WebGL 畫面 ReadPixels 讀回 CPU，會把數字壓到約 26 fps，不具代表性。
        b=await p.chromium.launch(channel='chrome', headless=HEADLESS, args=['--ignore-gpu-blocklist'])
        out['browser']=b.version; out['mode']='headless' if HEADLESS else out['mode']
        for (name,vp,extra) in CFG:
          if ONLY and name!=ONLY: continue
          # 暖機：同一個瀏覽器先開一次頁面播 6 秒（第一次開頁時 GPU 行程要編譯著色器、建字型快取，前幾秒會掉幀；這是一次性的冷啟動成本，另記在 cold_start）
          wctx=await b.new_context(viewport=vp,**extra); wpg=await wctx.new_page(); await wpg.goto(BASE); await wpg.wait_for_function('window.__ready===true',timeout=60000)
          await wpg.evaluate("window.__bench.start(); document.querySelector('#btn-play').click()"); await wpg.wait_for_timeout(6000)
          wr=await wpg.evaluate('window.__bench.stop()'); out.setdefault('cold_start',{})[name]={'first_6s_frames':len(wr['dts']),'first_6s_over_20ms':sum(1 for d in wr['dts'] if d>20)}; await wctx.close()
          for scen in SCEN:
           for th in THROTTLE:
            ctx=await b.new_context(viewport=vp,**extra); pg=await ctx.new_page()
            if th>1:
                cdp=await ctx.new_cdp_session(pg); await cdp.send('Emulation.setCPUThrottlingRate',{'rate':th})
            q='?date=1940-05-20' if scen=='zoompan' else ''
            await pg.goto(BASE+q); await pg.wait_for_function('window.__ready===true',timeout=60000); await pg.wait_for_timeout(1000)
            if scen=='playback':
                await pg.evaluate("window.__bench.start(); document.querySelector('#btn-play').click()"); await pg.wait_for_timeout(31500)
            else:
                await pg.evaluate("window.__bench.start(); document.querySelector('#btn-play').click()")
                await pg.evaluate(ZOOMPAN, name=='mobile')
            res=await pg.evaluate('window.__bench.stop()'); dts=res['dts']
            renderer=await pg.evaluate("(()=>{const gl=__map.painter.context.gl;const e=gl.getExtension('WEBGL_debug_renderer_info');return e?gl.getParameter(e.UNMASKED_RENDERER_WEBGL):'?'})()")
            labels=await pg.evaluate('window.__labels')
            overlap=any(abs(a['x']-b2['x'])<(a['w']+b2['w'])/2 for i,a in enumerate(labels) for b2 in labels[i+1:])
            r={'mode':'headless' if HEADLESS else 'headed-xvfb','scenario':scen,'name':name,'cpu_throttle':th,'viewport':vp,'device_scale_factor':extra.get('device_scale_factor'),**stats(dts),
               'webgl_renderer':renderer,'timeline_label_overlap':overlap,
               'blur_fallback_triggered':await pg.evaluate('!!window.__blurFallback'),'pixel_ratio_fallback':await pg.evaluate('window.__prFallback||null'),
               'slow_frames_sample':res['slow'][:12],'slow_frames_by_day':{str(k):sum(1 for s in res['slow'] if int(s[0])==k) for k in range(26)}}
            out['runs'].append(r); print(json.dumps({k:v for k,v in r.items() if k!='slow_frames_sample'},ensure_ascii=False)); await ctx.close()
        if video:
            for name,vp,extra in CFG:
                if ONLY and name!=ONLY: continue
                ctx=await b.new_context(viewport=vp,record_video_dir='/tmp/vid_'+name,record_video_size=vp,**extra); pg=await ctx.new_page()
                await pg.goto(BASE); await pg.wait_for_function('window.__ready===true',timeout=60000); await pg.wait_for_timeout(800)
                await pg.evaluate("document.querySelector('#btn-play').click()"); await pg.wait_for_timeout(15500)   # 約到 5/23
                mob = name=='mobile'
                await pg.evaluate("""async (mob) => { const m = window.__map; window.__unfollow(); const w = ms => new Promise(r => setTimeout(r, ms));
                  m.easeTo({ zoom: mob ? 8.0 : 8.8, center: [1.95, 50.85], duration: 2200 }); await w(2600);
                  m.panBy([mob ? -120 : -300, mob ? 60 : 120], { duration: 1500 }); await w(1900);
                  m.easeTo({ zoom: mob ? 6.0 : 6.6, duration: 2000 }); await w(2400); }""", mob)
                await pg.evaluate("document.querySelector('#follow').click()"); await pg.wait_for_timeout(8000)
                path=await pg.video.path(); await ctx.close(); shutil.move(path, f'{name}-30s.webm')
        await b.close()
    if old and (ONLY or len(THROTTLE)<2 or len(SCEN)<2):   # 部分重跑：合併舊結果
        keep=[r for r in old.get('runs',[]) if not any(r.get('mode')==n['mode'] and r.get('scenario')==n['scenario'] and r['name']==n['name'] and r['cpu_throttle']==n['cpu_throttle'] for n in out['runs'])]
        out['runs']=keep+out['runs']
    json.dump(out,open('fps.json','w'),ensure_ascii=False,indent=1)
asyncio.run(run('--no-video' not in args))
