# -*- coding: utf-8 -*-
"""
@Author: Haoran Yu
@Desc: 批量处理多个模式（串行，无并行）
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


MODES = [
    "ACCESS-CM2", "ACCESS-ESM1-5", "AWI-CM-1-1-MR",
    "CanESM5", "CESM2", "CNRM-CM6-1",
    "EC-Earth3-Veg", "FGOALS-g3", "IITM-ESM", "INM-CM4-8", "INM-CM5-0",
    "KACE-1-0-G", "KIOST-ESM", "MPI-ESM1-2-HR", "MRI-ESM2-0",
    "NESM3", "NorESM2-LM", "NorESM2-MM", "TaiESM1",
]

SCENARIOS = ["ssp126", "ssp245", "ssp585"]

THIS_DIR = Path(__file__).resolve().parent
SCRIPT_PATH = THIS_DIR / "3计算模式数据强度和降水变率.py"


def run_one_mode(mode: str) -> int:
    """执行单个模式计算。

    参数:
        mode: 模式名称。

    返回:
        子进程退出码，0 表示成功。
    """
    cmd = [
        sys.executable,
        str(SCRIPT_PATH),
        "--mode",
        mode,
        "--scenarios",
        *SCENARIOS,
    ]
    result = subprocess.run(cmd, cwd=str(THIS_DIR))
    return result.returncode


def main() -> None:
    """批量执行入口。

    参数:
        无。

    返回:
        无。
    """
    if not SCRIPT_PATH.exists():
        raise FileNotFoundError(f"未找到脚本: {SCRIPT_PATH}")

    print(f"待处理模式数量: {len(MODES)}")
    failed_modes = []

    for mode in MODES:
        print(f"\n===== 开始处理模式: {mode} =====")
        code = run_one_mode(mode)
        if code != 0:
            print(f"[ERROR] 模式 {mode} 处理失败，退出码: {code}")
            failed_modes.append(mode)
        else:
            print(f"[DONE] 模式 {mode} 处理完成")

    print("\n批处理结束")
    print(f"成功: {len(MODES) - len(failed_modes)} / {len(MODES)}")

    if failed_modes:
        print("失败模式:")
        for mode in failed_modes:
            print(f"- {mode}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
