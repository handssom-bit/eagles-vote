import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, time
import time as sleep_time

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
    div.vote-done > div.stButton > button {
        background-color: #FF6600 !important; color: #FFFFFF !important;
    }
    div.stButton > button:hover { background-color: #FF6600 !important; color: #FFFFFF !important; }
    .game-box { border-bottom: 1px solid #eee; padding: 15px 0; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 구글 시트 연결 ---
try:
    SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    st.error("⚠️ 시트 연결 설정(secrets)을 확인해주세요.")

SCH_SHEET, ADM_SHEET, VOTE_SHEET = "경기일정", "관리자명단", "투표결과"
COLS = ["경기정보", "경기장소", "날짜", "이름", "연락처", "참석여부", "뒷풀이"]

def load_data(sheet_name, columns=COLS):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl="0s")
        return df if df is not None and not df.empty else pd.DataFrame(columns=columns)
    except: return pd.DataFrame(columns=columns)

# 24시간 자동 숨김 필터링 (현황 확인을 위해 48시간으로 여유 있게 설정)
def get_active_games(df):
    if df.empty: return df
    now = datetime.now()
    active_indices = []
    for idx, row in df.iterrows():
        try:
            game_dt = datetime.strptime(f"{row['경기날짜']} {row['경기시간']}", "%Y-%m-%d %H:%M")
            if now <= game_dt + timedelta(hours=48): active_indices.append(idx)
        except: active_indices.append(idx)
    return df.loc[active_indices]

# --- 3. 세션 상태 초기화 ---
if 'is_admin' not in st.session_state: st.session_state.is_admin = False
if 'step' not in st.session_state: st.session_state.step = "input"
if 'user_info' not in st.session_state: st.session_state.user_info = {}
if 'selected_game_info' not in st.session_state: st.session_state.selected_game_info = {}
if 'voted_games' not in st.session_state: st.session_state.voted_games = []

# --- 4. 메인 화면 ---
st.title("⚾ 한화이글스 단관 모집")
tab_list = ["투표하기", "참석 현황", "관리자 인증"]
if st.session_state.is_admin: tab_list.append("⚙️ 관리자 설정")
tabs = st.tabs(tab_list)

# --- Tab 1: 투표하기 (기존 로직 유지) ---
with tabs[0]:
    raw_sched = load_data(SCH_SHEET, ["경기날짜", "상대팀", "경기시간", "투표마감", "경기장소"])
    sched_df = get_active_games(raw_sched)
    
    if sched_df.empty:
        st.info("현재 투표 가능한 경기 일정이 없습니다.")
    else:
        if st.session_state.step == "input":
            for index, row in sched_df.iterrows():
                game_tag = f"{row['경기날짜']} vs {row['상대팀']}"
                st.markdown(f'<div class="game-box"><b>📅 {row["경기날짜"]} ({row["경기시간"]}) vs {row["상대팀"]}</b><br>📍 {row["경기장소"]}</div>', unsafe_allow_html=True)
                is_voted = game_tag in st.session_state.voted_games
                if is_voted: st.markdown('<div class="vote-done">', unsafe_allow_html=True)
                if st.button("✅ 완료 / 재투표" if is_voted else "🧡 투표하기", key=f"v_{index}"):
                    st.session_state.selected_game_info = row.to_dict(); st.session_state.step = "info_input"; st.rerun()
                if is_voted: st.markdown('</div>', unsafe_allow_html=True)

        elif st.session_state.step == "info_input":
            st.subheader(f"📝 {st.session_state.selected_game_info['경기날짜']} 정보 입력")
            n = st.text_input("이름", key="in_n"); p = st.text_input("연락처 (숫자만)", key="in_p")
            plus = st.checkbox("+1 (동반인 포함)", key="in_plus")
            if st.button("다음"):
                if n and p: st.session_state.user_info = {"이름":n, "연락처":p.replace("-",""), "plus_one":plus}; st.session_state.step = "step1"; st.rerun()
                else: st.warning("정보를 입력해 주세요.")
        
        elif st.session_state.step == "step1":
            if st.button("🧡 단관참석"): st.session_state.user_info['참석']="참석"; st.session_state.step="step2"; st.rerun()
        
        elif st.session_state.step == "step2":
            c1, c2 = st.columns(2)
            if c1.button("🍻 뒷풀이 참석"): st.session_state.user_info['뒷풀이']="참석"; st.session_state.step="confirm"; st.rerun()
            if c2.button("🏠 미참석"): st.session_state.user_info['뒷풀이']="미참석"; st.session_state.step="confirm"; st.rerun()

        elif st.session_state.step == "confirm":
            if st.button("🚀 최종 투표 제출"):
                try:
                    info, user = st.session_state.selected_game_info, st.session_state.user_info
                    tag = f"{info['경기날짜']} vs {info['상대팀']}"
                    df = load_data(VOTE_SHEET)
                    if not df.empty:
                        df = df[~((df['경기정보']==tag) & (df['이름']==user['이름']) & (df['연락처']==user['연락처']))]
                        df = df[~((df['경기정보']==tag) & (df['이름']=="+1") & (df['연락처']=="-"))]
                    new_row = {"경기정보": tag, "경기장소": info['경기장소'], "날짜": datetime.now().strftime("%Y-%m-%d %H:%M"), "이름": user['이름'], "연락처": user['연락처'], "참석여부": "참석", "뒷풀이": user['뒷풀이']}
                    rows = [new_row]
                    if user['plus_one']: rows.append({**new_row, "이름": "+1", "연락처": "-", "날짜": "-"})
                    conn.update(spreadsheet=SHEET_URL, worksheet=VOTE_SHEET, data=pd.concat([df, pd.DataFrame(rows)], ignore_index=True))
                    st.session_state.voted_games.append(tag)
                    st.success("✅ 저장 성공!"); sleep_time.sleep(1); st.session_state.step = "input"; st.rerun()
                except Exception as e: st.error(f"❌ 오류: {e}")

# --- Tab 2: 참석 현황 (요청하신 기능 보강) ---
with tabs[1]:
    st.subheader("📊 실시간 참석 명단")
    raw_sched = load_data(SCH_SHEET, ["경기날짜", "상대팀", "경기시간"])
    visible_sched = get_active_games(raw_sched) # 48시간 내 경기만 노출
    
    if not visible_sched.empty:
        game_list = [f"{row['경기날짜']} vs {row['상대팀']}" for _, row in visible_sched.iterrows()]
        selected_game = st.selectbox("현황을 확인할 경기를 선택하세요", game_list, key="view_sel")
        
        all_res = load_data(VOTE_SHEET)
        # 선택한 경기에 해당하는 데이터만 필터링
        view_df = all_res[all_res['경기정보'] == selected_game].copy()
        
        if not view_df.empty:
            st.success(f"현재 총 {len(view_df)}명이 투표했습니다.")
            view_df.reset_index(drop=True, inplace=True); view_df.index += 1
            st.table(view_df[["이름", "참석여부", "뒷풀이"]])
            
            # 요약 정보
            party_in = len(view_df[view_df['뒷풀이'] == "참석"])
            st.info(f"🍻 뒷풀이 참석: {party_in}명 / 🏠 미참석: {len(view_df)-party_in}명")
        else:
            # [수정] 데이터가 없을 경우 명확하게 안내
            st.warning(f"📢 '{selected_game}' 경기는 아직 투표 결과가 없습니다.")
            st.info("투표하기 탭에서 첫 번째 투표를 완료해 주세요!")
    else:
        st.info("현재 현황을 확인할 수 있는 최근 경기 일정이 없습니다.")

# --- Tab 3: 관리자 인증 (기존 유지) ---
with tabs[2]:
    if not st.session_state.is_admin:
        st.subheader("🔐 관리자 로그인")
        ln = st.text_input("이름", key="a_n"); lp = st.text_input("연락처", type="password", key="a_p")
        if st.button("로그인"):
            if (ln == "윤상성" and lp == "01032200995") or not load_data(ADM_SHEET)[(load_data(ADM_SHEET)['이름']==ln) & (load_data(ADM_SHEET)['연락처'].astype(str)==lp)].empty:
                st.session_state.is_admin = True; st.rerun()
            else: st.error("정보 불일치")
    else:
        st.success("관리자 모드"); st.button("로그아웃", on_click=lambda: setattr(st.session_state, 'is_admin', False))

# --- Tab 4: 관리자 설정 (기존 유지) ---
if st.session_state.is_admin:
    with tabs[3]:
        with st.expander("📅 일정 등록"):
            with st.form("add"):
                c1, c2 = st.columns(2)
                d, o, l = c1.date_input("날짜"), c2.text_input("팀"), st.text_input("장소")
                t = c1.selectbox("시간", [time(h, m) for h in range(12, 24) for m in [0, 30]])
                if st.form_submit_button("저장"):
                    new = pd.DataFrame([{"경기날짜": str(d), "상대팀": o, "경기시간": t.strftime("%H:%M"), "투표마감": str(d)+" 23:59", "경기장소": l}])
                    conn.update(spreadsheet=SHEET_URL, worksheet=SCH_SHEET, data=pd.concat([load_data(SCH_SHEET), new], ignore_index=True)); st.rerun()
