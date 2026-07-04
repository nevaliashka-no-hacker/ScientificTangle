#!/usr/bin/env python
import subprocess
import sys
import os
from pathlib import Path

def check_dependencies():
    required = ["streamlit", "pyvis", "pandas"]
    missing = []
    
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
            
    if missing:
        print(f"Установите недостающие пакеты: pip install {' '.join(missing)}")
        return False
    return True

def main():
    print("Запуск ScientificTangle Frontend")
    print("-" * 40)
    
    if not check_dependencies():
        sys.exit(1)
        
    script_path = Path(__file__).parent / "app.py"
    
    if not script_path.exists():
        print(f"Ошибка: {script_path} не найден")
        sys.exit(1)
        
    cmd = [
        "streamlit", "run",
        str(script_path),
        "--server.port", "8501",
        "--server.address", "0.0.0.0",
        "--browser.gatherUsageStats", "false"
    ]
    
    print(f"Запуск: {' '.join(cmd)}")
    print("Откройте браузер по адресу: http://localhost:8501")
    print("-" * 40)
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nОстановка сервера...")
    except Exception as e:
        print(f"Ошибка запуска: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()