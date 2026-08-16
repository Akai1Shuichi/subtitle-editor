"""Launcher — chạy file này thay vì src/main.py trực tiếp."""
import sys
from pathlib import Path

# Đảm bảo thư mục gốc project nằm trong sys.path
sys.path.insert(0, str(Path(__file__).parent))

from src.main import main

if __name__ == "__main__":
    main()
