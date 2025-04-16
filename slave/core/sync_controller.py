#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Slave同步控制器模块

管理同步过程，协调网络客户端、软件时钟和同步监控器。
"""

import threading
import time
from enum import Enum

# 导入共享模块
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from common.config import SYNC_INTERVAL, ROUNDS_PER_SYNC, LOG_FILE_SLAVE
from common.utils.logger import setup_logger

# 导入Slave模块
from slave.network.client import NetworkClient


class SyncStatus(Enum):
    """同步状态枚举"""
    STOPPED = 0     # 已停止
    SYNCING = 1     # 同步中
    SYNCHRONIZED = 2  # 已同步
    ERROR = 3       # 错误


class SyncController:
    """同步控制器类
    
    管理同步过程，执行周期性的时间同步。
    """
    
    def __init__(self, software_clock, sync_monitor, log_file=None):
        """初始化同步控制器
        
        Args:
            software_clock: SoftwareClock实例
            sync_monitor: SyncMonitor实例
            log_file: 日志文件路径
        """
        self.software_clock = software_clock
        self.sync_monitor = sync_monitor
        self.network_client = NetworkClient(log_file)
        
        self.sync_thread = None
        self.running = False
        self.status = SyncStatus.STOPPED
        
        # 同步状态跟踪
        self.last_sync_time = 0
        self.sync_success_count = 0
        self.sync_fail_count = 0
        
        # 设置日志记录器
        self.logger = setup_logger('slave.sync_controller', log_file)
    
    def start(self):
        """启动同步控制器
        
        Returns:
            bool: 启动是否成功
        """
        if self.running:
            return False
        
        self.running = True
        self.status = SyncStatus.SYNCING
        
        # 重置状态
        self.sync_success_count = 0
        self.sync_fail_count = 0
        
        # 创建并启动同步线程
        self.sync_thread = threading.Thread(
            target=self._sync_loop,
            name="SyncControllerThread"
        )
        self.sync_thread.daemon = True
        self.sync_thread.start()
        
        self.logger.info("同步控制器已启动")
        return True
    
    def stop(self):
        """停止同步控制器"""
        if not self.running:
            return
        
        self.running = False
        self.status = SyncStatus.STOPPED
        
        # 等待同步线程结束
        if self.sync_thread and self.sync_thread.is_alive():
            self.sync_thread.join(2.0)
        
        self.logger.info("同步控制器已停止")
    
    def _sync_loop(self):
        """同步循环
        
        定期执行同步过程。
        """
        while self.running:
            try:
                # 执行一次同步
                success = self._perform_sync()
                
                if success:
                    self.sync_success_count += 1
                    self.sync_fail_count = 0  # 重置失败计数
                else:
                    self.sync_fail_count += 1
                    
                    # 如果连续失败次数过多，更新状态
                    if self.sync_fail_count >= 3:
                        self.status = SyncStatus.ERROR
                        self.sync_monitor.update_master_online_status(False)
                
                # 更新最后同步时间
                self.last_sync_time = time.time()
                
                # 等待下一次同步
                for _ in range(int(SYNC_INTERVAL * 2)):  # 分成小段以便响应停止
                    if not self.running:
                        break
                    time.sleep(0.5)
                    
            except Exception as e:
                self.logger.error(f"同步循环异常: {e}")
                self.status = SyncStatus.ERROR
                time.sleep(1)  # 出错后暂停一下
    
    def _perform_sync(self):
        """执行一次同步
        
        Returns:
            bool: 同步是否成功
        """
        self.logger.debug("开始同步过程")
        
        # 设置状态为同步中
        old_status = self.status
        self.status = SyncStatus.SYNCING
        self.sync_monitor.update_sync_status(self.status)
        
        # 执行多轮同步
        result = self.network_client.perform_sync_round(ROUNDS_PER_SYNC)
        
        if not result or not all(result):
            self.logger.warning("同步失败")
            
            # 恢复之前的状态（如果原来是已同步，保持已同步）
            if old_status == SyncStatus.SYNCHRONIZED:
                self.status = SyncStatus.SYNCHRONIZED
            else:
                self.status = SyncStatus.ERROR
                
            self.sync_monitor.update_sync_status(self.status)
            self.sync_monitor.update_master_online_status(False)
            return False
        
        # 解析结果
        timestamps, filtered_offset, filtered_delay = result
        
        # 根据偏移量大小决定调整方式
        if abs(filtered_offset) > 10.0:
            # 偏移量过大，直接调整时间而不是依赖PID
            self.software_clock.set_time_offset(-filtered_offset)  # 负值是因为要减去偏移
            self.logger.info(f"偏移量过大 ({filtered_offset:.3f}秒)，已直接调整时钟时间")
        else:
            # 偏移量在可接受范围内，使用PID驯化
            self.software_clock.discipline(filtered_offset)
        
        # 更新同步监控器
        current_timestamp_ms = self.software_clock.current_timestamp_ms()
        self.sync_monitor.add_offset_record(current_timestamp_ms, filtered_offset)
        self.sync_monitor.update_master_online_status(True)
        
        # 设置状态为已同步
        self.status = SyncStatus.SYNCHRONIZED
        self.sync_monitor.update_sync_status(self.status)
        
        self.logger.info(f"同步成功: offset={filtered_offset:.9f}, delay={filtered_delay:.9f}")
        return True
    
    def get_status(self):
        """获取当前同步状态
        
        Returns:
            SyncStatus: 当前状态
        """
        return self.status
    
    def is_running(self):
        """检查是否正在运行
        
        Returns:
            bool: 是否正在运行
        """
        return self.running
    
    def get_last_sync_time(self):
        """获取最后同步时间
        
        Returns:
            float: 最后同步时间戳
        """
        return self.last_sync_time 