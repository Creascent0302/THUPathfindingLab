#!/bin/sh

# ==============================================
# 一键启动程序脚本 - POSIX 兼容版
# 版本: 1.7
# 最后更新: 2025-07-07
# 新增功能: 只关闭rosbridge节点
# ==============================================

# 配置区域 - 根据您的系统修改这些变量
LOG_DIR="$HOME/launcher_logs"  # 日志目录
ROS_WORKSPACE="/home/jimmy/drivable"  # ROS工作空间路径

# 初始化日志系统
init_logging() {
    mkdir -p "$LOG_DIR"
    timestamp=$(date +%Y%m%d_%H%M%S)
    MAIN_LOG="$LOG_DIR/launch_$timestamp.log"
    
    # 创建日志文件头
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
    } > "$MAIN_LOG"
}

# 记录日志函数
log() {
    local message="$(date +'%T') - $1"
    echo "$message" | tee -a "$MAIN_LOG"
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
    # 检查并加载ROS环境
    local ros_setup="$ROS_WORKSPACE/devel/setup.sh"
    
    # 首选setup.sh，如果不存在则尝试setup.bash
    [ -f "$ros_setup" ] || ros_setup="$ROS_WORKSPACE/devel/setup.bash"
    
    if [ -f "$ros_setup" ]; then
        log "加载ROS环境: $ros_setup"
        . "$ros_setup"
        log "✓ ROS环境已加载 (工作空间: $ROS_WORKSPACE)"
        return 0
    else
        log "[错误] ROS设置文件未找到: $ROS_WORKSPACE/devel/setup.{sh,bash}"
        return 1
    fi
}

# 只关闭rosbridge节点
stop_rosbridge() {
    log "检查并关闭rosbridge节点..."
    
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

# 启动ROS Drivable
start_ros_Drivable() {
    log "启动ROS Drivable..."
    
    # 检查roslaunch是否可用
    if ! command -v roslaunch >/dev/null 2>&1; then
        log "[错误] roslaunch命令不可用!"
        log "请确保ROS环境已正确加载"
        return 1
    fi
    
    # 检查包是否存在
    if ! rospack find drivable_area_detection >/dev/null 2>&1; then
        log "[错误] drivable_area_detection包未找到!"
        log "请确保工作空间已正确构建"
        return 1
    fi
    
    log_file="$LOG_DIR/drivable_$(date +%s).log"
    
    # 启动ROS节点
    log "启动命令: roslaunch drivable_area_detection clean_drivable.launch"
    nohup roslaunch drivable_area_detection clean_drivable.launch > "$log_file" 2>&1 &
    ROS_PID=$!
    
    # 等待启动完成
    sleep 5
    
    # 检查进程是否运行
    if ps -p $ROS_PID >/dev/null 2>&1; then
        log "✓ ROS Drivable已启动 (PID: $ROS_PID)"
        log "日志文件: $log_file"
        
        # 检查节点是否注册
        if rosnode list | grep -q "drivable"; then
            log "节点已成功注册到ROS Master"
        else
            log "⚠ 节点未注册到ROS Master，可能有启动问题"
        fi
        
        return 0
    else
        log "[错误] ROS Drivable启动失败!"
        log "最后10行日志:"
        tail -n 10 "$log_file" | tee -a "$MAIN_LOG"
        return 1
    fi
}

# ==============================================
# 主执行流程
# ==============================================

# 初始化日志系统
init_logging

# 记录开始时间
START_TIME=$(date +%s)

# 检查必要命令
check_command roslaunch "ROS启动命令" || exit 1
check_command rospack "ROS包管理" || exit 1
check_command pgrep "进程查找" || exit 1

# 加载必要环境
if ! load_environments; then
    log "[致命错误] 无法加载ROS环境"
    exit 2
fi

# 只关闭rosbridge节点
if ! stop_rosbridge; then
    log "[警告] rosbridge停止过程可能不完整"
fi

# 启动ROS Drivable
if ! start_ros_Drivable; then
    log "[致命错误] 无法启动ROS Drivable"
    exit 3
fi

# 计算运行时间
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# 完成信息
{
    echo ""
    echo "=============================================="
    echo "ROS Drivable启动成功!"
    echo "总耗时: $DURATION 秒"
    echo "主日志文件: $MAIN_LOG"
    
    if [ -n "$ROS_PID" ]; then
        echo "ROS Drivable PID: $ROS_PID"
        echo "停止命令: kill $ROS_PID"
    fi
    
    # 显示当前运行的ROS节点
    echo "当前活动ROS节点:"
    rosnode list 2>/dev/null || echo "无节点或roscore未运行"
    echo "=============================================="
} | tee -a "$MAIN_LOG"

exit 0
