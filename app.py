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

CHAT_MODEL = "llama-3.3-70b-versatile"
STT_MODEL = "whisper-large-v3-turbo"
TTS_LANG = "en"  # change to "ur" for Urdu, "de" for German, etc.
SYSTEM_PROMPT = (
    "You are Xeno, a friendly voice assistant. Your replies are read aloud, "
    "so keep them short (1-3 sentences), natural, and do not use markdown, "
    "bullet points, or emojis."
)

# ---------- Groq client ----------
if "GROQ_API_KEY" not in st.secrets:
    st.error("Missing GROQ_API_KEY. Add it in App settings -> Secrets.")
    st.stop()

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

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
                transcript = client.audio.transcriptions.create(
                    file=("speech.wav", audio_bytes),
                    model=STT_MODEL,
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
                    response = client.chat.completions.create(
                        model=CHAT_MODEL,
                        messages=api_messages,
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
