"""快速截圖：python tools/peek.py out.png 'query' [mobile]"""
import asyncio, sys
from playwright.async_api import async_playwright
async def m():
  out, qs = sys.argv[1], sys.argv[2]; mob = len(sys.argv) > 3
  async with async_playwright() as p:
    b=await p.chromium.launch(channel='chrome',args=['--ignore-gpu-blocklist'])
    ctx=await b.new_context(**({'viewport':{'width':390,'height':844},'device_scale_factor':3,'is_mobile':True,'has_touch':True} if mob else {'viewport':{'width':1440,'height':900}}))
    pg=await ctx.new_page(); e=[]
    pg.on('console',lambda m: m.type=='error' and e.append(m.text)); pg.on('pageerror',lambda x:e.append('PE '+str(x)))
    await pg.goto('http://localhost:8765/index.html?'+qs); await pg.wait_for_function('window.__ready===true',timeout=20000)
    await pg.evaluate("document.querySelector('#event').style.display='none'")
    await pg.wait_for_timeout(1200); await pg.screenshot(path=out); print(e[:6], await pg.evaluate('window.__state()'))
    await b.close()
asyncio.run(m())
