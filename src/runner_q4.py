"""Problem 4 runner: mixed omni/directional hunt."""

from __future__ import annotations

from policy import HuntPolicy
from robot_client import RobotClient


def run_q4(bot: RobotClient) -> dict:
    return HuntPolicy(bot, directional=True).run()
