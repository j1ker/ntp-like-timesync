#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Slave网络客户端模块

实现与Master的通信，发送同步请求并接收响应。
"""

import socket
import threading
import time
import struct
import random

# 导入共享模块
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from common.protocol import parse_reply_packet, calculate_offset_delay
from common.config import MASTER_IP, SYNC_PORT, SYNC_TIMEOUT, MAX_SEQUENCE
from common.utils.logger import setup_logger


class NetworkClient:
    """Slave网络客户端类
    
    发送同步请求到Master，接收响应并计算时钟偏移量。
    """
    
    def __init__(self, software_clock, log_file=None):
        """初始化网络客户端
        
        Args:
            software_clock: SoftwareClock实例，用于获取软件时钟时间
            log_file: 日志文件路径
        """
        self.client_socket = None
        self.server_addr = (MASTER_IP, SYNC_PORT)
        self.sequence = random.randint(0, MAX_SEQUENCE)
        self.software_clock = software_clock
        
        # 设置日志记录器
        self.logger = setup_logger('slave.network', log_file)
    
    def create_socket(self):
        """创建UDP套接字
        
        Returns:
            bool: 创建是否成功
        """
        try:
            if self.client_socket:
                self.client_socket.close()
                
            # 创建UDP套接字
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.client_socket.settimeout(SYNC_TIMEOUT)
            return True
            
        except Exception as e:
            self.logger.error(f"创建套接字失败: {e}")
            return False
    
    def close_socket(self):
        """关闭UDP套接字"""
        if self.client_socket:
            self.client_socket.close()
            self.client_socket = None
    
    def create_request_packet(self, sequence):
        """创建同步请求数据包
        
        Args:
            sequence: 序列号
            
        Returns:
            tuple: (bytes, float) 编码后的数据包字节和发送时间t1
        """
        # 使用软件时钟获取t1，而不是系统时钟
        t1 = self.software_clock.current_time_val()
        packet = struct.pack('>BHddd', 0x01, sequence, t1, 0.0, 0.0)
        return packet, t1
    
    def send_sync_request(self):
        """发送同步请求并接收响应
        
        进行一次完整的时间戳交换。
        
        Returns:
            tuple: ((t1, t2, t3, t4), offset, delay) 或 (None, None, None) 表示失败
        """
        try:
            if not self.client_socket:
                if not self.create_socket():
                    return None, None, None
            
            # 递增序列号
            self.sequence = (self.sequence + 1) % MAX_SEQUENCE
            
            # 创建请求包并记录发送时间T1 - 使用我们自己的方法获取软件时钟时间
            request_packet, t1 = self.create_request_packet(self.sequence)
            
            # 发送请求
            self.client_socket.sendto(request_packet, self.server_addr)
            
            # 接收响应
            try:
                data, addr = self.client_socket.recvfrom(1024)
                # 使用软件时钟记录接收时间T4，而不是系统时钟
                t4 = self.software_clock.current_time_val()
                
                # 解析响应包
                result = parse_reply_packet(data)
                if result:
                    flags, seq, t1_echo, t2, t3 = result
                    
                    # 检查序列号是否匹配
                    if seq != self.sequence:
                        self.logger.warning(f"序列号不匹配: 预期={self.sequence}, 实际={seq}")
                        return None, None, None
                    
                    # 计算偏移量和延迟
                    offset, delay = calculate_offset_delay(t1, t2, t3, t4)
                    
                    # 返回四个时间戳、偏移量和延迟
                    timestamps = (t1, t2, t3, t4)
                    return timestamps, offset, delay
                
            except socket.timeout:
                self.logger.warning("同步请求超时")
            
        except Exception as e:
            self.logger.error(f"发送同步请求失败: {e}")
            
        return None, None, None
    
    def perform_sync_round(self, rounds=6):
        """执行多轮同步
        
        进行指定轮数的时间戳交换，选择延迟最小的样本。
        
        Args:
            rounds: 同步轮数
            
        Returns:
            tuple: (filtered_timestamps, filtered_offset, filtered_delay) 或 (None, None, None) 表示失败
                  filtered_timestamps: (t1, t2, t3, t4) 最佳样本的四个时间戳
        """
        valid_samples = []
        
        # 创建新套接字
        if not self.create_socket():
            return None, None, None
        
        try:
            # 进行多轮同步
            for i in range(rounds):
                timestamps, offset, delay = self.send_sync_request()
                
                if timestamps and offset is not None and delay is not None:
                    # 收集有效样本
                    valid_samples.append((timestamps, offset, delay))
                    self.logger.debug(f"轮次 {i+1}/{rounds}: offset={offset:.9f}, delay={delay:.9f}")
                else:
                    self.logger.warning(f"轮次 {i+1}/{rounds}: 同步失败")
            
            # 关闭套接字
            self.close_socket()
            
            # 检查是否有有效样本
            if not valid_samples:
                self.logger.error("所有同步轮次均失败")
                return None, None, None
            
            # 选择延迟最小的样本
            best_sample = min(valid_samples, key=lambda x: x[2])
            filtered_timestamps, filtered_offset, filtered_delay = best_sample
            
            self.logger.info(f"过滤后结果: offset={filtered_offset:.9f}, delay={filtered_delay:.9f}")
            return filtered_timestamps, filtered_offset, filtered_delay
            
        except Exception as e:
            self.logger.error(f"执行同步轮次时出错: {e}")
            self.close_socket()
            return None, None, None 