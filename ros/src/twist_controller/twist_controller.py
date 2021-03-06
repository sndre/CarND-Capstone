from datetime import datetime

from pid import PID
from lowpass import LowPassFilter
from twist_controller_logger import TwistControllerLogger

GAS_DENSITY = 2.858
ONE_MPH = 0.44704


class TwistController(object):
    def __init__(self, yaw_controller, max_steer_angle, sample_rate):
        self.yaw_controller = yaw_controller
        self.sample_rate = sample_rate

        self.throttle_pid_ctrl = PID(kp=0.2, ki=0.005, kd=0.1, mn=0.0, mx=1.0)
        self.brake_pid_ctrl = PID(kp=100.0, ki=0.001, kd=0.1, mn=0.1, mx=2000)
        self.steer_pid_ctrl = PID(kp=0.7, ki=0.004, kd=0.3, mn=-max_steer_angle, mx=max_steer_angle) # sometimes leaves lane
        # self.steer_pid_ctrl = PID(kp=1.0, ki=0.001, kd=0.5, mn=-max_steer_angle, mx=max_steer_angle) # more jiggle, but mostly stays inside the lane

        self.steer_filter = LowPassFilter(tau=1.50, ts=1.0)

        self.logger = TwistControllerLogger(self, rate=1)

    def control(self, target_linear_velocity, target_angular_velocity,
                current_linear_velocity, cte):

        linear_cte = target_linear_velocity - current_linear_velocity

        # helps brake faster
        if linear_cte < -1.0:
            self.throttle_pid_ctrl.error_integral = 0

        throttle = self.throttle_pid_ctrl.step(linear_cte, self.sample_rate)
        brake = None

        if throttle > 0:
            self.brake_pid_ctrl.reset()
        else:
            throttle = None
            self.throttle_pid_ctrl.reset()
            brake = self.brake_pid_ctrl.step(-linear_cte, self.sample_rate)

        angular_cte = cte
        steer = self.steer_pid_ctrl.step(angular_cte, self.sample_rate)
        steer_filtered = self.steer_filter.filt(steer)

        steering = self.yaw_controller.get_steering(target_linear_velocity, target_angular_velocity,
                                                    current_linear_velocity)

        self.logger.log(steer, steer_filtered, steering, current_linear_velocity,
                        target_linear_velocity, throttle, brake)

        steer = steering + steer_filtered

        return throttle, brake, steer

    def reset(self):
        self.throttle_pid_ctrl.reset()
        self.steer_pid_ctrl.reset()
