/**
 * 後端 DTO 型別別名。型別本體由 `pnpm gen:api` 從 `backend/openapi/v1.json` 產生到 `core/api-schema.ts`（PRD §5、§7），
 * 這裡只取名字，不手寫欄位，避免與後端契約脫節（`pnpm check:api` 會檢查產生檔是否過期）。
 */
import type { components } from '../api-schema';

type Schemas = components['schemas'];

export type ApiEnvelope<T> = { statusCode: number; message: string; data: T };

export type ControlMapDto = Schemas['ControlMapDto'];
export type ControlFeature = Schemas['ControlFeature'];
export type ControlFeatureProperties = Schemas['ControlFeatureProperties'];
export type CitationDto = Schemas['CitationDto'];
export type TheaterStateDto = Schemas['TheaterStateDto'];
export type SnapshotRefDto = Schemas['SnapshotRefDto'];
export type IntervalDto = Schemas['IntervalDto'];
export type TimelineSnapshotDto = Schemas['TimelineSnapshotDto'];
export type SnapshotSourceDto = Schemas['SnapshotSourceDto'];
export type PaginatedSnapshots = Schemas['PaginatedResponseOfTimelineSnapshotDto'];
export type SourceDto = Schemas['SourceDto'];
export type RegimeDto = Schemas['RegimeDto'];
export type RegimeNameDto = Schemas['RegimeNameDto'];

/** `LocalizedText`：OpenAPI 只描述成 additionalProperties，這裡收斂成兩種語言（R4）。 */
export type LocalizedText = Partial<Record<'zh-Hant' | 'en', string>> & Record<string, string | undefined>;
