"""compare-MMDD.png：左 v2.0（_v2.0/ 重建）、右 v2.1；上排桌機，下排手機。"""
import sys
from PIL import Image, ImageDraw, ImageFont
F='/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
def font(sz):
    try: return ImageFont.truetype(F, sz, index=2)
    except Exception: return ImageFont.load_default()
for d in sys.argv[1:]:
    dl=Image.open(f'_v2.0/desktop-{d}.png').convert('RGB'); dr=Image.open(f'desktop-{d}.png').convert('RGB')
    ml=Image.open(f'_v2.0/mobile-{d}.png').convert('RGB'); mr=Image.open(f'mobile-{d}.png').convert('RGB')
    s=0.5; dw,dh=int(dl.width*s),int(dl.height*s); mh=dh; mw=int(ml.width*mh/ml.height)
    pad=16; head=56; W=dw*2+pad*3; H=head+dh+pad+mh+pad*2
    out=Image.new('RGB',(W,H),(18,20,24)); g=ImageDraw.Draw(out)
    for col,(a,b,label) in enumerate([(dl,ml,'v2.0（舊：火花、爆裂、全部同強度）'),(dr,mr,'v2.1（醋酸片圖層＋焦點強調＋平靜交戰記號）')]):
        x=pad+col*(dw+pad); g.text((x,14),label,font=font(24),fill=(233,228,216))
        out.paste(a.resize((dw,dh)),(x,head)); out.paste(b.resize((mw,mh)),(x+(dw-mw)//2,head+dh+pad))
    g.text((W-pad-560,H-30),f'1940-{d[:2]}-{d[2:]}｜示例，非史料｜上：桌機 1440×900　下：手機 390×844',font=font(16),fill=(170,177,184))
    out.save(f'compare-{d}.png'); print('ok',d,out.size)
