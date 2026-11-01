import { placeCard } from './card-placement';

describe('placeCard（資訊卡避開時間軸與視窗邊緣）', () => {
  const W = 1440, H = 700;

  it('上半部點擊：放右側、往下長，maxHeight 到容器下緣（時間軸上緣）為止', () => {
    const p = placeCard(400, 200, W, H);
    expect(p).toEqual({ left: 412, top: 160, bottom: null, maxHeight: H - 160 - 8 });
  });

  it('下半部點擊：往上長（以 bottom 定位），卡片下緣不超過容器', () => {
    const p = placeCard(400, 600, W, H);
    expect(p.top).toBeNull();
    expect(p.bottom).toBe(60);
    expect(p.maxHeight).toBe(H - 60 - 8);
  });

  it('貼近容器下緣：bottom 至少留 8px', () => {
    expect(placeCard(400, 690, W, H).bottom).toBe(8);
  });

  it('右側放不下：改放點的左側；兩側都放不下就貼右緣並留邊', () => {
    expect(placeCard(1300, 200, W, H).left).toBe(1300 - 12 - 340);
    expect(placeCard(200, 200, 360, H).left).toBe(12);
  });

  it('上緣：top 至少 8px', () => {
    expect(placeCard(400, 10, W, H).top).toBe(8);
  });
});
