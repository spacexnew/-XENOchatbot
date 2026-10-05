import hashlib
import io

import streamlit as st
import groq
from groq import Groq
from gtts import gTTS

# ---------- Page setup ----------
st.set_page_config(page_title="Xeno Voice Bot", page_icon="🎙️")
st.title("🎙️ Xeno - Voice Assistant")
st.caption("Click the mic, speak, then click stop. Xeno will answer out loud.")

# Models are tried in order; if one is retired, the next is used automatically
CHAT_MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]
STT_MODELS = ["whisper-large-v3", "whisper-large-v3-turbo"]
TTS_LANG = "en"  # change to "ur" for Urdu, "de" for German, etc.
SYSTEM_PROMPT = (
    "You are Xeno, a voice assistant. Never introduce yourself, never say your name, "
    "and never start with a greeting unless the user greets you or asks who you are. "
    "Answer the question directly in 1-3 short sentences. Your replies are read aloud, "
    "so do not use markdown, bullet points, or emojis. "
    "If the user asks you to write a message, email, or text, reply with only the "
    "message itself, ready to send, with no extra commentary."
)

# ---------- Groq client ----------
if "GROQ_API_KEY" not in st.secrets:
    st.error("Missing GROQ_API_KEY. Add it in App settings -> Secrets.")
    st.stop()

client = Groq(api_key=st.secrets["GROQ_API_KEY"])



def call_with_fallback(models, fn):
    """Run fn(model) for each model until one works."""
    last_error = None
    for model in models:
        try:
            return fn(model)
        except groq.APIStatusError as e:
            if e.status_code in (400, 404):  # model missing/retired -> try next
                last_error = e
                continue
            raise
    raise last_error


# ---------- Session state ----------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_audio_id" not in st.session_state:
    st.session_state.last_audio_id = None
if "reply_audio" not in st.session_state:
    st.session_state.reply_audio = None

with st.sidebar:
    st.header("Xeno")
    if st.button("Clear conversation"):
        st.session_state.messages = []
        st.session_state.reply_audio = None
        st.session_state.last_audio_id = None
        st.rerun()

# ---------- Voice input ----------
audio = st.audio_input("🎤 Speak to Xeno")

if audio is not None:
    audio_bytes = audio.getvalue()
    audio_id = hashlib.md5(audio_bytes).hexdigest()

    # Only process each recording once
    if audio_id != st.session_state.last_audio_id:
        st.session_state.last_audio_id = audio_id
        try:
            # 1) Speech -> text
            with st.spinner("Listening..."):
                transcript = call_with_fallback(
                    STT_MODELS,
                    lambda m: client.audio.transcriptions.create(
                        file=("speech.wav", audio_bytes), model=m
                    ),
                )
            user_text = transcript.text.strip()

            if user_text:
                st.session_state.messages.append({"role": "user", "content": user_text})

                # 2) Text -> AI reply
                api_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ]
                with st.spinner("Thinking..."):
                    response = call_with_fallback(
                        CHAT_MODELS,
                        lambda m: client.chat.completions.create(
                            model=m, messages=api_messages
                        ),
                    )
                reply = response.choices[0].message.content
                st.session_state.messages.append({"role": "assistant", "content": reply})

                # 3) Reply text -> speech
                with st.spinner("Speaking..."):
                    mp3 = io.BytesIO()
                    gTTS(text=reply, lang=TTS_LANG).write_to_fp(mp3)
                    st.session_state.reply_audio = mp3.getvalue()
            else:
                st.warning("I couldn't hear anything. Please try again.")

        except groq.APIStatusError as e:
            st.error(f"Groq error {e.status_code}: {e.response.text}")
        except Exception as e:
            st.error(f"Something went wrong: {e}")

# ---------- Play the latest reply ----------
if st.session_state.reply_audio:
    st.audio(st.session_state.reply_audio, format="audio/mp3", autoplay=True)

# ---------- Transcript ----------
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
