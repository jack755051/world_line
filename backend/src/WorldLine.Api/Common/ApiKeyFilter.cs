using System.Security.Cryptography;
using System.Text;
using WorldLine.Contracts;

namespace WorldLine.Api.Common;

/// <summary>
/// 寫入端點的驗證（PRD §5 Auth：讀取公開；寫入用 <c>X-API-Key</c>，單一 key 存環境變數 <c>WORLDLINE_API_KEY</c>）。
/// 未設定 key 時一律拒絕寫入（503），避免「忘了設定」變成「完全裸露」。比對用固定時間比較。
/// </summary>
public sealed class ApiKeyFilter(IConfiguration configuration) : IEndpointFilter
{
    public const string HeaderName = "X-API-Key";
    public const string ConfigKey = "WORLDLINE_API_KEY";

    public async ValueTask<object?> InvokeAsync(EndpointFilterInvocationContext context, EndpointFilterDelegate next)
    {
        var expected = configuration[ConfigKey];
        if (string.IsNullOrWhiteSpace(expected))
        {
            return ApiResults.Fail(StatusCodes.Status503ServiceUnavailable, ErrorCodes.WritesDisabled,
                $"伺服器未設定 {ConfigKey}，所有寫入請求一律拒絕。");
        }

        var provided = context.HttpContext.Request.Headers[HeaderName].ToString();
        if (string.IsNullOrEmpty(provided) || !FixedTimeEquals(provided, expected))
        {
            return ApiResults.Fail(StatusCodes.Status401Unauthorized, ErrorCodes.Unauthorized,
                $"寫入端點需要有效的 {HeaderName} 標頭。");
        }

        return await next(context);
    }

    private static bool FixedTimeEquals(string a, string b) =>
        CryptographicOperations.FixedTimeEquals(Encoding.UTF8.GetBytes(a), Encoding.UTF8.GetBytes(b));
}
