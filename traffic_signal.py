from signal_phases import SignalPhaseManager, PhaseType, SignalState
import numpy as np
from datetime import datetime, timedelta

class AdaptiveTrafficSignal:
    def __init__(self):
        self.phase_manager = SignalPhaseManager()
        self.current_phase = PhaseType.NS
        self.phase_start_time = datetime.now()
        self.is_transitioning = False
        self.transition_start = None
        
        # Signal colors for UI
        self.signal_colors = {
            SignalState.RED: (255, 0, 0),
            SignalState.YELLOW: (255, 255, 0),
            SignalState.GREEN: (0, 255, 0)
        }
        
        self.vehicle_counts = {'NS': 0, 'EW': 0}
        
    def update_traffic_density(self, direction, count):
        """Update traffic count for a direction"""
        self.vehicle_counts[direction] = count
        
    def get_current_states(self):
        """Get current state of all signals"""
        if self.is_transitioning:
            states = self.phase_manager.get_transition_states(self.current_phase)
        else:
            states = self.phase_manager.get_phase_states(self.current_phase)
            
        return {
            direction: {
                'state': state.value,
                'color': self.signal_colors[state]
            }
            for direction, state in states.items()
        }
        
    def should_switch_phase(self):
        """Determine if phase should switch based on timing and traffic"""
        if self.is_transitioning:
            return (datetime.now() - self.transition_start).total_seconds() >= self.phase_manager.yellow_duration
            
        current_time = datetime.now()
        phase_duration = (current_time - self.phase_start_time).total_seconds()
        
        # Calculate traffic density for current and opposite directions
        current_direction = 'NS' if self.current_phase == PhaseType.NS else 'EW'
        opposite_direction = 'EW' if self.current_phase == PhaseType.NS else 'NS'
        
        current_density = self.vehicle_counts[current_direction]
        opposite_density = self.vehicle_counts[opposite_direction]
        
        # Get optimal duration based on traffic
        optimal_duration = self.phase_manager.calculate_optimal_duration(
            self.current_phase,
            current_density / (current_density + opposite_density) if current_density + opposite_density > 0 else 0.5
        )
        
        return phase_duration >= optimal_duration
        
    def switch_phase(self):
        """Handle phase switching with transition"""
        if self.is_transitioning:
            self.is_transitioning = False
            self.current_phase = PhaseType.EW if self.current_phase == PhaseType.NS else PhaseType.NS
            self.phase_start_time = datetime.now()
        else:
            self.is_transitioning = True
            self.transition_start = datetime.now()
        
        return self.get_current_states()
    
    def get_current_state(self):
        """Get current signal state with timing information"""
        current_time = datetime.now()
        phase_duration = (current_time - self.phase_start_time).total_seconds()
        optimal_time = self.phase_manager.calculate_optimal_duration(
            self.current_phase,
            self.vehicle_counts['NS'] / (self.vehicle_counts['NS'] + self.vehicle_counts['EW']) if self.vehicle_counts['NS'] + self.vehicle_counts['EW'] > 0 else 0.5
        )
        
        return {
            'current_phase': self.current_phase.value,
            'time_elapsed': phase_duration,
            'optimal_time': optimal_time,
            'vehicle_count': self.vehicle_counts[self.current_phase.value]
        }
    
    def get_intersection_state(self, intersection_id):
        """Get current state for specific intersection"""
        return self.get_current_state()
    
    def update_intersection_density(self, intersection_id, ns_count, ew_count):
        """Update traffic density for a specific intersection"""
        self.vehicle_counts['NS'] = ns_count
        self.vehicle_counts['EW'] = ew_count
