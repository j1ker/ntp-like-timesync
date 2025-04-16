#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
通用日志模块

提供统一的日志配置和接口，支持控制台和文件输出。
"""

import os
import logging
from logging.handlers import RotatingFileHandler


def setup_logger(name, log_file=None, level=logging.INFO):
    """配置并返回一个logger实例
    
    Args:
        name: 日志器名称
        log_file: 日志文件路径，None表示仅输出到控制台
        level: 日志级别，默认INFO
        
    Returns:
        logging.Logger: 配置好的日志器
    """
    # 创建logger实例
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 如果logger已经有处理器，说明已经配置过，直接返回
    if logger.handlers:
        return logger
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 如果指定了日志文件，创建文件处理器
    if log_file:
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # 创建滚动文件处理器，最大2MB，保留5个备份
        file_handler = RotatingFileHandler(
            log_file, maxBytes=2*1024*1024, backupCount=5
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger 