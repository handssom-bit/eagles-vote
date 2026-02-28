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
    </style>
    """, unsafe_allow_html=True)

# --- 2. 구글 시트 연결 ---
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
conn = st.connection("gsheets", type=GSheetsConnection)

SCH_SHEET = "경기일정"
ADM_SHEET = "관리자명단"
DEFAULT_DATA_SHEET = "투표결과" # 개별 탭 없을 때 저장될 기본 탭
COLS = ["경기정보", "경기장소", "날짜", "이름", "연락처", "참석여부", "뒷풀이"]

def load_data(sheet_name, columns=COLS):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl="0s")
        if df is None or df.empty: return pd.DataFrame(columns=columns)
        return df
    except: return pd.DataFrame(columns=columns)

# --- 3. 세션 상태 초기화 (중요: 관리자 인증 상태 유지) ---
if 'is_admin' not in st.session_state: st.session_state.is_admin = False
if 'step' not in st.session_state: st.session_state.step = "input"
if 'user_info' not in st.session_state: st.session_state.user_info = {}
if 'selected_game_info' not in st.session_state: st.session_state.selected_game_info = {}

# --- 4. 메인 화면 ---
st.title("⚾ 한화이글스 단관 모집")
# 관리자 인증 상태에 따라 탭 메뉴가 유동적으로 변합니다.
tab_list = ["투표하기", "참석 현황", "관리자 인증"]
if st.session_state.is_admin:
    tab_list.append("⚙️ 관리자 설정")

tabs = st.tabs(tab_list)

# --- Tab 1: 투표하기 ---
with tabs[0]:
    sched_df = load_data(SCH_SHEET, ["경기날짜", "상대팀", "경기시간", "투표마감", "경기장소"])
    
    if sched_df.empty:
        st.info("현재 등록된 경기 일정이 없습니다.")
    else:
        if st.session_state.step == "input":
            st.subheader("📢 투표하실 경기를 선택해 주세요")
            for idx, row in sched_df.iterrows():
                if pd.isna(row['경기날짜']): continue
                loc_txt = f" @{row['경기장소']}" if row['경기장소'] else ""
                btn_label = f"🧡 {row['경기날짜']} vs {row['상대팀']} ({row['경기시간']}){loc_txt}"
                if st.button(btn_label, key=f"game_v_{idx}"):
                    st.session_state.selected_game_info = row.to_dict()
                    st.session_state.step = "info_input"; st.rerun()

        elif st.session_state.step == "info_input":
            info = st.session_state.selected_game_info
            st.subheader(f"📝 [{info['경기날짜']}] 정보 입력")
            name = st.text_input("이름", key="user_name")
            phone = st.text_input("연락처", key="user_phone")
            plus_one = st.checkbox("+1 (동반인 포함)", key="user_plus")
            
            # 이전 버튼 삭제 요청 반영 -> 다음 버튼만 노출
            if st.button("다음 단계", key="go_to_step1"):
                if name and phone:
                    st.session_state.user_info = {"이름": name, "연락처": phone, "plus_one": plus_one}
                    st.session_state.step = "step1"; st.rerun()
                else: st.warning("이름과 연락처를 모두 입력해 주세요.")

        elif st.session_state.step == "step1":
            st.subheader(f"🙋‍♂️ {st.session_state.user_info['이름']}님, 직관 오시나요?")
            if st.button("🧡 단관참석", key="btn_attend"):
                st.session_state.user_info['참석'] = "참석"; st.session_state.step = "step2"; st.rerun()

        elif st.session_state.step == "step2":
            st.subheader("🍻 뒷풀이 여부")
            c1, c2 = st.columns(2)
            if c1.button("참석", key="btn_party_y"): 
                st.session_state.user_info['뒷풀이'] = "참석"; st.session_state.step = "confirm"; st.rerun()
            if c2.button("미참석", key="btn_party_n"): 
                st.session_state.user_info['뒷풀이'] = "미참석"; st.session_state.step = "confirm"; st.rerun()

        elif st.session_state.step == "confirm":
            info = st.session_state.selected_game_info
            st.warning(f"최종 투표: {info['경기날짜']} vs {info['상대팀']}")
            if st.button("최종 투표 제출", key="btn_final_submit"):
                user = st.session_state.user_info
                target_sheet = str(info['경기날짜']).strip()
                
                new_entry = {
                    "경기정보": f"{info['경기날짜']} vs {info['상대팀']}",
                    "경기장소": info['경기장소'],
                    "날짜": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "이름": user['이름'], "연락처": user['연락처'], "참석여부": "참석", "뒷풀이": user['뒷풀이']
                }
                
                # 재투표/덮어쓰기 로직 포함
                df = load_data(target_sheet)
                if not df.empty:
                    df = df[~((df['이름'] == user['이름']) & (df['연락처'] == user['연락처']))]
                
                final_list = [new_entry]
                if user.get('plus_one'):
                    final_list.append({**new_entry, "이름": "+1", "연락처": "-", "날짜": "-"})
                
                updated_df = pd.concat([df, pd.DataFrame(final_list)], ignore_index=True)
                
                try:
                    conn.update(spreadsheet=SHEET_URL, worksheet=target_sheet, data=updated_df)
                except: # 날짜별 탭이 없으면 기본 탭에 저장
                    df_def = load_data(DEFAULT_DATA_SHEET)
                    updated_def = pd.concat([df_def, pd.DataFrame(final_list)], ignore_index=True)
                    conn.update(spreadsheet=SHEET_URL, worksheet=DEFAULT_DATA_SHEET, data=updated_def)
                
                st.session_state.step = "done"; st.rerun()

        elif st.session_state.step == "done":
            st.success("🎉 투표가 성공적으로 완료되었습니다!"); st.balloons()
            if st.button("🔄 다른 경기 투표하기", key="btn_reset"):
                st.session_state.step = "input"; st.session_state.user_info = {}; st.rerun()

# --- Tab 2: 참석 현황 ---
with tabs[1]:
    sched_df = load_data(SCH_SHEET, ["경기날짜", "상대팀"])
    if not sched_df.empty:
        game_dates = sched_df['경기날짜'].unique().tolist()
        sel_date = st.selectbox("현황 확인할 날짜 선택", game_dates, key="view_sel_date")
        res_df = load_data(sel_date)
        if not res_df.empty:
            st.metric("현재 참석 인원", f"{len(res_df)}명")
            st.table(res_df.assign(No=lambda x: range(1, len(x)+1))[["No", "이름", "참석여부", "뒷풀이"]])
        else: st.info("해당 날짜에 등록된 투표가 아직 없습니다.")

# --- Tab 3: 관리자 인증 (확실히 복구됨) ---
with tabs[2]:
    if not st.session_state.is_admin:
        st.subheader("🔐 관리자 로그인")
        adm_n = st.text_input("관리자 성함", key="login_adm_n")
        adm_p = st.text_input("관리자 연락처", type="password", key="login_adm_p")
        if st.button("인증하기", key="btn_adm_login"):
            if adm_n == "윤상성" and adm_p == "01032200995":
                st.session_state.is_admin = True; st.rerun()
            else:
                adm_list = load_data(ADM_SHEET, ["이름", "연락처"])
                if not adm_list[(adm_list['이름'] == adm_n) & (adm_list['연락처'].astype(str) == adm_p)].empty:
                    st.session_state.is_admin = True; st.rerun()
                else: st.error("관리자 정보가 일치하지 않습니다.")
    else:
        st.success("✅ 관리자 모드로 접속 중입니다.")
        if st.button("로그아웃", key="btn_adm_logout"):
            st.session_state.is_admin = False; st.rerun()

# --- Tab 4: 관리자 설정 (관리자 전용 메뉴) ---
if st.session_state.is_admin:
    with tabs[3]:
        st.header("⚙️ 관리자 제어 센터")
        with st.expander("📅 일정 등록", expanded=False):
            with st.form("add_game_final"):
                c1, c2 = st.columns(2)
                g_date = c1.date_input("경기 날짜")
                g_opp = c2.text_input("상대팀")
                g_loc = st.text_input("경기 장소")
                pm_times = [time(h, m) for h in range(12, 24) for m in [0, 30]]
                g_time = c1.selectbox("시작 시간", pm_times, format_func=lambda x: x.strftime("%H:%M"))
                d_date = st.date_input("마감 날짜", value=g_date)
                d_time = st.time_input("마감 시간")
                if st.form_submit_button("일정 저장"):
                    dead_str = datetime.combine(d_date, d_time).strftime("%Y-%m-%d %H:%M")
                    new_game = pd.DataFrame([{"경기날짜": str(g_date), "상대팀": g_opp, "경기시간": g_time.strftime("%H:%M"), "투표마감": dead_str, "경기장소": g_loc}])
                    old_sch = load_data(SCH_SHEET, ["경기날짜", "상대팀", "경기시간", "투표마감", "경기장소"])
                    conn.update(spreadsheet=SHEET_URL, worksheet=SCH_SHEET, data=pd.concat([old_sch, new_game], ignore_index=True))
                    st.success("✅ 일정이 등록되었습니다."); st.rerun()

        with st.expander("⚠️ 일정 및 데이터 삭제", expanded=False):
            sch_list = load_data(SCH_SHEET, ["경기날짜", "상대팀"])
            if not sch_list.empty:
                opts = [f"{r['경기날짜']} vs {r['상대팀']}" for _, r in sch_list.iterrows()]
                target = st.selectbox("삭제할 일정", opts, key="sel_del_game")
                if st.button("🔥 삭제 실행", disabled=not st.checkbox("데이터 삭제에 동의합니다.", key="chk_del")):
                    d_key = target.split(" vs ")[0]
                    conn.update(spreadsheet=SHEET_URL, worksheet=SCH_SHEET, data=sch_list[sch_list['경기날짜'] != d_key])
                    try: conn.update(spreadsheet=SHEET_URL, worksheet=d_key, data=pd.DataFrame(columns=COLS))
                    except: pass
                    st.success("삭제 완료!"); st.rerun()
