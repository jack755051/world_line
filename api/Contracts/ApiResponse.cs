using Microsoft.AspNetCore.Http;

namespace WorldLine.Api.Contracts;

/// <summary>
/// 統一回應包裝格式（PRD §7、task 2.0 已拍板，2026-08-29 修訂）：三欄固定，沿用 sanring 慣例，
/// 不用 ASP.NET 內建 ProblemDetails。成功時 <see cref="Data"/> 放 resource；失敗時固定為 null。
/// <see cref="Message"/> 放 <see cref="ApiMessageCodes"/> 定義的穩定代碼，不是給人看的中文句子
/// ——前端自己查翻譯字典決定顯示文字。這代表單一代碼裝不下的細節（例如多筆欄位驗證各自的
/// 錯誤原因）目前會被犧牲掉，換取代碼本身穩定可依賴；仍不新增第 4 個欄位。
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
    public static ApiResponse<T> Ok<T>(T data, string code = ApiMessageCodes.FetchSuccess) =>
        new() { StatusCode = StatusCodes.Status200OK, Message = code, Data = data };

    public static ApiResponse<object?> Error(int statusCode, string code) =>
        new() { StatusCode = statusCode, Message = code, Data = null };
}
