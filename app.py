import os
import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="XENO Voice Assistant", layout="centered")
st.title("🎙️ XENO Voice Assistant")

# Grab the API key securely from Streamlit Secrets
api_key = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=api_key)

# Initialize conversation memory
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "Your name is XENO. You are a helpful voice work assistant. Keep responses relatively concise since they will be read aloud."}
    ]

# Display historical chat text
for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# 1. VOICE INPUT: Add an audio recorder input button
audio_value = st.audio_input("Press to record your voice for XENO")

if audio_value:
    # Save the temporary audio recorded from your phone/computer mic
    with open("temp_audio.wav", "wb") as f:
        f.write(audio_value.read())
        
    with st.spinner("XENO is listening..."):
        # 2. SPEECH-TO-TEXT: Convert your recorded voice into text using Whisper
        audio_file = open("temp_audio.wav", "rb")
        transcription = client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_file
        )
        user_text = transcription.text

    # Display your spoken words as text
    with st.chat_message("user"):
        st.markdown(user_text)
    st.session_state.messages.append({"role": "user", "content": user_text})

    # Generate XENO's intelligence response
    with st.chat_message("assistant"):
        with st.spinner("XENO is thinking..."):
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=st.session_state.messages
            )
            answer = response.choices.message.content
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
        
        # 3. TEXT-TO-SPEECH: Convert XENO's reply text into a spoken voice file
        with st.spinner("XENO is speaking..."):
            voice_response = client.audio.speech.create(
                model="tts-1",
                voice="alloy", # You can change voice to: echo, onyx, nova, or shimmer
                input=answer
            )
            # Save speech to a file
            voice_response.stream_to_file("xeno_reply.mp3")
            
            # Play the audio back automatically through your phone/computer speakers
            st.audio("xeno_reply.mp3", autoplay=True)
