"""v2.2 截圖：python tools/shoot.py [only-name ...]（需先在 8765 埠開靜態伺服器）
一般日期截圖用自動鏡頭；縮放序列／局部用 ?view=lng,lat,z（會停止跟隨鏡頭）。手機 zoom 自動 −0.9。"""
import sys, asyncio
from playwright.async_api import async_playwright
BASE='http://localhost:8765/index.html'
SHOTS=[(f'{d[5:].replace("-","")}', f'date={d}', None) for d in ['1940-05-10','1940-05-13','1940-05-20','1940-05-21','1940-05-26','1940-06-04']]
SHOTS+=[('zoom-1-overview','date=1940-05-26',(2.9,50.6,5.5)),
        ('zoom-2-corps','date=1940-05-26',(2.7,50.85,6.8)),
        ('zoom-3-division','date=1940-05-26',(2.55,50.95,8.3)),
        ('meuse-0513','date=1940-05-13',(4.95,49.85,8.4)),
        ('sedan-0516','date=1940-05-16',(4.4,49.75,7.6)),
        ('sedan-0517','date=1940-05-17',(4.0,49.8,7.4)),
        ('pockets-0524','date=1940-05-24',(1.9,50.85,8.2)),
        ('pockets-0528','date=1940-05-28',(2.6,50.8,7.6))]
ONLY=sys.argv[1:]
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(channel='chrome', args=['--ignore-gpu-blocklist'])
        for name, vp, extra in [('desktop',{'width':1440,'height':900},{}),('mobile',{'width':390,'height':844},{'device_scale_factor':3,'is_mobile':True,'has_touch':True})]:
            ctx = await b.new_context(viewport=vp, **extra); pg = await ctx.new_page()
            errs=[]; pg.on('console', lambda m: m.type=='error' and errs.append(m.text)); pg.on('pageerror', lambda e: errs.append(str(e)))
            for tag,q,view in SHOTS:
                if ONLY and tag not in ONLY: continue
                if view:
                    z=view[2]-(0.9 if name=='mobile' else 0); q+=f'&view={view[0]},{view[1]},{z:.2f}'
                await pg.goto(f'{BASE}?{q}'); await pg.wait_for_function('window.__ready===true',timeout=60000)
                await pg.evaluate("document.querySelector('#event').style.display='none'")
                await pg.wait_for_timeout(1200)
                await pg.screenshot(path=f'{name}-{tag}.png')
            print(name, 'errors:', errs[:5])
            await ctx.close()
        await b.close()
asyncio.run(main())
