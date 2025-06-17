import tkinter as tk
from tkinter import messagebox
import random
from collections import deque
from typing import List, Dict, Deque
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np

class Passenger:
    def __init__(self, current_floor: str, target_floor: str, direction: str):
        self.current_floor = current_floor
        self.target_floor = target_floor
        self.direction = direction
        self.waiting_time = 0
        self.id = id(self)  # 唯一标识乘客

class Elevator:
    def __init__(self, eid: int, allowed_floors: List[str], max_capacity: int):
        self.eid = eid
        self.current_floor = allowed_floors[0]
        self.allowed_floors = allowed_floors
        self.max_capacity = max_capacity
        self.direction = "idle"  # up, down, idle
        self.passengers: List[Passenger] = []
        self.target_floors = deque()
        self.status = "idle"
        self.current_y = 40 + allowed_floors.index(self.current_floor) * 40  # 电梯Y坐标

class ElevatorSystemGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("电梯调度仿真系统")
        self.master.geometry("1200x700")
        self.master.configure(bg="#f0f7ff")  # 主背景色
        
        # 色彩方案
        self.colors = {
            "bg_main": "#f0f7ff",       # 主背景色
            "bg_panel": "#ffffff",      # 面板背景色
            "bg_button": "#e3f2fd",     # 按钮背景色
            "bg_button_hover": "#bbdefb", # 按钮悬停色
            "fg_text": "#334155",       # 正文文字色
            "fg_highlight": "#1e40af",  # 强调文字色
            "elevator_idle": "#bfdbfe", # 电梯空闲色
            "elevator_up": "#3b82f6",   # 电梯上行色
            "elevator_down": "#2563eb", # 电梯下行色
            "passenger_wait": "#f87171",# 等待乘客色
            "peak_period": "#f59e0b",   # 高峰时段色
            "grid_line": "#e2e8f0",     # 网格线色
            "shadow": "#ddd",           # 阴影色
            "dark_bg": "#1e293b",       # 深色模式背景
            "dark_fg": "#e2e8f0"        # 深色模式文字
        }
        self.dark_mode = False
        
        self.running = False
        self.timer = None
        self.elevator_animations = {}  # 存储电梯动画状态
        
        # ========== 顶部控制栏 ==========
        self.top_frame = tk.Frame(master, relief=tk.RAISED, bd=1, bg=self.colors["bg_panel"])
        self.top_frame.pack(fill=tk.X, padx=15, pady=10)
        
        # 左侧参数设置
        self.param_frame = tk.Frame(self.top_frame, bg=self.colors["bg_panel"])
        self.param_frame.pack(side=tk.LEFT, padx=5)
        
        tk.Label(self.param_frame, text="电梯数量:", bg=self.colors["bg_panel"], 
                fg=self.colors["fg_text"]).grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.n_elevators_var = tk.IntVar(value=3)
        tk.Spinbox(self.param_frame, from_=1, to=6, textvariable=self.n_elevators_var, 
                  width=5, bg=self.colors["bg_main"], fg=self.colors["fg_text"]).grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(self.param_frame, text="地上楼层:", bg=self.colors["bg_panel"], 
                fg=self.colors["fg_text"]).grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.floors_up_var = tk.IntVar(value=10)
        tk.Entry(self.param_frame, textvariable=self.floors_up_var, width=5, 
                bg=self.colors["bg_main"], fg=self.colors["fg_text"]).grid(row=1, column=1, padx=5, pady=5)
        
        tk.Label(self.param_frame, text="地下楼层:", bg=self.colors["bg_panel"], 
                fg=self.colors["fg_text"]).grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.floors_down_var = tk.IntVar(value=5)
        tk.Entry(self.param_frame, textvariable=self.floors_down_var, width=5, 
                bg=self.colors["bg_main"], fg=self.colors["fg_text"]).grid(row=2, column=1, padx=5, pady=5)
        
        tk.Label(self.param_frame, text="电梯容量:", bg=self.colors["bg_panel"], 
                fg=self.colors["fg_text"]).grid(row=3, column=0, padx=5, pady=5, sticky="e")
        self.capacity_var = tk.IntVar(value=13)
        tk.Entry(self.param_frame, textvariable=self.capacity_var, width=5, 
                bg=self.colors["bg_main"], fg=self.colors["fg_text"]).grid(row=3, column=1, padx=5, pady=5)
        
        # 右侧高峰设置
        self.peak_frame = tk.Frame(self.top_frame, bg=self.colors["bg_panel"])
        self.peak_frame.pack(side=tk.LEFT, padx=20)
        
        tk.Label(self.peak_frame, text="早高峰:", bg=self.colors["bg_panel"], 
                fg=self.colors["fg_text"]).grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.peak_morning_var = tk.StringVar(value="07:00-09:00")
        tk.Entry(self.peak_frame, textvariable=self.peak_morning_var, width=10, 
                bg=self.colors["bg_main"], fg=self.colors["fg_text"]).grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(self.peak_frame, text="晚高峰:", bg=self.colors["bg_panel"], 
                fg=self.colors["fg_text"]).grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.peak_evening_var = tk.StringVar(value="18:00-21:00")
        tk.Entry(self.peak_frame, textvariable=self.peak_evening_var, width=10, 
                bg=self.colors["bg_main"], fg=self.colors["fg_text"]).grid(row=1, column=1, padx=5, pady=5)
        
        # 功能按钮
        self.btn_frame = tk.Frame(self.top_frame, bg=self.colors["bg_panel"])
        self.btn_frame.pack(side=tk.RIGHT, padx=5)
        
        self.elevator_floors_btn = self.create_hover_button(
            self.btn_frame, "设置停靠楼层", self.set_elevator_floors_dialog)
        self.elevator_floors_btn.grid(row=0, column=0, padx=5, pady=5)
        
        self.start_btn = self.create_hover_button(self.btn_frame, "开始仿真", self.start_simulation)
        self.start_btn.grid(row=0, column=1, padx=5, pady=5)
        
        self.stop_btn = self.create_hover_button(self.btn_frame, "停止仿真", self.stop_simulation)
        self.stop_btn.grid(row=0, column=2, padx=5, pady=5)
        self.stop_btn.config(state=tk.DISABLED)
        
        self.dark_mode_btn = self.create_hover_button(self.btn_frame, "🌙", self.toggle_dark_mode)
        self.dark_mode_btn.grid(row=0, column=3, padx=5, pady=5)
        
        self.status_label = tk.Label(self.top_frame, text="就绪", fg=self.colors["fg_highlight"],
                                    bg=self.colors["bg_panel"], font=("Arial", 9, "bold"))
        self.status_label.pack(side=tk.RIGHT, padx=10)
        
        # ========== 主内容区域 ==========
        self.main_frame = tk.Frame(master, bg=self.colors["bg_main"])
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # ========== 仿真图形区域 ==========
        self.sim_frame = tk.Frame(self.main_frame, bg=self.colors["bg_panel"], 
                                 relief=tk.RAISED, bd=1)
        self.sim_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.canvas = tk.Canvas(self.sim_frame, bg=self.colors["bg_main"],
                               highlightthickness=0, relief=tk.FLAT)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.time_label = tk.Label(self.sim_frame, text="", 
                                  bg=self.colors["bg_panel"], fg=self.colors["fg_text"],
                                  font=("Arial", 10, "bold"))
        self.time_label.pack(pady=5)
        
        # ========== 统计信息区域 ==========
        self.stats_frame = tk.Frame(self.main_frame, bg=self.colors["bg_panel"],
                                  relief=tk.RAISED, bd=1, width=300)
        self.stats_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=5, pady=5)
        self.stats_frame.pack_propagate(False)  # 防止内容影响Frame大小
        
        tk.Label(self.stats_frame, text="系统统计", bg=self.colors["bg_panel"],
               fg=self.colors["fg_highlight"], font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=10, padx=10)
        
        self.stats_text = tk.Text(self.stats_frame, height=12, width=30, wrap=tk.WORD,
                                bg=self.colors["bg_main"], fg=self.colors["fg_text"],
                                relief=tk.FLAT, bd=1)
        self.stats_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.stats_text.config(state=tk.DISABLED)
        
        # 图表区域
        self.chart_frame = tk.Frame(self.stats_frame, bg=self.colors["bg_panel"],
                                  relief=tk.SUNKEN, bd=1)
        self.chart_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.fig = Figure(figsize=(2.8, 3), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas_chart = FigureCanvasTkAgg(self.fig, self.chart_frame)
        self.canvas_chart.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # 变量初始化
        self.elevator_floors = None
        self.floors = []
        self.elevators = []
        self.waiting_passengers: Dict[str, Deque[Passenger]] = {}
        self.time = 360  # 6:00
        self.peak_periods = {}
        self.passenger_history = []
        self.passenger_stats = {"total": 0, "boarded": 0, "wait_times": []}
        
        # 绑定窗口缩放事件
        self.master.bind("<Configure>", self.on_window_resize)

    def create_hover_button(self, parent, text, command):
        """创建带悬停效果的按钮"""
        button = tk.Button(parent, text=text, command=command,
                          bg=self.colors["bg_button"],
                          fg=self.colors["fg_text"],
                          activebackground=self.colors["bg_button_hover"],
                          activeforeground=self.colors["fg_highlight"],
                          relief=tk.FLAT,
                          bd=1,
                          padx=8, pady=4,
                          font=("Arial", 9))
        # 鼠标悬停效果
        button.bind("<Enter>", lambda e: button.config(bg=self.colors["bg_button_hover"]))
        button.bind("<Leave>", lambda e: button.config(bg=self.colors["bg_button"]))
        return button

    def set_elevator_floors_dialog(self):
        """设置电梯停靠楼层的模态对话框"""
        n_elev = self.n_elevators_var.get()
        n_up = self.floors_up_var.get()
        n_down = self.floors_down_var.get()
        if n_up < 1 or n_down < 0:
            messagebox.showerror("错误", "楼层数必须为正整数")
            return
        
        all_floors = [f"F{i}" for i in range(n_up, 0, -1)] + ["0"] + [f"B{i}" for i in range(n_down, 0, -1)]
        
        top = tk.Toplevel(self.master)
        top.title("电梯停靠楼层设置")
        top.transient(self.master)
        top.grab_set()
        top.configure(bg=self.colors["bg_panel"])
        top.geometry(f"{60+len(all_floors)*60}x{80+30*n_elev}")
        
        # 标题行
        tk.Label(top, text="楼层", bg=self.colors["bg_panel"], fg=self.colors["fg_text"],
               font=("Arial", 9, "bold")).grid(row=0, column=0, padx=10, pady=5)
        for i in range(n_elev):
            tk.Label(top, text=f"电梯{i+1}", bg=self.colors["bg_panel"], fg=self.colors["fg_text"],
                   font=("Arial", 9, "bold")).grid(row=0, column=i+1, padx=10, pady=5)
        
        vars_ = []
        for j, floor in enumerate(all_floors):
            tk.Label(top, text=floor, bg=self.colors["bg_panel"], fg=self.colors["fg_text"],
                   anchor=tk.E).grid(row=j+1, column=0, padx=5, pady=2)
            row_vars = []
            for i in range(n_elev):
                v = tk.IntVar(value=1)
                c = tk.Checkbutton(top, variable=v, bg=self.colors["bg_panel"],
                                 activebackground=self.colors["bg_button"],
                                 highlightthickness=0)
                c.grid(row=j+1, column=i+1, padx=5, pady=2)
                row_vars.append(v)
            vars_.append(row_vars)
        
        def save():
            self.elevator_floors = []
            for i in range(n_elev):
                floors = [all_floors[j] for j in range(len(all_floors)) if vars_[j][i].get()]
                if not floors:
                    messagebox.showerror("错误", f"电梯{i+1}必须至少选择一个楼层")
                    return
                self.elevator_floors.append(floors)
            top.destroy()
        
        tk.Button(top, text="保存", command=save,
                bg=self.colors["bg_button"], fg=self.colors["fg_text"],
                activebackground=self.colors["bg_button_hover"],
                relief=tk.FLAT, bd=1, padx=10, pady=4).grid(
            row=len(all_floors)+1, column=0, columnspan=n_elev+1, pady=10)
        
        top.wait_window()

    def parse_peak_period(self, s):
        """解析高峰时间段"""
        try:
            start, end = s.split("-")
            h1, m1 = map(int, start.split(":"))
            h2, m2 = map(int, end.split(":"))
            return (h1*60+m1, h2*60+m2)
        except:
            messagebox.showerror("错误", "高峰时间格式应为 hh:mm-hh:mm")
            return (0, 0)

    def setup_simulation(self):
        """初始化仿真参数"""
        n_elev = self.n_elevators_var.get()
        n_up = self.floors_up_var.get()
        n_down = self.floors_down_var.get()
        capacity = self.capacity_var.get()
        
        if n_up < 1 or n_down < 0 or n_elev < 1 or n_elev > 6 or capacity < 1:
            messagebox.showerror("错误", "参数非法，请检查输入")
            return False
        
        all_floors = [f"F{i}" for i in range(n_up, 0, -1)] + ["0"] + [f"B{i}" for i in range(n_down, 0, -1)]
        
        if self.elevator_floors is None:
            self.elevator_floors = [all_floors for _ in range(n_elev)]
        
        self.floors = all_floors
        self.elevators = [Elevator(i+1, self.elevator_floors[i], capacity) for i in range(n_elev)]
        self.waiting_passengers = {f: deque() for f in self.floors}
        self.time = 360  # 6:00
        self.peak_periods = {
            "morning": self.parse_peak_period(self.peak_morning_var.get()),
            "evening": self.parse_peak_period(self.peak_evening_var.get())
        }
        self.passenger_history = []
        self.passenger_stats = {"total": 0, "boarded": 0, "wait_times": []}
        
        # 初始化图表
        self.ax.clear()
        self.ax.set_facecolor(self.colors["bg_main"] if not self.dark_mode else self.colors["dark_bg"])
        self.ax.tick_params(axis='both', colors=self.colors["fg_text"] if not self.dark_mode else self.colors["dark_fg"])
        self.ax.spines['left'].set_color(self.colors["grid_line"] if not self.dark_mode else "#475569")
        self.ax.spines['right'].set_color(self.colors["grid_line"] if not self.dark_mode else "#475569")
        self.ax.spines['top'].set_color(self.colors["grid_line"] if not self.dark_mode else "#475569")
        self.ax.spines['bottom'].set_color(self.colors["grid_line"] if not self.dark_mode else "#475569")
        self.ax.set_title("乘客等待时间", color=self.colors["fg_highlight"] if not self.dark_mode else "#93c5fd")
        self.ax.set_xlabel("乘客编号", color=self.colors["fg_text"] if not self.dark_mode else self.colors["dark_fg"])
        self.ax.set_ylabel("等待时间(分钟)", color=self.colors["fg_text"] if not self.dark_mode else self.colors["dark_fg"])
        self.canvas_chart.draw()
        
        # 初始化画布
        self.canvas.delete("all")
        self.draw_static()
        
        return True

    def start_simulation(self):
        """开始仿真"""
        if not self.setup_simulation():
            return
        
        self.running = True
        self.elevator_floors_btn.config(state=tk.DISABLED)
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_label.config(text="仿真运行中...")
        self.update_simulation()

    def stop_simulation(self):
        """停止仿真"""
        self.running = False
        self.elevator_floors_btn.config(state=tk.NORMAL)
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_label.config(text="仿真已停止")
        if self.timer:
            self.master.after_cancel(self.timer)
            self.timer = None
        self.update_stats()

    def is_peak(self):
        """判断是否处于高峰时段"""
        current_minute = self.time % 1440
        for (start, end) in self.peak_periods.values():
            if start <= current_minute < end:
                return True
        return False

    def generate_passengers(self):
        """生成乘客"""
        base_rate = 0.01 if not self.is_peak() else 0.06
        for floor in self.floors:
            if random.random() < base_rate:
                possible_targets = [f for f in self.floors if f != floor]
                current_minute = self.time % 1440
                peak = False
                direction = ""
                target = random.choice(possible_targets)
                
                # 高峰时段特殊处理
                if current_minute in range(*self.peak_periods.get("morning", (0, 0))):
                    if floor in self.floors[-6:]:  # 假设最后6层为高层
                        target = random.choice(self.floors[:-6])
                        direction = "up"
                        peak = True
                elif current_minute in range(*self.peak_periods.get("evening", (0, 0))):
                    if floor in self.floors[:-6]:
                        target = random.choice(self.floors[-6:])
                        direction = "down"
                        peak = True
                
                # 非高峰时段随机方向
                if not peak:
                    target = random.choice(possible_targets)
                    direction = "up" if self.floors.index(target) < self.floors.index(floor) else "down"
                
                p = Passenger(floor, target, direction)
                self.waiting_passengers[floor].append(p)
                self.passenger_history.append(p)
                self.passenger_stats["total"] += 1

    def step_elevators(self):
        """电梯运行逻辑"""
        # 计算各楼层等待情况
        floor_waits = {f: (sum(p.waiting_time for p in self.waiting_passengers[f]), len(self.waiting_passengers[f]))
                       for f in self.floors}
        elevator_targets = set()
        
        for elevator in self.elevators:
            # 下客
            departing = [p for p in elevator.passengers if p.target_floor == elevator.current_floor]
            for p in departing:
                elevator.passengers.remove(p)
                if p in self.passenger_history:
                    self.passenger_stats["boarded"] += 1
                    self.passenger_stats["wait_times"].append(p.waiting_time)
            
            # 上客
            floor_queue = self.waiting_passengers[elevator.current_floor]
            to_board = []
            for p in list(floor_queue):
                if (p.direction == elevator.direction or elevator.direction == "idle") and p.target_floor in elevator.allowed_floors:
                    to_board.append(p)
            
            # 计算可用座位
            available_slots = elevator.max_capacity - len(elevator.passengers)
            for p in to_board[:available_slots]:
                elevator.passengers.append(p)
                floor_queue.remove(p)
                if p.target_floor not in elevator.target_floors:
                    elevator.target_floors.append(p.target_floor)
            
            # 确定下一个目标楼层
            next_dest = None
            if elevator.passengers:
                # 根据车内乘客目标确定方向
                targets = [self.floors.index(p.target_floor) for p in elevator.passengers]
                avg_target = sum(targets) / len(targets)
                curr_idx = self.floors.index(elevator.current_floor)
                if avg_target < curr_idx:
                    elevator.direction = "up"
                elif avg_target > curr_idx:
                    elevator.direction = "down"
                else:
                    elevator.direction = "idle"
            else:
                # 响应等待人数多/等待时间久的楼层
                candidates = [(f, floor_waits[f][1], floor_waits[f][0]) for f in elevator.allowed_floors
                              if floor_waits[f][1] > 0 and f not in elevator_targets]
                if candidates:
                    candidates.sort(key=lambda x: (-x[1], -x[2]))
                    next_dest = candidates[0][0]
                    elevator_targets.add(next_dest)
                    curr_idx = self.floors.index(elevator.current_floor)
                    target_idx = self.floors.index(next_dest)
                    if target_idx < curr_idx:
                        elevator.direction = "up"
                    elif target_idx > curr_idx:
                        elevator.direction = "down"
                    else:
                        elevator.direction = "idle"
                else:
                    elevator.direction = "idle"
            
            # 记录移动前位置用于动画
            if elevator.direction in ["up", "down"]:
                elevator.from_y = elevator.current_y
                curr_idx = self.floors.index(elevator.current_floor)
                if elevator.direction == "up" and curr_idx > 0 and self.floors[curr_idx-1] in elevator.allowed_floors:
                    elevator.current_floor = self.floors[curr_idx-1]
                elif elevator.direction == "down" and curr_idx < len(self.floors)-1 and self.floors[curr_idx+1] in elevator.allowed_floors:
                    elevator.current_floor = self.floors[curr_idx+1]
                elevator.to_y = 40 + self.floors.index(elevator.current_floor) * 40
                elevator.move_step = 0

    def animate_elevator_movement(self, elevator):
        """电梯移动动画"""
        if not hasattr(elevator, 'from_y') or not hasattr(elevator, 'to_y'):
            return
        
        step = 5  # 动画步长
        elevator.move_step += step
        
        # 计算当前Y坐标
        if elevator.from_y < elevator.to_y:
            elevator.current_y = min(elevator.from_y + elevator.move_step, elevator.to_y)
        else:
            elevator.current_y = max(elevator.from_y - elevator.move_step, elevator.to_y)
        
        # 绘制电梯
        self.draw_elevators()
        
        # 继续动画或结束
        if elevator.current_y != elevator.to_y:
            self.elevator_animations[elevator.eid] = self.master.after(30, lambda: self.animate_elevator_movement(elevator))
        else:
            # 清除动画状态
            if elevator.eid in self.elevator_animations:
                self.master.after_cancel(self.elevator_animations[elevator.eid])
                del self.elevator_animations[elevator.eid]
            if hasattr(elevator, 'from_y'):
                del elevator.from_y
            if hasattr(elevator, 'to_y'):
                del elevator.to_y

    def draw_static(self):
        """绘制静态背景"""
        n_elev = len(self.elevators)
        self.canvas.delete("all")
        
        # 绘制网格线和楼层标签
        for i, floor in enumerate(self.floors):
            y = 40 + i * 40
            self.canvas.create_line(60, y, 60 + n_elev * 80, y, 
                                   fill=self.colors["grid_line"], width=1)
            self.canvas.create_text(40, y, text=floor, 
                                   font=("Arial", 10), fill=self.colors["fg_text"])
        
        # 绘制电梯轨道
        for eid in range(n_elev):
            x = 60 + eid * 80
            self.canvas.create_rectangle(x, 40, x + 60, 40 + len(self.floors) * 40, 
                                        outline="#c0c0c0", width=1, dash=(4, 4))

    def draw_elevators(self):
        """绘制电梯和乘客"""
        n_elev = len(self.elevators)
        self.canvas.delete("elevator")  # 清除旧电梯
        
        for eid, elevator in enumerate(self.elevators):
            try:
                y = elevator.current_y
            except AttributeError:
                # 如果没有current_y属性，使用默认值
                y = 40 + self.floors.index(elevator.current_floor) * 40
            
            x = 60 + eid * 80
            
            # 根据电梯状态设置颜色
            if elevator.direction == "up":
                color = self.colors["elevator_up"]
            elif elevator.direction == "down":
                color = self.colors["elevator_down"]
            else:
                color = self.colors["elevator_idle"]
            
            # 绘制带阴影的电梯
            self.canvas.create_rectangle(x+5, y-30, x+55, y+10, 
                                        fill=color, outline="black", width=1,
                                        tags="elevator")
            
            # 绘制电梯状态图标
            if elevator.direction == "up":
                self.canvas.create_polygon(
                    x+45, y-25, x+50, y-30, x+55, y-25,
                    fill="white", outline="black", width=1, tags="elevator"
                )
            elif elevator.direction == "down":
                self.canvas.create_polygon(
                    x+45, y+5, x+50, y+10, x+55, y+5,
                    fill="white", outline="black", width=1, tags="elevator"
                )
            
            # 显示电梯编号和人数
            self.canvas.create_text(x+30, y-18, text=f"电梯{elevator.eid}",
                                   font=("Arial", 9, "bold"), fill="black", tags="elevator")
            self.canvas.create_text(x+30, y-5, 
                                   text=f"{len(elevator.passengers)}/{elevator.max_capacity}",
                                   font=("Arial", 8), fill="black", tags="elevator")
        
        # 绘制等待乘客
        for i, floor in enumerate(self.floors):
            q = self.waiting_passengers[floor]
            y = 40 + i * 40
            n = len(q)
            if n > 0:
                self.canvas.create_oval(15, y-5, 25, y+5, fill=self.colors["passenger_wait"],
                                      outline="", tags="passenger")
                self.canvas.create_text(30, y, text=str(n), font=("Arial", 9),
                                      fill=self.colors["passenger_wait"], tags="passenger")

    def draw_time(self):
        """绘制时间和高峰状态"""
        hour = (self.time // 60) % 24
        minute = self.time % 60
        peak_text = "是" if self.is_peak() else "否"
        peak_color = self.colors["peak_period"] if self.is_peak() else self.colors["fg_text"]
        
        self.time_label.config(
            text=f"时间：{hour:02d}:{minute:02d}   高峰：{peak_text}",
            fg=peak_color,
            font=("Arial", 10, "bold" if self.is_peak() else "")
        )

    def update_stats(self):
        """更新统计信息"""
        self.stats_text.config(state=tk.NORMAL)
        self.stats_text.delete(1.0, tk.END)
        
        # 基本信息
        self.stats_text.insert(tk.END, "===== 系统状态 =====\n\n")
        self.stats_text.insert(tk.END, f"仿真时间: {(self.time // 60) % 24:02d}:{self.time % 60:02d}\n")
        self.stats_text.insert(tk.END, f"当前高峰: {'是' if self.is_peak() else '否'}\n\n")
        
        # 乘客统计
        self.stats_text.insert(tk.END, "===== 乘客统计 =====\n\n")
        self.stats_text.insert(tk.END, f"总生成乘客: {self.passenger_stats['total']}\n")
        self.stats_text.insert(tk.END, f"已乘梯乘客: {self.passenger_stats['boarded']}\n")
        
        if self.passenger_stats["boarded"] > 0:
            avg_wait = sum(self.passenger_stats["wait_times"]) / self.passenger_stats["boarded"]
            self.stats_text.insert(tk.END, f"平均等待时间: {avg_wait:.2f} 分钟\n")
            self.stats_text.insert(tk.END, f"最长等待时间: {max(self.passenger_stats['wait_times'])} 分钟\n")
        else:
            self.stats_text.insert(tk.END, "平均等待时间: 0 分钟\n")
        
        # 电梯状态
        self.stats_text.insert(tk.END, "\n===== 电梯状态 =====\n\n")
        for elevator in self.elevators:
            passengers = len(elevator.passengers)
            self.stats_text.insert(tk.END, f"电梯{elevator.eid}: {elevator.current_floor}, {elevator.direction}, "
                                          f"{passengers}/{elevator.max_capacity}人\n")
        
        self.stats_text.config(state=tk.DISABLED)
        
        # 更新图表
        if self.passenger_stats["wait_times"]:
            self.ax.clear()
            x = np.arange(1, len(self.passenger_stats["wait_times"]) + 1)
            y = self.passenger_stats["wait_times"]
            self.ax.plot(x, y, 'o-', color=self.colors["elevator_up"], alpha=0.7, linewidth=1.5)
            self.ax.set_ylim(0, max(y) + 5 if y else 10)
            self.ax.grid(axis='y', linestyle='--', alpha=0.7)
            self.canvas_chart.draw()

    def update_simulation(self):
        """更新仿真状态