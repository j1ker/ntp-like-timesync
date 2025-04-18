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
        self.prev_error = 0.0 # 初始化为0.0，或在第一次discipline调用前设为None
        
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
                                    正值表示Slave时钟落后于Master，需要加速
                                    负值表示Slave时钟领先于Master，需要减速
        """
        with self.lock:
            # 记录偏移量
            self.current_offset = current_filtered_offset
            
            # 计算误差（目标是使偏移趋于0）
            # 正偏移（Slave落后）需要正调整（加速）
            # 负偏移（Slave领先）需要负调整（减速）
            error = current_filtered_offset

            # 检测误差符号变化并重置积分项，防止积分饱和问题
            # 仅在prev_error有效且符号确实相反时执行
            if self.prev_error != 0.0 and error * self.prev_error < 0:
                 self.logger.info(f"检测到误差符号变化 ({self.prev_error:.6f} -> {error:.6f})，重置PID积分项。")
                 self.integral = 0.0
            
            # 大偏移处理：如果误差非常大，则使用饱和的PID调整
            if abs(error) > 1.0:  # 1秒以上的偏移视为大偏移
                self.logger.warning(f"检测到大偏移: {error:.6f}秒，重置PID控制器")
                self.integral = 0.0  # 重置积分项，防止积累过大的积分
                # 使用最大频率调整，无条件信任master
                adjustment = (error / abs(error)) * MAX_RATE_ADJUSTMENT 
                direction = "加速" if adjustment > 0 else "减速"
                self.logger.info(f"大偏移调整方向: {direction}, 调整量: {adjustment:.6f}")
            else:
                # 正常PID控制流程
                # 更新积分项（带抗饱和限制）
                self.integral += error
                self.integral = max(PID_MIN_INTEGRAL, min(PID_MAX_INTEGRAL, self.integral))
                
                # 计算微分项
                derivative = error - self.prev_error
                
                # 计算PID输出
                adjustment = self.Kp * error + self.Ki * self.integral + self.Kd * derivative
                
                # 限制调整范围
                adjustment = max(-MAX_RATE_ADJUSTMENT, min(MAX_RATE_ADJUSTMENT, adjustment))
                
                direction = "加速" if adjustment > 0 else "减速"
                self.logger.debug(f"PID调整方向: {direction}, 调整量: {adjustment:.6f}")
            
            # 应用频率调整
            self.rate_adjustment = adjustment
            
            # 更新上一次误差状态，用于下次微分计算和符号变化检测
            self.prev_error = error
            
            self.logger.debug(f"时钟驯化: offset={current_filtered_offset:.9f}, "
                             f"adjustment={adjustment:.9f}, "
                             f"P={self.Kp * error:.9f}, "
                             f"I={self.Ki * self.integral:.9f}, "
                             f"D={self.Kd * derivative:.9f}")
    
    def current_time_val(self):
        """获取当前软件时钟时间值
        
        通过应用频率调整因子，计算调整后的时间。
        
        频率调整器说明：
        - rate_adjustment > 0: 加速时钟，使其赶上Master（当Slave落后时）
        - rate_adjustment < 0: 减速时钟，使其等待Master（当Slave领先时）
        
        Returns:
            float: 当前软件时钟时间（Unix时间戳，秒）
        """
        with self.lock:
            # 计算基于性能计数器的流逝时间
            elapsed_perf = time.perf_counter() - self.init_perf_counter
            
            # 应用频率调整
            # 当rate_adjustment > 0时，时钟流逝更快（例如1.01倍速）
            # 当rate_adjustment < 0时，时钟流逝更慢（例如0.99倍速）
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
            
            # 同时重置PID控制器状态
            self.integral = 0.0
            self.prev_error = 0.0
            self.rate_adjustment = 0.0  # 重置频率调整
            
            # 记录操作
            self.logger.info(f"手动调整时钟偏移: {offset_seconds:.3f}秒，已重置PID控制器状态") 