#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Slave应用主窗口

提供用户界面显示同步状态、时钟偏移量图表和控制同步。
"""

import sys
import os
import datetime
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QTextEdit, QGroupBox, QFrame, QSplitter,
    QStatusBar
)
from PyQt5.QtCore import QTimer, QDateTime, Qt, pyqtSlot
from PyQt5.QtGui import QIcon, QColor, QFont, QPainter

# 导入共享模块
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from common.config import (
    MASTER_IP, SYNC_PORT, LOG_FILE_SLAVE, CHART_UPDATE_INTERVAL
)
from common.utils.logger import setup_logger

# 导入Slave模块
from slave.core.software_clock import SoftwareClock
from slave.core.sync_monitor import SyncMonitor
from slave.core.sync_controller import SyncController, SyncStatus
from slave.gui.chart_widget import SyncChartView


class StatusIndicator(QFrame):
    """状态指示器组件
    
    显示主节点在线状态的圆形指示器。
    """
    
    def __init__(self, parent=None):
        """初始化状态指示器
        
        Args:
            parent: 父部件
        """
        super().__init__(parent)
        
        # 设置固定大小
        self.setFixedSize(20, 20)
        
        # 设置边框
        self.setFrameShape(QFrame.Box)
        self.setFrameShadow(QFrame.Sunken)
        
        # 默认为离线状态（红色）
        self.online = False
        
    def set_online(self, online):
        """设置在线状态
        
        Args:
            online: 是否在线
        """
        if self.online != online:
            self.online = online
            self.update()
    
    def paintEvent(self, event):
        """绘制事件处理
        
        Args:
            event: 绘制事件
        """
        super().paintEvent(event)
        
        # 创建绘制器
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 设置颜色
        if self.online:
            color = QColor(0, 180, 0)  # 绿色表示在线
        else:
            color = QColor(220, 0, 0)  # 红色表示离线
        
        # 绘制圆形
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(3, 3, 14, 14)


class SlaveMainWindow(QMainWindow):
    """Slave应用主窗口类"""
    
    def __init__(self):
        """初始化主窗口"""
        super().__init__()
        
        # 设置日志记录器
        self.logger = setup_logger('slave.gui', LOG_FILE_SLAVE)
        
        # 创建核心组件
        self.software_clock = SoftwareClock(LOG_FILE_SLAVE)
        self.sync_monitor = SyncMonitor(LOG_FILE_SLAVE)
        self.sync_controller = SyncController(
            self.software_clock, self.sync_monitor, LOG_FILE_SLAVE
        )
        
        # 连接信号
        self.sync_monitor.status_changed.connect(self.on_master_status_changed)
        self.sync_monitor.sync_status_changed.connect(self.on_sync_status_changed)
        
        # 初始化UI
        self.init_ui()
        
        # 创建定时器更新UI
        self.ui_timer = QTimer(self)
        self.ui_timer.timeout.connect(self.update_ui)
        self.ui_timer.start(100)  # 每100毫秒更新一次
        
        # 创建图表更新定时器
        self.chart_timer = QTimer(self)
        self.chart_timer.timeout.connect(self.update_chart)
        self.chart_timer.start(CHART_UPDATE_INTERVAL)
        
        self.logger.info("Slave应用已启动")
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("ScapySync Slave")
        self.setGeometry(100, 100, 1000, 800)
        
        # 创建中央部件
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 状态组
        status_group = QGroupBox("系统状态")
        status_layout = QGridLayout()
        
        # 当前时间
        self.lbl_current_time_title = QLabel("当前时钟时间:")
        self.lbl_current_time = QLabel()
        self.lbl_current_time.setStyleSheet("font-size: 16pt; font-weight: bold;")
        status_layout.addWidget(self.lbl_current_time_title, 0, 0)
        status_layout.addWidget(self.lbl_current_time, 0, 1)
        
        # 主节点状态
        self.lbl_master_status_title = QLabel("主节点状态:")
        self.master_status_indicator = StatusIndicator()
        self.lbl_master_status = QLabel("离线")
        status_layout.addWidget(self.lbl_master_status_title, 1, 0)
        
        master_status_layout = QHBoxLayout()
        master_status_layout.addWidget(self.master_status_indicator)
        master_status_layout.addWidget(self.lbl_master_status)
        master_status_layout.addStretch()
        
        status_layout.addLayout(master_status_layout, 1, 1)
        
        # 同步状态
        self.lbl_sync_status_title = QLabel("同步状态:")
        self.lbl_sync_status = QLabel("已停止")
        status_layout.addWidget(self.lbl_sync_status_title, 2, 0)
        status_layout.addWidget(self.lbl_sync_status, 2, 1)
        
        # 偏移量
        self.lbl_offset_title = QLabel("当前偏移量:")
        self.lbl_offset = QLabel("0.000000 秒")
        status_layout.addWidget(self.lbl_offset_title, 3, 0)
        status_layout.addWidget(self.lbl_offset, 3, 1)
        
        # 频率调整
        self.lbl_rate_title = QLabel("频率调整:")
        self.lbl_rate = QLabel("0.000000")
        status_layout.addWidget(self.lbl_rate_title, 4, 0)
        status_layout.addWidget(self.lbl_rate, 4, 1)
        
        # 控制按钮
        self.btn_start_sync = QPushButton("启动同步")
        self.btn_start_sync.clicked.connect(self.on_start_sync_clicked)
        
        self.btn_stop_sync = QPushButton("停止同步")
        self.btn_stop_sync.clicked.connect(self.on_stop_sync_clicked)
        self.btn_stop_sync.setEnabled(False)
        
        status_layout.addWidget(self.btn_start_sync, 0, 2)
        status_layout.addWidget(self.btn_stop_sync, 1, 2)
        
        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)
        
        # 创建分割器
        splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(splitter, 1)  # 1表示拉伸因子
        
        # 图表显示区域
        chart_group = QGroupBox("偏移量图表")
        chart_layout = QVBoxLayout()
        
        self.chart_view = SyncChartView()
        chart_layout.addWidget(self.chart_view)
        
        chart_group.setLayout(chart_layout)
        splitter.addWidget(chart_group)
        
        # 日志显示区域
        log_group = QGroupBox("同步日志")
        log_layout = QVBoxLayout()
        
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        log_layout.addWidget(self.txt_log)
        
        log_group.setLayout(log_layout)
        splitter.addWidget(log_group)
        
        # 设置分割器初始大小
        splitter.setSizes([400, 200])
        
        # 状态栏
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage(f"服务器地址: {MASTER_IP}:{SYNC_PORT}")
        
        # 添加日志
        self.add_log("应用已启动")
        self.add_log(f"连接至服务器: {MASTER_IP}:{SYNC_PORT}")
    
    def update_ui(self):
        """更新UI显示"""
        # 更新当前时间
        current_time = self.software_clock.time_string()
        self.lbl_current_time.setText(current_time)
        
        # 更新偏移量
        offset = self.software_clock.get_current_offset()
        self.lbl_offset.setText(f"{offset:.9f} 秒")
        
        # 更新频率调整
        rate = self.software_clock.get_rate_adjustment()
        self.lbl_rate.setText(f"{rate:.9f}")
        
        # 更新日志
        logs = self.sync_monitor.get_new_logs()
        if logs:
            for log in logs:
                if log not in self.txt_log.toPlainText():
                    self.txt_log.append(log)
            
            # 自动滚动到底部
            cursor = self.txt_log.textCursor()
            cursor.movePosition(cursor.End)
            self.txt_log.setTextCursor(cursor)
    
    def update_chart(self):
        """更新图表"""
        offset_history = self.sync_monitor.get_offset_history()
        self.chart_view.update_data(offset_history)
    
    @pyqtSlot()
    def on_start_sync_clicked(self):
        """启动同步按钮点击处理"""
        if self.sync_controller.start():
            self.btn_start_sync.setEnabled(False)
            self.btn_stop_sync.setEnabled(True)
            self.add_log("同步已启动")
        else:
            self.add_log("启动同步失败")
    
    @pyqtSlot()
    def on_stop_sync_clicked(self):
        """停止同步按钮点击处理"""
        self.sync_controller.stop()
        self.btn_start_sync.setEnabled(True)
        self.btn_stop_sync.setEnabled(False)
        self.add_log("同步已停止")
    
    @pyqtSlot(bool)
    def on_master_status_changed(self, online):
        """主节点状态变化处理
        
        Args:
            online: 是否在线
        """
        self.master_status_indicator.set_online(online)
        self.lbl_master_status.setText("在线" if online else "离线")
        
        # 设置颜色
        if online:
            self.lbl_master_status.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.lbl_master_status.setStyleSheet("color: red;")
    
    @pyqtSlot(object)
    def on_sync_status_changed(self, status):
        """同步状态变化处理
        
        Args:
            status: SyncStatus枚举值
        """
        if status == SyncStatus.STOPPED:
            self.lbl_sync_status.setText("已停止")
            self.lbl_sync_status.setStyleSheet("color: gray;")
        elif status == SyncStatus.SYNCING:
            self.lbl_sync_status.setText("同步中")
            self.lbl_sync_status.setStyleSheet("color: blue;")
        elif status == SyncStatus.SYNCHRONIZED:
            self.lbl_sync_status.setText("已同步")
            self.lbl_sync_status.setStyleSheet("color: green; font-weight: bold;")
        elif status == SyncStatus.ERROR:
            self.lbl_sync_status.setText("同步失败")
            self.lbl_sync_status.setStyleSheet("color: red;")
    
    def add_log(self, message):
        """添加日志到日志显示区
        
        Args:
            message: 日志消息
        """
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{current_time}] {message}"
        self.txt_log.append(log_entry)
        
        # 自动滚动到底部
        cursor = self.txt_log.textCursor()
        cursor.movePosition(cursor.End)
        self.txt_log.setTextCursor(cursor)
    
    def closeEvent(self, event):
        """窗口关闭事件处理
        
        Args:
            event: 关闭事件
        """
        # 停止同步控制器
        if self.sync_controller.is_running():
            self.sync_controller.stop()
        
        # 停止UI更新定时器
        if self.ui_timer.isActive():
            self.ui_timer.stop()
        
        # 停止图表更新定时器
        if self.chart_timer.isActive():
            self.chart_timer.stop()
        
        self.logger.info("应用已关闭")
        event.accept() 