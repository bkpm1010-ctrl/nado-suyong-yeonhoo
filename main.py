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

# 파일명 정규화 함수
def normalize_filename(filename, form='NFC'):
    return unicodedata.normalize(form, str(filename))

# 환경 데이터 로딩
@st.cache_data
def load_environment_data():
    data_dir = Path("data")
    env_data = {}
    
    if not data_dir.exists():
        st.error(f"❌ data 폴더를 찾을 수 없습니다: {data_dir.absolute()}")
        return env_data
    
    for school_name in SCHOOL_INFO.keys():
        found = False
        for file_path in data_dir.iterdir():
            if not file_path.is_file() or file_path.suffix.lower() != '.csv':
                continue
            
            file_name_nfc = normalize_filename(file_path.name, 'NFC')
            file_name_nfd = normalize_filename(file_path.name, 'NFD')
            target_nfc = normalize_filename(f"{school_name}_환경데이터.csv", 'NFC')
            target_nfd = normalize_filename(f"{school_name}_환경데이터.csv", 'NFD')
            
            if file_name_nfc == target_nfc or file_name_nfd == target_nfd:
                try:
                    df = pd.read_csv(file_path)
                    df['학교'] = school_name
                    env_data[school_name] = df
                    found = True
                    break
                except Exception as e:
                    st.error(f"❌ {school_name} 환경 데이터 로딩 실패: {e}")
        
        if not found:
            st.warning(f"⚠️ {school_name}_환경데이터.csv 파일을 찾을 수 없습니다.")
    
    return env_data

# 생육 데이터 로딩
@st.cache_data
def load_growth_data():
    data_dir = Path("data")
    growth_data = {}
    
    if not data_dir.exists():
        st.error(f"❌ data 폴더를 찾을 수 없습니다: {data_dir.absolute()}")
        return growth_data
    
    excel_file = None
    for file_path in data_dir.iterdir():
        if not file_path.is_file():
            continue
        
        file_name_nfc = normalize_filename(file_path.name, 'NFC')
        file_name_nfd = normalize_filename(file_path.name, 'NFD')
        target_nfc = normalize_filename("4개교_생육결과데이터.xlsx", 'NFC')
        target_nfd = normalize_filename("4개교_생육결과데이터.xlsx", 'NFD')
        
        if file_name_nfc == target_nfc or file_name_nfd == target_nfd:
            excel_file = file_path
            break
    
    if excel_file is None:
        st.error("❌ 4개교_생육결과데이터.xlsx 파일을 찾을 수 없습니다.")
        return growth_data
    
    try:
        excel_data = pd.ExcelFile(excel_file)
        
        for sheet_name in excel_data.sheet_names:
            sheet_nfc = normalize_filename(sheet_name, 'NFC')
            sheet_nfd = normalize_filename(sheet_name, 'NFD')
            
            for school_name in SCHOOL_INFO.keys():
                school_nfc = normalize_filename(school_name, 'NFC')
                school_nfd = normalize_filename(school_name, 'NFD')
                
                if sheet_nfc == school_nfc or sheet_nfd == school_nfd:
                    df = pd.read_excel(excel_file, sheet_name=sheet_name)
                    df['학교'] = school_name
                    df['EC'] = SCHOOL_INFO[school_name]['ec']
                    growth_data[school_name] = df
                    break
        
    except Exception as e:
        st.error(f"❌ 생육 데이터 로딩 실패: {e}")
    
    return growth_data

# 메인 앱
def main():
    st.title("🌱 극지식물 최적 EC 농도 연구")
    
    # 데이터 로딩
    with st.spinner("데이터를 불러오는 중..."):
        env_data = load_environment_data()
        growth_data = load_growth_data()
    
    if not env_data or not growth_data:
        st.error("❌ 필요한 데이터 파일을 불러올 수 없습니다. data 폴더와 파일을 확인해주세요.")
        return
    
    # 사이드바
    st.sidebar.header("🔍 필터")
    schools = ["전체"] + list(SCHOOL_INFO.keys())
    selected_school = st.sidebar.selectbox("학교 선택", schools)
    
    # 탭 생성
    tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])
    
    # Tab 1: 실험 개요
    with tab1:
        st.header("실험 개요")
        
        st.markdown("""
        ### 🎯 연구 목적
        극지식물의 최적 성장을 위한 **EC(전기전도도) 농도**를 실험적으로 도출합니다.
        
        ### 🔬 실험 방법
        - 4개 고등학교에서 각기 다른 EC 조건으로 극지식물 재배
        - 환경 데이터(온도, 습도, pH, EC) 지속적 모니터링
        - 생육 결과(생중량, 잎 수, 길이) 측정 및 비교
        """)
        
        st.subheader("📋 학교별 실험 조건")
        
        condition_df = pd.DataFrame([
            {
                "학교": school,
                "목표 EC": info['ec'],
                "개체수": len(growth_data[school]) if school in growth_data else 0,
                "색상": info['color']
            }
            for school, info in SCHOOL_INFO.items()
        ])
        
        st.dataframe(
            condition_df,
            hide_index=True,
            use_container_width=True
        )
        
        st.subheader("📊 주요 지표")
        
        total_samples = sum(len(df) for df in growth_data.values())
        avg_temp = pd.concat([df['temperature'] for df in env_data.values()]).mean()
        avg_humidity = pd.concat([df['humidity'] for df in env_data.values()]).mean()
        
        # 최적 EC 계산 (평균 생중량 기준)
        growth_combined = pd.concat(growth_data.values())
        avg_biomass = growth_combined.groupby('EC')['생중량(g)'].mean()
        optimal_ec = avg_biomass.idxmax()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("총 개체수", f"{total_samples}개")
        with col2:
            st.metric("평균 온도", f"{avg_temp:.1f}°C")
        with col3:
            st.metric("평균 습도", f"{avg_humidity:.1f}%")
        with col4:
            st.metric("최적 EC", f"{optimal_ec:.1f} dS/m", delta="🏆")
    
    # Tab 2: 환경 데이터
    with tab2:
        st.header("환경 데이터 분석")
        
        # 학교별 환경 평균 비교
        st.subheader("📈 학교별 환경 평균 비교")
        
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
        env_summary_df = pd.DataFrame(env_summary)
        
        # 2x2 서브플롯
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=("평균 온도 (°C)", "평균 습도 (%)", "평균 pH", "목표 EC vs 실측 EC (dS/m)")
        )
        
        # 온도
        fig.add_trace(
            go.Bar(
                x=env_summary_df['학교'],
                y=env_summary_df['평균 온도'],
                marker_color=[SCHOOL_INFO[s]['color'] for s in env_summary_df['학교']],
                name="온도"
            ),
            row=1, col=1
        )
        
        # 습도
        fig.add_trace(
            go.Bar(
                x=env_summary_df['학교'],
                y=env_summary_df['평균 습도'],
                marker_color=[SCHOOL_INFO[s]['color'] for s in env_summary_df['학교']],
                name="습도"
            ),
            row=1, col=2
        )
        
        # pH
        fig.add_trace(
            go.Bar(
                x=env_summary_df['학교'],
                y=env_summary_df['평균 pH'],
                marker_color=[SCHOOL_INFO[s]['color'] for s in env_summary_df['학교']],
                name="pH"
            ),
            row=2, col=1
        )
        
        # EC 비교
        fig.add_trace(
            go.Bar(
                x=env_summary_df['학교'],
                y=env_summary_df['목표 EC'],
                name="목표 EC",
                marker_color='lightgray'
            ),
            row=2, col=2
        )
        
        fig.add_trace(
            go.Bar(
                x=env_summary_df['학교'],
                y=env_summary_df['평균 EC'],
                name="실측 EC",
                marker_color=[SCHOOL_INFO[s]['color'] for s in env_summary_df['학교']]
            ),
            row=2, col=2
        )
        
        fig.update_layout(
            height=700,
            showlegend=False,
            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif", size=12)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 시계열 데이터
        if selected_school != "전체":
            st.subheader(f"📉 {selected_school} 시계열 데이터")
            
            school_env = env_data[selected_school].copy()
            school_env['time'] = pd.to_datetime(school_env['time'], errors='coerce')
            school_env = school_env.sort_values('time')
            
            fig_time = make_subplots(
                rows=3, cols=1,
                subplot_titles=("온도 변화 (°C)", "습도 변화 (%)", "EC 변화 (dS/m)"),
                vertical_spacing=0.1
            )
            
            # 온도
            fig_time.add_trace(
                go.Scatter(
                    x=school_env['time'],
                    y=school_env['temperature'],
                    mode='lines',
                    name="온도",
                    line=dict(color=SCHOOL_INFO[selected_school]['color'])
                ),
                row=1, col=1
            )
            
            # 습도
            fig_time.add_trace(
                go.Scatter(
                    x=school_env['time'],
                    y=school_env['humidity'],
                    mode='lines',
                    name="습도",
                    line=dict(color=SCHOOL_INFO[selected_school]['color'])
                ),
                row=2, col=1
            )
            
            # EC
            fig_time.add_trace(
                go.Scatter(
                    x=school_env['time'],
                    y=school_env['ec'],
                    mode='lines',
                    name="실측 EC",
                    line=dict(color=SCHOOL_INFO[selected_school]['color'])
                ),
                row=3, col=1
            )
            
            # 목표 EC 수평선
            target_ec = SCHOOL_INFO[selected_school]['ec']
            fig_time.add_trace(
                go.Scatter(
                    x=school_env['time'],
                    y=[target_ec] * len(school_env),
                    mode='lines',
                    name="목표 EC",
                    line=dict(color='red', dash='dash')
                ),
                row=3, col=1
            )
            
            fig_time.update_layout(
                height=900,
                showlegend=True,
                font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif", size=12)
            )
            
            st.plotly_chart(fig_time, use_container_width=True)
        
        # 원본 데이터
        with st.expander("📋 환경 데이터 원본 보기"):
            if selected_school == "전체":
                display_env = pd.concat(env_data.values(), ignore_index=True)
            else:
                display_env = env_data[selected_school]
            
            st.dataframe(display_env, use_container_width=True)
            
            # CSV 다운로드
            csv = display_env.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 CSV 다운로드",
                data=csv,
                file_name=f"{selected_school}_환경데이터.csv",
                mime="text/csv"
            )
    
    # Tab 3: 생육 결과
    with tab3:
        st.header("생육 결과 분석")
        
        # 전체 생육 데이터
        growth_combined = pd.concat(growth_data.values(), ignore_index=True)
        
        # 핵심 결과 카드
        st.subheader("🥇 핵심 결과: EC별 평균 생중량")
        
        ec_biomass = growth_combined.groupby('EC')['생중량(g)'].mean().sort_values(ascending=False)
        best_ec = ec_biomass.idxmax()
        
        cols = st.columns(len(ec_biomass))
        for idx, (ec, biomass) in enumerate(ec_biomass.items()):
            with cols[idx]:
                school = [s for s, info in SCHOOL_INFO.items() if info['ec'] == ec][0]
                delta = "🏆 최적" if ec == best_ec else ""
                st.metric(
                    f"EC {ec}",
                    f"{biomass:.2f}g",
                    delta=delta
                )
        
        # EC별 생육 비교 (2x2)
        st.subheader("📊 EC별 생육 비교")
        
        growth_summary = growth_combined.groupby('EC').agg({
            '생중량(g)': 'mean',
            '잎 수(장)': 'mean',
            '지상부 길이(mm)': 'mean',
            '개체번호': 'count'
        }).reset_index()
        growth_summary.columns = ['EC', '평균 생중량', '평균 잎 수', '평균 지상부 길이', '개체수']
        
        fig_growth = make_subplots(
            rows=2, cols=2,
            subplot_titles=("⭐ 평균 생중량 (g)", "평균 잎 수 (장)", "평균 지상부 길이 (mm)", "개체수")
        )
        
        school_names = [s for s, info in SCHOOL_INFO.items()]
        colors = [SCHOOL_INFO[s]['color'] for s in school_names]
        
        # 생중량
        fig_growth.add_trace(
            go.Bar(
                x=growth_summary['EC'],
                y=growth_summary['평균 생중량'],
                marker_color=colors,
                name="생중량",
                text=growth_summary['평균 생중량'].round(2),
                textposition='outside'
            ),
            row=1, col=1
        )
        
        # 잎 수
        fig_growth.add_trace(
            go.Bar(
                x=growth_summary['EC'],
                y=growth_summary['평균 잎 수'],
                marker_color=colors,
                name="잎 수",
                text=growth_summary['평균 잎 수'].round(1),
                textposition='outside'
            ),
            row=1, col=2
        )
        
        # 지상부 길이
        fig_growth.add_trace(
            go.Bar(
                x=growth_summary['EC'],
                y=growth_summary['평균 지상부 길이'],
                marker_color=colors,
                name="지상부 길이",
                text=growth_summary['평균 지상부 길이'].round(1),
                textposition='outside'
            ),
            row=2, col=1
        )
        
        # 개체수
        fig_growth.add_trace(
            go.Bar(
                x=growth_summary['EC'],
                y=growth_summary['개체수'],
                marker_color=colors,
                name="개체수",
                text=growth_summary['개체수'],
                textposition='outside'
            ),
            row=2, col=2
        )
        
        fig_growth.update_layout(
            height=700,
            showlegend=False,
            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif", size=12)
        )
        
        st.plotly_chart(fig_growth, use_container_width=True)
        
        # 생중량 분포 (박스플롯)
        st.subheader("📦 학교별 생중량 분포")
        
        fig_box = go.Figure()
        
        for school in SCHOOL_INFO.keys():
            school_growth = growth_data[school]
            fig_box.add_trace(
                go.Box(
                    y=school_growth['생중량(g)'],
                    name=f"{school} (EC {SCHOOL_INFO[school]['ec']})",
                    marker_color=SCHOOL_INFO[school]['color']
                )
            )
        
        fig_box.update_layout(
            yaxis_title="생중량 (g)",
            height=500,
            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif", size=12)
        )
        
        st.plotly_chart(fig_box, use_container_width=True)
        
        # 상관관계 분석
        st.subheader("🔗 상관관계 분석")
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_corr1 = go.Figure()
            
            for school in SCHOOL_INFO.keys():
                school_growth = growth_data[school]
                fig_corr1.add_trace(
                    go.Scatter(
                        x=school_growth['잎 수(장)'],
                        y=school_growth['생중량(g)'],
                        mode='markers',
                        name=school,
                        marker=dict(
                            color=SCHOOL_INFO[school]['color'],
                            size=8,
                            opacity=0.6
                        )
                    )
                )
            
            fig_corr1.update_layout(
                title="잎 수 vs 생중량",
                xaxis_title="잎 수 (장)",
                yaxis_title="생중량 (g)",
                height=400,
                font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif", size=12)
            )
            
            st.plotly_chart(fig_corr1, use_container_width=True)
        
        with col2:
            fig_corr2 = go.Figure()
            
            for school in SCHOOL_INFO.keys():
                school_growth = growth_data[school]
                fig_corr2.add_trace(
                    go.Scatter(
                        x=school_growth['지상부 길이(mm)'],
                        y=school_growth['생중량(g)'],
                        mode='markers',
                        name=school,
                        marker=dict(
                            color=SCHOOL_INFO[school]['color'],
                            size=8,
                            opacity=0.6
                        )
                    )
                )
            
            fig_corr2.update_layout(
                title="지상부 길이 vs 생중량",
                xaxis_title="지상부 길이 (mm)",
                yaxis_title="생중량 (g)",
                height=400,
                font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif", size=12)
            )
            
            st.plotly_chart(fig_corr2, use_container_width=True)
        
        # 원본 데이터
        with st.expander("📋 생육 데이터 원본 보기"):
            if selected_school == "전체":
                display_growth = growth_combined
            else:
                display_growth = growth_data[selected_school]
            
            st.dataframe(display_growth, use_container_width=True)
            
            # XLSX 다운로드
            buffer = io.BytesIO()
            display_growth.to_excel(buffer, index=False, engine="openpyxl")
            buffer.seek(0)
            
            st.download_button(
                label="📥 XLSX 다운로드",
                data=buffer,
                file_name=f"{selected_school}_생육데이터.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

if __name__ == "__main__":
    main()
