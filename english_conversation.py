import os
import io
import wave
import asyncio
import tempfile
import numpy as np
import av
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from streamlit_webrtc import webrtc_streamer, WebRtcMode, AudioProcessorBase
import edge_tts

from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder



st.write("🔍 DEBUG: secretsキー一覧 →", list(st.secrets.keys()))
st.write("🔍 OPENAIキー(secrets):", st.secrets.get("OPENAI_API_KEY", "None"))
st.write("🔍 OPENAIキー(env):", os.getenv("OPENAI_API_KEY", "None"))




# --- ✅ Pydanticエラー回避 ---
ChatOpenAI.model_rebuild()

# --- 環境変数読み込み ---
load_dotenv()

# ✅ Secrets と .env の両対応
OPENAI_API_KEY = None
if "OPENAI_API_KEY" in st.secrets:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
elif os.getenv("OPENAI_API_KEY"):
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    st.error("❌ OPENAI_API_KEY が設定されていません。Streamlit Cloud の Secrets または .env を確認してください。")
    st.stop()

# --- OpenAI 初期化 ---
client = OpenAI(api_key=OPENAI_API_KEY)

# --- LangChain Memory 初期化 ---
if "conversation_memory" not in st.session_state:
    st.session_state.conversation_memory = ConversationBufferMemory(return_messages=True)

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.6, api_key=OPENAI_API_KEY)



# --- AI応答生成 ---
def get_ai_reply(user_text: str) -> str:
    memory = st.session_state.conversation_memory

    system_prompt = """
あなたは優しい英会話講師です。
出力フォーマット：
1行目：英語で自然な返答（CEFR B1-B2レベル、会話を続ける質問も含む）
2行目以降：「日本語訳：」で始めて翻訳
最後に「学習ポイント：」で1〜3個簡潔に説明
"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder("history"),
        ("human", "{input}"),
    ])

    chain = prompt | llm
    response = chain.invoke({
        "input": user_text,
        "history": memory.load_memory_variables({}).get("history", []),
    })

    reply = response.content
    memory.chat_memory.add_user_message(user_text)
    memory.chat_memory.add_ai_message(reply)
    return reply


# --- Whisper文字起こし ---
def transcribe_audio(wav_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(wav_bytes)
        tmp.flush()
        tmp_path = tmp.name

    with open(tmp_path, "rb") as f:
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="en",
        )
    return result.text.strip()


# --- Edge-TTS 音声合成 ---
async def _edge_tts_to_file(text: str, voice: str, out_path: str):
    tts = edge_tts.Communicate(text, voice=voice)
    await tts.save(out_path)

def synthesize_speech(text: str, voice="en-US-JennyNeural") -> str:
    if not text.strip():
        return ""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        out_path = tmp.name
    asyncio.run(_edge_tts_to_file(text, voice, out_path))
    return out_path


# --- WebRTC 録音処理 ---
class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.frames = []

    def recv_audio(self, frame: av.AudioFrame) -> av.AudioFrame:
        self.frames.append(frame)
        return frame


def frames_to_wav_bytes(frames) -> bytes:
    if not frames:
        raise ValueError("音声フレームが空です。")

    sample_rate = frames[0].sample_rate or 48000
    pcm_list = []
    for f in frames:
        a = f.to_ndarray()
        if a.ndim == 2:
            a = a[0]
        pcm_list.append(a)
    pcm = np.concatenate(pcm_list).astype(np.int16)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()


def extract_english_part(reply: str) -> str:
    if "日本語訳" in reply:
        return reply.split("日本語訳")[0].strip()
    return reply.split("\n")[0].strip()


# --- メインUI ---
def show_english_conversation():
    st.title("🎧 英会話トレーナー（スマホ対応・WebRTC版）")
    st.caption("🎙️ Start → Stop → この録音でAIに送信")

    col1, col2 = st.columns(2)
    with col1:
        voice = st.selectbox(
            "AI音声タイプ",
            ["en-US-JennyNeural", "en-US-GuyNeural", "en-GB-RyanNeural"],
            index=0,
        )
    with col2:
        st.caption("WebRTC録音 → Whisper認識 → ChatGPT応答 → Edge-TTS再生")

    st.markdown("---")

    ctx = webrtc_streamer(
        key="mobile-english-conversation",
        mode=WebRtcMode.SENDONLY,
        audio_receiver_size=1024,
        media_stream_constraints={"audio": True, "video": False},
        async_processing=True,
        audio_processor_factory=AudioProcessor,
    )

    if not ctx.state.playing:
        st.info("🎙️ Startボタンで録音開始 → Stopボタンで終了してください。")
    else:
        st.success("🔴 録音中です。Stopを押して終了。")

    if ctx.audio_processor and st.button("🎯 この録音でAIに送信"):
        frames = ctx.audio_processor.frames
        ctx.audio_processor.frames = []

        if not frames:
            st.warning("⚠️ 音声が取得できませんでした。録音が短すぎた可能性があります。")
            return

        try:
            wav_bytes = frames_to_wav_bytes(frames)
        except Exception as e:
            st.error(f"音声処理エラー: {e}")
            return

        st.audio(wav_bytes, format="audio/wav")

        with st.spinner("🎧 Whisperで音声を解析中..."):
            try:
                user_text = transcribe_audio(wav_bytes)
            except Exception as e:
                st.error(f"音声認識失敗: {e}")
                return

        if not user_text:
            st.warning("⚠️ 音声が認識できませんでした。もう一度話してください。")
            return

        st.markdown(f"**🗣 あなた:** {user_text}")

        with st.spinner("🤖 ChatGPTが応答中..."):
            reply = get_ai_reply(user_text)
        st.markdown("**🤖 AIの返答:**")
        st.markdown(reply)

        english_part = extract_english_part(reply)
        if english_part:
            with st.spinner("🔊 音声生成中..."):
                audio_path = synthesize_speech(english_part, voice=voice)
                if audio_path:
                    st.audio(audio_path, format="audio/mp3")

    st.markdown("---")
    st.subheader("💬 会話履歴（今回のセッション）")
    history = st.session_state.conversation_memory.load_memory_variables({}).get("history", [])
    if history:
        for m in history:
            role = "👤 You" if m.type == "human" else "🤖 AI"
            st.markdown(f"**{role}:** {m.content}")
    else:
        st.caption("まだ会話履歴がありません。Start → Stop → 送信で会話を始めてみましょう。")
