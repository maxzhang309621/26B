"""Problem 3 runner: omnidirectional hunt on a RobotClient environment."""

from __future__ import annotations

from policy import HuntPolicy
from robot_client import RobotClient


def run_q3(
    bot: RobotClient,
    *,
    enable_step8_clear_ready_insertion: bool = False,
) -> dict:
    """Official Q3: ring cover with opportunistic second looks and deferred clears."""
    return HuntPolicy(
        bot,
        directional=False,
        enable_step8_clear_ready_insertion=enable_step8_clear_ready_insertion,
    ).run()


def run_q3_batch(
    bot: RobotClient,
    *,
    target_n: int | None = None,
    do_enter: bool = True,
    enable_step8_clear_ready_insertion: bool = False,
) -> dict:
    """Selected Q3 practice scheme: hexagon cover, then receding-horizon batch clear."""
    return HuntPolicy(
        bot,
        directional=False,
        target_n=target_n,
        q3_path_profile="batch",
        enable_step8_clear_ready_insertion=enable_step8_clear_ready_insertion,
    ).run(do_enter=do_enter)
