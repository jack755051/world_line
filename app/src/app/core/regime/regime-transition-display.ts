import type { BadgeVariant } from '../../components/ui/badge';
import type { RegimeSummary } from './regime-directory.service';

/**
 * 任務 3.9（Story 4 AC#2）：政權狀態轉換的文字/視覺呈現，純函式，不依賴 Angular DI。
 *
 * PRD §4 憲法原話「取代跟消滅應該是兩種不同的定義」——`RegimeStatus`（見
 * `api/Domain/RegimeStatus.cs`、前端對照 `regime-status.enum.ts`）已經在資料層區分
 * 四種狀態（active/split/succeeded/conquered），這個檔案負責把狀態機的字面值轉成
 * 使用者看得懂的中文敘述＋`sanring-tag` 的 `variant`，讓「禪讓」跟「被滅亡」在畫面上
 * 明確是兩種不同顏色/文字，不能只看名稱猜。
 *
 * **刻意設計成接收「已經反查好的名稱」而不是直接吃 `RegimeDirectoryService`**：呼叫端
 * （`RegimeFocusPanelComponent`）已經有 `RegimeDirectoryService` 可以查
 * `successorOf()`/`splitChildrenOf()`/`regimeOf()`，這裡拿到的都是已經解析過的字串
 * 陣列/名稱，不重新注入一次 service——這個模組才能維持純函式、不用 TestBed 就能單元
 * 測試，跟 `edtf-display.ts`／`territory-morph.ts` 這些既有的純函式模組同一個設計
 * 原則。
 */

export interface RegimeOriginDescription {
  /** 例：「承 漢 禪讓而立」、「承 漢 分裂而立」、「獨立起始（無前身政權）」。 */
  text: string;
}

export interface RegimeEndDescription {
  /** `status==='active'` 時為 `null`——政權仍存續，沒有「終止」可以描述。 */
  text: string | null;
  /** 給 `sanring-tag`／`sanringBadge` 用的固定語意 variant，AC#2 視覺區分的關鍵：
      `destructive`（紅）＝被滅亡，`default`＝禪讓，`secondary`＝分裂，`outline`＝
      仍存續，四種狀態四種 variant，不可能混淆。 */
  variant: BadgeVariant;
}

/** 描述一個政權「怎麼來的」（`predecessorRegimeId`/`originTransitionType`）。 */
export function describeRegimeOrigin(params: {
  predecessorRegimeId: string | null;
  originTransitionType: RegimeSummary['originTransitionType'];
  predecessorName: string | undefined;
}): RegimeOriginDescription {
  const { predecessorRegimeId, originTransitionType, predecessorName } = params;
  if (predecessorRegimeId === null || originTransitionType === null) {
    return { text: '獨立起始（無前身政權）' };
  }
  const name = predecessorName ?? predecessorRegimeId;
  return {
    text: originTransitionType === 'split' ? `承 ${name} 分裂而立` : `承 ${name} 禪讓而立`,
  };
}

/** 描述一個政權「怎麼終止的」（`status`/`destroyedByRegimeId`＋反查到的後繼者）。
    `successorNames`/`splitChildrenNames` 是呼叫端已經用 `RegimeDirectoryService.
    successorOf()`/`splitChildrenOf()` 查好、轉成名稱的陣列——見上方類別文件的
    設計原則說明。 */
export function describeRegimeEnd(params: {
  status: RegimeSummary['status'];
  destroyedByRegimeId: string | null;
  destroyedByName: string | undefined;
  successorNames: readonly string[];
  splitChildrenNames: readonly string[];
}): RegimeEndDescription {
  switch (params.status) {
    case 'active':
      return { text: null, variant: 'outline' };
    case 'split': {
      const names =
        params.splitChildrenNames.length > 0 ? params.splitChildrenNames.join('／') : '（分裂政權尚未建檔）';
      return { text: `分裂為 ${names}`, variant: 'secondary' };
    }
    case 'succeeded': {
      const name = params.successorNames[0] ?? '（未知後繼政權）';
      return { text: `禪讓予 ${name}`, variant: 'default' };
    }
    case 'conquered': {
      const name = params.destroyedByName ?? params.destroyedByRegimeId ?? '（未知）';
      return { text: `被 ${name} 所滅`, variant: 'destructive' };
    }
  }
}
