import streamlit as st
from core import (
    normalize_rate,
    get_discounted_cf_by_stages,
    terminal_value_exit_multiple,
    terminal_value_perpetual,
    apply_margin_of_safety,
)

st.set_page_config(page_title="股票估值分析器（OCF版）", page_icon="📈", layout="centered")
st.title("📈 股票估值分析器（OCF版，N阶段可变）")

# ===================== 公共输入 =====================
ocf_ps0 = st.number_input("当前每股经营性净现金流 OCF/share", value=2.0, step=0.1, format="%.4f")
owner_cash_ratio = st.number_input("OCF折扣系数（如0.75）", value=0.75, step=0.01, format="%.4f")
r_input = st.number_input("折现率/期望年化回报率（支持15或0.15）", value=15.0, step=0.5, format="%.4f")
mos_input = st.number_input("安全边际（支持30或0.30）", value=30.0, step=1.0, format="%.4f")

terminal_mode = st.radio(
    "请选择终值方式",
    options=[1, 2, 3],
    format_func=lambda x: {
        1: "1) 退出倍数法（P/OCF）",
        2: "2) 永续增长法（Gordon 终值）",
        3: "3) 纯永续增长（不分阶段）",
    }[x],
)

# 标准化参数（供后续使用）
r = normalize_rate(r_input)
mos = normalize_rate(mos_input)

# ===================== 阶段输入（仅非纯永续模式） =====================
if terminal_mode != 3:
    n_stages = st.number_input("增长阶段数 N（任意整数，如10）", min_value=1, value=2, step=1)
    stages = []
    st.markdown("### 阶段参数")
    for i in range(1, n_stages + 1):
        cols = st.columns(2)
        years = cols[0].number_input(f"第{i}阶段年数", min_value=1, value=5, step=1, key=f"years_{i}")
        g_input = cols[1].number_input(
            f"第{i}阶段增长率（支持8或0.08）",
            value=8.0,
            step=0.5,
            format="%.4f",
            key=f"growth_{i}",
        )
        g = normalize_rate(g_input)
        stages.append((years, g))

# ===================== 终值方式特有输入 =====================
if terminal_mode == 1:
    exit_multiple = st.number_input("退出倍数 P/OCF（如12）", min_value=0.01, value=12.0, step=0.5)
elif terminal_mode == 2:
    g_terminal_input = st.number_input("终值永续增长率 g_terminal（支持3或0.03）", value=3.0, step=0.2, format="%.4f")
    g_terminal = normalize_rate(g_terminal_input)
elif terminal_mode == 3:
    g_input = st.number_input("永续增长率 g（支持3或0.03）", value=3.0, step=0.2, format="%.4f")
    g = normalize_rate(g_input)

# ===================== 估值按钮 =====================
if st.button("开始估值"):
    try:
        if ocf_ps0 <= 0:
            st.warning("警告：OCF/share <= 0，结果参考意义有限。")
        if not (0 < owner_cash_ratio <= 1):
            raise ValueError("OCF折扣系数应在 (0,1]")

        cf0 = ocf_ps0 * owner_cash_ratio

        # 模式3：纯永续增长
        if terminal_mode == 3:
            if r <= g:
                raise ValueError("纯永续模型要求 r > g")
            intrinsic = cf0 * (1 + g) / (r - g)
            buy_price = apply_margin_of_safety(intrinsic, mos)

            st.subheader("估值结果")
            st.write("**模型**: 纯永续增长")
            st.write(f"基准 OCF/share: `{ocf_ps0:.4f}`")
            st.write(f"OCF折扣系数: `{owner_cash_ratio:.2f}`")
            st.write(f"折现基准现金流 cf0: `{cf0:.4f}`")
            st.write(f"内在价值: **{intrinsic:.2f} 元**")
            st.write(f"安全边际: `{mos*100:.1f}%`")
            st.write(f"安全边际价格: **{buy_price:.2f} 元**")

        else:
            # N阶段增长 + 终值
            pv_cf, last_cf, total_years = get_discounted_cf_by_stages(cf0, r, stages)

            if terminal_mode == 1:
                pv_terminal = terminal_value_exit_multiple(last_cf, r, total_years, exit_multiple)
                terminal_desc = f"退出倍数法(P/OCF={exit_multiple:.2f})"
            elif terminal_mode == 2:
                pv_terminal = terminal_value_perpetual(last_cf, r, g_terminal, total_years)
                terminal_desc = f"永续终值法(g={g_terminal*100:.2f}%)"
            else:
                raise ValueError("终值方式仅支持 1/2/3")

            intrinsic = pv_cf + pv_terminal
            buy_price = apply_margin_of_safety(intrinsic, mos)

            st.subheader("估值结果")
            st.write(f"**模型**: N阶段增长 + 终值（N={n_stages}）")
            st.write(f"**终值方式**: {terminal_desc}")
            st.write(f"基准 OCF/share: `{ocf_ps0:.4f}`")
            st.write(f"OCF折扣系数: `{owner_cash_ratio:.2f}`")
            st.write(f"折现基准现金流 cf0: `{cf0:.4f}`")
            st.write(f"总估值年限: `{total_years}` 年")
            st.write(f"阶段现金流现值合计: `{pv_cf:.4f}`")
            st.write(f"终值现值: `{pv_terminal:.4f}`")
            st.write(f"内在价值: **{intrinsic:.2f} 元**")
            st.write(f"安全边际: `{mos*100:.1f}%`")
            st.write(f"安全边际价格: **{buy_price:.2f} 元**")

    except ValueError as e:
        st.error(f"输入或参数错误：{e}")