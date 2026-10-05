import hashlib
import io

import streamlit as st
import groq
from groq import Groq
from gtts import gTTS

# ---------- Page setup ----------
st.set_page_config(page_title="Xeno Voice Bot", page_icon="🎙️")
st.title("🎙️ Xeno - Voice Assistant")

# Models are tried in order; if one is retired, the next is used automatically
CHAT_MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]
STT_MODELS = ["whisper-large-v3", "whisper-large-v3-turbo"]
TTS_LANG = "en"  # change to "ur" for Urdu, "de" for German, etc.

ASSISTANT_PROMPT = (
    "You are Xeno, a voice assistant. Never introduce yourself, never say your name, "
    "and never start with a greeting unless the user greets you or asks who you are. "
    "Answer the question directly in 1-3 short sentences. Your replies are read aloud, "
    "so do not use markdown, bullet points, or emojis."
)


def writer_prompt(kind, tone):
    return (
        f"You are a professional writing assistant. Write a {kind} in a {tone} tone "
        "based on the user's spoken request. Output ONLY the finished text, ready to send, "
        "with no introduction, explanation or commentary. "
        "If it is an email, start with 'Subject: ...' on the first line, then a blank line, "
        "then the body, and end with a sign-off followed by [Your name]. "
        "Do not invent facts, dates, prices, links or names the user did not give; "
        "use [square brackets] for missing details. "
        "If the user asks to change the previous draft (shorter, more polite, add something), "
        "output the full revised version. "
        "Write in the language the user spoke unless they ask for another."
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


def show_code(text):
    """Show text in a box with a built-in copy button."""
    try:
        st.code(text, language=None, wrap_lines=True)
    except TypeError:
        st.code(text, language=None)


# ---------- Session state ----------
if "histories" not in st.session_state:
    st.session_state.histories = {"Assistant": [], "Writer": []}
if "last_audio_id" not in st.session_state:
    st.session_state.last_audio_id = None
if "reply_audio" not in st.session_state:
    st.session_state.reply_audio = None

# ---------- Sidebar ----------
with st.sidebar:
    st.header("Xeno")
    mode = st.radio("Mode", ["Assistant", "Writer"], help="Writer drafts messages and emails you can copy.")
    kind, tone = None, None
    if mode == "Writer":
        kind = st.selectbox("Write a", ["WhatsApp/SMS message", "Email", "LinkedIn message", "Social media caption"])
        tone = st.selectbox("Tone", ["professional", "friendly", "short and direct", "polite but firm"])
    if st.button("Clear this conversation"):
        st.session_state.histories[mode] = []
        st.session_state.reply_audio = None
        st.session_state.last_audio_id = None
        st.rerun()

history = st.session_state.histories[mode]

if mode == "Writer":
    st.caption(f"Say what you want to write, e.g. \"tell my client the report will be ready on Friday\". "
               "Then say \"make it shorter\" or \"more polite\" to edit.")
    system_prompt = writer_prompt(kind, tone)
else:
    st.caption("Click the mic, speak, then click stop. Xeno will answer out loud.")
    system_prompt = ASSISTANT_PROMPT

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
                history.append({"role": "user", "content": user_text})

                # 2) Text -> AI reply
                api_messages = [{"role": "system", "content": system_prompt}] + [
                    {"role": m["role"], "content": m["content"]} for m in history
                ]
                with st.spinner("Thinking..."):
                    response = call_with_fallback(
                        CHAT_MODELS,
                        lambda m: client.chat.completions.create(
                            model=m, messages=api_messages
                        ),
                    )
                reply = response.choices[0].message.content.strip()
                history.append({"role": "assistant", "content": reply})

                # 3) Speech: read the answer (Assistant) or just confirm (Writer)
                spoken = reply if mode == "Assistant" else "Your draft is ready. Check the screen."
                with st.spinner("Speaking..."):
                    mp3 = io.BytesIO()
                    gTTS(text=spoken, lang=TTS_LANG).write_to_fp(mp3)
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
for m in history:
    with st.chat_message(m["role"]):
        if mode == "Writer" and m["role"] == "assistant":
            show_code(m["content"])  # copy button in the top-right corner
        else:
            st.markdown(m["content"])
