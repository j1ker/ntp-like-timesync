#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ScapySync Slave应用入口

启动Slave主窗口应用。
"""

import sys
import os
from PyQt5.QtWidgets import QApplication

# 添加项目根目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

# 确保日志目录存在
os.makedirs("logs", exist_ok=True)

# 导入主窗口类
from slave.gui.main_window import SlaveMainWindow


def main():
    """应用主函数"""
    app = QApplication(sys.argv)
    window = SlaveMainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main() 