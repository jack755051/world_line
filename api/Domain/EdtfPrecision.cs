namespace WorldLine.Api.Domain;

/// <summary>EDTF 字串實際表達到哪個層級的時間精度（憲法 §9、notes §五、Story 5）。</summary>
public enum EdtfPrecision
{
    Year,
    Month,
    Day,
}
