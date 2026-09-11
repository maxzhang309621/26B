"""Problem 3 runner: omnidirectional hunt on a RobotClient environment."""

from __future__ import annotations

from policy import HuntPolicy
from robot_client import RobotClient


def run_q3(
    bot: RobotClient,
    *,
    enable_step8_clear_ready_insertion: bool = False,
) -> dict:
    """Run Q3; Step 8 remains opt-in for paired development evaluation."""
    return HuntPolicy(
        bot,
        directional=False,
        enable_step8_clear_ready_insertion=enable_step8_clear_ready_insertion,
    ).run()
