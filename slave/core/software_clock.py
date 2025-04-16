#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Slave软件时钟模块

实现一个软件时钟，与系统时钟隔离，通过PID控制器进行频率驯化，
使其逐渐与Master时钟同步。
"""

import time
import datetime
from threading import Lock

# 导入共享模块
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from common.config import PID_KP, PID_KI, PID_KD, PID_MAX_INTEGRAL, PID_MIN_INTEGRAL, MAX_RATE_ADJUSTMENT
from common.utils.logger import setup_logger


class SoftwareClock:
    """软件时钟类
    
    实现独立于系统时钟的内部时钟，通过PID控制调整频率，
    使其逐渐与Master时间同步。
    """
    
    def __init__(self, log_file=None):
        """初始化软件时钟
        
        Args:
            log_file: 日志文件路径
        """
        # 记录初始系统时间和性能计数器
        self.init_system_time = time.time()
        self.init_perf_counter = time.perf_counter()
        
        # PID控制器参数和状态
        self.Kp = PID_KP
        self.Ki = PID_KI
        self.Kd = PID_KD
        self.integral = 0.0
        self.prev_error = 0.0
        
        # 频率调整因子（默认为0，表示不调整）
        self.rate_adjustment = 0.0
        
        # 同步状态
        self.current_offset = 0.0  # 当前偏移量
        
        # 线程安全锁
        self.lock = Lock()
        
        # 设置日志记录器
        self.logger = setup_logger('slave.clock', log_file)
        self.logger.info("软件时钟已初始化")
    
    def discipline(self, current_filtered_offset):
        """驯化时钟频率
        
        根据当前偏移量，使用PID控制器计算频率调整量，
        使时钟逐渐与Master同步。
        
        Args:
            current_filtered_offset: 当前过滤后的时钟偏移量（秒）
        """
        with self.lock:
            # 记录偏移量
            self.current_offset = current_filtered_offset
            
            # 计算误差（目标是使偏移趋于0）
            error = current_filtered_offset
            
            # 更新积分项（带抗饱和限制）
            self.integral += error
            self.integral = max(PID_MIN_INTEGRAL, min(PID_MAX_INTEGRAL, self.integral))
            
            # 计算微分项
            derivative = error - self.prev_error
            
            # 计算PID输出
            adjustment = self.Kp * error + self.Ki * self.integral + self.Kd * derivative
            
            # 限制调整范围
            adjustment = max(-MAX_RATE_ADJUSTMENT, min(MAX_RATE_ADJUSTMENT, adjustment))
            
            # 应用频率调整
            self.rate_adjustment = adjustment
            
            # 更新状态
            self.prev_error = error
            
            self.logger.debug(f"时钟驯化: offset={current_filtered_offset:.9f}, "
                             f"adjustment={adjustment:.9f}, "
                             f"P={self.Kp * error:.9f}, "
                             f"I={self.Ki * self.integral:.9f}, "
                             f"D={self.Kd * derivative:.9f}")
    
    def current_time_val(self):
        """获取当前软件时钟时间值
        
        通过应用频率调整因子，计算调整后的时间。
        
        Returns:
            float: 当前软件时钟时间（Unix时间戳，秒）
        """
        with self.lock:
            # 计算基于性能计数器的流逝时间
            elapsed_perf = time.perf_counter() - self.init_perf_counter
            
            # 应用频率调整
            adjusted_elapsed = elapsed_perf * (1.0 + self.rate_adjustment)
            
            # 计算最终时间
            current_time = self.init_system_time + adjusted_elapsed
            
            return current_time
    
    def current_datetime(self):
        """获取当前软件时钟时间的datetime对象
        
        Returns:
            datetime.datetime: 当前软件时钟时间的datetime对象
        """
        return datetime.datetime.fromtimestamp(self.current_time_val())
    
    def time_string(self, format_str="%Y-%m-%d %H:%M:%S"):
        """获取格式化的当前软件时钟时间字符串
        
        Args:
            format_str: 时间格式字符串
            
        Returns:
            str: 格式化的时间字符串
        """
        return self.current_datetime().strftime(format_str)
    
    def current_timestamp_ms(self):
        """获取当前软件时钟的毫秒级时间戳
        
        用于图表X轴数据。
        
        Returns:
            int: 毫秒级时间戳
        """
        return int(self.current_time_val() * 1000)
    
    def get_current_offset(self):
        """获取当前偏移量
        
        Returns:
            float: 当前偏移量（秒）
        """
        with self.lock:
            return self.current_offset
    
    def get_rate_adjustment(self):
        """获取当前频率调整因子
        
        Returns:
            float: 频率调整因子
        """
        with self.lock:
            return self.rate_adjustment
            
    def set_time_offset(self, offset_seconds):
        """直接设置时钟偏移量
        
        通过调整init_system_time来立即改变时钟时间，但不影响频率调整
        
        Args:
            offset_seconds: 要设置的时间偏移量（秒），正值使时钟快进，负值使时钟后退
        """
        with self.lock:
            # 调整初始系统时间，这将改变current_time_val()的返回值
            self.init_system_time += offset_seconds
            
            # 记录操作
            self.logger.info(f"手动调整时钟偏移: {offset_seconds:.3f}秒")
            
            # 注意：此操作不影响PID控制器状态
            # 下一次调用discipline时，PID控制器会根据新的偏移量继续调整频率 