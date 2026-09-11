"""Read/click Wails WebView controls via UI Automation. Practice buttons only.

Never clicks by screen coordinates. Never Invoke a control whose name contains 正式.
PowerShell also aborts if a formal-activation dialog is visible.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from practice_guard import (
    FORMAL_UI_MARKERS,
    PRACTICE_NAV,
    PRACTICE_RETURN,
    PRACTICE_START_BUTTON,
    Q3_PRACTICE_DONE_ACK,
    Q3_PRACTICE_START,
    Q4_PRACTICE_DONE_ACK,
    Q4_PRACTICE_START,
    FormalTestBlocked,
    assert_no_formal_activation,
    assert_safe_click_target,
    assert_ui_not_formal,
    can_ack_q3_practice_done,
    can_ack_q4_practice_done,
    is_allowed_practice_click,
    is_allowed_q3_practice_click,
    is_allowed_q4_practice_click,
    normalize_label,
)

_PS_LIST = r"""
Add-Type -AssemblyName UIAutomationClient
$root = [System.Windows.Automation.AutomationElement]::RootElement
$cond = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ClassNameProperty,
    'WailsWebviewWindow'
)
$win = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $cond)
if (-not $win) { Write-Output 'NO_WINDOW'; exit 0 }
$all = $win.FindAll(
    [System.Windows.Automation.TreeScope]::Descendants,
    [System.Windows.Automation.Condition]::TrueCondition
)
foreach ($el in $all) {
    $name = $el.Current.Name
    if ([string]::IsNullOrWhiteSpace($name)) { continue }
    Write-Output $name
}
"""

# Extra lock inside the click helper: refuse forbidden names and abort if a
# formal-activation dialog is on screen. Exact name match only (never substring).
_PS_CLICK = r"""
param([Parameter(Mandatory=$true)][string]$ExactName)
Add-Type -AssemblyName UIAutomationClient
$root = [System.Windows.Automation.AutomationElement]::RootElement
$cond = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ClassNameProperty,
    'WailsWebviewWindow'
)
$win = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $cond)
if (-not $win) { Write-Output 'NO_WINDOW'; exit 3 }
$all = $win.FindAll(
    [System.Windows.Automation.TreeScope]::Descendants,
    [System.Windows.Automation.Condition]::TrueCondition
)
$want = ($ExactName -replace '\s','')
if ($want -match '正式' -or $want -eq '确认开始' -or $want -eq '再次确认开始' -or $want -eq '开始正式测试') {
    Write-Output ('DENIED_NAME|' + $ExactName)
    exit 8
}
$deny = @(
    '即将开始问题3正式测试','即将开始问题4正式测试',
    '再次确认开始','开始正式测试','确认开始'
)
foreach ($el in $all) {
    $name = $el.Current.Name
    if ([string]::IsNullOrWhiteSpace($name)) { continue }
    $got = ($name -replace '\s','')
    if ($deny -contains $got) {
        Write-Output ('FORMAL_DIALOG|' + $name)
        exit 9
    }
}
$target = $null
foreach ($el in $all) {
    $name = $el.Current.Name
    if ([string]::IsNullOrWhiteSpace($name)) { continue }
    $got = ($name -replace '\s','')
    if ($got -eq $want) { $target = $el; break }
}
if (-not $target) { Write-Output 'NOT_FOUND'; exit 4 }
try {
    $pat = $target.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
    $pat.Invoke()
    Write-Output 'CLICKED'
} catch {
    Write-Output ('NO_INVOKE|' + $_.Exception.Message)
    exit 5
}
"""


def _run_ps(script: str, args: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    with tempfile.NamedTemporaryFile(
        "w", suffix=".ps1", delete=False, encoding="utf-8-sig"
    ) as fh:
        fh.write(script)
        path = fh.name
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        path,
    ]
    if args:
        cmd.extend(args)
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    finally:
        Path(path).unlink(missing_ok=True)


def list_control_names() -> list[str]:
    proc = _run_ps(_PS_LIST)
    lines = [ln.strip() for ln in (proc.stdout or "").splitlines() if ln.strip()]
    if lines == ["NO_WINDOW"]:
        return []
    return lines


def inspect_and_guard() -> list[str]:
    labels = list_control_names()
    assert_ui_not_formal(labels)
    for lab in labels:
        for marker in FORMAL_UI_MARKERS:
            if normalize_label(marker) == normalize_label(lab):
                raise FormalTestBlocked(f"禁止正式测试：控件 {lab!r}")
    return labels


def _invoke_exact(label: str) -> str:
    assert_safe_click_target(label)
    proc = _run_ps(_PS_CLICK, ["-ExactName", label])
    out = (proc.stdout or "").strip()
    if "FORMAL_DIALOG" in out or proc.returncode == 9:
        raise FormalTestBlocked(f"点击前发现正式测试确认框，已中止且未再点: {out}")
    if "DENIED_NAME" in out or proc.returncode == 8:
        raise FormalTestBlocked(f"底层拒绝点击: {out}")
    if proc.returncode != 0 or not out.startswith("CLICKED"):
        raise RuntimeError(out or f"click failed code={proc.returncode}")
    return out


def click_practice(label: str, problem: int | None = None) -> None:
    assert_safe_click_target(label)
    if not is_allowed_practice_click(label, problem):
        raise FormalTestBlocked(f"拒绝点击非演练控件: {label!r}")
    labels = list_control_names()
    assert_no_formal_activation(labels)
    try:
        _invoke_exact(label)
    except RuntimeError as exc:
        raise RuntimeError(
            "未能点击演练按钮（WebView 默认不暴露网页按钮）。"
            "请用 scripts/launch_simulator_for_practice.bat 重新启动模拟器后再试，"
            f"或改用 --no-auto-start 并只点「{label}」。详情={exc}"
        ) from exc


def click_q3_practice_start() -> None:
    """Only Invoke the exact Q3 practice button. Never 正式, never 问题4, never coordinates."""
    if not is_allowed_q3_practice_click(Q3_PRACTICE_START):
        raise FormalTestBlocked("内部白名单错误：拒绝问题3演练按钮")
    assert_safe_click_target(Q3_PRACTICE_START)
    labels = list_control_names()
    assert_no_formal_activation(labels)
    if not any(normalize_label(lab) == normalize_label(Q3_PRACTICE_START) for lab in labels):
        raise RuntimeError("UIA 未找到「开始问题3演练测试」（需无障碍启动模拟器）")
    _invoke_exact(Q3_PRACTICE_START)
    assert_no_formal_activation(list_control_names())


def click_q3_practice_done_ack() -> bool:
    """Dismiss 「问题3演练测试完成」. Never click 正式测试的确认开始."""
    labels = list_control_names()
    assert_no_formal_activation(labels)
    if not can_ack_q3_practice_done(labels):
        return False
    assert_safe_click_target(Q3_PRACTICE_DONE_ACK)
    _invoke_exact(Q3_PRACTICE_DONE_ACK)
    return True


def click_q4_practice_start() -> None:
    """Only Invoke the exact Q4 practice button. Never 正式, never 问题3, never coordinates."""
    if not is_allowed_q4_practice_click(Q4_PRACTICE_START):
        raise FormalTestBlocked("内部白名单错误：拒绝问题4演练按钮")
    assert_safe_click_target(Q4_PRACTICE_START)
    labels = list_control_names()
    assert_no_formal_activation(labels)
    if not any(normalize_label(lab) == normalize_label(Q4_PRACTICE_START) for lab in labels):
        raise RuntimeError("UIA 未找到「开始问题4演练测试」（需无障碍启动模拟器）")
    _invoke_exact(Q4_PRACTICE_START)
    assert_no_formal_activation(list_control_names())


def click_q4_practice_done_ack() -> bool:
    """Dismiss 「问题4演练测试完成」. Never click 正式测试的确认开始."""
    labels = list_control_names()
    assert_no_formal_activation(labels)
    if not can_ack_q4_practice_done(labels):
        return False
    assert_safe_click_target(Q4_PRACTICE_DONE_ACK)
    _invoke_exact(Q4_PRACTICE_DONE_ACK)
    return True


def click_return_practice() -> None:
    if not is_allowed_q4_practice_click(PRACTICE_RETURN):
        raise FormalTestBlocked("拒绝返回非演练页")
    assert_safe_click_target(PRACTICE_RETURN)
    labels = list_control_names()
    assert_no_formal_activation(labels)
    _invoke_exact(PRACTICE_RETURN)


def start_practice(problem: int) -> None:
    if problem not in PRACTICE_START_BUTTON:
        raise FormalTestBlocked(f"非法题号 {problem}")
    labels = list_control_names()
    assert_no_formal_activation(labels)
    nav = normalize_label(PRACTICE_NAV)
    if any(normalize_label(x) == nav for x in labels):
        try:
            click_practice(PRACTICE_NAV, problem)
        except RuntimeError:
            pass
        assert_no_formal_activation(list_control_names())
    click_practice(PRACTICE_START_BUTTON[problem], problem)


def return_to_practice() -> None:
    assert_no_formal_activation(list_control_names())
    click_practice(PRACTICE_RETURN)
