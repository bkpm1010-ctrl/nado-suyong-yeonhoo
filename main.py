import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import unicodedata
import io

# 페이지 설정
st.set_page_config(
    page_title="극지식물 최적 EC 농도 연구",
    page_icon="🌱",
    layout="wide"
)

# 한글 폰트 설정
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# 학교별 EC 조건 및 색상
SCHOOL_INFO = {
    "송도고": {"ec": 1.0, "color": "#FF6B6B"},
    "하늘고": {"ec": 2.0, "color": "#4ECDC4"},
    "아라고": {"ec": 4.0, "color": "#45B7D1"},
    "동산고": {"ec": 8.0, "color": "#FFA07A"}
}

def normalize_filename(filename, form='NFC'):
    return unicodedata.normalize(form, str(filename))

# 환경 데이터 로딩
@st.cache_data
def load_environment_data():
    data_dir = Path("data")
    env_data = {}

    if not data_dir.exists():
        return env_data

    for school_name in SCHOOL_INFO.keys():
        for file_path in data_dir.glob("*.csv"):
            if normalize_filename(file_path.name) == normalize_filename(f"{school_name}_환경데이터.csv"):
                df = pd.read_csv(file_path)
                df['학교'] = school_name
                env_data[school_name] = df
                break

    return env_data

# 생육 데이터 로딩
@st.cache_data
def load_growth_data():
    data_dir = Path("data")
    growth_data = {}

    excel_path = data_dir / "4개교_생육결과데이터.xlsx"
    if not excel_path.exists():
        return growth_data

    excel = pd.ExcelFile(excel_path)

    for sheet in excel.sheet_names:
        for school in SCHOOL_INFO.keys():
            if normalize_filename(sheet) == normalize_filename(school):
                df = pd.read_excel(excel_path, sheet_name=sheet)
                df['학교'] = school
                df['EC'] = SCHOOL_INFO[school]['ec']
                growth_data[school] = df

    return growth_data

def main():
    st.title("🌱 극지식물 최적 EC 농도 연구")

    env_data = load_environment_data()
    growth_data = load_growth_data()

    if not env_data or not growth_data:
        st.error("❌ 데이터가 부족합니다. data 폴더를 확인하세요.")
        return

    st.sidebar.header("🔍 필터")
    schools = ["전체"] + sorted(set(env_data.keys()) & set(growth_data.keys()))
    selected_school = st.sidebar.selectbox("학교 선택", schools)

    tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

    # ---------------- Tab 1 ----------------
    with tab1:
        st.subheader("📋 학교별 실험 조건")

        condition_df = pd.DataFrame([
            {
                "학교": s,
                "목표 EC": SCHOOL_INFO[s]['ec'],
                "개체수": len(growth_data[s])
            }
            for s in growth_data.keys()
        ])

        st.dataframe(condition_df, hide_index=True, use_container_width=True)

    # ---------------- Tab 2 ----------------
    with tab2:
        st.subheader("📈 환경 평균 비교")

        env_summary = []
        for school, df in env_data.items():
            env_summary.append({
                "학교": school,
                "평균 온도": df['temperature'].mean(),
                "평균 습도": df['humidity'].mean(),
                "평균 pH": df['ph'].mean(),
                "평균 EC": df['ec'].mean(),
                "목표 EC": SCHOOL_INFO[school]['ec']
            })

        env_df = pd.DataFrame(env_summary)

        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=("온도", "습도", "pH", "EC")
        )

        fig.add_bar(x=env_df['학교'], y=env_df['평균 온도'], row=1, col=1)
        fig.add_bar(x=env_df['학교'], y=env_df['평균 습도'], row=1, col=2)
        fig.add_bar(x=env_df['학교'], y=env_df['평균 pH'], row=2, col=1)
        fig.add_bar(x=env_df['학교'], y=env_df['평균 EC'], row=2, col=2)

        st.plotly_chart(fig, use_container_width=True)

        if selected_school != "전체":
            df = env_data[selected_school]
            df['time'] = pd.to_datetime(df['time'], errors='coerce')

            fig_ts = make_subplots(rows=3, cols=1)
            fig_ts.add_scatter(x=df['time'], y=df['temperature'], row=1, col=1)
            fig_ts.add_scatter(x=df['time'], y=df['humidity'], row=2, col=1)
            fig_ts.add_scatter(x=df['time'], y=df['ec'], row=3, col=1)

            fig_ts.add_hline(
                y=SCHOOL_INFO[selected_school]['ec'],
                line_dash="dash",
                row=3, col=1
            )

            st.plotly_chart(fig_ts, use_container_width=True)

    # ---------------- Tab 3 ----------------
    with tab3:
        growth_all = pd.concat(growth_data.values(), ignore_index=True)

        ec_mean = growth_all.groupby('EC')['생중량(g)'].mean()

        cols = st.columns(len(ec_mean))
        for i, (ec, val) in enumerate(ec_mean.items()):
            cols[i].metric(f"EC {ec}", f"{val:.2f} g")

        fig_box = go.Figure()
        for school, df in growth_data.items():
            fig_box.add_box(
                y=df['생중량(g)'],
                name=f"{school} (EC {SCHOOL_INFO[school]['ec']})"
            )

        st.plotly_chart(fig_box, use_container_width=True)

        with st.expander("📋 생육 데이터 원본"):
            if selected_school == "전체":
                show_df = growth_all
            else:
                show_df = growth_data[selected_school]

            st.dataframe(show_df, use_container_width=True)

            buffer = io.BytesIO()
            show_df.to_excel(buffer, index=False)
            buffer.seek(0)

            st.download_button(
                "📥 XLSX 다운로드",
                data=buffer,
                file_name="생육데이터.xlsx"
            )

if __name__ == "__main__":
    main()
