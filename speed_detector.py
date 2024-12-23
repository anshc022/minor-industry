import numpy as np
import cv2
from datetime import datetime

class SpeedDetector:
    def __init__(self, distance_calibration=10.0):  # meters per 100 pixels
        self.tracked_objects = {}
        self.distance_calibration = distance_calibration
        
    def calculate_speed(self, current_bbox, object_id, frame_time):
        """Calculate speed of object between frames"""
        if object_id not in self.tracked_objects:
            self.tracked_objects[object_id] = {
                'positions': [current_bbox],
                'times': [frame_time],
                'speed': 0
            }
            return 0
            
        # Get previous position and time
        prev_bbox = self.tracked_objects[object_id]['positions'][-1]
        prev_time = self.tracked_objects[object_id]['times'][-1]
        
        # Calculate center points
        current_center = ((current_bbox[0] + current_bbox[2])/2, (current_bbox[1] + current_bbox[3])/2)
        prev_center = ((prev_bbox[0] + prev_bbox[2])/2, (prev_bbox[1] + prev_bbox[3])/2)
        
        # Calculate distance in pixels
        distance_pixels = np.sqrt((current_center[0] - prev_center[0])**2 + 
                                (current_center[1] - prev_center[1])**2)
        
        # Convert to meters using calibration
        distance_meters = distance_pixels * (self.distance_calibration/100)
        
        # Fix time difference calculation
        try:
            time_diff = (frame_time - prev_time).total_seconds()
        except (AttributeError, TypeError):
            time_diff = 0
            
        if time_diff > 0:
            # Ensure no division by zero
            speed = distance_meters / max(time_diff, 0.001)
            # Convert to km/h
            speed_kmh = speed * 3.6
            
            # Update tracking info
            self.tracked_objects[object_id]['positions'].append(current_bbox)
            self.tracked_objects[object_id]['times'].append(frame_time)
            self.tracked_objects[object_id]['speed'] = speed_kmh
            
            return speed_kmh
        
        return 0
