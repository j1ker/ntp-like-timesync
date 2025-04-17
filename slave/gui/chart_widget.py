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
        
        # 始终动态调整Y轴范围以更好地显示当前偏移波动
        if min_value != float('inf') and max_value != float('-inf'):
            # 计算数据范围
            y_range = max_value - min_value
            
            # 设置最小显示范围，确保即使所有值都相同时也能看到波动
            min_display_range = 0.000002  # 2微秒的最小显示范围
            
            if y_range < min_display_range:
                # 如果数据范围过小，居中扩展到最小显示范围
                mid_point = (min_value + max_value) / 2
                min_value = mid_point - min_display_range / 2
                max_value = mid_point + min_display_range / 2
                y_range = min_display_range
            
            # 添加边距，使数据点不太靠近坐标轴边缘
            padding = y_range * 0.3  # 30%的边距
            new_min = min_value - padding
            new_max = max_value + padding
            
            # 设置Y轴范围
            self.offset_axis.setRange(new_min, new_max)
            
            # 更新Y轴刻度数量，确保刻度间隔合理
            range_magnitude = max(abs(new_min), abs(new_max))
            if range_magnitude < 0.0001:  # 小于0.1毫秒
                self.offset_axis.setLabelFormat("%.9f")
                self.offset_axis.setTickCount(5)
            elif range_magnitude < 0.001:  # 小于1毫秒
                self.offset_axis.setLabelFormat("%.6f")
                self.offset_axis.setTickCount(5)
            elif range_magnitude < 0.01:  # 小于10毫秒
                self.offset_axis.setLabelFormat("%.5f")
                self.offset_axis.setTickCount(5)
            elif range_magnitude < 0.1:  # 小于100毫秒
                self.offset_axis.setLabelFormat("%.4f")
                self.offset_axis.setTickCount(5)
            elif range_magnitude < 1.0:  # 小于1秒
                self.offset_axis.setLabelFormat("%.3f")
                self.offset_axis.setTickCount(5)
            else:
                self.offset_axis.setLabelFormat("%.2f")
                self.offset_axis.setTickCount(7)


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