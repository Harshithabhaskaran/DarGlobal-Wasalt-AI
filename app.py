
import sys
import re
import html
from pathlib import Path

import streamlit as st


# ============================================================
# 1. PROJECT CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent
RAG_DIR = PROJECT_ROOT / "src" / "rag"

if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

from chat import (
    is_comparison_query,
    is_count_query,
    generate_property_answer,
)

from retrieve import (
    SemanticRetriever,
    classify_query,
    is_darglobal_query,
)
from generate import generate_answer


# ============================================================
# 2. PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="DarGlobal | Property Intelligence",
    page_icon="⌂",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# 3. DESIGN SYSTEM
# ============================================================

st.html("""
<style>

@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Playfair+Display:wght@400;500;600;700&display=swap');

:root {
    --bg: #F7F6F2;
    --surface: #FFFFFF;
    --surface-soft: #EEECE4;
    --ink: #202923;
    --green: #294735;
    --green-light: #E4ECE5;
    --gold: #A88952;
    --muted: #59645B;
    --border: #DCD9CE;
}

/* GLOBAL */

.stApp {
    background: var(--bg);
    color: var(--ink);
    font-family: 'DM Sans', sans-serif;
}

[data-testid="stHeader"] {
    background: #F7F6F2;
    border-bottom: 1px solid var(--border);
}

/* Hide Streamlit's development deployment control */
[data-testid="stAppDeployButton"] {
    display: none !important;
}

/* Main page width and spacing */

.block-container {
    max-width: 1240px;
    padding-top: 0.8rem;
    padding-bottom: 9rem !important;
}

/* Keep sufficient scroll space above the bottom chat input */

[data-testid="stMainBlockContainer"] {
    padding-bottom: 9rem !important;
    scroll-padding-bottom: 9rem;
}

h1, h2, h3 {
    font-family: 'Playfair Display', serif !important;
    color: var(--ink) !important;
}

p, li, label {
    font-family: 'DM Sans', sans-serif;
    color: var(--ink);
}

/* ANIMATIONS */

@keyframes fadeUp {
    from {
        opacity: 0;
        transform: translateY(12px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

/* SIDEBAR */

[data-testid="stSidebar"] {
    background: #EEECE4;
    border-right: 1px solid #D6D2C6;
    min-width: 270px !important;
    max-width: 270px !important;
}

[data-testid="stSidebar"] > div:first-child {
    padding-top: 1.1rem;
}

[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    padding-left: 1.1rem;
    padding-right: 1.1rem;
}

.sidebar-brand {
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 1.8px;
    color: #294735;
    animation: fadeIn 0.6s ease both;
}

.sidebar-heading {
    font-family: 'Playfair Display', serif;
    font-size: 27px;
    line-height: 1.2;
    font-weight: 600;
    margin-top: 17px;
    color: #202923;
    animation: fadeUp 0.6s ease both;
}

.sidebar-caption {
    font-size: 12px;
    color: #4F5B52;
    line-height: 1.65;
    margin-top: 9px;
}

.sidebar-section {
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 1.5px;
    color: #806333;
    margin-top: 23px;
    margin-bottom: 10px;
    text-transform: uppercase;
}

/* SIDEBAR BUTTONS */

[data-testid="stSidebar"] .stButton > button {
    background: #F9F8F4;
    border: 1px solid #D9D5C9;
    color: #27382D;
    font-size: 11px;
    font-weight: 600;
    text-align: left;
    border-radius: 9px;
    min-height: 41px;
    padding: 8px 10px;
    transition: all 0.2s ease;
}

[data-testid="stSidebar"] .stButton > button:hover {
    background: #DDE8DE;
    border-color: #91A895;
    color: #23432F;
    transform: translateX(2px);
}

.sidebar-divider {
    border-top: 1px solid #D7D2C5;
    margin: 19px 0 13px 0;
}

/* TOP HEADER */

.topbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    width: 100%;
    background: #EAE8DF;
    border: 1px solid #CFCABB;
    border-radius: 11px;
    padding: 12px 19px;
    margin-bottom: 19px;
    animation: fadeUp 0.5s ease both;
}

.wordmark {
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 2px;
    color: #203C2B;
}

.topbar-right {
    font-size: 10px;
    font-weight: 800;
    color: #294735;
    letter-spacing: 1px;
}

.online-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    background: #3F7651;
    border-radius: 50%;
    margin-right: 7px;
}

/* HERO */

.hero {
    background: linear-gradient(
        115deg,
        #FFFFFF 0%,
        #F5F3EA 62%,
        #E9E2D2 100%
    );
    border: 1px solid #DCD8CC;
    border-radius: 17px;
    padding: 25px 30px;
    position: relative;
    overflow: hidden;
    margin-bottom: 17px;
    animation: fadeUp 0.65s ease both;
}

.hero:after {
    content: "⌂";
    position: absolute;
    right: 35px;
    top: 2px;
    font-family: 'Playfair Display', serif;
    font-size: 145px;
    line-height: 1;
    color: rgba(168,137,82,0.12);
    pointer-events: none;
}

.eyebrow {
    font-size: 9px;
    letter-spacing: 2px;
    font-weight: 800;
    text-transform: uppercase;
    color: #806333;
    margin-bottom: 9px;
}

.hero-title {
    font-family: 'Playfair Display', serif;
    font-size: clamp(29px, 3.4vw, 42px);
    font-weight: 600;
    letter-spacing: -0.8px;
    line-height: 1.18;
    color: #202923;
    max-width: 730px;
    position: relative;
    z-index: 1;
}

.hero-title span {
    color: #294735;
    font-style: italic;
}

.hero-description {
    font-size: 12px;
    line-height: 1.65;
    color: #4F5B52;
    max-width: 610px;
    margin-top: 10px;
    position: relative;
    z-index: 1;
}

.hero-footer {
    display: flex;
    gap: 19px;
    flex-wrap: wrap;
    margin-top: 15px;
    font-size: 10px;
    font-weight: 700;
    color: #405845;
    letter-spacing: 0.3px;
}

/* SECTION LABELS */

.section-heading {
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 1.8px;
    text-transform: uppercase;
    color: #806333;
    margin-top: 17px;
    margin-bottom: 8px;
}

.section-subtitle {
    color: #59635C;
    font-size: 12px;
    margin-bottom: 13px;
}

/* FEATURE CARDS */

.feature-card {
    background: #FFFFFF;
    border: 1px solid #DCD9CE;
    border-radius: 13px;
    padding: 15px;
    min-height: 112px;
    transition: all 0.25s ease;
    animation: fadeUp 0.6s ease both;
}

.feature-card:hover {
    transform: translateY(-3px);
    border-color: #B9AA8B;
    box-shadow: 0 8px 18px rgba(42,59,45,0.08);
}

.feature-icon {
    font-size: 19px;
    margin-bottom: 8px;
}

.feature-name {
    font-size: 12px;
    font-weight: 700;
    color: #25352A;
}

.feature-desc {
    font-size: 10px;
    color: #5D665F;
    margin-top: 5px;
    line-height: 1.5;
}

/* BUTTONS */

.stButton > button {
    border-radius: 9px;
    border: 1px solid #D6D2C7;
    background: #FFFFFF;
    color: #26362B;
    font-family: 'DM Sans', sans-serif;
    font-size: 11px;
    font-weight: 600;
    padding: 9px 12px;
    min-height: 41px;
    transition: all 0.2s ease;
}

.stButton > button:hover {
    background: #E5ECE5;
    border-color: #A8B9A9;
    color: #294735;
    transform: translateY(-1px);
    box-shadow: 0 4px 10px rgba(41,71,53,0.08);
}

.stButton > button:active {
    background: #D7E4D9;
    border-color: #78947D;
}

/* CHAT MESSAGES */

[data-testid="stChatMessage"] {
    background: #FFFFFF;
    border: 1px solid #DCD9CE;
    border-radius: 14px;
    padding: 15px 17px;
    margin-bottom: 11px;
    animation: fadeUp 0.35s ease both;
}

/* CHAT INPUT
   Keep Streamlit's native bottom-docked input.
   Do not manually apply position: fixed. */

[data-testid="stChatInput"] {
    border-radius: 13px;
    border: 1px solid #CFCABB;
    background: #FFFFFF;
    box-shadow: 0 4px 16px rgba(32,41,35,0.08);
}

[data-testid="stChatInput"] textarea {
    font-family: 'DM Sans', sans-serif;
    font-size: 13px;
    color: #202923;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: #737B73;
    opacity: 1;
}

[data-testid="stChatInput"] button {
    background: #294735;
    color: #FFFFFF;
    border-radius: 9px;
    transition: all 0.2s ease;
}

[data-testid="stChatInput"] button:hover {
    background: #1F3829;
    color: #FFFFFF;
}

[data-testid="stBottomBlockContainer"] {
    background: rgba(247,246,242,0.97);
    padding-top: 0.5rem;
    padding-bottom: 0.8rem;
}

/* PROPERTY CARDS */

.property-card {
    background: #FFFFFF;
    border: 1px solid #DCD9CE;
    border-radius: 14px;
    padding: 17px;
    margin: 9px 0 5px 0;
    animation: fadeUp 0.45s ease both;
    transition: all 0.25s ease;
}

.property-card:hover {
    transform: translateY(-2px);
    border-color: #B8AA8D;
    box-shadow: 0 7px 18px rgba(38,55,42,0.08);
}

.property-card-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
}

.property-tag {
    background: #E4ECE5;
    color: #294735;
    padding: 5px 9px;
    border-radius: 5px;
    font-size: 9px;
    font-weight: 800;
    letter-spacing: 1px;
}

.property-number {
    color: #687068;
    font-size: 10px;
    letter-spacing: 1px;
}

.property-title {
    font-family: 'Playfair Display', serif;
    font-size: 18px;
    font-weight: 600;
    line-height: 1.4;
    color: #202923;
    margin-top: 10px;
}

.property-price {
    font-size: 21px;
    font-weight: 800;
    color: #294735;
    margin-top: 7px;
}

.property-location {
    color: #58635B;
    font-size: 11px;
    margin-top: 6px;
}

.property-divider {
    height: 1px;
    background: #E3E0D7;
    margin: 13px 0;
}

.property-details {
    display: flex;
    gap: 20px;
    flex-wrap: wrap;
    color: #4E5B51;
    font-size: 11px;
    line-height: 1.7;
}

.property-detail strong {
    display: block;
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #687068;
    margin-bottom: 2px;
}

/* SOURCES */

[data-testid="stExpander"] {
    border: 1px solid #DCD9CE;
    border-radius: 10px;
    background: #FFFFFF;
    margin-top: 10px;
}

a {
    color: #294735 !important;
    font-weight: 600;
}

hr {
    border-color: #DCD9CE !important;
}

/* FOOTER */

.footer {
    text-align: center;
    border-top: 1px solid #DCD9CE;
    padding-top: 15px;
    margin-top: 30px;
    color: #59635C;
    font-size: 9px;
    letter-spacing: 1.4px;
    line-height: 2;
}

/* TABLET AND MOBILE */

@media (max-width: 900px) {
    .block-container {
        padding-left: 1.2rem;
        padding-right: 1.2rem;
    }

    .hero {
        padding: 23px;
    }

    .hero-title {
        font-size: 34px;
    }
}

@media (max-width: 700px) {
    .block-container {
        padding-left: 0.9rem;
        padding-right: 0.9rem;
        padding-bottom: 10rem !important;
    }

    [data-testid="stMainBlockContainer"] {
        padding-bottom: 10rem !important;
    }

    .hero {
        padding: 20px 17px;
        margin-bottom: 13px;
    }

    .hero:after {
        right: 5px;
        font-size: 95px;
    }

    .hero-title {
        font-size: 29px;
    }

    .hero-description {
        font-size: 11px;
        max-width: 90%;
    }

    .hero-footer {
        gap: 10px;
        font-size: 9px;
    }

    .topbar {
        padding: 11px;
        margin-bottom: 14px;
    }

    .wordmark {
        font-size: 10px;
        letter-spacing: 1px;
    }

    .topbar-right {
        font-size: 8px;
        letter-spacing: 0.5px;
    }

    .feature-card {
        min-height: 100px;
    }

    [data-testid="stChatMessage"] {
        padding: 12px;
    }

    .property-details {
        gap: 13px;
    }
}

/* ACCESSIBILITY */

@media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
        scroll-behavior: auto !important;
    }
}

</style>
""")


# ============================================================
# 4. LOAD RETRIEVER
# ============================================================

@st.cache_resource(show_spinner="Loading property intelligence...")
def load_retriever():
    return SemanticRetriever()


# ============================================================
# 5. QUERY PROCESSING
# ============================================================

def process_query(query, retriever):

    filters = classify_query(query)

    comparison_query = is_comparison_query(query)
    count_query = is_count_query(query)

    # Identify DarGlobal queries using the module-level function.
    darglobal_query = is_darglobal_query(query)

    # --------------------------------------------------------
    # 1. DARGLOBAL QUESTIONS
    # Use semantic retrieval so project comparisons and
    # DarGlobal-specific questions reach the hybrid generator.
    # --------------------------------------------------------

    if darglobal_query:

        results = retriever.search(
            query,
            top_k=10
        )

    # --------------------------------------------------------
    # 2. WASALT PROPERTY COUNTS AND COMPARISONS
    # Retrieve all matching properties instead of only top 5.
    # --------------------------------------------------------

    elif comparison_query or count_query:

        structured_query = query

        if filters.get("page_type") != "property":
            structured_query += " properties"

        results = retriever.search_all_properties(
            structured_query
        )

    # --------------------------------------------------------
    # 3. GENERAL QUESTIONS
    # Normal semantic retrieval.
    # --------------------------------------------------------

    else:

        results = retriever.search(
            query,
            top_k=5
        )

    if not results:

        return (
            "I couldn't find matching information in the collected dataset.",
            [],
            [],
        )

    answer = None

    # Deterministic property answers apply only to Wasalt.
    if not darglobal_query and (comparison_query or count_query):

        answer = generate_property_answer(
            query,
            results
        )

    # DarGlobal questions and general questions use
    # the hybrid answer generator.
    if answer is None:

        answer = generate_answer(
            query,
            results
        )

    # --------------------------------------------------------
    # COLLECT UNIQUE SOURCES
    # --------------------------------------------------------

    sources = []
    seen_urls = set()

    for result in results:

        source_url = result.get("source_url")

        if source_url and source_url not in seen_urls:

            seen_urls.add(source_url)

            sources.append({
                "title": result.get("title", "Source"),
                "url": source_url,
            })

    return answer, sources, results

# ============================================================
# 6. PROPERTY CARD HELPERS
# ============================================================

def format_currency(price, currency):

    if price is None:
        return "Price unavailable"

    try:
        number = float(
            re.sub(r"[^\d.]", "", str(price))
        )

        formatted = f"{number:,.0f}"

    except (ValueError, TypeError):
        formatted = str(price)

    currency = str(currency or "").replace("/سنة", "/year")

    return f"{formatted} {currency}".strip()


def render_property_cards(results):

    properties = [
        item for item in results
        if item.get("page_type") == "property"
    ]

    if not properties:
        return

    st.html(f"""
    <div class="section-heading">
        PROPERTY DISCOVERIES
    </div>
    <div class="section-subtitle">
        {len(properties)} retrieved listing(s) from the collected knowledge base
    </div>
    """)

    for index, result in enumerate(properties, start=1):

        metadata = result.get("property_metadata") or {}

        title = html.escape(
            str(result.get("title") or "Property listing")
        )

        city = html.escape(
            str(metadata.get("city") or "Location unavailable")
        )

        district = metadata.get("district")

        location = (
            f"{html.escape(str(district))}, {city}"
            if district else city
        )

        bedrooms = metadata.get("bedrooms")
        bathrooms = metadata.get("bathrooms")
        area = metadata.get("area")

        intent = html.escape(
            str(result.get("listing_intent") or "PROPERTY")
        )

        price = html.escape(
            format_currency(
                metadata.get("price"),
                metadata.get("currency"),
            )
        )

        bedroom_value = (
            html.escape(str(bedrooms))
            if bedrooms is not None else "—"
        )

        bathroom_value = (
            html.escape(str(bathrooms))
            if bathrooms is not None else "—"
        )

        area_value = (
            html.escape(str(area)) + " SQM"
            if area is not None else "Not specified"
        )

        animation_delay = min(index * 0.08, 0.5)

        st.html(f"""
        <div class="property-card"
             style="animation-delay:{animation_delay}s;">

            <div class="property-card-top">
                <span class="property-tag">{intent}</span>
                <span class="property-number">LISTING {index:02d}</span>
            </div>

            <div class="property-title">{title}</div>

            <div class="property-price">{price}</div>

            <div class="property-location">
                ↗ &nbsp; {location}
            </div>

            <div class="property-divider"></div>

            <div class="property-details">

                <div class="property-detail">
                    <strong>Bedrooms</strong>
                    {bedroom_value}
                </div>

                <div class="property-detail">
                    <strong>Bathrooms</strong>
                    {bathroom_value}
                </div>

                <div class="property-detail">
                    <strong>Built-up area</strong>
                    {area_value}
                </div>

            </div>

        </div>
        """)

        source_url = result.get("source_url")

        if source_url:
            safe_url = html.escape(str(source_url), quote=True)

            st.markdown(
                f"[View original property listing ↗]({safe_url})"
            )


# ============================================================
# 7. SESSION STATE
# ============================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "suggested_query" not in st.session_state:
    st.session_state.suggested_query = None


# ============================================================
# 8. SIDEBAR
# ============================================================

with st.sidebar:

    st.html("""
    <div class="sidebar-brand">
        DARGLOBAL &nbsp; × &nbsp; WASALT
    </div>

    <div class="sidebar-heading">
        Property<br>Intelligence.
    </div>

    <div class="sidebar-caption">
        Discover properties and explore real estate opportunities
        through conversational AI.
    </div>

    <div class="sidebar-section">
        QUICK DISCOVERY
    </div>
    """)

    if st.button(
        "⌂  Apartments for rent in Riyadh",
        use_container_width=True,
    ):
        st.session_state.suggested_query = (
            "Show me apartments for rent in Riyadh"
        )
        st.rerun()

    if st.button(
        "◇  Cheapest apartment in Jeddah",
        use_container_width=True,
    ):
        st.session_state.suggested_query = (
            "Find the cheapest apartment for sale in Jeddah"
        )
        st.rerun()

    if st.button(
        "▤  Count apartments for sale",
        use_container_width=True,
    ):
        st.session_state.suggested_query = (
            "How many apartments are for sale in Jeddah?"
        )
        st.rerun()

    if st.button(
        "✳  Compare property prices",
        use_container_width=True,
    ):
        st.session_state.suggested_query = (
            "Compare the cheapest and most expensive apartments for sale in Jeddah"
        )
        st.rerun()

    st.html("""
    <div class="sidebar-divider"></div>
    """)

    if st.button(
        "↺  Start a new conversation",
        use_container_width=True,
    ):

        st.session_state.messages = []
        st.session_state.suggested_query = None

        st.rerun()


# ============================================================
# 9. TOP BAR
# ============================================================

st.html("""
<div class="topbar">

    <div class="wordmark">
        DARGLOBAL &nbsp; × &nbsp; WASALT
    </div>

    <div class="topbar-right">
        <span class="online-dot"></span>
        PROPERTY INTELLIGENCE
    </div>

</div>
""")


# ============================================================
# 10. HERO SECTION
# ============================================================

st.html("""
<div class="hero">

    <div class="eyebrow">
        REAL ESTATE · REIMAGINED
    </div>

    <div class="hero-title">
        Find more than a property.<br>
        <span>Find your next opportunity.</span>
    </div>

    <div class="hero-description">
        Explore property listings, uncover market insights,
        and compare real estate opportunities through a
        conversational AI experience powered by the
        collected property knowledge base.
    </div>

    <div class="hero-footer">
        <span>⌂ &nbsp; PROPERTY DISCOVERY</span>
        <span>◇ &nbsp; PRICE INTELLIGENCE</span>
        <span>✳ &nbsp; AI-POWERED SEARCH</span>
    </div>

</div>
""")


# ============================================================
# 11. LOAD KNOWLEDGE BASE
# ============================================================

try:

    retriever = load_retriever()

except Exception as error:

    st.error(
        f"Unable to load the knowledge base: {error}"
    )

    st.stop()


# ============================================================
# 12. WELCOME SCREEN
# ============================================================

if not st.session_state.messages:

    st.html("""
    <div class="section-heading">
        YOUR PERSONAL PROPERTY ASSISTANT
    </div>

    <h2 style="
        font-family:'Playfair Display',serif;
        font-size:25px;
        font-weight:600;
        color:#202923;
        margin-top:0;
        margin-bottom:6px;
    ">
        What would you like to discover?
    </h2>

    <p style="
        color:#59635B;
        font-size:12px;
        margin-bottom:15px;
    ">
        Start with one of these suggestions, or ask your own question below.
    </p>
    """)

    feature1, feature2, feature3 = st.columns(3)

    with feature1:

        st.html("""
        <div class="feature-card">
            <div class="feature-icon">⌂</div>
            <div class="feature-name">Discover properties</div>
            <div class="feature-desc">
                Explore listings across locations and property types.
            </div>
        </div>
        """)

    with feature2:

        st.html("""
        <div class="feature-card" style="animation-delay:0.1s;">
            <div class="feature-icon">◇</div>
            <div class="feature-name">Compare opportunities</div>
            <div class="feature-desc">
                Identify the lowest and highest listing prices.
            </div>
        </div>
        """)

    with feature3:

        st.html("""
        <div class="feature-card" style="animation-delay:0.2s;">
            <div class="feature-icon">▤</div>
            <div class="feature-name">Explore insights</div>
            <div class="feature-desc">
                Understand listing counts and platform information.
            </div>
        </div>
        """)

    st.html("""
    <div class="section-heading">
        SUGGESTED QUESTIONS
    </div>
    """)

    left, right = st.columns(2)

    with left:

        if st.button(
            "⌂  What rental properties are available in Riyadh?",
            use_container_width=True,
        ):

            st.session_state.suggested_query = (
                "What rental properties are available in Riyadh?"
            )

            st.rerun()

        if st.button(
            "◇  Cheapest apartment for sale in Jeddah",
            use_container_width=True,
        ):

            st.session_state.suggested_query = (
                "Cheapest apartment for sale in Jeddah"
            )

            st.rerun()

    with right:

        if st.button(
            "▤  How many apartments are for sale in Jeddah?",
            use_container_width=True,
        ):

            st.session_state.suggested_query = (
                "How many apartments are for sale in Jeddah?"
            )

            st.rerun()

        if st.button(
            "✳  What is Wasalt and what services does it provide?",
            use_container_width=True,
        ):

            st.session_state.suggested_query = (
                "What is Wasalt and what services does it provide?"
            )

            st.rerun()


# ============================================================
# 13. DISPLAY CHAT HISTORY
# ============================================================

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])

        if message["role"] == "assistant":

            if message.get("property_results"):

                render_property_cards(
                    message["property_results"]
                )

            if message.get("sources"):

                with st.expander("Explore retrieved sources"):

                    for source in message["sources"]:

                        st.markdown(
                            f"- [{source['title']}]({source['url']})"
                        )


# ============================================================
# 14. CHAT INPUT
# ============================================================

user_query = st.chat_input(
    "Ask about properties, locations, prices or real estate..."
)

if st.session_state.suggested_query:

    user_query = st.session_state.suggested_query

    st.session_state.suggested_query = None


# ============================================================
# 15. PROCESS QUESTION
# ============================================================

if user_query:

    st.session_state.messages.append({
        "role": "user",
        "content": user_query,
    })

    with st.chat_message("user"):
        st.markdown(user_query)

    with st.chat_message("assistant"):

        try:

            with st.spinner("Searching property intelligence..."):

                answer, sources, results = process_query(
                    user_query,
                    retriever,
                )

            st.markdown(answer)

            property_results = [
                item for item in results
                if item.get("page_type") == "property"
            ]

            if property_results:

                render_property_cards(
                    property_results
                )

            if sources:

                with st.expander("Explore retrieved sources"):

                    for source in sources:

                        st.markdown(
                            f"- [{source['title']}]({source['url']})"
                        )

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer,
                "sources": sources,
                "property_results": property_results,
            })

        except Exception as error:

            error_message = (
                f"Unable to process your question: {error}"
            )

            st.error(error_message)

            st.session_state.messages.append({
                "role": "assistant",
                "content": error_message,
                "sources": [],
                "property_results": [],
            })


# ============================================================
# 16. FOOTER
# ============================================================

st.html("""
<div class="footer">
    DARGLOBAL × WASALT<br>
    INTELLIGENT REAL ESTATE DISCOVERY<br>
    INFORMATION BASED ON THE COLLECTED KNOWLEDGE BASE
</div>
""")
