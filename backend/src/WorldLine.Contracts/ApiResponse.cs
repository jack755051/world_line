using System.Text.Json.Serialization;

namespace WorldLine.Contracts;

/// <summary>統一回應格式（PRD §7）：<c>{ statusCode, message, data }</c>。錯誤時另帶 <c>code</c>（§7 錯誤代碼）與欄位錯誤。</summary>
public sealed record ApiResponse<T>(
    int StatusCode,
    string Message,
    T? Data,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? Code = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] IReadOnlyDictionary<string, string[]>? Errors = null);

/// <summary>列表回應（PRD §7）。</summary>
public sealed record PaginatedResponse<T>(IReadOnlyList<T> Items, int Page, int PageSize, int Total);

/// <summary>PRD §7 錯誤代碼（AI 提案）。</summary>
public static class ErrorCodes
{
    public const string PeriodRequired = "PERIOD_REQUIRED";
    public const string SelfNameRequired = "SELF_NAME_REQUIRED";
    public const string ConflictingOfficialVersion = "CONFLICTING_OFFICIAL_VERSION";
    public const string OrphanExonym = "ORPHAN_EXONYM";
    public const string RevisionReasonRequired = "REVISION_REASON_REQUIRED";
    public const string CitationRequired = "CITATION_REQUIRED";
    public const string SourceNotQualified = "SOURCE_NOT_QUALIFIED";
    public const string InvalidTransition = "INVALID_TRANSITION";
    public const string VersionConflict = "VERSION_CONFLICT";
    public const string Unauthorized = "UNAUTHORIZED";

    // 以下為 PRD 未列、實作補上的通用代碼（待拍板）
    public const string ValidationFailed = "VALIDATION_FAILED";
    public const string NotFound = "NOT_FOUND";
    public const string Conflict = "CONFLICT";
    public const string WritesDisabled = "WRITES_DISABLED";
    public const string InternalError = "INTERNAL_ERROR";
}

/// <summary>健康檢查回應。</summary>
public sealed record HealthReportDto(string Status, IReadOnlyDictionary<string, string> Checks);
