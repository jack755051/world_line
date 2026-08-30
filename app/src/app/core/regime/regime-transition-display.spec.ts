import { describeRegimeEnd, describeRegimeOrigin } from './regime-transition-display';

describe('describeRegimeOrigin()', () => {
  it('predecessorRegimeId 為 null（例：漢，沒有前身政權）時回傳「獨立起始」', () => {
    expect(
      describeRegimeOrigin({ predecessorRegimeId: null, originTransitionType: null, predecessorName: undefined }),
    ).toEqual({ text: '獨立起始（無前身政權）' });
  });

  it('originTransitionType===split 時文字含「分裂」', () => {
    expect(
      describeRegimeOrigin({
        predecessorRegimeId: 'r-han',
        originTransitionType: 'split',
        predecessorName: '漢',
      }),
    ).toEqual({ text: '承 漢 分裂而立' });
  });

  it('originTransitionType===succeeded 時文字含「禪讓」', () => {
    expect(
      describeRegimeOrigin({
        predecessorRegimeId: 'r-wei',
        originTransitionType: 'succeeded',
        predecessorName: '魏',
      }),
    ).toEqual({ text: '承 魏 禪讓而立' });
  });

  it('查不到前身政權名稱時 fallback 用 id', () => {
    expect(
      describeRegimeOrigin({
        predecessorRegimeId: 'r-unknown',
        originTransitionType: 'split',
        predecessorName: undefined,
      }),
    ).toEqual({ text: '承 r-unknown 分裂而立' });
  });
});

describe('describeRegimeEnd()——AC#2 核心：禪讓跟被滅亡必須是不同 variant', () => {
  it('status=active 時沒有終止文字，variant=outline', () => {
    expect(
      describeRegimeEnd({
        status: 'active',
        destroyedByRegimeId: null,
        destroyedByName: undefined,
        successorNames: [],
        splitChildrenNames: [],
      }),
    ).toEqual({ text: null, variant: 'outline' });
  });

  it('status=split 時列出分裂出的政權，variant=secondary', () => {
    expect(
      describeRegimeEnd({
        status: 'split',
        destroyedByRegimeId: null,
        destroyedByName: undefined,
        successorNames: [],
        splitChildrenNames: ['魏', '蜀漢', '吳'],
      }),
    ).toEqual({ text: '分裂為 魏／蜀漢／吳', variant: 'secondary' });
  });

  it('status=split 但查無分裂政權時顯示佔位文字，不是空字串', () => {
    expect(
      describeRegimeEnd({
        status: 'split',
        destroyedByRegimeId: null,
        destroyedByName: undefined,
        successorNames: [],
        splitChildrenNames: [],
      }),
    ).toEqual({ text: '分裂為 （分裂政權尚未建檔）', variant: 'secondary' });
  });

  it('status=succeeded 時顯示禪讓對象，variant=default（跟 conquered 的 destructive 不同）', () => {
    expect(
      describeRegimeEnd({
        status: 'succeeded',
        destroyedByRegimeId: null,
        destroyedByName: undefined,
        successorNames: ['晉'],
        splitChildrenNames: [],
      }),
    ).toEqual({ text: '禪讓予 晉', variant: 'default' });
  });

  it('status=conquered 時顯示滅亡方，variant=destructive（紅色，跟 succeeded 明確區分）', () => {
    expect(
      describeRegimeEnd({
        status: 'conquered',
        destroyedByRegimeId: 'r-wei',
        destroyedByName: '魏',
        successorNames: [],
        splitChildrenNames: [],
      }),
    ).toEqual({ text: '被 魏 所滅', variant: 'destructive' });
  });

  it('status=conquered 但查無滅亡方名稱時 fallback 用 id', () => {
    expect(
      describeRegimeEnd({
        status: 'conquered',
        destroyedByRegimeId: 'r-unknown',
        destroyedByName: undefined,
        successorNames: [],
        splitChildrenNames: [],
      }),
    ).toEqual({ text: '被 r-unknown 所滅', variant: 'destructive' });
  });
});
