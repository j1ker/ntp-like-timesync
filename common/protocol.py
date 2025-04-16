#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ScapySync协议定义模块

定义ScapySync协议的数据包格式和处理方法，用于Master和Slave之间的时间同步通信。
协议基于UDP，使用Scapy创建自定义数据包实现四次时间戳交换。
"""

import struct
import time
from scapy.all import Packet, BitField, ShortField, IEEEDoubleField

# 协议常量
FLAG_REQUEST = 0x01    # 请求标志
FLAG_REPLY = 0x02      # 响应标志
DEFAULT_PORT = 12345   # 默认UDP端口

class ScapySyncPacket(Packet):
    """ScapySync协议数据包定义
    
    包含以下字段：
    - flags: 1字节标志位 (0x01=请求, 0x02=响应)
    - sequence: 2字节序列号
    - t1: 8字节T1时间戳 (Slave发送请求的时间)
    - t2: 8字节T2时间戳 (Master接收请求的时间)
    - t3: 8字节T3时间戳 (Master发送响应的时间)
    
    T4时间戳(Slave接收响应的时间)由Slave在接收包时记录，不包含在数据包中
    """
    name = "ScapySync"
    fields_desc = [
        BitField("flags", 0, 8),
        ShortField("sequence", 0),
        IEEEDoubleField("t1", 0),
        IEEEDoubleField("t2", 0),
        IEEEDoubleField("t3", 0)
    ]

def create_request_packet(sequence):
    """创建同步请求数据包
    
    Args:
        sequence: 序列号
        
    Returns:
        bytes: 编码后的数据包字节
    """
    t1 = time.time()  # 记录发送时间T1
    packet = struct.pack('>BHddd', FLAG_REQUEST, sequence, t1, 0.0, 0.0)
    return packet, t1

def create_reply_packet(request_packet, sequence, time_source=None):
    """创建同步响应数据包
    
    Args:
        request_packet: 收到的请求数据包字节
        sequence: 序列号
        time_source: 时间源，如果提供则使用该时间源获取时间
        
    Returns:
        bytes: 编码后的响应数据包字节
    """
    # 解析请求包
    try:
        flags, seq, t1, _, _ = struct.unpack('>BHddd', request_packet[:27])
        
        # 使用提供的时间源或默认使用系统时间
        if time_source:
            t2 = time_source.current_time()  # 记录接收时间T2
            t3 = time_source.current_time()  # 记录发送时间T3
        else:
            t2 = time.time()  # 记录接收时间T2
            t3 = time.time()  # 记录发送时间T3
            
        reply_packet = struct.pack('>BHddd', FLAG_REPLY, sequence, t1, t2, t3)
        return reply_packet, t2, t3
    except struct.error:
        return None, 0, 0

def parse_reply_packet(reply_packet):
    """解析响应数据包
    
    Args:
        reply_packet: 收到的响应数据包字节
        
    Returns:
        tuple: (flags, sequence, t1, t2, t3) 或None表示解析失败
    """
    try:
        result = struct.unpack('>BHddd', reply_packet[:27])
        return result
    except struct.error:
        return None

def calculate_offset_delay(t1, t2, t3, t4):
    """计算时钟偏移和网络延迟
    
    根据四个时间戳计算Slave相对于Master的时钟偏移和网络单程延迟
    
    Args:
        t1: Slave发送请求的时间
        t2: Master接收请求的时间
        t3: Master发送响应的时间
        t4: Slave接收响应的时间
        
    Returns:
        tuple: (offset, delay) 时钟偏移和网络延迟，单位为秒
    """
    offset = ((t2 - t1) + (t3 - t4)) / 2
    delay = ((t4 - t1) - (t3 - t2)) / 2
    return offset, delay 