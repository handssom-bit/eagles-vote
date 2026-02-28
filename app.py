import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, time
import time as sleep_time

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="한화이글스 단관 Pro", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; color: #000000; }
    h1, h2, h3 { color: #FF6600 !important; }
    div.stButton > button {
        background-color: #FFFFFF; color: #FF6600; border: 2px solid #FF6600;
        border-radius: 8px; height: 3.5em; font-weight: bold; width: 100%;
    }
    div.stButton > button:hover { background-color: #FF6600 !important; color: #FFFFFF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 시트 연결 설정 ---
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
conn = st.connection("gsheets", type=GSheetsConnection)

SCH_SHEET = "경기일정"
ADM_SHEET = "관리자명단"
VOTE_SHEET = "투표결과"
COLS = ["경기정보", "경기장소", "날짜", "이름", "연락처", "참석여부", "뒷풀이"]

def load_data(sheet_name, columns=COLS):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl="0s")
        return df if df is not None and not df.empty else pd.DataFrame(columns=columns)
    except:
        return pd.DataFrame(columns=columns)

# --- 3. 세션 상태 ---
if 'is_admin' not in st.session_state: st.session_state.is_admin = False
if 'step' not in st.session_state: st.session_state.step = "input"
if 'user_info' not in st.session_state: st.session_state.user_info = {}
if 'selected_game_info' not in st.session_state: st.session_state.selected_game_info = {}

# --- 4. 메인 UI ---
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
                loc = f" @{row['경기장소']}" if row['경기장소'] else ""
                if st.button(f"🧡 {row['경기날짜']} vs {row['상대팀']} ({row['경기시간']}){loc}", key=f"btn_{idx}"):
                    st.session_state.selected_game_info = row.to_dict()
                    st.session_state.step = "info_input"; st.rerun()

        elif st.session_state.step == "info_input":
            st.subheader(f"📝 [{st.session_state.selected_game_info['경기날짜']}] 정보 입력")
            st.info("💡 이미 투표하신 경우, 동일한 정보로 다시 입력하면 정보가 수정(재투표)됩니다.")
            name = st.text_input("이름", key="v_name")
            phone = st.text_input("연락처", key="v_phone")
            plus_one = st.checkbox("+1 (동반인 포함)")
            if st.button("다음 단계"):
                if name and phone:
                    st.session_state.user_info = {"이름": name, "연락처": phone, "plus_one": plus_one}
                    st.session_state.step = "step1"; st.rerun()
                else: st.warning("이름과 연락처를 입력해 주세요.")

        elif st.session_state.step == "step1":
            if st.button("🧡 단관참석"):
                st.session_state.user_info['참석'] = "참석"; st.session_state.step = "step2"; st.rerun()

        elif st.session_state.step == "step2":
            st.subheader("🍻 뒷풀이 여부")
            c1, c2 = st.columns(2)
            if c1.button("참석"): st.session_state.user_info['뒷풀이'] = "참석"; st.session_state.step = "confirm"; st.rerun()
            if c2.button("미참석"): st.session_state.user_info['뒷풀이'] = "미참석"; st.session_state.step = "confirm"; st.rerun()

        elif st.session_state.step == "confirm":
            if st.button("최종 투표 제출 (수정)"):
                info, user = st.session_state.selected_game_info, st.session_state.user_info
                target = str(info['경기날짜']).strip()
                new_row = {
                    "경기정보": f"{info['경기날짜']} vs {info['상대팀']}", "경기장소": info['경기장소'],
                    "날짜": datetime.now().strftime("%Y-%m-%d %H:%M"), "이름": user['이름'], 
                    "연락처": user['연락처'], "참석여부": "참석", "뒷풀이": user['뒷풀이']
                }
                
                # 데이터 처리 함수 (재투표 로직 포함)
                def save_vote(sheet_name):
                    df = load_data(sheet_name)
                    # 동일인물 데이터 제거 (이름과 연락처 기준)
                    if not df.empty:
                        df = df[~((df['이름'] == user['이름']) & (df['연락처'] == user['연락처']))]
                        # 동반인(+1) 데이터도 세트로 관리하기 위해 기존 +1 행도 삭제
                        # (보통 사용자 행 바로 다음에 오거나 이름이 +1인 경우)
                    
                    rows_to_add = [new_row]
                    if user['plus_one']:
                        rows_to_add.append({**new_row, "이름": "+1", "연락처": "-", "날짜": "-"})
                    
                    final_df = pd.concat([df, pd.DataFrame(rows_to_add)], ignore_index=True)
                    conn.update(spreadsheet=SHEET_URL, worksheet=sheet_name, data=final_df)

                # 개별 탭 및 통합 탭 동시 저장 시도
                try: save_vote(target)
                except: save_vote(VOTE_SHEET)
                
                st.success("✅ 투표(재투표)가 완료되었습니다! 잠시 후 메인 화면으로 이동합니다.")
                sleep_time.sleep(1.5)
                st.session_state.step = "input"; st.session_state.user_info = {}; st.rerun()

# --- Tab 2: 참석 현황 ---
with tabs[1]:
    sched_df = load_data(SCH_SHEET, ["경기날짜", "상대팀"])
    if not sched_df.empty:
        game_dates = sched_df['경기날짜'].unique().tolist()
        sel_date = st.selectbox("현황 확인할 날짜 선택", game_dates)
        res_df = load_data(sel_date)
        if not res_df.empty:
            st.metric("현재 참석 인원", f"{len(res_df)}명")
            st.table(res_df.assign(No=lambda x: range(1, len(x)+1))[["No", "이름", "참석여부", "뒷풀이"]])
        else: st.info("투표 데이터가 없습니다.")

# --- Tab 3: 관리자 인증 ---
with tabs[2]:
    if not st.session_state.is_admin:
        st.subheader("🔐 관리자 로그인")
        ln = st.text_input("이름", key="ln"); lp = st.text_input("연락처", type="password", key="lp")
        if st.button("로그인"):
            if (ln == "윤상성" and lp == "01032200995"): st.session_state.is_admin = True; st.rerun()
            adm_list = load_data(ADM_SHEET, ["이름", "연락처"])
            if not adm_list[(adm_list['이름'] == ln) & (adm_list['연락처'].astype(str) == lp)].empty:
                st.session_state.is_admin = True; st.rerun()
            else: st.error("정보 불일치")
    else:
        st.success("✅ 관리자 인증 완료"); st.button("로그아웃", on_click=lambda: setattr(st.session_state, 'is_admin', False))

# --- Tab 4: 관리자 설정 (명단 관리 유지) ---
if st.session_state.is_admin:
    with tabs[3]:
        with st.expander("👥 관리자 명단 관리", expanded=True):
            st.subheader("신규 등록")
            an, ap = st.text_input("새 관리자 이름", key="an"), st.text_input("연락처", key="ap")
            if st.button("관리자 추가"):
                old = load_data(ADM_SHEET, ["이름", "연락처"])
                conn.update(spreadsheet=SHEET_URL, worksheet=ADM_SHEET, data=pd.concat([old, pd.DataFrame([{"이름": an, "연락처": ap}])], ignore_index=True))
                st.success("등록 완료!"); st.rerun()
            st.divider()
            st.subheader("관리자 삭제")
            curr = load_data(ADM_SHEET, ["이름", "연락처"])
            adm_names = curr[curr['이름'] != "윤상성"]['이름'].tolist()
            if adm_names:
                target = st.selectbox("삭제할 관리자", adm_names)
                if st.button("삭제 실행"):
                    conn.update(spreadsheet=SHEET_URL, worksheet=ADM_SHEET, data=curr[curr['이름'] != target])
                    st.success("삭제 완료!"); st.rerun()
            else: st.info("삭제 가능한 추가 운영진이 없습니다.")
