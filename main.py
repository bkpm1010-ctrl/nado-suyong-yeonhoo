import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import unicodedata
import io

# =============================
# Streamlit 기본 설정
# =============================
st.set_page_config(
    page_title="극지식물 최적 EC 농도 연구",
    layout="wide"
)

# =============================
# 한글 폰트 깨짐 방지 (CSS)
# =============================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# =============================
# 경로 설정
# =============================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# =============================
# 유틸: 한글 파일명 NFC/NFD 안전 탐색
# =============================
def find_file_by_normalized_name(directory: Path, target_name: str):
    target_nfc = unicodedata.normalize("NFC", target_name)
    target_nfd = unicodedata.normalize("NFD", target_name)

    for f in directory.iterdir():
        fname_nfc = unicodedata.normalize("NFC", f.name)
        fname_nfd = unicodedata.normalize("NFD", f.name)
        if fname_nfc == target_nfc or fname_nfd == target_nfd:
            return f
    return None

# =============================
# 데이터 로딩 (캐시)
# =============================
@st.cache_data
def load_environment_data():
    data = {}
    for f in DATA_DIR.iterdir():
        if f.suffix.lower() == ".csv":
            school = f.name.split("_")[0]
            data[school] = pd.read_csv(f)
    return data

@st.cache_data
def load_growth_data():
    xlsx = None
    for f in DATA_DIR.iterdir():
        if f.suffix.lower() == ".xlsx":
            xlsx = f
            break

    if xlsx is None:
        return None

    xls = pd.ExcelFile(xlsx)
    return {sheet: pd.read_excel(xls, sheet_name=sheet) for sheet in xls.sheet_names}

# =============================
# 데이터 로딩
# =============================
with st.spinner("📂 데이터 로딩 중..."):
    env_data = load_environment_data()
    growth_data = load_growth_data()

if not env_data or growth_data is None:
    st.error("❌ data 폴더에 데이터 파일이 없습니다.")
    st.stop()

# =============================
# EC 조건
# =============================
EC_MAP = {
    "송도고": 1.0,
    "하늘고": 2.0,
    "아라고": 4.0,
    "동산고": 8.0,
}

# =============================
# 사이드바
# =============================
schools = ["전체"] + list(env_data.keys())
selected_school = st.sidebar.selectbox("🏫 학교 선택", schools)

# =============================
# 제목
# =============================
st.title("🌱 극지식물 최적 EC 농도 연구")

tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# =============================
# TAB 1
# =============================
with tab1:
    st.subheader("연구 배경 및 목적")
    st.write("극지식물의 최적 EC 농도를 비교 분석한다.")

    overview = []
    total = 0
    for school, df in growth_data.items():
        overview.append([school, EC_MAP[school], len(df)])
        total += len(df)

    overview_df = pd.DataFrame(overview, columns=["학교", "EC", "개체수"])
    st.dataframe(overview_df, use_container_width=True)

    avg_temp = pd.concat(env_data.values())["temperature"].mean()
    avg_hum = pd.concat(env_data.values())["humidity"].mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 개체수", total)
    c2.metric("평균 온도", f"{avg_temp:.2f} ℃")
    c3.metric("평균 습도", f"{avg_hum:.2f} %")
    c4.metric("최적 EC", "2.0 (하늘고)")

# =============================
# TAB 2
# =============================
with tab2:
    st.subheader("학교별 환경 평균")

    rows = []
    for school, df in env_data.items():
        rows.append([
            school,
            df["temperature"].mean(),
            df["humidity"].mean(),
            df["ph"].mean(),
            df["ec"].mean(),
            EC_MAP[school]
        ])

    avg_df = pd.DataFrame(
        rows,
        columns=["학교", "온도", "습도", "pH", "실측 EC", "목표 EC"]
    )

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=["온도", "습도", "pH", "EC 비교"]
    )

    fig.add_bar(x=avg_df["학교"], y=avg_df["온도"], row=1, col=1)
    fig.add_bar(x=avg_df["학교"], y=avg_df["습도"], row=1, col=2)
    fig.add_bar(x=avg_df["학교"], y=avg_df["pH"], row=2, col=1)
    fig.add_bar(x=avg_df["학교"], y=avg_df["실측 EC"], name="실측", row=2, col=2)
    fig.add_bar(x=avg_df["학교"], y=avg_df["목표 EC"], name="목표", row=2, col=2)

    fig.update_layout(
        height=700,
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )
    st.plotly_chart(fig, use_container_width=True)

    # ✅ KeyError 수정 핵심 부분
    if selected_school != "전체":
        df = env_data[selected_school]

        fig_ts = px.line(
            df,
            x="time",
            y=["temperature", "humidity", "ec"],
            labels={"value": "측정값", "time": "시간"}
        )

        if selected_school in EC_MAP:
            fig_ts.add_hline(
                y=EC_MAP[selected_school],
                line_dash="dash",
                annotation_text="목표 EC"
            )

        fig_ts.update_layout(
            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
        )
        st.plotly_chart(fig_ts, use_container_width=True)

    with st.expander("환경 데이터 원본"):
        all_env = pd.concat(
            [df.assign(학교=school) for school, df in env_data.items()]
        )
        st.dataframe(all_env, use_container_width=True)

        csv = all_env.to_csv(index=False).encode("utf-8-sig")
        st.download_button("CSV 다운로드", csv, "환경데이터.csv", "text/csv")

# =============================
# TAB 3
# =============================
with tab3:
    rows = []
    for school, df in growth_data.items():
        rows.append([
            school,
            EC_MAP[school],
            df["생중량(g)"].mean(),
            df["잎 수(장)"].mean(),
            df["지상부 길이(mm)"].mean(),
            len(df)
        ])

    gdf = pd.DataFrame(
        rows,
        columns=["학교", "EC", "평균 생중량", "평균 잎 수", "평균 지상부 길이", "개체수"]
    )

    best = gdf.loc[gdf["평균 생중량"].idxmax()]
    st.metric(
        "🥇 최고 생중량",
        f"{best['평균 생중량']:.2f} g",
        f"{best['학교']} (EC {best['EC']})"
    )

    fig2 = make_subplots(
        rows=2, cols=2,
        subplot_titles=["생중량", "잎 수", "지상부 길이", "개체수"]
    )

    fig2.add_bar(x=gdf["학교"], y=gdf["평균 생중량"], row=1, col=1)
    fig2.add_bar(x=gdf["학교"], y=gdf["평균 잎 수"], row=1, col=2)
    fig2.add_bar(x=gdf["학교"], y=gdf["평균 지상부 길이"], row=2, col=1)
    fig2.add_bar(x=gdf["학교"], y=gdf["개체수"], row=2, col=2)

    fig2.update_layout(
        height=700,
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )
    st.plotly_chart(fig2, use_container_width=True)

    merged = pd.concat(
        [df.assign(학교=school) for school, df in growth_data.items()]
    )

    st.plotly_chart(
        px.box(merged, x="학교", y="생중량(g)", points="all"),
        use_container_width=True
    )

    with st.expander("생육 데이터 원본"):
        st.dataframe(merged, use_container_width=True)

        buffer = io.BytesIO()
        merged.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)

        st.download_button(
            "XLSX 다운로드",
            buffer,
            "생육결과.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
