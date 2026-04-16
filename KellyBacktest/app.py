"""Streamlit 메인 애플리케이션 - 전략 기반 켈리 백테스팅 엔진"""

import numpy as np
import pandas as pd
import streamlit as st

from src import backtest_engine, data_loader, db_connector, kelly_engine, metrics, signal_engine, strategy_analyzer, visualization
from config import INITIAL_CASH, RISK_FREE_RATE

st.set_page_config(page_title="켈리 백테스팅 엔진", layout="wide")

st.title("📈 켈리 백테스팅 엔진 (Strategy-Driven Kelly)")
st.markdown(
    "**전략 상태(State)를 이벤트(Event)로 변환하고, Adjusted Kelly로 최적 베팅 비중을 계산한 뒤, "
    "Next-Day Execution 원칙 하에 신호 발생 시에만 진입/청산하는 백테스팅 엔진입니다.**"
)

# ---------------------------------------------------------------------------
# 세션 상태 초기화
# ---------------------------------------------------------------------------
for key in ["prices", "state", "events", "stats", "oos_stats", "trade_returns", "oos_returns",
            "f_star", "backtest_result", "grid_result"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ---------------------------------------------------------------------------
# 사이드바
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ 설정")

    # --- 1. 데이터 선택 ---
    st.subheader("1. 데이터 선택")
    data_source = st.radio(
        "데이터 소스",
        options=["샘플 데이터", "CSV 업로드", "Docker DB (게만아-트레이딩)"],
        index=0,
    )

    prices = None
    if data_source == "샘플 데이터":
        sample_mu = st.slider("연간 기대수익률 (μ)", -0.1, 0.3, 0.1, 0.01)
        sample_sigma = st.slider("연간 변동성 (σ)", 0.05, 0.5, 0.2, 0.01)
        prices = data_loader.generate_sample_data(
            ticker="SAMPLE", mu=sample_mu, sigma=sample_sigma
        )
    elif data_source == "CSV 업로드":
        uploaded_file = st.file_uploader("CSV 파일 업로드", type=["csv"])
        if uploaded_file is not None:
            try:
                prices = data_loader.load_csv(uploaded_file, wide_form=True)
                if isinstance(prices, pd.DataFrame) and prices.shape[1] == 1:
                    prices = prices.iloc[:, 0]
                st.success("파일 업로드 성공!")
            except Exception as e:
                st.error(f"파일 로딩 실패: {e}")
        else:
            st.info("CSV 파일을 업로드해주세요.")
    else:
        if db_connector.check_connection():
            st.success("✅ Docker DB 연결 성공")
            with st.spinner("종목 목록 로딩 중..."):
                symbols_df = db_connector.get_available_symbols()
            if not symbols_df.empty:
                selected_symbol = st.selectbox(
                    "종목 선택",
                    options=symbols_df["symbol"].tolist(),
                    index=symbols_df["symbol"].tolist().index("005930") if "005930" in symbols_df["symbol"].values else 0,
                    format_func=lambda x: f"{x} ({symbols_df[symbols_df['symbol']==x]['name'].values[0]})",
                )
                col1, col2 = st.columns(2)
                with col1:
                    db_start = st.date_input("시작일", value=pd.to_datetime("2020-01-02"))
                with col2:
                    db_end = st.date_input("종료일", value=pd.to_datetime("today"))
                if selected_symbol:
                    try:
                        df = db_connector.get_prices_from_db(
                            [selected_symbol],
                            start_date=db_start.strftime("%Y-%m-%d"),
                            end_date=db_end.strftime("%Y-%m-%d"),
                        )
                        if df.empty:
                            st.warning("선택한 기간/종목에 해당하는 데이터가 없습니다.")
                        else:
                            prices = df.iloc[:, 0]
                            st.success(f"{len(prices)}일치 데이터 로드 완료")
                    except Exception as e:
                        st.error(f"DB 쿼리 실패: {e}")
            else:
                st.warning("DB에 사용 가능한 종목 데이터가 없습니다.")
        else:
            st.error(
                "❌ Docker DB 연결 실패.\n\n"
                "`trading-mysql` 컨테이너가 실행 중인지, 3307 포트가 열린지 확인하세요."
            )

    if prices is not None:
        try:
            prices = data_loader.validate_data(prices)
            st.session_state["prices"] = prices
        except Exception as e:
            st.error(f"데이터 검증 오류: {e}")
            st.session_state["prices"] = None
    else:
        st.session_state["prices"] = None

    # --- 2. 전략 선택 ---
    st.subheader("2. 전략 선택")
    strategy_name = st.selectbox(
        "전략",
        options=["golden_cross", "rsi", "momentum_breakout", "bollinger"],
        format_func=lambda x: {
            "golden_cross": "Golden Cross (이동평균선 교차)",
            "rsi": "RSI 과매수/과매도",
            "momentum_breakout": "모멘텀 돌파",
            "bollinger": "볼린저 밴드 반전",
        }.get(x, x),
    )

    strategy_kwargs = {}
    if strategy_name == "golden_cross":
        strategy_kwargs["short"] = st.slider("단기 MA", 3, 20, 5, 1)
        strategy_kwargs["long"] = st.slider("장기 MA", 10, 60, 20, 5)
    elif strategy_name == "rsi":
        strategy_kwargs["period"] = st.slider("RSI 기간", 5, 30, 14, 1)
        strategy_kwargs["oversold"] = st.slider("과매도 임계값", 10, 40, 30, 5)
        strategy_kwargs["overbought"] = st.slider("과매수 임계값", 60, 90, 70, 5)
    elif strategy_name == "momentum_breakout":
        strategy_kwargs["lookback"] = st.slider("돌파 기간", 5, 60, 20, 5)
    else:  # bollinger
        strategy_kwargs["period"] = st.slider("볼린저 기간", 10, 40, 20, 5)
        strategy_kwargs["std"] = st.slider("표준편차 배수", 1.0, 3.0, 2.0, 0.5)

    holding_period = st.slider("보유 기간 (거래일)", 5, 60, 20, 5)
    direction = st.radio("포지션 방향", options=["long", "short"], index=0, format_func=lambda x: "롱 (매수)" if x == "long" else "숏 (공매도)")
    exit_on_opposite = st.checkbox("반대 신호 시 조기 청산", value=True)
    allow_renewal = st.checkbox("동일 신호 발생 시 보유 기간 연장", value=True)

    # --- OOS 설정 ---
    st.subheader("OOS 분리")
    use_oos = st.checkbox("OOS 분리 사용", value=False)
    oos_ratio = 1 - st.slider("OOS 비율", 0.0, 0.5, 0.3, 0.05)

    analyze_clicked = st.button("📊 전략 분석하기", type="primary")

    # --- 3. 켈리 설정 ---
    st.subheader("3. 켈리 설정")
    kelly_type = st.selectbox(
        "켈리 타입",
        options=["Numerical Kelly (Full)", "Half Kelly", "Custom Fraction"],
        index=1,
    )
    custom_fraction = 0.5
    if kelly_type == "Custom Fraction":
        custom_fraction = st.slider("적용 비율", 0.1, 1.0, 0.5, 0.05)

    run_clicked = st.button("🚀 백테스트 실행", type="primary", disabled=(st.session_state["stats"] is None))

# ---------------------------------------------------------------------------
# 메인 콘텐츠
# ---------------------------------------------------------------------------
if st.session_state["prices"] is None:
    st.info("👈 사이드바에서 데이터를 선택하거나 업로드해주세요.")
    st.stop()

prices = st.session_state["prices"]

# 전략 분석 실행
if analyze_clicked:
    with st.spinner("전략 신호 생성 및 통계 분석 중..."):
        state = signal_engine.get_signal(strategy_name, prices, **strategy_kwargs)
        events = strategy_analyzer.state_to_events(state, entry_state=1 if direction == "long" else -1)
        st.session_state["state"] = state
        st.session_state["events"] = events

        if use_oos:
            is_stats, f_raw, oos_returns = strategy_analyzer.analyze_with_oos(
                prices, events, split_ratio=oos_ratio, holding_period=holding_period,
                direction=direction, exit_on_opposite=exit_on_opposite, allow_renewal=allow_renewal
            )
            st.session_state["stats"] = is_stats
            st.session_state["oos_returns"] = oos_returns
            # OOS stats
            oos_stats = strategy_analyzer.compute_kelly_params(oos_returns)
            st.session_state["oos_stats"] = oos_stats
        else:
            trade_returns = strategy_analyzer.extract_signal_returns(
                prices, events, holding_period=holding_period, direction=direction,
                exit_on_opposite=exit_on_opposite, allow_renewal=allow_renewal
            )
            stats = strategy_analyzer.compute_kelly_params(trade_returns)
            st.session_state["trade_returns"] = trade_returns
            st.session_state["stats"] = stats
            st.session_state["oos_stats"] = None
            st.session_state["oos_returns"] = None
            f_raw = stats["f_star_adjusted"] if stats["valid"] else 0.0

        # 켈리 비율 계산
        if use_oos:
            f_raw = is_stats["f_star_numerical"] if is_stats["valid"] else 0.0
        else:
            f_raw = st.session_state["stats"]["f_star_numerical"] if st.session_state["stats"]["valid"] else 0.0

        if kelly_type == "Half Kelly":
            f_star = kelly_engine.fractional_kelly(f_raw, 0.5)
        elif kelly_type == "Custom Fraction":
            f_star = kelly_engine.fractional_kelly(f_raw, custom_fraction)
        else:
            f_star = max(0.0, f_raw)

        st.session_state["f_star"] = f_star

# 백테스트 실행
if run_clicked and st.session_state["stats"] is not None:
    with st.spinner("백테스팅 중..."):
        result = backtest_engine.run_strategy(
            prices,
            st.session_state["events"],
            kelly_fraction=st.session_state["f_star"],
            holding_period=holding_period,
            initial_cash=INITIAL_CASH,
            direction=direction,
            exit_on_opposite=exit_on_opposite,
            allow_renewal=allow_renewal,
        )
        st.session_state["backtest_result"] = result

# ---------------------------------------------------------------------------
# 탭 구조
# ---------------------------------------------------------------------------
tab1, tab2, tab_kelly, tab3, tab4 = st.tabs(["📈 전략 분석", "📉 백테스트 결과", "🧮 켈리 분석", "📋 성과 지표", "🔍 파라미터 최적화"])

# --- 탭 1: 전략 분석 ---
with tab1:
    if st.session_state["stats"] is None:
        st.info('"전략 분석하기" 버튼을 클릭하면 신호 통계와 켈리 비중이 표시됩니다.')
    else:
        stats = st.session_state["stats"]
        f_star = st.session_state["f_star"]
        state = st.session_state["state"]

        st.subheader("In-Sample / 전체 분석 결과")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("총 거래 횟수", f"{stats['n_trades']}회")
        with col2:
            st.metric("승률", f"{stats['win_rate']*100:.1f}%")
        with col3:
            st.metric("평균 수익", f"{stats['avg_win']*100:.2f}%")
        with col4:
            st.metric("평균 손실", f"{stats['avg_loss']*100:.2f}%")

        st.divider()

        col5, col6 = st.columns(2)
        st.plotly_chart(
            visualization.plot_price_with_signals(prices, state, title=f"{strategy_name} 상태(State) 분포"),
            use_container_width=True,
        )


# --- 켈리 분석 탭 ---
with tab_kelly:
    if st.session_state["stats"] is None:
        st.info('"전략 분석하기" 버튼을 클릭하면 켈리 분석 결과가 표시됩니다.')
    else:
        stats = st.session_state["stats"]
        f_star = st.session_state["f_star"]
        trade_returns = st.session_state.get("trade_returns") or st.session_state.get("oos_returns")

        st.subheader("📊 Numerical Kelly 분석")
        kcol1, kcol2, kcol3 = st.columns([1, 1, 2])
        with kcol1:
            if stats["valid"] and stats["f_star_numerical"] > 0:
                st.metric(
                    label="Numerical Kelly (f*)",
                    value=f"{stats['f_star_numerical']*100:.1f}%",
                    delta=f"적용 비중: {f_star*100:.1f}%" if kelly_type != "Numerical Kelly (Full)" else None,
                )
            elif stats["valid"] and stats["f_star_numerical"] <= 0:
                st.error(f"⚠️ 켈리 비중 음수 ({stats['f_star_numerical']*100:.1f}%). 이 전략은 '하지 마라'입니다.")
            else:
                st.warning(f"거래 횟수 부족 ({stats['n_trades']}회). 통계적으로 유의미하지 않습니다.")
        with kcol2:
            if stats["valid"]:
                st.metric("정규분포 근삿값", f"{stats['f_star_normal_approx']*100:.1f}%")
        with kcol3:
            st.caption("회색 값은 '정규분포 가정 시 근사값'이며, 기본 값은 Numerical 최적화 결과입니다.")

        if use_oos and st.session_state["oos_stats"] is not None:
            st.divider()
            oos_stats = st.session_state["oos_stats"]
            st.subheader("Out-of-Sample 켈리 결과")
            oos_col1, oos_col2 = st.columns(2)
            with oos_col1:
                st.metric("OOS Numerical Kelly", f"{oos_stats['f_star_numerical']*100:.1f}%")
            with oos_col2:
                st.metric("OOS 정규분포 근삿값", f"{oos_stats['f_star_normal_approx']*100:.1f}%")

        st.divider()
        st.subheader("수익률 통계 요약")
        rs = stats["return_stats"]
        rs_col1, rs_col2, rs_col3, rs_col4, rs_col5 = st.columns(5)
        with rs_col1:
            st.metric("평균", f"{rs['mean']*100:.2f}%")
        with rs_col2:
            st.metric("중앙값", f"{rs['median']*100:.2f}%")
        with rs_col3:
            st.metric("표준편차", f"{rs['std']*100:.2f}%")
        with rs_col4:
            st.metric("왜도", f"{rs['skewness']:.2f}")
        with rs_col5:
            st.metric("첨도", f"{rs['kurtosis']:.2f}")

        if trade_returns is not None and len(trade_returns) > 0:
            st.divider()
            dist_col, curve_col = st.columns(2)
            with dist_col:
                st.plotly_chart(
                    visualization.plot_trade_returns_distribution(trade_returns, title="거래별 수익률 분포"),
                    use_container_width=True,
                )
            with curve_col:
                f_vals, exp_log = kelly_engine.kelly_curve(trade_returns)
                st.plotly_chart(
                    visualization.plot_kelly_curve(f_vals, exp_log, f_star=stats["f_star_numerical"]),
                    use_container_width=True,
                )
            st.info(
                "💡 **Numerical Kelly**는 전체 거래 수익률 분포에서 $E[\\log(1+fX)]$를 직접 최적화한 값입니다. "
                "승률·평균손익비 공식과 다를 수 있으며, 분포의 꼬리와 스큐에 민감하게 반응합니다."
            )

# --- 탭 2: 백테스트 결과 ---
with tab2:
    if st.session_state["backtest_result"] is None:
        st.info('"백테스트 실행" 버튼을 클릭하면 결과가 표시됩니다.')
    else:
        result = st.session_state["backtest_result"]
        nav = result["nav"]
        buyhold = result["buyhold"]
        trade_log = result["trade_log"]
        position = result["position"]

        # 자기자본 핵심 지표
        peak = nav.cummax().iloc[-1]
        trough = nav.min()
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("최종 자본", f"{nav.iloc[-1]:,.0f} 원", delta=f"{metrics.total_return(nav)*100:.2f}%")
        with col2:
            st.metric("최고 자본 (Peak)", f"{peak:,.0f} 원")
        with col3:
            st.metric("최저 자본 (Trough)", f"{trough:,.0f} 원")
        with col4:
            st.metric("MDD", f"{metrics.max_drawdown(nav)*100:.2f}%")

        st.divider()

        # NAV 차트 컨트롤
        nav_log_scale = st.toggle("로그 스케일", value=False, key="nav_log")
        nav_show_dd = st.toggle("Drawdown 오버레이 표시", value=True, key="nav_dd")

        st.plotly_chart(
            visualization.plot_nav_comparison(nav, buyhold, log_scale=nav_log_scale, show_drawdown=nav_show_dd),
            use_container_width=True,
        )

        st.plotly_chart(
            visualization.plot_equity_growth(nav, buyhold),
            use_container_width=True,
        )

        st.plotly_chart(
            visualization.plot_position_history(position),
            use_container_width=True,
        )

        st.subheader("거래 내역")
        if not trade_log.empty:
            display_log = trade_log.copy()
            display_log["trade_return"] = display_log["trade_return"].apply(lambda x: f"{x*100:.2f}%")
            display_log["entry_price"] = display_log["entry_price"].apply(lambda x: f"{x:,.0f}")
            display_log["exit_price"] = display_log["exit_price"].apply(lambda x: f"{x:,.0f}")
            display_log["kelly_fraction"] = display_log["kelly_fraction"].apply(lambda x: f"{x*100:.1f}%")
            st.dataframe(display_log, use_container_width=True)
        else:
            st.warning("백테스트 기간 중 거래가 발생하지 않았습니다.")

# --- 탭 3: 성과 지표 ---
with tab3:
    if st.session_state["backtest_result"] is None:
        st.info('"백테스트 실행" 버튼을 클릭하면 성과 지표가 표시됩니다.')
    else:
        result = st.session_state["backtest_result"]
        nav = result["nav"]
        buyhold = result["buyhold"]

        col1, col2 = st.columns(2)
        with col1:
            report_nav = metrics.generate_report(nav, "Kelly Strategy")
            report_bh = metrics.generate_report(buyhold, "Buy & Hold")
            comparison = pd.merge(report_nav, report_bh, on="지표")
            st.dataframe(comparison, use_container_width=True)
        with col2:
            tr_pf = st.session_state.get("trade_returns")
            if tr_pf is None:
                tr_pf = st.session_state.get("oos_returns")
            if tr_pf is not None and len(tr_pf) > 0:
                report_trades = metrics.generate_trade_report(tr_pf, "Trades")
                st.dataframe(report_trades, use_container_width=True)

        st.plotly_chart(
            visualization.plot_drawdown(nav),
            use_container_width=True,
        )

        st.plotly_chart(
            visualization.plot_returns_histogram(nav, title="Kelly Strategy 일간 수익률 분포"),
            use_container_width=True,
        )

# --- 탭 4: 파라미터 최적화 ---
with tab4:
    st.subheader("🔍 Grid Search: 양수 켈리 엣지 찾기")
    st.markdown("여러 파라미터 조합을 자동으로 테스트하여 Adjusted Kelly가 양수인 조합을 찾습니다.")

    if strategy_name == "golden_cross":
        gs_short = st.multiselect("단기 MA", [3, 5, 10, 15], default=[5, 10])
        gs_long = st.multiselect("장기 MA", [20, 30, 60], default=[20, 30])
        param_grid = {"short": gs_short, "long": gs_long}
    elif strategy_name == "rsi":
        gs_period = st.multiselect("RSI 기간", [10, 14, 21], default=[14])
        gs_oversold = st.multiselect("과매도", [20, 25, 30], default=[30])
        gs_overbought = st.multiselect("과매수", [70, 75, 80], default=[70])
        param_grid = {"period": gs_period, "oversold": gs_oversold, "overbought": gs_overbought}
    elif strategy_name == "momentum_breakout":
        gs_lookback = st.multiselect("돌파 기간", [10, 20, 40], default=[20])
        param_grid = {"lookback": gs_lookback}
    else:  # bollinger
        gs_period = st.multiselect("볼린저 기간", [10, 20, 30], default=[20])
        gs_std = st.multiselect("표준편차 배수", [1.5, 2.0, 2.5], default=[2.0])
        param_grid = {"period": gs_period, "std": gs_std}

    gs_holding = st.multiselect("보유 기간", [10, 20, 40], default=[holding_period])
    gs_min_trades = st.number_input("최소 거래 횟수", min_value=5, max_value=500, value=20, step=5)
    gs_min_f = st.number_input("최소 f*", min_value=-1.0, max_value=10.0, value=0.0, step=0.1)

    grid_clicked = st.button("Grid Search 실행", type="primary")

    if grid_clicked:
        with st.spinner("파라미터 조합 탐색 중..."):
            if not gs_holding:
                st.error("최소 하나의 보유 기간을 선택하세요.")
            else:
                grid_df = strategy_analyzer.grid_search(
                    prices,
                    signal_name=strategy_name,
                    param_grid=param_grid,
                    holding_periods=gs_holding,
                    direction=direction,
                    min_trades=gs_min_trades,
                    min_f_star=gs_min_f,
                    exit_on_opposite=exit_on_opposite,
                    allow_renewal=allow_renewal,
                )
                st.session_state["grid_result"] = grid_df

    grid_result = st.session_state.get("grid_result")
    if grid_result is not None:
        if grid_result.empty:
            st.warning("조건을 만족하는 양수 켈리 조합을 찾지 못했습니다. 파라미터 범위를 넓혀보세요.")
        else:
            st.success(f"{len(grid_result)}개의 조합을 찾았습니다.")
            display_df = grid_result.copy()
            # 포맷팅
            for col in ["win_rate", "avg_win", "avg_loss", "f_star_numerical", "f_star_normal_approx", "f_star_adjusted", "f_star"]:
                if col in display_df.columns:
                    display_df[col] = display_df[col].apply(lambda x: f"{x*100:.2f}%" if col != "win_rate" else f"{x*100:.1f}%")
            st.dataframe(display_df, use_container_width=True)
