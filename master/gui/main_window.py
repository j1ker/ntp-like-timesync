#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Master应用主窗口

提供用户界面设置参考时间、启动/停止服务和显示日志。
"""

import sys
import os
import datetime
import time
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QGroupBox,
    QDateTimeEdit, QStatusBar
)
from PyQt5.QtCore import QTimer, QDateTime, Qt, pyqtSlot
from PyQt5.QtGui import QIcon, QColor

# 导入共享模块
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from common.config import MASTER_IP, SYNC_PORT, LOG_FILE_MASTER
from common.utils.logger import setup_logger

# 导入Master模块
from master.core.time_source import TimeSource
from master.network.server import NetworkServer


class MasterMainWindow(QMainWindow):
    """Master应用主窗口类"""
    
    def __init__(self):
        """初始化主窗口"""
        super().__init__()
        
        # 设置日志记录器
        self.logger = setup_logger('master.gui', LOG_FILE_MASTER)
        
        # 创建核心组件
        self.time_source = TimeSource()
        self.network_server = NetworkServer(self.time_source, LOG_FILE_MASTER)
        
        # 初始化UI
        self.init_ui()
        
        # 创建定时器更新UI
        self.ui_timer = QTimer(self)
        self.ui_timer.timeout.connect(self.update_ui)
        self.ui_timer.start(1000)  # 每秒更新一次
        
        # 确保日期时间选择器显示当前参考时间
        self.update_datetime_picker()
        
        self.logger.info("Master应用已启动")
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("ScapySync Master")
        self.setGeometry(100, 100, 800, 600)
        
        # 创建中央部件
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 参考时间设置组
        time_group = QGroupBox("参考时间设置")
        time_layout = QGridLayout()
        
        # 当前参考时间
        self.lbl_current_time_title = QLabel("当前参考时间:")
        self.lbl_current_time = QLabel()
        self.lbl_current_time.setStyleSheet("font-size: 16pt; font-weight: bold;")
        time_layout.addWidget(self.lbl_current_time_title, 0, 0)
        time_layout.addWidget(self.lbl_current_time, 0, 1)
        
        # 设置自定义时间
        self.lbl_custom_time = QLabel("设置自定义时间:")
        self.dt_custom_time = QDateTimeEdit(QDateTime.currentDateTime())
        self.dt_custom_time.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.dt_custom_time.setCalendarPopup(True)
        self.btn_set_time = QPushButton("设置")
        self.btn_set_time.clicked.connect(self.on_set_time_clicked)
        
        time_layout.addWidget(self.lbl_custom_time, 1, 0)
        time_layout.addWidget(self.dt_custom_time, 1, 1)
        time_layout.addWidget(self.btn_set_time, 1, 2)
        
        # 添加时间偏移按钮
        self.lbl_time_adjust = QLabel("时间快速调整:")
        time_layout.addWidget(self.lbl_time_adjust, 2, 0)
        
        # 创建时间偏移按钮的容器
        time_adjust_layout = QHBoxLayout()
        
        # 创建负偏移按钮
        self.btn_offset_minus_005 = QPushButton("-0.05s")
        self.btn_offset_minus_02 = QPushButton("-0.2s")
        self.btn_offset_minus_1 = QPushButton("-1s")
        self.btn_offset_minus_60 = QPushButton("-60s")
        
        # 创建正偏移按钮
        self.btn_offset_plus_005 = QPushButton("+0.05s")
        self.btn_offset_plus_02 = QPushButton("+0.2s")
        self.btn_offset_plus_1 = QPushButton("+1s")
        self.btn_offset_plus_60 = QPushButton("+60s")
        
        # 添加按钮到容器
        time_adjust_layout.addWidget(self.btn_offset_minus_60)
        time_adjust_layout.addWidget(self.btn_offset_minus_1)
        time_adjust_layout.addWidget(self.btn_offset_minus_02)
        time_adjust_layout.addWidget(self.btn_offset_minus_005)
        time_adjust_layout.addWidget(self.btn_offset_plus_005)
        time_adjust_layout.addWidget(self.btn_offset_plus_02)
        time_adjust_layout.addWidget(self.btn_offset_plus_1)
        time_adjust_layout.addWidget(self.btn_offset_plus_60)
        
        # 设置按钮点击事件
        self.btn_offset_minus_005.clicked.connect(lambda: self.on_time_adjust(-0.05))
        self.btn_offset_minus_02.clicked.connect(lambda: self.on_time_adjust(-0.2))
        self.btn_offset_minus_1.clicked.connect(lambda: self.on_time_adjust(-1))
        self.btn_offset_minus_60.clicked.connect(lambda: self.on_time_adjust(-60))
        self.btn_offset_plus_005.clicked.connect(lambda: self.on_time_adjust(0.05))
        self.btn_offset_plus_02.clicked.connect(lambda: self.on_time_adjust(0.2))
        self.btn_offset_plus_1.clicked.connect(lambda: self.on_time_adjust(1))
        self.btn_offset_plus_60.clicked.connect(lambda: self.on_time_adjust(60))
        
        # 将按钮容器添加到时间布局
        time_layout.addLayout(time_adjust_layout, 2, 1, 1, 2)
        
        time_group.setLayout(time_layout)
        main_layout.addWidget(time_group)
        
        # 网络服务控制组
        net_group = QGroupBox("网络服务")
        net_layout = QGridLayout()
        
        self.lbl_server_status_title = QLabel("服务器状态:")
        self.lbl_server_status = QLabel("未启动")
        self.lbl_server_status.setStyleSheet("color: red;")
        
        self.lbl_client_status_title = QLabel("客户端连接:")
        self.lbl_client_status = QLabel("无连接")
        self.lbl_client_status.setStyleSheet("color: gray;")
        
        self.btn_start_server = QPushButton("启动服务器")
        self.btn_start_server.clicked.connect(self.on_start_server_clicked)
        
        self.btn_stop_server = QPushButton("停止服务器")
        self.btn_stop_server.clicked.connect(self.on_stop_server_clicked)
        self.btn_stop_server.setEnabled(False)
        
        net_layout.addWidget(self.lbl_server_status_title, 0, 0)
        net_layout.addWidget(self.lbl_server_status, 0, 1)
        net_layout.addWidget(self.lbl_client_status_title, 1, 0)
        net_layout.addWidget(self.lbl_client_status, 1, 1)
        net_layout.addWidget(self.btn_start_server, 0, 2)
        net_layout.addWidget(self.btn_stop_server, 1, 2)
        
        net_group.setLayout(net_layout)
        main_layout.addWidget(net_group)
        
        # 日志显示区域
        log_group = QGroupBox("日志")
        log_layout = QVBoxLayout()
        
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        log_layout.addWidget(self.txt_log)
        
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)
        
        # 状态栏
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage(f"服务器地址: {MASTER_IP}:{SYNC_PORT}")
        
        # 添加日志
        self.add_log("应用已启动")
        self.add_log(f"服务器地址: {MASTER_IP}:{SYNC_PORT}")
    
    def update_ui(self):
        """更新UI显示"""
        # 更新当前时间
        current_time = self.time_source.time_string()
        self.lbl_current_time.setText(current_time)
        
        # 更新服务器状态
        if self.network_server.is_running():
            self.lbl_server_status.setText("运行中")
            self.lbl_server_status.setStyleSheet("color: green; font-weight: bold;")
            
            # 更新客户端连接状态
            if self.network_server.is_client_connected():
                self.lbl_client_status.setText("已连接")
                self.lbl_client_status.setStyleSheet("color: green;")
            else:
                self.lbl_client_status.setText("无连接")
                self.lbl_client_status.setStyleSheet("color: gray;")
        else:
            self.lbl_server_status.setText("未启动")
            self.lbl_server_status.setStyleSheet("color: red;")
            self.lbl_client_status.setText("无连接")
            self.lbl_client_status.setStyleSheet("color: gray;")
            
        # 更新日期时间选择器（每10秒更新一次）
        if int(time.time()) % 10 == 0:
            self.update_datetime_picker()
    
    @pyqtSlot()
    def on_set_time_clicked(self):
        """设置自定义时间按钮点击处理"""
        time_str = self.dt_custom_time.dateTime().toString("yyyy-MM-dd hh:mm:ss")
        if self.time_source.set_reference_time(time_str):
            self.add_log(f"设置参考时间: {time_str}")
        else:
            self.add_log("设置参考时间失败，格式有误")
            
        # 立即更新时间显示
        self.update_ui()
    
    @pyqtSlot()
    def on_time_adjust(self, seconds_offset):
        """时间偏移按钮点击处理
        
        Args:
            seconds_offset: 时间偏移量（秒）
        """
        self.time_source.adjust_reference_time(seconds_offset)
        current_time = self.time_source.time_string()
        self.add_log(f"调整参考时间 {'+' if seconds_offset > 0 else ''}{seconds_offset}s: {current_time}")
        
        # 立即更新时间显示
        self.update_ui()
        self.update_datetime_picker()
    
    @pyqtSlot()
    def on_start_server_clicked(self):
        """启动服务器按钮点击处理"""
        if self.network_server.start():
            self.btn_start_server.setEnabled(False)
            self.btn_stop_server.setEnabled(True)
            self.add_log("服务器已启动")
        else:
            self.add_log("启动服务器失败")
    
    @pyqtSlot()
    def on_stop_server_clicked(self):
        """停止服务器按钮点击处理"""
        self.network_server.stop()
        self.btn_start_server.setEnabled(True)
        self.btn_stop_server.setEnabled(False)
        self.add_log("服务器已停止")
    
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
    
    def update_datetime_picker(self):
        """更新日期时间选择器为当前参考时间"""
        current_datetime = self.time_source.current_datetime()
        qt_datetime = QDateTime(
            current_datetime.year,
            current_datetime.month,
            current_datetime.day,
            current_datetime.hour,
            current_datetime.minute,
            current_datetime.second
        )
        self.dt_custom_time.setDateTime(qt_datetime)
    
    def closeEvent(self, event):
        """窗口关闭事件处理
        
        Args:
            event: 关闭事件
        """
        # 停止网络服务器
        if self.network_server.is_running():
            self.network_server.stop()
        
        # 停止UI更新定时器
        if self.ui_timer.isActive():
            self.ui_timer.stop()
        
        self.logger.info("应用已关闭")
        event.accept() 