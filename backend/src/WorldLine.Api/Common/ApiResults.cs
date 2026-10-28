using WorldLine.Contracts;

namespace WorldLine.Api.Common;

/// <summary>產生 PRD §7 統一格式 <c>{ statusCode, message, data }</c> 的回應。</summary>
public static class ApiResults
{
    public static IResult Ok<T>(T data, string message = "OK") =>
        TypedResults.Json(new ApiResponse<T>(StatusCodes.Status200OK, message, data), statusCode: StatusCodes.Status200OK);

    public static IResult Created<T>(string location, T data, string message = "Created") =>
        new CreatedEnvelope<T>(location, new ApiResponse<T>(StatusCodes.Status201Created, message, data));

    public static IResult Fail(int statusCode, string code, string message, IReadOnlyDictionary<string, string[]>? errors = null) =>
        TypedResults.Json(new ApiResponse<object>(statusCode, message, null, code, errors), statusCode: statusCode);

    public static IResult Fail(ApiError error) => Fail(error.StatusCode, error.Code, error.Message, error.Errors);

    private sealed class CreatedEnvelope<T>(string location, ApiResponse<T> body) : IResult
    {
        public Task ExecuteAsync(HttpContext httpContext)
        {
            httpContext.Response.Headers.Location = location;
            return TypedResults.Json(body, statusCode: StatusCodes.Status201Created).ExecuteAsync(httpContext);
        }
    }
}

/// <summary>可預期的業務規則錯誤（I1–I6、R7 等）。由 <see cref="ApiExceptionHandler"/> 轉成統一格式。</summary>
public sealed class ApiError(int statusCode, string code, string message, IReadOnlyDictionary<string, string[]>? errors = null)
    : Exception(message)
{
    public int StatusCode { get; } = statusCode;
    public string Code { get; } = code;
    public IReadOnlyDictionary<string, string[]>? Errors { get; } = errors;

    public static ApiError BadRequest(string code, string message, string? field = null) =>
        new(StatusCodes.Status400BadRequest, code, message,
            field is null ? null : new Dictionary<string, string[]> { [field] = [message] });

    public static ApiError NotFound(string what) =>
        new(StatusCodes.Status404NotFound, ErrorCodes.NotFound, $"找不到{what}。");
}
