using Microsoft.AspNetCore.Diagnostics;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Npgsql;
using WorldLine.Api.Data;

namespace WorldLine.Api.Api;

/// <summary>把例外統一轉成 RFC 9457 ProblemDetails（application/problem+json）。</summary>
public sealed class ProblemExceptionHandler(IProblemDetailsService problemDetails, ILogger<ProblemExceptionHandler> logger)
    : IExceptionHandler
{
    public async ValueTask<bool> TryHandleAsync(HttpContext http, Exception exception, CancellationToken ct)
    {
        var (status, title, detail) = Map(exception);
        if (status >= 500) logger.LogError(exception, "Unhandled exception");

        http.Response.StatusCode = status;
        return await problemDetails.TryWriteAsync(new ProblemDetailsContext
        {
            HttpContext = http,
            Exception = exception,
            ProblemDetails = new ProblemDetails { Status = status, Title = title, Detail = detail },
        });
    }

    public static (int Status, string Title, string? Detail) Map(Exception exception)
    {
        switch (exception)
        {
            case MissingChangeReasonException e:
                return (400, "缺少修改原因", e.Message);
            case DbUpdateConcurrencyException:
                return (409, "版本衝突", "資料已被其他請求修改，請重新讀取後再送出（樂觀併發）。");
            case BadHttpRequestException e:
                return (e.StatusCode, "請求格式錯誤", e.Message);
        }

        var pg = Unwrap<PostgresException>(exception);
        if (pg is not null)
        {
            return pg.SqlState switch
            {
                PostgresErrorCodes.ExclusionViolation =>
                    (409, "I3 衝突：同政權同時間已有正式疆域", $"{pg.ConstraintName}：請改為修正既有版本，或標記為爭議並存（isDisputed）。"),
                PostgresErrorCodes.RestrictViolation => (409, "I5：史料不可刪除", pg.MessageText),
                PostgresErrorCodes.UniqueViolation => (409, "資料重複", pg.ConstraintName),
                PostgresErrorCodes.ForeignKeyViolation => (400, "參照的資料不存在", pg.ConstraintName),
                PostgresErrorCodes.CheckViolation or PostgresErrorCodes.NotNullViolation =>
                    (400, "違反資料約束", pg.ConstraintName is { } c ? $"{c}：{pg.MessageText}" : pg.MessageText),
                _ => (500, "資料庫錯誤", null),
            };
        }

        return (500, "伺服器錯誤", null);
    }

    private static T? Unwrap<T>(Exception? e) where T : Exception
    {
        while (e is not null)
        {
            if (e is T t) return t;
            e = e.InnerException;
        }
        return null;
    }
}
