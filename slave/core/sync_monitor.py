#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Slave同步监控器模块

跟踪和记录同步状态、偏移量历史和日志。
"""

import time
import datetime
import math
import statistics
from collections import deque
from threading import Lock
from PyQt5.QtCore import QObject, pyqtSignal

# 导入共享模块
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from common.config import CHART_MAX_POINTS, SYNC_THRESHOLD, OFFLINE_TIMEOUT
from common.utils.logger import setup_logger

# 导入Slave模块
from slave.core.sync_controller import SyncStatus


class SyncMonitor(QObject):
    """同步监控器类
    
    跟踪同步状态、Master在线状态，并维护偏移量历史记录。
    """
    
    # 定义信号
    status_changed = pyqtSignal(bool)  # Master状态变化信号
    sync_status_changed = pyqtSignal(object)  # 同步状态变化信号
    
    def __init__(self, log_file=None):
        """初始化同步监控器
        
        Args:
            log_file: 日志文件路径
        """
        super().__init__()
        
        # 同步状态
        self.master_online = False
        self.sync_status = SyncStatus.STOPPED
        self.last_offset = 0.0
        self.last_offset_time = 0
        
        # 偏移量历史记录（时间戳毫秒，偏移量秒）
        self.offset_history = deque(maxlen=CHART_MAX_POINTS)
        
        # 延迟历史记录
        self.delay_history = deque(maxlen=CHART_MAX_POINTS)
        
        # 性能指标
        self.performance_metrics = {
            'accuracy': 0.0,             # 时间准确度 (ms)
            'stability': 0.0,            # 时间稳定度 (标准差, ms)
            'precision': 0.0,            # 授时精度 (最大偏差, ms)
            'avg_delay': 0.0,            # 平均网络延迟 (ms)
            'sync_success_rate': 0.0,    # 同步成功率 (%)
            'last_update_time': 0        # 上次更新时间
        }
        
        # 同步统计数据
        self.total_sync_attempts = 0
        self.successful_sync_count = 0
        
        # 日志缓冲
        self.log_buffer = deque(maxlen=1000)
        
        # 线程安全锁
        self.lock = Lock()
        
        # 设置日志记录器
        self.logger = setup_logger('slave.sync_monitor', log_file)
        
        self.logger.info("同步监控器已初始化")
        
        # 添加初始日志
        self._add_log("同步监控器已启动")
        self._add_log(f"偏移量阈值: {SYNC_THRESHOLD} 秒")
    
    def update_master_online_status(self, online):
        """更新主节点在线状态
        
        Args:
            online: 是否在线
        """
        with self.lock:
            if self.master_online != online:
                self.master_online = online
                status_text = "在线" if online else "离线"
                self._add_log(f"主节点状态变更: {status_text}")
                
                # 发射信号
                self.status_changed.emit(online)
    
    def update_sync_status(self, status):
        """更新同步状态
        
        Args:
            status: SyncStatus枚举值
        """
        with self.lock:
            if self.sync_status != status:
                old_status = self.sync_status
                self.sync_status = status
                
                # 记录状态变化
                self._add_log(f"同步状态变更: {old_status.name} -> {status.name}")
                
                # 发射信号
                self.sync_status_changed.emit(status)
    
    def add_offset_record(self, timestamp_ms, offset, delay=None):
        """添加偏移量记录
        
        Args:
            timestamp_ms: 毫秒级时间戳
            offset: 偏移量（秒）
            delay: 网络延迟（秒），如果提供则也记录
        """
        with self.lock:
            # 更新最近偏移量
            self.last_offset = offset
            self.last_offset_time = time.time()
            
            # 添加到历史记录
            self.offset_history.append((timestamp_ms, offset))
            
            # 如果提供了延迟，也记录
            if delay is not None:
                self.delay_history.append((timestamp_ms, delay))
            
            # 更新同步统计
            self.total_sync_attempts += 1
            
            # 判断是否同步达标
            in_sync = abs(offset) < SYNC_THRESHOLD
            if in_sync:
                self.successful_sync_count += 1
                
            status_text = "已达标" if in_sync else "未达标"
            self._add_log(f"偏移量: {offset:.9f} 秒, {status_text}")
            
            # 更新性能指标
            self._update_performance_metrics()
    
    def _update_performance_metrics(self):
        """更新性能指标"""
        if len(self.offset_history) < 2:
            return
            
        # 获取最近的偏移量数据（转换为毫秒）
        recent_offsets = [offset * 1000 for _, offset in self.offset_history]
        
        # 时间准确度 - 最近偏移量的绝对值
        self.performance_metrics['accuracy'] = abs(recent_offsets[-1])
        
        # 时间稳定度 - 偏移量的标准差
        if len(recent_offsets) >= 3:
            self.performance_metrics['stability'] = statistics.stdev(recent_offsets)
        else:
            self.performance_metrics['stability'] = 0.0
            
        # 授时精度 - 最大偏差
        max_deviation = max(abs(offset) for offset in recent_offsets)
        self.performance_metrics['precision'] = max_deviation
        
        # 平均网络延迟
        if self.delay_history:
            delays_ms = [delay * 1000 for _, delay in self.delay_history]
            self.performance_metrics['avg_delay'] = sum(delays_ms) / len(delays_ms)
        
        # 同步成功率
        if self.total_sync_attempts > 0:
            self.performance_metrics['sync_success_rate'] = (self.successful_sync_count / self.total_sync_attempts) * 100
        
        # 更新时间
        self.performance_metrics['last_update_time'] = time.time()
    
    def reset_performance_metrics(self):
        """重置性能指标"""
        with self.lock:
            self.total_sync_attempts = 0
            self.successful_sync_count = 0
            self.performance_metrics = {
                'accuracy': 0.0,
                'stability': 0.0,
                'precision': 0.0,
                'avg_delay': 0.0,
                'sync_success_rate': 0.0,
                'last_update_time': 0
            }
    
    def get_performance_metrics(self):
        """获取性能指标
        
        Returns:
            dict: 性能指标字典
        """
        with self.lock:
            return self.performance_metrics.copy()
    
    def get_offset_history(self):
        """获取偏移量历史记录
        
        Returns:
            list: [(timestamp_ms, offset), ...] 偏移量历史记录
        """
        with self.lock:
            return list(self.offset_history)
    
    def get_last_offset(self):
        """获取最新偏移量
        
        Returns:
            float: 最新偏移量（秒）
        """
        with self.lock:
            return self.last_offset
    
    def is_master_online(self):
        """检查主节点是否在线
        
        Returns:
            bool: 主节点是否在线
        """
        with self.lock:
            # 检查最后偏移量时间
            if time.time() - self.last_offset_time > OFFLINE_TIMEOUT:
                if self.master_online:
                    self.update_master_online_status(False)
            
            return self.master_online
    
    def get_sync_status(self):
        """获取同步状态
        
        Returns:
            SyncStatus: 同步状态
        """
        with self.lock:
            return self.sync_status
    
    def _add_log(self, message):
        """添加日志
        
        Args:
            message: 日志消息
        """
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        # 添加到缓冲
        self.log_buffer.append(log_entry)
        
        # 同时写入日志记录器
        self.logger.info(message)
    
    def get_new_logs(self, count=None):
        """获取最新日志
        
        Args:
            count: 获取数量，None表示全部
            
        Returns:
            list: 日志条目列表
        """
        with self.lock:
            if count is None:
                return list(self.log_buffer)
            else:
                return list(self.log_buffer)[-count:] 