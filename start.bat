@echo off
echo Verifying bot integrity
python twb.py -i 2>NUL
if errorlevel 1 goto VERIFY_FAIL
python twb.py
goto :EOF
:VERIFY_FAIL
echo It looks like the bot failed to start.
echo Please try running the installer again or re-install the bot
echo If that does not fix the problem, please create an issue on https://github.com/stefan2200/TWB/issues
pause
goto :EOF
