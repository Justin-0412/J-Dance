import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import os
import re
import base64
import json
import io
import random
import time
import html

# ==========================================
# 1. 页面配置与原生组件彻底隐藏
# ==========================================
st.set_page_config(page_title="J-Dance | 专属英语练习", layout="wide", initial_sidebar_state="expanded")

hide_streamlit_style = """
<style>
    /* 彻底隐藏右上角默认菜单 */
    [data-testid="stToolbar"] {visibility: hidden !important;}
    #MainMenu {visibility: hidden !important;}

    /* 彻底隐藏原生顶栏和原生折叠按钮，为我们的自定义按钮让路 */
    [data-testid="stHeader"] { opacity: 0 !important; pointer-events: none !important; height: 0 !important; padding: 0 !important; }
    header::before { display: none !important; } 
    [data-testid="stSidebarHeader"] { opacity: 0 !important; pointer-events: none !important; height: 0 !important; margin: 0 !important; padding: 0 !important; }

    /* 页面顶部留白，防止内容顶天花板 */
    .block-container {padding-top: 5rem !important; max-width: 100%;}
    
    /* ========================================= */
    /* 🔥 黑客级 CSS：强行汉化文件上传组件 🔥 */
    /* ========================================= */
    [data-testid="stFileUploadDropzone"] > div > div > span { display: none !important; }
    [data-testid="stFileUploadDropzone"] > div > div > small { display: none !important; }
    [data-testid="stFileUploadDropzone"] > div > div::before { 
        content: "拖拽课程文件至此处"; 
        display: block; margin-bottom: 5px; color: #888; 
        font-family: 'Microsoft YaHei', sans-serif; font-size: 15px; 
    }
    [data-testid="stFileUploadDropzone"] > div > div::after { 
        content: "支持限制：200MB 以内 • 仅限 Excel 格式"; 
        display: block; font-size: 12px; color: #aaa; margin-top: 5px; 
    }
    [data-testid="stFileUploadDropzone"] button p { display: none !important; }
    [data-testid="stFileUploadDropzone"] button::after { 
        content: "浏览并选择文件"; 
        display: block; font-size: 14px; font-weight: 500; font-family: 'Microsoft YaHei', sans-serif;
    }
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)


# 内存缓存加载音频
@st.cache_data
def get_audio_base64(file_path):
    if not os.path.exists(file_path):
        return ""
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode()


# ==========================================
# 2. 侧边栏：多用户与 UI 管理
# ==========================================
st.sidebar.title("🎧 J-Dance")

user_name = st.sidebar.text_input("👤 用户昵称", value="Justin_Wen", help="修改昵称可创建独立的学习进度存档")
if not user_name:
    st.sidebar.warning("⚠️ 请输入昵称以加载进度！")
    st.stop()

theme_mode = st.sidebar.radio("🌗 屏幕模式", ["白天模式", "夜间模式", "跟随系统"], index=0)

if theme_mode == "夜间模式":
    st.markdown("""<style>
        .stApp { background-color: #121212 !important; color: #eee !important; }
        [data-testid="stSidebar"] { background-color: #1a1a1a !important; }
        h1, h2, h3, p, label, div { color: #eee !important; }
    </style>""", unsafe_allow_html=True)
    html_theme_class = "theme-dark"
elif theme_mode == "白天模式":
    st.markdown("""<style>
        .stApp { background-color: #ffffff !important; color: #111 !important; }
        [data-testid="stSidebar"] { background-color: #f0f2f6 !important; }
        h1, h2, h3, p, label, div { color: #111 !important; }
    </style>""", unsafe_allow_html=True)
    html_theme_class = "theme-light"
else:
    html_theme_class = "theme-auto"

st.sidebar.markdown("---")
st.sidebar.markdown("### 📂 我的课程库")

COURSES_DIR = "courses"
PROGRESS_FILE = "progress.json"
os.makedirs(COURSES_DIR, exist_ok=True)

if not os.path.exists(PROGRESS_FILE):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f)


def load_progress():
    with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_progress(data):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


files_ok = os.path.exists("type.wav") and os.path.exists("correct.wav")
if not files_ok:
    st.error("⚠️ 缺少音效文件！请确保项目目录下存在 `type.wav` 和 `correct.wav`。")
    st.stop()

# --- 动态生成并导出标准模板 ---
col_up, col_down = st.sidebar.columns(2)
template_df = pd.DataFrame({"English": ["Apple", "Hello world!"], "Chinese": ["苹果", "你好，世界！"]})
template_io = io.BytesIO()
with pd.ExcelWriter(template_io, engine='openpyxl') as writer:
    template_df.to_excel(writer, index=False, sheet_name='J-Dance模板')
template_data = template_io.getvalue()

st.sidebar.download_button(
    label="📄 导出标准模板",
    data=template_data,
    file_name="J-Dance_标准课程模板.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True
)

# --- 导入时隐藏后缀名 ---
uploaded_file = st.sidebar.file_uploader("📥 导入新课程", type=["xlsx", "xls"])
if uploaded_file:
    # 去除后缀，强制保存为标准的 .xlsx 以便统一管理
    clean_name = re.sub(r'\.xlsx?$|\.xls?$', '', uploaded_file.name)
    file_path = os.path.join(COURSES_DIR, clean_name + ".xlsx")
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.sidebar.success(f"《{clean_name}》导入成功！")

course_files = [f for f in os.listdir(COURSES_DIR) if f.endswith(".xlsx")]
if not course_files:
    st.info("💡 请在左侧导入你的 Excel 练习表。")
    st.stop()

# --- 构建映射字典，UI 层彻底隐藏后缀名 ---
course_dict = {f.replace(".xlsx", ""): f for f in course_files}

selected_course_name = st.sidebar.selectbox("📖 选择当前课程", list(course_dict.keys()))
selected_course = course_dict[selected_course_name] # 底层代码依然调用真实文件名

# 导出按钮
with open(os.path.join(COURSES_DIR, selected_course), "rb") as file:
    st.sidebar.download_button(
        label="📤 导出当前课程",
        data=file,
        file_name=selected_course,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

order_mode = st.sidebar.radio("练习顺序", ["按顺序练习", "随机练习"], key="order_mode")

try:
    df = pd.read_excel(os.path.join(COURSES_DIR, selected_course))
    if 'English' not in df.columns or 'Chinese' not in df.columns:
        st.error(f"⚠️ 导入异常：Excel 文件中必须包含 'English' 和 'Chinese' 列！")
        st.stop()
except Exception as e:
    st.error(f"⚠️ 文件读取失败: {e}")
    st.stop()

df = df.dropna(subset=['English', 'Chinese'])
df['English'] = df['English'].astype(str).str.strip()
df['Chinese'] = df['Chinese'].astype(str).str.strip()

# ==========================================
# 3. Session 状态绑定与多用户隔离
# ==========================================
progress_data = load_progress()

if progress_data and isinstance(list(progress_data.values())[0], dict) and "idx" in list(progress_data.values())[0]:
    progress_data = {}

if user_name not in progress_data:
    progress_data[user_name] = {}
user_data = progress_data[user_name]

if selected_course not in user_data:
    user_data[selected_course] = {"idx": 0, "error_book": [], "practice_order": list(range(len(df))), "combo": 0}
    save_progress(progress_data)

if 'current_user' not in st.session_state or st.session_state.current_user != user_name or 'current_course' not in st.session_state or st.session_state.current_course != selected_course:
    st.session_state.current_user = user_name
    st.session_state.current_course = selected_course
    st.session_state.course_state = user_data[selected_course].copy()
    st.session_state.tts_played = False
    st.session_state.start_time = time.time()
    st.session_state.has_started = False

course_state = st.session_state.course_state

if st.sidebar.button("🔄 重新开始本次练习"):
    course_state["idx"] = 0
    course_state["error_book"] = []
    course_state["combo"] = 0
    course_state["practice_order"] = list(range(len(df)))
    if order_mode == "随机练习":
        random.shuffle(course_state["practice_order"])
    user_data[selected_course] = course_state
    save_progress(progress_data)
    st.session_state.tts_played = False
    st.session_state.start_time = time.time()
    st.rerun()

st.sidebar.markdown("""
<style>
    .sidebar-brand-footer { position: fixed; bottom: 25px; width: 280px; text-align: center; font-size: 13px; color: #9ca3af; font-family: 'Poppins', sans-serif; letter-spacing: 0.5px; z-index: 100; pointer-events: none; }
</style>
<div class="sidebar-brand-footer">
    Crafted by <b style="color: #a855f7;">Justin_Wen</b><br>
    <span style="font-size: 11px; opacity: 0.7;">WeChat/QQ: 1101009</span>
</div>
""", unsafe_allow_html=True)

if not st.session_state.has_started:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # 使用无后缀的名字
        st.markdown(f"<h2 style='text-align:center;'>🎉 准备好挑战《{selected_course_name}》了吗？</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; color:gray;'>点击下方按钮激活系统引擎</p>", unsafe_allow_html=True)
        if st.button("🚀 点击开始练习", use_container_width=True):
            st.session_state.has_started = True
            st.rerun()
    st.stop()

# ==========================================
# 4. 课程完成报告页
# ==========================================
total_queue = len(course_state["practice_order"])
if course_state["idx"] >= total_queue:
    st.balloons()
    # 使用无后缀的名字
    st.header(f"📈 《{selected_course_name}》 学习报告")
    st.write(f"总计练习: **{total_queue}** 次 | 失误: **{len(course_state['error_book'])}** 次")
    if len(course_state["error_book"]) > 0:
        error_df = pd.DataFrame(course_state["error_book"]).drop_duplicates(subset=['English'])
        st.dataframe(error_df, use_container_width=True)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            error_df.to_excel(writer, index=False, sheet_name='错题本')
        st.download_button("📥 导出错题本", data=output.getvalue(), file_name=f"{selected_course_name}_错题本.xlsx")
    st.stop()

# ==========================================
# 5. 核心练习 UI 组件
# ==========================================
current_row_idx = course_state["practice_order"][course_state["idx"]]
row = df.iloc[current_row_idx]
eng = str(row['English'])
chi = str(row['Chinese'])

safe_chi = html.escape(chi)
safe_eng_json = json.dumps(eng)

tokens = re.findall(r"[a-zA-Z0-9']+|[^a-zA-Z0-9\s]", eng)
input_boxes_html = ""
target_words = []

for token in tokens:
    if re.match(r"^[a-zA-Z0-9']+$", token):
        idx = len(target_words)
        box_width = max(len(token), 1) + 1.2
        max_len = len(token) + 2
        input_boxes_html += f'<input type="text" class="word-box" id="word-{idx}" autocomplete="off" maxlength="{max_len}" style="width: {box_width}ch;">'
        target_words.append(token)
    else:
        input_boxes_html += f'<span class="punctuation">{html.escape(token)}</span>'

target_blocks_str = json.dumps(target_words)
progress_percent = (course_state["idx"] / total_queue) * 100
combo_html = f'<div class="combo-badge">🔥 Combo x{course_state["combo"]}</div>' if course_state["combo"] >= 2 else ''
progress_text = f"{course_state['idx'] + 1} / {total_queue}"
should_play_tts = "true" if not st.session_state.tts_played else "false"
elapsed_seconds = int(time.time() - st.session_state.start_time)

type_b64 = get_audio_base64("type.wav")
correct_b64 = get_audio_base64("correct.wav")

html_template = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600&display=swap');

    .theme-light {{
        --text-chinese: #777; --text-english: #111;
        --line-unfocused: #e5e5e5; --line-solidified: #f3f4f6; 
        --timer-color: #9ca3af; --track-bg: #f0f0f3; 
        --shadow-dark: #d1d1d4; --shadow-light: #ffffff;
    }}
    .theme-dark {{
        --text-chinese: #999; --text-english: #eee;
        --line-unfocused: #444; --line-solidified: #222; 
        --timer-color: #6b7280; --track-bg: #2b2b2b; 
        --shadow-dark: #1a1a1a; --shadow-light: #3c3c3c;
    }}

    @media (prefers-color-scheme: light) {{
        .theme-auto {{ --text-chinese: #777; --text-english: #111; --line-unfocused: #e5e5e5; --line-solidified: #f3f4f6; --timer-color: #9ca3af; --track-bg: #f0f0f3; --shadow-dark: #d1d1d4; --shadow-light: #ffffff; }}
    }}
    @media (prefers-color-scheme: dark) {{
        .theme-auto {{ --text-chinese: #999; --text-english: #eee; --line-unfocused: #444; --line-solidified: #222; --timer-color: #6b7280; --track-bg: #2b2b2b; --shadow-dark: #1a1a1a; --shadow-light: #3c3c3c; }}
    }}

    .custom-container {{
        --line-focused: #a855f7; --color-error: #ef4444;
        font-family: 'Poppins', 'Microsoft YaHei', sans-serif; text-align: center; max-width: 800px; margin: 0 auto; margin-top: 15vh; position: relative;
    }}

    @keyframes shake {{ 0%, 100% {{ transform: translateX(0); }} 25% {{ transform: translateX(-5px); }} 50% {{ transform: translateX(5px); }} 75% {{ transform: translateX(-5px); }} }}
    @keyframes soundwave {{ 0% {{ transform: scale(1); opacity: 0.5; }} 50% {{ transform: scale(1.2); opacity: 1; }} 100% {{ transform: scale(1); opacity: 0.5; }} }}
    .shake-err {{ animation: shake 0.35s ease-in-out; }}

    .floating-progress-wrapper {{ display: flex; justify-content: center; margin-bottom: 35px; }}
    .floating-progress-track {{ width: 240px; height: 14px; background: var(--track-bg); border-radius: 20px; box-shadow: 6px 6px 12px var(--shadow-dark), -6px -6px 12px var(--shadow-light); padding: 3px; display: flex; align-items: center; justify-content: flex-start; }}
    .floating-progress-fill {{ height: 100%; width: {progress_percent}%; background: linear-gradient(90deg, #a855f7, #ec4899); border-radius: 15px; box-shadow: 0 2px 6px rgba(168, 85, 247, 0.4); transition: width 0.4s ease; }}

    .status-header {{ display: flex; justify-content: space-between; align-items: center; padding: 0 10px 20px 10px; }}
    .status-left {{ display: flex; align-items: center; gap: 15px; }}
    .progress-text {{ font-size: 15px; font-weight: 600; color: var(--text-chinese); font-family: 'Poppins', sans-serif; }}
    .timer-container {{ display: flex; align-items: center; gap: 5px; color: var(--timer-color); font-family: 'Poppins', sans-serif; font-size: 16px; font-weight: 500; }}
    .combo-badge {{ font-size: 16px; font-weight: 800; color: #f97316; font-family: 'Poppins', sans-serif; }}

    .chinese-prompt {{ font-size: 32px; color: var(--text-chinese); margin-bottom: 40px; display: flex; justify-content: center; align-items: center; gap: 10px; font-weight: 500; font-family: 'Microsoft YaHei', sans-serif; }}
    .speaker-icon {{ font-size: 24px; opacity: 0.4; transition: opacity 0.3s, color 0.3s; cursor: pointer; }}
    .speaker-icon.playing {{ animation: soundwave 0.6s infinite; opacity: 1; color: var(--line-focused); }}

    .word-row {{ display: flex; flex-wrap: wrap; justify-content: center; align-items: baseline; gap: 12px; line-height: 2; }}
    .word-box {{ padding: 0 2px; font-size: 38px; font-family: 'Poppins', sans-serif; font-weight: 500; color: var(--text-english); background-color: transparent; border: none; border-bottom: 3px solid var(--line-unfocused); outline: none; text-align: center; transition: all 0.2s; caret-color: var(--line-focused); letter-spacing: 1px; }}
    .word-box:focus {{ border-bottom-color: var(--line-focused); }}
    .word-box.has-text:not(:focus) {{ border-bottom-color: var(--line-solidified); }}

    .punctuation {{ font-size: 38px; color: var(--text-english); margin-left: -8px; font-family: 'Poppins', sans-serif; font-weight: 500; }}
    .hint-text {{ font-size: 13px; color: var(--text-chinese); margin-top: 50px; opacity: 0.6; }}
    .success-glow {{ border-bottom-color: transparent !important; color: var(--line-focused) !important; text-shadow: 0 0 12px rgba(168, 85, 247, 0.4); }}
</style>

<div class="{html_theme_class} custom-container">
    <div class="floating-progress-wrapper">
        <div class="floating-progress-track">
            <div class="floating-progress-fill"></div>
        </div>
    </div>

    <div class="status-header">
        <div class="status-left">
            <div class="progress-text">🎯 {progress_text}</div>
            <div class="timer-container">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                <span id="live-timer">00:00:00</span>
            </div>
        </div>
        {combo_html}
    </div>

    <div class="chinese-prompt">
        {safe_chi} <span id="speaker" class="speaker-icon">🔊</span>
    </div>
    <div class="word-row" id="sentence-container">{input_boxes_html}</div>
    <div class="hint-text">💡 空格跳词 | 回车验证 | 长按 Alt 偷看答案</div>
</div>

<script>
    // --- 【全新模块】全局注入定制化左上角汉堡开关 ---
    if (!window.parent.document.getElementById('j-dance-menu-btn')) {{
        const menuBtn = window.parent.document.createElement('div');
        menuBtn.id = 'j-dance-menu-btn';
        menuBtn.innerHTML = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>';
        menuBtn.style.cssText = 'position: fixed; top: 20px; left: 20px; z-index: 999999; width: 44px; height: 44px; background: linear-gradient(135deg, #a855f7, #ec4899); color: white; border-radius: 12px; display: flex; justify-content: center; align-items: center; cursor: pointer; box-shadow: 0 4px 12px rgba(168, 85, 247, 0.4); transition: transform 0.2s;';

        menuBtn.onmouseenter = () => menuBtn.style.transform = 'scale(1.05)';
        menuBtn.onmouseleave = () => menuBtn.style.transform = 'scale(1)';

        menuBtn.onclick = () => {{
            const openBtn = window.parent.document.querySelector('[data-testid="collapsedControl"]');
            // 判断侧边栏是否处于关闭状态 (原生展开按钮可见即为关闭)
            const isClosed = openBtn && window.parent.getComputedStyle(openBtn).display !== 'none';

            if (isClosed) {{
                openBtn.click();
            }} else {{
                // 寻找侧边栏内部的原生关闭按钮
                const closeBtns = window.parent.document.querySelectorAll('[data-testid="stSidebar"] button');
                if (closeBtns.length > 0) closeBtns[0].click();
            }}
        }};
        window.parent.document.body.appendChild(menuBtn);
    }}

    // --- 核心逻辑 ---
    const typeSound = new Audio("data:audio/wav;base64,{type_b64}");
    const correctSound = new Audio("data:audio/wav;base64,{correct_b64}");
    const targetBlocks = {target_blocks_str};
    const numBlocks = targetBlocks.length;
    let sentenceMistake = false; 
    let userInputs = new Array(numBlocks).fill(""); 

    let totalSeconds = {elapsed_seconds};
    const timerEl = document.getElementById('live-timer');
    function formatTime(sec) {{
        const h = Math.floor(sec / 3600).toString().padStart(2, '0');
        const m = Math.floor((sec % 3600) / 60).toString().padStart(2, '0');
        const s = (sec % 60).toString().padStart(2, '0');
        return h === '00' ? `${{m}}:${{s}}` : `${{h}}:${{m}}:${{s}}`;
    }}
    timerEl.innerText = formatTime(totalSeconds);
    setInterval(() => {{ totalSeconds++; timerEl.innerText = formatTime(totalSeconds); }}, 1000);

    // --- TTS 引擎修复：防卡死、防浏览器垃圾回收误杀 ---
    function playTTS() {{
        window.speechSynthesis.cancel(); // 每次发音前清空历史队列
        
        // 将 utterance 挂载到 window 阻止垃圾回收器清理
        window.currentSpeech = new SpeechSynthesisUtterance({safe_eng_json});
        window.currentSpeech.lang = 'en-US'; 
        window.currentSpeech.rate = 1.0;
        
        const speakerIcon = document.getElementById('speaker');
        window.currentSpeech.onstart = () => speakerIcon.classList.add('playing');
        window.currentSpeech.onend = () => speakerIcon.classList.remove('playing');
        window.currentSpeech.onerror = (e) => console.log("TTS Error: ", e);
        
        window.speechSynthesis.speak(window.currentSpeech);
    }}

    if ({should_play_tts}) {{ setTimeout(playTTS, 300); }}
    document.getElementById('speaker').addEventListener('click', playTTS);

    // 真正的物理级隐形两个核心通信按钮，绝不报错
    const parentBtns = Array.from(window.parent.document.querySelectorAll('button'));
    const btnC = parentBtns.find(b => b.innerText.includes('H_C'));
    const btnE = parentBtns.find(b => b.innerText.includes('H_E'));

    if (btnC) {{ let container = btnC.closest('[data-testid="stElementContainer"]'); if(container) container.style.display = 'none'; }}
    if (btnE) {{ let container = btnE.closest('[data-testid="stElementContainer"]'); if(container) container.style.display = 'none'; }}

    for (let i = 0; i < numBlocks; i++) {{
        const box = document.getElementById(`word-${{i}}`);
        if(i === 0) setTimeout(() => box.focus(), 100);

        box.addEventListener('input', (e) => {{
            if (box.value.length > 0) box.classList.add('has-text');
            else box.classList.remove('has-text');
        }});

        box.addEventListener('keydown', (e) => {{
            if (e.key === 'Alt') {{
                e.preventDefault();
                if (e.repeat) return; 
                for (let j = 0; j < numBlocks; j++) {{
                    let b = document.getElementById(`word-${{j}}`);
                    userInputs[j] = b.value; 
                    b.value = targetBlocks[j];
                    b.style.color = 'var(--text-chinese)'; 
                }}
                sentenceMistake = true; 
                return;
            }}

            if (e.code === 'Space') {{
                e.preventDefault(); 
                if (i + 1 < numBlocks) document.getElementById(`word-${{i+1}}`).focus();
                return;
            }}

            if (e.key === 'Enter') {{
                e.preventDefault();
                let allCorrect = true;

                for (let j = 0; j < numBlocks; j++) {{
                    const checkBox = document.getElementById(`word-${{j}}`);
                    const typed = checkBox.value.toLowerCase().trim();
                    if (typed !== targetBlocks[j].toLowerCase()) {{
                        allCorrect = false;
                        checkBox.style.borderBottomColor = 'var(--color-error)';
                        checkBox.classList.remove('shake-err'); 
                        void checkBox.offsetWidth; 
                        checkBox.classList.add('shake-err');

                        setTimeout(() => {{
                           checkBox.classList.remove('shake-err');
                           if(document.activeElement === checkBox) checkBox.style.borderBottomColor = 'var(--line-focused)';
                           else checkBox.style.borderBottomColor = 'var(--line-unfocused)';
                        }}, 400);
                    }} 
                }}

                if (allCorrect) {{
                    if(correctSound.src) correctSound.play().catch(e=>console.log(e));
                    for (let j = 0; j < numBlocks; j++) {{
                        const b = document.getElementById(`word-${{j}}`);
                        b.disabled = true;
                        b.classList.add('success-glow');
                    }}
                    setTimeout(() => {{
                        if (sentenceMistake && btnE) btnE.click();
                        else if (!sentenceMistake && btnC) btnC.click();
                    }}, 600); // 👈 极速 600 毫秒跳题
                }} else {{
                    sentenceMistake = true;
                }}
                return;
            }}

            if (e.key === 'Backspace' && box.value.length === 0 && i > 0) {{
                document.getElementById(`word-${{i-1}}`).focus();
            }} else if (e.key !== 'Shift' && e.key !== 'Control' && e.key !== 'Meta' && e.key !== 'Alt') {{
                if(typeSound.src) {{
                    typeSound.currentTime = 0; 
                    typeSound.play().catch(e=>console.log(e));
                }}
            }}
        }});

        box.addEventListener('keyup', (e) => {{
            if (e.key === 'Alt') {{
                for (let j = 0; j < numBlocks; j++) {{
                    let b = document.getElementById(`word-${{j}}`);
                    b.value = userInputs[j]; 
                    b.style.color = 'var(--text-english)'; 
                }}
            }}
        }});
    }}
</script>
"""

components.html(html_template, height=600, scrolling=False)

# ==========================================
# 6. Python 隐藏通信接收器
# ==========================================
col1, col2 = st.columns(2)
with col1:
    btn_c = st.button("H_C", key="btn_c")
with col2:
    btn_e = st.button("H_E", key="btn_e")

if btn_c:
    course_state["combo"] += 1
    course_state["idx"] += 1
    user_data[selected_course] = course_state
    save_progress(progress_data)
    st.session_state.tts_played = False
    st.rerun()

if btn_e:
    course_state["combo"] = 0
    course_state["error_book"].append({"English": eng, "Chinese": chi})
    course_state["idx"] += 1
    user_data[selected_course] = course_state
    save_progress(progress_data)
    st.session_state.tts_played = False
    st.rerun()

if not st.session_state.tts_played:
    st.session_state.tts_played = True
