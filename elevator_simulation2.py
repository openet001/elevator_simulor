import pygame
import sys
import time
from enum import Enum
import random
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
import numpy as np

# 确保中文正常显示
pygame.font.init()
try:
    font = pygame.font.SysFont(["SimHei", "WenQuanYi Micro Hei", "Heiti TC"], 20)  # 减小字体大小
except:
    font = pygame.font.SysFont(None, 20)  # 减小字体大小

# 方向枚举
class Direction(Enum):
    IDLE = 0
    UP = 1
    DOWN = -1

# 电梯类
class Elevator:
    def __init__(self, elevator_id, accessible_floors, capacity=10, speed=1, acceleration=0.5):
        self.elevator_id = elevator_id
        self.current_floor = 1
        self.target_floor = 1
        self.direction = Direction.IDLE
        self.destination_floors = []  # 目标楼层列表
        self.accessible_floors = accessible_floors  # 可到达的楼层列表
        self.capacity = capacity  # 电梯容量
        self.passengers = []  # 电梯内的乘客
        self.is_door_open = False
        self.door_timer = 0
        self.door_open_time = 3  # 门保持打开的时间（秒）
        self.speed = speed  # 电梯速度（层/秒）
        self.acceleration = acceleration  # 电梯加速度
        self.current_speed = 0  # 当前速度
        self.position = 1.0  # 精确位置（浮点数）
        self.moving_progress = 0  # 移动进度（0-1）
        
    def add_destination(self, floor):
        # 检查楼层是否可到达
        if floor not in self.accessible_floors:
            print(f"电梯 {self.elevator_id} 无法到达楼层 {floor}")
            return
        
        # 如果楼层不在目标列表中，则添加
        if floor not in self.destination_floors:
            self.destination_floors.append(floor)
            
            # 根据当前位置和方向对目标楼层进行排序
            self._sort_destination_floors()
    
    def _sort_destination_floors(self):
        if not self.destination_floors:
            return
            
        # 如果电梯静止，根据最近楼层排序
        if self.direction == Direction.IDLE:
            self.destination_floors.sort(key=lambda x: abs(x - self.current_floor))
            if self.destination_floors:
                first_floor = self.destination_floors[0]
                self.direction = Direction.UP if first_floor > self.current_floor else Direction.DOWN
        # 如果电梯上升，按升序排列
        elif self.direction == Direction.UP:
            self.destination_floors.sort()
            # 如果当前楼层高于所有目标楼层，改变方向
            if self.current_floor > max(self.destination_floors):
                self.direction = Direction.DOWN
                self.destination_floors.sort(reverse=True)
        # 如果电梯下降，按降序排列
        elif self.direction == Direction.DOWN:
            self.destination_floors.sort(reverse=True)
            # 如果当前楼层低于所有目标楼层，改变方向
            if self.current_floor < min(self.destination_floors):
                self.direction = Direction.UP
                self.destination_floors.sort()
    
    def move(self, dt):
        # 如果门是打开的，等待一段时间再关闭
        if self.is_door_open:
            self.door_timer += dt
            if self.door_timer >= self.door_open_time:
                self.is_door_open = False
                self.door_timer = 0
            return
            
        # 如果没有目标楼层，电梯静止
        if not self.destination_floors:
            self.direction = Direction.IDLE
            self.current_speed = 0
            self.position = self.current_floor
            return
            
        # 获取下一个目标楼层
        next_floor = self.destination_floors[0]
        
        # 物理模拟移动
        if self.current_floor == next_floor:
            # 到达目标楼层
            self.destination_floors.pop(0)
            self.is_door_open = True  # 到达目标楼层后开门
            self.current_speed = 0
            self.position = self.current_floor
            
            # 重新排序目标楼层
            self._sort_destination_floors()
            
            return
        else:
            # 计算方向
            direction = 1 if next_floor > self.current_floor else -1
            
            # 计算到目标楼层的距离
            distance = abs(next_floor - self.position)
            
            # 加速/减速逻辑
            if distance > 1.0:
                # 还有足够距离，可以加速到最大速度
                self.current_speed = min(self.current_speed + self.acceleration * dt, self.speed)
            else:
                # 接近目标楼层，开始减速
                self.current_speed = max(self.current_speed - self.acceleration * dt, 0)
            
            # 更新位置
            self.position += direction * self.current_speed * dt
            
            # 更新当前楼层
            if direction > 0 and self.position >= self.current_floor + 0.5:
                self.current_floor += 1
            elif direction < 0 and self.position <= self.current_floor - 0.5:
                self.current_floor -= 1
    
    def get_status(self):
        direction_text = "静止"
        if self.direction == Direction.UP:
            direction_text = "上升"
        elif self.direction == Direction.DOWN:
            direction_text = "下降"
            
        return {
            "id": self.elevator_id,
            "current_floor": self.current_floor,
            "direction": direction_text,
            "is_door_open": self.is_door_open,
            "passenger_count": len(self.passengers),
            "capacity": self.capacity,
            "destination_floors": self.destination_floors,
            "position": self.position
        }
    
    def add_passenger(self, passenger):
        # 检查电梯是否已满
        if len(self.passengers) >= self.capacity:
            print(f"电梯 {self.elevator_id} 已满，无法添加乘客")
            return False
            
        self.passengers.append(passenger)
        passenger.in_elevator = True
        # 添加乘客的目标楼层
        self.add_destination(passenger.destination_floor)
        return True
    
    def remove_passengers(self):
        # 移除目的地是当前楼层的乘客
        remaining_passengers = []
        removed_passengers = []
        
        for passenger in self.passengers:
            if passenger.destination_floor == self.current_floor:
                removed_passengers.append(passenger)
            else:
                remaining_passengers.append(passenger)
                
        self.passengers = remaining_passengers
        return removed_passengers

# 乘客类
class Passenger:
    def __init__(self, start_floor, destination_floor, passenger_id=None):
        self.start_floor = start_floor
        self.destination_floor = destination_floor
        self.waiting_time = 0
        self.travel_time = 0
        self.in_elevator = False
        self.passenger_id = passenger_id or random.randint(1000, 9999)
        self.assigned_elevator = None
        self.waiting_animation = 0  # 等待动画状态
    
    def update_time(self, dt):
        if not self.in_elevator:
            self.waiting_time += dt
            self.waiting_animation += dt * 3  # 控制动画速度
        else:
            self.travel_time += dt

# 建筑物类
class Building:
    def __init__(self, total_floors=20):
        self.total_floors = total_floors
        self.elevators = []
        self.waiting_passengers = {i: [] for i in range(1, total_floors + 1)}
        self.completed_passengers = []
        
        # 统计信息
        self.total_waiting_time = 0
        self.total_travel_time = 0
        self.total_passengers = 0
        
        # 模拟数据收集
        self.waiting_times_history = []
        self.travel_times_history = []
        self.passenger_count_history = []
        self.time_history = []
        self.current_time = 0
    
    def add_elevator(self, elevator):
        self.elevators.append(elevator)
    
    def add_passenger(self, passenger):
        self.waiting_passengers[passenger.start_floor].append(passenger)
        self.total_passengers += 1
        
        # 为乘客分配电梯
        self._assign_elevator(passenger)
    
    def _assign_elevator(self, passenger):
        start_floor = passenger.start_floor
        direction = Direction.UP if passenger.destination_floor > start_floor else Direction.DOWN
        
        best_elevator = None
        min_score = float('inf')
        
        for elevator in self.elevators:
            # 检查电梯是否可以到达乘客的起始楼层和目标楼层
            if start_floor not in elevator.accessible_floors or \
               passenger.destination_floor not in elevator.accessible_floors:
                continue
                
            # 计算电梯得分
            score = self._calculate_elevator_score(elevator, start_floor, direction)
            
            if score < min_score:
                min_score = score
                best_elevator = elevator
                
        if best_elevator:
            # 为电梯添加目标楼层
            best_elevator.add_destination(start_floor)
            # 记录乘客被分配到的电梯
            passenger.assigned_elevator = best_elevator.elevator_id
    
    def _calculate_elevator_score(self, elevator, floor, direction):
        # 基础得分是电梯到目标楼层的距离
        distance = abs(elevator.current_floor - floor)
        
        # 如果电梯静止，加分
        if elevator.direction == Direction.IDLE:
            distance -= 5  # 给静止的电梯更高的优先级
            
        # 如果电梯正在向请求楼层移动，加分
        elif (direction == Direction.UP and elevator.direction == Direction.UP and elevator.current_floor < floor) or \
             (direction == Direction.DOWN and elevator.direction == Direction.DOWN and elevator.current_floor > floor):
            distance -= 3  # 给同向移动的电梯较高优先级
            
        # 如果电梯门是打开的，加分
        if elevator.is_door_open:
            distance -= 2
            
        # 考虑电梯负载
        load_factor = len(elevator.passengers) / elevator.capacity * 2
        
        return distance + load_factor
    
    def update(self, dt):
        self.current_time += dt
        
        # 更新所有乘客的等待时间
        for floor in self.waiting_passengers:
            for passenger in self.waiting_passengers[floor]:
                passenger.update_time(dt)
                
        # 更新所有电梯
        for elevator in self.elevators:
            elevator.move(dt)
            
            # 如果电梯门打开，处理乘客上下电梯
            if elevator.is_door_open:
                current_floor = elevator.current_floor
                
                # 乘客下电梯
                removed_passengers = elevator.remove_passengers()
                for passenger in removed_passengers:
                    self.completed_passengers.append(passenger)
                    self.total_waiting_time += passenger.waiting_time
                    self.total_travel_time += passenger.travel_time
                
                # 乘客上电梯
                remaining_passengers = []
                for passenger in self.waiting_passengers[current_floor]:
                    # 检查乘客是否被分配到这个电梯
                    if hasattr(passenger, 'assigned_elevator') and passenger.assigned_elevator == elevator.elevator_id:
                        if elevator.add_passenger(passenger):
                            # 乘客成功进入电梯
                            pass
                        else:
                            remaining_passengers.append(passenger)
                    else:
                        remaining_passengers.append(passenger)
                
                self.waiting_passengers[current_floor] = remaining_passengers
        
        # 收集统计数据
        self._collect_statistics(dt)
    
    def generate_random_passenger(self, dt):
        # 基于时间间隔生成乘客
        if random.random() < 0.1 * dt:  # 每秒10%的概率生成新乘客
            start_floor = random.randint(1, self.total_floors)
            
            # 确保目标楼层与起始楼层不同
            possible_destinations = list(range(1, self.total_floors + 1))
            possible_destinations.remove(start_floor)
            destination_floor = random.choice(possible_destinations)
            
            passenger = Passenger(start_floor, destination_floor)
            self.add_passenger(passenger)
            return passenger
        return None
    
    def _collect_statistics(self, dt):
        # 收集统计数据用于图表
        if self.current_time % 1 <= dt:  # 大约每秒收集一次数据
            total_waiting = sum(p.waiting_time for floor in self.waiting_passengers for p in self.waiting_passengers[floor])
            total_travel = sum(p.travel_time for elevator in self.elevators for p in elevator.passengers)
            
            waiting_count = sum(len(self.waiting_passengers[floor]) for floor in self.waiting_passengers)
            travel_count = sum(len(elevator.passengers) for elevator in self.elevators)
            
            avg_waiting_time = total_waiting / waiting_count if waiting_count > 0 else 0
            avg_travel_time = total_travel / travel_count if travel_count > 0 else 0
            
            self.waiting_times_history.append(avg_waiting_time)
            self.travel_times_history.append(avg_travel_time)
            self.passenger_count_history.append(waiting_count + travel_count)
            self.time_history.append(self.current_time)
            
            # 保持数据点数量在合理范围内
            max_points = 100
            if len(self.time_history) > max_points:
                self.time_history.pop(0)
                self.waiting_times_history.pop(0)
                self.travel_times_history.pop(0)
                self.passenger_count_history.pop(0)
    
    def get_statistics(self):
        total_passengers = sum(len(self.waiting_passengers[floor]) for floor in self.waiting_passengers)
        total_passengers += sum(len(elevator.passengers) for elevator in self.elevators)
        total_passengers += len(self.completed_passengers)
        
        # 计算平均等待时间和行程时间
        avg_waiting_time = self.total_waiting_time / len(self.completed_passengers) if self.completed_passengers else 0
        avg_travel_time = self.total_travel_time / len(self.completed_passengers) if self.completed_passengers else 0
        
        # 计算当前等待时间最长的乘客
        max_waiting_passenger = None
        max_waiting_time = 0
        for floor in self.waiting_passengers:
            for passenger in self.waiting_passengers[floor]:
                if passenger.waiting_time > max_waiting_time:
                    max_waiting_time = passenger.waiting_time
                    max_waiting_passenger = passenger
        
        return {
            "total_passengers": total_passengers,
            "waiting_passengers": sum(len(self.waiting_passengers[floor]) for floor in self.waiting_passengers),
            "passengers_in_elevators": sum(len(elevator.passengers) for elevator in self.elevators),
            "completed_trips": len(self.completed_passengers),
            "avg_waiting_time": avg_waiting_time,
            "avg_travel_time": avg_travel_time,
            "max_waiting_time": max_waiting_time,
            "time_history": self.time_history,
            "waiting_times_history": self.waiting_times_history,
            "travel_times_history": self.travel_times_history,
            "passenger_count_history": self.passenger_count_history
        }

# 电梯模拟器类
class ElevatorSimulator:
    def __init__(self, total_floors=20):
        self.building = Building(total_floors)
        self.running = False
        self.screen = None
        self.clock = None
        self.width = 1200
        self.height = 800
        self.floor_height = 600 / total_floors
        self.fps = 60
        self.time_multiplier = 1  # 时间倍率
        self.last_update_time = 0
        self.show_charts = False  # 是否显示图表
        
        # 初始化图表
        self.fig, self.axes = plt.subplots(2, 1, figsize=(6, 6))
        self.canvas = FigureCanvasAgg(self.fig)
        
    def setup(self):
        pygame.init()
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("电梯智能仿真模拟系统")
        self.clock = pygame.time.Clock()
        
        # 添加电梯
        self.building.add_elevator(Elevator(1, list(range(1, self.building.total_floors + 1)), 10, 1.2, 0.6))  # 全楼层，较快
        self.building.add_elevator(Elevator(2, list(range(1, self.building.total_floors + 1)), 10, 1.0, 0.5))  # 全楼层，标准
        self.building.add_elevator(Elevator(3, [1] + list(range(10, self.building.total_floors + 1)), 15, 1.5, 0.7))  # 低层和高层，高速
        self.building.add_elevator(Elevator(4, [1] + list(range(2, 11)), 15, 1.0, 0.5))  # 低层
        
        self.running = True
    
    def run(self):
        if not self.running:
            self.setup()
            
        while self.running:
            current_time = pygame.time.get_ticks()
            dt = self.clock.tick(self.fps) / 1000.0  # 转换为秒
            
            # 事件处理
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_UP:
                        self.time_multiplier = min(20, self.time_multiplier + 1)
                    elif event.key == pygame.K_DOWN:
                        self.time_multiplier = max(1, self.time_multiplier - 1)
                    elif event.key == pygame.K_SPACE:
                        self.show_charts = not self.show_charts
                    elif event.key == pygame.K_r:
                        # 重置模拟
                        self.__init__(self.building.total_floors)
                        self.setup()
            
            # 更新电梯状态
            self.building.update(dt * self.time_multiplier)
            self.building.generate_random_passenger(dt * self.time_multiplier)
            
            # 渲染
            self.render()
            
        pygame.quit()
    
    def render(self):
        self.screen.fill((240, 240, 240))
        
        # 绘制建筑物和电梯井道
        elevator_width = 70
        shaft_margin = 20
        shaft_width = elevator_width * len(self.building.elevators) + shaft_margin * (len(self.building.elevators) - 1)
        shaft_x = (self.width - shaft_width) // 2
        shaft_y = 50
        shaft_height = 600
        
        # 绘制井道边框
        pygame.draw.rect(self.screen, (100, 100, 100), 
                         (shaft_x - 10, shaft_y - 10, shaft_width + 20, shaft_height + 20), 2)
        
        # 绘制楼层分隔线
        for i in range(self.building.total_floors + 1):
            # 从底部开始计算y坐标
            y = shaft_y + (self.building.total_floors - i) * self.floor_height  # 修正：楼层从下往上递增
            pygame.draw.line(self.screen, (180, 180, 180), 
                             (shaft_x - 10, y), (shaft_x + shaft_width + 10, y), 1)
            
            # 绘制楼层号
            floor_num = self.building.total_floors - i  # 修正：楼层号从下往上递增
            floor_text = font.render(f"楼层 {floor_num}", True, (0, 0, 0))
            self.screen.blit(floor_text, (shaft_x - 10 - floor_text.get_width() - 10, y - floor_text.get_height() // 2))
            
            # 绘制等待的乘客
            if floor_num in self.building.waiting_passengers:
                passengers = self.building.waiting_passengers[floor_num]
                for j, passenger in enumerate(passengers):
                    # 乘客动画
                    offset_y = abs(np.sin(passenger.waiting_animation)) * 5
                    
                    # 根据乘客要去的方向绘制不同颜色
                    color = (100, 100, 200) if passenger.destination_floor > floor_num else (200, 100, 100)
                    
                    pygame.draw.circle(self.screen, color, 
                                      (shaft_x - 30 - (j % 3) * 20, y - 10 + offset_y), 8)
                    
                    # 绘制方向指示
                    if passenger.destination_floor > floor_num:
                        pygame.draw.polygon(self.screen, color, 
                                           [(shaft_x - 30 - (j % 3) * 20 - 5, y - 20),
                                            (shaft_x - 30 - (j % 3) * 20 + 5, y - 20),
                                            (shaft_x - 30 - (j % 3) * 20, y - 25)])
                    else:
                        pygame.draw.polygon(self.screen, color, 
                                           [(shaft_x - 30 - (j % 3) * 20 - 5, y),
                                            (shaft_x - 30 - (j % 3) * 20 + 5, y),
                                            (shaft_x - 30 - (j % 3) * 20, y + 5)])
        
        # 绘制电梯
        for i, elevator in enumerate(self.building.elevators):
            elevator_x = shaft_x + i * (elevator_width + shaft_margin)
            # 从底部开始计算电梯位置
            elevator_y = shaft_y + (self.building.total_floors - elevator.position) * self.floor_height  # 修正：电梯位置从下往上
            
            # 电梯颜色
            if elevator.is_door_open:
                elevator_color = (100, 200, 100)  # 绿色表示门开着
            elif elevator.direction == Direction.UP:
                elevator_color = (100, 100, 200)  # 蓝色表示上升
            elif elevator.direction == Direction.DOWN:
                elevator_color = (200, 100, 100)  # 红色表示下降
            else:
                elevator_color = (150, 150, 150)  # 灰色表示静止
                
            # 绘制电梯
            pygame.draw.rect(self.screen, elevator_color, 
                             (elevator_x, elevator_y, elevator_width, self.floor_height - 2))
            
            # 绘制电梯门
            door_width = elevator_width // 5
            if elevator.is_door_open:
                # 开门状态
                pygame.draw.rect(self.screen, (220, 220, 220), 
                                 (elevator_x + door_width, elevator_y, elevator_width - 2 * door_width, self.floor_height - 2))
            else:
                # 关门状态
                pygame.draw.rect(self.screen, (220, 220, 220), 
                                 (elevator_x, elevator_y, door_width, self.floor_height - 2))
                pygame.draw.rect(self.screen, (220, 220, 220), 
                                 (elevator_x + elevator_width - door_width, elevator_y, door_width, self.floor_height - 2))
            
            # 绘制电梯ID
            elevator_id_text = font.render(f"电梯 {elevator.elevator_id}", True, (0, 0, 0))
            self.screen.blit(elevator_id_text, 
                            (elevator_x + elevator_width // 2 - elevator_id_text.get_width() // 2, 
                             elevator_y + self.floor_height // 2 - elevator_id_text.get_height() // 2))
            
            # 绘制电梯内人数
            people_text = font.render(f"{len(elevator.passengers)}/{elevator.capacity}", True, (0, 0, 0))
            self.screen.blit(people_text, 
                            (elevator_x + elevator_width // 2 - people_text.get_width() // 2, 
                             elevator_y + self.floor_height // 2 + elevator_id_text.get_height() // 2 + 5))
            
            # 绘制电梯方向指示器
            if elevator.direction == Direction.UP:
                pygame.draw.polygon(self.screen, (255, 255, 255), 
                                   [(elevator_x + elevator_width // 2 - 8, elevator_y - 15),
                                    (elevator_x + elevator_width // 2 + 8, elevator_y - 15),
                                    (elevator_x + elevator_width // 2, elevator_y - 25)])
            elif elevator.direction == Direction.DOWN:
                pygame.draw.polygon(self.screen, (255, 255, 255), 
                                   [(elevator_x + elevator_width // 2 - 8, elevator_y - 5),
                                    (elevator_x + elevator_width // 2 + 8, elevator_y - 5),
                                    (elevator_x + elevator_width // 2, elevator_y + 5)])
        
        # 绘制控制面板
        control_panel_x = 50
        control_panel_y = shaft_y + shaft_height + 30
        control_panel_width = self.width - 100
        control_panel_height = 100
        
        pygame.draw.rect(self.screen, (220, 220, 220), 
                         (control_panel_x, control_panel_y, control_panel_width, control_panel_height))
        pygame.draw.rect(self.screen, (100, 100, 100), 
                         (control_panel_x, control_panel_y, control_panel_width, control_panel_height), 2)
        
        # 绘制电梯状态
        status_text = font.render("电梯状态:", True, (0, 0, 0))
        self.screen.blit(status_text, (control_panel_x + 20, control_panel_y + 20))
        
        for i, elevator in enumerate(self.building.elevators):
            status = elevator.get_status()
            elevator_status_text = font.render(
                f"电梯 {status['id']}: 楼层 {status['current_floor']:.1f}, {status['direction']}, "
                f"乘客 {status['passenger_count']}/{status['capacity']}", 
                True, (0, 0, 0))
            self.screen.blit(elevator_status_text, 
                            (control_panel_x + 20 + status_text.get_width() + 20 + i * 300, 
                             control_panel_y + 20))
        
        # 绘制统计信息
        stats = self.building.get_statistics()
        stats_text = font.render(
            f"总乘客: {stats['total_passengers']}, 等待中: {stats['waiting_passengers']}, "
            f"电梯中: {stats['passengers_in_elevators']}, 已完成: {stats['completed_trips']}, "
            f"最长等待: {stats['max_waiting_time']:.1f}s", 
            True, (0, 0, 0))
        self.screen.blit(stats_text, (control_panel_x + 20, control_panel_y + 60))
        
        # 绘制时间倍率
        speed_text = font.render(f"模拟速度: {self.time_multiplier}x (↑/↓键调整), 按空格切换图表, 按R重置", True, (0, 0, 0))
        self.screen.blit(speed_text, (self.width - speed_text.get_width() - 20, 20))
        
        # 绘制图表
        if self.show_charts:
            self._render_charts()
        
        # 更新显示
        pygame.display.flip()
    
    def _render_charts(self):
        stats = self.building.get_statistics()
        
        # 清除图表
        for ax in self.axes:
            ax.clear()
        
        # 绘制等待时间和行程时间图表
        if stats['time_history']:
            self.axes[0].plot(stats['time_history'], stats['waiting_times_history'], 'r-', label='平均等待时间')
            self.axes[0].plot(stats['time_history'], stats['travel_times_history'], 'b-', label='平均行程时间')
            self.axes[0].set_xlabel('时间 (秒)')
            self.axes[0].set_ylabel('时间 (秒)')
            self.axes[0].legend()
            self.axes[0].grid(True)
            
            # 绘制乘客数量图表
            self.axes[1].plot(stats['time_history'], stats['passenger_count_history'], 'g-', label='乘客总数')
            self.axes[1].set_xlabel('时间 (秒)')
            self.axes[1].set_ylabel('乘客数量')
            self.axes[1].legend()
            self.axes[1].grid(True)
            
            # 调整布局
            self.fig.tight_layout()
            
            # 渲染图表到Pygame
            self.canvas.draw()
            renderer = self.canvas.get_renderer()
            raw_data = renderer.tostring_rgb()
            
            size = self.canvas.get_width_height()
            chart_surf = pygame.image.fromstring(raw_data, size, "RGB")
            
            # 将图表绘制到屏幕上
            self.screen.blit(chart_surf, (10, 10))

# 主函数
def main():
    simulator = ElevatorSimulator(total_floors=20)
    simulator.run()

if __name__ == "__main__":
    main()        