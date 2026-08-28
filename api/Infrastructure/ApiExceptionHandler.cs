using Microsoft.AspNetCore.Diagnostics;
using WorldLine.Api.Contracts;

namespace WorldLine.Api.Infrastructure;

/// <summary>
/// 讓未捕捉例外也回傳統一包裝格式（task 2.0），不是 ASP.NET 預設的 ProblemDetails。
/// </summary>
public class ApiExceptionHandler(ILogger<ApiExceptionHandler> logger) : IExceptionHandler
{
    public async ValueTask<bool> TryHandleAsync(HttpContext httpContext, Exception exception, CancellationToken cancellationToken)
    {
        logger.LogError(exception, "Unhandled exception while processing {Path}", httpContext.Request.Path);

        httpContext.Response.StatusCode = StatusCodes.Status500InternalServerError;
        await httpContext.Response.WriteAsJsonAsync(
            ApiResponse.Error(StatusCodes.Status500InternalServerError, "系統發生未預期錯誤"),
            cancellationToken);

        return true;
    }
}
