@echo off
REM ---- Lanzador local del Comparador de Precios ----
cd /d "%~dp0"
echo Iniciando la aplicacion en http://localhost:8501 ...
"C:\Users\Comet\AppData\Local\Programs\Python\Python312\python.exe" -m streamlit run app.py --server.port 8501
pause
