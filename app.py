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
    
    [data-testid="column"] { flex: 1 1 calc(50% - 1rem) !important; min-width: calc(50% - 1rem) !important; }
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
        df = conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl="0s")
        return df if not df.empty else pd.DataFrame(columns=columns)
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

# --- Tab 1: 투표하기 (드롭다운 제거 버전) ---
with tabs[0]:
    sched_df = load_data(SCH_SHEET, ["경기날짜", "상대팀", "경기시간", "투표마감", "경기장소"])
    
    if sched_df.empty:
        st.info("현재 등록된 경기 일정이 없습니다.")
    else:
        if st.session_state.step == "input":
            st.subheader("📢 투표하실 경기를 선택해 주세요")
            for index, row in sched_df.iterrows():
                game_label = f"🧡 {row['경기날짜']} vs {row['상대팀']} ({row['경기시간']})"
                # 경기별 투표 버튼 생성
                if st.button(game_label, key=f"game_btn_{index}"):
                    # 마감 체크
                    try:
                        deadline = datetime.strptime(row['투표마감'], "%Y-%m-%d %H:%M")
                        if datetime.now() > deadline:
                            st.error(f"⚠️ 해당 경기는 투표가 마감되었습니다. ({row['투표마감']})")
                        else:
                            st.session_state.selected_game = f"{row['경기날짜']} vs {row['상대팀']} ({row['경기시간']})"
                            st.session_state.step = "info_input"
                            st.rerun()
                    except:
                        st.error("마감 시간 형식이 올바르지 않습니다.")

        elif st.session_state.step == "info_input":
            st.subheader(f"📝 [{st.session_state.selected_game}] 정보 입력")
            plus_one = st.checkbox("+1 (동반인 포함)")
            name = st.text_input("이름")
            phone = st.text_input("연락처")
            col_back, col_next = st.columns(2)
            if col_back.button("이전으로"):
                st.session_state.step = "input"; st.rerun()
            if col_next.button("다음 단계"):
                if name and phone:
                    st.session_state.user_info = {"이름": name, "연락처": phone, "plus_one": plus_one}
                    st.session_state.step = "step1"; st.rerun()

        elif st.session_state.step == "step1":
            st.subheader(f"🙋‍♂️ {st.session_state.user_info['이름']}님, 직관 오시나요?")
            if st.button("🧡 단관참석"):
                st.session_state.user_info['참석'] = "참석"; st.session_state.step = "step2"; st.rerun()

        elif st.session_state.step == "step2":
            st.subheader("🍻 뒷풀이 여부")
            c1, c2 = st.columns(2)
            with c1: 
                if st.button("참석"): 
                    st.session_state.user_info['뒷풀이'] = "참석"; st.session_state.step = "confirm"; st.rerun()
            with c2: 
                if st.button("미참석"): 
                    st.session_state.user_info['뒷풀이'] = "미참석"; st.session_state.step = "confirm"; st.rerun()

        elif st.session_state.step == "confirm":
            st.warning(f"최종 확인: {st.session_state.selected_game}")
            if st.button("최종 투표 제출"):
                existing_data = load_data(DATA_SHEET, ["경기정보", "날짜", "이름", "연락처", "참석여부", "뒷풀이"])
                new_rows = [{"경기정보": st.session_state.selected_game, "날짜": datetime.now().strftime("%Y-%m-%d %H:%M"), "이름": st.session_state.user_info['이름'], "연락처": st.session_state.user_info['연락처'], "참석여부": "참석", "뒷풀이": st.session_state.user_info['뒷풀이']}]
                if st.session_state.user_info.get('plus_one'):
                    new_rows.append({"경기정보": st.session_state.selected_game, "날짜": "-", "이름": "+1", "연락처": "-", "참석여부": "참석", "뒷풀이": st.session_state.user_info['뒷풀이']})
                conn.update(spreadsheet=SHEET_URL, worksheet=DATA_SHEET, data=pd.concat([existing_data, pd.DataFrame(new_rows)], ignore_index=True))
                st.session_state.step = "done"; st.rerun()

        elif st.session_state.step == "done":
            st.balloons()
            st.success(f"🎉 {st.session_state.selected_game} 투표 완료!")
            if st.button("🔄 다른 경기 투표 / 재투표"):
                st.session_state.step = "input"; st.session_state.user_info = {}; st.rerun()

# --- Tab 2: 참석 현황 ---
with tabs[1]:
    sched_df = load_data(SCH_SHEET, ["경기날짜", "상대팀"])
    if not sched_df.empty:
        game_list = [f"{row['경기날짜']} vs {row['상대팀']}" for _, row in sched_df.iterrows()]
        selected_view = st.selectbox("현황 확인할 경기 선택", game_list)
        all_data = load_data(DATA_SHEET, ["경기정보", "이름", "참석여부", "뒷풀이"])
        view_df = all_data[all_data['경기정보'].str.contains(selected_view, na=False)].copy()
        if not view_df.empty:
            st.metric("총 인원", f"{len(view_df)}명")
            view_df.reset_index(drop=True, inplace=True); view_df.index += 1
            st.table(view_df[["이름", "참석여부", "뒷풀이"]])
        else: st.info("아직 데이터가 없습니다.")

# --- Tab 3: 관리자 인증 ---
with tabs[2]:
    if not st.session_state.is_admin:
        a_name = st.text_input("관리자 이름")
        a_phone = st.text_input("연락처", type="password")
        if st.button("로그인"):
            if a_name == "윤상성" and a_phone == "01032200995":
                st.session_state.is_admin = True; st.rerun()
            else:
                admin_list = load_data(ADM_SHEET, ["이름", "연락처"])
                if not admin_list[(admin_list['이름'] == a_name) & (admin_list['연락처'].astype(str) == a_phone)].empty:
                    st.session_state.is_admin = True; st.rerun()
                else: st.error("정보 불일치")
    else:
        st.success("✅ 관리자 모드"); st.button("로그아웃", on_click=lambda: setattr(st.session_state, 'is_admin', False))

# --- Tab 4: 관리자 설정 (장소 필드 추가) ---
if st.session_state.is_admin:
    with tabs[3]:
        st.header("⚙️ 관리자 제어 센터")
        with st.expander("📅 일정 등록", expanded=True):
            with st.form("add_game"):
                c1, c2 = st.columns(2)
                g_date = c1.date_input("경기 날짜")
                g_opp = c2.text_input("상대팀")
                g_loc = st.text_input("경기 장소 (기록용)") # 장소 입력 필드 추가
                pm_times = [time(h, m) for h in range(12, 24) for m in [0, 30]]
                g_time = c1.selectbox("시작 시간", pm_times, format_func=lambda x: x.strftime("%H:%M"))
                st.divider()
                d_date = st.date_input("마감 날짜", value=g_date)
                d_time = st.time_input("마감 시간")
                if st.form_submit_button("일정 저장"):
                    dead_str = datetime.combine(d_date, d_time).strftime("%Y-%m-%d %H:%M")
                    new_game = pd.DataFrame([{"경기날짜": str(g_date), "상대팀": g_opp, "경기시간": g_time.strftime("%H:%M"), "투표마감": dead_str, "경기장소": g_loc}])
                    old_sch = load_data(SCH_SHEET, ["경기날짜", "상대팀", "경기시간", "투표마감", "경기장소"])
                    conn.update(spreadsheet=SHEET_URL, worksheet=SCH_SHEET, data=pd.concat([old_sch, new_game], ignore_index=True))
                    st.success("✅ 일정 및 장소가 등록되었습니다."); st.rerun()

        with st.expander("👤 관리자 명단 관리"):
            st.subheader("신규 등록")
            n_name = st.text_input("이름"); n_phone = st.text_input("연락처(숫자만)")
            if st.button("등록하기"):
                old_adm = load_data(ADM_SHEET, ["이름", "연락처"])
                conn.update(spreadsheet=SHEET_URL, worksheet=ADM_SHEET, data=pd.concat([old_adm, pd.DataFrame([{"이름": n_name, "연락처": n_phone}])], ignore_index=True))
                st.success("등록 완료"); st.rerun()

        with st.expander("⚠️ 일정 및 데이터 삭제"):
            sch_to_del = load_data(SCH_SHEET, ["경기날짜", "상대팀"])
            if not sch_to_del.empty:
                opts = [f"{r['경기날짜']} vs {r['상대팀']}" for _, r in sch_to_del.iterrows()]
                sel_del = st.selectbox("삭제 선택", opts)
                if st.button("🔥 삭제 실행", disabled=not st.checkbox(f"'{sel_del}'의 모든 데이터를 삭제하시겠습니까?")):
                    updated_sch = sch_to_del.drop(sch_to_del.index[opts.index(sel_del)])
                    conn.update(spreadsheet=SHEET_URL, worksheet=SCH_SHEET, data=updated_sch)
                    all_data = load_data(DATA_SHEET, ["경기정보", "날짜", "이름", "연락처", "참석여부", "뒷풀이"])
                    conn.update(spreadsheet=SHEET_URL, worksheet=DATA_SHEET, data=all_data[~all_data['경기정보'].str.contains(sel_del)])
                    st.success("삭제 완료"); st.
