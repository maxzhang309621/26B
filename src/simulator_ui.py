"""Read/click Wails WebView controls via UI Automation. Practice buttons only."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from practice_guard import (
    FORMAL_UI_MARKERS,
    PRACTICE_NAV,
    PRACTICE_RETURN,
    PRACTICE_START_BUTTON,
    FormalTestBlocked,
    assert_ui_not_formal,
    is_allowed_practice_click,
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
$target = $null
$want = ($ExactName -replace '\s','')
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


def click_practice(label: str, problem: int | None = None) -> None:
    if not is_allowed_practice_click(label, problem):
        raise FormalTestBlocked(f"拒绝点击非演练控件: {label!r}")
    inspect_and_guard()
    proc = _run_ps(_PS_CLICK, ["-ExactName", label])
    out = (proc.stdout or "").strip()
    if proc.returncode != 0 or not out.startswith("CLICKED"):
        raise RuntimeError(
            "未能点击演练按钮（WebView 默认不暴露网页按钮）。"
            "请用 scripts/launch_simulator_for_practice.bat 重新启动模拟器后再试，"
            f"或改用 --no-auto-start 并只点「{label}」。详情={out!r} code={proc.returncode}"
        )


def start_practice(problem: int) -> None:
    if problem not in PRACTICE_START_BUTTON:
        raise FormalTestBlocked(f"非法题号 {problem}")
    labels = inspect_and_guard()
    nav = normalize_label(PRACTICE_NAV)
    if any(normalize_label(x) == nav for x in labels):
        try:
            click_practice(PRACTICE_NAV, problem)
        except RuntimeError:
            pass
        inspect_and_guard()
    click_practice(PRACTICE_START_BUTTON[problem], problem)


def return_to_practice() -> None:
    inspect_and_guard()
    click_practice(PRACTICE_RETURN)
