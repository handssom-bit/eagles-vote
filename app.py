import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. 디자인 및 설정 ---
st.set_page_config(page_title="한화이글스 단관 시스템 Pro", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; color: #000000; }
    h1, h2, h3 { color: #FF6600 !important; }
    /* 버튼 스타일 */
    div.stButton > button {
        background-color: #FFFFFF; color: #FF6600; border: 2px solid #FF6600;
        border-radius: 8px; font-weight: bold; width: 100%;
    }
    div.stButton > button:hover { background-color: #FF6600 !important; color: #FFFFFF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 구글 시트 연결 ---
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
conn = st.connection("gsheets", type=GSheetsConnection)

# 시트 이름 정의
SCH_SHEET = "경기일정"
ADM_SHEET = "관리자명단"

# 데이터 불러오기 함수
def load_data(sheet_name, columns):
    try:
        return conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl="0s")
    except:
        return pd.DataFrame(columns=columns)

# --- 3. 세션 상태 초기화 ---
if 'is_admin' not in st.session_state: st.session_state.is_admin = False
if 'step' not in st.session_state: st.session_state.step = "input"

# --- 4. 메인 화면 ---
st.title("🦅 한화이글스 단관 시스템 Pro")

# 탭 구성 (관리자 전용 탭은 조건부 노출)
tab_titles = ["투표하기", "참석 현황", "관리자 인증"]
if st.session_state.is_admin:
    tab_titles.append("⚙️ 관리자 설정")

tabs = st.tabs(tab_titles)

# --- Tab 1 & 2: 투표 및 현황 (이전 로직 활용) ---
with tabs[0]:
    st.subheader("⚾ 경기 투표")
    sched_df = load_data(SCH_SHEET, ["경기날짜", "상대팀", "경기시간", "투표마감"])
    if sched_df.empty:
        st.info("현재 등록된 경기 일정이 없습니다.")
    else:
        # 경기 선택 및 투표 로직 실행 (생략된 부분은 이전 코드와 동일)
        st.write("경기를 선택하여 투표를 진행해 주세요.")

with tabs[1]:
    st.subheader("📊 실시간 현황")
    # 선택된 경기의 탭 데이터를 불러와 표로 표시

# --- Tab 2 (인증): 관리자 로그인 ---
with tabs[2]:
    if not st.session_state.is_admin:
        st.subheader("🔐 관리자 로그인")
        admin_name = st.text_input("관리자 이름")
        admin_phone = st.text_input("관리자 연락처", type="password")
        
        if st.button("로그인"):
            # 관리자 명단 확인
            admin_list = load_data(ADM_SHEET, ["이름", "연락처"])
            
            # 첫 관리자 설정 (명단이 비어있을 때 본인 등록용)
            if admin_list.empty and admin_name == "본인이름" and admin_phone == "본인전화번호":
                new_admin = pd.DataFrame([{"이름": admin_name, "연락처": admin_phone}])
                conn.update(spreadsheet=SHEET_URL, worksheet=ADM_SHEET, data=new_admin)
                st.session_state.is_admin = True
                st.rerun()
            
            # 명단 대조
            elif not admin_list[(admin_list['이름'] == admin_name) & (admin_list['연락처'] == admin_phone)].empty:
                st.session_state.is_admin = True
                st.success(f"{admin_name} 관리자님, 환영합니다!")
                st.rerun()
            else:
                st.error("관리자 명단에 없거나 정보가 일치하지 않습니다.")
    else:
        st.success("✅ 현재 관리자 권한으로 접속 중입니다.")
        if st.button("로그아웃"):
            st.session_state.is_admin = False
            st.rerun()

# --- Tab 3 (관리): 관리자 전용 페이지 (관리자만 보임) ---
if st.session_state.is_admin:
    with tabs[3]:
        st.header("⚙️ 관리자 제어 센터")
        
        # 1. 경기 일정 등록
        with st.expander("📅 새 경기 일정 등록", expanded=True):
            with st.form("new_game_form"):
                col1, col2 = st.columns(2)
                g_date = col1.date_input("경기 날짜")
                g_opp = col2.text_input("상대 팀 (예: LG, 삼성)")
                g_time = col1.time_input("경기 시작 시간")
                g_dead = col2.text_input("투표 마감 시간 (예: 15:00)")
                
                if st.form_submit_button("일정 저장"):
                    new_game = pd.DataFrame([{
                        "경기날짜": str(g_date), "상대팀": g_opp,
                        "경기시간": str(g_time)[:5], "투표마감": g_dead
                    }])
                    old_sched = load_data(SCH_SHEET, ["경기날짜", "상대팀", "경기시간", "투표마감"])
                    conn.update(spreadsheet=SHEET_URL, worksheet=SCH_SHEET, data=pd.concat([old_sched, new_game], ignore_index=True))
                    st.success(f"{g_date} 경기가 등록되었습니다!")

        # 2. 관리자 명단 관리
        with st.expander("👥 관리자 명단 관리"):
            curr_admins = load_data(ADM_SHEET, ["이름", "연락처"])
            st.write("현재 관리자 목록")
            st.table(curr_admins["이름"]) # 보안상 이름만 표시
            
            st.divider()
            st.subheader("➕ 관리자 추가")
            new_adm_name = st.text_input("신규 관리자 이름")
            new_adm_phone = st.text_input("신규 관리자 연락처")
            if st.button("관리자 임명"):
                add_adm = pd.DataFrame([{"이름": new_adm_name, "연락처": new_adm_phone}])
                conn.update(spreadsheet=SHEET_URL, worksheet=ADM_SHEET, data=pd.concat([curr_admins, add_adm], ignore_index=True))
                st.success("새로운 관리자가 등록되었습니다.")
                st.rerun()

            st.subheader("➖ 관리자 삭제")
            del_adm = st.selectbox("삭제할 관리자 선택", curr_admins["이름"])
            if st.button("관리자 해임"):
                updated_admins = curr_admins[curr_admins["이름"] != del_adm]
                conn.update(spreadsheet=SHEET_URL, worksheet=ADM_SHEET, data=updated_admins)
                st.success("해당 관리자가 삭제되었습니다.")
                st.rerun()
