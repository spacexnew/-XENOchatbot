import os
import streamlit as st
from groq import Groq
from gtts import gTTS

st.set_page_config(page_title="XENO Groq Voice Bot", layout="centered")
st.title("⚡ XENO: Fast Groq Voice Assistant")

# 1. Grab your Groq API Key securely from secrets
groq_key = st.secrets["GROQ_API_KEY"]
client = Groq(api_key=groq_key)

# 2. STRICTLY FORCE MEMORY TO RESET FOR XENO (Fixes the "Amy" name bug)
if "messages" not in st.session_state or len(st.session_state.messages) <= 1:
    st.session_state.messages = [
        {
            "role": "system", 
            "content": "Your name is XENO. You are a lightning-fast, helpful voice work assistant. Never call yourself Amy. Always refer to yourself as XENO. Keep responses brief and friendly."
        }
    ]

# Display historical conversation bubbles
for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# 3. VOICE INPUT: Record speech using your phone or computer mic
audio_value = st.audio_input("Tap to record your voice for XENO")

if audio_value:
    # Save the recorded audio byte stream to a file
    with open("temp_audio.wav", "wb") as f:
        f.write(audio_value.read())
        
    with st.spinner("XENO is listening..."):
        # SPEECH-TO-TEXT: Transcribe voice using Groq's Whisper engine
        with open("temp_audio.wav", "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-large-v3-turbo", 
                file=audio_file
            )
        user_text = transcription.text

    # Show what you said on screen
    with st.chat_message("user"):
        st.markdown(user_text)
    st.session_state.messages.append({"role": "user", "content": user_text})

    # 4. CHAT COMPLETION: Clean, corrected message payload to avoid BadRequestError
    with st.chat_message("assistant"):
        with st.spinner("XENO is typing..."):
            response = client.chat.completions.create(
                model="llama-3.3-70b-specdec", 
                messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
            )
            answer = response.choices.message.content
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
        
        # 5. TEXT-TO-SPEECH: Make XENO talk back using free gTTS
        with st.spinner("XENO is vocalizing..."):
            tts = gTTS(text=answer, lang='en', tld='com')
            tts.save("xeno_reply.mp3")
            
            # Autoplay audio directly through your mobile or desktop speaker
            st.audio("xeno_reply.mp3", autoplay=True)
