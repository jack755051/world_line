using Microsoft.AspNetCore.Diagnostics;
using Microsoft.EntityFrameworkCore;
using Npgsql;
using WorldLine.Contracts;

namespace WorldLine.Api.Common;

/// <summary>把例外統一轉成 PRD §7 格式 <c>{ statusCode, message, data: null, code }</c>。</summary>
public sealed class ApiExceptionHandler(ILogger<ApiExceptionHandler> logger) : IExceptionHandler
{
    public async ValueTask<bool> TryHandleAsync(HttpContext http, Exception exception, CancellationToken ct)
    {
        var error = Map(exception);
        if (error.StatusCode >= 500) logger.LogError(exception, "Unhandled exception");
        await ApiResults.Fail(error).ExecuteAsync(http);
        return true;
    }

    public static ApiError Map(Exception exception)
    {
        switch (exception)
        {
            case ApiError e:
                return e;
            case BadHttpRequestException e:
                return new ApiError(e.StatusCode, ErrorCodes.ValidationFailed, $"請求格式錯誤：{e.Message}");
            case DbUpdateConcurrencyException:
                return new ApiError(409, ErrorCodes.VersionConflict, "資料已被其他請求修改，請重新讀取後再送出。");
        }

        var pg = Unwrap<PostgresException>(exception);
        if (pg is not null)
        {
            return pg.SqlState switch
            {
                PostgresErrorCodes.RestrictViolation =>
                    new ApiError(409, ErrorCodes.Conflict, $"I5：{pg.MessageText}"),
                PostgresErrorCodes.ExclusionViolation or PostgresErrorCodes.UniqueViolation =>
                    new ApiError(409, ErrorCodes.Conflict, $"資料衝突：{pg.ConstraintName}"),
                PostgresErrorCodes.ForeignKeyViolation =>
                    new ApiError(400, ErrorCodes.ValidationFailed, $"參照的資料不存在：{pg.ConstraintName}"),
                PostgresErrorCodes.CheckViolation or PostgresErrorCodes.NotNullViolation =>
                    new ApiError(400, ErrorCodes.ValidationFailed, $"違反資料約束：{pg.ConstraintName ?? pg.MessageText}"),
                _ => new ApiError(500, ErrorCodes.InternalError, "資料庫錯誤。"),
            };
        }

        return new ApiError(500, ErrorCodes.InternalError, "伺服器錯誤。");
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
