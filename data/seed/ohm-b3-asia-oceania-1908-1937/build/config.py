"""第 3 批：南亞、東南亞、大洋洲 1937-07-07 前（既有政權只補 1937-07-07 前；完全沒有資料的新政權補 1908～1945）。"""
N = lambda lang, zh, en, layer='de_jure', orig=None, qid=None: (orig, lang, zh, en, layer, qid)
NEW = {
 'johore-protectorate': N('en', '柔佛保護國', 'Johore Protectorate'),
 'kedah-protectorate': N('en', '吉打保護國', 'Kedah Protectorate'),
 'kelantan-protectorate': N('en', '吉蘭丹保護國', 'Kelantan Protectorate'),
 'perlis-protectorate': N('en', '玻璃市保護國', 'Perlis Protectorate'),
 'trengganu-protectorate': N('en', '登嘉樓保護國', 'Trengganu Protectorate'),
 'us-philippine-islands': N('en', '美屬菲律賓群島', 'Philippine Islands (US)', orig='Philippine Islands'),
 'sultanate-of-sulu': N('tsg', '蘇祿蘇丹國', 'Sultanate of Sulu', orig='Kasultanan sin Sūg'),
 'australian-occupation-of-german-new-guinea': N('en', '澳洲佔領德屬新幾內亞', 'Australian occupation of German New Guinea', 'not_sovereign'),
 'german-new-guinea': N('de', '德屬新幾內亞', 'German New Guinea', orig='Deutsch-Neuguinea'),
 'japanese-occupation-of-german-pacific': N('ja', '日本佔領德屬太平洋屬地', 'Japanese occupation of German Pacific possessions', 'not_sovereign', orig='日本のドイツ植民地占領'),
 'australian-occupation-of-nauru': N('en', '澳洲佔領諾魯', 'Australian occupation of Nauru', 'not_sovereign', qid='-'),
 'nauru-mandate': N('en', '諾魯託管地', 'Nauru (mandate)', orig='Nauru'),
 'dominion-of-new-zealand': N('en', '紐西蘭', 'New Zealand'),
 'colony-of-fiji': N('en', '斐濟殖民地', 'Colony of Fiji'),
 'british-western-pacific-territories': N('en', '英屬西太平洋領地', 'British Western Pacific Territories'),
 'gilbert-and-ellice-islands': N('en', '吉爾伯特和埃利斯群島', 'Gilbert and Ellice Islands'),
 'new-hebrides-condominium': N('en', '新赫布里底共管地', 'New Hebrides Condominium', orig='New Hebrides / Nouvelles-Hébrides'),
 'new-caledonia': N('fr', '法屬新喀里多尼亞', 'New Caledonia'),
 'british-occupation-of-german-samoa': N('en', '紐西蘭佔領德屬薩摩亞', 'Occupation of German Samoa', 'not_sovereign', orig='British occupation of German Samoa'),
 'territory-of-western-samoa': N('en', '西薩摩亞託管地', 'Territory of Western Samoa'),
 'german-samoa': N('de', '德屬薩摩亞', 'German Samoa', orig='Deutsch-Samoa'),
 'cook-islands': N('en', '庫克群島', 'Cook Islands'),
 'wallis-and-futuna': N('fr', '瓦利斯和富圖納', 'Wallis and Futuna', orig='Colonie de Wallis-et-Futuna'),
 'pitcairn-islands': N('en', '皮特肯群島', 'Pitcairn Islands'),
 'protectorate-of-tonga': N('to', '東加保護國', 'Tonga (protectorate)', orig='Puleʻanga Fakatuʻi ʻo Tonga'),
 'tokelau-islands-protectorate': N('en', '托克勞群島保護地', 'Tokelau Islands Protectorate'),
 'french-establishments-in-oceania': N('fr', '法屬大洋洲', 'French Establishments in Oceania', orig="Établissements français de l'Océanie"),
}
MAP = {'British Raj': 'british-raj', 'British Burma': 'british-burma', 'British Ceylon': 'british-ceylon', 'Maldives Protectorate': 'maldives-protectorate',
 'India Portugues': 'portuguese-india', "Établissements français dans l'Inde": 'french-india', 'नेपाल': 'kingdom-of-nepal', 'འབྲུག་རྒྱལ་ཁབ།': 'kingdom-of-bhutan',
 'Nederlands-Indië': 'dutch-east-indies', 'Timor Português': 'portuguese-timor', 'Union Indochinoise': 'french-indochina', 'ราชอาณาจักรสยาม': 'kingdom-of-thailand',
 'British North Borneo': 'british-north-borneo', 'Protectorate of Brunei': 'brunei-protectorate', 'Protectorate of Sarawak': 'raj-of-sarawak',
 'Colony of the Straits Settlement': 'straits-settlements', 'Federated Malay States': 'british-malaya',
 'Johore Protectorate': 'johore-protectorate', 'Kedah Protectorate': 'kedah-protectorate', 'Kelantan Protectorate': 'kelantan-protectorate', 'Perlis Protectorate': 'perlis-protectorate',
 'Trengganu Protectorate': 'trengganu-protectorate', 'US Philippines': 'us-philippine-islands', 'Commonwealth of the Philippines': 'commonwealth-of-the-philippines',
 'Kasultanan sin Sūg': 'sultanate-of-sulu', 'Australia': 'commonwealth-of-australia', 'Australian occupation of German New Guinea': 'australian-occupation-of-german-new-guinea',
 'Deutsch-Neuguinea': 'german-new-guinea', '日本のドイツ植民地占領': 'japanese-occupation-of-german-pacific', 'Australian occupation of Nauru': 'australian-occupation-of-nauru',
 'Nauru': 'nauru-mandate', 'Dominion of New Zealand': 'dominion-of-new-zealand', 'Colony of Fiji': 'colony-of-fiji', 'British Western Pacific Territories': 'british-western-pacific-territories',
 'British Solomon Islands Protectorate': 'british-solomon-islands', 'Gilbert and Ellice Islands Colony': 'gilbert-and-ellice-islands', 'Gilbert and Ellice Islands Protectorate': 'gilbert-and-ellice-islands',
 'New Hebrides / Nouvelles-Hébrides': 'new-hebrides-condominium', 'Nouvelle-Calédonie': 'new-caledonia', 'British occupation of German Samoa': 'british-occupation-of-german-samoa',
 'Territory of Western Samoa': 'territory-of-western-samoa', 'Königreich Samoa': 'german-samoa', 'Cook Islands': 'cook-islands', "Kolonie d'Wallis-et-Futuna": 'wallis-and-futuna',
 'Pitcairn Islands': 'pitcairn-islands', 'Protectorate of Tonga': 'protectorate-of-tonga', 'Tokelau Islands Protectorate': 'tokelau-islands-protectorate',
 "Établissements français de l'Océani": 'french-establishments-in-oceania'}
DROP = {}
CLAMP_EXISTING = ('1908-01-01', '1937-07-07')
CLAMP = {'british-burma': ('1937-04-01', '1937-07-07')}   # 緬甸 1937-04-01 才自英屬印度分出；OHM 起日只有「1937」
SOURCE_TITLE = 'OpenHistoricalMap — boundary=administrative, admin_level=2 關係（南亞、東南亞、大洋洲 1908～1937-07-07；大洋洲新政權 1908～1945）'
TRIAL = '南亞、東南亞、大洋洲 1908-01-01～1937-07-06（新政權到 1945-09-30）'
