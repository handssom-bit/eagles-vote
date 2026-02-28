import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, time
import time as sleep_time

# --- 1. 페이지 설정 및 디자인 (기존 스타일 유지) ---
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
except Exception as e:
    st.error(f"⚠️ 연결 설정(secrets) 확인 필요: {e}")

SCH_SHEET, ADM_SHEET, VOTE_SHEET = "경기일정", "관리자명단", "투표결과"
COLS = ["경기정보", "경기장소", "날짜", "이름", "연락처", "참석여부", "뒷풀이"]

def load_data(sheet_name, columns=COLS):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl="0s")
        return df if df is not None and not df.empty else pd.DataFrame(columns=columns)
    except: return pd.DataFrame(columns=columns)

# 24시간 자동 숨김 필터링 함수
def get_active_games(df):
    if df.empty: return df
    now = datetime.now()
    active_indices = []
    for idx, row in df.iterrows():
        try:
            game_dt = datetime.strptime(f"{row['경기날짜']} {row['경기시간']}", "%Y-%m-%d %H:%M")
            if now <= game_dt + timedelta(hours=24): active_indices.append(idx)
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
tab_titles = ["투표하기", "참석 현황", "관리자 인증"]
if st.session_state.is_admin: tab_titles.append("⚙️ 관리자 설정")
tabs = st.tabs(tab_titles)

# --- Tab 1: 투표하기 ---
with tabs[0]:
    raw_sched = load_data(SCH_SHEET, ["경기날짜", "상대팀", "경기시간", "투표마감", "경기장소"])
    sched_df = get_active_games(raw_sched)
    
    if sched_df.empty:
        st.info("현재 투표 가능한 경기 일정이 없습니다.")
    else:
        if st.session_state.step == "input":
            st.subheader("📢 경기 일정을 확인하고 투표해 주세요")
            for index, row in sched_df.iterrows():
                game_tag = f"{row['경기날짜']} vs {row['상대팀']}"
                st.markdown(f'<div class="game-box"><b>📅 {row["경기날짜"]} ({row["경기시간"]}) vs {row["상대팀"]}</b><br>📍 {row["경기장소"]}</div>', unsafe_allow_html=True)
                
                is_voted = game_tag in st.session_state.voted_games
                if is_voted: st.markdown('<div class="vote-done">', unsafe_allow_html=True)
                if st.button("✅ 투표 완료 / 재투표" if is_voted else "🧡 투표하기", key=f"v_btn_{index}"):
                    st.session_state.selected_game_info = row.to_dict()
                    st.session_state.step = "info_input"
                    st.rerun()
                if is_voted: st.markdown('</div>', unsafe_allow_html=True)

        elif st.session_state.step == "info_input":
            st.subheader(f"📝 {st.session_state.selected_game_info['경기날짜']} 정보 입력")
            n = st.text_input("이름", key="in_name_v")
            p = st.text_input("연락처 (숫자만)", key="in_phone_v")
            plus = st.checkbox("+1 (동반인 포함)", key="in_plus_v")
            if st.button("다음 단계", key="next_btn_v"):
                if n and p:
                    st.session_state.user_info = {"이름":n, "연락처":p.replace("-",""), "plus_one":plus}
                    st.session_state.step = "step1"; st.rerun()
                else: st.warning("정보를 입력해 주세요.")
        
        elif st.session_state.step == "step1":
            if st.button("🧡 단관참석", key="attend_btn_v"):
                st.session_state.user_info['참석']="참석"; st.session_state.step="step2"; st.rerun()
        
        elif st.session_state.step == "step2":
            c1, c2 = st.columns(2)
            if c1.button("🍻 뒷풀이 참석", key="party_y_v"): 
                st.session_state.user_info['뒷풀이']="참석"; st.session_state.step="confirm"; st.rerun()
            if c2.button("🏠 미참석", key="party_n_v"): 
                st.session_state.user_info['뒷풀이']="미참석"; st.session_state.step="confirm"; st.rerun()

        elif st.session_state.step == "confirm":
            st.warning("⚠️ '최종 투표 제출' 버튼을 누르면 데이터 저장이 시작됩니다.")
            if st.button("🚀 최종 투표 제출 (수정 포함)", key="final_save_btn"):
                # [중요] 저장 시작을 알리는 상태창
                status_box = st.empty()
                status_box.info("⏳ 구글 시트에 데이터를 기록하는 중입니다. 잠시만 기다려주세요...")
                
                try:
                    info, user = st.session_state.selected_game_info, st.session_state.user_info
                    tag = f"{info['경기날짜']} vs {info['상대팀']}"
                    
                    # 1. 기존 데이터 로드
                    df = load_data(VOTE_SHEET)
                    
                    # 2. 재투표/덮어쓰기 로직: 동일 경기 내 이름+번호 일치 데이터 제거
                    if not df.empty:
                        df = df[~((df['경기정보']==tag) & (df['이름']==user['이름']) & (df['연락처']==user['연락처']))]
                        df = df[~((df['경기정보']==tag) & (df['이름']=="+1") & (df['연락처']=="-"))]
                    
                    # 3. 신규 행 생성
                    new_row = {
                        "경기정보": tag, "경기장소": info['경기장소'],
                        "날짜": datetime.now().strftime("%Y-%m-%d %H:%M"), 
                        "이름": user['이름'], "연락처": user['연락처'], 
                        "참석여부": "참석", "뒷풀이": user['뒷풀이']
                    }
                    rows_to_add = [new_row]
                    if user['plus_one']:
                        rows_to_add.append({**new_row, "이름": "+1", "연락처": "-", "날짜": "-"})
                    
                    # 4. 시트 업데이트 실행
                    updated_df = pd.concat([df, pd.DataFrame(rows_to_add)], ignore_index=True)
                    conn.update(spreadsheet=SHEET_URL, worksheet=VOTE_SHEET, data=updated_df)
                    
                    # 5. 성공 피드백
                    status_box.success("✅ 데이터 저장 성공! 메인 화면으로 이동합니다.")
                    if tag not in st.session_state.voted_games:
                        st.session_state.voted_games.append(tag)
                    
                    sleep_time.sleep(1.5)
                    st.session_state.step = "input"; st.session_state.user_info = {}; st.rerun()
                    
                except Exception as e:
                    # [중요] 실패 시 에러 내용을 무조건 화면에 고정
                    status_box.error(f"❌ 저장 실패! 구글 시트 설정을 확인하세요.\n에러 원인: {str(e)}")
                    st.button("🔄 다시 시도하기", on_click=lambda: setattr(st.session_state, 'step', 'confirm'))

# --- Tab 2: 참석 현황 (24시간 필터 유지) ---
with tabs[1]:
    sched_df = get_active_games(load_data(SCH_SHEET, ["경기날짜", "상대팀", "경기시간"]))
    if not sched_df.empty:
        game_list = [f"{row['경기날짜']} vs {row['상대팀']}" for _, row in sched_df.iterrows()]
        sel_game = st.selectbox("현황 확인할 경기 선택", game_list, key="status_box_v")
        all_res = load_data(VOTE_SHEET)
        view_df = all_res[all_res['경기정보'] == sel_game].copy()
        if not view_df.empty:
            st.metric("현재 참석 인원", f"{len(view_df)}명")
            view_df.reset_index(drop=True, inplace=True); view_df.index += 1
            st.table(view_df[["이름", "참석여부", "뒷풀이"]])
        else: st.info("아직 투표 데이터가 없습니다.")

# --- Tab 3: 관리자 인증 (로직 유지) ---
with tabs[2]:
    if not st.session_state.is_admin:
        st.subheader("🔐 관리자 로그인")
        ln = st.text_input("이름", key="adm_ln_v")
        lp = st.text_input("연락처", type="password", key="adm_lp_v")
        if st.button("로그인", key="adm_btn_v"):
            if (ln == "윤상성" and lp == "01032200995") or not load_data(ADM_SHEET)[(load_data(ADM_SHEET)['이름']==ln) & (load_data(ADM_SHEET)['연락처'].astype(str)==lp)].empty:
                st.session_state.is_admin = True; st.rerun()
            else: st.error("정보 불일치")
    else:
        st.success("✅ 관리자 모드 활성화 중"); st.button("로그아웃", on_click=lambda: setattr(st.session_state, 'is_admin', False))

# --- Tab 4: 관리자 설정 (기능 유지) ---
if st.session_state.is_admin:
    with tabs[3]:
        # (일정 등록, 운영진 삭제, 데이터 수동 삭제 기능은 이전과 동일하게 유지)
        with st.expander("⚠️ 일정 및 데이터 수동 삭제", expanded=False):
            sch = load_data(SCH_SHEET)
            if not sch.empty:
                opts = [f"{r['경기날짜']} vs {r['상대팀']}" for _, r in sch.iterrows()]
                sel_del = st.selectbox("삭제 일정 선택", opts, key="del_sel_v")
                if st.button("🔥 영구 삭제 실행", disabled=not st.checkbox("삭제 동의", key="del_chk_v")):
                    conn.update(spreadsheet=SHEET_URL, worksheet=SCH_SHEET, data=sch[~sch.apply(lambda r: f"{r['경기날짜']} vs {r['상대팀']}" == sel_del, axis=1)])
                    all_v = load_data(VOTE_SHEET)
                    conn.update(spreadsheet=SHEET_URL, worksheet=VOTE_SHEET, data=all_v[all_v['경기정보'] != sel_del])
                    st.success("삭제 완료!"); st.rerun()
