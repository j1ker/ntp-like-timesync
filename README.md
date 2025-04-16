# ScapySync时间同步演示系统

## 项目概述

ScapySync是一个时间同步演示系统，用于演示时间同步原理。系统包含两个独立的应用程序：Master（主节点）和Slave（从节点）。Master设定参考时间，Slave通过网络同步其内部时钟与Master时间，使用PID控制器进行频率驯化以实现平滑同步。

## 特点

- **自定义协议**：使用自定义的ScapySync协议进行时间戳交换
- **四时间戳机制**：使用T1/T2/T3/T4四个时间戳计算偏移量和网络延迟
- **统计过滤**：采用6轮时间戳交换并选择最佳样本，提高测量可靠性
- **PID频率驯化**：使用PID控制器调整Slave时钟频率，实现平滑同步
- **独立软件时钟**：Slave维护一个独立于系统时钟的软件时钟
- **实时监控**：图形界面显示偏移量、同步状态和日志
- **时间快速调整**：Master提供一系列快速时间偏移按钮，便于演示时间同步过程

## 系统要求

- Python 3.6+
- PyQt5
- PyQtChart
- Scapy

## 安装

1. 克隆此仓库
2. 安装依赖：
```bash
pip install -r requirements.txt
```

## 使用方法

### 启动Master应用

```bash
python -m master.main
```

1. 在Master界面中，可以设置自定义参考时间或使用系统时间
2. 使用时间快速调整按钮（+/-0.05s, +/-0.2s, +/-1s, +/-60s）调整参考时间
3. 点击"启动服务器"按钮启动时间同步服务

### 启动Slave应用

```bash
python -m slave.main
```

1. 在Slave界面中，点击"启动同步"按钮开始与Master同步
2. 查看偏移量图表和同步状态，观察同步过程
3. 尝试使用Master的时间快速调整按钮，观察Slave如何响应时间变化

## 网络设置

默认情况下，Master和Slave都使用本地通信，服务器地址为127.0.0.1，端口为12345。这些设置可以在`common/config.py`中修改。

## 项目结构

```
├── common/                  # 共享模块
│   ├── config.py            # 全局配置参数
│   ├── protocol.py          # ScapySync协议定义
│   └── utils/               # 通用工具
│       └── logger.py        # 日志工具
├── master/                  # Master应用
│   ├── core/                # 核心功能
│   │   └── time_source.py   # 时间源模块
│   ├── gui/                 # 用户界面
│   │   └── main_window.py   # 主窗口
│   ├── network/             # 网络功能
│   │   └── server.py        # 网络服务器
│   └── main.py              # 应用入口
└── slave/                   # Slave应用
    ├── core/                # 核心功能
    │   ├── software_clock.py # 软件时钟实现
    │   ├── sync_controller.py # 同步控制器
    │   └── sync_monitor.py  # 同步监控器
    ├── gui/                 # 用户界面
    │   ├── chart_widget.py  # 图表组件
    │   └── main_window.py   # 主窗口
    ├── network/             # 网络功能
    │   └── client.py        # 网络客户端
    └── main.py              # 应用入口
```

## 工作原理

1. Master启动后开始监听UDP端口，等待Slave的同步请求
2. Slave启动后开始定期向Master发送同步请求
3. 每次同步过程中，Slave进行6轮时间戳交换，获取T1/T2/T3/T4四个时间戳
4. Slave选择网络延迟最小的样本计算最终偏移量和延迟
5. Slave使用PID控制器根据偏移量调整内部时钟的频率
6. 调整后的时钟频率使Slave时钟逐渐同步到Master时间，实现平滑过渡

## 演示场景

使用Master的时间快速调整按钮，可以模拟以下场景：

1. **小幅度时间偏移**：使用±0.05s和±0.2s按钮创建小幅度时间变化，观察Slave如何平滑调整
2. **中等幅度时间跳变**：使用±1s按钮模拟时钟跳变，观察PID控制器的响应
3. **大幅度时间调整**：使用±60s按钮模拟系统时间重设，观察Slave恢复同步的过程 