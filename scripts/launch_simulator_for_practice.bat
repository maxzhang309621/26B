@echo off
REM Launch the official simulator with renderer accessibility so practice
REM buttons can be clicked by run_practice_batch.py --auto-start.
REM Do NOT use this to start formal tests. Login and stay on 演练测试.
cd /d "%~dp0..\Jammers-simulator"
set WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--force-renderer-accessibility
start "" "jammers-simulator.exe"
echo Started jammers-simulator.exe with accessibility. Use only 演练测试.
