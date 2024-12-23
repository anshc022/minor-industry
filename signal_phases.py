from enum import Enum
from dataclasses import dataclass
from typing import Dict, List

class SignalState(Enum):
    RED = "RED"
    YELLOW = "YELLOW"
    GREEN = "GREEN"

class PhaseType(Enum):
    NS = "NS"  # North-South
    EW = "EW"  # East-West

@dataclass
class PhaseConfig:
    states: Dict[str, SignalState]
    duration: int
    min_duration: int
    max_duration: int

class SignalPhaseManager:
    def __init__(self):
        self.yellow_duration = 3
        self.phase_patterns = {
            PhaseType.NS: PhaseConfig(
                states={
                    'N': SignalState.GREEN,
                    'S': SignalState.GREEN,
                    'E': SignalState.RED,
                    'W': SignalState.RED
                },
                duration=30,
                min_duration=10,
                max_duration=60
            ),
            PhaseType.EW: PhaseConfig(
                states={
                    'N': SignalState.RED,
                    'S': SignalState.RED,
                    'E': SignalState.GREEN,
                    'W': SignalState.GREEN
                },
                duration=30,
                min_duration=10,
                max_duration=60
            )
        }
        
    def get_transition_states(self, from_phase: PhaseType) -> Dict[str, SignalState]:
        """Get transition states (yellow lights) when changing from given phase"""
        states = {}
        current_config = self.phase_patterns[from_phase].states
        
        for direction, state in current_config.items():
            states[direction] = SignalState.YELLOW if state == SignalState.GREEN else SignalState.RED
            
        return states
        
    def get_phase_states(self, phase: PhaseType) -> Dict[str, SignalState]:
        """Get signal states for a given phase"""
        return self.phase_patterns[phase].states

    def calculate_optimal_duration(self, phase: PhaseType, traffic_density: float) -> int:
        """Calculate optimal phase duration based on traffic density"""
        base_duration = self.phase_patterns[phase].duration
        config = self.phase_patterns[phase]
        
        if traffic_density > 0.8:
            duration = base_duration * 1.5
        elif traffic_density > 0.4:
            duration = base_duration * 1.2
        else:
            duration = base_duration
            
        return min(max(duration, config.min_duration), config.max_duration)
