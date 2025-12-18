# app.py
import streamlit as st
import os
from backend.orchestrator_agent import orchestrate


st.set_page_config(page_title="🍑 Peach+", layout="wide")
st.title("🍑 Peach - Message_ix Chat Agent")

# ---------- FILE UPLOAD ----------
uploaded_file = st.file_uploader("📤 Upload scenario Excel file", type=["xlsx"])

input_file_path = None
uploaded = False

if uploaded_file:
    uploaded = True
    os.makedirs("data/history/uploads", exist_ok=True)
    os.makedirs("data/history/outputs", exist_ok=True)

    input_path = os.path.join("data/history/uploads", uploaded_file.name)
    with open(input_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.success(f"✅ File uploaded: {uploaded_file.name}")



# ---------- CHAT MEMORY ----------
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# ---------- USER INPUT ----------
user_input = st.chat_input("Type your instruction or question...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("⏳ Processing..."):
            try:
                result = orchestrate(
                    instruction=user_input,
                    uploaded=uploaded,
                    input_file=input_file_path
                )

                # ---------- DISPLAY ----------
                assistant_reply = result["reply"]
                st.markdown(assistant_reply)
                st.session_state.messages.append(
                    {"role": "assistant", "content": assistant_reply}
                )


                if result.get("code"):
                    with st.expander("🤖 Generated Code"):
                        st.code(result["code"], language="python")

                if result.get("logs"):
                    with st.expander("📜 Execution Logs"):
                        st.text(result["logs"])

                if result.get("output_file"):
                    st.download_button(
                        "⬇️ Download Updated Scenario",
                        data=open(result["output_file"], "rb"),
                        file_name=os.path.basename(result["output_file"]),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

            except Exception as e:
                error_message = f"❌ Error: (app.py) {e}"
                st.error(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})
