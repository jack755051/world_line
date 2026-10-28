using NpgsqlTypes;

namespace WorldLine.Api.Api;

/// <summary>
/// 年份區間轉換。API 一律用「含頭含尾」的整數年（天文紀年：0 = 西元前 1 年），
/// DB 的 int4range 會正規化成 [起, 迄+1)。
/// </summary>
public static class Ranges
{
    public static NpgsqlRange<int> Closed(int from, int to) => new(from, true, to, true);

    public static NpgsqlRange<int> From(int from, int? to) =>
        to is null
            ? new NpgsqlRange<int>(from, true, false, 0, false, true)
            : Closed(from, to.Value);

    public static int Lower(NpgsqlRange<int> r) => r.LowerBoundIsInclusive ? r.LowerBound : r.LowerBound + 1;

    public static int? UpperInclusive(NpgsqlRange<int> r) =>
        r.UpperBoundInfinite ? null : r.UpperBoundIsInclusive ? r.UpperBound : r.UpperBound - 1;
}
