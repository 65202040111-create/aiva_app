@echo off







REM 







REM 







REM 















REM 







if exist "venv\Scripts\activate.bat" (







    call venv\Scripts\activate.bat







)















REM 







start "" python app.py















REM 







timeout /t 3 >nul















REM 







start http://127.0.0.1:5000















echo Flask กำลังรัน... กด Ctrl+C เพื่อหยุด







pause