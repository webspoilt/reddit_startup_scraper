@echo off
echo ===================================================
echo     FORCE OLLAMA TO USE NVIDIA GPU (GTX 1650)
echo ===================================================

echo [1/4] Stopping current Ollama process...
taskkill /IM "ollama.exe" /F 2>nul
taskkill /IM "ollama app.exe" /F 2>nul
timeout /t 2 /nobreak >nul

echo.
echo [2/4] Setting Environment Variables...
set OLLAMA_HOST=0.0.0.0:11434
set OLLAMA_ORIGINS=*
:: This tells applications to ONLY see the first dedicated GPU
set CUDA_VISIBLE_DEVICES=0
set OLLAMA_DEBUG=1

echo.
echo [3/4] Finding Ollama Path...
where ollama >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Could not find 'ollama' in PATH.
    echo Please reinstall Ollama or add it to your PATH.
    pause
    exit /b
)

echo.
echo [4/4] Starting Ollama with NVIDIA GPU Forced...
echo.
echo Keep this window open! Ollama is running here.
echo You should see logs below. Look for "NVIDIA" or "compute capability".
echo.

ollama serve

pause
