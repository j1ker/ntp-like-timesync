#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Slave性能指标显示组件

显示时间同步性能指标。
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QGroupBox, QFrame, QPushButton
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette


class MetricIndicator(QFrame):
    """性能指标显示组件
    
    显示单个同步性能指标。
    """
    
    def __init__(self, title, unit="", parent=None):
        """初始化性能指标显示组件
        
        Args:
            title: 指标标题
            unit: 指标单位
            parent: 父部件
        """
        super().__init__(parent)
        
        # 设置边框
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        
        # 设置最小高度
        self.setMinimumHeight(90)
        
        # 创建布局
        layout = QVBoxLayout(self)
        
        # 标题标签
        self.lbl_title = QLabel(title)
        self.lbl_title.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setBold(True)
        self.lbl_title.setFont(title_font)
        
        # 值标签
        self.lbl_value = QLabel("0.000")
        self.lbl_value.setAlignment(Qt.AlignCenter)
        value_font = QFont()
        value_font.setPointSize(16)
        value_font.setBold(True)
        self.lbl_value.setFont(value_font)
        
        # 单位标签
        self.lbl_unit = QLabel(unit)
        self.lbl_unit.setAlignment(Qt.AlignCenter)
        
        # 添加到布局
        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_value)
        layout.addWidget(self.lbl_unit)
        
    def set_value(self, value, color=None):
        """设置指标值
        
        Args:
            value: 指标值
            color: 文本颜色，默认为None
        """
        # 更新值
        if isinstance(value, float):
            self.lbl_value.setText(f"{value:.3f}")
        else:
            self.lbl_value.setText(str(value))
        
        # 设置颜色
        if color:
            palette = self.lbl_value.palette()
            palette.setColor(QPalette.WindowText, QColor(color))
            self.lbl_value.setPalette(palette)


class PerformanceWidget(QWidget):
    """性能指标显示窗口
    
    显示多个同步性能指标。
    """
    
    def __init__(self, sync_monitor, parent=None):
        """初始化性能指标显示窗口
        
        Args:
            sync_monitor: SyncMonitor实例
            parent: 父部件
        """
        super().__init__(parent)
        
        self.sync_monitor = sync_monitor
        
        # 初始化UI
        self.init_ui()
        
        # 创建定时器，定期更新指标
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_metrics)
        self.update_timer.start(1000)  # 每秒更新一次
    
    def init_ui(self):
        """初始化用户界面"""
        main_layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("时间同步性能指标")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 指标容器
        metrics_group = QGroupBox()
        metrics_layout = QGridLayout(metrics_group)
        
        # 创建指标显示组件
        self.accuracy_indicator = MetricIndicator("时间准确度", "毫秒")
        self.stability_indicator = MetricIndicator("时间稳定度", "毫秒")
        self.precision_indicator = MetricIndicator("授时精度", "毫秒")
        self.delay_indicator = MetricIndicator("平均网络延迟", "毫秒")
        self.success_rate_indicator = MetricIndicator("同步成功率", "%")
        
        # 添加到网格布局
        metrics_layout.addWidget(self.accuracy_indicator, 0, 0)
        metrics_layout.addWidget(self.stability_indicator, 0, 1)
        metrics_layout.addWidget(self.precision_indicator, 1, 0)
        metrics_layout.addWidget(self.delay_indicator, 1, 1)
        metrics_layout.addWidget(self.success_rate_indicator, 2, 0, 1, 2)
        
        main_layout.addWidget(metrics_group)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        self.btn_reset = QPushButton("重置统计")
        self.btn_reset.clicked.connect(self.reset_statistics)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_reset)
        
        main_layout.addLayout(btn_layout)
    
    def update_metrics(self):
        """更新性能指标显示"""
        metrics = self.sync_monitor.get_performance_metrics()
        
        # 更新各指标显示
        self.accuracy_indicator.set_value(metrics['accuracy'])
        
        # 时间稳定度 - 红色表示不稳定，绿色表示稳定
        stability = metrics['stability']
        self.stability_indicator.set_value(stability)
        if stability > 0:
            if stability < 1.0:
                self.stability_indicator.set_value(stability, "green")
            elif stability < 5.0:
                self.stability_indicator.set_value(stability, "orange")
            else:
                self.stability_indicator.set_value(stability, "red")
        
        # 授时精度
        self.precision_indicator.set_value(metrics['precision'])
        
        # 网络延迟
        self.delay_indicator.set_value(metrics['avg_delay'])
        
        # 同步成功率 - 根据成功率设置颜色
        success_rate = metrics['sync_success_rate']
        self.success_rate_indicator.set_value(success_rate)
        if success_rate > 90:
            self.success_rate_indicator.set_value(success_rate, "green")
        elif success_rate > 70:
            self.success_rate_indicator.set_value(success_rate, "orange")
        else:
            self.success_rate_indicator.set_value(success_rate, "red")
    
    def reset_statistics(self):
        """重置统计数据"""
        self.sync_monitor.reset_performance_metrics()
        self.update_metrics()
    
    def showEvent(self, event):
        """窗口显示事件
        
        Args:
            event: 显示事件
        """
        super().showEvent(event)
        # 窗口显示时启动定时器
        if not self.update_timer.isActive():
            self.update_timer.start(1000)
    
    def hideEvent(self, event):
        """窗口隐藏事件
        
        Args:
            event: 隐藏事件
        """
        super().hideEvent(event)
        # 窗口隐藏时停止定时器
        if self.update_timer.isActive():
            self.update_timer.stop() 