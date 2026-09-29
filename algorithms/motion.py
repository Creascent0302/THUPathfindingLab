"""Short-term motion prediction from public dynamics and estimated commands."""

import math
import numpy as np

from pathlab.dynamics import integrate_motion, signed_speed


class MotionEstimate:
    """Command-based short-term prediction, never simulator telemetry."""

    def __init__(self, limits):
        self.limits = limits
        self.state = np.zeros(8, dtype=float)

    @property
    def speed(self):
        return float(np.linalg.norm(self.state[3:5]))

    @property
    def signed_speed(self):
        return float(signed_speed(self.state))

    @property
    def steering(self):
        return float(self.state[5])

    def advance(self, action, duration, dt):
        # Integrate the commands we actually issued. No simulator pose, velocity,
        # or route information is available to this estimate.
        remaining = max(0.0, float(duration))
        while remaining > 1e-9:
            step = min(float(dt), remaining, 0.1)
            self.state = integrate_motion(
                self.state,
                action.steering_angle_rad,
                action.speed_mps,
                self.limits,
                step,
            )
            remaining -= step
        translation, yaw = self.state[:2].copy(), float(self.state[2])
        cosine, sine = math.cos(yaw), math.sin(yaw)
        vx, vy = self.state[3:5]
        # The next observation uses the new vehicle frame. Preserve lateral
        # momentum when changing frame; resetting vy would erase tire dynamics.
        self.state[3:5] = cosine * vx + sine * vy, -sine * vx + cosine * vy
        self.state[:3] = 0
        return translation, yaw
