import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. 페이지 설정 및 디자인 (화이트 테마 + 버튼 효과) ---
st.set_page_config(page_title="한화이글스 단관 투표", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; color: #000000; }
    h1, h2, h3, .stHeader { color: #FF6600 !important; }
    .stTabs [data-baseweb="tab-list"] button { color: #444444; }
    .stTextInput label, .stCheckbox label { color: #000000 !important; font-weight: bold; }

    /* 버튼 기본 스타일: 흰색 배경 + 오렌지 테두리 */
    div.stButton > button {
        background-color: #FFFFFF;
        color: #FF6600;
        border: 2px solid #FF6600;
        border-radius: 8px;
        height: 3.5em;
        font-weight: bold;
        transition: all 0.2s;
    }
    /* 버튼 호버/클릭 효과: 오렌지 배경 + 흰색 글자 */
    div.stButton > button:hover, div.stButton > button:active {
        background-color: #FF6600 !important;
        color: #FFFFFF !important;
        border: 2px solid #FF6600 !important;
    }
    /* 비활성화된 버튼 스타일 */
    div.stButton > button:disabled {
        background-color: #F0F0F0 !important;
        color: #BBBBBB !important;
        border: 2px solid #DDDDDD !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 구글 시트 연결 ---
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

with tab1:
    # 0단계: 정보 입력
    if st.session_state.step == "input":
        st.subheader("📝 정보 입력")
        plus_one = st.checkbox("+1 (동반인이 한 명 더 있나요?)")
        name = st.text_input("이름")
        phone = st.text_input("연락처 (01012345678)")
        
        if st.button("투표 시작하기"):
            if name and phone:
                st.session_state.user_info = {"이름": name, "연락처": phone, "plus_one": plus_one}
                st.session_state.step = "step1"
                st.rerun()
            else:
                st.warning("이름과 연락처를 모두 입력해 주세요.")

    # 1단계: 경기 참석 투표
    elif st.session_state.step == "step1":
        st.subheader(f"🙋‍♂️ {st.session_state.user_info['이름']}님, 직관 오시나요?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🧡 단관참석"):
                st.session_state.user_info['참석'] = "단관참석"
                st.session_state.step = "step2" # 2단계로 이동
                st.rerun()
        with col2:
            st.button("미참석 (비활성)", disabled=True)

    # 2단계: 뒷풀이 참석 투표 (이 부분이 복구되었습니다)
    elif st.session_state.step == "step2":
        st.subheader("🍻 뒷풀이도 함께 하시나요?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("뒷풀이 참석"):
                st.session_state.user_info['뒷풀이'] = "참석"
                st.session_state.step = "confirm"
                st.rerun()
        with col2:
            if st.button("뒷풀이 미참석"):
                st.session_state.user_info['뒷풀이'] = "미참석"
                st.session_state.step = "confirm"
                st.rerun()

    # 최종 확인
    elif st.session_state.step == "confirm":
        st.subheader("✅ 마지막으로 확인해 주세요")
        info = st.session_state.user_info
        msg = f"**{info['이름']}**님\n- 경기: **{info['참석']}**\n- 뒷풀이: **{info['뒷풀이']}**"
        if info['plus_one']:
            msg += "\n- **동반인(+1) 포함**"
        
        st.info(msg)
        
        if st.button("최종 투표 제출"):
            existing_data = get_data()
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            # 데이터 생성
            new_rows = [{"날짜": now_str, "이름": info['이름'], "연락처": info['연락처'], "참석여부": info['참석'], "뒷풀이": info['뒷풀이']}]
            if info['plus_one']:
                new_rows.append({"날짜": now_str, "이름": "+1", "연락처": "-", "참석여부": info['참석'], "뒷풀이": info['뒷풀이']})
            
            updated_df = pd.concat([existing_data, pd.DataFrame(new_rows)], ignore_index=True)
            conn.update(spreadsheet=SHEET_URL, data=updated_df)
            
            st.session_state.step = "done"
            st.rerun()

    # 완료 화면
    elif st.session_state.step == "done":
        st.success("투표가 완료되었습니다! 구글 시트에 기록되었습니다. 🧡")
        if st.button("투표완료 (재투표 하시려면 클릭)"):
            st.session_state.step = "input" # 초기화
            st.rerun()

# --- Tab 2 & 3 (기존과 동일) ---
with tab2:
    st.header("📊 현재 투표 현황")
    data = get_data()
    if not data.empty:
        st.metric("총 참석 인원 (동반인 포함)", f"{len(data)}명")
        st.table(data[["이름", "참석여부", "뒷풀이"]])

with tab3:
    pwd = st.text_input("관리자 암호", type="password")
    if pwd == "eagles1234":
        admin_data = get_data()
        st.dataframe(admin_data)
        csv = admin_data.to_csv(index=False).encode('utf-8-sig')
        st.download_button("데이터 다운로드", data=csv, file_name="eagles_vote.csv")
