import sys
import random
import time
from collections import defaultdict
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QSpinBox, QPushButton, QGroupBox, QCheckBox, QGridLayout)
from PyQt5.QtCore import Qt, QTimer, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen, QFont


class Elevator:
    def __init__(self, id, max_capacity, default_floor, floors):
        self.id = id
        self.max_capacity = max_capacity
        self.current_floor = default_floor
        self.destination_floors = []
        self.direction = 0  # 0: idle, 1: up, -1: down
        self.passengers = []
        self.door_open = False
        self.default_floor = default_floor
        self.last_activity_time = time.time()
        self.allowed_floors = floors
        self.status = "空闲"
        self.position = 0  # 用于动画的当前位置
        self.target_position = 0  # 目标位置
        self.initial_delay = 3  # 初始延迟3秒
        
    def add_destination(self, floor):
        if floor not in self.destination_floors and floor in self.allowed_floors:
            self.destination_floors.append(floor)
            self.update_direction()
            
    def update_direction(self):
        if not self.destination_floors:
            self.direction = 0
            return
            
        # 按楼层排序目标楼层，处理多个目标
        self.destination_floors.sort()
        
        if self.current_floor < self.destination_floors[0]:
            self.direction = 1
        elif self.current_floor > self.destination_floors[-1]:
            self.direction = -1
        else:
            self.direction = 0
            
    def move(self):
        # 处理初始延迟
        if self.initial_delay > 0:
            self.status = f"初始化延迟:{self.initial_delay}秒"
            self.initial_delay -= 1
            return
            
        if not self.door_open:
            # 没有目标时返回默认楼层
            if not self.destination_floors and not self.passengers:
                idle_time = time.time() - self.last_activity_time
                if idle_time > 3:  # 3秒空闲
                    if self.current_floor != self.default_floor:
                        self.add_destination(self.default_floor)
                return
                
            # 根据方向移动
            if self.direction == 1 and self.current_floor < self.destination_floors[-1]:
                self.current_floor += 1
                self.status = f"上行至{self.current_floor}F"
            elif self.direction == -1 and self.current_floor > self.destination_floors[0]:
                self.current_floor -= 1
                self.status = f"下行至{self.current_floor}F"
            else:
                # 到达目标区域，准备开门
                self.open_door()
                self.destination_floors = [f for f in self.destination_floors if f != self.current_floor]
                self.update_direction()
                
    def open_door(self):
        self.door_open = True
        self.status = f"开门@{self.current_floor}F"
        self.last_activity_time = time.time()
        
    def close_door(self):
        self.door_open = False
        self.status = "空闲" if not self.destination_floors else self.status
        
    def board_passenger(self, passenger, floor_passengers):
        if len(self.passengers) < self.max_capacity:
            self.passengers.append(passenger)
            self.add_destination(passenger.destination)
            self.last_activity_time = time.time()
            # 从等待列表中移除乘客
            if passenger in floor_passengers:
                floor_passengers.remove(passenger)
            return True
        return False
    
    def unboard_passengers(self):
        unboarded = [p for p in self.passengers if p.destination == self.current_floor]
        self.passengers = [p for p in self.passengers if p.destination != self.current_floor]
        return unboarded


class Passenger:
    def __init__(self, current_floor, destination):
        self.current_floor = current_floor
        self.destination = destination
        self.waiting_time = 0
        self.in_elevator = False
        self.direction = 1 if destination > current_floor else -1  # 1: up, -1: down


class SimulationDisplay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.simulator = parent
        self.setStyleSheet("background-color: white;")
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw building
        self.draw_building(painter)
        
        # Draw elevators
        self.draw_elevators(painter)
        
        # Draw waiting passengers
        self.draw_waiting_passengers(painter)
        
        painter.end()
        
    def draw_building(self, painter):
        # Building dimensions
        building_width = 980  # 加宽建筑
        building_height = 720  # 加高建筑
        building_x = 50
        building_y = 50
        
        # Draw building outline
        painter.setPen(QPen(Qt.black, 2))
        painter.drawRect(building_x, building_y, building_width, building_height)
        
        # Draw floors
        floor_height = building_height / (self.simulator.total_floors + self.simulator.basement_floors + 2)
        
        for i, floor in enumerate(range(-self.simulator.basement_floors, self.simulator.total_floors + 1)):
            if floor == 0:
                continue
                
            y = building_y + building_height - (i + 1) * floor_height
            
            # Draw floor line
            painter.setPen(QPen(Qt.gray, 1))
            painter.drawLine(building_x, y, building_x + building_width, y)
            
            # Draw floor label
            painter.setPen(Qt.black)
            painter.drawText(building_x + 10, y + 20, f"{floor}F")
            
            # Draw elevator buttons
            button_size = 20
            button_x = building_x + building_width - 100
            
            # Up button
            up_button_rect = QRectF(button_x, y + 10, button_size, button_size)
            painter.setPen(QPen(Qt.black, 1))
            
            # Check if there are passengers waiting to go up
            has_up_passengers = any(
                p.direction == 1 for p in self.simulator.waiting_passengers.get(floor, [])
            )
            
            painter.setBrush(Qt.red if has_up_passengers else Qt.white)
            painter.drawEllipse(up_button_rect)
            painter.drawText(up_button_rect, Qt.AlignCenter, "↑")
            
            # Down button
            down_button_rect = QRectF(button_x + button_size + 10, y + 10, button_size, button_size)
            
            # Check if there are passengers waiting to go down
            has_down_passengers = any(
                p.direction == -1 for p in self.simulator.waiting_passengers.get(floor, [])
            )
            
            painter.setBrush(Qt.red if has_down_passengers else Qt.white)
            painter.drawEllipse(down_button_rect)
            painter.drawText(down_button_rect, Qt.AlignCenter, "↓")
        
    def draw_elevators(self, painter):
        if not self.simulator.elevators:
            return
            
        building_width = 980
        building_height = 720
        building_x = 50
        building_y = 50
        floor_height = building_height / (self.simulator.total_floors + self.simulator.basement_floors + 2)
        
        # Calculate elevator dimensions and positions
        elevator_width = 60
        elevator_spacing = (building_width - 150) / len(self.simulator.elevators)
        
        for i, elevator in enumerate(self.simulator.elevators):
            # Calculate elevator position with animation
            floor_index = (self.simulator.basement_floors + elevator.current_floor) if elevator.current_floor > 0 else (self.simulator.basement_floors + abs(elevator.current_floor))
            target_y = building_y + building_height - (floor_index + 1) * floor_height + 10
            
            # Update elevator's target position
            elevator.target_position = target_y
            
            # Animate movement (1 pixel per frame)
            if abs(elevator.position - target_y) > 1:
                if elevator.position < target_y:
                    elevator.position += 1
                else:
                    elevator.position -= 1
            
            elevator_x = building_x + 100 + i * elevator_spacing
            elevator_y = elevator.position
            
            # Draw elevator
            painter.setPen(QPen(Qt.black, 2))
            painter.setBrush(Qt.lightGray)
            painter.drawRect(elevator_x, elevator_y, elevator_width, floor_height - 20)
            
            # Draw door
            door_width = 20
            if elevator.door_open:
                # Open door
                painter.setBrush(Qt.white)
                painter.drawRect(elevator_x, elevator_y, door_width/2, floor_height - 20)
                painter.drawRect(elevator_x + elevator_width - door_width/2, elevator_y, door_width/2, floor_height - 20)
            else:
                # Closed door
                painter.setBrush(Qt.darkGray)
                painter.drawRect(elevator_x, elevator_y, door_width, floor_height - 20)
                painter.drawRect(elevator_x + elevator_width - door_width, elevator_y, door_width, floor_height - 20)
            
            # Draw elevator info
            painter.setPen(Qt.black)
            font = QFont()
            font.setPointSize(8)
            painter.setFont(font)
            
            # Elevator ID
            painter.drawText(elevator_x + 5, elevator_y + 15, f"电梯{elevator.id}")
            
            # Passenger count
            painter.drawText(elevator_x + 5, elevator_y + 30, f"{len(elevator.passengers)}/{elevator.max_capacity}")
            
            # Direction indicator
            if elevator.direction == 1:
                painter.drawText(elevator_x + elevator_width - 15, elevator_y + 15, "↑")
            elif elevator.direction == -1:
                painter.drawText(elevator_x + elevator_width - 15, elevator_y + 15, "↓")
            
            # Draw passengers in elevator (as simple circles)
            for j in range(len(elevator.passengers)):
                px = elevator_x + 15 + (j % 3) * 10
                py = elevator_y + 40 + (j // 3) * 15
                painter.setBrush(Qt.blue)
                painter.drawEllipse(px, py, 8, 8)
        
    def draw_waiting_passengers(self, painter):
        building_width = 980
        building_height = 720
        building_x = 50
        building_y = 50
        floor_height = building_height / (self.simulator.total_floors + self.simulator.basement_floors + 2)
        
        for floor, passengers in self.simulator.waiting_passengers.items():
            floor_index = (self.simulator.basement_floors + floor) if floor > 0 else (self.simulator.basement_floors + abs(floor))
            floor_y = building_y + building_height - (floor_index + 1) * floor_height + 10
            
            # Draw waiting passengers (as simple circles)
            for i, passenger in enumerate(passengers[:10]):  # Limit to 10 visible per floor
                px = building_x + 30 + (i % 5) * 15
                py = floor_y + (i // 5) * 15
                # 根据乘客方向使用不同颜色
                painter.setBrush(Qt.green if passenger.direction == 1 else Qt.yellow)
                painter.drawEllipse(px, py, 8, 8)


class ElevatorSimulator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("楼宇电梯运行模拟系统")
        self.setGeometry(50, 50, 1540, 820)  # 加宽加长窗口
        
        # Simulation parameters
        self.elevators = []
        self.total_floors = 20
        self.basement_floors = 0
        self.passengers = []
        self.waiting_passengers = defaultdict(list)
        self.simulation_time = 0
        self.time_multiplier = 60  # 1 real second = 1 simulation minute
        self.is_running = False
        self.initial_delay = 3  # 初始延迟3秒
        self.initial_passengers_generated = False
        self.peak_hours = {
            "morning": (8, 9),    # 8-9 AM
            "evening": (18, 21)   # 6-9 PM
        }
        self.last_passenger_generation = 0
        
        # UI Setup
        self.init_ui()
        
        # Timers
        self.simulation_timer = QTimer(self)
        self.simulation_timer.timeout.connect(self.update_simulation)
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.update_animation)
        
        # Start animation timer (60 FPS)
        self.animation_timer.start(16)
        
    def init_ui(self):
        # Main layout
        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Control panel (加宽控制面板)
        control_panel = QGroupBox("电梯配置")
        control_layout = QVBoxLayout()
        control_panel.setLayout(control_layout)
        control_panel.setFixedWidth(450)  # 加宽控制面板
        
        # Elevator count
        elevator_count_layout = QHBoxLayout()
        elevator_count_layout.addWidget(QLabel("电梯数量 (1-6):"))
        self.elevator_count = QSpinBox()
        self.elevator_count.setRange(1, 6)
        self.elevator_count.setValue(3)
        elevator_count_layout.addWidget(self.elevator_count)
        control_layout.addLayout(elevator_count_layout)
        
        # Total floors
        total_floors_layout = QHBoxLayout()
        total_floors_layout.addWidget(QLabel("地上楼层 (1-20):"))
        self.total_floors_input = QSpinBox()
        self.total_floors_input.setRange(1, 20)
        self.total_floors_input.setValue(20)
        total_floors_layout.addWidget(self.total_floors_input)
        control_layout.addLayout(total_floors_layout)
        
        # Basement floors
        basement_floors_layout = QHBoxLayout()
        basement_floors_layout.addWidget(QLabel("地下楼层 (0-2):"))
        self.basement_floors_input = QSpinBox()
        self.basement_floors_input.setRange(0, 2)
        self.basement_floors_input.setValue(1)
        basement_floors_layout.addWidget(self.basement_floors_input)
        control_layout.addLayout(basement_floors_layout)
        
        # Default floor
        default_floor_layout = QHBoxLayout()
        default_floor_layout.addWidget(QLabel("默认停靠楼层:"))
        self.default_floor_input = QSpinBox()
        self.default_floor_input.setRange(-2, 20)
        self.default_floor_input.setValue(1)
        default_floor_layout.addWidget(self.default_floor_input)
        control_layout.addLayout(default_floor_layout)
        
        # Elevator settings group
        self.elevator_settings_group = QGroupBox("电梯详细设置")
        self.elevator_settings_layout = QVBoxLayout()
        self.elevator_settings_group.setLayout(self.elevator_settings_layout)
        control_layout.addWidget(self.elevator_settings_group)
        
        # Create elevator settings based on count
        self.create_elevator_settings()
        self.elevator_count.valueChanged.connect(self.create_elevator_settings)
        
        # Simulation controls
        start_button = QPushButton("开始模拟")
        start_button.clicked.connect(self.start_simulation)
        control_layout.addWidget(start_button)
        
        stop_button = QPushButton("停止模拟")
        stop_button.clicked.connect(self.stop_simulation)
        control_layout.addWidget(stop_button)
        
        # Stats display
        self.stats_label = QLabel("模拟统计信息将显示在这里")
        self.stats_label.setWordWrap(True)
        control_layout.addWidget(self.stats_label)
        
        # Simulation display
        self.simulation_display = SimulationDisplay(self)
        
        # Add to main layout
        main_layout.addWidget(control_panel)
        main_layout.addWidget(self.simulation_display)
        
    def create_elevator_settings(self):
        # Clear existing settings
        while self.elevator_settings_layout.count():
            child = self.elevator_settings_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        # Create settings for each elevator
        for i in range(self.elevator_count.value()):
            group = QGroupBox(f"电梯 {i+1}")
            layout = QVBoxLayout()
            
            # Capacity
            cap_layout = QHBoxLayout()
            cap_layout.addWidget(QLabel("限乘人数:"))
            capacity = QSpinBox()
            capacity.setRange(1, 20)
            capacity.setValue(10)
            capacity.setObjectName(f"capacity_{i}")
            cap_layout.addWidget(capacity)
            layout.addLayout(cap_layout)
            
            # Allowed floors
            layout.addWidget(QLabel("可停靠楼层:"))
            
            # Create grid layout for floor checkboxes (11 columns)
            floor_grid = QGridLayout()
            
            min_floor = -self.basement_floors_input.value()
            max_floor = self.total_floors_input.value()
            floors = [f for f in range(min_floor, max_floor + 1) if f != 0]
            
            row, col = 0, 0
            for floor in floors:
                cb = QCheckBox(f"{floor}F")
                cb.setChecked(True)
                cb.setObjectName(f"elevator_{i}_floor_{floor}")
                floor_grid.addWidget(cb, row, col)
                col += 1
                if col >= 11:  # 每行11个复选框
                    col = 0
                    row += 1
            
            layout.addLayout(floor_grid)
            group.setLayout(layout)
            self.elevator_settings_layout.addWidget(group)
        
    def start_simulation(self):
        if self.is_running:
            return
            
        # Get simulation parameters
        self.total_floors = self.total_floors_input.value()
        self.basement_floors = self.basement_floors_input.value()
        default_floor = self.default_floor_input.value()
        
        # Initialize elevators
        self.elevators = []
        for i in range(self.elevator_count.value()):
            # Get capacity
            capacity = self.findChild(QSpinBox, f"capacity_{i}").value()
            
            # Get allowed floors
            allowed_floors = []
            min_floor = -self.basement_floors
            max_floor = self.total_floors
            for floor in range(min_floor, max_floor + 1):
                if floor == 0:
                    continue
                cb = self.findChild(QCheckBox, f"elevator_{i}_floor_{floor}")
                if cb and cb.isChecked():
                    allowed_floors.append(floor)
            
            # Create elevator (默认在1楼)
            elevator = Elevator(i+1, capacity, 1, allowed_floors)
            elevator.current_floor = 1  # 确保初始在1楼
            elevator.initial_delay = 3  # 设置初始延迟3秒
            self.elevators.append(elevator)
        
        # Reset simulation state
        self.passengers = []
        self.waiting_passengers = defaultdict(list)
        self.simulation_time = 0
        self.is_running = True
        self.initial_passengers_generated = False
        self.last_passenger_generation = 0
        
        # Start simulation timer (updates every second)
        self.simulation_timer.start(1000)
        
    def generate_initial_passengers(self):
        # 生成1-5名初始乘客
        passenger_count = random.randint(1, 5)
        
        # 楼层权重分配 (1楼70%，-1和-2各10%，其他楼层共10%)
        floor_weights = []
        all_floors = [f for f in range(-self.basement_floors, self.total_floors + 1) if f != 0]
        
        for floor in all_floors:
            if floor == 1:
                floor_weights.append(70)
            elif floor in (-1, -2):
                floor_weights.append(10)
            else:
                floor_weights.append(1)  # 其他楼层共享10%的权重
        
        # 生成起始楼层
        start_floors = random.choices(
            all_floors,
            weights=floor_weights,
            k=passenger_count
        )
        
        # 生成目标楼层 (不能与起始楼层相同)
        end_floors = []
        for start in start_floors:
            possible_floors = [f for f in all_floors if f != start]
            end_floors.append(random.choice(possible_floors))
        
        # 创建乘客 (检查楼层人数不超过5人)
        for start, end in zip(start_floors, end_floors):
            if len(self.waiting_passengers.get(start, [])) < 5:  # 楼层人数不超过5人
                passenger = Passenger(start, end)
                self.waiting_passengers[start].append(passenger)
                self.passengers.append(passenger)
        
        self.initial_passengers_generated = True
        
    def generate_passengers(self):
        # 检查是否在高峰期
        current_hour = (self.simulation_time // self.time_multiplier) % 24
        is_peak = (8 <= current_hour < 9) or (18 <= current_hour < 21)
        
        # 高峰期每1分钟生成1-5人，非高峰期每2分钟生成1-3人
        generation_interval = 1 if is_peak else 2
        max_passengers = 15 if is_peak else 5
        
        current_minute = self.simulation_time // self.time_multiplier
        if current_minute - self.last_passenger_generation < generation_interval:
            return
            
        self.last_passenger_generation = current_minute
        
        # 生成乘客
        passenger_count = random.randint(1, max_passengers)
        
        # 楼层权重分配 (1楼70%，-1和-2各10%，其他楼层共10%)
        floor_weights = []
        all_floors = [f for f in range(-self.basement_floors, self.total_floors + 1) if f != 0]
        
        for floor in all_floors:
            if floor == 1:
                floor_weights.append(70)
            elif floor in (-1, -2):
                floor_weights.append(10)
            else:
                floor_weights.append(1)  # 其他楼层共享10%的权重
        
        # 生成起始楼层
        start_floors = random.choices(
            all_floors,
            weights=floor_weights,
            k=passenger_count
        )
        
        # 生成目标楼层 (不能与起始楼层相同)
        end_floors = []
        for start in start_floors:
            possible_floors = [f for f in all_floors if f != start]
            end_floors.append(random.choice(possible_floors))
        
        # 创建乘客 (检查楼层人数不超过5人)
        for start, end in zip(start_floors, end_floors):
            if len(self.waiting_passengers.get(start, [])) < 5:  # 楼层人数不超过5人
                passenger = Passenger(start, end)
                self.waiting_passengers[start].append(passenger)
                self.passengers.append(passenger)
        
    def update_simulation(self):
        if not self.is_running:
            return
            
        # Advance simulation time
        self.simulation_time += 1
        
        # 处理初始延迟
        if not self.initial_passengers_generated:
            all_elevators_ready = all(elevator.initial_delay <= 0 for elevator in self.elevators)
            if all_elevators_ready:
                self.generate_initial_passengers()
        
        # Generate new passengers
        if self.initial_passengers_generated:
            self.generate_passengers()
        
        # Move elevators and handle passengers
        for elevator in self.elevators:
            # Move elevator
            elevator.move()
            
            # If door is open, handle passengers
            if elevator.door_open:
                # Unboard passengers
                unboarded = elevator.unboard_passengers()
                
                # Board passengers
                floor = elevator.current_floor
                floor_passengers = self.waiting_passengers.get(floor, [])
                
                if floor_passengers:
                    # 先处理同方向乘客
                    if elevator.direction == 1:  # Going up
                        to_board = [p for p in floor_passengers if p.direction == 1]
                    elif elevator.direction == -1:  # Going down
                        to_board = [p for p in floor_passengers if p.direction == -1]
                    else:  # Idle - 处理所有方向
                        to_board = floor_passengers[:]
                    
                    # 尝试让乘客登梯
                    boarded = 0
                    for passenger in to_board[:]:
                        if boarded >= elevator.max_capacity - len(elevator.passengers):
                            break
                        if elevator.board_passenger(passenger, floor_passengers):
                            boarded += 1
                
                # Close door after 3 seconds (reduced from 5 to improve flow)
                if time.time() - elevator.last_activity_time > 3:
                    elevator.close_door()
            
            # If elevator is idle, assign a random destination if there are waiting passengers
            if not elevator.destination_floors and not elevator.door_open and self.initial_passengers_generated:
                # 检查是否有等待的乘客
                all_waiting_floors = list(self.waiting_passengers.keys())
                if all_waiting_floors:
                    # 选择有乘客等待且电梯可到达的楼层
                    available_floors = [f for f in all_waiting_floors if f in elevator.allowed_floors]
                    if available_floors:
                        elevator.add_destination(random.choice(available_floors))
        
        # Update stats
        self.update_stats()
        
    def update_animation(self):
        self.simulation_display.update()
        
    def update_stats(self):
        total_passengers = len(self.passengers)
        waiting_passengers = sum(len(p) for p in self.waiting_passengers.values())
        in_elevator_passengers = total_passengers - waiting_passengers
        
        current_hour = (self.simulation_time // 60) % 24
        current_minute = self.simulation_time % 60
        
        stats = (
            f"模拟时间: {current_hour:02d}:{current_minute:02d}\n"
            f"总人数: {total_passengers} (等待: {waiting_passengers}, 乘梯: {in_elevator_passengers})\n"
            f"电梯状态:\n"
        )
        
        for elevator in self.elevators:
            stats += (
                f"电梯{elevator.id}: {elevator.status}, "
                f"人数: {len(elevator.passengers)}/{elevator.max_capacity}, "
                f"当前楼层: {elevator.current_floor}F, "
                f"目标楼层: {elevator.destination_floors}\n"
            )
        
        self.stats_label.setText(stats)
        
    def stop_simulation(self):
        self.is_running = False
        self.simulation_timer.stop()
        
        # 将所有电梯返回1楼并清空乘客
        for elevator in self.elevators:
            elevator.passengers = []
            elevator.destination_floors = []
            if elevator.current_floor != 1:
                elevator.add_destination(1)
            elevator.status = "返回1楼"
        
        # Clear all passengers and waiting lists
        self.passengers = []
        self.waiting_passengers = defaultdict(list)
        
        # Update stats to show cleared state
        self.update_stats()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    simulator = ElevatorSimulator()
    simulator.show()
    sys.exit(app.exec_())