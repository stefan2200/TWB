@echo off

echo Checking Python installation
goto :CHECK_PY

:CHECK_PY
python -V | find /v "Python" >NUL 2>NUL && (goto :PY_NO)
python -V | find "Python"    >NUL 2>NUL && (goto :PY_YAY)
goto :EOF

:PY_NO
echo Python is not installed on your system.
echo The download page should automatically open.
echo During installation please make sure that the Add Python 3.x to PATH is selected
start "" "https://www.python.org/downloads/windows/"
echo "After installing run this script again! Press enter to close this window"
pause
goto :EOF

:PY_YAY
for /f "delims=" %%V in ('python -V') do @set ver=%%V
echo Python, %ver% was found [OK]

echo Checking PIP installation
goto :CHECK_PIP

:CHECK_PIP
python -m pip --version | find /v "site-packages\pip" >NUL 2>NUL && (goto :PIP_NO)
python -m pip --version | find "site-packages\pip"    >NUL 2>NUL && (goto :PIP_YAY)
goto :EOF

:PIP_NO
echo Python pip.
echo The download page should automatically open.
start "" "https://pip.pypa.io/en/stable/installation/"
echo "After installing run this script again! Press enter to close this window"
pause
goto :EOF

:PIP_YAY
for /f "delims=" %%V in ('python -m pip --version') do @set ver=%%V
echo Python pip, %ver% was found [OK]
echo Installing and upgrading dependencies
python -m pip install --upgrade -r requirements.txt
echo Verifying bot integrity
python twb.py -i 2>NUL
if errorlevel 1 goto VERIFY_FAIL
echo Bot verify [OK]
pause
goto :EOF

:VERIFY_FAIL
echo It looks like the bot failed to start. If re-installing does not work, please create an issue on https://github.com/stefan2200/TWB/issues
pause
goto :EOF