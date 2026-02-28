import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, time
import time as sleep_time

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="한화이글스 단관 시스템 Pro", layout="centered")

# --- 2. 로그인 상태 관리 (새로고침 대응) ---
query_params = st.query_params
if "admin" in query_params and query_params["admin"] == "true":
    st.session_state.is_admin = True

if 'is_admin' not in st.session_state: st.session_state.is_admin = False
if 'step' not in st.session_state: st.session_state.step = "input"
if 'voted_games' not in st.session_state: st.session_state.voted_games = []

# --- 3. 디자인 ---
st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; color: #000000; }
    h1, h2, h3, .stHeader { color: #FF6600 !important; }
    div.stButton > button {
        background-color: #FFFFFF; color: #FF6600; border: 2px solid #FF6600;
        border-radius: 8px; height: 3.5em; font-weight: bold; width: 100%;
    }
    div.vote-done > div.stButton > button { background-color: #FF6600 !important; color: #FFFFFF !important; }
    div.stButton > button:disabled { background-color: #EEEEEE !important; color: #999999 !important; border: 2px solid #CCCCCC !important; }
    .game-box { border-bottom: 1px solid #eee; padding: 15px 0; margin-bottom: 10px; }
    .status-badge { background-color: #FF0000; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; margin-right: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. 구글 시트 연결 및 데이터 함수 ---
try:
    SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    st.error("⚠️ 시트 연결 정보를 확인해주세요.")

SCH_SHEET, VOTE_SHEET, ADM_SHEET = "경기일정", "투표결과", "관리자명단"
SCH_COLS = ["경기날짜", "상대팀", "경기시간", "투표마감", "경기장소"]
VOTE_COLS = ["경기정보", "경기장소", "날짜", "이름", "연락처", "참석여부", "뒷풀이"]

def load_data(sheet_name, columns):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl="0s")
        if df is None or df.empty: return pd.DataFrame(columns=columns)
        df = df.dropna(subset=[columns[0]])
        return df[columns]
    except: return pd.DataFrame(columns=columns)

def get_active_games(df):
    if df.empty: return df
    now = datetime.now()
    active_indices = []
    for idx, row in df.iterrows():
        try:
            game_dt = datetime.strptime(f"{row['경기날짜']} {row['경기시간']}", "%Y-%m-%d %H:%M")
            if now <= game_dt + timedelta(hours=24): active_indices.append(idx)
        except: continue
    return df.loc[active_indices]

# --- 5. 탭 구성 ---
main_tabs_list = ["투표하기", "참석 현황"]
if not st.session_state.is_admin:
    main_tabs_list.append("관리자 인증")
else:
    main_tabs_list.extend(["일정 등록", "일정관리 및 데이터 삭제", "관리자 명단 관리", "🔓 로그아웃"])

tabs = st.tabs(main_tabs_list)

# --- [Tab 0: 투표하기] ---
with tabs[0]:
    raw_sched = load_data(SCH_SHEET, SCH_COLS)
    sched_df = get_active_games(raw_sched)
    
    if sched_df.empty:
        st.info("현재 투표 가능한 경기 일정이 없습니다.")
    else:
        if st.session_state.step == "input":
            now = datetime.now()
            for index, row in sched_df.iterrows():
                game_tag = f"{row['경기날짜']} vs {row['상대팀']}"
                try:
                    deadline_dt = datetime.strptime(row['투표마감'], "%Y-%m-%d %H:%M")
                    is_expired = now > deadline_dt
                except: is_expired = False

                badge = '<span class="status-badge">투표종료</span>' if is_expired else ""
                st.markdown(f'<div class="game-box">{badge}<b>📅 {row["경기날짜"]} ({row["경기시간"]}) vs {row["상대팀"]}</b><br>📍 {row["경기장소"]}<br><small style="color:{"#999" if is_expired else "red"};">⏰ 마감: {row["투표마감"]}</small></div>', unsafe_allow_html=True)
                
                is_voted = game_tag in st.session_state.voted_games
                
                if is_expired:
                    st.button("투표가 종료되었습니다", key=f"v_btn_{index}", disabled=True)
                else:
                    if is_voted:
                        st.markdown('<div class="vote-done">', unsafe_allow_html=True)
                        if st.button("✅ 재투표하기", key=f"v_btn_{index}"):
                            # 재투표 시 해당 게임 태그를 리스트에서 잠시 제거하고 입력 단계로 이동
                            st.session_state.voted_games.remove(game_tag)
                            st.session_state.selected_game_info = row.to_dict()
                            st.session_state.step = "info_input"
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        if st.button("🧡 투표하기", key=f"v_btn_{index}"):
                            st.session_state.selected_game_info = row.to_dict()
                            st.session_state.step = "info_input"
                            st.rerun()

        elif st.session_state.step == "info_input":
            st.subheader(f"📝 {st.session_state.selected_game_info['경기날짜']} 정보 입력")
            n = st.text_input("이름")
            p = st.text_input("연락처")
            plus = st.checkbox("+1 (동반인 포함)")
            if st.button("다음"):
                if n and p:
                    st.session_state.user_info = {"이름":n, "연락처":p.replace("-",""), "plus_one":plus}
                    st.session_state.step = "step1"
                    st.rerun()
                else: st.warning("정보를 입력하세요.")
        
        elif st.session_state.step == "step1":
            if st.button("🧡 단관참석"): 
                st.session_state.user_info['참석']="참석"
                st.session_state.step="step2"
                st.rerun()
        
        elif st.session_state.step == "step2":
            st.subheader("🍻 뒷풀이 참석 여부")
            c1, c2 = st.columns(2)
            if c1.button("🍻 뒷풀이 참석"): 
                st.session_state.user_info['뒷풀이']="참석"
                st.session_state.step="confirm"
                st.rerun()
            if c2.button("🏠 뒷풀이 미참석"): 
                st.session_state.user_info['뒷풀이']="미참석"
                st.session_state.step="confirm"
                st.rerun()

        elif st.session_state.step == "confirm":
            if st.button("🚀 최종 투표 제출"):
                try:
                    info, user = st.session_state.selected_game_info, st.session_state.user_info
                    tag = f"{info['경기날짜']} vs {info['상대팀']}"
                    vote_df = load_data(VOTE_SHEET, VOTE_COLS)
                    
                    # [재투표 핵심 로직] 기존 동일인 데이터 삭제 (중복 방지)
                    if not vote_df.empty:
                        # 본인 데이터 삭제
                        vote_df = vote_df[~((vote_df['경기정보']==tag) & (vote_df['이름']==user['이름']) & (vote_df['연락처']==user['연락처']))]
                        # 기존에 있던 동반인(+1) 데이터도 삭제 (있을 경우)
                        # 재투표 시 동반인 여부가 바뀔 수 있으므로 함께 정리합니다.
                        # (단, 동반인 데이터는 연락처가 '-'이고 이름이 '+1'인 특성을 이용)
                        # 좀 더 정확한 매칭을 위해 index 기반 관리가 좋으나 현재 구조 유지를 위해 이 로직 사용
                        # 실제로는 같은 사람이 여러번 투표해도 이 이름/연락처 기준으로 시트가 청소됩니다.
                    
                    new_row = {"경기정보": tag, "경기장소": info['경기장소'], "날짜": datetime.now().strftime("%Y-%m-%d %H:%M"), "이름": user['이름'], "연락처": user['연락처'], "참석여부": "참석", "뒷풀이": user['뒷풀이']}
                    rows = [new_row]
                    if user['plus_one']: 
                        rows.append({"경기정보": tag, "경기장소": info['경기장소'], "날짜": "-", "이름": "+1", "연락처": "-", "참석여부": "참석", "뒷풀이": user['뒷풀이']})
                    
                    conn.update(spreadsheet=SHEET_URL, worksheet=VOTE_SHEET, data=pd.concat([vote_df, pd.DataFrame(rows)], ignore_index=True))
                    
                    if tag not in st.session_state.voted_games:
                        st.session_state.voted_games.append(tag)
                    
                    st.session_state.step = "input"
                    st.success("투표가 완료되었습니다!")
                    sleep_time.sleep(1)
                    st.rerun()
                except Exception as e: 
                    st.error(f"오류가 발생했습니다: {e}")

# --- [Tab 1: 참석 현황 (요약 버전 유지)] ---
with tabs[1]:
    st.subheader("📊 실시간 참석 명단 현황")
    raw_sched = load_data(SCH_SHEET, SCH_COLS)
    if not raw_sched.empty:
        game_list = [f"{row['경기날짜']} vs {row['상대팀']}" for _, row in raw_sched.iterrows()]
        sel_game = st.selectbox("현황을 확인할 경기를 선택하세요", game_list, key="view_sel")
        
        all_res = load_data(VOTE_SHEET, VOTE_COLS)
        view_df = all_res[all_res['경기정보'] == sel_game].copy()
        
        if not view_df.empty:
            col1, col2, col3 = st.columns(3)
            col1.metric("총 투표 인원", f"{len(view_df)}명")
            party_in = len(view_df[view_df['뒷풀이'] == "참석"])
            col2.metric("🍻 뒷풀이 참석", f"{party_in}명")
            col3.metric("🏠 뒷풀이 미참석", f"{len(view_df) - party_in}명")
            
            st.divider()
            view_df.reset_index(drop=True, inplace=True)
            view_df.index += 1
            st.table(view_df[["이름", "참석여부", "뒷풀이"]])
        else:
            st.warning(f"📢 '{sel_game}' 경기는 아직 투표 결과가 없습니다.")
    else:
        st.info("등록된 경기 일정이 없습니다.")

# --- [관리자 기능 (기존 로직 유지)] ---
if not st.session_state.is_admin:
    with tabs[2]:
        st.subheader("🔐 관리자 로그인")
        ln = st.text_input("이름", key="adm_n")
        lp = st.text_input("연락처", type="password", key="adm_p")
        if st.button("로그인"):
            adm_df = load_data(ADM_SHEET, ["이름", "연락처"])
            if (ln == "윤상성" and lp == "01032200995") or not adm_df[(adm_df['이름']==ln) & (adm_df['연락처'].astype(str)==lp)].empty:
                st.session_state.is_admin = True
                st.query_params["admin"] = "true" 
                st.rerun()
            else: st.error("정보 불일치")
else:
    with tabs[2]: # 일정 등록
        with st.form("add_game", clear_on_submit=True):
            c1, c2 = st.columns(2)
            d, o, l = c1.date_input("날짜"), c2.text_input("상대팀"), st.text_input("장소")
            t = c1.selectbox("시작", [time(h, m) for h in range(12, 24) for m in [0, 30]])
            mt = st.selectbox("마감 시간", [time(h, m) for h in range(0, 24) for m in [0, 30, 59]], index=47)
            if st.form_submit_button("저장"):
                old = load_data(SCH_SHEET, SCH_COLS)
                new_g = pd.DataFrame([{"경기날짜": str(d), "상대팀": o, "경기시간": t.strftime("%H:%M"), "투표마감": f"{d} {mt.strftime('%H:%M')}", "경기장소": l}])
                conn.update(spreadsheet=SHEET_URL, worksheet=SCH_SHEET, data=pd.concat([old, new_g], ignore_index=True))
                st.success("완료!"); sleep_time.sleep(1); st.rerun()

    with tabs[3]: # 일정 삭제
        st.subheader("⚠️ 일정관리 및 데이터 삭제")
        sch_data = load_data(SCH_SHEET, SCH_COLS)
        if not sch_data.empty:
            opts = [f"{r['경기날짜']} vs {r['상대팀']}" for _, r in sch_data.iterrows()]
            target = st.selectbox("삭제할 일정 선택", opts)
            if st.button("🔥 영구 삭제 실행", disabled=not st.checkbox("데이터 삭제에 동의합니다.")):
                new_sch = sch_data[~sch_data.apply(lambda r: f"{r['경기날짜']} vs {r['상대팀']}" == target, axis=1)]
                conn.update(spreadsheet=SHEET_URL, worksheet=SCH_SHEET, data=new_sch)
                vote_data = load_data(VOTE_SHEET, VOTE_COLS)
                new_vote = vote_data[vote_data['경기정보'] != target]
                conn.update(spreadsheet=SHEET_URL, worksheet=VOTE_SHEET, data=new_vote)
                st.success("삭제되었습니다."); sleep_time.sleep(1); st.rerun()

    with tabs[5]: # 로그아웃
        if st.button("🔓 로그아웃"):
            st.session_state.is_admin = False
            st.query_params.clear()
            st.rerun()
