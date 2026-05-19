@echo off
REM ---- Crea un enlace publico temporal para la app local ----
REM Requiere que iniciar.bat este ejecutandose en otra ventana.
echo Creando tunel publico (Cloudflare). Copia la URL https://...trycloudflare.com
"C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://localhost:8501 --no-autoupdate
pause
