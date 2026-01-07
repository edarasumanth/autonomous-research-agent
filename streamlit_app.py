"""
Autonomous Research Agent - Web Interface with Chat

A production-ready Streamlit web interface featuring:
- Chat-based research initiation
- Form-based structured research
- Follow-up Q&A for completed sessions
- PDF viewer and report rendering

Usage:
    streamlit run streamlit_app.py
"""

import os
import sys

# Ensure npm binaries (including claude CLI) are in PATH
npm_path = os.path.expanduser("~\\AppData\\Roaming\\npm")
if npm_path not in os.environ.get("PATH", ""):
    os.environ["PATH"] = npm_path + os.pathsep + os.environ.get("PATH", "")

import asyncio

import streamlit as st
import base64
import json
import traceback
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from web_research_agent import (
    ResearchRequest,
    ResearchProgress,
    run_web_research,
    list_research_sessions,
    get_session_report,
    get_session_pdfs,
    get_pdf_path,
)

from chat_research_agent import chat_with_agent, quick_research_chat


# =============================================================================
# Page Configuration
# =============================================================================

st.set_page_config(
    page_title="Research Agent",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }

    [data-testid="stSidebar"] {
        background-color: #f8f9fa;
    }

    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
    }

    .main-header h1 {
        margin: 0;
        font-size: 1.8rem;
    }

    .main-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
        font-size: 0.95rem;
    }

    .chat-message {
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 1rem;
    }

    .chat-message.user {
        background: #e3f2fd;
        margin-left: 20%;
    }

    .chat-message.assistant {
        background: #f5f5f5;
        margin-right: 10%;
    }

    .tool-notification {
        background: #fff3e0;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        font-size: 0.9rem;
        border-left: 3px solid #ff9800;
    }

    .stats-row {
        display: flex;
        gap: 1rem;
        margin: 1rem 0;
    }

    .stat-box {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        text-align: center;
        flex: 1;
    }

    .stat-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #667eea;
    }

    .stat-label {
        font-size: 0.8rem;
        color: #666;
    }

    .stButton > button {
        border-radius: 8px;
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border: none;
    }

    .pdf-frame {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        overflow: hidden;
    }

    /* Chat input styling */
    .stChatInput {
        border-radius: 12px;
    }

    /* Session card in sidebar */
    .session-item {
        padding: 0.75rem;
        margin-bottom: 0.5rem;
        background: white;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        cursor: pointer;
    }

    .session-item:hover {
        border-color: #667eea;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# Session State Initialization
# =============================================================================

if "current_view" not in st.session_state:
    st.session_state.current_view = "chat"  # Default to chat view

if "selected_session" not in st.session_state:
    st.session_state.selected_session = None

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

if "chat_session_path" not in st.session_state:
    st.session_state.chat_session_path = None

if "research_running" not in st.session_state:
    st.session_state.research_running = False

if "stop_requested" not in st.session_state:
    st.session_state.stop_requested = False

if "chat_model" not in st.session_state:
    st.session_state.chat_model = "claude-sonnet-4-20250514"


# =============================================================================
# Helper Functions
# =============================================================================

def clear_chat():
    """Clear chat history and start fresh."""
    st.session_state.chat_messages = []
    st.session_state.chat_session_path = None


def switch_to_chat():
    """Switch to chat view."""
    st.session_state.current_view = "chat"
    st.session_state.selected_session = None
    clear_chat()


def switch_to_session(session):
    """Switch to viewing a specific session."""
    st.session_state.current_view = "view_session"
    st.session_state.selected_session = session
    # Prepare chat for follow-up Q&A
    st.session_state.chat_messages = []
    st.session_state.chat_session_path = session["path"]


# =============================================================================
# Sidebar
# =============================================================================

with st.sidebar:
    st.markdown("## 🔬 Research Agent")

    # New Chat button
    if st.button("💬 New Chat", use_container_width=True, type="primary"):
        switch_to_chat()
        st.rerun()

    # Structured Research button
    if st.button("📋 Structured Research", use_container_width=True):
        st.session_state.current_view = "structured"
        st.session_state.selected_session = None
        st.rerun()

    st.markdown("---")
    st.markdown("### 📁 Research History")

    # List sessions
    sessions = list_research_sessions()

    if not sessions:
        st.caption("No research sessions yet")
    else:
        for session in sessions:
            # Parse info
            try:
                date_str = session["folder"][:15]
                date = datetime.strptime(date_str, "%Y%m%d_%H%M%S")
                date_display = date.strftime("%b %d, %H:%M")
            except:
                date_display = ""

            topic = session.get("metadata", {}).get("topic", session["topic"])
            if len(topic) > 30:
                topic = topic[:30] + "..."

            # Status
            status = "✅" if session.get("completion") else "⏳"
            pdf_count = len(session.get("pdfs", []))

            # Model info
            model = session.get("metadata", {}).get("model", "")
            model_short = ""
            if model:
                if "opus" in model.lower():
                    model_short = "Opus"
                elif "sonnet" in model.lower():
                    model_short = "Sonnet"
                elif "haiku" in model.lower():
                    model_short = "Haiku"
                else:
                    model_short = model.split("-")[0] if "-" in model else model[:10]

            # Button for each session
            btn_label = f"{status} **{topic}**"
            if date_display:
                btn_label += f"\n\n{date_display}"
            if model_short:
                btn_label += f" • {model_short}"
            if pdf_count:
                btn_label += f" • {pdf_count} PDFs"

            if st.button(btn_label, key=f"sess_{session['folder']}", use_container_width=True):
                switch_to_session(session)
                st.rerun()



# =============================================================================
# Main Content Area
# =============================================================================

# Header
st.markdown("""
<div class="main-header">
    <h1>🔬 Autonomous Research Agent</h1>
    <p>AI-powered research assistant • Chat naturally or use structured forms</p>
</div>
""", unsafe_allow_html=True)



# =============================================================================
# View: Chat Interface
# =============================================================================

if st.session_state.current_view == "chat":
    st.markdown("### 💬 Chat with Research Agent")

    # Model selector row
    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption("Ask me to research any topic. I'll search for papers, analyze them, and share my findings.")
    with col2:
        st.session_state.chat_model = st.selectbox(
            "Model",
            ["claude-sonnet-4-20250514", "claude-opus-4-20250514", "claude-haiku-3-5-20241022"],
            index=["claude-sonnet-4-20250514", "claude-opus-4-20250514", "claude-haiku-3-5-20241022"].index(st.session_state.chat_model),
            key="chat_model_selector",
            label_visibility="collapsed"
        )

    # Display chat messages
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Control buttons (show after messages exist)
    if st.session_state.chat_messages:
        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            if st.button("🔄 New Research", use_container_width=True):
                clear_chat()
                st.rerun()
        with col2:
            if st.button("🛑 End Session", use_container_width=True, type="secondary"):
                st.session_state.stop_requested = True
                st.success("Session ended. Start a new research or ask follow-up questions!")

    # Chat input
    if prompt := st.chat_input("Ask me to research something...", key="chat_input"):
        # Add user message
        st.session_state.chat_messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            response_placeholder.markdown("🔬 *Researching... please wait...*")
            response_container = [""]

            # Check if this is a research request
            research_keywords = ["research", "find papers", "search for", "look up", "investigate", "explore", "learn about", "tell me about"]
            is_research = any(kw in prompt.lower() for kw in research_keywords)

            try:
                # Create session folder if research-like query
                if is_research and not st.session_state.chat_session_path:
                    from web_research_tools import ResearchConfig
                    topic_words = prompt.split()[:5]
                    topic_slug = "_".join(topic_words)[:30]
                    st.session_state.chat_session_path = ResearchConfig.create_session_folder(
                        topic_slug, "research_sessions"
                    )
                    # Save metadata for chat session
                    chat_metadata = {
                        "topic": " ".join(topic_words),
                        "mode": "chat",
                        "model": st.session_state.chat_model,
                        "created_at": datetime.now().isoformat(),
                    }
                    with open(os.path.join(st.session_state.chat_session_path, "metadata.json"), "w") as f:
                        json.dump(chat_metadata, f, indent=2)

                import concurrent.futures

                # Capture values before entering thread
                chat_history = list(st.session_state.chat_messages[:-1])
                session_path = st.session_state.chat_session_path

                def run_async_chat(user_prompt, history, sess_path, chat_model):
                    """Run the async chat using anyio for proper task context."""
                    import anyio

                    if sys.platform == "win32":
                        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

                    async def collect_response():
                        result = ""
                        async for chunk in chat_with_agent(
                            user_prompt,
                            history,
                            mode="research",
                            research_session_path=sess_path,
                            model=chat_model,
                        ):
                            result += chunk
                        return result

                    return anyio.run(collect_response, backend="asyncio", backend_options={"use_uvloop": False})

                selected_model = st.session_state.chat_model
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_async_chat, prompt, chat_history, session_path, selected_model)
                    response_container[0] = future.result(timeout=300)

                response_placeholder.markdown(response_container[0])

                # Save completion.json if session exists and file doesn't exist yet
                if st.session_state.chat_session_path:
                    completion_path = os.path.join(st.session_state.chat_session_path, "completion.json")
                    if not os.path.exists(completion_path):
                        completion_data = {
                            "completed_at": datetime.now().isoformat(),
                            "mode": "chat",
                            "stats": {}
                        }
                        with open(completion_path, "w") as f:
                            json.dump(completion_data, f, indent=2)

            except Exception as e:
                error_details = traceback.format_exc()
                response_container[0] = f"Error: {str(e)}\n\n```\n{error_details}\n```"
                response_placeholder.markdown(response_container[0])

            # Save assistant response
            st.session_state.chat_messages.append({"role": "assistant", "content": response_container[0]})

    # Quick action buttons
    st.markdown("---")
    st.markdown("**Quick Research Topics:**")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🧠 Transformer Architectures", use_container_width=True):
            st.session_state.chat_messages.append({
                "role": "user",
                "content": "Research transformer architectures in deep learning - key innovations and recent advances"
            })
            st.rerun()

    with col2:
        if st.button("🧬 CRISPR Gene Editing", use_container_width=True):
            st.session_state.chat_messages.append({
                "role": "user",
                "content": "Research CRISPR gene editing technology - mechanisms, applications, and ethical considerations"
            })
            st.rerun()

    with col3:
        if st.button("🌍 Climate AI", use_container_width=True):
            st.session_state.chat_messages.append({
                "role": "user",
                "content": "Research how AI and machine learning are being applied to climate change prediction and mitigation"
            })
            st.rerun()


# =============================================================================
# View: Structured Research Form
# =============================================================================

elif st.session_state.current_view == "structured":
    st.markdown("### 📋 Structured Research")
    st.caption("Fill out the form for comprehensive, systematic research.")

    with st.form("research_form"):
        topic = st.text_input(
            "Research Topic *",
            placeholder="e.g., Mixture of Experts in Large Language Models"
        )

        background = st.text_area(
            "Background & Context *",
            placeholder="What specific aspects are you interested in?\nWhat questions do you want answered?",
            height=120
        )

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            depth = st.selectbox("Depth", ["quick", "standard", "deep"], index=1)
        with col2:
            max_papers = st.number_input("Max Papers", 1, 20, 8)
        with col3:
            max_searches = st.number_input("Max Searches", 3, 30, 15)
        with col4:
            model = st.selectbox("Model", [
                "claude-sonnet-4-20250514",
                "claude-opus-4-20250514",
                "claude-haiku-3-5-20241022",
            ], index=0)

        col4, col5 = st.columns(2)
        with col4:
            time_period = st.text_input("Time Period", placeholder="e.g., 2022-2024")
        with col5:
            domains = st.text_input("Domains", placeholder="e.g., ML, biology")

        submitted = st.form_submit_button("🚀 Start Research", type="primary", use_container_width=True)

        if submitted and topic and background:
            st.session_state.research_running = True
            st.session_state.research_request = ResearchRequest(
                topic=topic,
                background=background,
                depth=depth,
                max_papers=max_papers,
                time_period=time_period if time_period else None,
                domains=[d.strip() for d in domains.split(",") if d.strip()] if domains else [],
                max_searches=max_searches,
                model=model,
            )
            st.rerun()

    # Handle running research
    if st.session_state.get("research_running"):
        request = st.session_state.research_request
        st.markdown("---")
        st.markdown(f"### 🔄 Researching: {request.topic}")

        progress_bar = st.progress(0)
        status_text = st.empty()
        log_container = st.container()

        progress_data = {"searches": 0, "downloads": 0, "reads": 0, "notes": 0}

        def update_progress(p):
            progress_data["searches"] = p.searches
            progress_data["downloads"] = p.downloads
            progress_data["reads"] = p.pdfs_read
            progress_data["notes"] = p.notes_saved

        try:
            result = asyncio.run(run_web_research(request, update_progress))
            st.session_state.research_running = False

            if result.get("session_dir"):
                sessions = list_research_sessions()
                if sessions:
                    switch_to_session(sessions[0])
                st.success("✅ Research complete!")
                st.rerun()

        except Exception as e:
            st.session_state.research_running = False
            st.error(f"Error: {str(e)}")


# =============================================================================
# View: Session Details with Follow-up Chat
# =============================================================================

elif st.session_state.current_view == "view_session" and st.session_state.selected_session:
    session = st.session_state.selected_session
    topic = session.get("metadata", {}).get("topic", session["topic"])

    st.markdown(f"### 📋 {topic}")

    # Stats row
    comp = session.get("completion", {})
    stats = comp.get("stats", {})

    # Get model info
    model_full = session.get("metadata", {}).get("model", "Unknown")
    if "opus" in model_full.lower():
        model_display = "Opus"
    elif "sonnet" in model_full.lower():
        model_display = "Sonnet"
    elif "haiku" in model_full.lower():
        model_display = "Haiku"
    else:
        model_display = model_full[:15] if model_full else "Unknown"

    # Count actual PDFs and notes from filesystem (more reliable)
    pdfs_dir = os.path.join(session["path"], "pdfs")
    actual_pdfs = len([f for f in os.listdir(pdfs_dir) if f.endswith(".pdf")]) if os.path.exists(pdfs_dir) else 0
    notes_dir = os.path.join(session["path"], "notes")
    actual_notes = len(os.listdir(notes_dir)) if os.path.exists(notes_dir) else 0

    # Use actual counts, fall back to stats if available
    paper_count = actual_pdfs or stats.get('pdfs_read', stats.get('reads', 0))
    notes_count = actual_notes or stats.get('notes_saved', stats.get('notes', 0))

    cols = st.columns(5)
    with cols[0]:
        st.metric("Model", model_display)
    with cols[1]:
        duration = comp.get('duration_seconds', 0)
        st.metric("Duration", f"{duration:.0f}s" if duration else "N/A")
    with cols[2]:
        cost = comp.get('cost_usd')
        st.metric("Cost", f"${cost:.2f}" if cost else "N/A")
    with cols[3]:
        st.metric("Papers", paper_count)
    with cols[4]:
        st.metric("Notes", notes_count)

    # Tabs
    tab1, tab2, tab3 = st.tabs(["📄 Report", "📚 PDFs", "💬 Ask Questions"])

    with tab1:
        report = get_session_report(session["path"])
        if report:
            st.markdown(report)
        else:
            # No report - check if there are notes to display
            notes_dir = os.path.join(session["path"], "notes")
            if os.path.exists(notes_dir) and os.listdir(notes_dir):
                st.warning("No formal report was generated for this session. Displaying research notes instead:")
                st.markdown("---")
                for note_file in sorted(os.listdir(notes_dir)):
                    note_path = os.path.join(notes_dir, note_file)
                    try:
                        with open(note_path, "r", encoding="utf-8") as f:
                            note_data = json.load(f)
                        st.markdown(f"### 📝 {note_data.get('title', note_file)}")
                        if note_data.get('note_type'):
                            st.caption(f"Type: {note_data['note_type']}")
                        st.markdown(note_data.get('content', 'No content'))
                        st.markdown("---")
                    except Exception as e:
                        st.error(f"Error reading note {note_file}: {e}")
            elif paper_count > 0:
                st.info(f"No report available. This session has {paper_count} downloaded PDFs - you can view them in the PDFs tab or ask questions about them.")
            else:
                st.info("No report available. This session appears to be empty or incomplete.")

    with tab2:
        pdfs = get_session_pdfs(session["path"])
        if not pdfs:
            st.info("No PDFs in this session.")
        else:
            st.markdown(f"**{len(pdfs)} Papers Downloaded:**")

            for pdf in pdfs:
                col1, col2 = st.columns([5, 1])
                with col1:
                    st.markdown(f"📄 {pdf}")
                with col2:
                    pdf_path = get_pdf_path(session["path"], pdf)
                    if pdf_path:
                        with open(pdf_path, "rb") as f:
                            st.download_button("⬇️", f.read(), pdf, "application/pdf", key=f"dl_{pdf}")

            # PDF Viewer
            st.markdown("---")
            selected_pdf = st.selectbox("View PDF:", [""] + pdfs)
            if selected_pdf:
                pdf_path = get_pdf_path(session["path"], selected_pdf)
                if pdf_path:
                    with open(pdf_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode()
                    st.markdown(
                        f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="700px"></iframe>',
                        unsafe_allow_html=True
                    )

    with tab3:
        st.markdown("**Ask follow-up questions about this research:**")

        # Session-specific chat
        chat_key = f"chat_{session['folder']}"
        if chat_key not in st.session_state:
            st.session_state[chat_key] = []

        # Display messages
        for msg in st.session_state[chat_key]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Chat input
        if followup := st.chat_input("Ask about the research...", key=f"input_{session['folder']}"):
            st.session_state[chat_key].append({"role": "user", "content": followup})

            with st.chat_message("user"):
                st.markdown(followup)

            with st.chat_message("assistant"):
                placeholder = st.empty()
                response_container = [""]  # Use mutable container for async access

                try:
                    import concurrent.futures

                    # Capture values before entering thread
                    followup_history = list(st.session_state[chat_key][:-1])
                    sess_path = session["path"]
                    sess_model = session.get("metadata", {}).get("model")

                    def run_followup_chat(user_followup, history, path, followup_model):
                        """Run the async followup chat using anyio."""
                        import anyio

                        # Set Windows event loop policy for subprocess support
                        if sys.platform == "win32":
                            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

                        async def collect_followup():
                            result = ""
                            async for chunk in chat_with_agent(
                                user_followup,
                                history,
                                mode="followup",
                                research_session_path=path,
                                model=followup_model,
                            ):
                                result += chunk
                            return result

                        return anyio.run(collect_followup, backend="asyncio", backend_options={"use_uvloop": False})

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(run_followup_chat, followup, followup_history, sess_path, sess_model)
                        response_container[0] = future.result(timeout=300)

                    placeholder.markdown(response_container[0])

                except Exception as e:
                    error_details = traceback.format_exc()
                    response_container[0] = f"Error: {str(e)}\n\n```\n{error_details}\n```"
                    placeholder.markdown(response_container[0])

                st.session_state[chat_key].append({"role": "assistant", "content": response_container[0]})


# =============================================================================
# Footer
# =============================================================================

st.markdown("---")
st.caption("Powered by Claude Agent SDK • Built with Streamlit")
