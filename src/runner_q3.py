"""Problem 3 runner: omnidirectional hunt on a RobotClient environment."""

from __future__ import annotations

from policy import HuntPolicy
from robot_client import RobotClient


def run_q3(
    bot: RobotClient,
    *,
    target_n: int | None = None,
    do_enter: bool = True,
    enable_step8_clear_ready_insertion: bool = False,
) -> dict:
    """Video-aligned Q3: hexagon cover (6×1150), search-first, then batch clear."""
    return HuntPolicy(
        bot,
        directional=False,
        target_n=target_n,
        q3_path_profile="batch",
        enable_step8_clear_ready_insertion=enable_step8_clear_ready_insertion,
    ).run(do_enter=do_enter)


def run_q3_batch(
    bot: RobotClient,
    *,
    target_n: int | None = None,
    do_enter: bool = True,
    enable_step8_clear_ready_insertion: bool = False,
) -> dict:
    """Alias of ``run_q3`` (hexagon + receding-horizon batch clear)."""
    return run_q3(
        bot,
        target_n=target_n,
        do_enter=do_enter,
        enable_step8_clear_ready_insertion=enable_step8_clear_ready_insertion,
    )


def run_q3_defer(
    bot: RobotClient,
    *,
    enable_step8_clear_ready_insertion: bool = False,
) -> dict:
    """Legacy Q3: 8×1200 ring with mid-route deferred clears."""
    return HuntPolicy(
        bot,
        directional=False,
        q3_path_profile="defer",
        enable_step8_clear_ready_insertion=enable_step8_clear_ready_insertion,
    ).run()
