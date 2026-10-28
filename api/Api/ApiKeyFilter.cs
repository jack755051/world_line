using System.Security.Cryptography;
using System.Text;

namespace WorldLine.Api.Api;

/// <summary>
/// 寫入端點（POST/PATCH）的最小驗證（PRD §5 Auth 已拍板：單一 API Key，GET 公開）。
/// 金鑰來自環境變數／設定 WORLDLINE_API_KEY（只放 .env，不進版控），請求以標頭 X-Api-Key 帶入。
/// 未設定金鑰時一律拒絕寫入（503），避免「忘了設定」變成「完全裸露」。
/// </summary>
public sealed class ApiKeyFilter(IConfiguration configuration) : IEndpointFilter
{
    public const string HeaderName = "X-Api-Key";
    public const string ConfigKey = "WORLDLINE_API_KEY";

    public async ValueTask<object?> InvokeAsync(EndpointFilterInvocationContext context, EndpointFilterDelegate next)
    {
        var expected = configuration[ConfigKey];
        if (string.IsNullOrWhiteSpace(expected))
        {
            return Results.Problem(
                title: "寫入端點未啟用",
                detail: $"伺服器未設定 {ConfigKey}，所有寫入請求一律拒絕。",
                statusCode: StatusCodes.Status503ServiceUnavailable);
        }

        var provided = context.HttpContext.Request.Headers[HeaderName].ToString();
        if (string.IsNullOrEmpty(provided) || !FixedTimeEquals(provided, expected))
        {
            return Results.Problem(
                title: "未授權",
                detail: $"寫入端點需要有效的 {HeaderName} 標頭。",
                statusCode: StatusCodes.Status401Unauthorized);
        }

        return await next(context);
    }

    public static bool FixedTimeEquals(string a, string b) =>
        CryptographicOperations.FixedTimeEquals(Encoding.UTF8.GetBytes(a), Encoding.UTF8.GetBytes(b));
}
