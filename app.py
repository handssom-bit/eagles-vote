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
COLS = ["경기정보", "경기장소", "날짜", "이름", "연락처", "참석여부", "뒷풀이"]

def load_data(sheet_name, columns=COLS):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl="0s")
        if df is None or df.empty: return pd.DataFrame(columns=columns)
        return df
    except: return pd.DataFrame(columns=columns)

# --- 3. 세션 상태 초기화 ---
if 'is_admin' not in st.session_state: st.session_state.is_admin = False
if 'step' not in st.session_state: st.session_state.step = "input"
if 'user_info' not in st.session_state: st.session_state.user_info = {}
if 'selected_game_info' not in st.session_state: st.session_state.selected_game_info = {}

# --- 4. 메인 화면 ---
st.title("⚾ 한화이글스 단관 모집")
tabs = st.tabs(["투표하기", "참석 현황", "관리자 인증"] + (["⚙️ 관리자 설정"] if st.session_state.is_admin else []))

# --- Tab 1: 투표하기 ---
with tabs[0]:
    sched_df = load_data(SCH_SHEET, ["경기날짜", "상대팀", "경기시간", "투표마감", "경기장소"])
    if sched_df.empty:
        st.info("등록된 경기 일정이 없습니다.")
    else:
        if st.session_state.step == "input":
            st.subheader("📢 투표하실 경기를 선택해 주세요")
            for idx, row in sched_df.iterrows():
                if pd.isna(row['경기날짜']): continue
                loc_txt = f" @{row['경기장소']}" if row['경기장소'] else ""
                btn_label = f"🧡 {row['경기날짜']} vs {row['상대팀']} ({row['경기시간']}){loc_txt}"
                if st.button(btn_label, key=f"v_btn_{idx}"):
                    st.session_state.selected_game_info = row.to_dict()
                    st.session_state.step = "info_input"; st.rerun()
        # (중략: info_input, step1, step2 로직 유지 - 위 답변의 재투표/덮어쓰기 로직 적용)
        elif st.session_state.step == "info_input":
            info = st.session_state.selected_game_info
            st.subheader(f"📝 [{info['경기날짜']}] 정보 입력")
            name = st.text_input("이름", key="vote_name")
            phone = st.text_input("연락처", key="vote_phone")
            plus_one = st.checkbox("+1 (동반인 포함)", key="vote_plus")
            c1, c2 = st.columns(2)
            if c1.button("이전"): st.session_state.step = "input"; st.rerun()
            if c2.button("다음"):
                if name and phone:
                    st.session_state.user_info = {"이름": name, "연락처": phone, "plus_one": plus_one}
                    st.session_state.step = "step1"; st.rerun()
        # (이후 최종 제출까지의 로직 생략 없이 그대로 유지하여 적용하세요)

# --- Tab 2: 참석 현황 ---
with tabs[1]:
    sched_df = load_data(SCH_SHEET, ["경기날짜", "상대팀"])
    if not sched_df.empty:
        game_dates = sched_df['경기날짜'].unique().tolist()
        sel_date = st.selectbox("날짜별 현황 확인", game_dates, key="view_date_sel")
        res_df = load_data(sel_date)
        if not res_df.empty:
            st.metric("현재 참석", f"{len(res_df)}명")
            st.table(res_df.assign(No=lambda x: range(1, len(x)+1))[["No", "이름", "참석여부", "뒷풀이"]])
        else: st.info("아직 투표 데이터가 없습니다.")

# --- Tab 3: 관리자 인증 (복구된 화면) ---
with tabs[2]:
    if not st.session_state.is_admin:
        st.subheader("🔐 관리자 로그인")
        admin_name = st.text_input("이름", key="adm_login_n")
        admin_phone = st.text_input("연락처", type="password", key="adm_login_p")
        if st.button("로그인", key="adm_login_btn"):
            if admin_name == "윤상성" and admin_phone == "01032200995":
                st.session_state.is_admin = True; st.rerun()
            else:
                adm_list = load_data(ADM_SHEET, ["이름", "연락처"])
                if not adm_list[(adm_list['이름'] == admin_name) & (adm_list['연락처'].astype(str) == admin_phone)].empty:
                    st.session_state.is_admin = True; st.rerun()
                else: st.error("정보가 일치하지 않습니다.")
    else:
        st.success("✅ 관리자 권한으로 인증되었습니다.")
        if st.button("로그아웃", key="adm_logout"):
            st.session_state.is_admin = False; st.rerun()

# --- Tab 4: 관리자 설정 (기능 완전 복구) ---
if st.session_state.is_admin:
    with tabs[3]:
        st.header("⚙️ 관리자 제어 센터")
        
        with st.expander("📅 일정 등록", expanded=False):
            with st.form("add_game_form"):
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
                    st.success("✅ 일정 등록 완료!"); st.rerun()

        with st.expander("👤 관리자 명단 관리", expanded=False):
            st.subheader("신규 등록")
            n_name = st.text_input("새 관리자 이름", key="add_adm_n")
            n_phone = st.text_input("새 관리자 연락처", key="add_adm_p")
            if st.button("등록하기", key="add_adm_btn"):
                old_adm = load_data(ADM_SHEET, ["이름", "연락처"])
                conn.update(spreadsheet=SHEET_URL, worksheet=ADM_SHEET, data=pd.concat([old_adm, pd.DataFrame([{"이름": n_name, "연락처": n_phone}])], ignore_index=True))
                st.success("등록 완료"); st.rerun()
            
            st.divider()
            st.subheader("관리자 삭제")
            curr_adm = load_data(ADM_SHEET, ["이름", "연락처"])
            if not curr_adm.empty:
                del_adm = st.selectbox("삭제할 관리자", curr_adm[curr_adm['이름'] != "윤상성"]['이름'].tolist(), key="del_adm_sel")
                if st.button("삭제 실행", key="del_adm_btn"):
                    conn.update(spreadsheet=SHEET_URL, worksheet=ADM_SHEET, data=curr_adm[curr_adm['이름'] != del_adm])
                    st.success("삭제 완료"); st.rerun()

        with st.expander("⚠️ 일정 및 데이터 삭제", expanded=False):
            sch_list = load_data(SCH_SHEET, ["경기날짜", "상대팀"])
            if not sch_list.empty:
                opts = [f"{r['경기날짜']} vs {r['상대팀']}" for _, r in sch_list.iterrows()]
                target_del = st.selectbox("삭제할 일정 선택", opts, key="del_game_sel")
                confirm = st.checkbox("해당 날짜의 투표 명단 탭 데이터도 모두 비우시겠습니까?", key="del_game_chk")
                if st.button("🔥 일정 및 명단 삭제", key="del_game_btn", disabled=not confirm):
                    date_key = target_del.split(" vs ")[0]
                    conn.update(spreadsheet=SHEET_URL, worksheet=SCH_SHEET, data=sch_list[sch_list['경기날짜'] != date_key])
                    try:
                        conn.update(spreadsheet=SHEET_URL, worksheet=date_key, data=pd.DataFrame(columns=COLS))
                    except: pass
                    st.success("삭제 완료!"); st.rerun()
