import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# --- 1. 디자인 및 설정 ---
st.set_page_config(page_title="한화이글스 단관 시스템", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; color: #000000; }
    h1, h2, h3 { color: #FF6600 !important; }
    div.stButton > button {
        background-color: #FFFFFF; color: #FF6600; border: 2px solid #FF6600;
        border-radius: 8px; height: 3.5em; font-weight: bold; width: 100%;
    }
    div.stButton > button:hover { background-color: #FF6600 !important; color: #FFFFFF !important; }
    div.stButton > button:disabled { background-color: #F0F0F0 !important; color: #BBBBBB !important; border: 2px solid #DDDDDD !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 구글 시트 연결 ---
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
conn = st.connection("gsheets", type=GSheetsConnection)

# 경기 일정 관리용 메인 시트 이름 (이 시트는 미리 만들어두세요)
SCHEDULE_SHEET = "경기일정"

def get_schedule():
    try:
        return conn.read(spreadsheet=SHEET_URL, worksheet=SCHEDULE_SHEET, ttl="0s")
    except:
        return pd.DataFrame(columns=["경기날짜", "상대팀", "경기시간", "투표마감"])

def get_game_data(sheet_name):
    try:
        return conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl="0s")
    except:
        return pd.DataFrame(columns=["날짜", "이름", "연락처", "참석여부", "뒷풀이"])

# --- 3. 세션 상태 초기화 ---
if 'step' not in st.session_state: st.session_state.step = "input"
if 'selected_game' not in st.session_state: st.session_state.selected_game = None

# --- 4. 메인 화면 ---
st.title("🦅 한화이글스 단관 투표")

tab1, tab2, tab3 = st.tabs(["투표하기", "참석 현황", "관리자"])

# --- Tab 1: 투표하기 ---
with tab1:
    sched_df = get_schedule()
    
    if sched_df.empty:
        st.info("등록된 경기 일정이 없습니다. 관리자에게 문의하세요.")
    else:
        # 경기 선택
        game_list = [f"{row['경기날짜']} vs {row['상대팀']}" for _, row in sched_df.iterrows()]
        selected_game_idx = st.selectbox("투표할 경기를 선택하세요", range(len(game_list)), format_func=lambda x: game_list[x])
        game_info = sched_df.iloc[selected_game_idx]
        
        # 마감 시간 체크
        now = datetime.now()
        deadline = datetime.strptime(f"{game_info['경기날짜']} {game_info['투표마감']}", "%Y-%m-%d %H:%M")
        
        if now > deadline:
            st.error(f"⚠️ 해당 경기의 투표가 마감되었습니다. (마감시간: {game_info['투표마감']})")
        else:
            st.success(f"📍 일정: {game_info['경기날짜']} {game_info['경기시간']} / 마감: {game_info['투표마감']}")
            
            # 투표 단계 로직 (이전과 동일하되 selected_game 반영)
            if st.session_state.step == "input":
                plus_one = st.checkbox("+1 (동반인 포함)")
                name = st.text_input("이름")
                phone = st.text_input("연락처")
                if st.button("투표 진행"):
                    if name and phone:
                        st.session_state.user_info = {"이름": name, "연락처": phone, "plus_one": plus_one}
                        st.session_state.step = "step1"
                        st.rerun()

            elif st.session_state.step == "step1":
                st.subheader(f"🙋‍♂️ {st.session_state.user_info['이름']}님, 참석하시나요?")
                if st.button("🧡 단관참석"):
                    st.session_state.user_info['참석'] = "참석"
                    st.session_state.step = "step2"; st.rerun()

            elif st.session_state.step == "step2":
                st.subheader("🍻 뒷풀이 여부")
                c1, c2 = st.columns(2)
                with c1: 
                    if st.button("참석"): st.session_state.user_info['뒷풀이'] = "참석"; st.session_state.step = "confirm"; st.rerun()
                with c2: 
                    if st.button("미참석"): st.session_state.user_info['뒷풀이'] = "미참석"; st.session_state.step = "confirm"; st.rerun()

            elif st.session_state.step == "confirm":
                if st.button("최종 제출"):
                    sheet_name = game_info['경기날짜']
                    existing_data = get_game_data(sheet_name)
                    
                    new_rows = [{"날짜": datetime.now().strftime("%Y-%m-%d %H:%M"), "이름": st.session_state.user_info['이름'], "연락처": st.session_state.user_info['연락처'], "참석여부": "참석", "뒷풀이": st.session_state.user_info['뒷풀이']}]
                    if st.session_state.user_info['plus_one']:
                        new_rows.append({"날짜": "-", "이름": "+1", "연락처": "-", "참석여부": "참석", "뒷풀이": st.session_state.user_info['뒷풀이']})
                    
                    updated_df = pd.concat([existing_data, pd.DataFrame(new_rows)], ignore_index=True)
                    conn.update(spreadsheet=SHEET_URL, worksheet=sheet_name, data=updated_df)
                    st.session_state.step = "done"; st.rerun()

            elif st.session_state.step == "done":
                st.balloons()
                st.success("제출 완료!")
                if st.button("다시 투표 (수정)"): 
                    # 기존 데이터 삭제 로직은 복잡하므로 필요시 추가
                    st.session_state.step = "input"; st.rerun()

# --- Tab 2: 현황판 ---
with tab2:
    if not sched_df.empty:
        sel_game = st.selectbox("현황을 볼 경기 선택", sched_df['경기날짜'])
        view_df = get_game_data(sel_game)
        if not view_df.empty:
            st.metric("총 인원", f"{len(view_df)}명")
            st.table(view_df[["이름", "참석여부", "뒷풀이"]])
        else: st.write("투표 데이터가 없습니다.")

# --- Tab 3: 관리자 (일정 등록) ---
with tab3:
    pwd = st.text_input("Admin Password", type="password")
    if pwd == "eagles1234":
        st.subheader("📅 경기 일정 등록")
        with st.form("schedule_form"):
            g_date = st.date_input("경기 날짜")
            g_time = st.time_input("경기 시간")
            g_opp = st.text_input("상대팀")
            g_dead = st.time_input("투표 마감 시간 (해당 날짜 기준)")
            if st.form_submit_button("일정 추가"):
                new_sched = pd.DataFrame([{
                    "경기날짜": str(g_date), "상대팀": g_opp, 
                    "경기시간": str(g_time)[:5], "투표마감": str(g_dead)[:5]
                }])
                updated_sched = pd.concat([get_schedule(), new_sched], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, worksheet=SCHEDULE_SHEET, data=updated_sched)
                st.success("일정이 등록되었습니다!")
