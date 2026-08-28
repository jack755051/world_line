namespace WorldLine.Api.Domain;

/// <summary>
/// EDTF 尾綴不確定性標記（憲法 §9「模糊/爭議日期處理」、Story 5 AC）。只支援 EDTF 子集裡
/// 實際會用到的兩種：'?'（不確定）與 '~'（推測/近似）。不支援 '%'（兩者皆是，EDTF 完整規格
/// 才有）——憲法/PRD/notes 都沒有點名要用，過度設計，真的遇到需求再擴充。
/// </summary>
public enum EdtfQualifier
{
    None,
    Uncertain,   // 尾綴 '?'
    Approximate, // 尾綴 '~'
}
