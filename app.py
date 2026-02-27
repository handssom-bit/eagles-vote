import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. 페이지 설정 및 디자인 (화이트 테마) ---
st.set_page_config(page_title="한화이글스 단관 투표", layout="centered")

st.markdown("""
    <style>
    /* 전체 배경 흰색 및 글자색 검정 */
    .stApp {
        background-color: #FFFFFF;
        color: #000000;
    }
    
    /* 탭 메뉴 글자색 조정 */
    .stTabs [data-baseweb="tab-list"] button {
        color: #444444;
    }

    /* 제목 및 안내문구 색상 (한화 오렌지) */
    h1, h2, h3, .stHeader {
        color: #FF6600 !format;
    }
    
    /* 입력창 라벨 색상 */
    .stTextInput label, .stCheckbox label {
        color: #000000 !important;
        font-weight: bold;
    }

    /* 버튼 기본 스타일 (흰색 배경 + 오렌지 테두리) */
    div.stButton > button {
        background-color: #FFFFFF;
        color: #FF6600;
        border: 2px solid #FF6600;
        border-radius: 8px;
        height: 3em;
        transition: all 0.3s;
    }

    /* 버튼에 마우스 올리거나 클릭했을 때 (오렌지 배경 + 흰색 글자) */
    div.stButton > button:hover, div.stButton > button:active {
        background-color: #FF6600 !important;
        color: #FFFFFF !important;
    }
    
    /* 투표 결과 등 메트릭 숫자 색상 */
    [data-testid="stMetricValue"] {
        color: #FF6600 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 구글 시트 연결 (기존과 동일) ---
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        return conn.read(spreadsheet=SHEET_URL, ttl="0s")
    except:
        return pd.DataFrame(columns=["날짜", "이름", "연락처", "참석여부", "뒷풀이"])

# --- 3. 세션 상태 초기화 ---
if 'step' not in st.session_state:
    st.session_state.step = "input"
if 'user_info' not in st.session_state:
    st.session_state.user_info = {}

# --- 4. 메인 화면 ---
st.title("⚾ 한화이글스 단관 모집")
st.markdown("#### 승리를 위하여! 팬 여러분의 참석 여부를 알려주세요.")

tab1, tab2, tab3 = st.tabs(["투표하기", "참석 현황", "관리자"])

# --- Tab 1: 투표하기 ---
with tab1:
    if st.session_state.step == "input":
        st.subheader("📝 정보 입력")
        plus_one = st.checkbox("+1 (동반인이 한 명 더 있나요?)")
        name = st.text_input("이름")
        phone = st.text_input("연락처 (예: 01012345678)")
        
        if st.button("투표 시작하기"):
            if name and phone:
                st.session_state.user_info = {"이름": name, "연락처": phone, "plus_one": plus_one}
                st.session_state.step = "step1"
                st.rerun()
            else:
                st.warning("이름과 연락처를 모두 입력해 주세요.")

    elif st.session_state.step == "step1":
        st.subheader(f"🙋‍♂️ {st.session_state.user_info['이름']}님, 경기 보러 오시나요?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🧡 단관참석"):
                st.session_state.user_info['참석'] = "단관참석"
                st.session_state.step = "step2"
                st.rerun()
        with col2:
            st.button("미참석 (비활성)", disabled=True)

    # ... (뒷풀이 투표, 확인, 완료 로직은 디자인이 자동 적용되므로 기존 코드 유지) ...
