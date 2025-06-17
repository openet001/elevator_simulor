import random
import tkinter as tk
from tkinter import messagebox
from collections import deque
from typing import List, Dict

class Passenger:
    def __init__(self, current_floor: str, target_floor: str, direction: str):
        self.current_floor = current_floor
        self.target_floor = target_floor
        self.direction = direction
        self.waiting_time = 0

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

class ElevatorSystemGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("电梯仿真系统")
        self.running = False
        self.timer = None

        # ========== 控制面板 ==========
        self.ctrl_frame = tk.Frame(master, relief=tk.RIDGE, bd=2)
        self.ctrl_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        tk.Label(self.ctrl_frame, text="电梯数量(1-6):").grid(row=0, column=0, sticky='e')
        self.n_elevators_var = tk.IntVar(value=3)
        tk.Spinbox(self.ctrl_frame, from_=1, to=6, textvariable=self.n_elevators_var, width=5).grid(row=0, column=1)

        tk.Label(self.ctrl_frame, text="地上楼层数(≥1):").grid(row=1, column=0, sticky='e')
        self.floors_up_var = tk.IntVar(value=10)
        tk.Entry(self.ctrl_frame, textvariable=self.floors_up_var, width=5).grid(row=1, column=1)

        tk.Label(self.ctrl_frame, text="地下楼层数(≥0):").grid(row=2, column=0, sticky='e')
        self.floors_down_var = tk.IntVar(value=5)
        tk.Entry(self.ctrl_frame, textvariable=self.floors_down_var, width=5).grid(row=2, column=1)

        tk.Label(self.ctrl_frame, text="电梯容量:").grid(row=3, column=0, sticky='e')
        self.capacity_var = tk.IntVar(value=13)
        tk.Entry(self.ctrl_frame, textvariable=self.capacity_var, width=5).grid(row=3, column=1)

        tk.Label(self.ctrl_frame, text="早高峰(hh:mm-hh:mm):").grid(row=4, column=0, sticky='e')
        self.peak_morning_var = tk.StringVar(value="07:00-09:00")
        tk.Entry(self.ctrl_frame, textvariable=self.peak_morning_var, width=10).grid(row=4, column=1)

        tk.Label(self.ctrl_frame, text="晚高峰(hh:mm-hh:mm):").grid(row=5, column=0, sticky='e')
        self.peak_evening_var = tk.StringVar(value="18:00-21:00")
        tk.Entry(self.ctrl_frame, textvariable=self.peak_evening_var, width=10).grid(row=5, column=1)

        self.elevator_floors_btn = tk.Button(self.ctrl_frame, text="设置电梯停靠楼层", command=self.set_elevator_floors_dialog)
        self.elevator_floors_btn.grid(row=6, column=0, columnspan=2, pady=2)

        self.start_btn = tk.Button(self.ctrl_frame, text="开始仿真", command=self.start_simulation)
        self.start_btn.grid(row=7, column=0, columnspan=2, pady=6)

        self.stop_btn = tk.Button(self.ctrl_frame, text="停止仿真", command=self.stop_simulation, state=tk.DISABLED)
        self.stop_btn.grid(row=8, column=0, columnspan=2)

        self.status_label = tk.Label(self.ctrl_frame, text="", fg="blue")
        self.status_label.grid(row=9, column=0, columnspan=2, pady=6)

        # ========== 图形区域 ==========
        self.sim_frame = tk.Frame(master)
        self.sim_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas = None
        self.time_label = None

        # 变量
        self.elevator_floors = None
        self.floors = []
        self.elevators = []
        self.waiting_passengers: Dict[str, deque] = {}
        self.time = 0
        self.peak_periods = {}
        self.passenger_history = []

    def set_elevator_floors_dialog(self):
        n_elev = self.n_elevators_var.get()
        n_up = self.floors_up_var.get()
        n_down = self.floors_down_var.get()
        if n_up < 1 or n_down < 0:
            messagebox.showerror("错误", "楼层数非法")
            return
        all_floors = [f"F{i}" for i in range(n_up, 0, -1)] + ["0"] + [f"B{i}" for i in range(1, n_down+1)]
        top = tk.Toplevel(self.master)
        top.title("为每部电梯选择可停靠楼层")
        vars_ = []
        for i in range(n_elev):
            tk.Label(top, text=f"电梯{i+1}").grid(row=0, column=i+1)
        for j, floor in enumerate(all_floors):
            tk.Label(top, text=floor).grid(row=j+1, column=0)
            row_vars = []
            for i in range(n_elev):
                v = tk.IntVar(value=1)
                c = tk.Checkbutton(top, variable=v)
                c.grid(row=j+1, column=i+1)
                row_vars.append(v)
            vars_.append(row_vars)
        def save():
            self.elevator_floors = []
            for i in range(n_elev):
                floors = [all_floors[j] for j in range(len(all_floors)) if vars_[j][i].get()]
                if not floors:
                    messagebox.showerror("错误", f"电梯{i+1}未设置任何楼层")
                    return
                self.elevator_floors.append(floors)
            top.destroy()
        tk.Button(top, text="保存", command=save).grid(row=len(all_floors)+1, column=0, columnspan=n_elev+1)

    def parse_peak_period(self, s):
        start, end = s.split("-")
        h1, m1 = map(int, start.split(":"))
        h2, m2 = map(int, end.split(":"))
        return (h1 * 60+m1, h2 * 60+m2)

    def setup_simulation(self):
        n_elev = self.n_elevators_var.get()
        n_up = self.floors_up_var.get()
        n_down = self.floors_down_var.get()
        capacity = self.capacity_var.get()
        if n_up < 1 or n_down < 0 or n_elev < 1 or n_elev > 6 or capacity < 1:
            messagebox.showerror("错误", "参数非法")
            return False
        # 修改地下楼层生成顺序，从B1到Bn
        all_floors = [f"F{i}" for i in range(n_up, 0, -1)] + ["0"] + [f"B{i}" for i in range(1, n_down+1)]
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
        # 图形区域
        if self.canvas:
            self.canvas.destroy()
        if self.time_label:
            self.time_label.destroy()
        self.canvas = tk.Canvas(self.sim_frame, width=80 + n_elev*80, height=40*len(self.floors)+40, bg="white")
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.time_label = tk.Label(self.sim_frame, text="")
        self.time_label.pack()
        return True

    def start_simulation(self):
        if not self.setup_simulation():
            return
        self.running = True
        self.elevator_floors_btn.config(state=tk.DISABLED)
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_label.config(text="仿真运行中...")
        self.update_simulation()

    def stop_simulation(self):
        self.running = False
        self.elevator_floors_btn.config(state=tk.NORMAL)
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_label.config(text="仿真已停止")
        if self.timer:
            self.master.after_cancel(self.timer)
            self.timer = None

    def is_peak(self):
        for (start, end) in self.peak_periods.values():
            if start <= self.time % 1440 < end:
                return True
        return False

    def generate_passengers(self):
        base_rate = 0.01 if not self.is_peak() else 0.06
        for floor in self.floors:
            if random.random() < base_rate:
                possible_targets = [f for f in self.floors if f != floor]
                t = self.time % 1440
                peak = False
                if t in range(*self.peak_periods.get("morning", (0, 0))):
                    if floor in self.floors[-(len(self.floors)-self.floors.index("0")-1):]:  # 地下楼层
                        target = random.choice(self.floors[:self.floors.index("0")])  # 地上楼层
                        direction = "up"
                        peak = True
                elif t in range(*self.peak_periods.get("evening", (0, 0))):
                    if floor in self.floors[:self.floors.index("0")]:  # 地上楼层
                        target = random.choice(self.floors[-(len(self.floors)-self.floors.index("0")-1):])  # 地下楼层
                        direction = "down"
                        peak = True
                if not peak:
                    target = random.choice(possible_targets)
                    direction = "up" if self.floors.index(target) < self.floors.index(floor) else "down"
                p = Passenger(floor, target, direction)
                self.waiting_passengers[floor].append(p)
                self.passenger_history.append(p)

    def step_elevators(self):
        # 全局调度，避免某楼层呼叫长时间被忽略
        floor_waits = {f: (sum(p.waiting_time for p in self.waiting_passengers[f]), len(self.waiting_passengers[f]))
                       for f in self.floors}
        elevator_targets = set()
        for elevator in self.elevators:
            # 下客
            departing = [p for p in elevator.passengers if p.target_floor == elevator.current_floor]
            for p in departing:
                elevator.passengers.remove(p)
            # 上客
            floor_queue = self.waiting_passengers[elevator.current_floor]
            to_board = []
            for p in list(floor_queue):
                if (p.direction == elevator.direction or elevator.direction == "idle") and p.target_floor in elevator.allowed_floors:
                    to_board.append(p)
            available_slots = elevator.max_capacity - len(elevator.passengers)
            for p in to_board[:available_slots]:
                elevator.passengers.append(p)
                floor_queue.remove(p)
                if p.target_floor not in elevator.target_floors:
                    elevator.target_floors.append(p.target_floor)
            # 调度目标
            next_dest = None
            if elevator.passengers:
                # 车内目标
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
            # 移动
            if elevator.direction == "up":
                curr_idx = self.floors.index(elevator.current_floor)
                if curr_idx > 0 and self.floors[curr_idx-1] in elevator.allowed_floors:
                    elevator.current_floor = self.floors[curr_idx-1]
            elif elevator.direction == "down":
                curr_idx = self.floors.index(elevator.current_floor)
                if curr_idx < len(self.floors)-1 and self.floors[curr_idx+1] in elevator.allowed_floors:
                    elevator.current_floor = self.floors[curr_idx+1]

    def draw_static(self):
        self.canvas.delete("all")
        for i, floor in enumerate(self.floors):
            y = 40 + i*40
            self.canvas.create_line(60, y, 60 + len(self.elevators)*80, y, fill="#ccc")
            self.canvas.create_text(40, y, text=floor, font=("Arial", 12))
        for eid in range(len(self.elevators)):
            x = 60 + eid*80
            self.canvas.create_rectangle(x, 40, x+60, 40+len(self.floors)*40, outline="#888")

    def draw_elevators(self):
        for eid, elevator in enumerate(self.elevators):
            try:
                y = 40 + self.floors.index(elevator.current_floor)*40
            except ValueError:
                continue
            x = 60 + eid*80
            self.canvas.create_rectangle(x+5, y-30, x+55, y+10, fill="skyblue", outline="black", width=2)
            self.canvas.create_text(x+30, y-10, text=f"电梯{elevator.eid}\n{len(elevator.passengers)}人", font=("Arial", 8))
        for i, floor in enumerate(self.floors):
            q = self.waiting_passengers[floor]
            y = 40 + i*40
            n = len(q)
            if n > 0:
                self.canvas.create_text(20, y, text=f"{n}人", fill="red")

    def draw_time(self):
        hour = (self.time // 60) % 24
        minute = self.time % 60
        self.time_label.config(text=f"时间：{hour:02d}:{minute:02d}   高峰{'是' if self.is_peak() else '否'}")

    def update_simulation(self):
        if not self.running:
            return
        self.generate_passengers()
        self.step_elevators()
        self.draw_static()
        self.draw_elevators()
        self.draw_time()
        for f in self.floors:
            for p in self.waiting_passengers[f]:
                p.waiting_time += 1
        self.time += 1
        self.timer = self.master.after(200, self.update_simulation)

if __name__ == "__main__":
    root = tk.Tk()
    app = ElevatorSystemGUI(root)
    root.mainloop()