import streamlit as st
from core import (
    normalize_rate,
    get_discounted_cf_by_stages,
    terminal_value_exit_multiple,
    terminal_value_perpetual,
    apply_margin_of_safety,
)

st.set_page_config(
    page_title="价值投资估值工具",
    page_icon="📈",
    layout="wide",
)

# ===================== 红色黑科技风 + 输入框白字 =====================
st.markdown(
    """
<style>
:root{
    --bg:#07070B;
    --bg2:#0E0E16;
    --card:#141420;
    --line:rgba(255,45,85,.35);
    --red:#ff2d55;
    --text:#ffffff;
    --muted:#b7bfd6;
}

/* 主背景 */
[data-testid="stAppViewContainer"]{
    background:
      radial-gradient(1200px 600px at 90% -10%, rgba(255,45,85,.20), transparent 55%),
      radial-gradient(900px 500px at -10% 20%, rgba(255,45,85,.12), transparent 45%),
      linear-gradient(180deg, var(--bg), var(--bg2));
    color: var(--text);
}

/* 顶部透明 */
[data-testid="stHeader"]{
    background: transparent;
}

/* 页面主体宽度 */
.block-container{
    max-width: 1100px;
    padding-top: 1.5rem;
}

/* 文字 */
h1, h2, h3, h4, p, label, .stMarkdown, .stCaption {
    color: #fff !important;
}

/* 输入控件统一风格 */
div[data-baseweb="input"] > div,
div[data-baseweb="select"] > div,
[data-testid="stNumberInput"] > div > div,
[data-testid="stTextInput"] > div > div {
    background: #151522 !important;
    border: 1px solid var(--line) !important;
    border-radius: 10px !important;
}

/* 焦点态 */
div[data-baseweb="input"] > div:focus-within,
div[data-baseweb="select"] > div:focus-within,
[data-testid="stNumberInput"] > div > div:focus-within,
[data-testid="stTextInput"] > div > div:focus-within {
    border-color: var(--red) !important;
    box-shadow: 0 0 0 1px var(--red), 0 0 16px rgba(255,45,85,.25) !important;
}

/* ===== 所有输入框文字改纯白 ===== */
.stTextInput input,
.stNumberInput input,
.stTextArea textarea,
.stDateInput input,
.stTimeInput input,
div[data-baseweb="input"] input {
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    caret-color: #FFFFFF !important;
}

/* 占位符 */
.stTextInput input::placeholder,
.stNumberInput input::placeholder,
.stTextArea textarea::placeholder,
div[data-baseweb="input"] input::placeholder {
    color: rgba(255,255,255,.70) !important;
    -webkit-text-fill-color: rgba(255,255,255,.70) !important;
}

/* selectbox 当前值文字 */
div[data-baseweb="select"] * {
    color: #FFFFFF !important;
}

/* radio 文本 */
[data-testid="stRadio"] label, [data-testid="stRadio"] p {
    color: #FFFFFF !important;
}

/* 按钮 */
div.stButton > button{
    width: 100%;
    color: #fff !important;
    border: 1px solid var(--red) !important;
    background: linear-gradient(90deg, #7e0d27, #bf173c, #ff2d55) !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
}
div.stButton > button:hover{
    box-shadow: 0 0 18px rgba(255,45,85,.45);
    transform: translateY(-1px);
}

/* 卡片 */
.cyber-card{
    background: linear-gradient(180deg, rgba(255,255,255,.03), rgba(255,255,255,.00)), var(--card);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 10px;
    box-shadow: inset 0 0 22px rgba(255,45,85,.08), 0 10px 24px rgba(0,0,0,.35);
}
.cyber-label{
    color: var(--muted);
    font-size: 12px;
}
.cyber-value{
    color: #fff;
    font-size: 24px;
    font-weight: 800;
    margin-top: 4px;
}

/* 分割线 */
.hr{
    height:1px;
    background: linear-gradient(90deg, transparent, rgba(255,45,85,.55), transparent);
    margin: 8px 0 16px 0;
}
</style>
""",
    unsafe_allow_html=True,
)

def card(label: str, value: str):
    st.markdown(
        f"""
        <div class="cyber-card">
            <div class="cyber-label">{label}</div>
            <div class="cyber-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ===================== 标题 =====================
st.title("📈 价值投资估值工具（N阶段可变）")
st.write("公众号：**持续加载** ｜ 小红书：**面壁者**")
st.caption("欢迎关注，持续分享价值投资相关内容。")
st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

# ===================== 公共输入（标题下方） =====================
st.markdown("### ⚙️ 参数输入")
c1, c2 = st.columns(2)

with c1:
    ocf_ps0 = st.number_input("当前每股经营性净现金流 OCF/share", value=2.0, step=0.1, format="%.4f")
    owner_cash_ratio = st.number_input("OCF折扣系数（如0.75）", value=0.75, step=0.01, format="%.4f")

with c2:
    r_input = st.number_input("折现率/期望年化回报率（支持15或0.15）", value=15.0, step=0.5, format="%.4f")
    mos_input = st.number_input("安全边际（支持30或0.30）", value=30.0, step=1.0, format="%.4f")

terminal_mode = st.radio(
    "请选择终值方式",
    options=[1, 2, 3],
    horizontal=True,
    format_func=lambda x: {
        1: "1) 退出倍数法（P/OCF）",
        2: "2) 永续增长法（Gordon终值）",
        3: "3) 纯永续增长（不分阶段）",
    }[x],
)

r = normalize_rate(r_input)
mos = normalize_rate(mos_input)

# ===================== 阶段输入（仅非纯永续） =====================
stages = []
n_stages = 0
if terminal_mode != 3:
    n_stages = int(st.number_input("增长阶段数 N（任意整数，如10）", min_value=1, value=2, step=1))
    st.markdown("#### 阶段参数")
    for i in range(1, n_stages + 1):
        col_a, col_b = st.columns(2)
        years = int(col_a.number_input(f"第{i}阶段年数", min_value=1, value=5, step=1, key=f"years_{i}"))
        g_input_stage = col_b.number_input(
            f"第{i}阶段增长率（支持8或0.08）",
            value=8.0,
            step=0.5,
            format="%.4f",
            key=f"growth_{i}",
        )
        stages.append((years, normalize_rate(g_input_stage)))

# ===================== 终值方式特有输入 =====================
exit_multiple = None
g_terminal = None
g = None

if terminal_mode == 1:
    exit_multiple = st.number_input("退出倍数 P/OCF（如12）", min_value=0.01, value=12.0, step=0.5)
elif terminal_mode == 2:
    g_terminal_input = st.number_input("终值永续增长率 g_terminal（支持3或0.03）", value=3.0, step=0.2, format="%.4f")
    g_terminal = normalize_rate(g_terminal_input)
elif terminal_mode == 3:
    g_input = st.number_input("永续增长率 g（支持3或0.03）", value=3.0, step=0.2, format="%.4f")
    g = normalize_rate(g_input)

# 参数预览卡
p1, p2, p3, p4 = st.columns(4)
with p1:
    card("折现率 r", f"{r*100:.2f}%")
with p2:
    card("安全边际 MOS", f"{mos*100:.2f}%")
with p3:
    card("OCF/share", f"{ocf_ps0:.4f}")
with p4:
    card("OCF折扣系数", f"{owner_cash_ratio:.2f}")

# ===================== 估值按钮 =====================
if st.button("🚀 开始估值"):
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

            st.subheader("✅ 估值结果（纯永续增长）")
            r1, r2 = st.columns(2)
            with r1:
                card("内在价值", f"{intrinsic:.2f} 元")
            with r2:
                card("安全边际价格", f"{buy_price:.2f} 元")

        # 模式1/2：N阶段 + 终值
        else:
            pv_cf, last_cf, total_years = get_discounted_cf_by_stages(cf0, r, stages)

            if terminal_mode == 1:
                pv_terminal = terminal_value_exit_multiple(last_cf, r, total_years, exit_multiple)
                terminal_desc = f"退出倍数法（P/OCF={exit_multiple:.2f}）"
            elif terminal_mode == 2:
                pv_terminal = terminal_value_perpetual(last_cf, r, g_terminal, total_years)
                terminal_desc = f"永续终值法（g_terminal={g_terminal*100:.2f}%）"
            else:
                raise ValueError("终值方式仅支持 1/2/3")

            intrinsic = pv_cf + pv_terminal
            buy_price = apply_margin_of_safety(intrinsic, mos)

            st.subheader(f"✅ 估值结果（N阶段增长 + 终值，N={n_stages}）")
            st.caption(f"终值方式：{terminal_desc}")

            a, b, c, d = st.columns(4)
            with a:
                card("阶段现金流现值", f"{pv_cf:.2f}")
            with b:
                card("终值现值", f"{pv_terminal:.2f}")
            with c:
                card("内在价值", f"{intrinsic:.2f} 元")
            with d:
                card("安全边际价格", f"{buy_price:.2f} 元")

    except ValueError as e:
        st.error(f"输入或参数错误：{e}")
