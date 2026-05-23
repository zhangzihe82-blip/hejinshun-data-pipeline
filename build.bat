@echo off
chcp 65001 >nul
echo ============================================
echo    和金顺数据平台 - 打包脚本
echo ============================================
echo.

echo [1/3] 清理旧文件...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
del /q *.spec 2>nul
echo    完成

echo.
echo [2/3] 打包仪表盘应用...
pyinstaller --onefile --windowed --name "和金顺数据仪表盘" --add-data "templates;templates" main.py
echo    完成

echo.
echo [3/3] 清理临时文件...
rmdir /s /q build
del /q *.spec
echo    完成

echo.
echo ============================================
echo    打包成功！
echo    输出目录: dist\和金顺数据仪表盘.exe
echo ============================================
echo.
pause
