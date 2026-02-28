import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, time
import time as sleep_time

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
    </style>
    """, unsafe_allow_html=True)

# --- 2. 구글 시트 연결 설정 ---
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
conn = st.connection("gsheets", type=GSheetsConnection)

SCH_SHEET = "경기일정"
ADM_SHEET = "관리자명단"
VOTE_SHEET = "투표결과"  # 모든 데이터가 저장될 통합 탭
COLS = ["경기정보", "경기장소", "날짜", "이름", "연락처", "참석여부", "뒷풀이"]

def load_data(sheet_name, columns=COLS):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl="0s")
        if df is None or df.empty:
            return pd.DataFrame(columns=columns)
        return df
    except:
        return pd.DataFrame(columns=columns)

# --- 3. 세션 상태 초기화 ---
if 'is_admin' not in st.session_state: st.session_state.is_admin = False
if 'step' not in st.session_state: st.session_state.step = "input"
if 'user_info' not in st.session_state: st.session_state.user_info = {}
if 'selected_game_info' not in st.session_state: st.session_state.selected_game_info = {}

# --- 4. 메인 화면 구성 ---
st.title("⚾ 한화이글스 단관 모집")
tab_titles = ["투표하기", "참석 현황", "관리자 인증"]
if st.session_state.is_admin:
    tab_titles.append("⚙️ 관리자 설정")
tabs = st.tabs(tab_titles)

# --- Tab 1: 투표하기 (나열식 버튼 & 재투표 로직) ---
with tabs[0]:
    sched_df = load_data(SCH_SHEET, ["경기날짜", "상대팀", "경기시간", "투표마감", "경기장소"])
    
    if sched_df.empty:
        st.info("현재 등록된 경기 일정이 없습니다.")
    else:
        if st.session_state.step == "input":
            st.subheader("📢 투표하실 경기를 선택해 주세요")
            for index, row in sched_df.iterrows():
                if pd.isna(row['경기날짜']): continue
                loc_info = f" @{row['경기장소']}" if row['경기장소'] else ""
                game_label = f"🧡 {row['경기날짜']} vs {row['상대팀']} ({row['경기시간']}){loc_info}"
                
                if st.button(game_label, key=f"vote_btn_{index}"):
                    st.session_state.selected_game_info = row.to_dict()
                    st.session_state.step = "info_input"
                    st.rerun()

        elif st.session_state.step == "info_input":
            info = st.session_state.selected_game_info
            st.subheader(f"📝 [{info['경기날짜']}] 정보 입력")
            st.caption("💡 이미 투표하셨더라도 동일 정보로 입력하면 자동 수정됩니다.")
            name = st.text_input("이름", key="name_v")
            phone = st.text_input("연락처", key="phone_v")
            plus_one = st.checkbox("+1 (동반인 포함)", key="plus_v")
            
            if st.button("다음 단계"):
                if name and phone:
                    st.session_state.user_info = {"이름": name, "연락처": phone, "plus_one": plus_one}
                    st.session_state.step = "step1"; st.rerun()
                else: st.warning("이름과 연락처를 입력해 주세요.")

        elif st.session_state.step == "step1":
            st.subheader(f"🙋‍♂️ {st.session_state.user_info['이름']}님, 직관 오시나요?")
            if st.button("🧡 단관참석"):
                st.session_state.user_info['참석'] = "참석"; st.session_state.step = "step2"; st.rerun()

        elif st.session_state.step == "step2":
            st.subheader("🍻 뒷풀이 여부")
            c1, c2 = st.columns(2)
            if c1.button("참석"): 
                st.session_state.user_info['뒷풀이'] = "참석"; st.session_state.step = "confirm"; st.rerun()
            if c2.button("미참석"): 
                st.session_state.user_info['뒷풀이'] = "미참석"; st.session_state.step = "confirm"; st.rerun()

        elif st.session_state.step == "confirm":
            if st.button("최종 투표 제출"):
                info, user = st.session_state.selected_game_info, st.session_state.user_info
                game_tag = f"{info['경기날짜']} vs {info['상대팀']}"
                
                # 데이터 준비
                new_row = {
                    "경기정보": game_tag, "경기장소": info['경기장소'],
                    "날짜": datetime.now().strftime("%Y-%m-%d %H:%M"), "이름": user['이름'], 
                    "연락처": user['연락처'], "참석여부": "참석", "뒷풀이": user['뒷풀이']
                }
                
                # [통합 저장 및 재투표 로직]
                df = load_data(VOTE_SHEET)
                if not df.empty:
                    # 동일 경기에서 동일 이름+연락처 행 삭제
                    df = df[~((df['경기정보'] == game_tag) & (df['이름'] == user['이름']) & (df['연락처'] == user['연락처']))]
                    # 해당 유저의 동반인(+1) 행도 같이 삭제
                    df = df[~((df['경기정보'] == game_tag) & (df['이름'] == "+1") & (df['연락처'] == "-") & (df.index.isin(df[df['이름'] == user['이름']].index + 1)))]

                final_rows = [new_row]
                if user['plus_one']:
                    final_rows.append({**new_row, "이름": "+1", "연락처": "-", "날짜": "-"})
                
                final_df = pd.concat([df, pd.DataFrame(final_rows)], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, worksheet=VOTE_SHEET, data=final_df)
                
                st.success("✅ 투표가 정상적으로 저장되었습니다!")
                sleep_time.sleep(1)
                st.session_state.step = "input"; st.session_state.user_info = {}; st.rerun()

# --- Tab 2: 참석 현황 (필터링 방식) ---
with tabs[1]:
    sched_df = load_data(SCH_SHEET, ["경기날짜", "상대팀"])
    if not sched_df.empty:
        game_list = [f"{row['경기날짜']} vs {row['상대팀']}" for _, row in sched_df.iterrows()]
        sel_game = st.selectbox("현황 확인할 경기 선택", game_list, key="status_sel")
        
        all_res = load_data(VOTE_SHEET)
        view_df = all_res[all_res['경기정보'] == sel_game].copy()
        
        if not view_df.empty:
            st.metric("현재 참석 인원", f"{len(view_df)}명")
            view_df.reset_index(drop=True, inplace=True); view_df.index += 1
            st.table(view_df[["이름", "참석여부", "뒷풀이"]])
        else: st.info("아직 투표 데이터가 없습니다.")

# --- Tab 3: 관리자 인증 ---
with tabs[2]:
    if not st.session_state.is_admin:
        st.subheader("🔐 관리자 로그인")
        ln = st.text_input("이름", key="l_n"); lp = st.text_input("연락처", type="password", key="l_p")
        if st.button("로그인"):
            if (ln == "윤상성" and lp == "01032200995"): st.session_state.is_admin = True; st.rerun()
            adm_list = load_data(ADM_SHEET, ["이름", "연락처"])
            if not adm_list[(adm_list['이름'] == ln) & (adm_list['연락처'].astype(str) == lp)].empty:
                st.session_state.is_admin = True; st.rerun()
            else: st.error("정보가 일치하지 않습니다.")
    else:
        st.success("✅ 관리자 권한 접속 중"); st.button("로그아웃", on_click=lambda: setattr(st.session_state, 'is_admin', False))

# --- Tab 4: 관리자 설정 (기능 완전체) ---
if st.session_state.is_admin:
    with tabs[3]:
        st.header("⚙️ 관리자 제어 센터")
        
        with st.expander("📅 일정 등록", expanded=False):
            with st.form("add_game_form"):
                c1, c2 = st.columns(2)
                g_d, g_o, g_l = c1.date_input("날짜"), c2.text_input("상대팀"), st.text_input("장소")
                pm_times = [time(h, m) for h in range(12, 24) for m in [0, 30]]
                g_t = c1.selectbox("시작 시간", pm_times, format_func=lambda x: x.strftime("%H:%M"))
                if st.form_submit_button("일정 저장"):
                    new = pd.DataFrame([{"경기날짜": str(g_d), "상대팀": g_o, "경기시간": g_t.strftime("%H:%M"), "투표마감": str(g_d)+" 23:59", "경기장소": g_l}])
                    conn.update(spreadsheet=SHEET_URL, worksheet=SCH_SHEET, data=pd.concat([load_data(SCH_SHEET), new], ignore_index=True))
                    st.success("등록 완료!"); st.rerun()

        with st.expander("👤 관리자 명단 관리", expanded=True):
            st.subheader("운영진 추가")
            an, ap = st.text_input("새 관리자 이름", key="an"), st.text_input("연락처", key="ap")
            if st.button("관리자 등록"):
                old = load_data(ADM_SHEET, ["이름", "연락처"])
                conn.update(spreadsheet=SHEET_URL, worksheet=ADM_SHEET, data=pd.concat([old, pd.DataFrame([{"이름": an, "연락처": ap}])], ignore_index=True))
                st.success("등록 완료!"); st.rerun()
            st.divider()
            st.subheader("운영진 삭제")
            curr = load_data(ADM_SHEET, ["이름", "연락처"])
            names = curr[curr['이름'] != "윤상성"]['이름'].tolist()
            if names:
                target = st.selectbox("삭제할 관리자", names)
                if st.button("삭제 실행"):
                    conn.update(spreadsheet=SHEET_URL, worksheet=ADM_SHEET, data=curr[curr['이름'] != target])
                    st.success("삭제 완료!"); st.rerun()

        with st.expander("⚠️ 일정 및 데이터 삭제", expanded=False):
            sch = load_data(SCH_SHEET, ["경기날짜", "상대팀"])
            if not sch.empty:
                opts = [f"{r['경기날짜']} vs {r['상대팀']}" for _, r in sch.iterrows()]
                sel_del = st.selectbox("삭제할 일정", opts)
                if st.button("🔥 일정 및 투표 데이터 삭제", disabled=not st.checkbox("데이터 영구 삭제에 동의합니다.")):
                    conn.update(spreadsheet=SHEET_URL, worksheet=SCH_SHEET, data=sch[~sch.apply(lambda r: f"{r['경기날짜']} vs {r['상대팀']}" == sel_del, axis=1)])
                    all_v = load_data(VOTE_SHEET)
                    conn.update(spreadsheet=SHEET_URL, worksheet=VOTE_SHEET, data=all_v[all_v['경기정보'] != sel_del])
                    st.success("삭제 완료!"); st.rerun()
