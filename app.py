import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. 페이지 설정 및 디자인 ---
st.set_page_config(page_title="한화이글스 단관 시스템 Pro", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; color: #000000; }
    h1, h2, h3, .stHeader { color: #FF6600 !important; }
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

def load_data(sheet_name, columns):
    try:
        return conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl="0s")
    except:
        return pd.DataFrame(columns=columns)

# --- 3. 세션 상태 초기화 ---
if 'is_admin' not in st.session_state: st.session_state.is_admin = False
if 'step' not in st.session_state: st.session_state.step = "input"
if 'user_info' not in st.session_state: st.session_state.user_info = {}

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
        st.info("현재 등록된 경기 일정이 없습니다. 관리자에게 문의하세요.")
    else:
        # 경기 목록 생성
        game_list = [f"{row['경기날짜']} vs {row['상대팀']}" for _, row in sched_df.iterrows()]
        
        if st.session_state.step != "done":
            selected_game_idx = st.selectbox("투표할 경기를 선택하세요", range(len(game_list)), format_func=lambda x: game_list[x])
            game_info = sched_df.iloc[selected_game_idx]
            
            # 탭 이름 형식 (MM-DD, 상대팀)
            try:
                dt_obj = datetime.strptime(game_info['경기날짜'], "%Y-%m-%d")
                sheet_name = f"{dt_obj.strftime('%m-%d')}, {game_info['상대팀']}"
            except:
                sheet_name = game_info['경기날짜']

            now = datetime.now()
            try:
                deadline = datetime.strptime(game_info['투표마감'], "%Y-%m-%d %H:%M")
                if now > deadline:
                    st.error(f"⚠️ 투표가 마감되었습니다. (마감: {game_info['투표마감']})")
                    current_step = "locked"
                else:
                    st.success(f"✅ 투표 가능 (마감: {game_info['투표마감']})")
                    current_step = st.session_state.step
            except:
                st.error("마감 시간 형식 오류")
                current_step = "locked"

            # 투표 단계
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
                    st.session_state.user_info['참석'] = "참석"
                    st.session_state.step = "step2"; st.rerun()

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
                st.warning(f"최종 확인: {st.session_state.user_info['참석']} / 뒷풀이 {st.session_state.user_info['뒷풀이']}")
                if st.button("최종 제출"):
                    try:
                        existing_data = load_data(sheet_name, ["날짜", "이름", "연락처", "참석여부", "뒷풀이"])
                        new_rows = [{"날짜": datetime.now().strftime("%Y-%m-%d %H:%M"), "이름": st.session_state.user_info['이름'], "연락처": st.session_state.user_info['연락처'], "참석여부": "참석", "뒷풀이": st.session_state.user_info['뒷풀이']}]
                        if st.session_state.user_info['plus_one']:
                            new_rows.append({"날짜": "-", "이름": "+1", "연락처": "-", "참석여부": "참석", "뒷풀이": st.session_state.user_info['뒷풀이']})
                        
                        conn.update(spreadsheet=SHEET_URL, worksheet=sheet_name, data=pd.concat([existing_data, pd.DataFrame(new_rows)], ignore_index=True))
                        st.session_state.step = "done"; st.rerun()
                    except Exception as e:
                        st.error(f"구글 시트에 '{sheet_name}' 탭이 없습니다. 관리자에게 문의하세요.")
        else:
            st.success("🎉 투표가 성공적으로 완료되었습니다!")
            if st.button("새로 투표하기"):
                st.session_state.step = "input"; st.session_state.user_info = {}; st.rerun()

# --- Tab 2: 참석 현황 ---
with tabs[1]:
    sched_df = load_data(SCH_SHEET, ["경기날짜", "상대팀"])
    if not sched_df.empty:
        game_options = {f"{row['경기날짜']} vs {row['상대팀']}": row for _, row in sched_df.iterrows()}
        selected_view = st.selectbox("현황 확인할 경기 선택", game_options.keys())
        
        row = game_options[selected_view]
        dt_obj = datetime.strptime(row['경기날짜'], "%Y-%m-%d")
        view_sheet = f"{dt_obj.strftime('%m-%d')}, {row['상대팀']}"
        
        view_df = load_data(view_sheet, ["날짜", "이름", "연락처", "참석여부", "뒷풀이"])
        if not view_df.empty:
            st.metric("총 인원", f"{len(view_df)}명")
            st.table(view_df[["이름", "참석여부", "뒷풀이"]])
        else: st.info("투표 데이터가 없습니다.")

# --- Tab 3: 관리자 인증 ---
with tabs[2]:
    if not st.session_state.is_admin:
        st.subheader("🔐 관리자 로그인")
        admin_name = st.text_input("관리자 이름")
        admin_phone = st.text_input("관리자 연락처(숫자만)", type="password")
        if st.button("로그인"):
            # 윤상성 관리자님 강제 승인 로직 (기존 버그 해결)
            if admin_name == "윤상성" and admin_phone == "01032200995":
                admin_list = load_data(ADM_SHEET, ["이름", "연락처"])
                # 명단이 비어있거나 내가 없으면 등록
                if admin_list.empty or admin_list[admin_list['이름'] == "윤상성"].empty:
                    new_admin = pd.DataFrame([{"이름": "윤상성", "연락처": "01032200995"}])
                    conn.update(spreadsheet=SHEET_URL, worksheet=ADM_SHEET, data=pd.concat([admin_list, new_admin], ignore_index=True))
                st.session_state.is_admin = True; st.rerun()
            else:
                admin_list = load_data(ADM_SHEET, ["이름", "연락처"])
                if not admin_list[(admin_list['이름'] == admin_name) & (admin_list['연락처'] == admin_phone)].empty:
                    st.session_state.is_admin = True; st.rerun()
                else: st.error("정보 불일치. 이름을 확인해 주세요.")
    else:
        st.success("✅ 관리자 권한으로 로그인 중입니다.")
        if st.button("로그아웃"): st.session_state.is_admin = False; st.rerun()

# --- Tab 4: 관리자 설정 (자동 탭 생성) ---
if st.session_state.is_admin:
    with tabs[3]:
        st.header("⚙️ 관리자 제어 센터")
        with st.expander("📅 일정 등록 및 자동 탭 생성", expanded=True):
            with st.form("add_form"):
                c1, c2 = st.columns(2)
                g_date = c1.date_input("경기 날짜")
                g_opp = c2.text_input("상대팀")
                g_time = c1.time_input("경기 시간")
                st.divider()
                d_date = st.date_input("마감 날짜", value=g_date)
                d_time = st.time_input("마감 시간")
                if st.form_submit_button("저장 및 탭 생성"):
                    # 1. 경기 일정 저장
                    dead_str = datetime.combine(d_date, d_time).strftime("%Y-%m-%d %H:%M")
                    new_game = pd.DataFrame([{"경기날짜": str(g_date), "상대팀": g_opp, "경기시간": str(g_time)[:5], "투표마감": dead_str}])
                    old_sch = load_data(SCH_SHEET, ["경기날짜", "상대팀", "경기시간", "투표마감"])
                    conn.update(spreadsheet=SHEET_URL, worksheet=SCH_SHEET, data=pd.concat([old_sch, new_game], ignore_index=True))
                    
                    # 2. 새로운 투표 탭(05-10, LG 형식) 자동 생성 및 초기화
                    new_sheet_name = f"{g_date.strftime('%m-%d')}, {g_opp}"
                    initial_df = pd.DataFrame(columns=["날짜", "이름", "연락처", "참석여부", "뒷풀이"])
                    conn.update(spreadsheet=SHEET_URL, worksheet=new_sheet_name, data=initial_df)
                    
                    st.success(f"일정 등록 및 '{new_sheet_name}' 탭 생성 완료!"); st.rerun()
        
        with st.expander("🗑️ 일정 삭제"):
            sch_to_del = load_data(SCH_SHEET, ["경기날짜", "상대팀"])
            if not sch_to_del.empty:
                opts = [f"{r['경기날짜']} vs {r['상대팀']}" for _, r in sch_to_del.iterrows()]
                sel_del = st.selectbox("삭제 선택", opts)
                if st.button("삭제 실행"):
                    idx = opts.index(sel_del)
                    updated = sch_to_del.drop(sch_to_del.index[idx])
                    conn.update(spreadsheet=SHEET_URL, worksheet=SCH_SHEET, data=updated)
                    st.success("삭제 완료"); st.rerun()
