"""第 1 批：北美（加拿大、紐芬蘭、聖皮耶與密克隆、美國 1914-07-29 前；波多黎各與運河區包含在 OHM 美國 relation 內）。"""
# OHM name → slug（既有政權直接用既有 slug；新政權須在 NEW 裡）
MAP = {'Canada': 'canada', 'Dominion of Canada': 'canada',
       'Dominion of Newfoundland': 'dominion-of-newfoundland', 'Commission Government of Newfoundland': 'dominion-of-newfoundland',
       'Saint-Pierre et Miquelon': 'saint-pierre-and-miquelon', 'United States': 'united-states-of-america',
       'Koninkrijk der Nederlanden': 'kingdom-of-the-netherlands', 'Danmark': 'kingdom-of-denmark'}
# 新政權：slug → (自稱原文, 語言, zh-Hant, en, layer_status, wikidata)
NEW = {'canada': ('Dominion of Canada', 'en', '加拿大', 'Canada', 'de_jure', 'Q16'),
       'dominion-of-newfoundland': ('Dominion of Newfoundland', 'en', '紐芬蘭', 'Newfoundland', 'de_jure', 'Q38610'),
       'saint-pierre-and-miquelon': ('Saint-Pierre et Miquelon', 'fr', '法屬聖皮耶與密克隆', 'Saint Pierre and Miquelon', 'de_jure', 'Q34617')}
# 先到先得順序（紐芬蘭：2831077 與 2830879／2830878 重疊，排最後只補空檔）
ORDER = [2831074, 2831069, 2831058, 2831062, 2828507, 2830879, 2830878, 2831077, 2831312,
         2861547, 2861546, 2831010, 2873299, 2842116, 2842114, 2874809, 2874797, 2842113, 2874804, 2842115, 2873298, 2874803,
         2883430, 2869935, 2692238, 2850547, 2869937]
DROP = {2883430: '荷蘭既有紀錄只畫歐洲本土；若在 1940-05-15～1945-05-05 空檔補上會只出現海外領地（蘇利南、庫拉索），與前後不一致 → 待 Tai 決定是否撤回重寫既有荷蘭紀錄加入海外領地',
        2869935: '丹麥 1908-01-01～1908-10-06 空檔留到第 5 批（1908 全球缺口）一起處理；格陵蘭是否加入既有丹麥紀錄待 Tai 決定',
        2692238: '同上（丹麥既有紀錄已涵蓋）', 2850547: '同上（丹麥既有紀錄已涵蓋）', 2869937: '同上（丹麥既有紀錄已涵蓋）'}
SOURCE_TITLE = 'OpenHistoricalMap — boundary=administrative, admin_level=2 關係（北美：加拿大、紐芬蘭、聖皮耶與密克隆、美國 1908～1914，1908～1945）'
TRIAL = '北美 1908-01-01～1945-09-30'
# 美國只補 1914-07-29 前（Tai 00:53）；1945-09-02 之後的空檔不在本批範圍
CLAMP = {'united-states-of-america': ('1908-01-01', '1914-07-29')}
