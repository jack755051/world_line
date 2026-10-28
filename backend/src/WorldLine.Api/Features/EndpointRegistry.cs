using WorldLine.Api.Common;

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
