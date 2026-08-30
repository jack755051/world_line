using System.Security.Cryptography;
using System.Text;
using WorldLine.Api.Contracts;

namespace WorldLine.Api.Infrastructure;

/// <summary>
/// task 2.14：寫入端點（POST/PATCH）的最小 API Key 驗證（PRD §5 已拍板：單一固定
/// key，讀取端點第一階段完全公開；JWT／多使用者帳號不在這個階段範圍，等真的開放教育
/// 對象時再評估升級）。比對 request header <c>X-API-Key</c> 是否等於環境變數
/// <c>API_WRITE_KEY</c>（本機開發放在 repo 根目錄的 <c>.env</c>，透過
/// <c>docker-compose.yml</c> 的 <c>env_file</c> 注入容器）。
///
/// **只擋 POST/PATCH，不是整個 pipeline 都要驗證**：這個 API 目前設計上也只有這兩種
/// 寫入動詞（沒有 PUT/DELETE 端點），GET 端點完全不掛這層檢查，符合已拍板的「讀取端點
/// 第一階段公開」。
/// </summary>
public class ApiWriteKeyMiddleware(RequestDelegate next, IConfiguration configuration, ILogger<ApiWriteKeyMiddleware> logger)
{
    private const string ApiKeyHeaderName = "X-API-Key";

    private static readonly HashSet<string> WriteMethods =
        new(StringComparer.OrdinalIgnoreCase) { HttpMethods.Post, HttpMethods.Patch };

    public async Task InvokeAsync(HttpContext context)
    {
        if (!WriteMethods.Contains(context.Request.Method))
        {
            await next(context);
            return;
        }

        var expectedKey = configuration["API_WRITE_KEY"];

        // 沒設定 API_WRITE_KEY 時，不能讓「沒設定」等同於「不驗證」——那樣一個忘記設定
        // 環境變數的部署會意外變成完全不設防的寫入端點，比明確擋下所有寫入請求更危險。
        // 這是設定錯誤（500），不是呼叫端的問題（401），錯誤碼要分開。
        if (string.IsNullOrEmpty(expectedKey))
        {
            logger.LogError("API_WRITE_KEY 未設定，寫入端點 {Method} {Path} 已擋下", context.Request.Method, context.Request.Path);
            await WriteErrorAsync(context, StatusCodes.Status500InternalServerError, ApiMessageCodes.InternalError);
            return;
        }

        var providedKey = context.Request.Headers[ApiKeyHeaderName].FirstOrDefault();
        if (providedKey is null || !FixedTimeEquals(providedKey, expectedKey))
        {
            await WriteErrorAsync(context, StatusCodes.Status401Unauthorized, ApiMessageCodes.Unauthorized);
            return;
        }

        await next(context);
    }

    /// <summary>用固定時間比較，不是字串 <c>==</c>——API key 比對是這個專案目前唯一的
    /// 安全邊界，避免用回應時間側錄出正確字元。單人自用階段風險很低，但這個防護幾乎
    /// 零成本，沒有理由不做對。</summary>
    private static bool FixedTimeEquals(string provided, string expected)
    {
        var providedBytes = Encoding.UTF8.GetBytes(provided);
        var expectedBytes = Encoding.UTF8.GetBytes(expected);
        // CryptographicOperations.FixedTimeEquals 要求等長輸入；長度不等本身已經洩漏一點點
        // timing 資訊，但那是長度差異、不是內容差異，是可接受的已知取捨，不逐字元比較。
        if (providedBytes.Length != expectedBytes.Length)
        {
            return false;
        }
        return CryptographicOperations.FixedTimeEquals(providedBytes, expectedBytes);
    }

    private static async Task WriteErrorAsync(HttpContext context, int statusCode, string code)
    {
        context.Response.StatusCode = statusCode;
        await context.Response.WriteAsJsonAsync(ApiResponse.Error(statusCode, code));
    }
}
