
import json
import numpy as np

from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
from sentence_transformers import SentenceTransformer


# --------------------------------------------------
# PATHS
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CHUNKS_FILE = PROJECT_ROOT / "data" / "processed" / "document_chunks.json"

DOCUMENTS_FILE = PROJECT_ROOT / "data" / "processed" / "cleaned_documents.json"

INDEX_DIR = PROJECT_ROOT / "data" / "processed" / "vector_index"
INDEX_DIR.mkdir(parents=True, exist_ok=True)

EMBEDDINGS_FILE = INDEX_DIR / "embeddings.npy"
METADATA_FILE = INDEX_DIR / "metadata.json"


# --------------------------------------------------
# MODEL CONFIGURATION
# --------------------------------------------------

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

BATCH_SIZE = 32


# --------------------------------------------------
# JSON HELPERS
# --------------------------------------------------

def load_json(file_path):

    if not file_path.exists():
        raise FileNotFoundError(
            f"Required file not found: {file_path}"
        )

    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def get_documents():

    dataset = load_json(DOCUMENTS_FILE)

    if isinstance(dataset, dict):
        return dataset.get("documents", [])

    return dataset


def get_chunks():

    dataset = load_json(CHUNKS_FILE)

    if isinstance(dataset, dict):
        return dataset.get("chunks", [])

    return dataset


# --------------------------------------------------
# DOCUMENT LOOKUP
# --------------------------------------------------

def build_document_lookup(documents):

    lookup = {}

    for document in documents:

        document_id = document.get("document_id")

        if document_id is not None:
            lookup[str(document_id)] = document

    return lookup


# --------------------------------------------------
# PROPERTY LISTING CLASSIFICATION
# --------------------------------------------------

def infer_listing_intent(document):

    """
    Infer SALE or RENT only for property documents.
    """

    page_type = str(
        document.get("page_type", "")
    ).lower()

    if page_type != "property":
        return None

    intent = str(
        document.get("listing_intent", "")
    ).upper()

    if intent in ("SALE", "RENT"):
        return intent

    title = str(
        document.get("title", "")
    ).lower()

    source_url = str(
        document.get("source_url", document.get("url", ""))
    ).lower()

    full_text = str(
        document.get("full_text", "")
    ).lower()

    text = f"{title} {source_url} {full_text}"

    if "for sale" in text or "/sale" in source_url:
        return "SALE"

    if "for rent" in text or "/rent" in source_url:
        return "RENT"

    return None


# --------------------------------------------------
# PROPERTY METADATA NORMALIZATION
# --------------------------------------------------

def normalize_property_metadata(chunk, document):

    """
    Preserve structured property metadata.

    Chunk metadata takes priority.
    Document metadata is used as fallback.
    """

    chunk_metadata = chunk.get("property_metadata")

    document_metadata = document.get("property_metadata")

    if not isinstance(chunk_metadata, dict):
        chunk_metadata = {}

    if not isinstance(document_metadata, dict):
        document_metadata = {}

    property_metadata = {
        **document_metadata,
        **chunk_metadata
    }

    expected_fields = [
        "bedrooms",
        "bathrooms",
        "city",
        "region",
        "district",
        "country",
        "property_type",
        "price",
        "currency",
        "availability",
        "area",
        "url"
    ]

    normalized = {}

    for field in expected_fields:

        value = property_metadata.get(field)

        if isinstance(value, str):
            value = value.strip()

        normalized[field] = value if value not in ("", None) else None

    return normalized


# --------------------------------------------------
# METADATA PREPARATION
# --------------------------------------------------

def prepare_metadata(chunks, document_lookup):

    metadata_chunks = []

    for chunk in chunks:

        document_id = str(
            chunk.get("document_id", "")
        )

        document = document_lookup.get(
            document_id,
            {}
        )

        # Page type.
        page_type = (
            chunk.get("page_type")
            or document.get("page_type")
            or "unknown"
        )

        page_type = str(page_type).lower()

        # Listing intent.
        listing_intent = None

        if page_type == "property":

            listing_intent = (
                chunk.get("listing_intent")
                or document.get("listing_intent")
                or infer_listing_intent(document)
            )

            if listing_intent:

                listing_intent = str(
                    listing_intent
                ).upper()

                if listing_intent not in ("SALE", "RENT"):
                    listing_intent = None

        # Property metadata.
        property_metadata = normalize_property_metadata(
            chunk,
            document
        )

        # Preserve source information.
        website = (
            chunk.get("website")
            or document.get("website")
        )

        source_type = (
            chunk.get("source_type")
            or document.get("source_type")
            or "website"
        )

        published_date = (
            chunk.get("published_date")
            or document.get("published_date")
            or ""
        )

        source_url = (
            chunk.get("source_url")
            or document.get("url")
        )

        # Preserve all relevant chunk information.
        metadata_chunks.append({

            "chunk_id": chunk.get("chunk_id"),

            "document_id": chunk.get("document_id"),

            "website": website,

            "source_type": source_type,

            "published_date": published_date,

            "page_type": page_type,

            "listing_intent": listing_intent,

            "title": (
                chunk.get("title")
                or document.get("title")
            ),

            "source_url": source_url,

            "property_metadata": property_metadata,

            "text": chunk["text"]

        })

    return metadata_chunks


# --------------------------------------------------
# BUILD VECTOR INDEX
# --------------------------------------------------

def main():

    print("=" * 55)
    print("BUILDING SEMANTIC SEARCH INDEX")
    print("=" * 55)

    # Load data.
    print("\nLoading document chunks...")

    chunks = get_chunks()

    print("Loading cleaned documents...")

    documents = get_documents()

    if not chunks:
        raise ValueError("No document chunks found.")

    if not documents:
        raise ValueError("No cleaned documents found.")

    print("\nTotal chunks:", len(chunks))
    print("Total documents:", len(documents))

    # Build document lookup.
    document_lookup = build_document_lookup(documents)

    # Validate chunk text.
    texts = []

    for index, chunk in enumerate(chunks):

        text = str(
            chunk.get("text", "")
        ).strip()

        if not text:
            raise ValueError(
                f"Empty text found in chunk at index {index}."
            )

        texts.append(text)

    # Load embedding model.
    print("\nLoading embedding model:", MODEL_NAME)

    model = SentenceTransformer(MODEL_NAME)

    print("Embedding model loaded successfully.")

    # Generate normalized embeddings.
    print("\nGenerating embeddings...")

    embeddings = model.encode(

        texts,

        batch_size=BATCH_SIZE,

        show_progress_bar=True,

        convert_to_numpy=True,

        normalize_embeddings=True

    )

    embeddings = np.asarray(
        embeddings,
        dtype=np.float32
    )

    # Validate embedding dimensions.
    if embeddings.shape[0] != len(chunks):

        raise ValueError(
            "Embedding count does not match chunk count."
        )

    # Prepare metadata.
    print("\nPreparing metadata...")

    metadata_chunks = prepare_metadata(
        chunks,
        document_lookup
    )

    # Save embeddings.
    np.save(
        EMBEDDINGS_FILE,
        embeddings
    )

    # Build metadata object.
    metadata = {

        "model_name": MODEL_NAME,

        "embedding_dimension": int(
            embeddings.shape[1]
        ),

        "total_vectors": int(
            embeddings.shape[0]
        ),

        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "chunks": metadata_chunks

    }

    # Save metadata.
    with open(
        METADATA_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            metadata,
            file,
            indent=4,
            ensure_ascii=False
        )

    # --------------------------------------------------
    # INDEX SUMMARY
    # --------------------------------------------------

    property_chunks = [
        chunk
        for chunk in metadata_chunks
        if chunk["page_type"] == "property"
    ]

    sale_chunks = [
        chunk
        for chunk in property_chunks
        if chunk["listing_intent"] == "SALE"
    ]

    rent_chunks = [
        chunk
        for chunk in property_chunks
        if chunk["listing_intent"] == "RENT"
    ]

    unknown_intent_chunks = [
        chunk
        for chunk in property_chunks
        if chunk["listing_intent"] is None
    ]

    unique_property_documents = len({

        chunk["document_id"]

        for chunk in property_chunks

        if chunk["document_id"] is not None

    })

    # Metadata completeness.
    unique_property_metadata = {}

    for chunk in property_chunks:

        document_id = chunk["document_id"]

        unique_property_metadata[document_id] = (
            chunk["property_metadata"]
        )

    properties = list(
        unique_property_metadata.values()
    )

    with_city = sum(
        1 for p in properties if p.get("city")
    )

    with_bedrooms = sum(
        1 for p in properties if p.get("bedrooms") is not None
    )

    with_property_type = sum(
        1 for p in properties if p.get("property_type")
    )

    with_price = sum(
        1 for p in properties if p.get("price") is not None
    )

    # Source distribution.
    website_counts = Counter(
        chunk.get("website")
        for chunk in metadata_chunks
    )

    source_type_counts = Counter(
        chunk.get("source_type")
        for chunk in metadata_chunks
    )

    # --------------------------------------------------
    # SUMMARY
    # --------------------------------------------------

    print("\n" + "=" * 55)
    print("INDEX BUILD COMPLETED")
    print("=" * 55)

    print("\nVECTOR INFORMATION")

    print("Total vectors:", embeddings.shape[0])

    print("Embedding dimensions:", embeddings.shape[1])

    print("\nSOURCE DISTRIBUTION")

    for website, count in website_counts.items():
        print(f"{website}: {count} chunks")

    print("\nSOURCE TYPES")

    for source_type, count in source_type_counts.items():
        print(f"{source_type}: {count} chunks")

    print("\nPROPERTY INFORMATION")

    print("Property chunks:", len(property_chunks))

    print("Unique property documents:", unique_property_documents)

    print("Sale chunks:", len(sale_chunks))

    print("Rent chunks:", len(rent_chunks))

    print("Unknown listing intent chunks:", len(unknown_intent_chunks))

    print("\nPROPERTY METADATA COMPLETENESS")

    print("Properties with city:", with_city)

    print("Properties with bedrooms:", with_bedrooms)

    print("Properties with property type:", with_property_type)

    print("Properties with price:", with_price)

    print("\nOUTPUT FILES")

    print("Embedding file:", EMBEDDINGS_FILE)

    print("Metadata file:", METADATA_FILE)

    print("\n" + "=" * 55)


# --------------------------------------------------
# ENTRY POINT
# --------------------------------------------------

if __name__ == "__main__":

    main()
