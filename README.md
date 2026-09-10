# 2026 高教社杯 B 题：无线电干扰源的快速自动定位与清除

本仓库是问题 1–4 的本地实现与官方模拟器**演练**客户端。默认只跑演练，**禁止启动正式测试**。

远程仓库：<https://github.com/maxzhang309621/26B.git>

## 目录

| 路径 | 内容 |
|------|------|
| `src/` | 几何、协议客户端、搜索策略、问题 3/4 入口、单元测试 |
| `scripts/` | 以无障碍方式启动官方模拟器（便于自动点演练按钮） |
| `docs/pipeline/` | 架构、算法方案、实现记录 |
| `data/` | 附件 1/2 拷贝 |
| `output/figures/` | 问题 1/2 示意图 |

官方模拟器 `Jammers-simulator/` 中的 exe 与运行数据不入库，需自行安装。

## 环境

Python 3.10+。

```text
pip install -r requirements.txt
```

## 本地测试（不连官方模拟器）

```text
cd src
python -m unittest tests.test_geometry tests.test_protocol tests.test_q3 tests.test_q4 tests.test_practice_guard
python q1_cli.py
```

## 官方演练（不要做正式测试）

1. 启动模拟器并登录，停在「演练测试」。
2. 将队号写入 `robot_id.txt`（可先复制 `robot_id.txt.example`），或使用 `--robot-id`。
3. 单局：

```text
cd src
python run_drill.py --problem 3 --robot-id <队号>
python run_drill.py --problem 4 --robot-id <队号>
```

4. 批量演练：

```text
python run_practice_batch.py --robot-id <队号> --repeat-3 3 --repeat-4 3 --no-auto-start
```

`--auto-start` 会尝试点击「开始问题X演练测试」。若点不到，用 `scripts/launch_simulator_for_practice.bat` 启动模拟器后再试，或改用 `--no-auto-start` 手动只点演练按钮。

程序会拒绝 `--formal` / `--official`，并在发现正式测试日志或正式测试界面文案时中止。

## 协议

机器狗仅四条指令：`POST /enter` `/measure` `/clear` `/exit`，默认 `http://127.0.0.1:2026`。移动与切频由 `/measure` 的坐标和频道推断；`/clear` 不切频。
