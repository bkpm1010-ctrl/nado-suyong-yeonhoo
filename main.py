import streamlit as st
import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots
from pathlib import Path
import unicodedata
import io

# =============================
# 기본 설정
# =============================
st.set_page_config(page_title="🌱 극지식물 최적 EC 농도 연구", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# =============================
# EC 조건 (안전 접근만 사용)
# =============================
EC_MAP = {
    "송도고": 1.0,
    "하늘고": 2.0,
    "아라고": 4.0,
    "동산고": 8.0,
}

# =============================
# 데이터 로딩
# =============================
@st.cache_data
def load_env_data():
    data = {}
    for f in DATA_DIR.iterdir():
        if f.suffix.lower() == ".csv":
            school = unicodedata.normalize("NFC", f.name.split("_")[0].strip())
            data[school] = pd.read_csv(f)
    return data

@st.cache_data
def load_growth_data():
    for f in DATA_DIR.iterdir():
        if f.suffix.lower() == ".xlsx":
            xls = pd.ExcelFile(f)
            return {
                unicodedata.normalize("NFC", s.strip()): pd.read_excel(xls, s)
                for s in xls.sheet_names
            }
    return None

with st.spinner("📂 데이터 로딩 중..."):
    env_data = load_env_data()
    growth_data = load_growth_data()

if not env_data or growth_data is None:
    st.error("❌ data 폴더에 데이터가 없습니다.")
    st.stop()

# =============================
# 사이드바
# =============================
schools = ["전체"] + sorted(env_data.keys())
selected_school = st.sidebar.selectbox("🏫 학교 선택", schools)

st.title("🌱 극지식물 최적 EC 농도 연구")

tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# =============================
# TAB 1 실험 개요
# =============================
with tab1:
    st.subheader("연구 배경 및 목적")
    st.write("EC 농도 차이에 따른 극지식물 생육 특성을 비교하여 최적 EC를 도출한다.")

    overview = []
    total_cnt = 0
    for school, df in growth_data.items():
        ec = EC_MAP.get(school)
        if ec is None:
            continue
        overview.append([school, ec, len(df)])
        total_cnt += len(df)

    overview_df = pd.DataFrame(overview, columns=["학교", "EC 목표", "개체수"])
    st.dataframe(overview_df, use_container_width=True)

    avg_temp = pd.concat(env_data.values())["temperature"].mean()
    avg_hum = pd.concat(env_data.values())["humidity"].mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 개체수", total_cnt)
    c2.metric("평균 온도", f"{avg_temp:.2f} ℃")
    c3.metric("평균 습도", f"{avg_hum:.2f} %")
    c4.metric("최적 EC", "2.0 (하늘고)")

# =============================
# TAB 2 환경 데이터
# =============================
with tab2:
    st.subheader("학교별 환경 평균 비교")

    rows = []
    for school, df in env_data.items():
        ec_target = EC_MAP.get(school)
        if ec_target is None:
            continue
        rows.append([
            school,
            df["temperature"].mean(),
            df["humidity"].mean(),
            df["ph"].mean(),
            df["ec"].mean(),
            ec_target
        ])

    avg_df = pd.DataFrame(
        rows, columns=["학교", "온도", "습도", "pH", "실측 EC", "목표 EC"]
    )

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=["평균 온도", "평균 습도", "평균 pH", "목표 EC vs 실측 EC"]
    )

    fig.add_bar(x=avg_df["학교"], y=avg_df["온도"], row=1, col=1)
    fig.add_bar(x=avg_df["학교"], y=avg_df["습도"], row=1, col=2)
    fig.add_bar(x=avg_df["학교"], y=avg_df["pH"], row=2, col=1)
    fig.add_bar(x=avg_df["학교"], y=avg_df["실측 EC"], name="실측", row=2, col=2)
    fig.add_bar(x=avg_df["학교"], y=avg_df["목표 EC"], name="목표", row=2, col=2)

    fig.update_layout(height=700)
    st.plotly_chart(fig, use_container_width=True)

    # 📈 선택 학교 시계열
    if selected_school != "전체":
        df = env_data[selected_school]
        fig_ts = px.line(
            df,
            x="time",
            y=["temperature", "humidity", "ec"],
            title=f"{selected_school} 환경 변화"
        )
        if selected_school in EC_MAP:
            fig_ts.add_hline(y=EC_MAP[selected_school], line_dash="dash", annotation_text="목표 EC")
        st.plotly_chart(fig_ts, use_container_width=True)

    # 📂 원본 + 다운로드
    with st.expander("📂 환경 데이터 원본"):
        env_all = pd.concat(
            [df.assign(학교=s) for s, df in env_data.items()]
        )
        st.dataframe(env_all, use_container_width=True)

        csv = env_all.to_csv(index=False).encode("utf-8-sig")
        st.download_button("CSV 다운로드", csv, "환경데이터_전체.csv", "text/csv")

# =============================
# TAB 3 생육 결과
# =============================
with tab3:
    rows = []
    for school, df in growth_data.items():
        ec = EC_MAP.get(school)
        if ec is None:
            continue
        rows.append([
            school,
            ec,
            df["생중량(g)"].mean(),
            df["잎 수(장)"].mean(),
            df["지상부 길이(mm)"].mean(),
            len(df)
        ])

    gdf = pd.DataFrame(
        rows, columns=["학교", "EC", "평균 생중량", "평균 잎 수", "평균 지상부 길이", "개체수"]
    )

    best = gdf.loc[gdf["평균 생중량"].idxmax()]
    st.metric(
        "🥇 EC별 평균 생중량 최고",
        f"{best['평균 생중량']:.2f} g",
        f"{best['학교']} (EC {best['EC']})"
    )

    fig2 = make_subplots(
        rows=2, cols=2,
        subplot_titles=["평균 생중량 ⭐", "평균 잎 수", "평균 지상부 길이", "개체수"]
    )

    fig2.add_bar(x=gdf["학교"], y=gdf["평균 생중량"], row=1, col=1)
    fig2.add_bar(x=gdf["학교"], y=gdf["평균 잎 수"], row=1, col=2)
    fig2.add_bar(x=gdf["학교"], y=gdf["평균 지상부 길이"], row=2, col=1)
    fig2.add_bar(x=gdf["학교"], y=gdf["개체수"], row=2, col=2)

    fig2.update_layout(height=700)
    st.plotly_chart(fig2, use_container_width=True)

    merged = pd.concat(
        [df.assign(학교=s) for s, df in growth_data.items() if s in EC_MAP]
    )

    # 📦 분포
    st.plotly_chart(
        px.box(merged, x="학교", y="생중량(g)", points="all"),
        use_container_width=True
    )

    # 🔗 상관관계
    c1, c2 = st.columns(2)
    c1.plotly_chart(
        px.scatter(merged, x="잎 수(장)", y="생중량(g)", color="학교"),
        use_container_width=True
    )
    c2.plotly_chart(
        px.scatter(merged, x="지상부 길이(mm)", y="생중량(g)", color="학교"),
        use_container_width=True
    )

    # 📂 원본 + 다운로드
    with st.expander("📂 생육 데이터 원본"):
        st.dataframe(merged, use_container_width=True)

        buffer = io.BytesIO()
        merged.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)

        st.download_button(
            "XLSX 다운로드",
            buffer,
            "생육결과_전체.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
