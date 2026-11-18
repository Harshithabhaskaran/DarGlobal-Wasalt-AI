
import json
import re
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer


# --------------------------------------------------
# PATHS
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INDEX_DIR = PROJECT_ROOT / "data" / "processed" / "vector_index"

EMBEDDINGS_FILE = INDEX_DIR / "embeddings.npy"
METADATA_FILE = INDEX_DIR / "metadata.json"


# --------------------------------------------------
# MODEL CONFIGURATION
# --------------------------------------------------

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

DEFAULT_TOP_K = 5
MIN_SIMILARITY = 0.20
DARGLOBAL_MIN_SIMILARITY = 0.08
LEXICAL_BOOST = 0.12


# --------------------------------------------------
# NORMALIZATION
# --------------------------------------------------

NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10,
}

CITY_ALIASES = {
    "riyadh": ["riyadh"],
    "jeddah": ["jeddah"],
    "khobar": ["khobar", "al khobar"],
    "dammam": ["dammam", "al dammam", "aldammam"],
}

PROPERTY_TYPE_ALIASES = {
    "apartment": ["apartment", "apartments", "flat", "flats"],
    "villa": ["villa", "villas"],
    "house": ["house", "houses"],
    "townhouse": ["townhouse", "townhouses"],
    "land": ["land", "plot", "plots"],
}


# --------------------------------------------------
# SOURCE CLASSIFICATION
# --------------------------------------------------

DARGLOBAL_KEYWORDS = [
    "darglobal",
    "dar global",
    "dar global plc",
]

WASALT_KEYWORDS = [
    "wasalt",
]

PROJECT_ALIASES = [
    "trump plaza",
    "trump tower",
    "rayana",
    "neptune villas",
    "neptune",
    "amaya",
    "wadi safar",
    "aida",
    "the astera",
    "d villas",
    "jumeirah golf estates",
    "trump international hotel",
    "trump international golf club",
    "simaisima villas",
    "great escape",
    "da vinci tower",
]


STOPWORDS = {
    "a", "an", "and", "are", "about", "at", "be", "by",
    "can", "compare", "describe", "do", "does", "for",
    "from", "give", "has", "have", "how", "i", "in",
    "information", "is", "it", "me", "of", "on", "or",
    "please", "show", "tell", "the", "their", "them",
    "there", "these", "this", "to", "was", "what",
    "were", "which", "with", "would", "you", "your",
    "projects", "project", "developments", "development",
}


def normalize_text(value):

    if value is None:
        return ""

    value = str(value).lower().strip()
    value = re.sub(r"[_\-]+", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value


def tokenize(value):

    tokens = re.findall(
        r"\b[a-z0-9]+\b",
        normalize_text(value)
    )

    return {
        token for token in tokens
        if token not in STOPWORDS and len(token) > 1
    }


def is_darglobal_query(query):

    normalized_query = normalize_text(query)

    # Explicit company reference.
    if any(
        keyword in normalized_query
        for keyword in DARGLOBAL_KEYWORDS
    ):
        return True

    # Recognise project names even when the user
    # does not explicitly mention DarGlobal.
    if any(
        project in normalized_query
        for project in PROJECT_ALIASES
    ):
        return True

    return False


def is_wasalt_query(query):

    normalized_query = normalize_text(query)

    return any(
        keyword in normalized_query
        for keyword in WASALT_KEYWORDS
    )


def normalize_city(city):

    city = normalize_text(city)

    if not city:
        return None

    for standard_name, aliases in CITY_ALIASES.items():

        for alias in aliases:

            if alias in city:
                return standard_name

    return city


def normalize_bedrooms(value):

    if value is None:
        return None

    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def normalize_property_type(value):

    value = normalize_text(value)

    if not value:
        return None

    for standard_name, aliases in PROPERTY_TYPE_ALIASES.items():

        if value in aliases:
            return standard_name

    return value


# --------------------------------------------------
# QUERY EXTRACTION
# --------------------------------------------------

def extract_city(query):

    normalized_query = normalize_text(query)

    for standard_name, aliases in CITY_ALIASES.items():

        for alias in aliases:

            pattern = r"\b" + re.escape(alias) + r"\b"

            if re.search(pattern, normalized_query):
                return standard_name

    return None


def extract_bedrooms(query):

    normalized_query = normalize_text(query)

    number_pattern = (
        r"(1|2|3|4|5|6|7|8|9|10|"
        r"one|two|three|four|five|six|seven|eight|nine|ten)"
    )

    pattern = (
        r"\b" + number_pattern +
        r"\s*[- ]?\s*(?:bedrooms?|beds)\b"
    )

    match = re.search(pattern, normalized_query)

    if not match:
        return None

    value = match.group(1)

    if value in NUMBER_WORDS:
        return NUMBER_WORDS[value]

    return int(value)


def extract_property_type(query):

    normalized_query = normalize_text(query)

    for standard_name, aliases in PROPERTY_TYPE_ALIASES.items():

        for alias in aliases:

            pattern = r"\b" + re.escape(alias) + r"\b"

            if re.search(pattern, normalized_query):
                return standard_name

    return None


# --------------------------------------------------
# QUERY CLASSIFICATION
# --------------------------------------------------

def classify_query(query):

    normalized_query = normalize_text(query)

    rent_keywords = [
        "rent", "rental", "renting", "lease",
        "to let", "for lease", "monthly rent",
        "yearly rent",
    ]

    sale_keywords = [
        "sale", "sell", "buy", "purchase",
        "buying", "for sale",
    ]

    property_keywords = [
        "property", "properties", "apartment",
        "apartments", "villa", "villas",
        "house", "houses", "bedroom", "bedrooms",
        "real estate", "listing", "listings",
        "sqm", "square meter", "townhouse", "land",
    ]

    has_rent = any(
        keyword in normalized_query
        for keyword in rent_keywords
    )

    has_sale = any(
        keyword in normalized_query
        for keyword in sale_keywords
    )

    has_property = any(
        keyword in normalized_query
        for keyword in property_keywords
    )

    city = extract_city(query)
    bedrooms = extract_bedrooms(query)
    property_type = extract_property_type(query)

    listing_intent = None

    if has_rent and not has_sale:
        listing_intent = "RENT"

    elif has_sale and not has_rent:
        listing_intent = "SALE"

    is_property_query = any([
        has_property,
        city is not None,
        bedrooms is not None,
        property_type is not None,
        listing_intent is not None,
    ])

    return {
        "page_type": "property" if is_property_query else None,
        "listing_intent": listing_intent,
        "city": city,
        "bedrooms": bedrooms,
        "property_type": property_type,
    }


# --------------------------------------------------
# SEMANTIC RETRIEVER
# --------------------------------------------------

class SemanticRetriever:

    def __init__(self):

        print("Loading semantic search index...")

        if not EMBEDDINGS_FILE.exists():
            raise FileNotFoundError(
                f"Embeddings not found: {EMBEDDINGS_FILE}"
            )

        if not METADATA_FILE.exists():
            raise FileNotFoundError(
                f"Metadata not found: {METADATA_FILE}"
            )

        self.embeddings = np.load(
            EMBEDDINGS_FILE
        ).astype(np.float32)

        with open(
            METADATA_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            metadata = json.load(file)

        self.chunks = metadata["chunks"]

        if len(self.chunks) != self.embeddings.shape[0]:

            raise ValueError(
                "Embedding and metadata counts do not match."
            )

        self.embedding_dimension = self.embeddings.shape[1]

        print("\nLoading embedding model...")

        self.model = SentenceTransformer(MODEL_NAME)

        print("\nRetriever ready.")
        print("Total chunks:", len(self.chunks))
        print("Embedding dimensions:", self.embedding_dimension)

    # --------------------------------------------------
    # SOURCE FILTERING
    # --------------------------------------------------

    def matches_source_filter(self, chunk, query):

        website = normalize_text(chunk.get("website"))

        if is_darglobal_query(query):
            return website == "darglobal"

        if is_wasalt_query(query):
            return website == "wasalt"

        return True

    # --------------------------------------------------
    # PROPERTY FILTERING
    # --------------------------------------------------

    def matches_property_filters(self, chunk, filters):

        if normalize_text(chunk.get("page_type")) != "property":
            return False

        required_intent = filters["listing_intent"]

        if required_intent:

            actual_intent = str(
                chunk.get("listing_intent") or ""
            ).upper()

            if actual_intent != required_intent:
                return False

        property_metadata = (
            chunk.get("property_metadata") or {}
        )

        required_city = filters["city"]

        if required_city:

            actual_city = normalize_city(
                property_metadata.get("city")
            )

            if actual_city != required_city:
                return False

        required_bedrooms = filters["bedrooms"]

        if required_bedrooms is not None:

            actual_bedrooms = normalize_bedrooms(
                property_metadata.get("bedrooms")
            )

            if actual_bedrooms != required_bedrooms:
                return False

        required_type = filters["property_type"]

        if required_type:

            actual_type = normalize_property_type(
                property_metadata.get("property_type")
            )

            if actual_type != required_type:
                return False

        return True

    # --------------------------------------------------
    # LEXICAL RELEVANCE
    # --------------------------------------------------

    def calculate_lexical_boost(self, query, chunk):

        query_tokens = tokenize(query)

        if not query_tokens:
            return 0.0

        chunk_text = normalize_text(chunk.get("text"))
        chunk_title = normalize_text(chunk.get("title"))

        chunk_tokens = tokenize(
            chunk_title + " " + chunk_text
        )

        matched_tokens = query_tokens.intersection(
            chunk_tokens
        )

        overlap = len(matched_tokens) / len(query_tokens)

        boost = overlap * LEXICAL_BOOST

        normalized_query = normalize_text(query)

        for project in PROJECT_ALIASES:

            if project in normalized_query:

                if project in chunk_text or project in chunk_title:
                    boost += LEXICAL_BOOST

        return min(boost, 0.30)

    # --------------------------------------------------
    # RESULT FORMATTING
    # --------------------------------------------------

    def format_result(self, chunk, score=None, index=None):

        listing_intent = chunk.get("listing_intent")

        if listing_intent:
            listing_intent = str(listing_intent).upper()

        return {
            "score": score,
            "chunk_id": chunk.get("chunk_id"),
            "document_id": chunk.get("document_id"),
            "page_type": normalize_text(
                chunk.get("page_type")
            ),
            "listing_intent": listing_intent,
            "title": chunk.get("title"),
            "website": chunk.get("website"),
            "source_type": chunk.get("source_type"),
            "published_date": chunk.get("published_date"),
            "source_url": chunk.get("source_url"),
            "property_metadata": (
                chunk.get("property_metadata") or {}
            ),
            "text": chunk.get("text"),
        }

    # --------------------------------------------------
    # ALL MATCHING PROPERTY LISTINGS
    # --------------------------------------------------

    def search_all_properties(self, query):

        if not query or not query.strip():
            return []

        # Never treat DarGlobal project questions as
        # Wasalt property listing searches.
        if is_darglobal_query(query):
            return []

        filters = classify_query(query)

        if filters["page_type"] != "property":
            return []

        results = []
        seen_documents = set()

        for index, chunk in enumerate(self.chunks):

            if not self.matches_property_filters(
                chunk,
                filters
            ):
                continue

            if not self.matches_source_filter(chunk, query):
                continue

            document_id = chunk.get("document_id")

            key = (
                document_id
                if document_id is not None
                else chunk.get("chunk_id", index)
            )

            if key in seen_documents:
                continue

            seen_documents.add(key)

            results.append(
                self.format_result(chunk)
            )

        return results

    # --------------------------------------------------
    # SEMANTIC SEARCH
    # --------------------------------------------------

    def search(
        self,
        query,
        top_k=DEFAULT_TOP_K,
        min_similarity=MIN_SIMILARITY
    ):

        if not query or not query.strip() or top_k <= 0:
            return []

        query = query.strip()

        filters = classify_query(query)

        is_darglobal = is_darglobal_query(query)

        # Critical fix:
        # A city mention alone should not turn a
        # DarGlobal project question into a Wasalt search.
        is_property_query = (
            filters["page_type"] == "property"
            and not is_darglobal
        )

        effective_threshold = (
            DARGLOBAL_MIN_SIMILARITY
            if is_darglobal
            else min_similarity
        )

        query_embedding = self.model.encode(
            query,
            convert_to_numpy=True,
            normalize_embeddings=True
        )

        query_embedding = np.asarray(
            query_embedding,
            dtype=np.float32
        )

        semantic_scores = self.embeddings @ query_embedding

        ranked_results = []

        for index, chunk in enumerate(self.chunks):

            if not self.matches_source_filter(chunk, query):
                continue

            semantic_score = float(
                semantic_scores[index]
            )

            if is_property_query:

                if not self.matches_property_filters(
                    chunk,
                    filters
                ):
                    continue

            lexical_boost = 0.0

            if is_darglobal:

                lexical_boost = self.calculate_lexical_boost(
                    query,
                    chunk
                )

            combined_score = semantic_score + lexical_boost

            if (
                not is_property_query
                and combined_score < effective_threshold
            ):
                continue

            ranked_results.append((
                combined_score,
                semantic_score,
                index,
                chunk
            ))

        ranked_results.sort(
            key=lambda item: item[0],
            reverse=True
        )

        results = []

        seen_documents = set()
        seen_chunks = set()

        for combined_score, semantic_score, index, chunk in ranked_results:

            if is_property_query:

                document_id = chunk.get("document_id")

                key = (
                    document_id
                    if document_id is not None
                    else chunk.get("chunk_id", index)
                )

                if key in seen_documents:
                    continue

                seen_documents.add(key)

            else:

                chunk_id = chunk.get("chunk_id", index)

                if chunk_id in seen_chunks:
                    continue

                seen_chunks.add(chunk_id)

            result = self.format_result(
                chunk,
                score=round(combined_score, 4),
                index=index
            )

            result["semantic_score"] = round(
                semantic_score,
                4
            )

            results.append(result)

            if len(results) >= top_k:
                break

        return results


# --------------------------------------------------
# RESULT DISPLAY
# --------------------------------------------------

def display_results(query, results):

    print("\nQUESTION:", query)
    print("=" * 70)

    if not results:

        print("No matching results found.")
        return

    for rank, result in enumerate(results, start=1):

        print(f"\nResult {rank}")
        print("Score:", result.get("score"))
        print("Semantic score:", result.get("semantic_score"))
        print("Chunk:", result.get("chunk_id"))
        print("Title:", result.get("title"))
        print("Website:", result.get("website"))
        print("Source type:", result.get("source_type"))
        print("Published date:", result.get("published_date"))
        print("Source:", result.get("source_url"))

        property_metadata = result.get(
            "property_metadata", {}
        )

        if result.get("page_type") == "property":

            print("\nProperty details:")
            print("City:", property_metadata.get("city"))
            print("Bedrooms:", property_metadata.get("bedrooms"))
            print("Property type:", property_metadata.get("property_type"))
            print("Price:", property_metadata.get("price"))
            print("Currency:", property_metadata.get("currency"))

        print("\nContent:")
        print((result.get("text") or "")[:700])
        print("-" * 70)


# --------------------------------------------------
# TESTING
# --------------------------------------------------

if __name__ == "__main__":

    retriever = SemanticRetriever()

    test_queries = [
        "What properties are available for sale?",
        "Show me apartments available for rent.",
        "What properties are available in Riyadh?",
        "What properties are available in Jeddah?",
        "Show me three bedroom apartments for sale.",
        "Show me two bedroom apartments in Khobar.",
        "Show me rental properties in Dammam.",
        "What information does Wasalt provide?",
        "What were DarGlobal PLC financial results for FY2025?",
        "What projects does DarGlobal have in Riyadh?",
        "Tell me about Trump Plaza Jeddah.",
        "Compare DarGlobal's Riyadh and Jeddah developments.",
        "What are the major DarGlobal projects in Saudi Arabia?",
    ]

    print("\nRUNNING SAMPLE QUERIES")

    for query in test_queries:

        results = retriever.search(
            query,
            top_k=5
        )

        display_results(query, results)

    print("\nALL MATCHING JEDDAH SALE PROPERTIES")

    all_properties = retriever.search_all_properties(
        "cheapest apartment for sale in Jeddah"
    )

    display_results(
        "All apartments for sale in Jeddah",
        all_properties
    )

    print("\nINTERACTIVE SEARCH MODE")

    while True:

        query = input(
            "\nEnter your question (or type exit): "
        ).strip()

        if query.lower() in {"exit", "quit"}:
            break

        if not query:
            continue

        results = retriever.search(
            query,
            top_k=5
        )

        display_results(query, results)
