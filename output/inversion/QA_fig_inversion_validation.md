# QA：fig_inversion_validation

- 脚本：`src/figures/fig_inversion_validation.py`
- 主文件：`output/inversion/fig_inversion_validation.pdf`（矢量）
- 预览：`output/inversion/fig_inversion_validation.png`（300 dpi）
- 数据：mock 问题 3，seed 0，10 个全向源；**未抽样**

## Figure contract

- **结论（3 秒）**：角扇交会可行域包含真源；点估计 RMSE 约 11.5 m；示向残差全部落在 ±1° 内。
- **证据链**
  - a：测站与 ±1.01° 角扇（机制）
  - b：可行域 + 包围圆叠真值（包含性）
  - c：10 个源的估计 vs 真值（空间精度，全部点）
  - d：21 条示向残差与 ±1° 带（误差模型）
- **原型**：asymmetric mixed（a/b 机制，c/d 定量）
- **版式**：双栏 183 mm × 142 mm；RGB；矢量 PDF + 300 dpi PNG
- **风险**：无假设检验（几何包含，非组间比较）；直方图 n=21 已加 rug；中文投稿将 YaHei 置于 Arial 之前

## Pass 0–3

| 项 | 结果 |
|----|------|
| AP-0 三套 baseline | PASS（随后为国赛中文覆盖 `font.sans-serif`） |
| AP-1/2 默认色 / jet | PASS（CATEGORICAL + 蓝序色） |
| AP-3 去顶右边框 | PASS |
| AP-4 图例遮挡 | PASS（a 内左下空白区；d 改为注记） |
| AP-5 矢量导出 | PASS |
| AP-6 小样本散点 | PASS（c 画出全部 n=10） |
| AP-7 字体 | PASS（Arial 仍在列表；中文用 YaHei） |
| CL 字号 ≥5 pt | PASS |
| VI 未丢点 | PASS（10 频道、21 残差） |
| VV 渲染 | PASS（无缺字告警） |

## 统计与可重复

| 量 | 定义 | 值 |
|----|------|-----|
| n（c） | 有两站以上示向且得到点估计的频道 | 10 |
| n（d） | 上述频道全部 `direction` 残差条数 | 21 |
| 中心 | 定位误差算术平均 | 10.23 m |
| 离散 | RMSE \(\sqrt{\sum e_i^2/n}\) | 11.48 m |
| 残差 | \(\theta_{\mathrm{true}}-\mathrm{svd}\) | 均值 −0.149°，最大绝对值 0.980° |
| 检验 | 无（有界误差带包含，非显著性检验） | — |
| 来源 | `invert_cli._run_mock_case`，seed=0，全向 10 源 | 可复现 |

生产资产 `assets/figures/` 未随精简安装提供，四面板均为 **param inherit / cross-type**，非 native run。
