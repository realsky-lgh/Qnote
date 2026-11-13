#!/usr/bin/env python3
"""
Qnote - 极简速记纸
即开即记，丝滑老手涂鸦，双击 Alt 呼出，双击 ~ 切换模式，10 款艺术护眼纸张。
"""
import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from qnote.app import QnoteApplication

def main():
    app = QnoteApplication(sys.argv)
    sys.exit(app.run())

if __name__ == "__main__":
    main()
