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
    /* 비활성화 버튼 스타일 */
    div.stButton > button:disabled {
        background-color: #EEEEEE !important; color: #999999 !important; border: 2px solid #CCCCCC !important;
    }
    div.stButton > button:hover:not(:disabled) { background-color: #FF6600 !important; color: #FFFFFF !important; }
    .game-box { border-bottom: 1px solid #eee; padding: 15px 0; margin-bottom: 10px; }
    .status-badge { background-color: #FF0000; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; margin-right: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 구글 시트 연결 ---
try:
    SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    st.error("⚠️ 시트 연결 설정을 확인해주세요.")

SCH_SHEET, ADM_SHEET, VOTE_SHEET = "경기일정", "관리자명단", "투표결과"
COLS = ["경기정보", "경기장소", "날짜", "이름", "연락처", "참석여부", "뒷풀이"]

def load_data(sheet_name, columns=COLS):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl="0s")
        if df is None or df.empty: return pd.DataFrame(columns=columns)
        return df
    except: return pd.DataFrame(columns=columns)

def get_active_games(df):
    if df.empty: return df
    now = datetime.now()
    active_indices = []
    for idx, row in df.iterrows():
        try:
            if pd.isna(row['경기날짜']): continue
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

# --- 4. 메인 화면 탭 구성 ---
main_tabs = ["투표하기", "참석 현황"]
if not st.session_state.is_admin:
    main_tabs.append("관리자 인증")
else:
    main_tabs.extend(["일정 등록", "일정관리 및 데이터 삭제", "관리자 명단 관리", "🔓 로그아웃"])

tabs = st.tabs(main_tabs)

# --- [Tab 0: 투표하기] ---
with tabs[0]:
    raw_sched = load_data(SCH_SHEET, ["경기날짜", "상대팀", "경기시간", "투표마감", "경기장소"])
    sched_df = get_active_games(raw_sched)
    if sched_df.empty: st.info("현재 투표 가능한 경기 일정이 없습니다.")
    else:
        if st.session_state.step == "input":
            st.subheader("📢 경기 일정을 확인하고 투표해 주세요")
            now = datetime.now()
            for index, row in sched_df.iterrows():
                game_tag = f"{row['경기날짜']} vs {row['상대팀']}"
                
                # 투표 마감 여부 확인 로직
                try:
                    deadline_dt = datetime.strptime(row['투표마감'], "%Y-%m-%d %H:%M")
                    is_expired = now > deadline_dt
                except:
                    is_expired = False

                # 마감 시 [투표종료] 텍스트 추가
                expire_txt = '<span class="status-badge">투표종료</span>' if is_expired else ""
                st.markdown(f'''
                    <div class="game-box">
                        {expire_txt}<b>📅 {row["경기날짜"]} ({row["경기시간"]}) vs {row["상대팀"]}</b><br>
                        📍 {row["경기장소"]}<br>
                        <small style="color:{"#999" if is_expired else "red"};">⏰ 마감시간: {row["투표마감"]}</small>
                    </div>''', unsafe_allow_html=True)
                
                is_voted = game_tag in st.session_state.voted_games
                
                # 투표 종료 시 처리
                if is_expired:
                    if st.button("투표가 종료되었습니다", key=f"v_btn_{index}", disabled=True):
                        pass # 비활성화 버튼
                else:
                    if is_voted: st.markdown('<div class="vote-done">', unsafe_allow_html=True)
                    if st.button("✅ 투표 완료 / 재투표" if is_voted else "🧡 투표하기", key=f"v_btn_{index}"):
                        st.session_state.selected_game_info = row.to_dict(); st.session_state.step = "info_input"; st.rerun()
                    if is_voted: st.markdown('</div>', unsafe_allow_html=True)

        elif st.session_state.step == "info_input":
            # (투표 프로세스 로직 유지)
            st.subheader(f"📝 {st.session_state.selected_game_info['경기날짜']} 정보 입력")
            n = st.text_input("이름", key="n_f"); p = st.text_input("연락처", key="p_f")
            plus = st.checkbox("+1 (동반인 포함)", key="plus_f")
            
            # 여기서도 한 번 더 마감 체크 (부정 투표 방지)
            now_check = datetime.now()
            try:
                deadline_dt = datetime.strptime(st.session_state.selected_game_info['투표마감'], "%Y-%m-%d %H:%M")
                if now_check > deadline_dt:
                    st.error("이미 종료된 투표입니다.")
                    if st.button("처음으로"): st.session_state.step = "input"; st.rerun()
                    st.stop()
            except: pass

            if st.button("다음"):
                if n and p: st.session_state.user_info = {"이름":n, "연락처":p.replace("-",""), "plus_one":plus}; st.session_state.step = "step1"; st.rerun()
                else: st.warning("정보를 입력해 주세요.")
        
        # (step1, step2, confirm 로직 기존과 동일하게 유지)
        elif st.session_state.step == "step1":
            if st.button("🧡 단관참석"): st.session_state.user_info['참석']="참석"; st.session_state.step="step2"; st.rerun()
        elif st.session_state.step == "step2":
            c1, c2 = st.columns(2); 
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
                    if tag not in st.session_state.voted_games: st.session_state.voted_games.append(tag)
                    st.success("✅ 저장 완료!"); sleep_time.sleep(1); st.session_state.step = "input"; st.rerun()
                except Exception as e: st.error(f"❌ 저장 오류: {e}")

# --- [Tab 1: 참석 현황] ---
with tabs[1]:
    st.subheader("📊 실시간 참석 명단")
    raw_sched = load_data(SCH_SHEET, ["경기날짜", "상대팀", "경기시간"])
    visible_sched = get_active_games(raw_sched)
    if not visible_sched.empty:
        game_list = [f"{row['경기날짜']} vs {row['상대팀']}" for _, row in visible_sched.iterrows()]
        sel_game = st.selectbox("경기를 선택하세요", game_list, key="stat_sel")
        all_res = load_data(VOTE_SHEET)
        view_df = all_res[all_res['경기정보'] == sel_game].copy()
        if not view_df.empty:
            st.success(f"현재 총 {len(view_df)}명이 투표했습니다.")
            view_df.reset_index(drop=True, inplace=True); view_df.index += 1
            st.table(view_df[["이름", "참석여부", "뒷풀이"]])
        else: st.warning(f"📢 '{sel_game}' 경기는 아직 투표 결과가 없습니다.")
    else: st.info("최근 경기 일정이 없습니다.")

# --- [관리자 전용 기능 Tabs 2~5 로직 동일 유지] ---
if not st.session_state.is_admin:
    with tabs[2]:
        st.subheader("🔐 관리자 로그인")
        ln = st.text_input("이름", key="a_n"); lp = st.text_input("연락처", type="password", key="a_p")
        if st.button("로그인"):
            if (ln == "윤상성" and lp == "01032200995") or not load_data(ADM_SHEET)[(load_data(ADM_SHEET)['이름']==ln) & (load_data(ADM_SHEET)['연락처'].astype(str)==lp)].empty:
                st.session_state.is_admin = True; st.rerun()
            else: st.error("정보 불일치")
else:
    # 1. 일정 등록 (투표 마감 설정 포함)
    with tabs[2]:
        st.subheader("📅 새 경기 일정 등록")
        with st.form("add_game_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            d = c1.date_input("경기 날짜", value=datetime.now())
            o = c2.text_input("상대팀")
            l = st.text_input("경기 장소")
            t = c1.selectbox("경기 시작 시간", [time(h, m) for h in range(12, 24) for m in [0, 30]])
            st.divider()
            col_d, col_t = st.columns(2)
            deadline_date = col_d.date_input("투표 마감 날짜", value=d)
            deadline_time = col_t.selectbox("투표 마감 시간", [time(h, m) for h in range(0, 24) for m in [0, 30, 59]], index=47)
            if st.form_submit_button("일정 저장"):
                if o and l:
                    deadline_str = f"{deadline_date} {deadline_time.strftime('%H:%M')}"
                    new_data = pd.DataFrame([{"경기날짜": str(d), "상대팀": o, "경기시간": t.strftime("%H:%M"), "투표마감": deadline_str, "경기장소": l}])
                    conn.update(spreadsheet=SHEET_URL, worksheet=SCH_SHEET, data=pd.concat([load_data(SCH_SHEET), new_data], ignore_index=True))
                    st.success(f"✅ 저장 완료!"); sleep_time.sleep(1); st.rerun()
                else: st.warning("필수 입력 누락")

    # 2. 일정관리 및 데이터 삭제
    with tabs[3]:
        st.subheader("⚠️ 일정관리 및 데이터 삭제")
        sch_all = load_data(SCH_SHEET, ["경기날짜", "상대팀"])
        if not sch_all.empty:
            opts = [f"{r['경기날짜']} vs {r['상대팀']}" for _, r in sch_all.iterrows()]
            sel_del = st.selectbox("삭제할 일정 선택", opts)
            if st.button("🔥 삭제 실행", disabled=not st.checkbox("삭제 동의")):
                conn.update(spreadsheet=SHEET_URL, worksheet=SCH_SHEET, data=sch_all[~sch_all.apply(lambda r: f"{r['경기날짜']} vs {r['상대팀']}" == sel_del, axis=1)])
                all_v = load_data(VOTE_SHEET); conn.update(spreadsheet=SHEET_URL, worksheet=VOTE_SHEET, data=all_v[all_v['경기정보'] != sel_del])
                st.success("✅ 완료!"); st.rerun()

    # 3. 관리자 명단 관리
    with tabs[4]:
        st.subheader("👤 운영진 추가 및 삭제")
        col_a, col_b = st.columns(2)
        with col_a:
            an = st.text_input("이름", key="new_adm_name"); ap = st.text_input("연락처", key="new_adm_phone")
            if st.button("운영진 등록"):
                conn.update(spreadsheet=SHEET_URL, worksheet=ADM_SHEET, data=pd.concat([load_data(ADM_SHEET), pd.DataFrame([{"이름": an, "연락처": ap}])], ignore_index=True))
                st.success("✅ 등록 성공!"); st.rerun()
        with col_b:
            curr_adm = load_data(ADM_SHEET); adm_names = curr_adm[curr_adm['이름'] != "윤상성"]['이름'].tolist()
            if adm_names:
                target_adm = st.selectbox("삭제 대상", adm_names)
                if st.button("운영진 삭제하기"):
                    conn.update(spreadsheet=SHEET_URL, worksheet=ADM_SHEET, data=curr_adm[curr_adm['이름'] != target_adm]); st.rerun()

    # 4. 로그아웃
    with tabs[5]:
        if st.button("🔓 로그아웃 실행"): st.session_state.is_admin = False; st.rerun()
