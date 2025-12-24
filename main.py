import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import unicodedata
import io

# ===============================
# 기본 설정
# ===============================
st.set_page_config(
    page_title="극지식물 최적 EC 농도 연구",
    layout="wide"
)

# 한글 폰트 (Streamlit)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# ===============================
# 상수 정의
# ===============================
DATA_DIR = Path("data")

EC_TARGET = {
    "송도고": 1.0,
    "하늘고": 2.0,
    "아라고": 4.0,
    "동산고": 8.0
}

SCHOOL_COLOR = {
    "송도고": "#1f77b4",
    "하늘고": "#2ca02c",
    "아라고": "#ff7f0e",
    "동산고": "#d62728"
}

# ===============================
# 유틸 함수 (NFC/NFD 파일 인식)
# ===============================
def normalize_name(name: str) -> set:
    return {
        unicodedata.normalize("NFC", name),
        unicodedata.normalize("NFD", name)
    }

def find_file_by_name(directory: Path, target_name: str):
    target_norm = normalize_name(target_name)
    for f in directory.iterdir():
        if normalize_name(f.name) & target_norm:
            return f
    return None

# ===============================
# 데이터 로딩
# ===============================
@st.cache_data
def load_environment_data():
    data = {}
    for school in EC_TARGET.keys():
        filename = f"{school}_환경데이터.csv"
        file_path = find_file_by_name(DATA_DIR, filename)
        if file_path is None:
            st.error(f"❌ 환경 데이터 파일을 찾을 수 없습니다: {filename}")
            continue
        df = pd.read_csv(file_path)
        df["time"] = pd.to_datetime(df["time"])
        df["학교"] = school
        data[school] = df
    return data

@st.cache_data
def load_growth_data():
    file_path = find_file_by_name(DATA_DIR, "4개교_생육결과데이터.xlsx")
    if file_path is None:
        st.error("❌ 생육 결과 XLSX 파일을 찾을 수 없습니다.")
        return {}

    xls = pd.ExcelFile(file_path, engine="openpyxl")
    data = {}
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        df["학교"] = sheet
        data[sheet] = df
    return data

with st.spinner("📂 데이터 로딩 중..."):
    env_data = load_environment_data()
    growth_data = load_growth_data()

if not env_data or not growth_data:
    st.stop()

# ===============================
# 사이드바
# ===============================
st.sidebar.title("🏫 학교 선택")
school_option = st.sidebar.selectbox(
    "학교",
    ["전체"] + list(EC_TARGET.keys())
)

# ===============================
# 제목
# ===============================
st.title("🌱 극지식물 최적 EC 농도 연구")

tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# ===============================
# TAB 1 : 실험 개요
# ===============================
with tab1:
    st.subheader("📌 연구 배경 및 목적")
    st.write("""
    본 연구는 **극지식물의 최적 EC(Electrical Conductivity) 농도**를 도출하기 위해  
    서로 다른 EC 조건에서 재배된 식물의 **환경 데이터와 생육 결과**를 비교·분석하였다.
    """)

    overview_df = pd.DataFrame({
        "학교": EC_TARGET.keys(),
        "EC 목표": EC_TARGET.values(),
        "개체수": [len(growth_data[s]) for s in EC_TARGET.keys()],
        "색상": [SCHOOL_COLOR[s] for s in EC_TARGET.keys()]
    })
    st.dataframe(overview_df, use_container_width=True)

    total_count = sum(len(df) for df in growth_data.values())
    avg_temp = pd.concat(env_data.values())["temperature"].mean()
    avg_hum = pd.concat(env_data.values())["humidity"].mean()
    optimal_ec = 2.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 개체수", f"{total_count} 개")
    c2.metric("평균 온도", f"{avg_temp:.1f} ℃")
    c3.metric("평균 습도", f"{avg_hum:.1f} %")
    c4.metric("최적 EC", f"{optimal_ec} ⭐")

# ===============================
# TAB 2 : 환경 데이터
# ===============================
with tab2:
    st.subheader("📊 학교별 환경 평균 비교")

    avg_env = []
    for school, df in env_data.items():
        avg_env.append({
            "학교": school,
            "온도": df["temperature"].mean(),
            "습도": df["humidity"].mean(),
            "pH": df["ph"].mean(),
            "EC": df["ec"].mean(),
            "EC 목표": EC_TARGET[school]
        })
    avg_env_df = pd.DataFrame(avg_env)

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("평균 온도", "평균 습도", "평균 pH", "목표 EC vs 실측 EC")
    )

    fig.add_bar(x=avg_env_df["학교"], y=avg_env_df["온도"], row=1, col=1)
    fig.add_bar(x=avg_env_df["학교"], y=avg_env_df["습도"], row=1, col=2)
    fig.add_bar(x=avg_env_df["학교"], y=avg_env_df["pH"], row=2, col=1)
    fig.add_bar(x=avg_env_df["학교"], y=avg_env_df["EC"], name="실측", row=2, col=2)
    fig.add_bar(x=avg_env_df["학교"], y=avg_env_df["EC 목표"], name="목표", row=2, col=2)

    fig.update_layout(
        height=600,
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )
    st.plotly_chart(fig, use_container_width=True)

    if school_option != "전체":
        df = env_data[school_option]
        st.subheader(f"⏱ {school_option} 시계열 변화")

        fig_ts = go.Figure()
        fig_ts.add_line(x=df["time"], y=df["temperature"], name="온도")
        fig_ts.add_line(x=df["time"], y=df["humidity"], name="습도")
        fig_ts.add_line(x=df["time"], y=df["ec"], name="EC")
        fig_ts.add_hline(
            y=EC_TARGET[school_option],
            line_dash="dash",
            annotation_text="목표 EC"
        )
        fig_ts.update_layout(
            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
        )
        st.plotly_chart(fig_ts, use_container_width=True)

    with st.expander("📥 환경 데이터 원본"):
        for school, df in env_data.items():
            st.write(f"### {school}")
            st.dataframe(df)
            buffer = io.BytesIO()
            df.to_csv(buffer, index=False)
            buffer.seek(0)
            st.download_button(
                f"{school} CSV 다운로드",
                data=buffer,
                file_name=f"{school}_환경데이터.csv",
                mime="text/csv"
            )

# ===============================
# TAB 3 : 생육 결과
# ===============================
with tab3:
    st.subheader("🥇 EC별 평균 생중량")

    summary = []
    for school, df in growth_data.items():
        summary.append({
            "학교": school,
            "EC": EC_TARGET.get(school, None),
            "평균 생중량": df["생중량(g)"].mean(),
            "평균 잎 수": df["잎 수(장)"].mean(),
            "평균 지상부 길이": df["지상부 길이(mm)"].mean(),
            "개체수": len(df)
        })
    summary_df = pd.DataFrame(summary)

    best = summary_df.loc[summary_df["평균 생중량"].idxmax()]

    st.metric(
        "⭐ 최적 EC (평균 생중량 최대)",
        f"EC {best['EC']} ({best['학교']})"
    )

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("평균 생중량", "평균 잎 수", "평균 지상부 길이", "개체수")
    )

    fig.add_bar(x=summary_df["학교"], y=summary_df["평균 생중량"], row=1, col=1)
    fig.add_bar(x=summary_df["학교"], y=summary_df["평균 잎 수"], row=1, col=2)
    fig.add_bar(x=summary_df["학교"], y=summary_df["평균 지상부 길이"], row=2, col=1)
    fig.add_bar(x=summary_df["학교"], y=summary_df["개체수"], row=2, col=2)

    fig.update_layout(
        height=600,
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )
    st.plotly_chart(fig, use_container_width=True)

    all_growth = pd.concat(growth_data.values())
    fig_box = px.violin(
        all_growth,
        x="학교",
        y="생중량(g)",
        box=True,
        points="all"
    )
    fig_box.update_layout(
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )
    st.plotly_chart(fig_box, use_container_width=True)

    fig_corr1 = px.scatter(all_growth, x="잎 수(장)", y="생중량(g)", color="학교")
    fig_corr2 = px.scatter(all_growth, x="지상부 길이(mm)", y="생중량(g)", color="학교")

    st.plotly_chart(fig_corr1, use_container_width=True)
    st.plotly_chart(fig_corr2, use_container_width=True)

    with st.expander("📥 생육 데이터 원본"):
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            for school, df in growth_data.items():
                df.to_excel(writer, sheet_name=school, index=False)
        buffer.seek(0)

        st.download_button(
            "전체 생육 데이터 XLSX 다운로드",
            data=buffer,
            file_name="4개교_생육결과데이터.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
