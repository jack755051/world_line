"""產生 data/dunkirk-1940.example.json（示例，非史料，schema v2：多重多邊形控制區＋包圍圈）並做自動陸地檢查。
- 地面部隊、交戰、前線頂點（非 sea 錨點）必須落在 Natural Earth 1:10m 陸地上。
- 海軍單位、海軍箭頭中段必須在海上；sea 錨點必須在海上。
- 失敗就 exit 1。用法：python tools/build_data.py
"""
import json, sys, math
from shapely.geometry import shape, Point, Polygon, MultiPolygon, mapping, box
from shapely.ops import unary_union
LAND = shape(json.load(open('battles/dunkirk-1940-example/geo/land.geojson'))['features'][0]['geometry'])
KEYS = ['1940-05-10','1940-05-12','1940-05-13','1940-05-15','1940-05-17','1940-05-20',
        '1940-05-21','1940-05-24','1940-05-26','1940-05-28','1940-05-31','1940-06-04']
def K(md): return '1940-'+md
S='s'  # sea anchor flag
# ---------------- 前線鏈（北→南，軸心控制區在鏈的東側）----------------
BORDER_SOUTH = [(6.52,49.53),(6.36,49.46),(6.73,49.17),(7.1,49.15),(7.6,49.08),(8.2,48.97),(7.8,48.55),(7.58,48.1),(7.58,47.6),(7.6,47.0)]
SOMME_TO_BORDER = [(1.75,50.05),(1.95,50.04),(2.2,49.86),(2.5,49.86),(2.93,49.9),(3.07,49.75),(3.3,49.6),(3.6,49.5),(4.0,49.45),
                   (4.37,49.48),(4.92,49.52),(5.3,49.52),(5.76,49.5),(6.0,49.45)] + BORDER_SOUTH
FRONTS = {
 '05-10': [(6.9,54.0,S),(7.21,53.25),(7.05,52.65),(6.7,52.48),(6.98,52.22),(6.75,52.05),(6.4,51.85),(6.0,51.82),(6.2,51.45),(6.05,51.2),
           (5.98,50.98),(6.05,50.75),(6.27,50.6),(6.4,50.32),(6.13,50.15),(6.4,49.82)] + BORDER_SOUTH,
 '05-12': [(5.0,53.7,S),(5.35,53.05),(5.6,52.6),(5.62,52.1),(5.45,51.9),(4.75,51.72),(5.0,51.52),(5.25,51.3),(5.2,51.05),(5.0,50.85),
           (5.08,50.67),(5.2,50.5),(5.0,50.35),(4.95,50.25),(4.86,50.12),(4.78,49.9),(4.98,49.7),(5.3,49.56),(5.76,49.5),(6.0,49.45)] + BORDER_SOUTH,
 '05-13': [(4.3,52.4,S),(4.7,52.1),(4.95,51.95),(4.65,51.7),(4.9,51.55),(5.1,51.3),(4.95,51.05),(4.85,50.9),(4.98,50.65),(5.0,50.45),
           (4.88,50.33),(4.84,50.26),(4.9,50.18),(4.83,50.08),(4.72,49.88),(4.85,49.66),(4.95,49.62),(5.3,49.56),(5.76,49.5),(6.0,49.45)] + BORDER_SOUTH,
 '05-15': [(3.9,52.05,S),(4.18,51.9),(4.4,51.6),(4.55,51.4),(4.6,51.15),(4.68,50.95),(4.62,50.75),(4.72,50.57),(4.85,50.46),(4.68,50.32),
           (4.45,50.18),(4.3,50.0),(4.0,49.75),(4.3,49.56),(4.6,49.56),(4.92,49.55),(5.3,49.52),(5.76,49.5),(6.0,49.45)] + BORDER_SOUTH,
 '05-17': [(3.4,51.75,S),(4.1,51.42),(4.3,51.15),(4.42,50.86),(4.3,50.6),(4.4,50.42),(3.98,50.28),(3.69,50.13),(3.5,50.08),(3.3,49.86),
           (3.65,49.6),(4.0,49.5),(4.37,49.48),(4.92,49.53),(5.3,49.52),(5.76,49.5),(6.0,49.45)] + BORDER_SOUTH,
 '05-20': [(3.4,51.6,S),(3.83,51.3),(3.8,51.05),(3.6,50.85),(3.4,50.6),(3.55,50.36),(3.1,50.3),(2.85,50.24),(2.6,50.24),(2.34,50.17),
           (2.0,50.22),(1.66,50.24),(1.3,50.25,S),(1.3,50.05,S)] + SOMME_TO_BORDER,
 '05-21': [(3.4,51.6,S),(3.83,51.3),(3.8,51.05),(3.6,50.85),(3.4,50.6),(3.55,50.36),(3.1,50.3),(2.88,50.22),(2.66,50.19),(2.4,50.2),
           (2.0,50.32),(1.68,50.38),(1.3,50.38,S),(1.3,50.05,S)] + SOMME_TO_BORDER,
 '05-24': [(3.3,51.5,S),(3.6,51.3),(3.6,51.05),(3.53,50.98),(3.27,50.83),(3.12,50.78),(3.2,50.65),(3.35,50.5),(3.08,50.37),(2.9,50.42),
           (2.8,50.53),(2.64,50.53),(2.4,50.64),(2.25,50.75),(2.21,50.83),(2.15,50.97),(2.05,51.2,S),(1.45,51.15,S),(1.2,50.2,S)] + [(1.55,50.06)] + SOMME_TO_BORDER,
 '05-26': [(3.35,51.45,S),(3.42,51.25),(3.4,51.05),(3.3,51.0),(3.2,50.93),(3.12,50.8),(3.15,50.62),(3.02,50.52),(2.8,50.53),(2.64,50.53),
           (2.4,50.64),(2.25,50.75),(2.21,50.83),(2.15,50.97),(2.05,51.2,S),(1.45,51.15,S),(1.2,50.2,S)] + [(1.55,50.06)] + SOMME_TO_BORDER,
 '05-28': [(2.8,51.3,S),(2.76,51.12),(2.86,51.03),(2.9,50.86),(2.74,50.79),(2.5,50.79),(2.46,50.88),(2.4,50.95),(2.26,50.99),(2.1,51.12,S),
           (1.4,50.9,S),(1.2,50.2,S)] + [(1.55,50.06)] + SOMME_TO_BORDER,
 '05-31': [(2.75,51.3,S),(2.74,51.12),(2.66,51.06),(2.58,50.99),(2.43,50.96),(2.27,51.0),(2.1,51.12,S),(1.4,50.9,S),(1.2,50.2,S)] + [(1.55,50.06)] + SOMME_TO_BORDER,
 '06-04': [(2.6,51.3,S),(2.4,51.15,S),(2.1,51.12,S),(1.4,50.9,S),(1.2,50.2,S)] + [(1.55,50.06)] + SOMME_TO_BORDER,
}
# ---------------- 包圍圈（盟軍據守、被軸心控制區包住的口袋；示例幾何，需查證）----------------
# 每個口袋有固定 id，跨關鍵日形變；某日沒有＝已陷落（渲染時縮回中心）。環可以伸到海上，海面層會蓋掉。
POCKETS = {
 '05-24': [dict(id='pk-boulogne', name_zh='布洛涅包圍圈', side='allied', ring=[(1.50,50.80),(1.66,50.80),(1.71,50.74),(1.68,50.68),(1.56,50.66),(1.48,50.70)]),
           dict(id='pk-calais', name_zh='加萊包圍圈', side='allied', ring=[(1.76,51.03),(1.95,51.02),(1.98,50.94),(1.88,50.89),(1.78,50.91),(1.70,50.97)])],
 '05-26': [dict(id='pk-calais', name_zh='加萊包圍圈', side='allied', ring=[(1.80,51.0),(1.91,50.99),(1.925,50.945),(1.86,50.922),(1.79,50.935),(1.76,50.97)])],
 '05-28': [dict(id='pk-lille', name_zh='里爾包圍圈', side='allied', ring=[(2.92,50.70),(3.10,50.72),(3.20,50.65),(3.15,50.56),(3.0,50.55),(2.9,50.62)])],
 '05-31': [dict(id='pk-lille', name_zh='里爾包圍圈', side='allied', ring=[(2.99,50.67),(3.10,50.68),(3.14,50.63),(3.08,50.585),(2.99,50.595)])],
}
EAST_CLOSE = [(13.0,47.0),(13.0,56.5)]
def control_for(md):
    ch=[(p[0],p[1]) for p in FRONTS[md]]
    main=Polygon(ch+EAST_CLOSE+[(ch[0][0],56.5)]).buffer(0).intersection(box(-6.5,46.0,13.0,56.5))
    ax=main
    for pk in POCKETS.get(md,[]):
        g=Polygon(pk['ring']).buffer(0)
        ax = ax.difference(g) if pk['side']=='allied' else ax.union(g)
    return main, ax
# ---------------- 部隊 ----------------
def sidc(side, branch, ech, dim='G'):
    aff = 'F' if side=='allied' else 'H'
    fn = {'infantry':'UCI---','armor':'UCA---','motorized':'UCIZ--','cavalry':'UCRVA-','air':'MF----','naval':'C-----'}[branch]
    e = {'brigade':'H','division':'I','corps':'J','army':'K'}.get(ech,'-')
    if dim=='A': return f'S{aff}APMF--------'[:15]
    if dim=='S': return f'S{aff}SPC---------'[:15]
    return f'S{aff}GP{fn}-{e}---'
U = []  # (id, side, name_zh, name_orig, echelon, branch, parent, label, level)
def unit(i, side, zh, orig, ech, br, parent=None, label='', level='both', dim='G'):
    U.append(dict(id=i, side=side, name_zh=zh, name_orig=orig, echelon=ech, branch=br, parent_id=parent,
                  label=label, display=level, sidc=sidc(side,br,ech,dim), domain={'G':'ground','A':'air','S':'sea'}[dim]))
P = {}  # id -> {md: (lon,lat,state)}
def pos(i, **kw):
    P[i] = {k[1:].replace('_','-'): v for k,v in kw.items()}
A,Dd,R,M,E,X,V = 'attack','defend','retreat','move','encircled','surrendered','evacuating'
# 軸心
unit('de-18a','axis','第18集團軍','18. Armee','army','infantry',label='18')
pos('de-18a', m05_10=(7.15,52.3,A), m05_12=(5.85,52.15,A), m05_13=(5.25,51.95,A), m05_15=(4.75,51.85,A), m05_17=(4.55,51.4,A), m05_20=(4.05,51.2,M),
    m05_21=(4.0,51.2,M), m05_24=(3.78,51.2,A), m05_26=(3.62,51.2,A), m05_28=(3.1,51.15,A), m05_31=(2.88,51.06,A), m06_04=(2.55,51.0,A))
unit('de-6a','axis','第6集團軍','6. Armee','army','infantry',label='6')
pos('de-6a', m05_10=(6.3,50.82,A), m05_12=(5.45,50.88,A), m05_13=(5.12,50.88,A), m05_15=(4.85,50.78,A), m05_17=(4.6,50.85,A), m05_20=(3.95,50.85,A),
    m05_21=(3.9,50.85,A), m05_24=(3.55,50.9,A), m05_26=(3.38,50.95,A), m05_28=(3.1,50.85,A), m05_31=(2.95,50.9,A), m06_04=(2.75,50.95,M))
unit('de-xvi','axis','第16軍（摩托化）','XVI. Armeekorps (mot.)','corps','armor','de-6a',label='XVI')
pos('de-xvi', m05_10=(6.35,51.02,M), m05_12=(5.22,50.66,A), m05_13=(5.12,50.62,A), m05_15=(4.9,50.55,A), m05_17=(4.5,50.38,A), m05_20=(3.4,50.22,M),
    m05_21=(3.25,50.25,M), m05_24=(2.95,50.33,A), m05_26=(2.9,50.4,A), m05_28=(2.8,50.6,A), m05_31=(2.85,50.15,M), m06_04=(2.7,49.98,M))
unit('de-xv','axis','第15軍（摩托化）','XV. Armeekorps (mot.)','corps','armor','de-4a',label='XV')
pos('de-xv', m05_10=(6.5,50.42,M), m05_12=(5.35,50.25,A), m05_13=(5.02,50.25,A), m05_15=(4.5,50.12,A), m05_17=(3.85,50.08,A), m05_20=(2.95,50.17,A),
    m05_21=(2.85,50.15,Dd), m05_24=(2.6,50.42,A), m05_26=(2.55,50.47,A), m05_28=(2.62,50.68,A), m05_31=(2.4,50.2,M), m06_04=(2.02,50.14,M))
unit('de-7pz','axis','第7裝甲師','7. Panzer-Division','division','armor','de-xv','7',level='detail')
pos('de-7pz', m05_13=(4.93,50.28,A), m05_21=(2.7,50.15,Dd), m05_24=(2.65,50.45,A), m05_26=(2.62,50.48,A), m05_28=(2.72,50.73,A), m05_31=(2.55,50.25,M), m06_04=(2.05,50.02,M))
unit('de-sstk','axis','SS骷髏師（摩托化）','SS-Division Totenkopf','division','motorized','de-xv','SS-T',level='detail')
pos('de-sstk', m05_21=(2.86,50.2,Dd), m05_24=(2.5,50.5,A), m05_26=(2.45,50.56,A), m05_28=(2.55,50.72,A), m05_31=(2.3,50.3,M), m06_04=(2.1,50.15,M))
unit('de-xli','axis','第41軍（摩托化）','XXXXI. Armeekorps (mot.)','corps','armor','de-pgk',label='XLI')
pos('de-xli', m05_10=(6.5,50.1,M), m05_12=(5.05,49.95,A), m05_13=(4.85,49.9,A), m05_15=(4.15,49.74,A), m05_17=(3.6,49.97,A), m05_20=(2.55,50.12,A),
    m05_21=(2.3,50.17,A), m05_24=(2.18,50.66,A), m05_26=(2.15,50.72,A), m05_28=(2.3,50.8,A), m05_31=(2.2,50.4,M), m06_04=(1.85,50.12,M))
unit('de-xix','axis','第19軍（摩托化）','XIX. Armeekorps (mot.)','corps','armor','de-pgk',label='XIX')
pos('de-xix', m05_10=(6.6,49.92,M), m05_12=(5.25,49.75,A), m05_13=(5.02,49.72,A), m05_15=(4.55,49.66,A), m05_17=(3.62,49.8,A), m05_20=(2.1,50.12,A),
    m05_21=(1.95,50.2,A), m05_24=(1.85,50.75,A), m05_26=(1.95,50.85,A), m05_28=(2.08,50.9,A), m05_31=(2.5,49.95,M), m06_04=(2.85,49.9,M))
unit('de-1pz','axis','第1裝甲師','1. Panzer-Division','division','armor','de-xix','1',level='detail')
pos('de-1pz', m05_13=(4.97,49.71,A), m05_21=(2.05,50.12,A), m05_24=(2.05,50.85,A), m05_26=(2.08,50.9,A), m05_28=(2.13,50.93,A), m05_31=(2.55,49.98,M), m06_04=(2.9,49.92,M))
unit('de-2pz','axis','第2裝甲師','2. Panzer-Division','division','armor','de-xix','2',level='detail')
pos('de-2pz', m05_13=(4.86,49.75,A), m05_21=(1.82,50.15,A), m05_24=(1.75,50.67,A), m05_26=(1.78,50.78,A), m05_28=(1.8,50.8,M), m05_31=(2.3,49.95,M), m06_04=(2.6,49.92,M))
unit('de-10pz','axis','第10裝甲師','10. Panzer-Division','division','armor','de-xix','10',level='detail')
pos('de-10pz', m05_13=(5.02,49.655,A), m05_21=(2.25,50.05,M), m05_24=(1.95,50.6,A), m05_26=(1.9,50.93,A), m05_28=(1.95,50.92,M), m05_31=(2.6,49.95,M), m06_04=(2.95,49.88,M))
unit('de-4a','axis','第4集團軍','4. Armee','army','infantry',label='4')
pos('de-4a', m05_10=(6.62,50.3,M), m05_12=(5.65,50.32,A), m05_13=(5.25,50.38,A), m05_15=(4.8,50.33,A), m05_17=(4.2,50.24,A), m05_20=(3.45,50.25,A),
    m05_21=(3.35,50.27,A), m05_24=(3.05,50.3,A), m05_26=(2.98,50.45,A), m05_28=(2.98,50.49,A), m05_31=(2.95,50.62,M), m06_04=(2.75,50.6,M))
unit('de-12a','axis','第12集團軍','12. Armee','army','infantry',label='12')
pos('de-12a', m05_10=(6.75,49.85,M), m05_12=(5.6,49.85,M), m05_13=(5.2,49.8,A), m05_15=(4.85,49.72,A), m05_17=(4.45,49.6,A), m05_20=(3.9,49.62,Dd),
    m05_21=(3.9,49.62,Dd), m05_24=(3.6,49.62,Dd), m05_26=(3.6,49.62,Dd), m05_28=(3.55,49.64,Dd), m05_31=(3.5,49.65,Dd), m06_04=(3.5,49.65,Dd))
unit('de-16a','axis','第16集團軍','16. Armee','army','infantry',label='16')
pos('de-16a', m05_10=(6.85,49.58,M), m05_12=(6.0,49.72,M), m05_13=(5.6,49.7,M), m05_15=(5.2,49.63,Dd), m05_17=(5.05,49.6,Dd), m05_20=(5.1,49.62,Dd),
    m05_21=(5.1,49.62,Dd), m05_24=(5.1,49.62,Dd), m05_26=(5.1,49.62,Dd), m05_28=(5.1,49.62,Dd), m05_31=(5.1,49.62,Dd), m06_04=(5.1,49.62,Dd))
unit('de-abb','axis','德軍步兵師（阿布維爾橋頭堡）','Infanterie-Division (Abbeville)','division','infantry',label='ID',level='detail')
pos('de-abb', m05_24=(1.85,50.08,Dd), m05_26=(1.85,50.08,Dd), m05_28=(1.84,50.08,Dd), m05_31=(1.85,50.08,Dd), m06_04=(1.85,50.08,Dd))
unit('de-lw','axis','德國空軍（第2航空隊）','Luftflotte 2','army','air',label='LF2',dim='A')
pos('de-lw', m05_26=(2.6,50.72,A), m05_28=(2.5,50.82,A), m05_31=(2.45,50.88,A), m06_04=(2.55,50.7,M))
# 盟軍
unit('nl-army','allied','荷蘭陸軍','Koninklijke Landmacht','army','infantry',label='NL')
pos('nl-army', m05_10=(5.5,52.05,Dd), m05_12=(5.1,52.05,Dd), m05_13=(4.5,52.05,Dd), m05_15=(4.65,52.05,X))
unit('be-army','allied','比利時陸軍','Armée belge','army','infantry',label='BE')
pos('be-army', m05_10=(5.35,51.05,Dd), m05_12=(4.82,51.08,Dd), m05_13=(4.7,51.08,Dd), m05_15=(4.5,51.05,Dd), m05_17=(4.1,51.1,R), m05_20=(3.62,51.1,Dd),
    m05_21=(3.6,51.08,Dd), m05_24=(3.35,51.05,Dd), m05_26=(3.22,51.08,Dd), m05_28=(3.05,51.12,X))
unit('fr-7a','allied','法國第7集團軍','7e Armée','army','motorized',label='7')
pos('fr-7a', m05_10=(3.0,50.95,M), m05_12=(4.72,51.5,A), m05_13=(4.5,51.42,R), m05_15=(4.25,51.25,R), m05_17=(2.9,49.6,M), m05_20=(2.5,49.72,Dd),
    m05_21=(2.4,49.75,Dd), m05_24=(2.5,49.75,Dd), m05_26=(2.4,49.75,Dd), m05_28=(2.4,49.75,Dd), m05_31=(2.4,49.72,Dd), m06_04=(2.4,49.7,Dd))
unit('bef','allied','英國遠征軍','British Expeditionary Force','army','infantry',label='BEF')
pos('bef', m05_10=(3.2,50.65,M), m05_12=(4.55,50.83,Dd), m05_13=(4.55,50.83,Dd), m05_15=(4.5,50.82,Dd), m05_17=(4.15,50.8,R), m05_20=(3.45,50.75,Dd),
    m05_21=(3.3,50.62,Dd), m05_24=(3.05,50.68,Dd), m05_26=(2.88,50.75,Dd), m05_28=(2.65,50.95,R), m05_31=(2.5,51.03,V))
unit('uk-i','allied','英軍第1軍','I Corps','corps','infantry','bef','I',level='detail')
pos('uk-i', m05_21=(3.28,50.58,Dd), m05_24=(3.12,50.6,Dd), m05_26=(2.98,50.63,Dd), m05_28=(2.62,50.92,R), m05_31=(2.42,51.02,V))
unit('uk-ii','allied','英軍第2軍','II Corps','corps','infantry','bef','II',level='detail')
pos('uk-ii', m05_21=(3.42,50.72,Dd), m05_24=(3.12,50.75,Dd), m05_26=(3.02,50.78,Dd), m05_28=(2.82,50.86,Dd), m05_31=(2.6,51.05,V))
unit('uk-iii','allied','英軍第3軍','III Corps','corps','infantry','bef','III',level='detail')
pos('uk-iii', m05_21=(3.25,50.5,Dd), m05_24=(2.85,50.6,Dd), m05_26=(2.72,50.62,Dd), m05_28=(2.55,50.85,R), m05_31=(2.45,50.99,V))
unit('uk-50','allied','英軍第50步兵師','50th (Northumbrian) Infantry Division','division','motorized','uk-iii','50',level='detail')
pos('uk-50', m05_21=(2.8,50.32,A), m05_24=(2.95,50.72,Dd), m05_26=(2.86,50.82,Dd), m05_28=(2.78,50.95,R), m05_31=(2.55,51.05,V))
unit('uk-1atb','allied','英軍第1陸軍戰車旅','1st Army Tank Brigade','brigade','armor','bef','1',level='detail')
pos('uk-1atb', m05_21=(2.7,50.28,A), m05_24=(2.8,50.7,Dd), m05_26=(2.72,50.78,Dd), m05_28=(2.7,50.98,R), m05_31=(2.5,51.04,V))
unit('fr-1a','allied','法國第1集團軍','1re Armée','army','infantry',label='1')
pos('fr-1a', m05_10=(3.75,50.4,M), m05_12=(4.62,50.6,Dd), m05_13=(4.62,50.6,Dd), m05_15=(4.58,50.55,Dd), m05_17=(4.05,50.5,R), m05_20=(3.32,50.46,Dd),
    m05_21=(3.22,50.45,Dd), m05_24=(3.15,50.55,Dd), m05_26=(3.02,50.6,Dd), m05_28=(3.05,50.63,E), m05_31=(3.06,50.63,X))
unit('fr-cc','allied','法國騎兵軍（機械化）','Corps de cavalerie','corps','armor','fr-1a',label='CC')
pos('fr-cc', m05_10=(3.9,50.62,M), m05_12=(4.92,50.64,Dd), m05_13=(4.9,50.62,Dd), m05_15=(4.7,50.48,R), m05_17=(4.2,50.48,R), m05_20=(3.22,50.38,Dd),
    m05_21=(3.0,50.33,A), m05_24=(2.95,50.45,Dd), m05_26=(2.8,50.62,Dd), m05_28=(2.6,50.9,R), m05_31=(2.35,50.99,V))
unit('fr-rg','allied','法軍後衛（敦克爾克）','Arrière-garde française','corps','infantry',label='16',level='detail')
pos('fr-rg', m05_28=(2.33,50.98,Dd), m05_31=(2.38,51.0,Dd), m06_04=(2.38,51.02,X))
unit('fr-9a','allied','法國第9集團軍','9e Armée','army','infantry',label='9')
pos('fr-9a', m05_10=(4.3,50.0,M), m05_12=(4.72,50.12,Dd), m05_13=(4.7,50.1,Dd), m05_15=(4.2,50.05,R), m05_17=(3.95,50.1,X))
unit('fr-2a','allied','法國第2集團軍','2e Armée','army','infantry',label='2')
pos('fr-2a', m05_10=(5.0,49.6,Dd), m05_12=(4.95,49.62,Dd), m05_13=(4.88,49.6,Dd), m05_15=(4.85,49.45,Dd), m05_17=(4.9,49.43,Dd), m05_20=(4.9,49.42,Dd),
    m05_21=(4.9,49.42,Dd), m05_24=(4.9,49.42,Dd), m05_26=(4.9,49.42,Dd), m05_28=(4.9,49.42,Dd), m05_31=(4.9,49.42,Dd), m06_04=(4.9,49.42,Dd))
unit('fr-4dcr','allied','法國第4裝甲師','4e DCR','division','armor',label='4')
pos('fr-4dcr', m05_17=(3.7,49.55,A), m05_20=(3.5,49.42,Dd), m05_21=(3.4,49.42,Dd), m05_24=(2.4,49.65,M), m05_26=(2.0,49.9,M), m05_28=(1.88,49.98,A), m05_31=(1.85,49.97,Dd), m06_04=(1.9,49.9,Dd))
unit('uk-rn','allied','皇家海軍（發電機行動船隊）','Royal Navy / Dynamo','army','naval',label='RN',dim='S')
pos('uk-rn', m05_26=(1.55,51.08,M), m05_28=(1.9,51.15,M), m05_31=(2.1,51.13,M), m06_04=(1.6,51.1,M))
# v2.2 新增：裝甲集群與更多師（位置由上級推導，標 derived）
unit('de-pgk','axis','克萊斯特裝甲集群','Panzergruppe von Kleist','army','armor',label='PzGr K')
P['de-pgk']={md:((P['de-xix'][md][0]+P['de-xli'][md][0])/2,(P['de-xix'][md][1]+P['de-xli'][md][1])/2,P['de-xix'][md][2],'derived') for md in P['de-xix'] if md in P['de-xli']}
unit('de-6pz','axis','第6裝甲師','6. Panzer-Division','division','armor','de-xli','6',level='detail'); P['de-6pz']={'05-13':(4.78,49.885,A)}
unit('de-8pz','axis','第8裝甲師','8. Panzer-Division','division','armor','de-xli','8',level='detail'); P['de-8pz']={'05-13':(4.9,49.84,A)}
unit('de-5pz','axis','第5裝甲師','5. Panzer-Division','division','armor','de-xv','5',level='detail'); P['de-5pz']={'05-13':(4.96,50.2,A)}
unit('de-3pz','axis','第3裝甲師','3. Panzer-Division','division','armor','de-xvi','3',level='detail'); P['de-3pz']={}
unit('de-4pz','axis','第4裝甲師','4. Panzer-Division','division','armor','de-xvi','4',level='detail'); P['de-4pz']={}
unit('fr-2dlm','allied','法國第2輕機械化師','2e DLM','division','armor','fr-cc','2L',level='detail'); P['fr-2dlm']={}
unit('fr-3dlm','allied','法國第3輕機械化師','3e DLM','division','armor','fr-cc','3L',level='detail'); P['fr-3dlm']={}
unit('fr-55di','allied','法國第55步兵師','55e DI','division','infantry','fr-2a','55',level='detail'); P['fr-55di']={'05-13':(4.8,49.64,Dd)}
unit('fr-71di','allied','法國第71步兵師','71e DI','division','infantry','fr-2a','71',level='detail'); P['fr-71di']={'05-13':(4.98,49.58,Dd)}
unit('fr-18di','allied','法國第18步兵師','18e DI','division','infantry','fr-9a','18',level='detail'); P['fr-18di']={'05-13':(4.8,50.25,Dd)}
unit('uk-20gds','allied','英軍第20近衛旅（布洛涅）','20th Guards Brigade','brigade','infantry',None,'20G',level='detail'); P['uk-20gds']={'05-24':(1.63,50.72,E)}
unit('uk-30bde','allied','英軍第30旅（加萊）','30th Infantry Brigade','brigade','motorized',None,'30',level='detail'); P['uk-30bde']={'05-24':(1.87,50.95,Dd),'05-26':(1.86,50.95,E)}
KEYMD = [k[5:] for k in KEYS]
# 子單位缺的關鍵日：跟父單位 + 偏移（標 derived）
CTRL = {md: control_for(md)[1] for md in KEYMD}
def side_ok(side, x, y, md):
    ins = CTRL[md].contains(Point(x,y)); return ins if side=='axis' else not ins
NEW_DERIVE = {'de-6pz','de-8pz','de-5pz','de-3pz','de-4pz','fr-2dlm','fr-3dlm','fr-55di','fr-71di','fr-18di'}
order = sorted(U, key=lambda u: {'army':0,'corps':1,'division':2,'brigade':2}[u['echelon']])
for u in order:
    pid = u['parent_id']; d = P[u['id']]
    if not pid: continue
    sib = [x['id'] for x in U if x['parent_id']==pid]; k = sib.index(u['id']); n = len(sib)
    present = [md for md in KEYMD if md in d]
    first = KEYMD.index(present[0]) if present else len(KEYMD)
    last = KEYMD.index(present[-1]) if present else -1
    for md in KEYMD:
        if md in d or md not in P[pid]: continue
        i = KEYMD.index(md)
        if u['id'] not in NEW_DERIVE and i > first: continue   # 舊單位只往前補
        if u['id'] in NEW_DERIVE and present and i > last + 1 and P[pid][md][2] in (X,): continue
        pl = P[pid][md]
        for r in (0.10, 0.07, 0.045, 0.02):
            ok=False
            for t in range(12):
                a = 2*math.pi*(k/n) + math.pi/2 + t*math.pi/6
                x, y = pl[0]+r*math.cos(a)*1.4, pl[1]+r*math.sin(a)
                if LAND.contains(Point(x,y)) and side_ok(u['side'], x, y, md): ok=True; break
            if ok: break
        if ok: d[md] = (round(x,3), round(y,3), pl[2], 'derived')
# ---------------- 箭頭（指向該關鍵日；路徑為推進軸線）----------------
AR = []
def arrow(md, side, kind, pts, unit_id=None):
    AR.append(dict(date=K(md), side=side, kind=kind, unit_id=unit_id, path=[list(p) for p in pts]))
arrow('05-12','axis','armor',[(6.55,49.9),(5.9,49.82),(5.15,49.74)],'de-xix')
arrow('05-12','axis','armor',[(6.45,50.1),(5.7,50.0),(5.0,49.94)],'de-xli')
arrow('05-12','axis','armor',[(6.45,50.42),(5.8,50.3),(5.08,50.25)],'de-xv')
arrow('05-12','axis','armor',[(6.3,50.98),(5.7,50.78),(5.25,50.66)],'de-xvi')
arrow('05-12','axis','infantry',[(6.7,52.3),(6.2,52.2),(5.75,52.12)],'de-18a')
arrow('05-12','allied','infantry',[(3.25,50.68),(3.9,50.8),(4.5,50.83)],'bef')
arrow('05-12','allied','infantry',[(3.8,50.42),(4.2,50.55),(4.58,50.6)],'fr-1a')
arrow('05-12','allied','motorized',[(3.05,50.98),(3.9,51.3),(4.65,51.5)],'fr-7a')
arrow('05-13','axis','armor',[(5.75,49.8),(5.25,49.74),(4.92,49.68),(4.74,49.61)],'de-xix')
arrow('05-13','axis','armor',[(5.7,50.32),(5.25,50.28),(4.95,50.25),(4.76,50.21)],'de-xv')
arrow('05-13','axis','armor',[(5.55,50.0),(5.1,49.94),(4.84,49.89),(4.64,49.87)],'de-xli')
arrow('05-15','axis','armor',[(4.95,49.7),(4.6,49.68),(4.2,49.7)],'de-xix')
arrow('05-15','axis','armor',[(4.75,49.9),(4.45,49.8),(4.08,49.74)],'de-xli')
arrow('05-15','axis','armor',[(4.9,50.24),(4.7,50.2),(4.42,50.15)],'de-xv')
arrow('05-15','axis','infantry',[(5.1,51.85),(4.8,51.9),(4.5,51.92)],'de-18a')
arrow('05-17','axis','armor',[(4.45,49.68),(3.95,49.75),(3.45,49.86)],'de-xix')
arrow('05-17','axis','armor',[(4.08,49.76),(3.85,49.9),(3.55,49.98)],'de-xli')
arrow('05-17','axis','armor',[(4.4,50.15),(4.0,50.2),(3.7,50.15)],'de-xv')
arrow('05-17','allied','counter',[(3.58,49.45),(3.72,49.55),(3.88,49.65)],'fr-4dcr')
arrow('05-20','axis','armor',[(3.5,49.85),(2.9,49.98),(2.3,50.03),(1.75,50.12)],'de-xix')
arrow('05-20','axis','armor',[(3.55,49.98),(3.0,50.1),(2.45,50.18)],'de-xli')
arrow('05-20','axis','armor',[(3.65,50.16),(3.25,50.2),(2.9,50.19)],'de-xv')
arrow('05-20','allied','retreat',[(4.2,50.82),(3.85,50.78),(3.5,50.74)],'bef')
arrow('05-21','allied','counter',[(2.78,50.34),(2.7,50.26),(2.74,50.2)],'uk-1atb')
arrow('05-21','axis','armor',[(2.05,50.2),(1.85,50.3),(1.72,50.48)],'de-2pz')
arrow('05-24','axis','armor',[(1.85,50.2),(1.68,50.45),(1.72,50.7),(1.95,50.86)],'de-xix')
arrow('05-24','axis','armor',[(2.35,50.22),(2.25,50.45),(2.2,50.66)],'de-xli')
arrow('05-24','axis','armor',[(2.85,50.2),(2.75,50.35),(2.62,50.48)],'de-xv')
arrow('05-24','axis','infantry',[(3.8,50.88),(3.6,50.9),(3.35,50.92)],'de-6a')
arrow('05-26','axis','infantry',[(3.55,50.92),(3.4,50.96),(3.25,50.98)],'de-6a')
arrow('05-26','axis','infantry',[(3.8,51.22),(3.65,51.22),(3.48,51.22)],'de-18a')
arrow('05-26','allied','naval',[(2.35,51.07),(1.9,51.2),(1.42,51.16)],'uk-rn')
arrow('05-28','axis','infantry',[(3.25,50.86),(3.1,50.86),(2.95,50.86)],'de-6a')
arrow('05-28','axis','infantry',[(3.35,51.16),(3.15,51.15),(2.9,51.12)],'de-18a')
arrow('05-28','axis','armor',[(2.58,50.5),(2.6,50.62),(2.62,50.76)],'de-xv')
arrow('05-28','allied','retreat',[(3.0,50.72),(2.85,50.84),(2.68,50.95)],'bef')
arrow('05-28','allied','counter',[(1.95,49.88),(1.9,49.96),(1.85,50.04)],'fr-4dcr')
arrow('05-28','allied','naval',[(2.45,51.08),(2.0,51.25),(1.45,51.32)],'uk-rn')
arrow('05-31','axis','infantry',[(3.0,51.1),(2.88,51.09),(2.76,51.08)],'de-18a')
arrow('05-31','axis','infantry',[(2.98,50.86),(2.8,50.92),(2.64,50.96)],'de-6a')
arrow('05-31','allied','naval',[(2.45,51.08),(1.95,51.22),(1.42,51.16)],'uk-rn')
arrow('05-31','allied','naval',[(2.58,51.12),(2.4,51.3),(1.5,51.33)],'uk-rn')
arrow('06-04','axis','infantry',[(2.7,51.0),(2.55,51.01),(2.42,51.02)],'de-18a')
# ---------------- 交戰 ----------------
EN = []
def eng(md, i, name, lon, lat, att, dfn, tag, label):
    EN.append(dict(id=i, date=K(md), name_zh=name, lng=lon, lat=lat,
        units=[{'unit_id':u,'role':'attacker'} for u in att]+[{'unit_id':u,'role':'defender'} for u in dfn],
        interaction_tag=tag, interaction_zh=label, outcome=None, source='example'))
eng('05-12','e-hannut','漢努特（示例）',5.08,50.67,['de-xvi'],['fr-cc'],'armor_vs_armor','裝甲 vs 裝甲')
eng('05-13','e-sedan','色當渡河（示例）',4.93,49.69,['de-xix'],['fr-2a'],'armor_air_vs_infantry','裝甲＋空襲 vs 步兵')
eng('05-13','e-dinant','迪南渡河（示例）',4.9,50.25,['de-xv'],['fr-9a'],'armor_vs_infantry','裝甲 vs 步兵')
eng('05-15','e-gembloux','讓布盧（示例）',4.7,50.56,['de-xvi'],['fr-1a'],'armor_vs_infantry','裝甲 vs 步兵防線')
eng('05-15','e-stonne','斯通訥（示例）',4.92,49.55,['de-xix'],['fr-2a'],'armor_vs_infantry','裝甲 vs 步兵')
eng('05-17','e-montcornet','蒙科爾內反擊（示例）',3.9,49.66,['fr-4dcr'],['de-xix'],'armor_vs_armor','裝甲 vs 裝甲（反擊）')
eng('05-20','e-abbeville','阿布維爾（示例）',1.84,50.11,['de-xix'],[],'armor_vs_rear','裝甲 vs 後方')
eng('05-21','e-arras','阿拉斯反擊（示例）',2.74,50.25,['uk-1atb','uk-50'],['de-7pz','de-sstk'],'armor_vs_armor','裝甲 vs 裝甲／摩托化步兵')
eng('05-24','e-aa','阿河運河（停止令）',2.2,50.8,['de-xli'],['bef'],'armor_halt','裝甲停於運河（停止令）')
eng('05-24','e-boulogne','布洛涅（示例）',1.66,50.72,['de-2pz'],['uk-20gds'],'armor_vs_infantry','裝甲 vs 步兵（包圍圈）')
eng('05-26','e-calais','加萊（示例）',1.9,50.94,['de-10pz'],['uk-30bde'],'armor_vs_infantry','裝甲 vs 步兵（包圍圈）')
eng('05-31','e-lille','里爾（示例）',3.12,50.6,['de-4a'],['fr-1a'],'infantry_vs_infantry','步兵 vs 步兵（包圍圈）')
eng('05-26','e-lys','利斯河（示例）',3.22,50.97,['de-6a'],['be-army'],'infantry_vs_infantry','步兵 vs 步兵')
eng('05-26','e-beach1','海灘空襲（示例）',2.45,51.05,['de-lw'],['uk-rn'],'air_vs_naval','空襲 → 海灘撤退')
eng('05-28','e-ypres','伊珀爾—科米訥（示例）',2.9,50.82,['de-6a'],['uk-ii'],'infantry_vs_infantry','步兵 vs 步兵')
eng('05-28','e-abb2','阿布維爾反擊（示例）',1.85,50.05,['fr-4dcr'],['de-abb'],'armor_vs_infantry','裝甲 vs 步兵（橋頭堡）')
eng('05-31','e-perim','敦克爾克周邊（示例）',2.6,50.99,['de-18a'],['fr-rg'],'infantry_vs_infantry','步兵 vs 步兵（後衛）')
eng('05-31','e-beach2','海灘空襲（示例）',2.52,51.07,['de-lw'],['uk-rn'],'air_vs_naval','空襲 → 海灘撤退')
eng('06-04','e-fall','敦克爾克陷落（示例）',2.38,51.03,['de-18a'],['fr-rg'],'infantry_vs_infantry','後衛投降')
# ---------------- 關鍵日 ----------------
CAM = {'overview':[0.8,48.8,8.2,53.0],'mid':[0.6,49.3,5.4,51.6],'close':[0.9,49.85,3.9,51.45]}
CAM_M = {'overview':[2.6,48.9,7.4,52.6],'mid':[0.9,49.4,4.6,51.5],'close':[1.2,49.9,3.6,51.35]}
KF = [
 ('05-10','overview','黃色方案：入侵低地國','FALL GELB',False),
 ('05-12','overview','穿越阿登','ARDENNES',False),
 ('05-13','overview','色當突破','SEDAN',True),
 ('05-15','overview','荷蘭投降・突破擴大','BREAKTHROUGH',False),
 ('05-17','overview','蒙科爾內反擊','MONTCORNET',False),
 ('05-20','mid','鐮刀收割：抵達海岸','SICHELSCHNITT',True),
 ('05-21','close','阿拉斯反擊','ARRAS',False),
 ('05-24','close','停止令','HALTBEFEHL',False),
 ('05-26','close','發電機行動開始','OPERATION DYNAMO',True),
 ('05-28','close','比利時投降','28 MAI',False),
 ('05-31','close','包圍圈收縮','PERIMETER',False),
 ('06-04','close','敦克爾克陷落・撤退結束','4 JUIN',True),
]
# 每個關鍵日的「焦點圖層」：自動模式下 C 交戰／D 地名跟著這裡開關
FOCUS = {'05-10':['places'],'05-12':['engagements'],'05-13':['engagements'],'05-15':['engagements'],'05-17':['engagements'],
         '05-20':['places','engagements'],'05-21':['engagements'],'05-24':['places','engagements'],'05-26':['places','engagements'],
         '05-28':['engagements'],'05-31':['engagements'],'06-04':['places']}
# 每個關鍵日的焦點部隊（全強度顯示；其餘縮小變淡、不顯示徽章）
FOCUS_UNITS = {
 '05-10':['de-xix','de-xv','de-xvi','bef','fr-1a'],
 '05-12':['de-xix','de-xli','de-xv','de-xvi','fr-cc'],
 '05-13':['de-xix','de-xv','de-xli','fr-2a','fr-9a'],
 '05-15':['de-xix','de-xli','de-xv','fr-9a','de-xvi','fr-1a'],
 '05-17':['de-xix','de-xli','fr-4dcr','de-xv'],
 '05-20':['de-xix','de-xli','de-xv','bef'],
 '05-21':['uk-1atb','uk-50','de-7pz','de-sstk','de-2pz'],
 '05-24':['de-xix','de-xli','de-1pz','de-2pz','de-10pz','bef','uk-20gds','uk-30bde'],
 '05-26':['bef','uk-rn','de-lw','de-6a','be-army','uk-i','uk-ii','uk-iii','uk-30bde'],
 '05-28':['be-army','de-6a','uk-ii','fr-4dcr','de-abb','uk-rn','de-18a','fr-1a'],
 '05-31':['fr-rg','de-18a','uk-rn','de-lw','de-6a','fr-1a','de-4a'],
 '06-04':['fr-rg','de-18a'],
}
# 每個關鍵日在「自動」模式下顯示的 6–8 個地名
PLACES = {
 '05-10':['鹿特丹','布魯塞爾','列日','盧森堡','色當','巴黎'],
 '05-12':['列日','漢努特','迪南','色當','布魯塞爾','安特衛普'],
 '05-13':['色當','迪南','蒙泰梅','布魯塞爾','讓布盧','鹿特丹'],
 '05-15':['鹿特丹','讓布盧','色當','蒙科爾內','布魯塞爾','安特衛普'],
 '05-17':['蒙科爾內','拉昂','聖康坦','色當','布魯塞爾','里爾'],
 '05-20':['阿布維爾','亞眠','阿拉斯','聖康坦','里爾','布魯塞爾','敦克爾克'],
 '05-21':['阿拉斯','阿布維爾','布洛涅','里爾','敦克爾克','亞眠'],
 '05-24':['格拉沃利訥','聖奧梅爾','加萊','布洛涅','敦克爾克','里爾'],
 '05-26':['敦克爾克','多佛','加萊','伊珀爾','里爾','奧斯坦德','尼烏波特'],
 '05-28':['敦克爾克','伊珀爾','尼烏波特','里爾','阿布維爾','多佛'],
 '05-31':['敦克爾克','尼烏波特','拉帕訥','格拉沃利訥','多佛','里爾'],
 '06-04':['敦克爾克','多佛','阿布維爾','亞眠'],
}
# 事件字卡：一句話（示例敘述，需查證）
LINE = {
 '05-10':'德軍同時進攻荷蘭、比利時、盧森堡；英法聯軍北上迎擊。',
 '05-12':'德軍裝甲穿越阿登森林，抵達默茲河。',
 '05-13':'德軍在色當、迪南渡過默茲河，法軍防線出現缺口。',
 '05-15':'荷蘭投降；色當突破口向西擴大。',
 '05-17':'法軍第4裝甲師在蒙科爾內反擊。',
 '05-20':'德軍裝甲抵達阿布維爾海岸，北方盟軍被切斷。',
 '05-21':'英軍在阿拉斯以戰車反擊德軍側翼。',
 '05-24':'德軍裝甲停在阿河運河一線；布洛涅、加萊被圍。',
 '05-26':'英軍開始從敦克爾克海上撤退。',
 '05-28':'比利時陸軍投降；法軍第1集團軍一部被圍在里爾。',
 '05-31':'包圍圈縮到敦克爾克周邊海岸一帶。',
 '06-04':'法軍後衛投降，撤退結束。',
}
data = {
 'meta': {'campaign':'dunkirk-1940-example','title_zh':'敦克爾克 1940','is_example':True,'banner':'示例，非史料',
          'schema_version':2,'generated_by':'tools/build_data.py',
          'note':'全部為示例資料，依大致地理手工擺放，未逐筆對照史料；不含傷亡數字。歷史細節見 NOTES-needs-checking.md。',
          'date_start':KEYS[0],'date_end':KEYS[-1],'cameras':CAM,'cameras_mobile':CAM_M},
 'keyframes':[{'date':K(md),'camera':c,'event_zh':ev,'event_en':en,'major':mj,'focus':FOCUS.get(md,[]),'focus_units':FOCUS_UNITS[md],'places':PLACES[md],'event_line':LINE[md]} for md,c,ev,en,mj in KF],
 'units':U,
 'positions':[], 'fronts':[], 'arrows':AR, 'engagements':EN,
}
for u in U:
    for md in KEYMD:
        v = P[u['id']].get(md)
        if v: data['positions'].append({'unit_id':u['id'],'date':K(md),'lng':v[0],'lat':v[1],'state':v[2],
            'status':'derived' if len(v)>3 else 'example','precision_m':20000,'source':'example'})
for md in KEYMD:
    data['fronts'].append({'date':K(md),'status':'example','axis_side':'east',
        'line':[[p[0],p[1]] + (['sea'] if len(p)>2 else []) for p in FRONTS[md]],
        'pockets':[{'id':pk['id'],'name_zh':pk['name_zh'],'side':pk['side'],'status':'example','ring':[list(v) for v in pk['ring']]} for pk in POCKETS.get(md,[])]})
    main, ax = control_for(md)
    ax = ax if ax.geom_type=='MultiPolygon' else MultiPolygon([ax])
    fl = ax.boundary.intersection(LAND.buffer(0.002))
    rn = lambda g: json.loads(json.dumps(mapping(g.simplify(0.002))), parse_float=lambda x: round(float(x),4))
    data['fronts'][-1]['control'] = {'axis': rn(ax)}          # 衍生：軸心控制區（MultiPolygon）
    data['fronts'][-1]['front_lines'] = rn(fl)               # 衍生：陸上前線（MultiLineString）
# ---------------- 自動陸地檢查 ----------------
errs=[]
on = lambda x,y: LAND.contains(Point(x,y))
dom = {u['id']:u['domain'] for u in U}
for p in data['positions']:
    d=dom[p['unit_id']]
    if d=='ground' and not on(p['lng'],p['lat']): errs.append(f"unit {p['unit_id']} {p['date']} at sea {p['lng']},{p['lat']}")
    if d=='sea' and on(p['lng'],p['lat']): errs.append(f"naval {p['unit_id']} {p['date']} on land")
for f in data['fronts']:
    for v in f['line']:
        if len(v)>2 and on(v[0],v[1]): errs.append(f"front {f['date']} sea-anchor on land {v}")
        if len(v)==2 and not on(v[0],v[1]): errs.append(f"front {f['date']} vertex at sea {v}")
for md in KEYMD:
    main,_ = control_for(md)
    for pk in POCKETS.get(md,[]):
        g=Polygon(pk['ring'])
        if not g.is_valid: errs.append(f"pocket {pk['id']} {md} invalid ring")
        if not LAND.contains(g.representative_point()) and not LAND.intersects(g): errs.append(f"pocket {pk['id']} {md} not on land")
        if pk['side']=='allied' and not main.buffer(1e-6).contains(g.intersection(LAND)): errs.append(f"pocket {pk['id']} {md} not enclosed by axis area")
for a in AR:
    pts=a['path']
    if a['kind']=='naval':
        for v in pts[1:-1]:
            if on(*v): errs.append(f"naval arrow {a['date']} mid on land {v}")
    else:
        # 沿線取樣
        for i in range(len(pts)-1):
            for t in [j/8 for j in range(9)]:
                x=pts[i][0]+(pts[i+1][0]-pts[i][0])*t; y=pts[i][1]+(pts[i+1][1]-pts[i][1])*t
                if not on(x,y): errs.append(f"arrow {a['date']} {a['unit_id']} at sea {x:.3f},{y:.3f}"); break
for e in EN:
    if not on(e['lng'],e['lat']) and e['interaction_tag']!='air_vs_naval': errs.append(f"engagement {e['id']} at sea")
ids={u['id'] for u in U}
for e in EN:
    for x in e['units']:
        if x['unit_id'] not in ids: errs.append('bad unit ref '+x['unit_id'])
json.dump(data, open('battles/dunkirk-1940-example/battle.json','w'), ensure_ascii=False, indent=1)
report={'checked_positions':len(data['positions']),'checked_front_vertices':sum(len(f['line']) for f in data['fronts']),
        'checked_arrows':len(AR),'checked_engagements':len(EN),'errors':errs}
json.dump(report, open('battles/dunkirk-1940-example/land-check.json','w'), ensure_ascii=False, indent=1)
print(json.dumps({k:v for k,v in report.items() if k!='errors'}), 'errors:', len(errs))
for e in errs: print(' ', e)
sys.exit(1 if errs else 0)
