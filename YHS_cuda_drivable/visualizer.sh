#!/bin/sh

# ==============================================
# 一键启动程序脚本 - POSIX 兼容版
# 修复所有 "Syntax error: redirection unexpected" 问题
# 版本: 1.5
# 最后更新: 2025-07-07
# 新增功能: 关闭现有rosbridge节点
# ==============================================

# 配置区域 - 根据您的系统修改这些变量
LOG_DIR="$HOME/launcher_logs"  # 日志目录
CONDA_BASE="$HOME/miniconda3"  # Conda安装路径
ROS_VERSION="melodic"           # ROS版本 (noetic, foxy, 等)

# 初始化日志系统（完全POSIX兼容）
init_logging() {
    mkdir -p "$LOG_DIR"
    timestamp=$(date +%Y%m%d_%H%M%S)
    MAIN_LOG="$LOG_DIR/launch_$timestamp.log"
    
    # 创建日志文件
    : > "$MAIN_LOG"  # 清空或创建文件
    
    # 记录初始信息
    {
        echo "=============================================="
        echo "启动日志 - $(date)"
        echo "用户: $(whoami)"
        echo "主机: $(hostname)"
        echo "工作目录: $(pwd)"
        echo "=============================================="
        echo "系统信息:"
        lsb_release -d 2>/dev/null || echo "未安装lsb_release"
        echo "内核: $(uname -r)"
        echo "PATH: $PATH"
        echo "=============================================="
    } >> "$MAIN_LOG"
}

# 记录日志函数
log() {
    echo "$(date +'%T') - $1" | tee -a "$MAIN_LOG"
}

# 检查命令是否存在
check_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        log "[错误] 命令未找到: $1"
        log "请安装: $2"
        return 1
    fi
    return 0
}

# 加载必要环境
load_environments() {
    # 加载Conda环境
    if [ -f "$CONDA_BASE/etc/profile.d/conda.sh" ]; then
        . "$CONDA_BASE/etc/profile.d/conda.sh"
        log "✓ Conda环境已加载"
    else
        log "⚠ 警告: 未找到Conda初始化脚本"
    fi
    
    # 加载ROS环境
    ros_setup="/opt/ros/$ROS_VERSION/setup.sh"
    [ -f "$ros_setup" ] || ros_setup="/opt/ros/$ROS_VERSION/setup.bash"
    
    if [ -f "$ros_setup" ]; then
        . "$ros_setup"
        log "✓ ROS环境已加载 ($ROS_VERSION)"
    else
        log "[错误] ROS设置文件未找到: /opt/ros/$ROS_VERSION/setup.{sh,bash}" 
        exit 3
    fi
}

# 关闭现有rosbridge节点
stop_existing_rosbridge() {
    log "检查并关闭现有rosbridge节点..."
    
    # 查找所有rosbridge相关进程
    rosbridge_pids=$(pgrep -f "rosbridge_websocket" || true)
    
    if [ -n "$rosbridge_pids" ]; then
        log "发现正在运行的rosbridge (PIDs: $rosbridge_pids)"
        log "正在停止rosbridge..."
        
        # 优雅地停止进程
        kill -TERM $rosbridge_pids >/dev/null 2>&1 || true
        
        # 等待进程退出
        local timeout=5
        while [ $timeout -gt 0 ]; do
            sleep 1
            running=$(pgrep -f "rosbridge_websocket" || true)
            [ -z "$running" ] && break
            timeout=$((timeout - 1))
            log "等待rosbridge退出... (剩余: ${timeout}秒)"
        done
        
        # 强制杀死未退出的进程
        if [ -n "$running" ]; then
            log "进程未正常退出，强制杀死..."
            kill -KILL $rosbridge_pids >/dev/null 2>&1 || true
            sleep 1
        fi
        
        # 最终确认
        if [ -z "$(pgrep -f "rosbridge_websocket" || true)" ]; then
            log "✓ rosbridge 已成功停止"
        else
            log "⚠ 警告: 仍有rosbridge进程在运行"
            log "剩余进程: $(pgrep -f "rosbridge_websocket" || echo '无')"
        fi
    else
        log "rosbridge 未在运行"
    fi
    
    return 0
}

# 重启Nginx服务
restart_nginx() {
    log "步骤 1/4: 重启Nginx服务..."
    
    # 检查Nginx是否安装
    if ! command -v nginx >/dev/null 2>&1; then
        log "[错误] Nginx未安装!"
        log "安装命令: sudo apt install nginx"
        return 1
    fi
    
    # 使用sudo重启Nginx
    sudo systemctl restart nginx 2> "$LOG_DIR/nginx_error.log"
    nginx_status=$?
    
    if [ $nginx_status -eq 0 ]; then
        log "✓ Nginx重启成功"
        
        # 验证Nginx状态
        if systemctl is-active nginx >/dev/null 2>&1; then
            log "  Nginx状态: 运行中"
        else
            log "⚠ Nginx状态: 未运行"
        fi
        return 0
    else
        log "[错误] Nginx重启失败 (状态码: $nginx_status)"
        log "错误详情:"
        cat "$LOG_DIR/nginx_error.log" | tee -a "$MAIN_LOG"
        return 1
    fi
}

# 管理Conda环境
manage_conda() {
    log "步骤 2/4: 管理Conda环境..."
    
    # 检查Conda是否可用
    if ! command -v conda >/dev/null 2>&1; then
        log "⚠ Conda不可用，跳过此步骤"
        return 0
    fi
    
    # 退出所有活动的Conda环境
    while [ -n "$CONDA_PREFIX" ]; do
        env_name=$(basename "$CONDA_PREFIX")
        log "  正在退出Conda环境: $env_name"
        conda deactivate
    done
    
    log "✓ 当前不在任何Conda环境中"
}

# 启动ROS Bridge
start_ros_bridge() {
    log "步骤 3/4: 启动ROS Bridge..."
    
    # 检查roslaunch是否可用
    if ! command -v roslaunch >/dev/null 2>&1; then
        log "[错误] roslaunch命令不可用!"
        log "请确保ROS安装正确且环境已加载"
        return 1
    fi
    
    # 检查rosbridge_server包是否存在
    if ! rospack find rosbridge_server >/dev/null 2>&1; then
        log "[错误] rosbridge_server包未找到!"
        log "安装命令: sudo apt install ros-$ROS_VERSION-rosbridge-server"
        return 1
    fi
    
    log_file="$LOG_DIR/rosbridge_$(date +%s).log"
    
    # 启动ROS Bridge
    log "  启动命令: roslaunch rosbridge_server rosbridge_websocket.launch"
    nohup roslaunch rosbridge_server rosbridge_websocket.launch > "$log_file" 2>&1 &
    ROS_PID=$!
    
    # 等待启动完成
    sleep 5
    
    # 检查进程是否运行
    if ps -p $ROS_PID >/dev/null 2>&1; then
        log "✓ ROS Bridge已启动 (PID: $ROS_PID)"
        log "  日志文件: $log_file"
        
        # 检查节点是否注册
        if rosnode list | grep -q "rosbridge"; then
            log "节点已成功注册到ROS Master"
        else
            log "⚠ 节点未注册到ROS Master，可能有启动问题"
        fi
        
        return 0
    else
        log "[错误] ROS Bridge启动失败!"
        log "最后10行日志:"
        tail -n 10 "$log_file" | tee -a "$MAIN_LOG"
        return 1
    fi
}

# 打开浏览器
open_browser() {
    log "步骤 4/4: 使用DBus打开浏览器..."
    
    # 尝试使用DBus打开
    if dbus-send --print-reply --dest=org.freedesktop.DBus /org/freedesktop/DBus org.freedesktop.DBus.ListNames 2>/dev/null; then
        log "DBus服务可用，尝试打开浏览器..."
        
        # 使用DBus打开URL
        if dbus-send --type=method_call --dest=org.freedesktop.portal.Desktop /org/freedesktop/portal/desktop org.freedesktop.portal.OpenURI.OpenURI string:"" string:"http://localhost" >/dev/null 2>&1; then
            log "✓ 通过DBus打开浏览器成功"
            return 0
        else
            log "✗ DBus打开浏览器失败"
        fi
    else
        log "⚠ DBus服务不可用"
    fi
    
    # 回退到其他方法...
}
# ==============================================
# 主执行流程
# ==============================================

# 初始化日志系统
init_logging

# 记录开始时间
START_TIME=$(date +%s)

# 检查必要命令
check_command systemctl "系统服务管理器" || exit 1
check_command sudo "权限管理工具" || exit 1
check_command pgrep "进程查找" || exit 1

# 加载必要环境
load_environments

# 执行各步骤
restart_nginx || exit 2
manage_conda

# 先关闭现有rosbridge
stop_existing_rosbridge

# 然后启动新的ROS Bridge
start_ros_bridge || exit 3
open_browser

# 计算运行时间
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# 完成信息
{
    echo ""
    echo "=============================================="
    echo "所有服务启动完成!"
    echo "总耗时: $DURATION 秒"
    echo "主日志文件: $MAIN_LOG"
    
    if [ -n "$ROS_PID" ]; then
        echo "ROS Bridge PID: $ROS_PID"
        echo "停止命令: kill $ROS_PID"
    fi
    
    # 显示当前运行的ROS节点
    echo "当前活动ROS节点:"
    rosnode list 2>/dev/null || echo "无节点或roscore未运行"
    echo "=============================================="
} #| tee -a "$MAIN_LOG"

#exit 0
