"""Problem 4 runner: mixed omni/directional hunt."""

from __future__ import annotations

from policy import HuntPolicy
from robot_client import RobotClient


def run_q4(
    bot: RobotClient,
    target_n: int | None = None,
    *,
    do_enter: bool = True,
    q4_omni_n: int | None = None,
    q4_dir_n: int | None = None,
) -> dict:
    """Official Q4 submission baseline: ``v_nofar`` fixed 12×2100 cover path."""
    return HuntPolicy(
        bot,
        directional=True,
        q4_dynamic_outer=False,
        q4_profile="dynamic_pure",
        target_n=target_n,
        q4_enter_omni=q4_omni_n,
        q4_enter_dir=q4_dir_n,
    ).run(do_enter=do_enter)


def run_q4_pathopt(
    bot: RobotClient,
    target_n: int | None = None,
    *,
    do_enter: bool = True,
    q4_omni_n: int | None = None,
    q4_dir_n: int | None = None,
) -> dict:
    """Experimental Q4 path-time profile: sector-fused cover, deferred clear, greedy probes."""
    return HuntPolicy(
        bot,
        directional=True,
        q4_dynamic_outer=False,
        q4_profile="dynamic_pure",
        q4_path_profile="pathopt",
        target_n=target_n,
        q4_enter_omni=q4_omni_n,
        q4_enter_dir=q4_dir_n,
    ).run(do_enter=do_enter)


def run_q4_v2(
    bot: RobotClient,
    target_n: int | None = None,
    *,
    do_enter: bool = True,
    q4_omni_n: int | None = None,
    q4_dir_n: int | None = None,
) -> dict:
    """Experimental Q4: dynamic outer ring (dir≥8 → 12×2100 else 11×1900) + v2 locate."""
    return HuntPolicy(
        bot,
        directional=True,
        q4_dynamic_outer=True,
        q4_profile="v2",
        target_n=target_n,
        q4_enter_omni=q4_omni_n,
        q4_enter_dir=q4_dir_n,
    ).run(do_enter=do_enter)
