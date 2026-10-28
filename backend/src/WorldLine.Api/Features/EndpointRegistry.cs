using WorldLine.Api.Common;
using WorldLine.Contracts;

namespace WorldLine.Api.Features;

/// <summary>集中註冊 <c>/api/v1</c> 底下的 Feature 端點。讀取公開；寫入群組一律掛 <see cref="ApiKeyFilter"/>。</summary>
public static class EndpointRegistry
{
    public static void Map(RouteGroupBuilder api)
    {
        var write = api.MapGroup("").AddEndpointFilter<ApiKeyFilter>();

        SourcesEndpoints.Map(api, write);
        RegimesEndpoints.Map(api, write);
        TheatersEndpoints.Map(write);
        ControlEndpoints.Map(api, write);
        TimelineEndpoints.Map(api);
    }

    /// <summary>OpenAPI：成功回應為 <c>ApiResponse&lt;T&gt;</c>（200）。</summary>
    public static RouteHandlerBuilder Ok<T>(this RouteHandlerBuilder b) =>
        b.Produces<ApiResponse<T>>(StatusCodes.Status200OK);

    /// <summary>OpenAPI：建立成功回應為 <c>ApiResponse&lt;T&gt;</c>（201）。</summary>
    public static RouteHandlerBuilder Created<T>(this RouteHandlerBuilder b) =>
        b.Produces<ApiResponse<T>>(StatusCodes.Status201Created);

    /// <summary>OpenAPI：錯誤回應同為統一格式（data 為 null，另帶 code）。</summary>
    public static RouteHandlerBuilder Errors(this RouteHandlerBuilder b, params int[] statusCodes)
    {
        foreach (var code in statusCodes) b.Produces<ApiResponse<object>>(code);
        return b;
    }

    /// <summary>寫入端點在 OpenAPI 標示需要 ApiKey。</summary>
    public static RouteHandlerBuilder RequiresApiKey(this RouteHandlerBuilder b) =>
        b.AddOpenApiOperationTransformer((op, _, _) =>
        {
            op.Security ??= [];
            op.Security.Add(new Microsoft.OpenApi.OpenApiSecurityRequirement
            {
                [new Microsoft.OpenApi.OpenApiSecuritySchemeReference("ApiKey")] = [],
            });
            return Task.CompletedTask;
        });
}
