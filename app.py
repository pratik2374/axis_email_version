"""Simple chatbot UI for Axis Bank Document Verification."""

import os
import tempfile

import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Axis Bank Document Verification Chatbot",
    page_icon="🏦",
    layout="centered"
)

# Title & hero info
st.title("🏦 Axis Bank Document Verification Desk")
st.caption("Compose messages, upload proofs, and receive verification briefings.")
st.markdown(
    """
**Supported Documents:** Aadhaar, PAN, Passport, Utility Bills, Bank Statements, Salary Slips, Form 16, ITR  
**Typical Requests:** Account opening, address change, loan processing, credit card KYC, business onboarding  
**Next Steps:** Upload files → describe what you need → wait for the assistant's review
"""
)
with st.expander("ℹ️ Tips"):
        st.markdown(
            """
1. Attach PDFs or images before sending a request.  
2. Summarize the outcome you need (e.g., *confirm PAN authenticity*).  
3. Mention any deadlines or application IDs for context.  
4. Sensitive numbers are masked automatically in responses.
"""
        )


OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    st.info("❗ OpenAI API Key Not Found, Please setup in (secrets.toml) file.")
    st.stop()

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
from verification_agent import create_agent

# Initialize session state
if "agent" not in st.session_state:
    st.session_state.agent = create_agent()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = {}
if "temp_dir" not in st.session_state:
    st.session_state.temp_dir = tempfile.mkdtemp()
if "pending_upload_ack" not in st.session_state:
    st.session_state.pending_upload_ack = False


def save_uploaded_file(uploaded_file, temp_dir: str) -> str:
    """Save uploaded file to temporary directory and return path."""
    file_path = os.path.join(temp_dir, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path


st.markdown("---")

# Display email-style thread
thread = st.container()
role_label = {"user": "From: Customer", "assistant": "From: Axis Verification Desk"}

with thread:
    for message in st.session_state.messages:
        st.markdown(f"**{role_label.get(message['role'], 'Note')}**")
        st.markdown(message["content"])
        st.markdown("---")

upload_col, compose_col = st.columns([1, 2], vertical_alignment="top")

with upload_col:
    st.subheader("Attachments")
    uploaded_files = st.file_uploader(
        "Attach supporting documents (PDF, PNG, JPG)",
        type=["jpg", "jpeg", "png", "pdf"],
        accept_multiple_files=True,
        help="Attach the files you want the verification desk to review."
    )

    if uploaded_files:
        new_files = []
        for uploaded_file in uploaded_files:
            file_path = save_uploaded_file(uploaded_file, st.session_state.temp_dir)
            if uploaded_file.name not in st.session_state.uploaded_files:
                new_files.append(uploaded_file.name)
            st.session_state.uploaded_files[uploaded_file.name] = file_path

        if new_files:
            st.success(f"✅ {len(new_files)} new file(s) attached: {', '.join(new_files)}")
            st.session_state.pending_upload_ack = True
        else:
            st.info(f"📎 {len(uploaded_files)} file(s) already attached")


with compose_col:
    st.subheader("Compose")
    with st.form("email_composer"):
        prompt = st.text_area("Compose your note", placeholder="Describe what needs to be verified…", height=149)
        submitted = st.form_submit_button("Send Message", use_container_width=True)

if submitted and prompt.strip():
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.spinner("Sending your request to AXIS BANK HELP DESK..."):
        try:
            user_message = prompt

            if st.session_state.uploaded_files:
                file_info = "\n\n[UPLOADED FILES AVAILABLE FOR ANALYSIS]\n"
                for filename, file_path in st.session_state.uploaded_files.items():
                    if os.path.exists(file_path):
                        file_info += f"File: {filename}\nPath: {file_path}\n\n"
                    else:
                        file_info += f"File: {filename} (path not found: {file_path})\n\n"

                instructions = ""
                if st.session_state.pending_upload_ack:
                    instructions = (
                        "\n\n[NEW UPLOADS]\n"
                        "Please confirm you have received and reviewed the newly attached files listed below "
                        "before addressing the customer's request.\n"
                    )
                file_info += "You can use the analyze_document_image tool with these file paths to verify documents."
                user_message = prompt + instructions + file_info

            response = st.session_state.agent.run(user_message)
            assistant_response = response.content if hasattr(response, 'content') else str(response)

            st.session_state.messages.append({
                "role": "assistant",
                "content": assistant_response
            })
            st.session_state.pending_upload_ack = False
            st.rerun()

        except Exception as e:
            error_msg = f"Sorry, I encountered an error: {str(e)}"
            st.error(error_msg)
            st.exception(e)
            st.session_state.messages.append({
                "role": "assistant",
                "content": error_msg
            })
