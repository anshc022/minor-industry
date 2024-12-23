YOLO_CONFIG = {
    'model_path': 'yolov8n.pt',
    'conf_threshold': 0.5,
    'classes_of_interest': [2, 3, 5, 7]  # car, motorcycle, bus, truck
}

UI_CONFIG = {
    'window_width': 1200,
    'window_height': 800,
    'title': 'Smart Traffic Management System'
}

VIDEO_CONFIG = {
    'source': 0,  # 0 for webcam, or path to video file
    'fps': 30,
    'resolution': (1280, 720)
}
