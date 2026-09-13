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
    use_dir_corrector: bool | None = True,
) -> dict:
    """Default Q4: hexbatch + dir corrector + cover-phase cheap enroute clears."""
    return HuntPolicy(
        bot,
        directional=True,
        q4_dynamic_outer=False,
        q4_profile="dynamic_pure",
        q4_path_profile="hexbatch",
        target_n=target_n,
        q4_enter_omni=q4_omni_n,
        q4_enter_dir=q4_dir_n,
        use_dir_corrector=use_dir_corrector,
    ).run(do_enter=do_enter)


def run_q4_hexbatch(
    bot: RobotClient,
    target_n: int | None = None,
    *,
    do_enter: bool = True,
    q4_omni_n: int | None = None,
    q4_dir_n: int | None = None,
    use_dir_corrector: bool | None = True,
) -> dict:
    """Alias of ``run_q4`` (hexbatch is the default)."""
    return run_q4(
        bot,
        target_n=target_n,
        do_enter=do_enter,
        q4_omni_n=q4_omni_n,
        q4_dir_n=q4_dir_n,
        use_dir_corrector=use_dir_corrector,
    )


def run_q4_nofar(
    bot: RobotClient,
    target_n: int | None = None,
    *,
    do_enter: bool = True,
    q4_omni_n: int | None = None,
    q4_dir_n: int | None = None,
) -> dict:
    """Legacy Q4: ``v_nofar`` origin + 8×1200 + 12×2100, clear as soon as heard."""
    return HuntPolicy(
        bot,
        directional=True,
        q4_dynamic_outer=False,
        q4_profile="dynamic_pure",
        q4_path_profile="v_nofar",
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
    """Experimental Q4: interleaved inner/outer cover, clear as soon as heard."""
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
