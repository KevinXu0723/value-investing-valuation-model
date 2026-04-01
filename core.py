def normalize_rate(x: float) -> float:
    """兼容 5 和 0.05 两种输入，阈值改为 >=1"""
    return x / 100 if x >= 1 else x


def read_float(prompt, default=None):
    s = input(prompt).strip()
    if s == "":
        if default is None:
            raise ValueError("输入不能为空")
        return float(default)
    return float(s)


def read_int(prompt, default=None):
    s = input(prompt).strip()
    if s == "":
        if default is None:
            raise ValueError("输入不能为空")
        return int(default)
    return int(s)


def get_discounted_cf_by_stages(cf0, r, stages):
    """
    stages: [(years, growth), ...]
    返回:
      pv_cf: 各年现金流现值合计
      last_cf: 最后一年现金流
      total_years: 总年数
    """
    if r <= -1:
        raise ValueError("折现率必须 > -100%")

    pv_cf = 0.0
    cf = cf0
    t = 0

    for i, (years, g) in enumerate(stages, start=1):
        if years <= 0:
            raise ValueError(f"第{i}阶段年数必须 > 0")
        if g <= -1:
            raise ValueError(f"第{i}阶段增长率必须 > -100%")

        for _ in range(years):
            t += 1
            cf = cf * (1 + g)
            pv_cf += cf / ((1 + r) ** t)

    return pv_cf, cf, t


def terminal_value_exit_multiple(last_cf, r, n, exit_multiple):
    if exit_multiple <= 0:
        raise ValueError("退出倍数必须 > 0")
    tv = last_cf * exit_multiple
    return tv / ((1 + r) ** n)


def terminal_value_perpetual(last_cf, r, g, n):
    """
    终值发生在第 n 年末：
    TV_n = CF_(n+1)/(r-g) = last_cf*(1+g)/(r-g)
    再折现回今天
    """
    if g <= -1:
        raise ValueError("永续增长率必须 > -100%")
    if r <= g:
        raise ValueError("永续增长模型要求 r > g")
    tv_n = last_cf * (1 + g) / (r - g)
    return tv_n / ((1 + r) ** n)


def apply_margin_of_safety(value, mos):
    if not (0 <= mos < 1):
        raise ValueError("安全边际需在 [0,1) 之间")
    return value * (1 - mos)


def run_stock_analyzer():
    print("=== 股票估值分析器（OCF版，N阶段可变） ===")
    print("终值方式：")
    print("1) 退出倍数法（P/OCF）")
    print("2) 永续增长法（Gordon 终值）")
    print("3) 纯永续增长（不分阶段）")

    try:
        terminal_mode = read_int("请选择终值方式(1/2/3): ")

        ocf_ps0 = read_float("请输入当前每股经营性净现金流 OCF/share: ")
        owner_cash_ratio = read_float("请输入OCF折扣系数(如0.75): ", 0.75)
        r = normalize_rate(read_float("请输入折现率/期望年化回报率(如0.15): "))
        mos = normalize_rate(read_float("请输入安全边际(如0.30): "))

        if ocf_ps0 <= 0:
            print("警告：OCF/share <= 0，结果参考意义有限。")
        if not (0 < owner_cash_ratio <= 1):
            raise ValueError("OCF折扣系数应在 (0,1]")

        cf0 = ocf_ps0 * owner_cash_ratio

        # 纯永续：不走阶段
        if terminal_mode == 3:
            g = normalize_rate(read_float("请输入永续增长率 g (如0.03): "))
            if r <= g:
                raise ValueError("纯永续模型要求 r > g")
            intrinsic = cf0 * (1 + g) / (r - g)
            buy_price = apply_margin_of_safety(intrinsic, mos)

            print("\n========== 估值结果 ==========")
            print("模型: 纯永续增长")
            print(f"基准 OCF/share: {ocf_ps0:.4f}")
            print(f"OCF折扣系数: {owner_cash_ratio:.2f}")
            print(f"折现基准现金流 cf0: {cf0:.4f}")
            print(f"内在价值: {intrinsic:.2f}元")
            print(f"安全边际: {mos*100:.1f}%")
            print(f"安全边际价格: {buy_price:.2f}元")
            print("=============================")
            return

        # N阶段输入
        n_stages = read_int("请输入增长阶段数 N（任意整数，如10）: ")
        if n_stages <= 0:
            raise ValueError("阶段数 N 必须 > 0")

        stages = []
        print("\n请依次输入每个阶段参数：")
        for i in range(1, n_stages + 1):
            years = read_int(f"第{i}阶段年数: ")
            g = normalize_rate(read_float(f"第{i}阶段增长率(如0.08): "))
            stages.append((years, g))

        pv_cf, last_cf, total_years = get_discounted_cf_by_stages(cf0, r, stages)

        if terminal_mode == 1:
            exit_multiple = read_float("请输入退出倍数 P/OCF (如12): ")
            pv_terminal = terminal_value_exit_multiple(last_cf, r, total_years, exit_multiple)
            terminal_desc = f"退出倍数法(P/OCF={exit_multiple:.2f})"
        elif terminal_mode == 2:
            g_terminal = normalize_rate(read_float("请输入终值永续增长率 g_terminal: "))
            pv_terminal = terminal_value_perpetual(last_cf, r, g_terminal, total_years)
            terminal_desc = f"永续终值法(g={g_terminal*100:.2f}%)"
        else:
            raise ValueError("终值方式仅支持 1/2/3")

        intrinsic = pv_cf + pv_terminal
        buy_price = apply_margin_of_safety(intrinsic, mos)

        print("\n========== 估值结果 ==========")
        print(f"模型: N阶段增长 + 终值（N={n_stages}）")
        print(f"终值方式: {terminal_desc}")
        print(f"基准 OCF/share: {ocf_ps0:.4f}")
        print(f"OCF折扣系数: {owner_cash_ratio:.2f}")
        print(f"折现基准现金流 cf0: {cf0:.4f}")
        print(f"总估值年限: {total_years} 年")
        print(f"阶段现金流现值合计: {pv_cf:.4f}")
        print(f"终值现值: {pv_terminal:.4f}")
        print(f"内在价值: {intrinsic:.2f}元")
        print(f"安全边际: {mos*100:.1f}%")
        print(f"安全边际价格: {buy_price:.2f}元")
        print("=============================")

    except ValueError as e:
        print(f"输入或参数错误：{e}")


if __name__ == "__main__":
    run_stock_analyzer()