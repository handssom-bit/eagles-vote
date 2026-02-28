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
    div.stButton > button {
        background-color: #FFFFFF; color: #FF6600; border: 2px solid #FF6600;
        border-radius: 8px; font-weight: bold; width: 100%;
    }
    div.stButton > button:hover { background-color: #FF6600 !important; color: #FFFFFF !important; }
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

# --- Tab 1: 투표하기 (복수 경기 대응) ---
with tabs[0]:
    sched_df = load_data(SCH_SHEET, ["경기날짜", "상대팀", "경기시간", "투표마감"])
    
    if sched_df.empty:
        st.info("현재 등록된 경기 일정이 없습니다.")
    else:
        # 경기 목록 생성
        game_list = [f"{row['경기날짜']} vs {row['상대팀']} ({row['경기시간']})" for _, row in sched_df.iterrows()]
        
        # 투표 완료 상태가 아닐 때만 경기 선택 가능
        if st.session_state.step != "done":
            selected_game = st.selectbox("투표할 경기를 선택하세요", game_list, key="main_game_select")
            st.session_state.selected_game = selected_game
            
            # 선택된 경기의 마감 시간 체크
            game_info = sched_df[game_list.index(selected_game) == sched_df.index].iloc[0]
            try:
                deadline = datetime.strptime(game_info['투표마감'], "%Y-%m-%d %H:%M")
                if datetime.now() > deadline:
                    st.error(f"⚠️ 해당 경기는 투표가 마감되었습니다. ({game_info['투표마감']})")
                    current_step = "locked"
                else:
                    current_step = st.session_state.step
            except: current_step = "locked"

            if current_step == "input":
                st.subheader(f"📝 [{selected_game}] 정보 입력")
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
                st.info(f"선택 경기: {st.session_state.selected_game}")
                if st.button("최종 제출"):
                    try:
                        existing_data = load_data(DATA_SHEET, ["경기정보", "날짜", "이름", "연락처", "참석여부", "뒷풀이"])
                        new_rows = [{"경기정보": st.session_state.selected_game, "날짜": datetime.now().strftime("%Y-%m-%d %H:%M"), "이름": st.session_state.user_info['이름'], "연락처": st.session_state.user_info['연락처'], "참석여부": "참석", "뒷풀이": st.session_state.user_info['뒷풀이']}]
                        if st.session_state.user_info.get('plus_one'):
                            new_rows.append({"경기정보": st.session_state.selected_game, "날짜": "-", "이름": "+1", "연락처": "-", "참석여부": "참석", "뒷풀이": st.session_state.user_info['뒷풀이']})
                        
                        updated_df = pd.concat([existing_data, pd.DataFrame(new_rows)], ignore_index=True)
                        conn.update(spreadsheet=SHEET_URL, worksheet=DATA_SHEET, data=updated_df)
                        st.session_state.step = "done"; st.rerun()
                    except Exception as e: st.error(f"오류 발생: {e}")
        else:
            st.success(f"🎉 {st.session_state.selected_game} 투표 완료!")
            if st.button("🔄 다른 경기 투표하기 / 재투표"):
                st.session_state.step = "input"; st.session_state.user_info = {}; st.rerun()

# --- Tab 2: 참석 현황 ---
with tabs[1]:
    sched_df = load_data(SCH_SHEET, ["경기날짜", "상대팀"])
    if not sched_df.empty:
        game_list = [f"{row['경기날짜']} vs {row['상대팀']}" for _, row in sched_df.iterrows()]
        selected_view = st.selectbox("현황 확인할 경기 선택", game_list, key="view_select")
        
        all_data = load_data(DATA_SHEET, ["경기정보", "이름", "참석여부", "뒷풀이"])
        view_df = all_data[all_data['경기정보'].str.contains(selected_view, na=False)].copy()
        
        if not view_df.empty:
            st.metric("현재 참석 인원", f"{len(view_df)}명")
            st.table(view_df.reset_index(drop=True)[["이름", "참석여부", "뒷풀이"]])
        else: st.info("투표 데이터가 없습니다.")

# --- Tab 3: 관리자 인증 ---
with tabs[2]:
    if not st.session_state.is_admin:
        a_name = st.text_input("관리자 이름")
        a_phone = st.text_input("연락처 (숫자만)", type="password")
        if st.button("로그인"):
            if (a_name == "윤상성" and a_phone == "01032200995"):
                st.session_state.is_admin = True; st.rerun()
            else:
                admin_list = load_data(ADM_SHEET, ["이름", "연락처"])
                if not admin_list[(admin_list['이름'] == a_name) & (admin_list['연락처'].astype(str) == a_phone)].empty:
                    st.session_state.is_admin = True; st.rerun()
                else: st.error("인증 실패")
    else:
        st.success("관리자 인증 완료"); st.button("로그아웃", on_click=lambda: setattr(st.session_state, 'is_admin', False))

# --- Tab 4: 관리자 설정 (기능 완전 복구) ---
if st.session_state.is_admin:
    with tabs[3]:
        st.header("⚙️ 관리자 제어 센터")
        
        # 1. 일정 등록
        with st.expander("📅 일정 등록 (여러 경기 가능)"):
            with st.form("add_game"):
                c1, c2 = st.columns(2)
                g_date = c1.date_input("경기 날짜")
                g_opp = c2.text_input("상대팀")
                g_time = c1.selectbox("경기 시간", [time(h, m) for h in range(13, 20) for m in [0, 30]])
                d_date = st.date_input("투표 마감일", value=g_date)
                d_time = st.time_input("투표 마감시간", value=time(18, 0))
                if st.form_submit_button("일정 추가 저장"):
                    new_game = pd.DataFrame([{"경기날짜": str(g_date), "상대팀": g_opp, "경기시간": g_time.strftime("%H:%M"), "투표마감": datetime.combine(d_date, d_time).strftime("%Y-%m-%d %H:%M")}])
                    old_sch = load_data(SCH_SHEET, ["경기날짜", "상대팀", "경기시간", "투표마감"])
                    conn.update(spreadsheet=SHEET_URL, worksheet=SCH_SHEET, data=pd.concat([old_sch, new_game], ignore_index=True))
                    st.success("새 일정이 등록되었습니다."); st.rerun()

        # 2. 일정 및 데이터 삭제
        with st.expander("🗑️ 일정 및 투표 데이터 삭제"):
            sch_df = load_data(SCH_SHEET, ["경기날짜", "상대팀"])
            if not sch_df.empty:
                del_list = [f"{r['경기날짜']} vs {r['상대팀']}" for _, r in sch_df.iterrows()]
                target = st.selectbox("삭제할 경기 선택", del_list)
                if st.button("🔥 선택한 경기 및 모든 투표 삭제", help="주의! 복구 불가능"):
                    # 일정 삭제
                    new_sch = sch_df.drop(sch_df.index[del_list.index(target)])
                    conn.update(spreadsheet=SHEET_URL, worksheet=SCH_SHEET, data=new_sch)
                    # 결과 데이터 삭제
                    res_df = load_data(DATA_SHEET, ["경기정보"])
                    conn.update(spreadsheet=SHEET_URL, worksheet=DATA_SHEET, data=res_df[~res_df['경기정보'].str.contains(target)])
                    st.success("삭제 완료!"); st.rerun()

        # 3. 관리자 명단 관리
        with st.expander("👥 관리자 명단 관리"):
            st.subheader("신규 관리자 등록")
            new_adm_name = st.text_input("새 관리자 이름")
            new_adm_phone = st.text_input("새 관리자 연락처 (숫자만)")
            if st.button("관리자 추가"):
                old_adm = load_data(ADM_SHEET, ["이름", "연락처"])
                new_adm_df = pd.concat([old_adm, pd.DataFrame([{"이름": new_adm_name, "연락처": new_adm_phone}])], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, worksheet=ADM_SHEET, data=new_adm_df)
                st.success("관리자 등록 완료!"); st.rerun()
            
            st.divider()
            st.subheader("관리자 삭제")
            adm_df = load_data(ADM_SHEET, ["이름", "연락처"])
            if not adm_df.empty:
                adm_to_del = st.selectbox("삭제할 관리자", adm_df['이름'].tolist())
                if st.button("선택 관리자 삭제"):
                    updated_adm = adm_df[adm_df['이름'] != adm_to_del]
                    conn.update(spreadsheet=SHEET_URL, worksheet=ADM_SHEET, data=updated_adm)
                    st.success("관리자 삭제 완료!"); st.rerun()
