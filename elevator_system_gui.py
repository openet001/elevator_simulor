import tkinter as tk
from tkinter import messagebox
import random
from collections import deque
from typing import List, Dict, Deque
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import time

class Passenger:
    def __init__(self, current_floor: str, target_floor: str, direction: str):
        self.current_floor = current_floor
        self.target_floor = target_floor
        self.direction = direction
        self.waiting_time = 0
        self.id = id(self)

class Elevator:
    def __init__(self, eid: int, allowed_floors: List[str], max_capacity: int):
        self.eid = eid
        self.current_floor = allowed_floors[-1]
        self.allowed_floors = allowed_floors
        self.max_capacity = max_capacity
        self.direction = "idle"
        self.passengers: List[Passenger] = []
        self.target_floors = deque()
        self.status = "idle"
        self.current_y = 40 + allowed_floors.index(self.current_floor) * 40
        self.door_open = False
        self.door_timer = 0
        self.idle_timer = 0
        self.emergency_reset = False
        self.resetting = False
        self.floors = allowed_floors
        self.busy_for_call: Dict[str, str] = {}

    def is_idle_too_long(self, max_idle_time=10):
        return self.direction == "idle" and self.idle_timer >= max_idle_time

    def get_direction_symbol(self):
        if self.direction == "up":
            return "↑"
        elif self.direction == "down":
            return "↓"
        return "○"

    def start_emergency_reset(self):
        self.emergency_reset = True
        self.target_floors = deque()
        if self.current_floor != "0":
            if self.floors.index(self.current_floor) > self.floors.index("0"):
                self.direction = "down"
            else:
                self.direction = "up"

class ElevatorSystemGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("电梯调度仿真系统 作者：chuck 847297@qq.com [未经充分测试，请勿用于实际模拟]")
        self.master.geometry("1200x700")
        self.colors = {
            "bg_main": "#f0f7ff",
            "bg_panel": "#ffffff",
            "bg_button": "#e3f2fd",
            "bg_button_hover": "#bbdefb",
            "fg_text": "#334155",
            "fg_highlight": "#1e40af",
            "elevator_idle": "#bfdbfe",
            "elevator_up": "#3b82f6",
            "elevator_down": "#2563eb",
            "passenger_wait": "#f87171",
            "peak_period": "#f59e0b",
            "grid_line": "#e2e8f0",
            "shadow": "#ddd",
            "dark_bg": "#1e293b",
            "dark_fg": "#e2e8f0"
        }
        self.dark_mode = False
        self.running = False
        self.timer = None
        self.elevator_animations = {}
        self.use_real_time = False
        self.last_real_time_update = 0

        self.top_frame = tk.Frame(master, relief=tk.RAISED, bd=1, bg=self.colors["bg_panel"])
        self.top_frame.pack(fill=tk.X, padx=15, pady=10)
        self.param_frame = tk.Frame(self.top_frame, bg=self.colors["bg_panel"])
        self.param_frame.pack(side=tk.LEFT, padx=5)
        tk.Label(self.param_frame, text="电梯数量:", bg=self.colors["bg_panel"], fg=self.colors["fg_text"]).grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.n_elevators_var = tk.IntVar(value=3)
        tk.Spinbox(self.param_frame, from_=1, to=6, textvariable=self.n_elevators_var, width=5, bg=self.colors["bg_main"], fg=self.colors["fg_text"]).grid(row=0, column=1, padx=5, pady=5)
        tk.Label(self.param_frame, text="地上楼层:", bg=self.colors["bg_panel"], fg=self.colors["fg_text"]).grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.floors_up_var = tk.IntVar(value=10)
        tk.Entry(self.param_frame, textvariable=self.floors_up_var, width=5, bg=self.colors["bg_main"], fg=self.colors["fg_text"]).grid(row=1, column=1, padx=5, pady=5)
        tk.Label(self.param_frame, text="地下楼层:", bg=self.colors["bg_panel"], fg=self.colors["fg_text"]).grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.floors_down_var = tk.IntVar(value=2)
        tk.Entry(self.param_frame, textvariable=self.floors_down_var, width=5, bg=self.colors["bg_main"], fg=self.colors["fg_text"]).grid(row=2, column=1, padx=5, pady=5)
        tk.Label(self.param_frame, text="电梯容量:", bg=self.colors["bg_panel"], fg=self.colors["fg_text"]).grid(row=3, column=0, padx=5, pady=5, sticky="e")
        self.capacity_var = tk.IntVar(value=13)
        tk.Entry(self.param_frame, textvariable=self.capacity_var, width=5, bg=self.colors["bg_main"], fg=self.colors["fg_text"]).grid(row=3, column=1, padx=5, pady=5)
        self.peak_frame = tk.Frame(self.top_frame, bg=self.colors["bg_panel"])
        self.peak_frame.pack(side=tk.LEFT, padx=20)
        tk.Label(self.peak_frame, text="早高峰:", bg=self.colors["bg_panel"], fg=self.colors["fg_text"]).grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.peak_morning_var = tk.StringVar(value="07:00-09:00")
        tk.Entry(self.peak_frame, textvariable=self.peak_morning_var, width=10, bg=self.colors["bg_main"], fg=self.colors["fg_text"]).grid(row=0, column=1, padx=5, pady=5)
        tk.Label(self.peak_frame, text="晚高峰:", bg=self.colors["bg_panel"], fg=self.colors["fg_text"]).grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.peak_evening_var = tk.StringVar(value="18:00-21:00")
        tk.Entry(self.peak_frame, textvariable=self.peak_evening_var, width=10, bg=self.colors["bg_main"], fg=self.colors["fg_text"]).grid(row=1, column=1, padx=5, pady=5)
        self.btn_frame = tk.Frame(self.top_frame, bg=self.colors["bg_panel"])
        self.btn_frame.pack(side=tk.RIGHT, padx=5)
        self.elevator_floors_btn = self.create_hover_button(self.btn_frame, "设置停靠楼层", self.set_elevator_floors_dialog)
        self.elevator_floors_btn.grid(row=0, column=0, padx=5, pady=5)
        self.start_btn = self.create_hover_button(self.btn_frame, "开始仿真", self.start_simulation)
        self.start_btn.grid(row=0, column=1, padx=5, pady=5)
        self.stop_btn = self.create_hover_button(self.btn_frame, "停止仿真", self.stop_simulation)
        self.stop_btn.grid(row=0, column=2, padx=5, pady=5)
        self.stop_btn.config(state=tk.DISABLED)
        self.time_mode_btn = self.create_hover_button(self.btn_frame, "使用真实时间", self.toggle_time_mode)
        self.time_mode_btn.grid(row=0, column=3, padx=5, pady=5)
        self.dark_mode_btn = self.create_hover_button(self.btn_frame, "🌙", self.toggle_dark_mode)
        self.dark_mode_btn.grid(row=0, column=4, padx=5, pady=5)
        self.emergency_btn = self.create_hover_button(self.btn_frame, "紧急复位", self.emergency_reset)
        self.emergency_btn.grid(row=0, column=5, padx=5, pady=5)
        self.emergency_btn.config(state=tk.DISABLED)
        self.status_label = tk.Label(self.top_frame, text="就绪", fg=self.colors["fg_highlight"],
                                    bg=self.colors["bg_panel"], font=("Arial", 9, "bold"))
        self.status_label.pack(side=tk.RIGHT, padx=10)
        self.main_frame = tk.Frame(master, bg=self.colors["bg_main"])
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.sim_frame = tk.Frame(self.main_frame, bg=self.colors["bg_panel"], relief=tk.RAISED, bd=1)
        self.sim_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.canvas = tk.Canvas(self.sim_frame, bg=self.colors["bg_main"], highlightthickness=0, relief=tk.FLAT)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.time_label = tk.Label(self.sim_frame, text="", bg=self.colors["bg_panel"], fg=self.colors["fg_text"], font=("Arial", 10, "bold"))
        self.time_label.pack(pady=5)
        self.stats_frame = tk.Frame(self.main_frame, bg=self.colors["bg_panel"], relief=tk.RAISED, bd=1, width=300)
        self.stats_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=5, pady=5)
        self.stats_frame.pack_propagate(False)
        tk.Label(self.stats_frame, text="系统统计", bg=self.colors["bg_panel"],
               fg=self.colors["fg_highlight"], font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=10, padx=10)
        self.stats_text = tk.Text(self.stats_frame, height=12, width=30, wrap=tk.WORD,
                                bg=self.colors["bg_main"], fg=self.colors["fg_text"],
                                relief=tk.FLAT, bd=1)
        self.stats_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.stats_text.config(state=tk.DISABLED)
        self.chart_frame = tk.Frame(self.stats_frame, bg=self.colors["bg_panel"], relief=tk.SUNKEN, bd=1)
        self.chart_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.fig = Figure(figsize=(2.8, 3), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas_chart = FigureCanvasTkAgg(self.fig, self.chart_frame)
        self.canvas_chart.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.elevator_floors = None
        self.floors = []
        self.elevators = []
        self.waiting_passengers: Dict[str, Dict[str, Deque[Passenger]]] = {}
        self.time = 360
        self.peak_periods = {}
        self.passenger_history = []
        self.passenger_stats = {"total": 0, "boarded": 0, "wait_times": []}
        self.max_idle_time = 10
        self.master.bind("<Configure>", self.on_window_resize)
        self.setup_matplotlib_fonts()

    def setup_matplotlib_fonts(self):
        try:
            import matplotlib.font_manager as fm
            font_names = [f.name for f in fm.fontManager.ttflist]
            chinese_fonts = ['Microsoft JianhengHei', 'WenQuanYi Micro Hei', 'Heiti TC', 'Microsoft YaHei', 'SimSun']
            available_font = None
            for font in chinese_fonts:
                if font in font_names:
                    available_font = font
                    break
            if available_font:
                matplotlib.rcParams["font.family"] = available_font
        except Exception as e:
            print(f"字体配置错误: {e}")

    def create_hover_button(self, parent, text, command):
        button = tk.Button(parent, text=text, command=command,
                          bg=self.colors["bg_button"],
                          fg=self.colors["fg_text"],
                          activebackground=self.colors["bg_button_hover"],
                          activeforeground=self.colors["fg_highlight"],
                          relief=tk.FLAT,
                          bd=1,
                          padx=8, pady=4,
                          font=("Arial", 9))
        button.bind("<Enter>", lambda e: button.config(bg=self.colors["bg_button_hover"]))
        button.bind("<Leave>", lambda e: button.config(bg=self.colors["bg_button"]))
        return button

    def set_elevator_floors_dialog(self):
        n_elev = self.n_elevators_var.get()
        n_up = self.floors_up_var.get()
        n_down = self.floors_down_var.get()
        if n_up < 1 or n_down < 0:
            messagebox.showerror("错误", "楼层数必须为正整数")
            return
        all_floors = [f"F{i}" for i in range(n_up, 0, -1)] + ["0"] + [f"B{i}" for i in range(1, n_down+1)]
        top = tk.Toplevel(self.master)
        top.title("电梯停靠楼层设置")
        top.transient(self.master)
        top.grab_set()
        top.configure(bg=self.colors["bg_panel"])
        top.geometry(f"{60+len(all_floors)*60}x{80+30*n_elev}")
        tk.Label(top, text="楼层", bg=self.colors["bg_panel"], fg=self.colors["fg_text"], font=("Arial", 9, "bold")).grid(row=0, column=0, padx=10, pady=5)
        for i in range(n_elev):
            tk.Label(top, text=f"电梯{i+1}", bg=self.colors["bg_panel"], fg=self.colors["fg_text"], font=("Arial", 9, "bold")).grid(row=0, column=i+1, padx=10, pady=5)
        vars_ = []
        for j, floor in enumerate(all_floors):
            tk.Label(top, text=floor, bg=self.colors["bg_panel"], fg=self.colors["fg_text"], anchor=tk.E).grid(row=j+1, column=0, padx=5, pady=2)
            row_vars = []
            for i in range(n_elev):
                v = tk.IntVar(value=1)
                c = tk.Checkbutton(top, variable=v, bg=self.colors["bg_panel"],
                                 activebackground=self.colors["bg_button"],
                                 highlightthickness=0)
                c.grid(row=j+1, column=i+1, padx=5, pady=2)
                row_vars.append(v)
            vars_.append(row_vars)
        def save_settings():
            self.elevator_floors = []
            for i in range(n_elev):
                floors = []
                for j, floor in enumerate(all_floors):
                    if vars_[j][i].get() == 1:
                        floors.append(floor)
                self.elevator_floors.append(floors)
            top.destroy()
        btn_frame = tk.Frame(top, bg=self.colors["bg_panel"])
        btn_frame.grid(row=len(all_floors)+1, column=0, columnspan=n_elev+1, pady=10)
        save_btn = self.create_hover_button(btn_frame, "保存设置", save_settings)
        save_btn.pack(side=tk.RIGHT, padx=5)
        cancel_btn = self.create_hover_button(btn_frame, "取消", top.destroy)
        cancel_btn.pack(side=tk.RIGHT, padx=5)
        top.wait_window()

    def start_simulation(self):
        if self.running:
            return
        n_elevators = self.n_elevators_var.get()
        n_up = self.floors_up_var.get()
        n_down = self.floors_down_var.get()
        capacity = self.capacity_var.get()
        if n_up < 1 or n_down < 0:
            messagebox.showerror("错误", "楼层数必须为正整数")
            return
        self.floors = [f"F{i}" for i in range(n_up, 0, -1)] + ["0"] + [f"B{i}" for i in range(1, n_down+1)]
        if self.elevator_floors is None or len(self.elevator_floors) != n_elevators:
            self.elevator_floors = [self.floors.copy() for _ in range(n_elevators)]
        else:
            if len(self.elevator_floors) < n_elevators:
                for _ in range(n_elevators - len(self.elevator_floors)):
                    self.elevator_floors.append(self.floors.copy())
            elif len(self.elevator_floors) > n_elevators:
                self.elevator_floors = self.elevator_floors[:n_elevators]
        self.elevators = []
        for i in range(n_elevators):
            if not self.elevator_floors[i]:
                self.elevator_floors[i] = self.floors.copy()
            initial_floor = self.elevator_floors[i][-1]
            elevator = Elevator(i, self.elevator_floors[i], capacity)
            elevator.current_floor = initial_floor
            elevator.current_y = 40 + self.floors.index(initial_floor) * 40
            elevator.floors = self.floors
            elevator.busy_for_call = {}
            self.elevators.append(elevator)
        self.waiting_passengers = {floor: {"up": deque(), "down": deque()} for floor in self.floors}
        self.parse_peak_periods()
        self.passenger_stats = {"total": 0, "boarded": 0, "wait_times": []}
        self.running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.emergency_btn.config(state=tk.NORMAL)
        self.status_label.config(text="运行中（仿真时间）" if not self.use_real_time else "运行中（真实时间）")
        self.update_simulation()

    def stop_simulation(self):
        self.running = False
        if self.timer:
            self.master.after_cancel(self.timer)
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.emergency_btn.config(state=tk.DISABLED)
        self.status_label.config(text="已停止")

    def toggle_time_mode(self):
        self.use_real_time = not self.use_real_time
        if self.use_real_time:
            self.time_mode_btn.config(text="使用真实时间")
            self.time = self.get_current_hour_minute()
        else:
            self.time_mode_btn.config(text="使用仿真时间")
        self.status_label.config(text="运行中（真实时间）" if self.use_real_time else "运行中（仿真时间）")
        self.update_time_display()

    def get_current_hour_minute(self):
        current_time = time.localtime()
        return current_time.tm_hour * 60 + current_time.tm_min

    def parse_peak_periods(self):
        morning_str = self.peak_morning_var.get()
        evening_str = self.peak_evening_var.get()
        try:
            start, end = morning_str.split('-')
            start_hour, start_min = map(int, start.strip().split(':'))
            end_hour, end_min = map(int, end.strip().split(':'))
            self.peak_periods["morning"] = (start_hour * 60 + start_min, end_hour * 60 + end_min)
            start, end = evening_str.split('-')
            start_hour, start_min = map(int, start.strip().split(':'))
            end_hour, end_min = map(int, end.strip().split(':'))
            self.peak_periods["evening"] = (start_hour * 60 + start_min, end_hour * 60 + end_min)
        except:
            self.peak_periods["morning"] = (420, 540)
            self.peak_periods["evening"] = (1080, 1260)

    def is_peak_time(self):
        if "morning" in self.peak_periods:
            start, end = self.peak_periods["morning"]
            if start <= self.time < end:
                return True
        if "evening" in self.peak_periods:
            start, end = self.peak_periods["evening"]
            if start <= self.time < end:
                return True
        return False

    def generate_passengers(self):
        base_rate = 0.025
        if self.is_peak_time():
            base_rate = 0.075
        for floor in self.floors:
            if random.random() < base_rate:
                if floor == self.floors[0]:
                    direction = "down"
                elif floor == self.floors[-1]:
                    direction = "up"
                else:
                    direction = "up" if random.random() < 0.5 else "down"
                if direction == "up":
                    possible_targets = self.floors[:self.floors.index(floor)]
                else:
                    possible_targets = self.floors[self.floors.index(floor)+1:]
                if not possible_targets:
                    continue
                target_floor = random.choice(possible_targets)
                passenger = Passenger(floor, target_floor, direction)
                self.waiting_passengers[floor][direction].append(passenger)
                self.passenger_stats["total"] += 1

    def assign_elevators(self):
        for elevator in self.elevators:
            remove_list = []
            for key, reqdir in elevator.busy_for_call.items():
                if key == (elevator.current_floor, reqdir):
                    remove_list.append(key)
            for key in remove_list:
                del elevator.busy_for_call[key]
        for floor in self.floors:
            for direction in ["up", "down"]:
                if not self.waiting_passengers[floor][direction]:
                    continue
                already_assigned = False
                for elevator in self.elevators:
                    if (floor, direction) in elevator.busy_for_call:
                        already_assigned = True
                        break
                if already_assigned:
                    continue
                best_elevator = None
                min_dist = float('inf')
                for elevator in self.elevators:
                    if elevator.resetting or elevator.emergency_reset or floor not in elevator.allowed_floors:
                        continue
                    if elevator.direction == "idle" and not elevator.target_floors:
                        dist = abs(self.floors.index(floor) - self.floors.index(elevator.current_floor))
                        if dist < min_dist:
                            min_dist = dist
                            best_elevator = elevator
                if best_elevator:
                    best_elevator.target_floors.append(floor)
                    best_elevator.busy_for_call[(floor, direction)] = direction
                    if self.floors.index(floor) < self.floors.index(best_elevator.current_floor):
                        best_elevator.direction = "up"
                    elif self.floors.index(floor) > self.floors.index(best_elevator.current_floor):
                        best_elevator.direction = "down"
                    else:
                        best_elevator.direction = direction

    def move_elevators(self):
        for elevator in self.elevators:
            if getattr(elevator, "resetting", False):
                curr_idx = self.floors.index(elevator.current_floor)
                zero_idx = self.floors.index("0")
                if curr_idx > zero_idx:
                    elevator.current_floor = self.floors[curr_idx - 1]
                    elevator.current_y += 40
                    elevator.direction = "down"
                elif curr_idx < zero_idx:
                    elevator.current_floor = self.floors[curr_idx + 1]
                    elevator.current_y -= 40
                    elevator.direction = "up"
                else:
                    elevator.resetting = False
                    elevator.direction = "idle"
                    elevator.door_open = False
                    elevator.door_timer = 0
                    elevator.target_floors.clear()
                    elevator.passengers.clear()
                    # 全部电梯到0层才清空系统等待和统计
                    if all(not elev.resetting and elev.current_floor == "0" for elev in self.elevators):
                        for floor in self.floors:
                            self.waiting_passengers[floor]["up"].clear()
                            self.waiting_passengers[floor]["down"].clear()
                        self.passenger_stats = {"total": 0, "boarded": 0, "wait_times": []}
                continue
            if elevator.door_open:
                elevator.door_timer += 1
                if elevator.door_timer >= 3:
                    elevator.door_open = False
                    elevator.door_timer = 0
                continue
            curr_idx = self.floors.index(elevator.current_floor)
            if elevator.direction == "up" and curr_idx == 0:
                if elevator.passengers or elevator.target_floors:
                    elevator.direction = "down"
                else:
                    elevator.direction = "idle"
            elif elevator.direction == "down" and curr_idx == len(self.floors) - 1:
                if elevator.passengers or elevator.target_floors:
                    elevator.direction = "up"
                else:
                    elevator.direction = "idle"
            if elevator.direction == "idle" and elevator.target_floors:
                next_floor = elevator.target_floors[0]
                curr_idx = self.floors.index(elevator.current_floor)
                target_idx = self.floors.index(next_floor)
                if target_idx < curr_idx:
                    elevator.direction = "up"
                elif target_idx > curr_idx:
                    elevator.direction = "down"
                else:
                    elevator.direction = "idle"
            if not elevator.target_floors and not elevator.passengers:
                elevator.direction = "idle"
                elevator.idle_timer += 1
                continue
            else:
                elevator.idle_timer = 0
            move_next = False
            if elevator.direction == "up":
                next_idx = self.floors.index(elevator.current_floor) - 1
                if next_idx >= 0:
                    elevator.current_floor = self.floors[next_idx]
                    elevator.current_y -= 40
                    move_next = True
            elif elevator.direction == "down":
                next_idx = self.floors.index(elevator.current_floor) + 1
                if next_idx < len(self.floors):
                    elevator.current_floor = self.floors[next_idx]
                    elevator.current_y += 40
                    move_next = True
            else:
                move_next = False
            stop = False
            if elevator.passengers and any(p.target_floor == elevator.current_floor for p in elevator.passengers):
                stop = True
            if elevator.direction == "up" and self.waiting_passengers[elevator.current_floor]["up"]:
                stop = True
            if elevator.direction == "down" and self.waiting_passengers[elevator.current_floor]["down"]:
                stop = True
            curr_idx = self.floors.index(elevator.current_floor)
            if curr_idx == 0 and (self.waiting_passengers[elevator.current_floor]["up"] or self.waiting_passengers[elevator.current_floor]["down"]):
                stop = True
            if curr_idx == len(self.floors) - 1 and (self.waiting_passengers[elevator.current_floor]["up"] or self.waiting_passengers[elevator.current_floor]["down"]):
                stop = True
            if stop:
                elevator.door_open = True
                self.handle_passengers(elevator)
                self.update_direction_after_stop(elevator)
                curr_idx = self.floors.index(elevator.current_floor)
                if elevator.direction == "up" and curr_idx == 0:
                    if elevator.passengers or elevator.target_floors:
                        elevator.direction = "down"
                    else:
                        elevator.direction = "idle"
                elif elevator.direction == "down" and curr_idx == len(self.floors) - 1:
                    if elevator.passengers or elevator.target_floors:
                        elevator.direction = "up"
                    else:
                        elevator.direction = "idle"
            if elevator.direction == "up":
                curr_idx = self.floors.index(elevator.current_floor)
                targets = [self.floors.index(p.target_floor) for p in elevator.passengers if self.floors.index(p.target_floor) < curr_idx]
                waiting_above = any(self.waiting_passengers[self.floors[i]]["up"]
                                    for i in range(0, curr_idx))
                if not targets and not waiting_above and not elevator.target_floors:
                    elevator.direction = "idle"
            elif elevator.direction == "down":
                curr_idx = self.floors.index(elevator.current_floor)
                targets = [self.floors.index(p.target_floor) for p in elevator.passengers if self.floors.index(p.target_floor) > curr_idx]
                waiting_below = any(self.waiting_passengers[self.floors[i]]["down"]
                                    for i in range(curr_idx + 1, len(self.floors)))
                if not targets and not waiting_below and not elevator.target_floors:
                    elevator.direction = "idle"

    def handle_passengers(self, elevator):
        current_floor = elevator.current_floor
        leaving = [p for p in elevator.passengers if p.target_floor == current_floor]
        for p in leaving:
            elevator.passengers.remove(p)
            self.passenger_stats["boarded"] += 1
            self.passenger_stats["wait_times"].append(p.waiting_time)
        available_space = elevator.max_capacity - len(elevator.passengers)
        curr_idx = self.floors.index(current_floor)
        if curr_idx == 0 or curr_idx == len(self.floors) - 1:
            direction_list = ["up", "down"]
        else:
            direction_list = [elevator.direction]
        for direction in direction_list:
            if available_space <= 0:
                break
            queue = self.waiting_passengers[current_floor][direction]
            to_board = min(available_space, len(queue))
            for _ in range(to_board):
                p = queue.popleft()
                elevator.passengers.append(p)
                available_space -= 1
        for floor in self.floors:
            for d in ["up", "down"]:
                for p in self.waiting_passengers[floor][d]:
                    p.waiting_time += 1

    def update_direction_after_stop(self, elevator):
        curr_idx = self.floors.index(elevator.current_floor)
        remove_list = []
        for key, reqdir in elevator.busy_for_call.items():
            if key == (elevator.current_floor, reqdir):
                remove_list.append(key)
        for key in remove_list:
            del elevator.busy_for_call[key]
        if elevator.direction == "up":
            targets = [self.floors.index(p.target_floor) for p in elevator.passengers if self.floors.index(p.target_floor) < curr_idx]
            waiting_above = any(self.waiting_passengers[self.floors[i]]["up"]
                                for i in range(0, curr_idx))
            if targets or waiting_above or elevator.target_floors:
                elevator.direction = "up"
            else:
                elevator.direction = "idle"
        elif elevator.direction == "down":
            targets = [self.floors.index(p.target_floor) for p in elevator.passengers if self.floors.index(p.target_floor) > curr_idx]
            waiting_below = any(self.waiting_passengers[self.floors[i]]["down"]
                                for i in range(curr_idx + 1, len(self.floors)))
            if targets or waiting_below or elevator.target_floors:
                elevator.direction = "down"
            else:
                elevator.direction = "idle"

    def update_stats(self):
        self.stats_text.config(state=tk.NORMAL)
        self.stats_text.delete(1.0, tk.END)
        total_passengers = self.passenger_stats["total"]
        boarded_passengers = self.passenger_stats["boarded"]
        avg_wait_time = sum(self.passenger_stats["wait_times"]) / len(self.passenger_stats["wait_times"]) if self.passenger_stats["wait_times"] else 0
        self.stats_text.insert(tk.END, f"总乘客数: {total_passengers}\n")
        self.stats_text.insert(tk.END, f"已运送乘客: {boarded_passengers}\n")
        self.stats_text.insert(tk.END, f"等待中乘客: {total_passengers - boarded_passengers}\n")
        self.stats_text.insert(tk.END, f"平均等待时间: {avg_wait_time:.1f} 时间单位\n\n")
        for i, elevator in enumerate(self.elevators):
            run_status = "空闲" if elevator.direction == "idle" else "运行"
            door_status = "开门" if elevator.door_open else "关门"
            self.stats_text.insert(
                tk.END, 
                f"电梯 {i+1}: {elevator.current_floor} 层, {run_status}, {len(elevator.passengers)}/{elevator.max_capacity} 人, {door_status}\n"
            )
        self.stats_text.config(state=tk.DISABLED)
        self.update_chart()

    def update_chart(self):
        self.ax.clear()
        floor_waiting_counts = {floor: len(self.waiting_passengers[floor]["up"]) + len(self.waiting_passengers[floor]["down"]) for floor in self.floors}
        sorted_floors = sorted(self.floors, key=lambda x: (x[0] == 'B', int(x[1:]) if x[0] == 'B' else -int(x[1:]) if x != '0' else 0))
        floors_labels = sorted_floors
        counts = [floor_waiting_counts[floor] for floor in sorted_floors]
        self.ax.bar(floors_labels, counts, color='#3b82f6')
        self.ax.set_xlabel('楼层')
        self.ax.set_ylabel('等待人数')
        self.ax.set_title('各楼层等待人数')
        self.ax.tick_params(axis='x', rotation=45)
        self.fig.tight_layout()
        self.canvas_chart.draw()

    def update_canvas(self):
        self.canvas.delete("all")
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        floor_height = min(40, canvas_height / (len(self.floors) + 2))
        elevator_width = min(60, canvas_width / (len(self.elevators) + 2))
        for i, floor in enumerate(self.floors):
            y_top = 40 + i * floor_height
            y_center = y_top + floor_height / 2
            self.canvas.create_line(0, y_center, canvas_width, y_center, fill=self.colors["grid_line"])
            self.canvas.create_text(20, y_center, text=floor, fill=self.colors["fg_text"], font=("Arial", 10, "bold"))
            up_passengers = self.waiting_passengers[floor]["up"]
            down_passengers = self.waiting_passengers[floor]["down"]
            if up_passengers:
                self.canvas.create_text(40, y_center, text=str(len(up_passengers)), fill=self.colors["passenger_wait"], font=("Arial", 10, "bold"))
                self.canvas.create_text(50, y_center, text="↑", fill=self.colors["elevator_up"], font=("Arial", 10, "bold"))
            if down_passengers:
                self.canvas.create_text(70, y_center, text=str(len(down_passengers)), fill=self.colors["passenger_wait"], font=("Arial", 10, "bold"))
                self.canvas.create_text(80, y_center, text="↓", fill=self.colors["elevator_down"], font=("Arial", 10, "bold"))
        for i, elevator in enumerate(self.elevators):
            x = 100 + i * (elevator_width + 20)
            self.canvas.create_rectangle(x, 40, x + elevator_width, 40 + len(self.floors) * floor_height,
                                        fill=self.colors["bg_main"], outline=self.colors["grid_line"])
            floor_index = self.floors.index(elevator.current_floor)
            y_top = 40 + floor_index * floor_height
            y_center = y_top + floor_height / 2
            elevator_color = self.colors["elevator_idle"]
            if elevator.direction == "up":
                elevator_color = self.colors["elevator_up"]
            elif elevator.direction == "down":
                elevator_color = self.colors["elevator_down"]
            self.canvas.create_rectangle(
                x, y_center - floor_height/2, x + elevator_width, y_center + floor_height/2,
                fill=elevator_color, outline=self.colors["shadow"], width=2
            )
            door_width = elevator_width / 2
            if elevator.door_open:
                self.canvas.create_rectangle(x, y_center - floor_height/2, x + door_width - 5, y_center + floor_height/2,
                                            fill=self.colors["bg_main"], outline=self.colors["shadow"])
                self.canvas.create_rectangle(x + door_width + 5, y_center - floor_height/2, x + elevator_width, y_center + floor_height/2,
                                            fill=self.colors["bg_main"], outline=self.colors["shadow"])
            else:
                self.canvas.create_line(x + door_width, y_center - floor_height/2, x + door_width, y_center + floor_height/2,
                                       fill=self.colors["shadow"], width=2)
            self.canvas.create_text(x + elevator_width/2, y_center, text=str(len(elevator.passengers)),
                                   fill=self.colors["fg_text"], font=("Arial", 12, "bold"))
            status_text = f"电梯 {elevator.eid+1}"
            direction_symbol = elevator.get_direction_symbol()
            status_text += f" {direction_symbol}"
            self.canvas.create_text(x + elevator_width/2, y_center - floor_height/2 - 10,
                                   text=status_text, fill=self.colors["fg_text"], font=("Arial", 9, "bold"))
            self.canvas.create_text(x + elevator_width/2, y_center + floor_height/2 + 10,
                                   text=elevator.current_floor, fill=self.colors["fg_text"], font=("Arial", 9, "bold"))

    def update_simulation(self):
        if not self.running:
            return
        if self.use_real_time:
            current_time = self.get_current_hour_minute()
            if current_time != self.last_real_time_update:
                self.time = current_time
                self.last_real_time_update = current_time
            self.status_label.config(text="运行中（真实时间）")
        else:
            self.time = (self.time + 1) % 1440
            self.status_label.config(text="运行中（仿真时间）")
        self.update_time_display()
        self.generate_passengers()
        self.assign_elevators()
        self.move_elevators()
        self.update_canvas()
        self.update_stats()
        self.timer = self.master.after(500, self.update_simulation)

    def update_time_display(self):
        if self.use_real_time:
            current_time = time.localtime()
            hours = current_time.tm_hour
            minutes = current_time.tm_min
            seconds = current_time.tm_sec
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d} (电脑真实时间)"
        else:
            hours = self.time // 60
            minutes = self.time % 60
            time_str = f"{hours:02d}:{minutes:02d} (仿真时间)"
        if self.is_peak_time():
            time_str += " (高峰时段)"
        self.time_label.config(text=time_str)

    def on_window_resize(self, event):
        if self.running:
            self.update_canvas()

    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        if self.dark_mode:
            self.colors = {
                "bg_main": "#1e293b",
                "bg_panel": "#0f172a",
                "bg_button": "#1e40af",
                "bg_button_hover": "#3b82f6",
                "fg_text": "#e2e8f0",
                "fg_highlight": "#93c5fd",
                "elevator_idle": "#334155",
                "elevator_up": "#3b82f6",
                "elevator_down": "#2563eb",
                "passenger_wait": "#f87171",
                "peak_period": "#f59e0b",
                "grid_line": "#334155",
                "shadow": "#020617",
                "dark_bg": "#1e293b",
                "dark_fg": "#e2e8f0"
            }
            self.dark_mode_btn.config(text="☀️")
        else:
            self.colors = {
                "bg_main": "#f0f7ff",
                "bg_panel": "#ffffff",
                "bg_button": "#e3f2fd",
                "bg_button_hover": "#bbdefb",
                "fg_text": "#334155",
                "fg_highlight": "#1e40af",
                "elevator_idle": "#bfdbfe",
                "elevator_up": "#3b82f6",
                "elevator_down": "#2563eb",
                "passenger_wait": "#f87171",
                "peak_period": "#f59e0b",
                "grid_line": "#e2e8f0",
                "shadow": "#ddd",
                "dark_bg": "#1e293b",
                "dark_fg": "#e2e8f0"
            }
            self.dark_mode_btn.config(text="🌙")
        self.master.configure(bg=self.colors["bg_main"])
        self.top_frame.configure(bg=self.colors["bg_panel"])
        self.param_frame.configure(bg=self.colors["bg_panel"])
        self.peak_frame.configure(bg=self.colors["bg_panel"])
        self.btn_frame.configure(bg=self.colors["bg_panel"])
        self.status_label.configure(bg=self.colors["bg_panel"], fg=self.colors["fg_text"])
        self.main_frame.configure(bg=self.colors["bg_main"])
        self.sim_frame.configure(bg=self.colors["bg_panel"])
        self.canvas.configure(bg=self.colors["bg_main"])
        self.time_label.configure(bg=self.colors["bg_panel"], fg=self.colors["fg_text"])
        self.stats_frame.configure(bg=self.colors["bg_panel"])
        self.stats_text.configure(bg=self.colors["bg_main"], fg=self.colors["fg_text"])
        self.chart_frame.configure(bg=self.colors["bg_panel"])
        for widget in self.btn_frame.winfo_children():
            if isinstance(widget, tk.Button):
                widget.configure(bg=self.colors["bg_button"],
                                fg=self.colors["fg_text"],
                                activebackground=self.colors["bg_button_hover"],
                                activeforeground=self.colors["fg_highlight"])
        self.stats_text.configure(bg=self.colors["bg_main"], fg=self.colors["fg_text"])
        if self.running:
            self.update_canvas()

    def emergency_reset(self):
        for elevator in self.elevators:
            elevator.resetting = True
            elevator.door_open = False
            elevator.door_timer = 0
            if self.floors.index(elevator.current_floor) > self.floors.index("0"):
                elevator.direction = "down"
            elif self.floors.index(elevator.current_floor) < self.floors.index("0"):
                elevator.direction = "up"
            else:
                elevator.direction = "idle"

if __name__ == "__main__":
    root = tk.Tk()
    app = ElevatorSystemGUI(root)
    root.mainloop()