using Microsoft.AspNetCore.Http;

namespace WorldLine.Api.Contracts;

/// <summary>
/// 統一回應包裝格式（PRD §7、task 2.0 已拍板）：三欄固定，沿用 sanring 慣例，不用 ASP.NET
/// 內建 ProblemDetails。成功時 <see cref="Data"/> 放 resource；失敗時固定為 null，多筆欄位
/// 驗證錯誤併入 <see cref="Message"/>（分號串接），不新增第 4 個欄位。
/// </summary>
public class ApiResponse<T>
{
    public required int StatusCode { get; init; }
    public required string? Message { get; init; }
    public required T? Data { get; init; }
}

/// <summary>建構 <see cref="ApiResponse{T}"/> 的靜態輔助方法，讓 controller 不用每次手動組欄位。</summary>
public static class ApiResponse
{
    public static ApiResponse<T> Ok<T>(T data, string message = "OK") =>
        new() { StatusCode = StatusCodes.Status200OK, Message = message, Data = data };

    public static ApiResponse<object?> Error(int statusCode, string message) =>
        new() { StatusCode = statusCode, Message = message, Data = null };
}
