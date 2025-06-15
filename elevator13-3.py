import sys
import random
import time
from collections import defaultdict
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QSpinBox, QPushButton, QGroupBox, QCheckBox, QGridLayout,
                            QScrollArea)
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
        self.idle_start_time = None  # 记录开始空闲的时间
        self.returning_home = False   # 是否正在返回默认楼层
        self.operation_mode = 1  # 0: 单独运行, 1: 并行运行
        
    def add_destination(self, floor):
        if floor not in self.destination_floors and floor in self.allowed_floors:
            self.destination_floors.append(floor)
            self.update_direction()
            
    def update_direction(self):
        if not self.destination_floors:
            self.direction = 0
            return
            
        # 根据方向排序目标楼层
        if self.direction == 1:  # 上行时按升序排列，低楼层先到达
            self.destination_floors.sort()
        elif self.direction == -1:  # 下行时按降序排列，高楼层先到达
            self.destination_floors.sort(reverse=True)
            
        if self.current_floor < self.destination_floors[0]:
            self.direction = 1
        elif self.current_floor > self.destination_floors[-1]:
            self.direction = -1
        else:
            # 特殊情况处理：如果电梯在目标楼层之间，选择最近的目标
            if not self.door_open:  # 确保不在开门状态
                if abs(self.current_floor - self.destination_floors[0]) < abs(self.current_floor - self.destination_floors[-1]):
                    self.direction = -1 if self.current_floor > self.destination_floors[0] else 1
                else:
                    self.direction = -1 if self.current_floor > self.destination_floors[-1] else 1
            else:
                self.direction = 0
                
    def move(self):
        # 处理初始状态
        current_time = time.time()
        
        # 处理返回默认楼层逻辑
        if self.returning_home:
            if not self.door_open and self.destination_floors:
                if self.current_floor < self.destination_floors[0]:
                    self.current_floor += 1
                    self.status = f"上行至{self.current_floor}F"
                elif self.current_floor > self.destination_floors[0]:
                    self.current_floor -= 1
                    self.status = f"下行至{self.current_floor}F"
                elif self.current_floor == self.destination_floors[0]:
                    self.open_door()
                    self.destination_floors.remove(self.current_floor)
            return

        # 正常移动逻辑
        if not self.door_open:
            # 没有目标时返回默认楼层
            if not self.destination_floors and not self.passengers:
                if self.idle_start_time is None:
                    self.idle_start_time = current_time
                else:
                    idle_time = current_time - self.idle_start_time
                    if idle_time > 20 and self.current_floor != self.default_floor:
                        self.add_destination(self.default_floor)
                        self.returning_home = True
                        self.status = f"返回{self.default_floor}F"
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
        # 设置开门状态和时间
        self.door_open = True
        self.last_activity_time = time.time()
        if self.returning_home and self.current_floor == self.default_floor:
            self.status = f"到达{self.default_floor}F"
            # 5秒后自动关门
            QTimer.singleShot(5000, self.close_door_after_return)
        else:
            self.status = f"开门@{self.current_floor}F"
        
    def close_door_after_return(self):
        if self.returning_home and self.current_floor == self.default_floor:
            self.close_door()
            self.returning_home = False
            self.idle_start_time = time.time()
            self.status = f"空闲@{self.default_floor}F"
        
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
        # 按照目标楼层排序乘客
        # 上行时低楼层先下，下行时高楼层先下
        if self.direction == 1:
            self.passengers.sort(key=lambda p: p.destination)
        elif self.direction == -1:
            self.passengers.sort(key=lambda p: p.destination, reverse=True)
            
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
        building_width = 900
        building_height = 700
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
            
        building_width = 900
        building_height = 700
        building_x = 50
        building_y = 50
        floor_height = building_height / (self.simulator.total_floors + self.simulator.basement_floors + 2)
        
        # Calculate elevator dimensions and positions
        elevator_width = 80  # 增加电梯宽度
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
            # 根据运行模式设置不同颜色
            if elevator.operation_mode == 0:  # 单独运行
                painter.setBrush(QColor(200, 200, 255))  # 浅蓝色
            else:  # 并行运行
                painter.setBrush(Qt.lightGray)
            painter.drawRect(elevator_x, elevator_y, elevator_width, floor_height - 20)
            
            # Draw door
            door_width = 30  # 增加门宽度
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
            font.setPointSize(9)  # 增加字体大小
            painter.setFont(font)
            
            # Elevator ID
            painter.drawText(elevator_x + 5, elevator_y + 15, f"电梯{elevator.id}")
            
            # 运行模式
            mode_text = "单" if elevator.operation_mode == 0 else "并"
            painter.setPen(QColor(0, 0, 200) if elevator.operation_mode == 0 else QColor(0, 100, 0))
            painter.drawText(elevator_x + elevator_width - 15, elevator_y + 35, mode_text)
            painter.setPen(Qt.black)
            
            # Passenger count
            painter.drawText(elevator_x + 5, elevator_y + 35, f"{len(elevator.passengers)}/{elevator.max_capacity}")
            
            # Direction indicator
            if elevator.direction == 1:
                painter.drawText(elevator_x + elevator_width - 15, elevator_y + 15, "↑")
            elif elevator.direction == -1:
                painter.drawText(elevator_x + elevator_width - 15, elevator_y + 15, "↓")
            
            # Draw passengers in elevator (as colored circles)
            for j, passenger in enumerate(elevator.passengers):
                px = elevator_x + 15 + (j % 4) * 15  # 每行4人
                py = elevator_y + 50 + (j // 4) * 15
                
                # 修复除零错误：添加分母检查
                if elevator.direction == 1:
                    # 上行时，低楼层颜色更浅
                    denominator = (self.simulator.total_floors - elevator.current_floor)
                    if denominator != 0:
                        color_ratio = 1.0 - (passenger.destination - elevator.current_floor) / denominator
                    else:
                        color_ratio = 0.5  # 默认中等绿色
                    color = QColor(0, int(255 * color_ratio), 0)
                else:
                    # 下行时，高楼层颜色更浅
                    denominator = (elevator.current_floor - (-self.simulator.basement_floors))
                    if denominator != 0:
                        color_ratio = (passenger.destination - (-self.simulator.basement_floors)) / denominator
                    else:
                        color_ratio = 0.5  # 默认中等红色
                    color = QColor(int(255 * color_ratio), 0, 0)
                    
                painter.setBrush(color)
                painter.drawEllipse(px, py, 10, 10)
                
                # 显示乘客目标楼层
                painter.setPen(Qt.white)
                painter.drawText(px + 2, py + 8, f"{passenger.destination}")
                painter.setPen(Qt.black)
        
    def draw_waiting_passengers(self, painter):
        building_width = 900
        building_height = 700
        building_x = 50
        building_y = 50
        floor_height = building_height / (self.simulator.total_floors + self.simulator.basement_floors + 2)
        
        for floor, passengers in self.simulator.waiting_passengers.items():
            floor_index = (self.simulator.basement_floors + floor) if floor > 0 else (self.simulator.basement_floors + abs(floor))
            floor_y = building_y + building_height - (floor_index + 1) * floor_height + 10
            
            # Draw waiting passengers (as colored circles)
            for i, passenger in enumerate(passengers[:20]):  # 最多显示20人
                px = building_x + 30 + (i % 5) * 15
                py = floor_y + (i // 5) * 15
                # 根据乘客方向使用不同颜色
                painter.setBrush(Qt.green if passenger.direction == 1 else Qt.yellow)
                painter.drawEllipse(px, py, 10, 10)
                
                # 显示乘客目标楼层
                painter.setPen(Qt.black)
                painter.drawText(px + 2, py + 8, f"{passenger.destination}")


class ElevatorSimulator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("智能电梯调度系统")
        self.setGeometry(100, 100, 1400, 900)  # 增加窗口高度
        
        # Simulation parameters
        self.elevators = []
        self.total_floors = 20
        self.basement_floors = 0
        self.passengers = []
        self.waiting_passengers = defaultdict(list)
        self.simulation_time = 0
        self.time_multiplier = 60  # 1 real second = 1 simulation minute
        self.is_running = False
        self.initial_passengers_generated = False
        self.last_passenger_generation = 0
        self.no_passenger_time = 0  # 无乘客时间计数
        self.peak_hours = {
            "morning": (8, 9),    # 8-9 AM
            "evening": (18, 21)   # 6-9 PM
        }
        
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
        
        # Control panel
        control_panel = QGroupBox("电梯配置")
        control_layout = QVBoxLayout()
        control_panel.setLayout(control_layout)
        control_panel.setFixedWidth(400)  # 增加控制面板宽度
        
        # Elevator count (限制最多4部电梯)
        elevator_count_layout = QHBoxLayout()
        elevator_count_layout.addWidget(QLabel("电梯数量 (1-4):"))
        self.elevator_count = QSpinBox()
        self.elevator_count.setRange(1, 4)
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
        
        # Initial passengers
        initial_passengers_layout = QHBoxLayout()
        initial_passengers_layout.addWidget(QLabel("初始乘客数:"))
        self.initial_passengers_input = QSpinBox()
        self.initial_passengers_input.setRange(0, 20)
        self.initial_passengers_input.setValue(5)  # 默认5人
        initial_passengers_layout.addWidget(self.initial_passengers_input)
        control_layout.addLayout(initial_passengers_layout)
        
        # Elevator settings group
        self.elevator_settings_group = QGroupBox("电梯详细设置")
        self.elevator_settings_layout = QVBoxLayout()
        self.elevator_settings_group.setLayout(self.elevator_settings_layout)
        
        # 使用滚动区域包装电梯设置
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_content.setLayout(self.elevator_settings_layout)
        scroll_area.setWidget(scroll_content)
        control_layout.addWidget(scroll_area)
        
        # Create elevator settings based on count
        self.create_elevator_settings()
        self.elevator_count.valueChanged.connect(self.create_elevator_settings)
        
        # Simulation controls (放在同一行)
        control_buttons_layout = QHBoxLayout()
        start_button = QPushButton("开始模拟")
        start_button.setStyleSheet("background-color: #4CAF50; color: white; font-size: 14px;")
        start_button.setFixedHeight(40)
        start_button.clicked.connect(self.start_simulation)
        control_buttons_layout.addWidget(start_button)
        
        stop_button = QPushButton("停止模拟")
        stop_button.setStyleSheet("background-color: #f44336; color: white; font-size: 14px;")
        stop_button.setFixedHeight(40)
        stop_button.clicked.connect(self.stop_simulation)
        control_buttons_layout.addWidget(stop_button)
        
        control_layout.addLayout(control_buttons_layout)
        
        # Stats display
        self.stats_label = QLabel("模拟统计信息将显示在这里")
        self.stats_label.setWordWrap(True)
        self.stats_label.setStyleSheet("font-size: 14px; border: 1px solid #ccc; padding: 10px;")
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
            group.setStyleSheet("QGroupBox { font-weight: bold; }")
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
            
            # Operation mode
            mode_layout = QHBoxLayout()
            mode_layout.addWidget(QLabel("运行模式:"))
            single_mode = QCheckBox("单独运行")
            single_mode.setObjectName(f"single_mode_{i}")
            single_mode.toggled.connect(lambda checked, idx=i: self.set_operation_mode(idx, checked))
            mode_layout.addWidget(single_mode)
            
            parallel_mode = QCheckBox("并行运行")
            parallel_mode.setObjectName(f"parallel_mode_{i}")
            parallel_mode.setChecked(True)
            parallel_mode.toggled.connect(lambda checked, idx=i: self.set_operation_mode(idx, not checked))
            mode_layout.addWidget(parallel_mode)
            
            # 确保两个模式互斥
            single_mode.toggled.connect(lambda checked, cb=parallel_mode: cb.setChecked(not checked))
            parallel_mode.toggled.connect(lambda checked, cb=single_mode: cb.setChecked(not checked))
            
            layout.addLayout(mode_layout)
            
            # Allowed floors
            layout.addWidget(QLabel("可停靠楼层:"))
            
            # Create grid layout for floor checkboxes
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
                if col >= 5:  # 每行5个复选框
                    col = 0
                    row += 1
            
            layout.addLayout(floor_grid)
            group.setLayout(layout)
            self.elevator_settings_layout.addWidget(group)
        
    def set_operation_mode(self, elevator_idx, is_single):
        # 设置电梯运行模式 (0: 单独运行, 1: 并行运行)
        if elevator_idx < len(self.elevators):
            self.elevators[elevator_idx].operation_mode = 0 if is_single else 1
            
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
            
            # Get operation mode
            single_mode_cb = self.findChild(QCheckBox, f"single_mode_{i}")
            operation_mode = 0 if single_mode_cb and single_mode_cb.isChecked() else 1
            
            # Create elevator
            elevator = Elevator(i+1, capacity, default_floor, allowed_floors)
            elevator.current_floor = default_floor  # 确保初始在默认楼层
            elevator.operation_mode = operation_mode
            self.elevators.append(elevator)
        
        # Reset simulation state
        self.passengers = []
        self.waiting_passengers = defaultdict(list)
        self.simulation_time = 0
        self.is_running = True
        self.initial_passengers_generated = False
        self.last_passenger_generation = 0
        self.no_passenger_time = 0
        
        # Generate initial passengers
        initial_passenger_count = self.initial_passengers_input.value()
        self.generate_passengers(initial_passenger_count)
        self.initial_passengers_generated = True
        
        # 初始分配电梯任务
        self.assign_elevators()
        
        # Start simulation timer (updates every second)
        self.simulation_timer.start(1000)
        
    def assign_elevators(self):
        # 为等待的乘客分配电梯
        for floor, passengers in list(self.waiting_passengers.items()):
            if not passengers:
                continue
                
            # 为该楼层的乘客找到最合适的电梯
            for passenger in passengers[:]:
                best_elevator = self.find_best_elevator(floor, passenger.direction)
                if best_elevator:
                    # 分配电梯
                    if floor not in best_elevator.destination_floors:
                        best_elevator.add_destination(floor)
                    # 如果电梯是空闲的，设置方向
                    if best_elevator.direction == 0:
                        best_elevator.direction = 1 if floor > best_elevator.current_floor else -1
    
    def find_best_elevator(self, floor, direction):
        # 找到最适合的电梯
        best_elevator = None
        min_distance = float('inf')
        
        # 首先查找并行运行的电梯
        for elevator in self.elevators:
            if elevator.operation_mode == 1:  # 并行运行
                # 检查电梯是否可以到达该楼层
                if floor not in elevator.allowed_floors:
                    continue
                    
                # 计算距离
                distance = abs(elevator.current_floor - floor)
                
                # 优先考虑空闲或同向的电梯
                if elevator.direction == 0:  # 空闲电梯
                    if distance < min_distance:
                        min_distance = distance
                        best_elevator = elevator
                elif elevator.direction == 1 and direction == 1 and floor > elevator.current_floor:
                    # 上行电梯，乘客也上行，且乘客在电梯上方
                    if distance < min_distance:
                        min_distance = distance
                        best_elevator = elevator
                elif elevator.direction == -1 and direction == -1 and floor < elevator.current_floor:
                    # 下行电梯，乘客也下行，且乘客在电梯下方
                    if distance < min_distance:
                        min_distance = distance
                        best_elevator = elevator
        
        # 如果没有找到并行运行的电梯，查找单独运行的电梯
        if not best_elevator:
            for elevator in self.elevators:
                if elevator.operation_mode == 0:  # 单独运行
                    # 检查电梯是否可以到达该楼层
                    if floor not in elevator.allowed_floors:
                        continue
                        
                    # 计算距离
                    distance = abs(elevator.current_floor - floor)
                    
                    # 优先考虑空闲或同向的电梯
                    if elevator.direction == 0:  # 空闲电梯
                        if distance < min_distance:
                            min_distance = distance
                            best_elevator = elevator
                    elif elevator.direction == 1 and direction == 1 and floor > elevator.current_floor:
                        # 上行电梯，乘客也上行，且乘客在电梯上方
                        if distance < min_distance:
                            min_distance = distance
                            best_elevator = elevator
                    elif elevator.direction == -1 and direction == -1 and floor < elevator.current_floor:
                        # 下行电梯，乘客也下行，且乘客在电梯下方
                        if distance < min_distance:
                            min_distance = distance
                            best_elevator = elevator
        
        # 如果还是没有找到，选择距离最近的电梯
        if not best_elevator:
            for elevator in self.elevators:
                if floor in elevator.allowed_floors:
                    distance = abs(elevator.current_floor - floor)
                    if distance < min_distance:
                        min_distance = distance
                        best_elevator = elevator
                        
        return best_elevator
        
    def generate_passengers(self, count=1):
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
            k=count
        )
        
        # 生成目标楼层 (不能与起始楼层相同)
        end_floors = []
        for start in start_floors:
            possible_floors = [f for f in all_floors if f != start]
            end_floors.append(random.choice(possible_floors))
        
        # 创建乘客 (检查楼层人数不超过5人)
        new_passengers = []
        for start, end in zip(start_floors, end_floors):
            if len(self.waiting_passengers.get(start, [])) < 5:  # 楼层人数不超过5人
                passenger = Passenger(start, end)
                self.waiting_passengers[start].append(passenger)
                self.passengers.append(passenger)
                new_passengers.append(passenger)
                
        # 为新生成的乘客分配电梯
        if new_passengers:
            self.assign_elevators()
        
    def update_simulation(self):
        if not self.is_running:
            return
            
        # Advance simulation time
        self.simulation_time += 1
        
        # 检查是否需要生成新乘客
        current_hour = (self.simulation_time // 60) % 24
        is_peak = (8 <= current_hour < 9) or (18 <= current_hour < 21)
        generation_interval = 1 if is_peak else 2  # 高峰期1分钟，非高峰期2分钟
        
        current_minute = self.simulation_time // self.time_multiplier
        if current_minute - self.last_passenger_generation >= generation_interval:
            max_passengers = 5 if is_peak else 3
            self.generate_passengers(random.randint(1, max_passengers))
            self.last_passenger_generation = current_minute
        
        # 处理电梯和乘客交互
        for elevator in self.elevators:
            # 防止电梯卡在中间状态
            if not elevator.door_open and not elevator.destination_floors and elevator.current_floor != elevator.default_floor:
                elevator.add_destination(elevator.default_floor)
                elevator.returning_home = True
                elevator.status = f"返回{elevator.default_floor}F"
            
            elevator.move()
            
            # 处理开门状态
            if elevator.door_open:
                # 非返回默认楼层的正常开门，5秒后关门
                if not elevator.returning_home and time.time() - elevator.last_activity_time > 5:
                    elevator.close_door()
                else:
                    # 开门时处理乘客上下
                    floor = elevator.current_floor
                    floor_passengers = self.waiting_passengers.get(floor, [])
                    
                    # 乘客下电梯
                    unboarded = elevator.unboard_passengers()
                    
                    # 乘客上电梯
                    if floor_passengers:
                        # 先处理同方向乘客
                        if elevator.direction == 1:  # 上行
                            to_board = [p for p in floor_passengers if p.direction == 1]
                        elif elevator.direction == -1:  # 下行
                            to_board = [p for p in floor_passengers if p.direction == -1]
                        else:  # 空闲 - 处理所有方向
                            to_board = floor_passengers[:]
                        
                        # 尝试让乘客登梯
                        boarded = 0
                        for passenger in to_board[:]:
                            if boarded >= elevator.max_capacity - len(elevator.passengers):
                                break
                            if elevator.board_passenger(passenger, floor_passengers):
                                boarded += 1
                                
                        # 如果有乘客登梯，更新电梯方向
                        if boarded > 0 and elevator.direction == 0:
                            elevator.update_direction()
                    else:
                        # 如果没有乘客等待，提前关门
                        if not elevator.returning_home and time.time() - elevator.last_activity_time > 3:
                            elevator.close_door()

        # 检查并重新分配未被处理的乘客
        for floor, passengers in list(self.waiting_passengers.items()):
            if passengers:
                # 检查是否有电梯已分配到该楼层
                assigned = any(
                    floor in elevator.destination_floors 
                    for elevator in self.elevators
                )
                
                # 如果没有电梯前往该楼层，重新分配
                if not assigned:
                    for passenger in passengers:
                        best_elevator = self.find_best_elevator(floor, passenger.direction)
                        if best_elevator and floor not in best_elevator.destination_floors:
                            best_elevator.add_destination(floor)
                            # 如果电梯是空闲的，设置方向
                            if best_elevator.direction == 0:
                                best_elevator.direction = 1 if floor > best_elevator.current_floor else -1
        
        # 更新统计信息
        self.update_stats()
        
        # 刷新显示
        self.simulation_display.update()
    
    def update_stats(self):
        # 计算总乘客数
        total_passengers = len(self.passengers)
        
        # 计算等待中的乘客数
        waiting_passengers = sum(len(p) for p in self.waiting_passengers.values())
        
        # 计算在电梯中的乘客数
        in_elevator = sum(len(e.passengers) for e in self.elevators)
        
        # 计算已完成行程的乘客数
        completed_trips = total_passengers - waiting_passengers - in_elevator
        
        # 计算平均等待时间
        avg_wait_time = 0
        if waiting_passengers > 0:
            total_wait_time = sum(p.waiting_time for floor_ps in self.waiting_passengers.values() for p in floor_ps)
            avg_wait_time = total_wait_time / waiting_passengers
        
        # 电梯状态
        elevator_status = "\n".join(
            f"电梯 {e.id}: {e.status}, 当前{len(e.passengers)}/{e.max_capacity}人"
            for e in self.elevators
        )
        
        # 显示统计信息
        current_time = self.format_time(self.simulation_time)
        stats_text = (
            f"模拟时间: {current_time}\n"
            f"总乘客数: {total_passengers}\n"
            f"等待中: {waiting_passengers}\n"
            f"电梯中: {in_elevator}\n"
            f"已完成: {completed_trips}\n"
            f"平均等待时间: {avg_wait_time:.1f} 分钟\n\n"
            f"电梯状态:\n{elevator_status}"
        )
        
        self.stats_label.setText(stats_text)
    
    def format_time(self, seconds):
        """将模拟秒数转换为小时:分钟格式"""
        hours = (seconds // 60) % 24
        minutes = seconds % 60
        return f"{hours:02d}:{minutes:02d}"
    
    def update_animation(self):
        """更新动画状态"""
        if self.is_running:
            self.simulation_display.update()
    
    def stop_simulation(self):
        """停止模拟"""
        self.is_running = False
        self.simulation_timer.stop()
        self.stats_label.setText("模拟已停止")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ElevatorSimulator()
    window.show()
    sys.exit(app.exec_())