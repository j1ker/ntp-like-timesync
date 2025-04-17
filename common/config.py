#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ScapySync系统配置模块

提供系统全局配置参数，包括网络设置、同步参数、PID控制器参数等。
"""

# 网络设置
MASTER_IP = "127.0.0.1"  # Master服务器IP地址
SYNC_PORT = 12345        # 同步通信端口

# 同步参数
SYNC_INTERVAL = 5        # 同步间隔(秒)
ROUNDS_PER_SYNC = 6      # 每次同步的轮数
SYNC_TIMEOUT = 1.0       # 同步请求超时时间(秒)
MAX_SEQUENCE = 65535     # 最大序列号

# PID控制器参数
PID_KP = 0.8             # 比例系数
PID_KI = 0.5             # 积分系数
PID_KD = 0.1             # 微分系数
PID_MAX_INTEGRAL = 1.0   # 积分项上限(防止积分饱和)
PID_MIN_INTEGRAL = -1.0  # 积分项下限
MAX_RATE_ADJUSTMENT = 1  # 最大频率调整量

# 状态阈值
SYNC_THRESHOLD = 0.001   # 同步阈值(秒)，低于此值认为已同步，由原来的1000秒改为1毫秒
OFFLINE_TIMEOUT = 15     # 主节点离线超时(秒)

# 图表显示设置
CHART_MAX_POINTS = 30   # 图表最大显示点数，设为30显示最近30次测量
CHART_Y_MIN = -1100.0   # 图表Y轴最小值(秒)
CHART_Y_MAX = 1100.0    # 图表Y轴最大值(秒)
CHART_UPDATE_INTERVAL = 1000  # 图表更新间隔(毫秒)

# 日志设置
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL = "INFO"       # 日志级别
LOG_FILE_MASTER = "logs/master.log"  # Master日志文件
LOG_FILE_SLAVE = "logs/slave.log"    # Slave日志文件 