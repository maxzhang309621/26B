"""Problem 3 runner: omnidirectional hunt on a RobotClient environment."""

from __future__ import annotations

from policy import HuntPolicy
from robot_client import RobotClient


def run_q3(bot: RobotClient) -> dict:
    return HuntPolicy(bot, directional=False).run()
