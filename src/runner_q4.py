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
    """Official Q4 submission baseline: ``v_nofar`` origin+8×995+12×1865."""
    return HuntPolicy(
        bot,
        directional=True,
        q4_dynamic_outer=False,
        q4_profile="dynamic_pure",
        target_n=target_n,
        q4_enter_omni=q4_omni_n,
        q4_enter_dir=q4_dir_n,
    ).run(do_enter=do_enter)


def run_q4_spiral(
    bot: RobotClient,
    target_n: int | None = None,
    *,
    do_enter: bool = True,
    q4_omni_n: int | None = None,
    q4_dir_n: int | None = None,
) -> dict:
    """Experimental Q4: Archimedean spiral to 1865 m then one outer lap."""
    return HuntPolicy(
        bot,
        directional=True,
        q4_dynamic_outer=False,
        q4_profile="dynamic_pure",
        q4_route="spiral",
        target_n=target_n,
        q4_enter_omni=q4_omni_n,
        q4_enter_dir=q4_dir_n,
    ).run(do_enter=do_enter)


def run_q4_bounce(
    bot: RobotClient,
    target_n: int | None = None,
    *,
    do_enter: bool = True,
    q4_omni_n: int | None = None,
    q4_dir_n: int | None = None,
) -> dict:
    """Experimental Q4: ping-pong between inner 8×995 and outer 12×1865."""
    return HuntPolicy(
        bot,
        directional=True,
        q4_dynamic_outer=False,
        q4_profile="dynamic_pure",
        q4_route="bounce",
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
    """Experimental Q4: dynamic outer (dir=0 → skip else 12×1865) + v2 locate."""
    return HuntPolicy(
        bot,
        directional=True,
        q4_dynamic_outer=True,
        q4_profile="v2",
        target_n=target_n,
        q4_enter_omni=q4_omni_n,
        q4_enter_dir=q4_dir_n,
    ).run(do_enter=do_enter)
