@echo off
cd /d "%~dp0"
start "vulnerable 5001" cmd /k ".venv\Scripts\activate && python -m crashpay.shop vulnerable"
start "fixed 5002" cmd /k ".venv\Scripts\activate && python -m crashpay.shop fixed"
start "ai-patched v1 5004" cmd /k ".venv\Scripts\activate && python run_shop.py patched_shop 5004"
start "ai-patched v2 5005" cmd /k ".venv\Scripts\activate && python run_shop.py patched_shop_v2 5005"
start "ai-patched v3 5006" cmd /k ".venv\Scripts\activate && python run_shop.py patched_shop_v3 5006"
start "ai-patched v4 5007" cmd /k ".venv\Scripts\activate && python run_shop.py patched_shop_v4 5007"
start "web 5000" cmd /k ".venv\Scripts\activate && python -m crashpay.web"