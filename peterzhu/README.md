# CUMCM 2026 B — Peterzhu 工作副本

本目录挂在团队仓库 [maxzhang309621/26B](https://github.com/maxzhang309621/26B) 的 **Peterzhu** 分支，不覆盖上游 `src/`。

正式测试三次机会不要动；只做演练。

## 目录

- `B题.pdf` / `附件/` 赛题
- `solution/` 建模与代码（含视频方案 `video_impl.py`）
- `模拟器/` 官方模拟器（**不入库**，体积过大）

## 运行

```powershell
cd solution
python solve_b.py              # 本地几何 + 旧策略
python video_impl.py           # 视频口径：七星 / MEC / 最坏情况第二点
python run_practice_only.py smoke
python run_video_practice.py q3   # 须先在模拟器点「演练」
```
