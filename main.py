import cv2
import numpy as np
from ultralytics import YOLO
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from ui_manager import TrafficUI
from datetime import datetime

class TrafficMonitoringSystem:
    def __init__(self):
        self.model = YOLO('yolov8n.pt')
        self.classes = self.model.names
        self.ui = None
        self.current_video_paths = [None] * 4
        self.last_frame_time = None
        self.tracked_vehicles = {}
        
    def process_frame(self, frame, camera_index=0):
        if frame is None:
            return [], None
            
        current_time = datetime.now()
        results = self.model(frame)[0]
        vehicles = []
        
        # Fix results processing
        if hasattr(results.boxes, 'data') and len(results.boxes.data) > 0:
            for result in results.boxes.data.tolist():
                if len(result) >= 6:  # Ensure we have all required values
                    x1, y1, x2, y2, score, class_id = result
                    if score > 0.5 and int(class_id) in [2, 3, 5, 7]:  # car, motorcycle, bus, truck
                        bbox = (int(x1), int(y1), int(x2), int(y2))
                        vehicle_class = self.classes[int(class_id)]
                        
                        # Calculate speed and create vehicle object
                        if vehicle_class in self.tracked_vehicles:
                            vehicle_id = self.tracked_vehicles[vehicle_class]
                        else:
                            vehicle_id = len(self.tracked_vehicles)
                            self.tracked_vehicles[vehicle_class] = vehicle_id
                        
                        speed = self.ui.speed_detector.calculate_speed(bbox, vehicle_id, current_time)
                        
                        # Draw detection box and label
                        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                        label = f"{vehicle_class}: {speed:.1f} km/h"
                        cv2.putText(frame, label, (int(x1), int(y1)-10), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                        
                        # Add vehicle to tracking
                        vehicles.append({
                            'bbox': bbox,
                            'class': vehicle_class,
                            'speed': speed,
                            'id': vehicle_id,
                            'position': 'NS' if y1 < frame.shape[0]/2 else 'EW'
                        })
        
        # Update UI with detected vehicles
        self.ui.set_current_vehicles(vehicles)
        
        return vehicles, frame

    def set_video_source(self, video_path):
        self.current_video_path = video_path
        
    def run(self):
        app = QApplication([])
        self.ui = TrafficUI()
        
        # Process all camera feeds
        def process_all_cameras():
            for i in range(4):
                frame = self.ui.get_current_frame(i)
                if frame is not None:
                    vehicles, processed_frame = self.process_frame(frame, i)
                    if processed_frame is not None:
                        self.ui.update_video_feed(processed_frame, i)  # Add camera index
                        # Update vehicle counts and traffic data
                        for vehicle in vehicles:
                            self.ui.update_vehicle_count(vehicle['class'].lower())
        
        self.ui.capture_timer.timeout.connect(process_all_cameras)
        
        self.ui.show()
        return app.exec_()

if __name__ == "__main__":
    system = TrafficMonitoringSystem()
    system.run()
