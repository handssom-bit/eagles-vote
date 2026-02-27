import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. 페이지 설정 및 디자인 (페이드아웃/애니메이션 제거 스타일 포함) ---
st.set_page_config(page_title="한화이글스 단관 시스템 Pro", layout="centered")

st.markdown("""
    <style>
    /* 전체 배경 및 폰트 설정 */
    .stApp { background-color: #FFFFFF; color: #000000; }
    h1, h2, h3, .stHeader { color: #FF6600 !important; }
    
    /* 화면 전환 시 애니메이션 효과 강제 제거 */
    * {
        transition: none !important;
        animation: none !important;
    }

    /* 버튼 스타일 */
    div.stButton > button {
        background-color: #FFFFFF; color: #FF6600; border: 2px solid #FF6600;
        border-radius: 8px; height: 3.5em; font-weight: bold; width: 100%;
        transition: none !important; /* 버튼 호버 효과도 즉각적으로 변경 */
    }
    div.stButton > button:hover { background-color: #FF6600 !important; color: #FFFFFF !important; }

    /* 투표 단계 컨테이너 높이 최소 유지 (화면 덜컹거림 방지) */
    [data-testid="stVerticalBlock"] > div:has(div.stButton) {
        min-height: 250px;
    }
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
            
            now = datetime.now()
            try:
                deadline = datetime.strptime(game_info['투표마감'], "%Y-%m-%d %H:%M")
                if now > deadline:
                    st.error(f"⚠️ 투표 마감: {game_info['투표마감']}")
                    current_step = "locked"
                else:
                    st.success(f"✅ 투표 가능 (마감: {game_info['투표마감']})")
                    current_step = st.session_state.step
            except:
                current_step = "locked"

            # 투표 폼을 감싸는 컨테이너 (레이아웃 고정용)
            vote_container = st.container()
            with vote_container:
                if current_step == "input":
                    st.subheader("📝 정보 입력")
                    plus_one = st.checkbox("+1 (동반인 포함)")
                    name = st.text_input("이름", key="name_input")
                    phone = st.text_input("연락처", key="phone_input")
                    if st.button("투표 시작", key="start_btn"):
                        if name and phone:
                            st.session_state.user_info = {"이름": name, "연락처": phone, "plus_one": plus_one}
                            st.session_state.step = "step1"; st.rerun()

                elif current_step == "step1":
                    st.subheader(f"🙋‍♂️ {st.session_state.user_info['이름']}님, 직관 오시나요?")
                    if st.button("🧡 단관참석", key="attend_btn"):
                        st.session_state.user_info['참석'] = "참석"
                        st.session_state.step = "step2"; st.rerun()

                elif current_step == "step2":
                    st.subheader("🍻 뒷풀이 여부")
                    c1, c2 = st.columns(2)
                    with c1: 
                        if st.button("참석", key="party_y"): 
                            st.session_state.user_info['뒷풀이'] = "참석"; st.session_state.step = "confirm"; st.rerun()
                    with c2: 
                        if st.button("미참석", key="party_n"): 
                            st.session_state.user_info['뒷풀이'] = "미참석"; st.session_state.step = "confirm"; st.rerun()

                elif current_step == "confirm":
                    st.subheader("✅ 최종 확인")
                    if st.button("최종 제출", key="submit_btn"):
                        existing_data = load_data(DATA_SHEET, ["경기정보", "날짜", "이름", "연락처", "참석여부", "뒷풀이"])
                        game_tag = st.session_state.selected_game
                        
                        new_rows = [{"경기정보": game_tag, "날짜": datetime.now().strftime("%Y-%m-%d %H:%M"), "이름": st.session_state.user_info['이름'], "연락처": st.session_state.user_info['연락처'], "참석여부": "참석", "뒷풀이": st.session_state.user_info['뒷풀이']}]
                        if st.session_state.user_info['plus_one']:
                            new_rows.append({"경기정보": game_tag, "날짜": "-", "이름": "+1", "연락처": "-", "참석여부": "참석", "뒷풀이": st.session_state.user_info['뒷풀이']})
                        
                        conn.update(spreadsheet=SHEET_URL, worksheet=DATA_SHEET, data=pd.concat([existing_data, pd.DataFrame(new_rows)], ignore_index=True))
                        st.session_state.step = "done"; st.rerun()
        
        else:
            st.success(f"🎉 {st.session_state.selected_game} 경기 투표를 완료했습니다!")
            if st.button("🔄 다시 투표하기 (재투표)", key="restart_btn"):
                st.session_state.step = "input"; st.session_state.user_info = {}; st.rerun()

# --- Tab 2: 참석 현황 (기존 동일) ---
with tabs[1]:
    sched_df = load_data(SCH_SHEET, ["경기날짜", "상대팀"])
    if not sched_df.empty:
        game_list = [f"{row['경기날짜']} vs {row['상대팀']}" for _, row in sched_df.iterrows()]
        default_idx = 0
        if st.session_state.selected_game in game_list:
            default_idx = game_list.index(st.session_state.selected_game)
        selected_view = st.selectbox("현황 확인할 경기 선택", game_list, index=default_idx, key="view_select")
        all_data = load_data(DATA_SHEET, ["경기정보", "날짜", "이름", "연락처", "참석여부", "뒷풀이"])
        view_df = all_data[all_data['경기정보'] == selected_view]
        if not view_df.empty:
            st.metric("총 인원 (동반인 포함)", f"{len(view_df)}명")
            st.table(view_df[["이름", "참석여부", "뒷풀이"]])
        else: st.info("아직 투표 데이터가 없습니다.")

# --- Tab 3: 관리자 인증 (기존 동일) ---
with tabs[2]:
    if not st.session_state.is_admin:
        st.subheader("🔐 관리자 로그인")
        admin_name = st.text_input("관리자 이름", key="admin_name")
        admin_phone = st.text_input("관리자 연락처(숫자만)", type="password", key="admin_phone")
        if st.button("로그인", key="login_btn"):
            if admin_name == "윤상성" and admin_phone == "01032200995":
                st.session_state.is_admin = True; st.rerun()
            else:
                admin_list = load_data(ADM_SHEET, ["이름", "연락처"])
                if not admin_list[(admin_list['이름'] == admin_name) & (admin_list['연락처'] == admin_phone)].empty:
                    st.session_state.is_admin = True; st.rerun()
                else: st.error("정보 불일치")
    else:
        st.success("✅ 관리자 로그인 중")
        if st.button("로그아웃", key="logout_btn"): st.session_state.is_admin = False; st.rerun()

# --- Tab 4: 관리자 설정 (기존 동일) ---
if st.session_state.is_admin:
    with tabs[3]:
        st.header("⚙️ 관리자 제어 센터")
        with st.expander("📅 일정 등록", expanded=True):
            with st.form("add_form"):
                c1, c2 = st.columns(2)
                g_date = c1.date_input("경기 날짜")
                g_opp = c2.text_input("상대팀")
                g_time = c1.time_input("경기 시작 시간")
                st.divider()
                d_date = st.date_input("마감 날짜", value=g_date)
                d_time = st.time_input("마감 시간")
                if st.form_submit_button("일정 저장"):
                    dead_str = datetime.combine(d_date, d_time).strftime("%Y-%m-%d %H:%M")
                    new_game = pd.DataFrame([{"경기날짜": str(g_date), "상대팀": g_opp, "경기시간": str(g_time)[:5], "투표마감": dead_str}])
                    old_sch = load_data(SCH_SHEET, ["경기날짜", "상대팀", "경기시간", "투표마감"])
                    conn.update(spreadsheet=SHEET_URL, worksheet=SCH_SHEET, data=pd.concat([old_sch, new_game], ignore_index=True))
                    st.success("✅ 일정 등록 완료!"); st.rerun()
        
        with st.expander("🗑️ 일정 및 데이터 삭제"):
            st.error("❗ 주의: 삭제 시 해당 경기의 모든 투표 기록이 영구적으로 사라집니다.")
            sch_to_del = load_data(SCH_SHEET, ["경기날짜", "상대팀"])
            if not sch_to_del.empty:
                opts = [f"{r['경기날짜']} vs {r['상대팀']}" for _, r in sch_to_del.iterrows()]
                sel_del = st.selectbox("삭제할 일정 선택", opts, key="del_select")
                confirm_check = st.checkbox(f"위의 '{sel_del}' 일정과 모든 데이터를 정말로 삭제하시겠습니까?", key="del_confirm")
                if st.button("🔥 일정 및 데이터 삭제", disabled=not confirm_check, key="del_btn"):
                    idx = opts.index(sel_del)
                    updated_sch = sch_to_del.drop(sch_to_del.index[idx])
                    conn.update(spreadsheet=SHEET_URL, worksheet=SCH_SHEET, data=updated_sch)
                    all_data = load_data(DATA_SHEET, ["경기정보", "날짜", "이름", "연락처", "참석여부", "뒷풀이"])
                    updated_data = all_data[all_data['경기정보'] != sel_del]
                    conn.update(spreadsheet=SHEET_URL, worksheet=DATA_SHEET, data=updated_data)
                    st.success(f"🗑️ '{sel_del}' 데이터 삭제가 완료되었습니다."); st.rerun()
