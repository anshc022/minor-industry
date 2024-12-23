from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import cv2
import numpy as np  # Fixed import syntax
from datetime import datetime
from speed_detector import SpeedDetector
from traffic_signal import AdaptiveTrafficSignal
from traffic_predictor import TrafficPredictor  # Add this import

class TrafficUI(QMainWindow):
    def __init__(self):
        super().__init__()
        # Initialize lists and variables first
        self.vehicle_count = {'car': 0, 'motorcycle': 0, 'bus': 0, 'truck': 0}
        self.alerts = []
        self.cameras = [None] * 4
        self.video_paths = [None] * 4
        self.current_frame = [None] * 4
        self.video_labels = []  # Initialize before initUI
        self.is_monitoring = False
        self.current_vehicles = []
        self.record_buttons = []  # Add list for record buttons
        self.is_all_monitoring = False
        self.total_vehicles = 0
        self.density_update_timer = QTimer(self)
        self.density_update_timer.timeout.connect(self.update_total_density)
        self.density_update_timer.start(1000)  # Update every second
        
        # Initialize timers
        self.capture_timer = QTimer(self)
        self.capture_timer.timeout.connect(self.update_frame)
        self.capture_timer.setInterval(30)
        
        # Initialize detectors and signals
        self.speed_detector = SpeedDetector()
        self.next_object_id = 0
        self.tracked_vehicles = {}
        
        self.traffic_signal = AdaptiveTrafficSignal()
        self.signal_timer = QTimer(self)
        self.signal_timer.timeout.connect(self.update_traffic_signal)
        self.signal_timer.start(1000)
        
        self.traffic_predictor = TrafficPredictor()
        
        self.screen = QApplication.primaryScreen().availableGeometry()
        
        # Initialize UI after all variables are set
        self.alert_list = QListWidget()
        self.speed_list = QListWidget()
        self.prediction_list = QListWidget()
        self.recommendation_list = QListWidget()  # Add this line before initUI
        self.initUI()
        
        self.fps_counter = 0
        self.fps_timer = QTimer(self)
        self.fps_timer.timeout.connect(self.calculate_fps)
        self.fps_timer.start(1000)  # Update FPS every second
        self.last_frame_times = [datetime.now()] * 4
        
        # Replace dark theme with light theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
                color: #000000;
            }
            QGroupBox {
                background-color: white;
                border: 1px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                font-weight: bold;
                color: #2196F3;
            }
            QGroupBox::title {
                color: #1976D2;
            }
            QLabel {
                color: #333333;
            }
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 5px;
                background-color: white;
                text-align: center;
                color: black;
            }
            QListWidget {
                background-color: white;
                border: 1px solid #cccccc;
                border-radius: 5px;
                color: #333333;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        
        # Add prediction update timer
        self.prediction_timer = QTimer(self)
        self.prediction_timer.timeout.connect(self.update_predictions)
        self.prediction_timer.start(60000)  # Update predictions every minute

    def initUI(self):
        # Update window geometry to account for taskbar
        window_width = 1400
        window_height = min(800, self.screen.height() - 100)  # Leave space for taskbar
        x = (self.screen.width() - window_width) // 2
        y = (self.screen.height() - window_height) // 2
        self.setGeometry(x, y, window_width, window_height)
        self.setWindowTitle('Smart Traffic Management System')
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        
        # Create scroll areas for left and right panels
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Create containers
        left_container = QWidget()
        right_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        right_layout = QVBoxLayout(right_container)
        
        # Set containers to scroll areas
        left_scroll.setWidget(left_container)
        right_scroll.setWidget(right_container)
        
        # Add master control panel with minimum height
        master_control = QWidget()
        master_control.setMinimumHeight(50)
        master_layout = QHBoxLayout(master_control)
        self.master_start_btn = QPushButton('Start All Cameras')
        self.master_start_btn.clicked.connect(self.toggle_all_monitoring)
        self.master_start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14px;
                padding: 8px;
                min-width: 120px;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        master_layout.addWidget(self.master_start_btn)
        left_layout.addWidget(master_control)
        
        # Rest of the UI components
        # ...existing UI component code...
        
        # Update video grid layout
        video_grid = QGridLayout()
        self.camera_status_indicators = []  # Add list for camera status indicators
        self.fps_labels = []  # Add list for fps labels
        for i in range(4):
            video_container = QGroupBox(f'Camera {i+1}')
            video_container.setStyleSheet("""
                QGroupBox {
                    background-color: white;
                    border: 1px solid #cccccc;
                }
            """)
            video_layout = QVBoxLayout(video_container)
            
            # Video display with fixed size
            video_label = QLabel()
            video_label.setFixedSize(400, 300)
            self.video_labels.append(video_label)
            video_layout.addWidget(video_label)
            
            # Control buttons with minimum height
            btn_layout = QHBoxLayout()
            upload_btn = QPushButton('Upload Video')
            upload_btn.setMinimumHeight(30)
            upload_btn.clicked.connect(lambda checked, x=i: self.upload_video(x))
            btn_layout.addWidget(upload_btn)
            
            # Add camera status indicator
            status_label = QLabel("●")
            status_label.setStyleSheet("color: #ff4444; font-size: 20px;")  # Red for inactive
            btn_layout.addWidget(status_label)
            self.camera_status_indicators.append(status_label)
            
            # Add fps counter per camera
            fps_label = QLabel("0 FPS")
            fps_label.setStyleSheet("color: #2196F3;")  # Blue for FPS
            btn_layout.addWidget(fps_label)
            self.fps_labels.append(fps_label)
            
            video_layout.addLayout(btn_layout)
            video_grid.addWidget(video_container, i//2, i%2)
            
        left_layout.addLayout(video_grid)
        
        # Add scrollable areas to main layout
        main_layout.addWidget(left_scroll, stretch=2)
        main_layout.addWidget(right_scroll, stretch=1)
        
        # Set margins and spacing
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        left_layout.setContentsMargins(5, 5, 5, 5)
        right_layout.setContentsMargins(5, 5, 5, 5)
        
        # Initialize timer for updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        
        # Add the alert system at the top of the right panel
        alert_group = QGroupBox('System Alerts')
        alert_layout = QVBoxLayout()
        self.alert_list = QListWidget()
        self.alert_list.setMaximumHeight(150)  # Limit height
        alert_layout.addWidget(self.alert_list)
        alert_group.setLayout(alert_layout)
        right_layout.addWidget(alert_group)
        
        # Add statistics group
        stats_group = QGroupBox('Traffic Statistics')
        stats_layout = QVBoxLayout()
        
        # Vehicle counters
        self.vehicle_labels = {}
        for vehicle in ['Car', 'Motorcycle', 'Bus', 'Truck']:
            counter = QLabel(f'{vehicle}s: 0')
            self.vehicle_labels[vehicle.lower()] = counter
            stats_layout.addWidget(counter)
            
        stats_group.setLayout(stats_layout)
        right_layout.addWidget(stats_group)
        
        # Add prediction panel
        prediction_group = QGroupBox('Traffic Predictions')
        prediction_layout = QVBoxLayout()
        
        # Add time label
        self.prediction_time = QLabel('Next Update:')
        prediction_layout.addWidget(self.prediction_time)
        
        self.prediction_list.setMinimumHeight(150)
        self.prediction_list.setAlternatingRowColors(True)
        prediction_layout.addWidget(self.prediction_list)
        
        # Add recommendations section
        recommendation_label = QLabel('Traffic Recommendations:')
        prediction_layout.addWidget(recommendation_label)
        self.recommendation_list.setAlternatingRowColors(True)
        prediction_layout.addWidget(self.recommendation_list)
        
        # Add refresh button
        refresh_btn = QPushButton('Refresh Predictions')
        refresh_btn.clicked.connect(self.update_predictions)
        prediction_layout.addWidget(refresh_btn)
        
        prediction_group.setLayout(prediction_layout)
        right_layout.addWidget(prediction_group)
        
        # Add speed monitoring group
        speed_group = QGroupBox('Speed Monitoring')
        speed_layout = QVBoxLayout()
        self.speed_list = QListWidget()
        speed_layout.addWidget(self.speed_list)
        speed_group.setLayout(speed_layout)
        right_layout.addWidget(speed_group)
        
        # Add the density group before traffic signal controls
        density_group = QGroupBox('Overall Traffic Density')
        density_layout = QVBoxLayout()
        
        # Add density label and progress bar
        self.density_label = QLabel('Current Density: Normal')
        self.density_progress = QProgressBar()
        self.density_progress.setMinimum(0)
        self.density_progress.setMaximum(100)
        self.density_progress.setValue(0)
        self.density_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: green;
            }
        """)
        
        density_layout.addWidget(self.density_label)
        density_layout.addWidget(self.density_progress)
        density_group.setLayout(density_layout)
        right_layout.addWidget(density_group)

        # Update traffic signal control panel for multiple intersections
        signal_group = QGroupBox('Traffic Signal Control')
        signal_layout = QGridLayout()
        
        self.intersection_controls = []
        for i in range(4):
            intersection_box = QGroupBox(f'Intersection {i+1}')
            intersection_layout = QVBoxLayout()
            
            # Signal status
            ns_light = QLabel('North-South: RED')
            ew_light = QLabel('East-West: RED')
            phase_time = QLabel('Phase Time: 0s')
            
            # Traffic density bars
            ns_density = QProgressBar()
            ew_density = QProgressBar()
            
            intersection_layout.addWidget(ns_light)
            intersection_layout.addWidget(ew_light)
            intersection_layout.addWidget(phase_time)
            intersection_layout.addWidget(QLabel('N-S Traffic:'))
            intersection_layout.addWidget(ns_density)
            intersection_layout.addWidget(QLabel('E-W Traffic:'))
            intersection_layout.addWidget(ew_density)
            
            intersection_box.setLayout(intersection_layout)
            signal_layout.addWidget(intersection_box, i//2, i%2)
            
            self.intersection_controls.append({
                'ns_light': ns_light,
                'ew_light': ew_light,
                'phase_time': phase_time,
                'ns_density': ns_density,
                'ew_density': ew_density
            })
            
        signal_group.setLayout(signal_layout)
        right_layout.addWidget(signal_group)
        
        # Enable all components
        for progress_bar in [self.density_progress] + [c['ns_density'] for c in self.intersection_controls] + [c['ew_density'] for c in self.intersection_controls]:
            progress_bar.setEnabled(True)
            progress_bar.setTextVisible(True)
            progress_bar.setFormat("%v%")

        # Set list widgets properties
        for list_widget in [self.alert_list, self.speed_list, self.prediction_list, self.recommendation_list]:
            list_widget.setEnabled(True)
            list_widget.setAlternatingRowColors(True)
            list_widget.setStyleSheet("""
                QListWidget {
                    border: 1px solid gray;
                    border-radius: 5px;
                    background-color: white;
                }
                QListWidget::item:alternate {
                    background-color: #f0f0f0;
                }
            """)
        
        # System status group
        status_group = QGroupBox('System Status')
        status_layout = QVBoxLayout()
        
        # Add system status label, FPS counter, and camera status
        self.status_label = QLabel('System Status: Ready')
        self.fps_label = QLabel('FPS: 0')
        self.camera_status = QLabel('Camera Status: Not connected')
        
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: bold;
                padding: 5px;
            }
        """)
        
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.fps_label)
        status_layout.addWidget(self.camera_status)
        status_group.setLayout(status_layout)
        right_layout.addWidget(status_group)

        # Add traffic signal visualization
        signal_visual_group = QGroupBox('Traffic Signal Status')
        signal_visual_layout = QGridLayout()

        # Create signal lights
        self.signal_lights = {}
        positions = {'N': (0, 1), 'S': (2, 1), 'E': (1, 2), 'W': (1, 0)}
        
        for direction, pos in positions.items():
            light_widget = QWidget()
            light_layout = QVBoxLayout()
            
            red = QLabel()
            yellow = QLabel()
            green = QLabel()
            
            for light in (red, yellow, green):
                light.setFixedSize(30, 30)
                light.setStyleSheet('background-color: gray; border-radius: 15px;')
                light_layout.addWidget(light)
                
            light_widget.setLayout(light_layout)
            signal_visual_layout.addWidget(light_widget, *pos)
            
            self.signal_lights[direction] = {
                'red': red,
                'yellow': yellow,
                'green': green
            }
            
        signal_visual_group.setLayout(signal_visual_layout)
        right_layout.addWidget(signal_visual_group)

    def update_video_feed(self, frame, camera_index=0):
        """Update video feed for specific camera"""
        if 0 <= camera_index < len(self.video_labels):
            height, width, channel = frame.shape
            bytes_per_line = 3 * width
            q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
            self.video_labels[camera_index].setPixmap(QPixmap.fromImage(q_image))
        
    def update_vehicle_count(self, vehicle_type):
        self.vehicle_count[vehicle_type] += 1
        self.vehicle_labels[vehicle_type].setText(f'{vehicle_type.title()}s: {self.vehicle_count[vehicle_type]}')
        self.total_vehicles += 1
        self.update_total_density()
        
    def add_alert(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        alert_item = QListWidgetItem(f"[{timestamp}] {message}")
        
        # Color code alerts based on content
        if "Error" in message or "High" in message:
            alert_item.setForeground(Qt.red)
        elif "Warning" in message or "Medium" in message:
            alert_item.setForeground(Qt.darkYellow)
        else:
            alert_item.setForeground(Qt.darkGreen)
            
        self.alert_list.insertItem(0, alert_item)
        
        # Limit number of alerts
        while self.alert_list.count() > 100:
            self.alert_list.takeItem(self.alert_list.count() - 1)
        
    def update_density(self, density_value):
        self.density_progress.setValue(density_value)
        if density_value > 80:
            self.density_label.setText("Traffic Density: High")
        elif density_value > 40:
            self.density_label.setText("Traffic Density: Medium")
        else:
            self.density_label.setText("Traffic Density: Low")
            
        # Add gradient colors to density bar
        if density_value > 80:
            color = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff0000, stop:1 #cc0000)"
        elif density_value > 40:
            color = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ffff00, stop:1 #cccc00)"
        else:
            color = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00ff00, stop:1 #00cc00)"
            
        self.density_progress.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
                color: white;
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background: {color};
                border-radius: 3px;
            }}
        """)
            
    def upload_video(self, camera_index):
        file_name, _ = QFileDialog.getOpenFileName(
            self, f"Open Video File for Camera {camera_index+1}", "", 
            "Video Files (*.mp4 *.avi *.mkv *.mov);;All Files (*.*)"
        )
        
        if file_name:
            self.video_paths[camera_index] = file_name
            self.add_alert(f"Video loaded for Camera {camera_index+1}: {file_name.split('/')[-1]}")
            
    def update_frame(self):
        """Update all active camera feeds"""
        for i, camera in enumerate(self.cameras):
            if camera is not None:
                ret, frame = camera.read()
                if ret:
                    # Process frame
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = frame.shape
                    scale = min(400/w, 300/h)
                    new_w, new_h = int(w * scale), int(h * scale)
                    frame = cv2.resize(frame, (new_w, new_h))
                    
                    self.current_frame[i] = frame
                    
                    # Update video label
                    bytes_per_line = ch * new_w
                    qt_image = QImage(frame.data, new_w, new_h, bytes_per_line, QImage.Format_RGB888)
                    self.video_labels[i].setPixmap(QPixmap.fromImage(qt_image))
                    
                    self.last_frame_times[i] = datetime.now()
                    self.update_system_status(i, True)
                    
                    # Update traffic densities for both directions
                    total_vehicles_in_frame = len(self.current_vehicles)
                    if total_vehicles_in_frame > 0:
                        # Split frame into NS and EW regions and count vehicles
                        frame_height = frame.shape[0]
                        ns_vehicles = len([v for v in self.current_vehicles if v['bbox'][1] < frame_height/2])
                        ew_vehicles = total_vehicles_in_frame - ns_vehicles
                        
                        # Update traffic signal densities
                        self.traffic_signal.update_traffic_density('NS', ns_vehicles)
                        self.traffic_signal.update_traffic_density('EW', ew_vehicles)
                        
                        # Add traffic data point for prediction
                        self.traffic_predictor.add_data_point(
                            datetime.now(),
                            total_vehicles_in_frame,
                            max(ns_vehicles, ew_vehicles),
                            'NS' if ns_vehicles > ew_vehicles else 'EW'
                        )
                        
                        # Train model periodically
                        if len(self.traffic_predictor.historical_data['time']) % 100 == 0:
                            self.traffic_predictor.train_model()
                else:
                    # Handle frame read failure
                    if self.video_paths[i]:  # Reset video if it's a file
                        camera.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    self.update_system_status(i, False)

        # Update intersection traffic counts
        for i, frame in enumerate(self.current_frame):
            if frame is not None:
                frame_height = frame.shape[0]
                vehicles_in_frame = [v for v in self.current_vehicles if v.get('camera_index', 0) == i]
                
                ns_count = len([v for v in vehicles_in_frame if v['bbox'][1] < frame_height/2])
                ew_count = len(vehicles_in_frame) - ns_count
                
                self.traffic_signal.update_intersection_density(i+1, ns_count, ew_count)
        
        # Update traffic signal displays
        self.update_traffic_signals()
        
        # Update camera status indicators with new colors
        for i, camera in enumerate(self.cameras):
            if camera is not None and camera.isOpened():
                self.camera_status_indicators[i].setStyleSheet("color: #4CAF50; font-size: 20px;")  # Green
            else:
                self.camera_status_indicators[i].setStyleSheet("color: #ff4444; font-size: 20px;")  # Red

    def get_current_frame(self, camera_index=0):
        """Get current frame from specified camera"""
        return self.current_frame[camera_index]

    def closeEvent(self, event):
        """Clean up all camera resources"""
        for camera in self.cameras:
            if camera is not None:
                camera.release()
        event.accept()
        
    def toggle_recording(self, camera_index):
        """Modified to handle recording per camera"""
        record_btn = self.record_buttons[camera_index]
        if record_btn.text() == "Record":
            record_btn.setText("Stop Recording")
            self.add_alert(f"Recording started for Camera {camera_index + 1}")
        else:
            record_btn.setText("Record")
            self.add_alert(f"Recording stopped for Camera {camera_index + 1}")
            
    def update_stats(self):
        # Update FPS
        self.fps_label.setText(f"FPS: {np.random.randint(25, 31)}")  # Example FPS update

    def set_current_vehicles(self, vehicles):
        """Update the current detected vehicles"""
        self.current_vehicles = vehicles

    def update_speed(self, vehicle_id, vehicle_class, speed):
        """Update speed information in UI"""
        speed_text = f"{vehicle_class}: {speed:.1f} km/h"
        
        # Add or update speed in list
        found = False
        for i in range(self.speed_list.count()):
            item = self.speed_list.item(i)
            if item.text().startswith(f"{vehicle_id}:"):
                item.setText(f"{vehicle_id}: {speed_text}")
                found = True
                break
                
        if not found:
            self.speed_list.addItem(f"{vehicle_id}: {speed_text}")
            
        # Remove old entries
        while self.speed_list.count() > 10:
            self.speed_list.takeItem(self.speed_list.count() - 1)
            
        # Add alert for speeding
        if speed > 60:  # Customizable speed limit
            self.add_alert(f"Speeding detected! {speed_text}")
            
        # Enhanced speed alert styling
        if speed > 60:
            alert_item = QListWidgetItem(f"⚠️ Speeding: {speed_text}")
            alert_item.setForeground(Qt.red)
            self.alert_list.insertItem(0, alert_item)
            
    def update_traffic_signal(self):
        """Update traffic signal display and control"""
        try:
            # Get global traffic state
            state = self.traffic_signal.get_current_state()
            
            # Update all intersections
            for i in range(4):
                intersection_state = self.traffic_signal.get_intersection_state(i+1)
                controls = self.intersection_controls[i]
                
                # Update signal displays
                if intersection_state['current_phase'] == 'NS':
                    controls['ns_light'].setText(f'North-South: GREEN ({intersection_state["time_elapsed"]:.1f}s)')
                    controls['ew_light'].setText('East-West: RED')
                else:
                    controls['ns_light'].setText('North-South: RED')
                    controls['ew_light'].setText(f'East-West: GREEN ({intersection_state["time_elapsed"]:.1f}s)')
                
                # Update traffic counts and density
                ns_count = intersection_state['vehicle_counts']['NS']
                ew_count = intersection_state['vehicle_counts']['EW']
                total_count = max(1, ns_count + ew_count)
                
                # Calculate and update density percentages
                ns_density = int((ns_count/total_count) * 100)
                ew_density = int((ew_count/total_count) * 100)
                
                controls['ns_density'].setValue(ns_density)
                controls['ew_density'].setValue(ew_density)
                
                # Update density bar styles
                controls['ns_density'].setStyleSheet(self.get_congestion_style(ns_density))
                controls['ew_density'].setStyleSheet(self.get_congestion_style(ew_density))
                
                # Check for phase switches
                if self.traffic_signal.should_switch_phase(i+1):
                    new_phase = self.traffic_signal.switch_intersection_phase(i+1)
                    self.add_alert(f"Intersection {i+1}: Switching to {new_phase} phase")
                    
        except Exception as e:
            print(f"Error updating traffic signals: {str(e)}")
            self.add_alert("Error updating traffic signals")
            
    def get_congestion_style(self, congestion):
        """Get progress bar style based on congestion level"""
        if congestion > 80:
            color = "red"
        elif congestion > 40:
            color = "yellow"
        else:
            color = "green"
            
        return f"""
            QProgressBar {{
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {color};
            }}
        """

    def toggle_all_monitoring(self):
        """Toggle monitoring for all cameras"""
        if not self.is_all_monitoring:
            self.total_vehicles = 0  # Reset vehicle count when starting monitoring
            # Start all cameras
            success = True
            for i in range(4):
                try:
                    if self.video_paths[i]:
                        self.cameras[i] = cv2.VideoCapture(self.video_paths[i])
                    else:
                        self.cameras[i] = cv2.VideoCapture(i)
                        
                    if not self.cameras[i].isOpened():
                        raise Exception(f"Could not open video source for Camera {i+1}")
                        
                except Exception as e:
                    self.add_alert(f"Error starting camera {i+1}: {str(e)}")
                    success = False
                    
            if success:
                self.is_all_monitoring = True
                self.master_start_btn.setText("Stop All Cameras")
                self.master_start_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #f44336;
                        color: white;
                        font-size: 14px;
                        padding: 8px;
                        min-width: 120px;
                    }
                    QPushButton:hover {
                        background-color: #da190b;
                    }
                """)
                self.capture_timer.start()
                self.add_alert("Started monitoring all cameras")
        else:
            # Stop all cameras
            for i in range(4):
                if self.cameras[i] is not None:
                    self.cameras[i].release()
                    self.cameras[i] = None
                    self.current_frame[i] = None
                    
            self.is_all_monitoring = False
            self.master_start_btn.setText("Start All Cameras")
            self.master_start_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    font-size: 14px;
                    padding: 8px;
                    min-width: 120px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
            self.capture_timer.stop()
            self.add_alert("Stopped monitoring all cameras")
            
    def update_total_density(self):
        """Update overall traffic density based on total vehicles"""
        try:
            total_active_cameras = sum(1 for camera in self.cameras if camera is not None)
            if total_active_cameras > 0:
                # Calculate density as percentage of maximum expected vehicles (20 per camera)
                density_value = min(100, (self.total_vehicles / (20 * total_active_cameras)) * 100)
                
                # Update progress bar
                self.density_progress.setValue(int(density_value))
                
                # Update label and style based on density
                if density_value > 80:
                    self.density_label.setText("Traffic Density: High")
                    self.density_progress.setStyleSheet("""
                        QProgressBar::chunk { background-color: red; }
                        QProgressBar { text-align: center; }
                    """)
                elif density_value > 40:
                    self.density_label.setText("Traffic Density: Medium")
                    self.density_progress.setStyleSheet("""
                        QProgressBar::chunk { background-color: yellow; }
                        QProgressBar { text-align: center; }
                    """)
                else:
                    self.density_label.setText("Traffic Density: Low")
                    self.density_progress.setStyleSheet("""
                        QProgressBar::chunk { background-color: green; }
                        QProgressBar { text-align: center; }
                    """)
                
                # Add alert for high density
                if density_value > 80:
                    self.add_alert(f"High traffic density detected: {density_value:.1f}%")
        except Exception as e:
            print(f"Error updating density: {str(e)}")
            
    def update_predictions(self):
        """Update traffic predictions"""
        try:
            current_time = datetime.now()
            self.prediction_time.setText(f'Last Update: {current_time.strftime("%H:%M:%S")}')
            
            # Get predictions for next 15 minutes
            ns_predictions = self.traffic_predictor.predict_traffic(current_time, 'NS')
            ew_predictions = self.traffic_predictor.predict_traffic(current_time, 'EW')
            
            # Clear and update prediction display
            self.prediction_list.clear()
            
            if not self.traffic_predictor.is_model_trained:
                self.prediction_list.addItem("Training prediction model...")
                item = QListWidgetItem(f"Collecting data: {len(self.traffic_predictor.historical_data['time'])}/100")
                item.setForeground(Qt.blue)
                self.prediction_list.addItem(item)
                return
            
            # Add header
            header = QListWidgetItem("Predicted Traffic Volumes")
            header.setForeground(Qt.blue)
            header.setFont(QFont("Arial", 10, QFont.Bold))
            self.prediction_list.addItem(header)
            
            # Add predictions with color coding
            for i, (ns_pred, ew_pred) in enumerate(zip(ns_predictions, ew_predictions)):
                time_str = ns_pred['time'].strftime('%H:%M')
                
                # Format prediction text
                pred_text = (f"{time_str} | NS: {ns_pred['predicted_vehicles']} vehicles "
                           f"({ns_pred['congestion_risk']}) | "
                           f"EW: {ew_pred['predicted_vehicles']} vehicles "
                           f"({ew_pred['congestion_risk']})")
                
                item = QListWidgetItem(pred_text)
                
                # Color code based on highest congestion risk
                max_risk = max(ns_pred['congestion_risk'], ew_pred['congestion_risk'])
                if max_risk == 'High':
                    item.setForeground(Qt.red)
                elif max_risk == 'Medium':
                    item.setForeground(Qt.darkYellow)
                else:
                    item.setForeground(Qt.darkGreen)
                    
                self.prediction_list.addItem(item)
            
            # Update recommendations
            self.recommendation_list.clear()
            recommendations = self.traffic_predictor.get_recommendations(ns_predictions + ew_predictions)
            
            for rec in recommendations:
                item = QListWidgetItem(f"➤ {rec}")
                item.setForeground(Qt.blue)
                self.recommendation_list.addItem(item)
                
        except Exception as e:
            print(f"Prediction update error: {str(e)}")
            self.add_alert(f"Error updating predictions: {str(e)}")
            
    def update_traffic_signals(self):
        """Update all traffic signal displays"""
        try:
            for i in range(4):
                intersection_state = self.traffic_signal.get_intersection_state(i+1)
                controls = self.intersection_controls[i]
                
                # Update signal displays with colors
                if intersection_state['current_phase'] == 'NS':
                    controls['ns_light'].setText(f'North-South: GREEN ({intersection_state["time_elapsed"]:.1f}s)')
                    controls['ew_light'].setText('East-West: RED')
                else:
                    controls['ns_light'].setText('North-South: RED')
                    controls['ew_light'].setText(f'East-West: GREEN ({intersection_state["time_elapsed"]:.1f}s)')
                
                # Update traffic counts and density
                ns_count = intersection_state['vehicle_count'] if intersection_state['current_phase'] == 'NS' else 0
                ew_count = intersection_state['vehicle_count'] if intersection_state['current_phase'] == 'EW' else 0
                total_count = max(1, ns_count + ew_count)
                
                # Calculate and update density percentages
                ns_density = int((ns_count / total_count) * 100)
                ew_density = int((ew_count / total_count) * 100)
                
                controls['ns_density'].setValue(ns_density)
                controls['ew_density'].setValue(ew_density)
                
                # Update density bar styles
                controls['ns_density'].setStyleSheet(self.get_congestion_style(ns_density))
                controls['ew_density'].setStyleSheet(self.get_congestion_style(ew_density))
                
                # Check for phase switches
                if self.traffic_signal.should_switch_phase():
                    new_phase = self.traffic_signal.switch_phase()
                    self.add_alert(f"Intersection {i+1}: Switching to {new_phase} phase")
                    
            states = self.traffic_signal.get_current_states()
            
            for direction, lights in self.signal_lights.items():
                state = states[direction]
                
                # Reset all lights
                lights['red'].setStyleSheet('background-color: gray; border-radius: 15px;')
                lights['yellow'].setStyleSheet('background-color: gray; border-radius: 15px;')
                lights['green'].setStyleSheet('background-color: gray; border-radius: 15px;')
                
                # Light up current state
                if state['state'] == 'RED':
                    lights['red'].setStyleSheet('background-color: red; border-radius: 15px;')
                elif state['state'] == 'YELLOW':
                    lights['yellow'].setStyleSheet('background-color: yellow; border-radius: 15px;')
                elif state['state'] == 'GREEN':
                    lights['green'].setStyleSheet('background-color: green; border-radius: 15px;')
                    
            # Update timing information
            phase_info = self.traffic_signal.get_current_state()
            self.phase_time.setText(
                f"Phase Time: {phase_info['time_elapsed']:.1f}s\n"
                f"Optimal Time: {phase_info['optimal_time']:.1f}s"
            )
            
        except Exception as e:
            self.add_alert(f"Error updating signals: {str(e)}")

    def calculate_fps(self):
        """Calculate and update FPS for each camera"""
        current_time = datetime.now()
        for i in range(4):
            if self.cameras[i] is not None:
                time_diff = (current_time - self.last_frame_times[i]).total_seconds()
                if time_diff > 0:
                    fps = 1.0 / time_diff
                    self.fps_label.setText(f"FPS: {fps:.1f}")
                self.last_frame_times[i] = current_time

    def update_system_status(self, camera_index, is_active):
        """Update system status indicators"""
        status = "Active" if is_active else "Inactive"
        self.camera_status.setText(f"Camera {camera_index + 1}: {status}")
        self.camera_status.setStyleSheet(f"color: {'green' if is_active else 'red'}")
        
        # Update overall system status
        active_cameras = sum(1 for cam in self.cameras if cam is not None and cam.isOpened())
        if active_cameras > 0:
            status_text = f"System Status: Running ({active_cameras} cameras active)"
            status_color = "green"
        else:
            status_text = "System Status: Idle"
            status_color = "orange"
            
        self.status_label.setText(status_text)
        self.status_label.setStyleSheet(f"color: {status_color}; font-weight: bold;")