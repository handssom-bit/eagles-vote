import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. 페이지 설정 및 디자인 (화이트 테마 & 오렌지 포인트) ---
st.set_page_config(page_title="한화이글스 단관 시스템 Pro", layout="centered")

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
        width: 100%;
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

# --- 2. 구글 시트 연결 설정 ---
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
conn = st.connection("gsheets", type=GSheetsConnection)

# 시트 이름 정의
SCH_SHEET = "경기일정"
ADM_SHEET = "관리자명단"

def load_data(sheet_name, columns):
    try:
        return conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl="0s")
    except:
        return pd.DataFrame(columns=columns)

# --- 3. 세션 상태 초기화 ---
if 'is_admin' not in st.session_state: st.session_state.is_admin = False
if 'step' not in st.session_state: st.session_state.step = "input"
if 'user_info' not in st.session_state: st.session_state.user_info = {}

# --- 4. 메인 화면 구성 ---
st.title("⚾ 한화이글스 단관 모집")
st.markdown("#### 승리를 위하여! 팬 여러분의 참석 여부를 알려주세요.")

# 관리자 로그인 여부에 따라 탭 구성 변경
tab_titles = ["투표하기", "참석 현황", "관리자 인증"]
if st.session_state.is_admin:
    tab_titles.append("⚙️ 관리자 설정")

tabs = st.tabs(tab_titles)

# --- Tab 1: 투표하기 ---
with tabs[0]:
    sched_df = load_data(SCH_SHEET, ["경기날짜", "상대팀", "경기시간", "투표마감"])
    
    if sched_df.empty:
        st.info("현재 등록된 경기 일정이 없습니다. 관리자에게 문의하세요.")
    else:
        # 경기 선택
        game_list = [f"{row['경기날짜']} vs {row['상대팀']}" for _, row in sched_df.iterrows()]
        selected_game_idx = st.selectbox("투표할 경기를 선택하세요", range(len(game_list)), format_func=lambda x: game_list[x])
        game_info = sched_df.iloc[selected_game_idx]
        
        # 마감 시간 체크
        now = datetime.now()
        try:
            deadline = datetime.strptime(game_info['투표마감'], "%Y-%m-%d %H:%M")
            if now > deadline:
                st.error(f"⚠️ 투표가 마감되었습니다. (마감 일시: {game_info['투표마감']})")
                current_step = "locked"
            else:
                st.success(f"✅ 투표 가능 (마감: {game_info['투표마감']})")
                current_step = st.session_state.step
        except:
            st.error("마감 시간 설정에 오류가 있습니다.")
            current_step = "locked"

        if current_step != "locked":
            if current_step == "input":
                st.subheader("📝 정보 입력")
                plus_one = st.checkbox("+1 (동반인이 한 명 더 있나요?)")
                name = st.text_input("이름")
                phone = st.text_input("연락처")
                if st.button("투표 시작하기"):
                    if name and phone:
                        st.session_state.user_info = {"이름": name, "연락처": phone, "plus_one": plus_one}
                        st.session_state.step = "step1"; st.rerun()
                    else:
                        st.warning("이름과 연락처를 입력해 주세요.")
            
            elif current_step == "step1":
                st.subheader(f"🙋‍♂️ {st.session_state.user_info['이름']}님, 직관 오시나요?")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🧡 단관참석"):
                        st.session_state.user_info['참석'] = "참석"
                        st.session_state.step = "step2"; st.rerun()
                with col2: st.button("미참석 (비활성)", disabled=True)

            elif current_step == "step2":
                st.subheader("🍻 뒷풀이도 함께 하시나요?")
                c1, c2 = st.columns(2)
                with c1: 
                    if st.button("뒷풀이 참석"): 
                        st.session_state.user_info['뒷풀이'] = "참석"; st.session_state.step = "confirm"; st.rerun()
                with c2: 
                    if st.button("뒷풀이 미참석"): 
                        st.session_state.user_info['뒷풀이'] = "미참석"; st.session_state.step = "confirm"; st.rerun()

            elif current_step == "confirm":
                info = st.session_state.user_info
                st.warning(f"최종 확인: {info['참석']} / 뒷풀이 {info['뒷풀이']}")
                if st.button("최종 투표 제출"):
                    sheet_name = game_info['경기날짜']
                    existing_data = load_data(sheet_name, ["날짜", "이름", "연락처", "참석여부", "뒷풀이"])
                    new_rows = [{"날짜": datetime.now().strftime("%Y-%m-%d %H:%M"), "이름": info['이름'], "연락처": info['연락처'], "참석여부": "참석", "뒷풀이": info['뒷풀이']}]
                    if info['plus_one']:
                        new_rows.append({"날짜": "-", "이름": "+1", "연락처": "-", "참석여부": "참석", "뒷풀이": info['뒷풀이']})
                    conn.update(spreadsheet=SHEET_URL, worksheet=sheet_name, data=pd.concat([existing_data, pd.DataFrame(new_rows)], ignore_index=True))
                    st.session_state.step = "done"; st.rerun()

            elif current_step == "done":
                st.success("투표가 완료되었습니다! 🧡")
                if st.button("재투표 하시겠습니까?"):
                    st.session_state.step = "input"; st.rerun()

# --- Tab 2: 참석 현황 ---
with tabs[1]:
    sched_df = load_data(SCH_SHEET, ["경기날짜", "상대팀"])
    if not sched_df.empty:
        view_game = st.selectbox("현황을 확인할 경기 선택", sched_df['경기날짜'])
        view_df = load_data(view_game, ["날짜", "이름", "연락처", "참석여부", "뒷풀이"])
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
            # 윤상성 관리자님 강제 승인 및 자동 등록 로직
            if admin_name == "윤상성" and admin_phone == "01032200995":
                admin_list = load_data(ADM_SHEET, ["이름", "연락처"])
                if admin_list.empty or admin_list[(admin_list['이름'] == "윤상성")].empty:
                    new_admin = pd.DataFrame([{"이름": "윤상성", "연락처": "01032200995"}])
                    conn.update(spreadsheet=SHEET_URL, worksheet=ADM_SHEET, data=pd.concat([admin_list, new_admin], ignore_index=True))
                st.session_state.is_admin = True; st.rerun()
            else:
                admin_list = load_data(ADM_SHEET, ["이름", "연락처"])
                if not admin_list[(admin_list['이름'] == admin_name) & (admin_list['연락처'] == admin_phone)].empty:
                    st.session_state.is_admin = True; st.rerun()
                else: st.error("관리자 정보가 일치하지 않습니다.")
    else:
        st.success("✅ 관리자 권한으로 로그인 중입니다.")
        if st.button("로그아웃"): st.session_state.is_admin = False; st.rerun()

# --- Tab 4: 관리자 설정 (일정 등록 및 삭제) ---
if st.session_state.is_admin:
    with tabs[3]:
        st.header("⚙️ 관리자 제어 센터")
        
        # 1. 경기 일정 등록
        with st.expander("📅 새 경기 일정 및 마감 설정", expanded=True):
            with st.form("new_game_form"):
                c1, c2 = st.columns(2)
                g_date = c1.date_input("경기 날짜")
                g_opp = c2.text_input("상대 팀")
                g_time = c1.time_input("경기 시간")
                st.divider()
                st.subheader("투표 마감 일시 설정")
                d_date = st.date_input("마감 날짜", value=g_date)
                d_time = st.time_input("마감 시간")
                if st.form_submit_button("일정 저장"):
                    deadline_str = datetime.combine(d_date, d_time).strftime("%Y-%m-%d %H:%M")
                    new_game = pd.DataFrame([{"경기날짜": str(g_date), "상대팀": g_opp, "경기시간": str(g_time)[:5], "투표마감": deadline_str}])
                    old_sched = load_data(SCH_SHEET, ["경기날짜", "상대팀", "경기시간", "투표마감"])
                    conn.update(spreadsheet=SHEET_URL, worksheet=SCH_SHEET, data=pd.concat([old_sched, new_game], ignore_index=True))
                    st.success("✅ 경기 일정이 등록되었습니다!")
                    st.rerun()

        # 2. 경기 일정 삭제
        with st.expander("🗑️ 경기 일정 삭제"):
            st.warning("⚠️ 일정을 삭제하면 목록에서 제거됩니다. 투표 데이터 탭은 수동 관리를 권장합니다.")
            sched_to_del = load_data(SCH_SHEET, ["경기날짜", "상대팀", "경기시간", "투표마감"])
            if not sched_to_del.empty:
                del_options = [f"{row['경기날짜']} vs {row['상대팀']}" for _, row in sched_to_del.iterrows()]
                selected_del = st.selectbox("삭제할 경기를 선택하세요", del_options)
                if st.button("선택한 일정 삭제"):
                    idx = del_options.index(selected_del)
                    updated_sched = sched_to_del.drop(sched_to_del.index[idx])
                    conn.update(spreadsheet=SHEET_URL, worksheet=SCH_SHEET, data=updated_sched)
                    st.success(f"🗑️ {selected_del} 삭제 완료")
                    st.rerun()
            else: st.info("등록된 일정이 없습니다.")

        # 3. 관리자 명단 관리
        with st.expander("👥 관리자 명단 관리"):
            curr_admins = load_data(ADM_SHEET, ["이름", "연락처"])
            st.table(curr_admins["이름"])
            st.divider()
            new_adm_name = st.text_input("신규 관리자 성함")
            new_adm_phone = st.text_input("신규 관리자 연락처(숫자만)")
            if st.button("관리자 임명"):
                add_adm = pd.DataFrame([{"이름": new_adm_name, "연락처": new_adm_phone}])
                conn.update(spreadsheet=SHEET_URL, worksheet=ADM_SHEET, data=pd.concat([curr_admins, add_adm], ignore_index=True))
                st.success("임명 완료")
                st.rerun()
