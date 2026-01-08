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
import base64
import json
import random
import shutil
import traceback
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from chat_research_agent import chat_with_agent
from web_research_agent import (
    ResearchRequest,
    get_pdf_path,
    get_session_pdfs,
    get_session_report,
    list_research_sessions,
    run_web_research,
)

# =============================================================================
# Page Configuration
# =============================================================================

st.set_page_config(
    page_title="Research Agent",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS - Enhanced UI
st.markdown(
    """
<style>
    /* Main container */
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }

    [data-testid="stSidebar"] .stButton > button {
        transition: all 0.2s ease;
    }

    [data-testid="stSidebar"] .stButton > button:hover {
        transform: translateX(3px);
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
    }

    /* Main header */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 20px rgba(102, 126, 234, 0.3);
    }

    .main-header h1 {
        margin: 0;
        font-size: 1.8rem;
        font-weight: 700;
    }

    .main-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
        font-size: 0.95rem;
    }

    /* Metrics styling */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        padding: 1rem;
        border-radius: 12px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }

    [data-testid="stMetric"] label {
        color: #666;
        font-size: 0.85rem;
    }

    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #667eea;
        font-weight: 600;
    }

    /* Chat messages */
    .stChatMessage {
        border-radius: 16px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    }

    /* Expander styling */
    .streamlit-expanderHeader {
        background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
        border-radius: 8px;
        font-weight: 500;
    }

    .streamlit-expanderHeader:hover {
        background: linear-gradient(135deg, #e9ecef 0%, #f8f9fa 100%);
    }

    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        font-weight: 500;
    }

    /* Button styling */
    .stButton > button {
        border-radius: 10px;
        font-weight: 500;
        transition: all 0.2s ease;
    }

    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border: none;
    }

    .stButton > button[kind="secondary"] {
        border: 2px solid #667eea;
        color: #667eea;
    }

    /* Info/Success/Warning boxes */
    .stAlert {
        border-radius: 12px;
        border: none;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }

    /* Chat input */
    .stChatInput > div {
        border-radius: 24px;
        border: 2px solid #e0e0e0;
        transition: border-color 0.2s ease;
    }

    .stChatInput > div:focus-within {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }

    /* Selectbox styling */
    .stSelectbox > div > div {
        border-radius: 8px;
    }

    /* Progress spinner */
    .stSpinner > div {
        border-color: #667eea;
    }

    /* Download button */
    .stDownloadButton > button {
        background: #28a745;
        color: white;
        border: none;
        border-radius: 8px;
    }

    .stDownloadButton > button:hover {
        background: #218838;
    }

    /* Code blocks in notes */
    code {
        background: #f1f3f4;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.9em;
    }

    /* Session card in sidebar */
    .session-item {
        padding: 0.75rem;
        margin-bottom: 0.5rem;
        background: white;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        cursor: pointer;
        transition: all 0.2s ease;
    }

    .session-item:hover {
        border-color: #667eea;
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.2);
    }
</style>
""",
    unsafe_allow_html=True,
)


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
        # Reset quick topics for fresh experience
        if "quick_topics" in st.session_state:
            del st.session_state.quick_topics
        switch_to_chat()
        st.rerun()

    # Structured Research button
    if st.button("📋 Structured Research", use_container_width=True):
        st.session_state.current_view = "structured"
        st.session_state.selected_session = None
        st.rerun()

    st.markdown("---")

    # Research History section with management
    history_col1, history_col2 = st.columns([3, 1])
    with history_col1:
        st.markdown("### 📁 Research History")
    with history_col2:
        # Clear history button (small)
        if "confirm_clear" not in st.session_state:
            st.session_state.confirm_clear = False

    # List sessions
    sessions = list_research_sessions()

    # Filter to show only meaningful sessions (with metadata or completion)
    valid_sessions = [
        s
        for s in sessions
        if s.get("metadata")
        or s.get("completion")
        or s.get("has_report")
        or len(s.get("pdfs", [])) > 0
    ]

    if not valid_sessions:
        st.caption("✨ No research sessions yet")
        st.caption("Start a new chat to begin researching!")
    else:
        # Show count and clear option
        st.caption(f"📊 {len(valid_sessions)} session(s)")

        # Clear all history button with confirmation
        if st.session_state.confirm_clear:
            st.warning("⚠️ Delete all sessions?")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✓ Yes", use_container_width=True, type="primary"):
                    # Delete all sessions
                    for session in valid_sessions:
                        try:
                            shutil.rmtree(session["path"])
                        except Exception:
                            pass
                    st.session_state.confirm_clear = False
                    st.session_state.selected_session = None
                    st.session_state.current_view = "chat"
                    st.rerun()
            with col2:
                if st.button("✗ No", use_container_width=True):
                    st.session_state.confirm_clear = False
                    st.rerun()
        else:
            if st.button("🗑️ Clear All History", use_container_width=True, type="secondary"):
                st.session_state.confirm_clear = True
                st.rerun()

        st.markdown("---")

        for session in valid_sessions:
            # Parse info
            try:
                date_str = session["folder"][:15]
                date = datetime.strptime(date_str, "%Y%m%d_%H%M%S")
                date_display = date.strftime("%b %d, %H:%M")
            except (ValueError, KeyError):
                date_display = ""

            topic = session.get("metadata", {}).get("topic", session["topic"])
            # Clean up topic display
            topic = topic.replace("_", " ").replace("chat research", "").strip()
            if not topic or topic.lower() in ["chat", "research"]:
                topic = "Research Session"
            if len(topic) > 28:
                topic = topic[:25] + "..."

            # Status - check for completion AND report
            has_completion = session.get("completion") is not None
            has_report = session.get("has_report", False)
            pdf_count = len(session.get("pdfs", []))

            # Determine status icon
            if has_completion and has_report:
                status = "✅"  # Fully complete with report
            elif has_completion and pdf_count > 0:
                status = "📄"  # Complete with PDFs but no report
            elif has_completion:
                status = "📝"  # Complete but minimal data
            else:
                status = "⏳"  # In progress

            # Model info
            model = session.get("metadata", {}).get("model", "") or session.get(
                "completion", {}
            ).get("model", "")
            model_short = ""
            if model:
                if "opus" in model.lower():
                    model_short = "🧠"
                elif "sonnet" in model.lower():
                    model_short = "⚡"
                elif "haiku" in model.lower():
                    model_short = "🚀"

            # Duration info
            duration = session.get("completion", {}).get("duration_seconds", 0)
            if duration >= 60:
                duration_str = f"{int(duration//60)}m"
            elif duration > 0:
                duration_str = f"{int(duration)}s"
            else:
                duration_str = ""

            # Build label
            btn_label = f"{status} **{topic}**"
            meta_parts = []
            if date_display:
                meta_parts.append(date_display)
            if model_short:
                meta_parts.append(model_short)
            if duration_str:
                meta_parts.append(duration_str)
            if pdf_count:
                meta_parts.append(f"📚{pdf_count}")

            if meta_parts:
                btn_label += f"\n\n{' • '.join(meta_parts)}"

            if st.button(btn_label, key=f"sess_{session['folder']}", use_container_width=True):
                switch_to_session(session)
                st.rerun()


# =============================================================================
# Main Content Area
# =============================================================================

# Header
st.markdown(
    """
<div class="main-header">
    <h1>🔬 Autonomous Research Agent</h1>
    <p>AI-powered research assistant • Chat naturally or use structured forms</p>
</div>
""",
    unsafe_allow_html=True,
)


# =============================================================================
# View: Chat Interface
# =============================================================================

if st.session_state.current_view == "chat":
    st.markdown("### 💬 Chat with Research Agent")

    # Model selector row with descriptions
    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption(
            "Ask me to research any topic. I'll search for papers, analyze them, and share my findings."
        )
    with col2:
        model_options = {
            "claude-sonnet-4-20250514": "⚡ Sonnet (Fast)",
            "claude-opus-4-20250514": "🧠 Opus (Best)",
            "claude-haiku-3-5-20241022": "🚀 Haiku (Quick)",
        }
        selected_display = st.selectbox(
            "Model",
            list(model_options.values()),
            index=list(model_options.keys()).index(st.session_state.chat_model),
            key="chat_model_selector",
            label_visibility="collapsed",
        )
        # Map back to model ID
        st.session_state.chat_model = list(model_options.keys())[
            list(model_options.values()).index(selected_display)
        ]

    # Welcome section for new users (show when no messages)
    if not st.session_state.chat_messages:
        st.markdown("---")

        # Welcome card
        st.markdown(
            """
        <div style="background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%); padding: 1.5rem; border-radius: 12px; margin-bottom: 1rem;">
            <h4 style="margin: 0 0 0.5rem 0;">👋 Welcome to the Research Agent!</h4>
            <p style="margin: 0; color: #555;">I can help you explore academic topics by searching papers, analyzing PDFs, and generating comprehensive reports.</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # How it works
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(
                """
            **🔍 Step 1: Ask**

            Type your research topic or question in the chat below.
            """
            )
        with col2:
            st.markdown(
                """
            **📚 Step 2: Research**

            I'll search for papers, download PDFs, and analyze the content.
            """
            )
        with col3:
            st.markdown(
                """
            **📄 Step 3: Report**

            Get a comprehensive report with key findings and sources.
            """
            )

        st.markdown("---")
        st.info(
            '💡 **Tip:** Be specific! Instead of "AI", try "Recent advances in transformer architectures for natural language processing"'
        )

    # Display chat messages
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Control buttons (show after messages exist)
    if st.session_state.chat_messages:
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("🔄 New Research", use_container_width=True, type="primary"):
                # Reset quick topics for fresh experience
                if "quick_topics" in st.session_state:
                    del st.session_state.quick_topics
                clear_chat()
                st.rerun()
        with col2:
            if st.button("🛑 End Session", use_container_width=True, type="secondary"):
                st.session_state.stop_requested = True
                st.success("Session ended. Start a new research or ask follow-up questions!")
        st.markdown("---")

    # Chat input - handle both manual input and quick topic buttons
    chat_prompt = st.chat_input("Ask me to research something...", key="chat_input")

    # Check for pending query from quick topic buttons
    pending_query = st.session_state.pop("pending_query", None)
    prompt = chat_prompt or pending_query

    if prompt:
        # Add user message
        st.session_state.chat_messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            response_container = [""]

            # Show spinner while processing
            with st.spinner("🔬 Researching... This may take a few minutes..."):
                # Track start time for duration
                start_time = datetime.now()

                try:
                    # Always create session folder if one doesn't exist
                    if not st.session_state.chat_session_path:
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
                        with open(
                            os.path.join(st.session_state.chat_session_path, "metadata.json"), "w"
                        ) as f:
                            json.dump(chat_metadata, f, indent=2)

                    import concurrent.futures

                    # Capture values before entering thread
                    chat_history = list(st.session_state.chat_messages[:-1])
                    session_path = st.session_state.chat_session_path

                    # Store cost info from callback
                    cost_info = {"duration_ms": 0, "cost_usd": 0}

                    def on_complete(duration_ms, cost_usd):
                        cost_info["duration_ms"] = duration_ms
                        cost_info["cost_usd"] = cost_usd

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
                                on_complete=on_complete,
                            ):
                                result += chunk
                            return result

                        return anyio.run(
                            collect_response,
                            backend="asyncio",
                            backend_options={"use_uvloop": False},
                        )

                    selected_model = st.session_state.chat_model
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            run_async_chat, prompt, chat_history, session_path, selected_model
                        )
                        response_container[0] = future.result(timeout=300)

                    response_placeholder.markdown(response_container[0])

                    # Save/update completion.json with duration and cost
                    if st.session_state.chat_session_path:
                        completion_path = os.path.join(
                            st.session_state.chat_session_path, "completion.json"
                        )
                        end_time = datetime.now()
                        duration_seconds = (end_time - start_time).total_seconds()

                        # Load existing completion data or create new
                        if os.path.exists(completion_path):
                            with open(completion_path, "r") as f:
                                completion_data = json.load(f)
                            # Add to existing duration and cost
                            completion_data["duration_seconds"] = (
                                completion_data.get("duration_seconds", 0) + duration_seconds
                            )
                            completion_data["cost_usd"] = completion_data.get(
                                "cost_usd", 0
                            ) + cost_info.get("cost_usd", 0)
                        else:
                            completion_data = {
                                "completed_at": end_time.isoformat(),
                                "mode": "chat",
                                "model": st.session_state.chat_model,
                                "duration_seconds": duration_seconds,
                                "cost_usd": cost_info.get("cost_usd", 0),
                                "stats": {},
                            }

                        completion_data["last_updated"] = end_time.isoformat()
                        with open(completion_path, "w") as f:
                            json.dump(completion_data, f, indent=2)

                        # Show completion summary
                        st.success(
                            f"✅ Research complete! Duration: {duration_seconds:.0f}s | Cost: ${cost_info.get('cost_usd', 0):.4f}"
                        )

                except Exception as e:
                    error_details = traceback.format_exc()
                    response_container[0] = f"Error: {str(e)}\n\n```\n{error_details}\n```"
                    response_placeholder.markdown(response_container[0])

            # Save assistant response
            st.session_state.chat_messages.append(
                {"role": "assistant", "content": response_container[0]}
            )

            # Rerun to refresh sidebar with new session
            st.rerun()

    # Quick action buttons with rotating topics
    st.markdown("---")
    st.markdown("**💡 Quick Research Topics:**")

    # Pool of diverse research topics
    ALL_RESEARCH_TOPICS = [
        {
            "icon": "🧠",
            "label": "Transformer Architectures",
            "query": "Research transformer architectures in deep learning - key innovations and recent advances",
        },
        {
            "icon": "🧬",
            "label": "CRISPR Gene Editing",
            "query": "Research CRISPR gene editing technology - mechanisms, applications, and ethical considerations",
        },
        {
            "icon": "🌍",
            "label": "Climate AI",
            "query": "Research how AI and machine learning are being applied to climate change prediction and mitigation",
        },
        {
            "icon": "🤖",
            "label": "Large Language Models",
            "query": "Research the latest advances in large language models - architectures, training methods, and capabilities",
        },
        {
            "icon": "🧪",
            "label": "mRNA Vaccines",
            "query": "Research mRNA vaccine technology - how it works, advantages, and future applications beyond COVID-19",
        },
        {
            "icon": "🔋",
            "label": "Solid-State Batteries",
            "query": "Research solid-state battery technology - current progress, challenges, and potential for electric vehicles",
        },
        {
            "icon": "🌐",
            "label": "Web3 & Blockchain",
            "query": "Research Web3 technologies and blockchain - decentralized systems, smart contracts, and real-world applications",
        },
        {
            "icon": "🧠",
            "label": "Neuromorphic Computing",
            "query": "Research neuromorphic computing - brain-inspired chips, architectures, and applications",
        },
        {
            "icon": "🔬",
            "label": "Quantum Computing",
            "query": "Research quantum computing advances - qubit technologies, algorithms, and near-term applications",
        },
        {
            "icon": "🏥",
            "label": "AI in Drug Discovery",
            "query": "Research AI applications in drug discovery - molecular design, clinical trials, and recent breakthroughs",
        },
        {
            "icon": "🚀",
            "label": "Space Exploration Tech",
            "query": "Research recent advances in space exploration technology - propulsion, habitation, and Mars missions",
        },
        {
            "icon": "🌱",
            "label": "Vertical Farming",
            "query": "Research vertical farming and controlled environment agriculture - technologies, economics, and sustainability",
        },
        {
            "icon": "🎮",
            "label": "AI in Gaming",
            "query": "Research AI applications in video games - procedural generation, NPCs, and player modeling",
        },
        {
            "icon": "🔐",
            "label": "Post-Quantum Cryptography",
            "query": "Research post-quantum cryptography - algorithms resistant to quantum attacks and standardization efforts",
        },
        {
            "icon": "🧬",
            "label": "Synthetic Biology",
            "query": "Research synthetic biology - engineered organisms, biofuels, and biosensors",
        },
        {
            "icon": "🏗️",
            "label": "3D Printed Construction",
            "query": "Research 3D printing in construction - materials, techniques, and sustainable building applications",
        },
        {
            "icon": "🧠",
            "label": "Brain-Computer Interfaces",
            "query": "Research brain-computer interfaces - neural implants, non-invasive methods, and medical applications",
        },
        {
            "icon": "🌊",
            "label": "Ocean Energy",
            "query": "Research ocean energy technologies - wave, tidal, and thermal energy conversion systems",
        },
        {
            "icon": "🤖",
            "label": "Autonomous Vehicles",
            "query": "Research autonomous vehicle technology - sensors, decision-making systems, and regulatory challenges",
        },
        {
            "icon": "💊",
            "label": "Personalized Medicine",
            "query": "Research personalized medicine - genomics, pharmacogenomics, and tailored treatment approaches",
        },
        {
            "icon": "🌿",
            "label": "Carbon Capture",
            "query": "Research carbon capture and storage technologies - direct air capture, geological storage, and utilization",
        },
        {
            "icon": "🔮",
            "label": "Augmented Reality",
            "query": "Research augmented reality technology - displays, tracking, and enterprise applications",
        },
        {
            "icon": "🧫",
            "label": "Lab-Grown Meat",
            "query": "Research cultured meat technology - cell cultivation, scaling challenges, and environmental impact",
        },
        {
            "icon": "⚡",
            "label": "Nuclear Fusion",
            "query": "Research nuclear fusion energy - tokamaks, stellarators, and recent breakthrough experiments",
        },
    ]

    # Initialize or get random topics for this session
    if "quick_topics" not in st.session_state:
        st.session_state.quick_topics = random.sample(ALL_RESEARCH_TOPICS, 3)

    col1, col2, col3 = st.columns(3)
    topics = st.session_state.quick_topics

    with col1:
        if st.button(f"{topics[0]['icon']} {topics[0]['label']}", use_container_width=True):
            st.session_state.pending_query = topics[0]["query"]
            st.rerun()

    with col2:
        if st.button(f"{topics[1]['icon']} {topics[1]['label']}", use_container_width=True):
            st.session_state.pending_query = topics[1]["query"]
            st.rerun()

    with col3:
        if st.button(f"{topics[2]['icon']} {topics[2]['label']}", use_container_width=True):
            st.session_state.pending_query = topics[2]["query"]
            st.rerun()

    # Refresh topics button
    if st.button("🔄 Show different topics", type="secondary"):
        st.session_state.quick_topics = random.sample(ALL_RESEARCH_TOPICS, 3)
        st.rerun()


# =============================================================================
# View: Structured Research Form
# =============================================================================

elif st.session_state.current_view == "structured":
    st.markdown("### 📋 Structured Research")
    st.caption("Fill out the form for comprehensive, systematic research.")

    with st.form("research_form"):
        topic = st.text_input(
            "Research Topic *", placeholder="e.g., Mixture of Experts in Large Language Models"
        )

        background = st.text_area(
            "Background & Context *",
            placeholder="What specific aspects are you interested in?\nWhat questions do you want answered?",
            height=120,
        )

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            depth = st.selectbox("Depth", ["quick", "standard", "deep"], index=1)
        with col2:
            max_papers = st.number_input("Max Papers", 1, 20, 8)
        with col3:
            max_searches = st.number_input("Max Searches", 3, 30, 15)
        with col4:
            model = st.selectbox(
                "Model",
                [
                    "claude-sonnet-4-20250514",
                    "claude-opus-4-20250514",
                    "claude-haiku-3-5-20241022",
                ],
                index=0,
            )

        col4, col5 = st.columns(2)
        with col4:
            time_period = st.text_input("Time Period", placeholder="e.g., 2022-2024")
        with col5:
            domains = st.text_input("Domains", placeholder="e.g., ML, biology")

        submitted = st.form_submit_button(
            "🚀 Start Research", type="primary", use_container_width=True
        )

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

        # Show spinner while research is running
        with st.spinner("🔬 Research in progress... This may take several minutes..."):
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

    # Get model info (try metadata first, fall back to completion)
    model_full = session.get("metadata", {}).get("model") or comp.get("model", "Unknown")
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
    actual_pdfs = (
        len([f for f in os.listdir(pdfs_dir) if f.endswith(".pdf")])
        if os.path.exists(pdfs_dir)
        else 0
    )
    notes_dir = os.path.join(session["path"], "notes")
    actual_notes = len(os.listdir(notes_dir)) if os.path.exists(notes_dir) else 0

    # Use actual counts, fall back to stats if available
    paper_count = actual_pdfs or stats.get("pdfs_read", stats.get("reads", 0))
    notes_count = actual_notes or stats.get("notes_saved", stats.get("notes", 0))

    # Enhanced metrics display with icons
    cols = st.columns(5)
    with cols[0]:
        model_icon = (
            "🧠"
            if "opus" in model_full.lower()
            else "⚡" if "sonnet" in model_full.lower() else "🚀"
        )
        st.metric(f"{model_icon} Model", model_display)
    with cols[1]:
        duration = comp.get("duration_seconds", 0)
        duration_display = (
            f"{int(duration//60)}m {int(duration%60)}s" if duration >= 60 else f"{int(duration)}s"
        )
        st.metric("⏱️ Duration", duration_display if duration else "—")
    with cols[2]:
        cost = comp.get("cost_usd")
        st.metric("💰 Cost", f"${cost:.3f}" if cost else "—")
    with cols[3]:
        st.metric("📚 Papers", paper_count if paper_count else "—")
    with cols[4]:
        st.metric("📝 Notes", notes_count if notes_count else "—")

    # Tabs
    tab1, tab2, tab3 = st.tabs(["📄 Report", "📚 PDFs", "💬 Ask Questions"])

    with tab1:
        report = get_session_report(session["path"])
        if report:
            st.markdown(report)

            # Email Report Section
            st.markdown("---")
            with st.expander("📧 Send Report via Email", expanded=False):
                # Check if SMTP is configured
                from email_service import EmailConfig

                email_config = EmailConfig.from_env()
                smtp_configured = email_config.is_smtp_configured()

                if smtp_configured:
                    st.markdown("Enter your email address to receive this report:")

                    # Use session-specific key for email input
                    email_key = f"email_input_{session['folder']}"
                    recipient_email = st.text_input(
                        "Your email address",
                        key=email_key,
                        placeholder="your.email@example.com",
                        label_visibility="collapsed",
                    )

                    col1, col2 = st.columns([1, 3])
                    with col1:
                        send_clicked = st.button(
                            "📤 Send Report",
                            key=f"send_email_{session['folder']}",
                            type="primary",
                            use_container_width=True,
                        )

                    if send_clicked:
                        if recipient_email and recipient_email.strip():
                            from email_service import send_email_report

                            with st.spinner("Sending email..."):
                                success, message = send_email_report(
                                    report_content=report,
                                    topic=topic,
                                    recipient=recipient_email.strip(),
                                )

                            if success:
                                st.success(f"✅ {message}")
                            else:
                                st.error(f"❌ {message}")
                        else:
                            st.warning("Please enter your email address")
                else:
                    st.info(
                        "📧 Email sending is not configured. Contact the administrator to enable SMTP settings."
                    )
        else:
            # No report - check if there are notes to display
            notes_dir = os.path.join(session["path"], "notes")
            if os.path.exists(notes_dir) and os.listdir(notes_dir):
                st.info("📋 **Research findings from this session:**")

                # Group notes by type
                findings = []
                summaries = []
                other_notes = []

                for note_file in sorted(os.listdir(notes_dir)):
                    note_path = os.path.join(notes_dir, note_file)
                    try:
                        with open(note_path, "r", encoding="utf-8") as f:
                            note_data = json.load(f)
                            note_data["_filename"] = note_file
                            note_type = note_data.get("type", note_data.get("note_type", "other"))
                            if note_type == "finding":
                                findings.append(note_data)
                            elif note_type == "paper_summary":
                                summaries.append(note_data)
                            else:
                                other_notes.append(note_data)
                    except Exception:
                        pass

                # Display paper summaries first
                if summaries:
                    st.markdown("### 📚 Paper Summaries")
                    for note in summaries:
                        with st.expander(f"📄 {note.get('title', 'Untitled')}", expanded=True):
                            st.markdown(note.get("content", "No content available"))

                            # Source info
                            source = note.get("source", "")
                            if source and source != "N/A":
                                st.markdown(f"**Source:** {source}")

                            # Tags
                            tags = note.get("tags", [])
                            if tags:
                                st.markdown("**Tags:** " + " ".join([f"`{tag}`" for tag in tags]))
                    st.markdown("")

                # Display findings
                if findings:
                    st.markdown("### 💡 Key Findings")
                    for note in findings:
                        with st.expander(f"🔍 {note.get('title', 'Untitled')}", expanded=False):
                            st.markdown(note.get("content", "No content available"))

                            source = note.get("source", "")
                            if source and source != "N/A":
                                st.caption(f"📖 Source: {source}")

                            tags = note.get("tags", [])
                            if tags:
                                st.caption("🏷️ " + " • ".join(tags))
                    st.markdown("")

                # Display other notes
                if other_notes:
                    st.markdown("### 📝 Additional Notes")
                    for note in other_notes:
                        with st.expander(f"📌 {note.get('title', 'Untitled')}", expanded=False):
                            st.markdown(note.get("content", "No content available"))

                            source = note.get("source", "")
                            if source and source != "N/A":
                                st.caption(f"Source: {source}")

            elif paper_count > 0:
                st.info(
                    f"📚 This session has **{paper_count} downloaded PDFs**. View them in the PDFs tab or ask questions about them."
                )
            else:
                st.warning(
                    "⏳ This session appears to be empty or still in progress. Try running a new research query."
                )

    with tab2:
        pdfs = get_session_pdfs(session["path"])
        if not pdfs:
            st.info("📭 No PDFs have been downloaded in this session yet.")
        else:
            st.success(f"📚 **{len(pdfs)} Research Papers Downloaded**")

            # PDF list with better formatting
            for i, pdf in enumerate(pdfs, 1):
                col1, col2, col3 = st.columns([0.5, 4.5, 1])
                with col1:
                    st.markdown(f"**{i}.**")
                with col2:
                    # Clean up PDF name for display
                    display_name = pdf.replace("_", " ").replace(".pdf", "")
                    if len(display_name) > 60:
                        display_name = display_name[:57] + "..."
                    st.markdown(f"📄 {display_name}")
                with col3:
                    pdf_path = get_pdf_path(session["path"], pdf)
                    if pdf_path:
                        with open(pdf_path, "rb") as f:
                            st.download_button(
                                "⬇️ Download", f.read(), pdf, "application/pdf", key=f"dl_{pdf}"
                            )

            # PDF Viewer
            st.markdown("---")
            st.markdown("### 👁️ PDF Viewer")
            selected_pdf = st.selectbox(
                "Select a paper to view:", ["-- Select a PDF --"] + pdfs, key="pdf_viewer_select"
            )
            if selected_pdf and selected_pdf != "-- Select a PDF --":
                pdf_path = get_pdf_path(session["path"], selected_pdf)
                if pdf_path:
                    with open(pdf_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode()
                    st.markdown(
                        f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="700px" style="border: 1px solid #ddd; border-radius: 8px;"></iframe>',
                        unsafe_allow_html=True,
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

                # Show spinner while processing
                with st.spinner("💭 Thinking..."):
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
                                asyncio.set_event_loop_policy(
                                    asyncio.WindowsProactorEventLoopPolicy()
                                )

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

                            return anyio.run(
                                collect_followup,
                                backend="asyncio",
                                backend_options={"use_uvloop": False},
                            )

                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(
                                run_followup_chat, followup, followup_history, sess_path, sess_model
                            )
                            response_container[0] = future.result(timeout=300)

                        placeholder.markdown(response_container[0])

                    except Exception as e:
                        error_details = traceback.format_exc()
                        response_container[0] = f"Error: {str(e)}\n\n```\n{error_details}\n```"
                        placeholder.markdown(response_container[0])

                st.session_state[chat_key].append(
                    {"role": "assistant", "content": response_container[0]}
                )


# =============================================================================
# Footer
# =============================================================================

st.markdown("---")
st.caption("Powered by Claude Agent SDK • Built with Streamlit")
