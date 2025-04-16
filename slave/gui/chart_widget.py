#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Slave图表显示组件

显示时间偏移量历史图表。
"""

from PyQt5.QtCore import Qt, QMargins
from PyQt5.QtGui import QPen, QColor, QFont, QPainter
from PyQt5.QtChart import (
    QChart, QChartView, QLineSeries, QValueAxis
)

# 导入共享模块
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from common.config import CHART_Y_MIN, CHART_Y_MAX, CHART_MAX_POINTS


class SyncChartWidget(QChart):
    """同步偏移量图表组件
    
    显示时间偏移量历史数据，X轴为测量次数，Y轴为偏移量（秒）。
    """
    
    def __init__(self, parent=None):
        """初始化图表
        
        Args:
            parent: 父部件
        """
        super().__init__(parent)
        
        # 设置图表标题和主题
        self.setTitle("时钟偏移量历史")
        self.setTheme(QChart.ChartThemeLight)
        self.setAnimationOptions(QChart.SeriesAnimations)
        
        # 创建数据系列
        self.offset_series = QLineSeries()
        self.offset_series.setName("偏移量 (秒)")
        
        # 设置线条样式
        pen = QPen(QColor(0, 120, 215))
        pen.setWidth(2)
        self.offset_series.setPen(pen)
        
        # 添加系列到图表
        self.addSeries(self.offset_series)
        
        # 创建X轴（测量次数轴）
        self.count_axis = QValueAxis()
        self.count_axis.setTitleText("测量次数")
        self.count_axis.setTickCount(5)
        self.count_axis.setRange(0, CHART_MAX_POINTS)
        self.count_axis.setLabelFormat("%d")
        
        # 创建Y轴（偏移量轴）
        self.offset_axis = QValueAxis()
        self.offset_axis.setTitleText("偏移量 (秒)")
        self.offset_axis.setRange(CHART_Y_MIN, CHART_Y_MAX)
        self.offset_axis.setTickCount(7)
        self.offset_axis.setLabelFormat("%.2f")
        
        # 将轴添加到图表
        self.addAxis(self.count_axis, Qt.AlignBottom)
        self.addAxis(self.offset_axis, Qt.AlignLeft)
        
        # 将系列附加到轴
        self.offset_series.attachAxis(self.count_axis)
        self.offset_series.attachAxis(self.offset_axis)
        
        # 设置图例和边距
        self.legend().setVisible(True)
        self.legend().setAlignment(Qt.AlignBottom)
        self.setMargins(QMargins(10, 10, 10, 10))
    
    def update_chart(self, offset_history):
        """更新图表数据
        
        Args:
            offset_history: [(timestamp_ms, offset), ...] 偏移量历史数据列表
        """
        # 清空现有数据
        self.offset_series.clear()
        
        if not offset_history:
            return
        
        # 取最近的CHART_MAX_POINTS个数据点
        recent_history = offset_history[-CHART_MAX_POINTS:]
        
        # 添加数据点
        min_value = float('inf')
        max_value = float('-inf')
        
        for i, (_, offset) in enumerate(recent_history):
            # 添加数据点，X轴为数据点索引
            self.offset_series.append(i + 1, offset)
            
            # 更新范围
            min_value = min(min_value, offset)
            max_value = max(max_value, offset)
        
        # 设置X轴范围
        self.count_axis.setRange(1, len(recent_history) + 1)
        
        # 动态调整Y轴范围，确保数据在合适的范围内显示
        if min_value != float('inf') and max_value != float('-inf'):
            # 检查是否需要调整Y轴
            if min_value < CHART_Y_MIN or max_value > CHART_Y_MAX:
                # 如果数据超出了配置的范围，动态调整
                y_range = max_value - min_value
                padding = y_range * 0.2
                new_min = min(CHART_Y_MIN, min_value - padding)
                new_max = max(CHART_Y_MAX, max_value + padding)
                self.offset_axis.setRange(new_min, new_max)
            else:
                # 否则使用配置的范围
                self.offset_axis.setRange(CHART_Y_MIN, CHART_Y_MAX)


class SyncChartView(QChartView):
    """同步图表视图
    
    封装图表显示视图。
    """
    
    def __init__(self, parent=None):
        """初始化图表视图
        
        Args:
            parent: 父部件
        """
        # 创建图表
        chart = SyncChartWidget()
        
        # 初始化视图
        super().__init__(chart, parent)
        
        # 设置渲染属性
        self.setRenderHint(QPainter.Antialiasing)
        
        # 启用鼠标跟踪
        self.setMouseTracking(True)
    
    def update_data(self, offset_history):
        """更新图表数据
        
        Args:
            offset_history: [(timestamp_ms, offset), ...] 偏移量历史数据列表
        """
        # 调用图表的更新方法
        chart = self.chart()
        if isinstance(chart, SyncChartWidget):
            chart.update_chart(offset_history) 