import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import numpy as np
from datetime import datetime, time

# --- 1. 페이지 설정 및 디자인 ---
st.set_page_config(page_title="한화이글스 단관 시스템 Pro", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; color: #000000; }
    h1, h2, h3, .stHeader { color: #FF6600 !important; }
    * { transition: none !important; animation: none !important; }
    
    div.stButton > button {
        background-color: #FFFFFF; color: #FF6600; border: 2px solid #FF6600;
        border-radius: 8px; height: 3.5em; font-weight: bold; width: 100%;
    }
    div.stButton > button:hover { background-color: #FF6600 !important; color: #FFFFFF !important; }
    
    [data-testid="column"] {
        width: 100% !important;
        flex: 1 1 calc(50% - 1rem) !important;
        min-width: calc(50% - 1rem) !important;
    }
    
    [data-testid="stVerticalBlock"] > div:has(div.stButton) { min-height: 250px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 구글 시트 연결 ---
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
conn = st.connection("gsheets", type=GSheetsConnection)

SCH_SHEET = "경기일정"
ADM_SHEET = "관리자명단"
DATA_SHEET = "투표결과" 

def load_data(sheet_name, columns):
    try:
        return conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl="0s")
    except:
        return pd.DataFrame(columns=columns)

# --- 3. 세션 상태 초기화 ---
if 'is_admin' not in st.session_state: st.session_state.is_admin = False
if 'step' not in st.session_state: st.session_state.step = "input"
if 'user_info' not in st.session_state: st.session_state.user_info = {}
if 'selected_game' not in st.session_state: st.session_state.selected_game = None

# --- 4. 메인 화면 ---
st.title("⚾ 한화이글스 단관 모집")

tab_titles = ["투표하기", "참석 현황", "관리자 인증"]
if st.session_state.is_admin:
    tab_titles.append("⚙️ 관리자 설정")

tabs = st.tabs(tab_titles)

# --- Tab 1: 투표하기 (기존 로직 유지) ---
with tabs[0]:
    sched_df = load_data(SCH_SHEET, ["경기날짜", "상대팀", "경기시간", "투표마감"])
    if sched_df.empty:
        st.info("현재 등록된 경기 일정이 없습니다.")
    else:
        game_list = [f"{row['경기날짜']} vs {row['상대팀']}" for _, row in sched_df.iterrows()]
        if st.session_state.step != "done":
            selected_game_idx = st.selectbox("투표할 경기를 선택하세요", range(len(game_list)), format_func=lambda x: game_list[x], key="game_select")
            game_info = sched_df.iloc[selected_game_idx]
            st.session_state.selected_game = game_list[selected_game_idx]
            
            try:
                deadline = datetime.strptime(game_info['투표마감'], "%Y-%m-%d %H:%M")
                if datetime.now() > deadline:
                    st.error(f"⚠️ 투표 마감: {game_info['투표마감']}")
                    current_step = "locked"
                else:
                    st.success(f"✅ 투표 가능 (마감: {game_info['투표마감']})")
                    current_step = st.session_state.step
            except: current_step = "locked"

            if current_step == "input":
                st.subheader("📝 정보 입력")
                plus_one = st.checkbox("+1 (동반인 포함)")
                name = st.text_input("이름")
                phone = st.text_input("연락처")
                if st.button("투표 시작"):
                    if name and phone:
                        st.session_state.user_info = {"이름": name, "연락처": phone, "plus_one": plus_one}
                        st.session_state.step = "step1"; st.rerun()

            elif current_step == "step1":
                st.subheader(f"🙋‍♂️ {st.session_state.user_info['이름']}님, 직관 오시나요?")
                if st.button("🧡 단관참석"):
                    st.session_state.user_info['참석'] = "참석"; st.session_state.step = "step2"; st.rerun()

            elif current_step == "step2":
                st.subheader("🍻 뒷풀이 여부")
                c1, c2 = st.columns(2)
                with c1: 
                    if st.button("참석"): 
                        st.session_state.user_info['뒷풀이'] = "참석"; st.session_state.step = "confirm"; st.rerun()
                with c2: 
                    if st.button("미참석"): 
                        st.session_state.user_info['뒷풀이'] = "미참석"; st.session_state.step = "confirm"; st.rerun()

            elif current_step == "confirm":
                st.subheader("✅ 최종 확인")
                if st.button("최종 제출"):
                    existing_data = load_data(DATA_SHEET, ["경기정보", "날짜", "이름", "연락처", "참석여부", "뒷풀이"])
                    game_tag = st.session_state.selected_game
                    new_rows = [{"경기정보": game_tag, "날짜": datetime.now().strftime("%Y-%m-%d %H:%M"), "이름": st.session_state.user_info['이름'], "연락처": st.session_state.user_info['연락처'], "참석여부": "참석", "뒷풀이": st.session_state.user_info['뒷풀이']}]
                    if st.session_state.user_info['plus_one']:
                        new_rows.append({"경기정보": game_tag, "날짜": "-", "이름": "+1", "연락처": "-", "참석여부": "참석", "뒷풀이": st.session_state.user_info['뒷풀이']})
                    conn.update(spreadsheet=SHEET_URL, worksheet=DATA_SHEET, data=pd.concat([existing_data, pd.DataFrame(new_rows)], ignore_index=True))
                    st.session_state.step = "done"; st.rerun()
        else:
            st.success(f"🎉 {st.session_state.selected_game} 경기 투표를 완료했습니다!")
            if st.button("🔄 다시 투표하기 (재투표)"):
                st.session_state.step = "input"; st.session_state.user_info = {}; st.rerun()

# --- Tab 2: 참석 현황 (순번 추가 업데이트) ---
with tabs[1]:
    sched_df = load_data(SCH_SHEET, ["경기날짜", "상대팀"])
    if not sched_df.empty:
        game_list = [f"{row['경기날짜']} vs {row['상대팀']}" for _, row in sched_df.iterrows()]
        default_idx = game_list.index(st.session_state.selected_game) if st.session_state.selected_game in game_list else 0
        selected_view = st.selectbox("현황 확인할 경기 선택", game_list, index=default_idx)
        
        all_data = load_data(DATA_SHEET, ["경기정보", "날짜", "이름", "연락처", "참석여부", "뒷풀이"])
        view_df = all_data[all_data['경기정보'] == selected_view].copy()
        
        if not view_df.empty:
            st.metric("총 인원 (동반인 포함)", f"{len(view_df)}명")
            
            # --- 순번(No.) 열 생성 ---
            view_df.reset_index(drop=True, inplace=True) # 기존 인덱스 초기화
            view_df.index = view_df.index + 1 # 1번부터 시작하도록 설정
            view_df.index.name = "No." # 인덱스 이름을 No.로 설정
            
            # 표 표시 (인덱스를 포함하여 표시)
            st.table(view
