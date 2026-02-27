import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
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

# --- Tab 1: 투표하기 ---
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

# --- Tab 2: 참석 현황 ---
with tabs[1]:
    sched_df = load_data(SCH_SHEET, ["경기날짜", "상대팀"])
    if not sched_df.empty:
        game_list = [f"{row['경기날짜']} vs {row['상대팀']}" for _, row in sched_df.iterrows()]
        default_idx = game_list.index(st.session_state.selected_game) if st.session_state.selected_game in game_list else 0
        selected_view = st.selectbox("현황 확인할 경기 선택", game_list, index=default_idx)
        all_data = load_data(DATA_SHEET, ["경기정보", "날짜", "이름", "연락처", "참석여부", "뒷풀이"])
        view_df = all_data[all_data['경기정보'] == selected_view]
        if not view_df.empty:
            st.metric("총 인원 (동반인 포함)", f"{len(view_df)}명")
            st.table(view_df[["이름", "참석여부", "뒷풀이"]])
        else: st.info("아직 투표 데이터가 없습니다.")

# --- Tab 3: 관리자 인증 ---
with tabs[2]:
    if not st.session_state.is_admin:
        st.subheader("🔐 관리자 로그인")
        admin_name = st.text_input("관리자 이름")
        admin_phone = st.text_input("관리자 연락처(숫자만)", type="password")
        if st.button("로그인"):
            if admin_name == "윤상성" and admin_phone == "01032200995":
                st.session_state.is_admin = True; st.rerun()
            else:
                admin_list = load_data(ADM_SHEET, ["이름", "연락처"])
                if not admin_list[(admin_list['이름'] == admin_name) & (admin_list['연락처'].astype(str) == admin_phone)].empty:
                    st.session_state.is_admin = True; st.rerun()
                else: st.error("정보 불일치")
    else:
        st.success("✅ 관리자 로그인 중")
        if st.button("로그아웃"): st.session_state.is_admin = False; st.rerun()

# --- Tab 4: 관리자 설정 (오후 30분 단위 적용) ---
if st.session_state.is_admin:
    with tabs[3]:
        st.header("⚙️ 관리자 제어 센터")
        with st.expander("📅 일정 등록", expanded=True):
            with st.form("add_form"):
                c1, c2 = st.columns(2)
                g_date = c1.date_input("경기 날짜")
                g_opp = c2.text_input("상대팀")
                
                # --- 경기 시작 시간 (오후 30분 단위 드롭다운) ---
                pm_times = []
                for h in range(12, 24):
                    pm_times.append(time(h, 0))
                    pm_times.append(time(h, 30))
                
                g_time = c1.selectbox("경기 시작 시간 (오후)", pm_times, format_func=lambda x: x.strftime("%H:%M"))
                
                st.divider()
                st.subheader("투표 마감 일시 설정")
                d_date = st.date_input("마감 날짜", value=g_date)
                d_time = st.time_input("마감 시간") 
                
                if st.form_submit_button("일정 저장"):
                    dead_str = datetime.combine(d_date, d_time).strftime("%Y-%m-%d %H:%M")
                    new_game = pd.DataFrame([{"경기날짜": str(g_date), "상대팀": g_opp, "경기시간": g_time.strftime("%H:%M"), "투표마감": dead_str}])
                    old_sch = load_data(SCH_SHEET, ["경기날짜", "상대팀", "경기시간", "투표마감"])
                    conn.update(spreadsheet=SHEET_URL, worksheet=SCH_SHEET, data=pd.concat([old_sch, new_game], ignore_index=True))
                    st.success("✅ 일정 등록 완료!"); st.rerun()

        # ... 명단 관리 및 삭제 로직 동일 ...
        with st.expander("👤 관리자 명단 관리", expanded=False):
            st.subheader("➕ 신규 관리자 추가")
            new_adm_name = st.text_input("새 관리자 이름")
            new_adm_phone = st.text_input("새 관리자 연락처(숫자만)")
            if st.button("관리자 등록"):
                if new_adm_name and new_adm_phone:
                    old_admins = load_data(ADM_SHEET, ["이름", "연락처"])
                    new_adm_df = pd.DataFrame([{"이름": new_adm_name, "연락처": new_adm_phone}])
                    conn.update(spreadsheet=SHEET_URL, worksheet=ADM_SHEET, data=pd.concat([old_admins, new_adm_df], ignore_index=True))
                    st.success(f"✅ {new_adm_name} 등록 완료!"); st.rerun()

        with st.expander("⚠️ 일정 및 데이터 삭제", expanded=False):
            sch_to_del = load_data(SCH_SHEET, ["경기날짜", "상대팀"])
            if not sch_to_del.empty:
                opts = [f"{r['경기날짜']} vs {r['상대팀']}" for _, r in sch_to_del.iterrows()]
                sel_del = st.selectbox("삭제할 일정 선택", opts)
                confirm_check = st.checkbox(f"위의 '{sel_del}' 일정과 데이터를 정말로 삭제하시겠습니까?")
                if st.button("🔥 일정 및 데이터 삭제", disabled=not confirm_check):
                    updated_sch = sch_to_del.drop(sch_to_del.index[opts.index(sel_del)])
                    conn.update(spreadsheet=SHEET_URL, worksheet=SCH_SHEET, data=updated_sch)
                    all_data = load_data(DATA_SHEET, ["경기정보", "날짜", "이름", "연락처", "참석여부", "뒷풀이"])
                    conn.update(spreadsheet=SHEET_URL, worksheet=DATA_SHEET, data=all_data[all_data['경기정보'] != sel_del])
                    st.success("🗑️ 삭제 완료"); st.rerun()
