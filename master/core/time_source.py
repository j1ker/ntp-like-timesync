#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Master时间源模块

维护Master的基准时间，提供时间获取和格式化功能。
"""

import time
import datetime


class TimeSource:
    """Master时间源类
    
    维护Master的基准时间，可以设置自定义基准时间或使用系统时间。
    """
    
    def __init__(self):
        """初始化时间源
        
        默认以当前系统时间为基准，记录初始系统时间和性能计数器。
        """
        self.init_system_time = time.time()
        self.init_perf_counter = time.perf_counter()
        self.time_offset = 0.0  # 初始无偏移
        self.custom_time_set = False  # 是否已设置自定义时间
        
    def set_reference_time(self, time_string):
        """设置自定义基准时间
        
        Args:
            time_string: 格式为 "YYYY-MM-DD HH:MM:SS" 的时间字符串
            
        Returns:
            bool: 设置是否成功
        """
        try:
            # 解析时间字符串
            reference_datetime = datetime.datetime.strptime(
                time_string, "%Y-%m-%d %H:%M:%S"
            )
            reference_timestamp = reference_datetime.timestamp()
            
            # 获取当前经过的时间
            elapsed = time.perf_counter() - self.init_perf_counter
            
            # 更新初始时间点和性能计数器
            self.init_system_time = reference_timestamp - elapsed
            self.init_perf_counter = time.perf_counter()
            self.custom_time_set = True
            
            return True
        except ValueError:
            return False
    
    def adjust_reference_time(self, seconds_offset):
        """调整当前参考时间
        
        此方法只简单调整内部时钟的基准时间，不影响同步过程
        
        Args:
            seconds_offset: 要调整的秒数（正数为增加，负数为减少）
            
        Returns:
            float: 调整后的当前时间戳
        """
        # 更新初始系统时间以反映偏移
        self.init_system_time += seconds_offset
        
        return self.current_time()
    
    def current_time(self):
        """获取当前基准时间
        
        Returns:
            float: 当前基准时间（Unix时间戳，秒）
        """
        # 无论是否设置了自定义时间，都使用同样的逻辑计算当前时间
        # 基于初始时间加上经过的时间来计算
        elapsed = time.perf_counter() - self.init_perf_counter
        return self.init_system_time + elapsed
    
    def current_datetime(self):
        """获取当前基准时间的datetime对象
        
        Returns:
            datetime.datetime: 当前基准时间的datetime对象
        """
        return datetime.datetime.fromtimestamp(self.current_time())
    
    def time_string(self, format_str="%Y-%m-%d %H:%M:%S"):
        """获取格式化的当前基准时间字符串
        
        Args:
            format_str: 时间格式字符串
            
        Returns:
            str: 格式化的时间字符串
        """
        return self.current_datetime().strftime(format_str) 