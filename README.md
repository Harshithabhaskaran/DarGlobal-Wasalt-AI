# DarGlobal × Wasalt AI – Property Intelligence Chatbot

An AI-powered real estate discovery assistant that answers questions about DarGlobal developments and Wasalt property listings using Retrieval-Augmented Generation (RAG).

**Live Application:** https://darglobal-wasalt.streamlit.app/  
**GitHub Repository:** https://github.com/Harshithabhaskaran/DarGlobal-Wasalt-AI

---

## 1. Project Overview

DarGlobal × Wasalt AI is a conversational real estate intelligence application designed to help users explore property listings, discover real estate developments, compare opportunities, and retrieve relevant market information.

The application combines web data collection, semantic search, vector embeddings, and Large Language Model (LLM) generation to provide context-grounded responses with source references.

## 2. Key Features

- **Conversational AI:** Ask natural-language questions about properties and developments.
- **Retrieval-Augmented Generation:** Retrieves relevant information from the collected knowledge base before generating responses.
- **Semantic Search:** Uses Sentence Transformers to retrieve contextually relevant documents.
- **Property Discovery:** Retrieves property listings based on location, property type, price, bedrooms, and other available attributes.
- **DarGlobal Intelligence:** Provides information about developments, locations, project milestones, and reported Gross Development Values.
- **Property Comparison:** Supports comparisons between developments and locations.
- **Source References:** Displays source links and relevant data notes.
- **Interactive Interface:** Premium Streamlit-based user interface.
- **Cloud Deployment:** Publicly accessible Streamlit Community Cloud application.
- **Docker Support:** Containerized application for reproducible deployment.

## 3. Technology Stack

| Component | Technology |
|---|---|
| Programming Language | Python 3.11 |
| Frontend | Streamlit |
| Web Scraping | Requests, BeautifulSoup4 |
| HTML Parsing | lxml |
| Data Processing | Python, Pandas, NumPy |
| Embeddings | Sentence Transformers |
| Embedding Model | all-MiniLM-L6-v2 |
| Retrieval | Custom semantic vector search |
| LLM Integration | OpenRouter API |
| Environment Management | python-dotenv |
| Containerization | Docker |
| Version Control | Git and GitHub |
| Cloud Deployment | Streamlit Community Cloud |

## 4. System Architecture

```text
Public Data Sources
       |
       v
Web Scraping and Collection
       |
       v
Raw JSON Documents
       |
       v
Data Cleaning and Preprocessing
       |
       v
Document Chunking
       |
       v
Sentence Transformer Embeddings
       |
       v
Vector Index (NumPy)
       |
       v
User Query
       |
       v
Semantic Retrieval
       |
       v
Relevant Context + Source References
       |
       v
OpenRouter LLM
       |
       v
Grounded Response
       |
       v
Streamlit Chat Interface
```

## 5. Knowledge Base

The collected dataset contains:

| Dataset component | Count |
|---|---:|
| Wasalt raw source pages | 35 |
| DarGlobal supplementary official filing | 1 |
| Total raw source documents | 36 |
| Cleaned documents | 35 |
| Document chunks | 402 |
| Embedding dimensions | 384 |
| Indexed vectors | 402 |

The Wasalt dataset includes property listings and related real estate information. The DarGlobal supplementary source contains information from its FY2025 results announcement.

**Data coverage note:** Direct DarGlobal website access was restricted during collection. Therefore, the DarGlobal project information was supplemented using its official FY2025 results announcement hosted by the FCA National Storage Mechanism. The collected dataset should not be interpreted as a complete scrape of either company's entire website or portfolio.

## 6. Project Structure

```text
DarGlobal-Wasalt-AI/
│
├── app.py
├── Dockerfile
├── requirements.txt
├── .dockerignore
├── .gitignore
│
├── data/
│   └── processed/
│       └── vector_index/
│           ├── embeddings.npy
│           └── metadata.json
│
└── src/
    ├── scraper/
    │   └── Web scraping modules
    │
    └── rag/
        ├── prepare_data.py
        ├── build_index.py
        ├── retrieve.py
        ├── generate.py
        └── chat.py
```

## 7. Local Installation and Execution

### Prerequisites

- Python 3.11
- Git
- OpenRouter API key

### Clone the repository

```bash
git clone https://github.com/Harshithabhaskaran/DarGlobal-Wasalt-AI.git
cd DarGlobal-Wasalt-AI
```

### Create a virtual environment

Windows:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Configure environment variables

Create a `.env` file in the project root:

```env
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_MODEL=openrouter/free
```

Never commit API keys or other secrets to GitHub.

### Run the application

```bash
streamlit run app.py
```

Open the local URL displayed in the terminal, normally:

```text
http://localhost:8501
```

## 8. Docker Deployment

Build the Docker image:

```bash
docker build -t darglobal-wasalt-ai .
```

Run the container:

```bash
docker run -d \
  --name darglobal-wasalt-ai \
  -p 8501:8501 \
  --env-file .env \
  darglobal-wasalt-ai
```

Open:

```text
http://localhost:8501
```

To inspect application logs:

```bash
docker logs darglobal-wasalt-ai
```

## 9. Cloud Deployment

The application is deployed using Streamlit Community Cloud.

**Live URL:** https://darglobal-wasalt.streamlit.app/

OpenRouter credentials are configured through Streamlit Cloud Secrets rather than being stored in the public repository.

Example Secrets configuration:

```toml
OPENROUTER_API_KEY = "your_api_key"
OPENROUTER_MODEL = "openrouter/free"
```

## 10. Example Queries

Try these questions in the live application:

1. Tell me about Trump Plaza in Jeddah.
2. Show me apartments for rent in Riyadh.
3. Compare DarGlobal developments in Riyadh and Jeddah.
4. Find one-bedroom apartments in Riyadh.
5. What are the major DarGlobal development announcements?

## 11. Data Sources

- [DarGlobal Official Website](https://www.darglobal.co.uk/)
- [Wasalt Property Platform](https://wasalt.sa/en)
- [DarGlobal FY2025 Results Announcement – FCA National Storage Mechanism](https://data.fca.org.uk/artefacts/NSM/RNS/72dab3cd-9922-4b16-9e31-9f48b1d2a5d2.html)

Property availability and project milestones should be independently verified with the original source. The application reflects its collected dataset and does not guarantee real-time listing availability or construction progress.

## 12. Future Enhancements

- Expand the knowledge base with additional verified property and development sources.
- Implement scheduled data refresh and indexing.
- Improve filtering and property recommendation capabilities.
- Add richer market analytics and geographical visualizations.
- Expand evaluation of retrieval relevance and answer quality.

---

## Author

**Harshitha Bhaskaran**  
M.Tech – Computer Science and Engineering (AI & ML)

GitHub: https://github.com/Harshithabhaskaran

**Project:** DarGlobal × Wasalt – AI-Powered Property Intelligence Chatbot
