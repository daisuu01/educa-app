# =============================================
# english_corrector.py（Secrets対応・ローカル両対応版）
# =============================================

import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os, random, base64
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# --- OpenAI 初期化 ---
load_dotenv()

# ① Streamlit Secrets → ② .env の順で探索
api_key = None
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
elif os.getenv("OPENAI_API_KEY"):
    api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    st.error("❌ OPENAI_API_KEY が設定されていません。Streamlit Secrets または .env を確認してください。")
    st.stop()

client = OpenAI(api_key=api_key)

# --- Firebase 初期化 ---
if not firebase_admin._apps:
    firebase_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
    if not firebase_path or not os.path.exists(firebase_path):
        st.error("❌ Firebase認証ファイルが見つかりません。")
        st.stop()
    cred = credentials.Certificate(firebase_path)
    firebase_admin.initialize_app(cred)
db = firestore.client()


# ==================================================
# 🔹 ChatGPT 出題生成
# ==================================================
def generate_question(level: int, recent_questions: list[str], mode_type: str) -> str:
    try:
        seed = random.randint(1, 10000)
        if mode_type == "和文英訳":
            prompt = f"""
            あなたは英作文問題の作成者です。
            難易度レベル{level}の「和文英訳問題」を1問作ってください。
            レベル1は中学英語基礎、レベル10は東大二次試験レベルです。
            以下の出題（直近50問）とは絶対に重複しないようにしてください。
            除外リスト: {recent_questions}
            出力は日本文のみ1つだけ表示してください。
            （乱数シード: {seed}）
            """
        else:
            prompt = f"""
            あなたは英作文のテーマ作成者です。
            難易度レベル{level}の「自由英作文テーマ」を1問作ってください。
            レベル1は簡単な日常会話、レベル10は抽象的・社会的テーマにしてください。
            以下のテーマ（直近50件）とは重複しないようにしてください。
            除外リスト: {recent_questions}
            出力は「英作文テーマを日本語で1行のみ」。
            （乱数シード: {seed}）
            """
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=1.0
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"❌ 出題エラー: {e}"


# ==================================================
# 🔹 添削プロンプト
# ==================================================
PROMPT_FREE = """あなたは英語の専門講師です。
次の英文を添削し、以下の3点を日本語で出力してください：
① 文法・語彙の誤りの指摘
② より自然な英文への改善提案
③ 模範解答例（自然で正確な英語）
英文：
{sentence}
"""

PROMPT_EXAM = """あなたは英語の専門講師です。
以下の日本文を英語に翻訳する問題を出題し、
その後、ユーザーが入力した英文を添削します。

【出題】：
{japanese_prompt}

ユーザーの英文：
{user_essay}

出力は次の形式で：
① 文法・語彙の誤りの指摘
② 改善された英文
③ 模範解答例
"""

PROMPT_THEME = """あなたは英語の専門講師です。
以下のテーマに対する自由英作文を添削してください。

【テーマ】：
{theme_prompt}

ユーザーの英文：
{user_essay}

出力は次の形式で：
① 文法・語彙の誤りの指摘
② 改善された英文
③ 模範解答例
"""


# ==================================================
# 🔹 ChatGPT 呼び出し
# ==================================================
def correct_essay(prompt_text: str) -> str:
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは日本人高校生の英作文を添削する英語講師です。"},
                {"role": "user", "content": prompt_text}
            ],
            temperature=0.5
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"❌ 添削エラー: {e}"


# ==================================================
# 🔹 Firestore 履歴管理
# ==================================================
def get_recent_questions(user_id: str, level: int, mode_type: str, limit: int = 50) -> list[str]:
    try:
        docs = (
            db.collection("users")
            .document(user_id)
            .collection("essay_history")
            .where("level", "==", level)
            .where("mode", "==", mode_type)
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        return [d.to_dict().get("question", "") for d in docs]
    except Exception:
        return []


def save_history(user_id: str, data: dict):
    db.collection("users").document(user_id).collection("essay_history").add(data)


# ==================================================
# 🔹 ChatGPT Vision OCR
# ==================================================
def extract_text_from_image_bytes(image_bytes_b64: str) -> str:
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "この画像に書かれている英語の文を正確に読み取り、テキストとして出力してください。"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_bytes_b64}"}}
                    ]
                }
            ],
            temperature=0
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"❌ 画像読取エラー: {e}"


# ==================================================
# 🖥️ Streamlit アプリ UI
# ==================================================
def show_essay_corrector(user_id: str):
    st.title("英作文添削")

    mode = st.radio(
        "モードを選択",
        ["出題モード（和文英訳／自由英作）", "自由添削モード"],
        horizontal=True
    )

    # ✅ 外部camera.htmlリンクは削除（内部カメラのみ使用）

    # -------------------------------------------------
    # 🎯 出題モード
    # -------------------------------------------------
    if mode == "出題モード（和文英訳／自由英作）":
        st.subheader("🎯 出題モード")

        mode_type = st.radio("出題タイプを選択", ["和文英訳", "自由英作"], horizontal=True)
        level = st.slider("レベル（1＝中学基礎 ～ 10＝東大レベル）", 1, 10, 3)
        st.caption(f"現在のレベル：{level}（{mode_type}）")

        if "question" not in st.session_state:
            st.session_state["question"] = ""

        if st.button("🎲 出題"):
            with st.spinner("Firestoreから履歴を確認中..."):
                recent_questions = get_recent_questions(user_id, level, mode_type)
            with st.spinner("新しい問題を生成中..."):
                question = generate_question(level, recent_questions, mode_type)
                st.session_state["question"] = question
                save_history(user_id, {
                    "level": level,
                    "mode": mode_type,
                    "question": question,
                    "timestamp": datetime.now()
                })

        # --- 出題表示 ---
        if st.session_state["question"]:
            st.markdown(f"""
                <div style="background-color:#f8f9fa;padding:15px 20px;margin:15px 0;
                    border-radius:8px;font-size:1.05em;color:#222;">
                <b>【お題（{mode_type}・レベル{level}）】</b><br>
                {st.session_state["question"]}
                </div>
            """, unsafe_allow_html=True)

        # --- 入力 or カメラ ---
        st.markdown("#### あなたの英作文を入力または撮影してください：")
        tab1, tab2 = st.tabs(["✏️ 入力", "📷 カメラ撮影"])

        with tab1:
            user_input = st.text_area("✏️ 英文入力", height=150)

        with tab2:
            st.info("📸 下のボタンを押してカメラを起動し、紙の答案を撮影してください。")

            # ✅ 初回アクセス時ポップアップ
            st.markdown(
                """
                <script>
                if (!localStorage.getItem("camera_permission_popup_shown")) {
                    alert("📸 カメラの使用を許可してください。\\n\\nカメラが起動しない場合は、Safari/Chrome の「🔒」マークから『カメラを許可』を選択してください。");
                    localStorage.setItem("camera_permission_popup_shown", "true");
                }
                </script>
                """,
                unsafe_allow_html=True
            )

            img_file = st.camera_input("⬇️ 撮影する（端末には保存されません）")
            extracted_text = None
            if img_file:
                st.info("📸 画像解析中...")
                base64_img = base64.b64encode(img_file.getvalue()).decode("utf-8")
                with st.spinner("文字を読み取っています..."):
                    extracted_text = extract_text_from_image_bytes(base64_img)
                st.success("✅ 読み取り完了！")
                st.text_area("読み取った英文", extracted_text, height=150)

        # --- 添削 ---
        if st.button("✏️ 添削する"):
            essay_text = extracted_text or user_input.strip()
            if not essay_text:
                st.warning("⚠ 英文を入力または撮影してください。")
            elif not st.session_state["question"]:
                st.warning("⚠ まず『出題』ボタンを押してください。")
            else:
                with st.spinner("添削中..."):
                    prompt = (PROMPT_EXAM if mode_type == "和文英訳" else PROMPT_THEME).format(
                        japanese_prompt=st.session_state["question"],
                        theme_prompt=st.session_state["question"],
                        user_essay=essay_text
                    )
                    result = correct_essay(prompt)
                    st.markdown("### 📘 添削結果")
                    st.write(result)
                    save_history(user_id, {
                        "mode": mode_type,
                        "level": level,
                        "question": st.session_state["question"],
                        "user_input": essay_text,
                        "correction": result,
                        "timestamp": datetime.now()
                    })

    # -------------------------------------------------
    # ✏️ 自由添削モード
    # -------------------------------------------------
    else:
        st.subheader("✏️ 自由英作文添削")
        st.markdown("#### あなたの英文を入力または撮影してください：")
        tab1, tab2 = st.tabs(["✏️ 入力", "📷 カメラ撮影"])

        with tab1:
            user_input = st.text_area("英文入力", height=150)

        with tab2:
            st.info("📸 下のボタンを押してカメラを起動し、答案を撮影してください。")

            # ✅ 初回アクセス時ポップアップ
            st.markdown(
                """
                <script>
                if (!localStorage.getItem("camera_permission_popup_shown")) {
                    alert("📸 カメラの使用を許可してください。\\n\\nカメラが起動しない場合は、Safari/Chrome の「🔒」マークから『カメラを許可』を選択してください。");
                    localStorage.setItem("camera_permission_popup_shown", "true");
                }
                </script>
                """,
                unsafe_allow_html=True
            )

            img_file = st.camera_input("⬇️ 撮影する（端末には保存されません）")
            extracted_text = None
            if img_file:
                base64_img = base64.b64encode(img_file.getvalue()).decode("utf-8")
                with st.spinner("画像から英文を抽出中..."):
                    extracted_text = extract_text_from_image_bytes(base64_img)
                st.text_area("読み取った英文", extracted_text, height=150)

        if st.button("✏️ 添削する"):
            essay_text = extracted_text or user_input.strip()
            if not essay_text:
                st.warning("⚠ 英文を入力または撮影してください。")
            else:
                with st.spinner("添削中..."):
                    prompt = PROMPT_FREE.format(sentence=essay_text)
                    result = correct_essay(prompt)
                    st.markdown("### 📘 添削結果")
                    st.write(result)
                    save_history(user_id, {
                        "mode": "自由添削",
                        "user_input": essay_text,
                        "correction": result,
                        "timestamp": datetime.now()
                    })
