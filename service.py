from dataclasses import dataclass, field
from typing import Literal, Optional, List

from core import (
    get_discounted_cf_by_stages,
    terminal_value_exit_multiple,
    terminal_value_perpetual,
    apply_margin_of_safety,
)


TerminalMode = Literal["exit_multiple", "perpetual", "pure_perpetual"]


@dataclass
class Stage:
    years: int
    growth: float  # 小数形式，比如 0.08


@dataclass
class ValuationInput:
    ocf_ps0: float
    owner_cash_ratio: float = 0.75
    discount_rate: float = 0.15
    margin_of_safety: float = 0.30
    terminal_mode: TerminalMode = "exit_multiple"
    stages: List[Stage] = field(default_factory=list)
    exit_multiple: Optional[float] = None
    terminal_growth: Optional[float] = None


@dataclass
class ValuationResult:
    cf0: float
    pv_stage_cf: float
    pv_terminal: float
    intrinsic_value: float
    buy_price: float
    total_years: int
    terminal_desc: str


def evaluate(inp: ValuationInput) -> ValuationResult:
    if inp.ocf_ps0 <= 0:
        raise ValueError("OCF/share 必须 > 0")
    if not (0 < inp.owner_cash_ratio <= 1):
        raise ValueError("OCF折扣系数应在 (0,1]")
    if inp.discount_rate <= -1:
        raise ValueError("折现率必须 > -100%")
    if not (0 <= inp.margin_of_safety < 1):
        raise ValueError("安全边际需在 [0,1)")

    cf0 = inp.ocf_ps0 * inp.owner_cash_ratio

    # 纯永续增长
    if inp.terminal_mode == "pure_perpetual":
        if inp.terminal_growth is None:
            raise ValueError("纯永续增长模式必须提供 terminal_growth")
        g = inp.terminal_growth
        r = inp.discount_rate
        if r <= g:
            raise ValueError("纯永续模型要求 r > g")

        intrinsic = cf0 * (1 + g) / (r - g)
        buy_price = apply_margin_of_safety(intrinsic, inp.margin_of_safety)

        return ValuationResult(
            cf0=cf0,
            pv_stage_cf=0.0,
            pv_terminal=intrinsic,
            intrinsic_value=intrinsic,
            buy_price=buy_price,
            total_years=0,
            terminal_desc=f"纯永续增长(g={g*100:.2f}%)",
        )

    # 非纯永续：必须有阶段
    if len(inp.stages) == 0:
        raise ValueError("N阶段模型必须提供 stages")

    stage_tuples = [(s.years, s.growth) for s in inp.stages]
    pv_cf, last_cf, total_years = get_discounted_cf_by_stages(cf0, inp.discount_rate, stage_tuples)

    if inp.terminal_mode == "exit_multiple":
        if inp.exit_multiple is None:
            raise ValueError("退出倍数法必须提供 exit_multiple")
        pv_terminal = terminal_value_exit_multiple(last_cf, inp.discount_rate, total_years, inp.exit_multiple)
        desc = f"退出倍数法(P/OCF={inp.exit_multiple:.2f})"

    elif inp.terminal_mode == "perpetual":
        if inp.terminal_growth is None:
            raise ValueError("永续终值法必须提供 terminal_growth")
        pv_terminal = terminal_value_perpetual(last_cf, inp.discount_rate, inp.terminal_growth, total_years)
        desc = f"永续终值法(g={inp.terminal_growth*100:.2f}%)"

    else:
        raise ValueError("terminal_mode 仅支持 exit_multiple/perpetual/pure_perpetual")

    intrinsic = pv_cf + pv_terminal
    buy_price = apply_margin_of_safety(intrinsic, inp.margin_of_safety)

    return ValuationResult(
        cf0=cf0,
        pv_stage_cf=pv_cf,
        pv_terminal=pv_terminal,
        intrinsic_value=intrinsic,
        buy_price=buy_price,
        total_years=total_years,
        terminal_desc=desc,
    )
