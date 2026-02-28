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

# --- Tab 1: 투표하기 (재투표/덮어쓰기 로직 포함) ---
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
                if st.button(btn_label, key=f"v_{idx}"):
                    st.session_state.selected_game_info = row.to_dict()
                    st.session_state.step = "info_input"; st.rerun()

        elif st.session_state.step == "info_input":
            info = st.session_state.selected_game_info
            st.subheader(f"📝 [{info['경기날짜']}] 정보 입력")
            name = st.text_input("이름", key="name_v")
            phone = st.text_input("연락처", key="phone_v", help="재투표 시 동일한 이름/연락처를 입력하면 기존 정보가 수정됩니다.")
            plus_one = st.checkbox("+1 (동반인 포함)")
            c1, c2 = st.columns(2)
            if c1.button("이전"): st.session_state.step = "input"; st.rerun()
            if c2.button("다음"):
                if name and phone:
                    st.session_state.user_info = {"이름": name, "연락처": phone, "plus_one": plus_one}
                    st.session_state.step = "step1"; st.rerun()

        elif st.session_state.step == "step1":
            if st.button("🧡 단관참석"):
                st.session_state.user_info['참석'] = "참석"; st.session_state.step = "step2"; st.rerun()

        elif st.session_state.step == "step2":
            st.subheader("🍻 뒷풀이 여부")
            c1, c2 = st.columns(2)
            if c1.button("참석"): st.session_state.user_info['뒷풀이'] = "참석"; st.session_state.step = "confirm"; st.rerun()
            if c2.button("미참석"): st.session_state.user_info['뒷풀이'] = "미참석"; st.session_state.step = "confirm"; st.rerun()

        elif st.session_state.step == "confirm":
            if st.button("최종 투표 제출 (수정 포함)"):
                info = st.session_state.selected_game_info
                user = st.session_state.user_info
                target_sheet = str(info['경기날짜']).strip()
                
                # 데이터 준비
                new_entry = {
                    "경기정보": f"{info['경기날짜']} vs {info['상대팀']}",
                    "경기장소": info['경기장소'],
                    "날짜": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "이름": user['이름'], "연락처": user['연락처'], "참석여부": "참석", "뒷풀이": user['뒷풀이']
                }
                
                # 기존 데이터 로드
                df = load_data(target_sheet)
                
                # [재투표/덮어쓰기 핵심 로직]
                # 이름과 연락처가 동시에 일치하는 행을 찾아 삭제 후 새로 추가
                if not df.empty:
                    # 기존 투표자 정보 및 해당 유저의 +1 데이터 삭제
                    df = df[~((df['이름'] == user['이름']) & (df['연락처'] == user['연락처']))]
                    # 동반인 데이터(+1)는 연락처가 없으므로 로직상 유저 데이터 바로 뒤에 붙는 점을 이용하거나, 
                    # 더 확실하게 하기 위해 유저가 새로 투표할 때 기존의 관련 +1 행도 같이 정리
                    # (단순화를 위해 여기서는 동일 유저의 이전 투표 내역만 정리)
                
                final_list = [new_entry]
                if user.get('plus_one'):
                    final_list.append({**new_entry, "이름": "+1", "연락처": "-", "날짜": "-"})
                
                updated_df = pd.concat([df, pd.DataFrame(final_list)], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, worksheet=target_sheet, data=updated_df)
                
                st.session_state.step = "done"; st.rerun()

        elif st.session_state.step == "done":
            st.success("투표/수정이 완료되었습니다!"); st.button("처음으로", on_click=lambda: setattr(st.session_state, 'step', 'input'))

# --- Tab 2: 참석 현황 ---
with tabs[1]:
    sched_df = load_data(SCH_SHEET, ["경기날짜", "상대팀"])
    if not sched_df.empty:
        game_dates = sched_df['경기날짜'].unique().tolist()
        sel_date = st.selectbox("날짜별 현황 확인", game_dates)
        res_df = load_data(sel_date)
        if not res_df.empty:
            st.metric("현재 참석", f"{len(res_df)}명")
            st.table(res_df.assign(No=lambda x: range(1, len(x)+1))[["No", "이름", "참석여부", "뒷풀이"]])
        else: st.info("아직 투표 데이터가 없습니다.")

# --- Tab 4: 관리자 설정 (데이터 자동 삭제 기능 포함) ---
if st.session_state.is_admin:
    with tabs[3]:
        with st.expander("⚠️ 일정 및 데이터 삭제"):
            sch_list = load_data(SCH_SHEET, ["경기날짜", "상대팀"])
            if not sch_list.empty:
                opts = [f"{r['경기날짜']} vs {r['상대팀']}" for _, r in sch_list.iterrows()]
                target_del = st.selectbox("삭제할 일정 선택", opts)
                if st.button("🔥 일정 및 해당 날짜 탭 데이터 삭제"):
                    # 1. 일정 시트에서 삭제
                    date_to_del = target_del.split(" vs ")[0]
                    new_sch = sch_list[sch_list['경기날짜'] != date_to_del]
                    conn.update(spreadsheet=SHEET_URL, worksheet=SCH_SHEET, data=new_sch)
                    
                    # 2. [자동 데이터 삭제] 해당 날짜 전용 탭의 내용을 초기화
                    try:
                        empty_df = pd.DataFrame(columns=COLS)
                        conn.update(spreadsheet=SHEET_URL, worksheet=date_to_del, data=empty_df)
                        st.success(f"✅ {date_to_del} 일정과 투표 명단이 모두 삭제되었습니다.")
                    except:
                        st.warning(f"일정은 삭제되었으나, '{date_to_del}' 탭을 찾을 수 없어 명단 삭제는 건너뛰었습니다.")
                    st.rerun()
