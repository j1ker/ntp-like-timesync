#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Master网络服务器模块

处理Slave的同步请求，发送响应数据包。
"""

import socket
import threading
import time
from datetime import datetime
import struct

# 导入共享模块
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
# 导入修改后的函数
from common.protocol import create_reply_packet, parse_request_packet
from common.config import SYNC_PORT
from common.utils.logger import setup_logger


class NetworkServer:
    """Master网络服务器类
    
    监听UDP端口，处理Slave的同步请求。
    """
    
    def __init__(self, time_source, log_file=None):
        """初始化网络服务器
        
        Args:
            time_source: TimeSource实例，用于获取基准时间
            log_file: 日志文件路径
        """
        self.time_source = time_source
        self.server_socket = None
        self.running = False
        self.listen_thread = None
        self.client_connected = False
        self.last_client_time = 0
        
        # 设置日志记录器
        self.logger = setup_logger('master.network', log_file)
        
        # 统计数据
        self.total_requests = 0
    
    def start(self, host='0.0.0.0', port=SYNC_PORT):
        """启动服务器
        
        Args:
            host: 服务器监听地址
            port: 服务器监听端口
            
        Returns:
            bool: 启动是否成功
        """
        if self.running:
            return False
        
        try:
            # 创建UDP套接字
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.server_socket.bind((host, port))
            self.server_socket.settimeout(0.5)  # 设置超时，便于停止
            
            self.running = True
            self.total_requests = 0
            
            # 创建并启动监听线程
            self.listen_thread = threading.Thread(
                target=self._listen_loop,
                name="NetworkServerThread"
            )
            self.listen_thread.daemon = True
            self.listen_thread.start()
            
            self.logger.info(f"服务器已启动，监听 {host}:{port}")
            return True
            
        except Exception as e:
            self.logger.error(f"启动服务器失败: {e}")
            if self.server_socket:
                self.server_socket.close()
                self.server_socket = None
            return False
    
    def stop(self):
        """停止服务器"""
        if not self.running:
            return
        
        self.running = False
        
        # 等待监听线程结束
        if self.listen_thread and self.listen_thread.is_alive():
            self.listen_thread.join(2.0)
        
        # 关闭套接字
        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None
        
        self.logger.info("服务器已停止")
    
    def _listen_loop(self):
        """监听循环，处理客户端请求"""
        self.logger.info("监听线程已启动")
        
        while self.running:
            try:
                # 接收数据包
                data, client_addr = self.server_socket.recvfrom(1024)
                # 立即记录 T2 
                t2 = self.time_source.current_time()
                
                # 处理请求，传入 t2
                self._handle_request(data, client_addr, t2)
                
                # 更新客户端连接状态
                self.client_connected = True
                self.last_client_time = time.time() # 使用系统时间跟踪最后活动时间
                
            except socket.timeout:
                # 检查客户端连接状态
                if self.client_connected and time.time() - self.last_client_time > 10:
                    self.client_connected = False
                    self.logger.info("客户端连接超时")
                continue
                
            except Exception as e:
                if self.running:  # 仅在正常运行时记录错误
                    self.logger.error(f"处理请求时出错: {e}")
    
    def _handle_request(self, data, client_addr, t2):
        """处理同步请求
        
        Args:
            data: 请求数据
            client_addr: 客户端地址
            t2: Master接收到请求的时间戳 (由 _listen_loop 传入)
        """
        # 解析请求包获取 sequence 和 t1
        parsed_request = parse_request_packet(data)
        if not parsed_request:
            self.logger.warning(f"收到无效或无法解析的请求包 from {client_addr}")
            return
        
        orig_seq, t1 = parsed_request
            
        # 在发送前记录 T3 
        t3 = self.time_source.current_time()
        
        # 创建响应包，传入所有时间戳
        reply_packet = create_reply_packet(orig_seq, t1, t2, t3)
        
        if reply_packet:
            # 发送响应
            try:
                self.server_socket.sendto(reply_packet, client_addr)
                
                # 更新统计
                self.total_requests += 1
                
                # 记录日志
                self.logger.debug(f"处理同步请求: seq={orig_seq}, client={client_addr}, t1={t1:.6f}, t2={t2:.6f}, t3={t3:.6f}")
                
                # 每100个请求记录一次统计
                if self.total_requests % 100 == 0:
                    self.logger.info(f"已处理 {self.total_requests} 个同步请求")
                    
            except Exception as send_error:
                self.logger.error(f"发送响应失败 to {client_addr}: {send_error}")
        else:
            self.logger.error(f"创建响应包失败 for seq={orig_seq}")

    def is_running(self):
        """获取服务器运行状态
        
        Returns:
            bool: 服务器是否正在运行
        """
        return self.running
    
    def is_client_connected(self):
        """获取客户端连接状态
        
        Returns:
            bool: 是否有客户端连接
        """
        return self.client_connected 