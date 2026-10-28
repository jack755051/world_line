FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src

COPY Directory.Build.props ./
COPY src/WorldLine.Contracts/WorldLine.Contracts.csproj src/WorldLine.Contracts/packages.lock.json src/WorldLine.Contracts/
COPY src/WorldLine.Api/WorldLine.Api.csproj src/WorldLine.Api/packages.lock.json src/WorldLine.Api/
RUN dotnet restore src/WorldLine.Api/WorldLine.Api.csproj --locked-mode

COPY src/ src/
# 建置期 OpenAPI 文件只在開發機產生（backend/openapi/v1.json），映像內不需要
RUN dotnet publish src/WorldLine.Api/WorldLine.Api.csproj -c Release -o /app --no-restore -p:OpenApiGenerateDocuments=false

FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS runtime
WORKDIR /app
COPY --from=build /app .
EXPOSE 8080
ENTRYPOINT ["dotnet", "WorldLine.Api.dll"]
