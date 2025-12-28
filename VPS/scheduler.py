import time
import random
import os
from datetime import datetime, timedelta
from auto_login import AutoLogin  # 假设你的类名是 ClawAuto

# 配置
MIN_DAYS = 15
MAX_DAYS = 25
CHECK_INTERVAL = 3600  # 每小时检查一次
STATE_FILE = "next_run_time.txt"

def get_next_run():
    """读取或生成下一次运行时间"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            try:
                ts = float(f.read().strip())
                return datetime.fromtimestamp(ts)
            except:
                pass
    return None

def save_next_run(next_time):
    """保存下一次运行时间"""
    with open(STATE_FILE, "w") as f:
        f.write(str(next_time.timestamp()))

def set_random_next_run():
    """计算 15-25 天后的随机时间"""
    days = random.randint(MIN_DAYS, MAX_DAYS)
    hours = random.randint(0, 23)
    minutes = random.randint(0, 59)
    
    next_time = datetime.now() + timedelta(days=days, hours=hours, minutes=minutes)
    save_next_run(next_time)
    print(f"📅 已排期下次执行时间: {next_time.strftime('%Y-%m-%d %H:%M:%S')}")
    return next_time

def main():
    print("🚀 Claw 自动化定时调度器启动...")
    
    while True:
        next_run = get_next_run()
        now = datetime.now()

        # 如果没有记录，或者已经过了预定时间
        if next_run is None or now >= next_run:
            print(f"⏰ 到达执行时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # --- 执行你的自动化脚本 ---
            try:
                app = ClawAuto()
                app.run()
                print("✅ 任务执行完毕")
            except Exception as e:
                print(f"❌ 任务执行出错: {e}")
            
            # 无论成功失败，都重新设定下一次时间点
            next_run = set_random_next_run()
            
            # 发送 TG 通知（可选）
            # app.tg.send(f"📅 任务已完成，下次执行约在: {next_run.strftime('%Y-%m-%d')}")

        else:
            # 还没到时间，显示倒计时
            diff = next_run - now
            print(f"💤 距离下次执行还有: {diff.days}天 {diff.seconds // 3600}小时 (预计: {next_run.strftime('%Y-%m-%d %H:%M:%S')})")
            
        # 等待一小时再次检查
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
