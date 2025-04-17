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
        tuple: (bytes, float) 编码后的数据包字节和发送时间t1
    """
    t1 = time.time()  # 记录发送时间T1
    packet = struct.pack('>BHddd', FLAG_REQUEST, sequence, t1, 0.0, 0.0)
    return packet, t1

def create_reply_packet(sequence, t1, t2, t3):
    """创建同步响应数据包
    
    直接使用传入的时间戳构建包。
    
    Args:
        sequence: 序列号 (从请求包中获取)
        t1: Slave发送请求的时间 (从请求包中获取)
        t2: Master接收请求的时间 (外部传入)
        t3: Master发送响应的时间 (外部传入)
        
    Returns:
        bytes: 编码后的响应数据包字节，如果出错则返回None
    """
    try:
        reply_packet = struct.pack('>BHddd', FLAG_REPLY, sequence, t1, t2, t3)
        return reply_packet
    except struct.error as e:
        # 可以考虑加入日志记录错误
        print(f"Error packing reply packet: {e}") # 临时添加打印
        return None

def parse_request_packet(request_packet):
    """解析请求数据包，主要获取t1和sequence
    
    Args:
        request_packet: 收到的请求数据包字节
        
    Returns:
        tuple: (sequence, t1) 或 None 表示解析失败
    """
    if len(request_packet) < 27:
        return None
    try:
        flags, seq, t1_val, _, _ = struct.unpack('>BHddd', request_packet[:27])
        if flags == FLAG_REQUEST:
            return seq, t1_val
        else:
            return None # 非请求包
    except struct.error:
        return None

def parse_reply_packet(reply_packet):
    """解析响应数据包
    
    Args:
        reply_packet: 收到的响应数据包字节
        
    Returns:
        tuple: (flags, sequence, t1, t2, t3) 或None表示解析失败
    """
    if len(reply_packet) < 27:
        return None
    try:
        result = struct.unpack('>BHddd', reply_packet[:27])
        # 检查是否是回复包 (可选但推荐)
        if result[0] == FLAG_REPLY:
            return result
        else:
            return None # 非回复包
    except struct.error:
        return None

def calculate_offset_delay(t1, t2, t3, t4):
    """计算时钟偏移和网络延迟
    
    根据四个时间戳计算Slave相对于Master的时钟偏移和网络单程延迟
    
    公式：
    - offset = ((t2 - t1) + (t3 - t4)) / 2  
      含义：主从时钟差的平均值
    - delay = ((t4 - t1) - (t3 - t2)) / 2
      含义：往返延迟减去主机处理时间，再除以2得到单程延迟
    
    Args:
        t1: Slave发送请求的时间
        t2: Master接收请求的时间
        t3: Master发送响应的时间
        t4: Slave接收响应的时间
        
    Returns:
        tuple: (offset, delay) 时钟偏移和网络延迟，单位为秒
    """
    # 计算偏移量（正值表示Slave时钟落后于Master）
    offset = ((t2 - t1) + (t3 - t4)) / 2
    
    # 计算网络单程延迟
    delay = ((t4 - t1) - (t3 - t2)) / 2
    
    # 确保延迟不为负值（理论上不应该出现，但可能因为时钟不稳定或测量误差）
    if delay < 0:
        delay = 0.0
    
    return offset, delay 