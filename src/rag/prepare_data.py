
import json
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from datetime import datetime, timezone
from collections import Counter


# --------------------------------------------------
# PATHS AND CONFIGURATION
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = PROJECT_ROOT / "data" / "raw"

WASALT_INPUT_FILE = RAW_DIR / "scraped_pages.json"
DARGLOBAL_INPUT_FILE = RAW_DIR / "darglobal_sources.json"

OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DOCUMENTS_FILE = OUTPUT_DIR / "cleaned_documents.json"
CHUNKS_FILE = OUTPUT_DIR / "document_chunks.json"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
MIN_CONTENT_LENGTH = 200


# --------------------------------------------------
# TEXT CLEANING
# --------------------------------------------------

def clean_text(text):

    if not isinstance(text, str):
        return ""

    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)

    return text.strip()


def canonicalize_url(url):

    parsed = urlsplit(url)

    path = parsed.path.rstrip("/") or "/"

    return urlunsplit((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        path,
        "",
        ""
    ))


# --------------------------------------------------
# LOAD MULTIPLE DATA SOURCES
# --------------------------------------------------

def load_raw_documents():

    all_documents = []

    source_counts = {}

    input_files = [
        ("Wasalt", WASALT_INPUT_FILE),
        ("DarGlobal", DARGLOBAL_INPUT_FILE)
    ]

    for source_name, filepath in input_files:

        if not filepath.exists():

            print(f"WARNING: {source_name} file not found: {filepath}")
            source_counts[source_name] = 0
            continue

        with open(
            filepath,
            "r",
            encoding="utf-8"
        ) as file:

            documents = json.load(file)

        if not isinstance(documents, list):
            raise ValueError(
                f"Expected a JSON list in {filepath}"
            )

        all_documents.extend(documents)

        source_counts[source_name] = len(documents)

        print(f"{source_name} raw documents: {len(documents)}")

    if not all_documents:

        raise FileNotFoundError(
            "No raw documents were found."
        )

    return all_documents, source_counts


# --------------------------------------------------
# STRUCTURED DATA EXTRACTION
# --------------------------------------------------

IMPORTANT_FIELDS = {
    "name": "Name",
    "description": "Description",
    "price": "Price",
    "priceCurrency": "Currency",
    "numberOfBedrooms": "Bedrooms",
    "numberOfRooms": "Rooms",
    "numberOfBathroomsTotal": "Bathrooms",
    "floorSize": "Built-up area",
    "addressLocality": "City",
    "addressRegion": "Region",
    "streetAddress": "Street or district",
    "addressCountry": "Country",
    "propertyType": "Property type",
    "availability": "Availability",
    "url": "URL",
    "datePosted": "Date posted",
    "dateModified": "Date modified",
    "numberOfUnits": "Number of units",
    "latitude": "Latitude",
    "longitude": "Longitude",
    "yearBuilt": "Year built",
    "image": "Image"
}


def extract_structured_text(json_ld):

    results = []
    seen = set()

    def walk(value):

        if isinstance(value, dict):

            for key, item in value.items():

                if key in IMPORTANT_FIELDS:

                    label = IMPORTANT_FIELDS[key]

                    if isinstance(item, dict):

                        if "value" in item:
                            item = item["value"]

                        elif "name" in item:
                            item = item["name"]

                        elif "address" in item:
                            item = item["address"]

                    if isinstance(item, (str, int, float)):

                        text = f"{label}: {item}"

                        if text not in seen:
                            results.append(text)
                            seen.add(text)

                if isinstance(item, (dict, list)):
                    walk(item)

        elif isinstance(value, list):

            for item in value:
                walk(item)

    if isinstance(json_ld, (list, dict)):
        walk(json_ld)

    return clean_text("\n".join(results))


# --------------------------------------------------
# PROPERTY METADATA EXTRACTION
# --------------------------------------------------

def extract_property_metadata(json_ld, title="", content=""):

    fields = {
        "numberOfBedrooms": "bedrooms",
        "numberOfBathroomsTotal": "bathrooms",
        "addressLocality": "city",
        "addressRegion": "region",
        "streetAddress": "district",
        "addressCountry": "country",
        "propertyType": "property_type",
        "price": "price",
        "priceCurrency": "currency",
        "availability": "availability",
        "floorSize": "area",
        "url": "url"
    }

    metadata = {}

    def normalize_value(value):

        if isinstance(value, dict):

            if "value" in value:
                return normalize_value(value["value"])

            if "name" in value:
                return normalize_value(value["name"])

            return None

        if isinstance(value, (str, int, float)):
            return value

        return None

    def walk(obj):

        if isinstance(obj, dict):

            for key, value in obj.items():

                if key in fields:

                    output_key = fields[key]
                    normalized = normalize_value(value)

                    if normalized is not None:
                        if output_key not in metadata:
                            metadata[output_key] = normalized

                if isinstance(value, (dict, list)):
                    walk(value)

        elif isinstance(obj, list):

            for item in obj:
                walk(item)

    if isinstance(json_ld, (dict, list)):
        walk(json_ld)

    search_text = f"{title}\n{content}"

    # BEDROOM FALLBACK

    if not metadata.get("bedrooms"):

        match = re.search(
            r"\b(\d+)\s*bedrooms?\b",
            search_text,
            re.IGNORECASE
        )

        if match:
            metadata["bedrooms"] = int(match.group(1))

    # BATHROOM FALLBACK

    if not metadata.get("bathrooms"):

        match = re.search(
            r"\b(\d+)\s*bathrooms?\b",
            search_text,
            re.IGNORECASE
        )

        if match:
            metadata["bathrooms"] = int(match.group(1))

    # CITY FALLBACK

    if not metadata.get("city"):

        match = re.search(
            r"\bCity:\s*([^\n,|]+)",
            content,
            re.IGNORECASE
        )

        if match:
            metadata["city"] = match.group(1).strip()

    # PROPERTY TYPE FALLBACK

    if not metadata.get("property_type"):

        match = re.search(
            r"\b(apartment|villa|house|townhouse|land)\b",
            title,
            re.IGNORECASE
        )

        if match:
            metadata["property_type"] = match.group(1).lower()

    # AREA FALLBACK

    if not metadata.get("area"):

        area_patterns = [

            r"\bBuilt[\s-]*up\s+Area\s*:\s*([\d,]+(?:\.\d+)?)\s*(SQM|m2|m²|sqm)\b",

            r"\b([\d,]+(?:\.\d+)?)\s*(SQM|m2|m²|sqm)\s+built[\s-]*up\s+area\b",

            r"\bArea\s*:\s*([\d,]+(?:\.\d+)?)\s*(SQM|m2|m²|sqm)\b"

        ]

        for pattern in area_patterns:

            match = re.search(
                pattern,
                search_text,
                re.IGNORECASE
            )

            if match:
                metadata["area"] = match.group(1)
                break

        if not metadata.get("area"):

            match = re.search(
                r"\b([\d,]+(?:\.\d+)?)\s*(SQM|m2|m²|sqm)\b",
                title,
                re.IGNORECASE
            )

            if match:
                metadata["area"] = match.group(1)

    # PRICE FALLBACK

    if not metadata.get("price"):

        price_patterns = [

            r"\bPrice\s*:\s*([\d,]+(?:\.\d+)?)\s*(SAR|USD|AED)?\b",

            r"\b([\d,]+(?:\.\d+)?)\s*(SAR|USD|AED)\b"

        ]

        for pattern in price_patterns:

            match = re.search(
                pattern,
                content,
                re.IGNORECASE
            )

            if match:

                metadata["price"] = match.group(1)

                if match.lastindex and match.lastindex >= 2:

                    currency = match.group(2)

                    if currency:
                        metadata.setdefault(
                            "currency",
                            currency.upper()
                        )

                break

    # CURRENCY FALLBACK

    if not metadata.get("currency"):

        currency_match = re.search(
            r"\b(SAR|USD|AED)\b",
            search_text,
            re.IGNORECASE
        )

        if currency_match:

            metadata["currency"] = (
                currency_match.group(1).upper()
            )

    # NUMERIC NORMALIZATION

    for field in ("bedrooms", "bathrooms", "price", "area"):

        value = metadata.get(field)

        if value is not None:

            if isinstance(value, dict):
                value = normalize_value(value)

            try:

                numeric_value = float(
                    str(value).replace(",", "").strip()
                )

                if numeric_value.is_integer():
                    numeric_value = int(numeric_value)

                metadata[field] = numeric_value

            except (ValueError, TypeError):
                pass

    # STRING CLEANING

    for field, value in list(metadata.items()):

        if isinstance(value, str):
            metadata[field] = clean_text(value)

    return metadata


# --------------------------------------------------
# LISTING INTENT EXTRACTION
# --------------------------------------------------

def extract_listing_intent(title="", content=""):

    text = f"{title} {content}".lower()

    sale_patterns = [
        r"\bfor sale\b",
        r"\bsale\b"
    ]

    rent_patterns = [
        r"\bfor rent\b",
        r"\bfor lease\b",
        r"\brent\b",
        r"\blease\b"
    ]

    is_sale = any(
        re.search(pattern, text)
        for pattern in sale_patterns
    )

    is_rent = any(
        re.search(pattern, text)
        for pattern in rent_patterns
    )

    if is_sale and not is_rent:
        return "SALE"

    if is_rent and not is_sale:
        return "RENT"

    return None


# --------------------------------------------------
# DOCUMENT CLEANING
# --------------------------------------------------

def clean_documents(raw_documents):

    cleaned_documents = []

    seen_urls = set()
    seen_content = set()

    stats = {
        "duplicate_urls": 0,
        "duplicate_content": 0,
        "short_documents": 0,
        "empty_documents": 0,
        "property_documents": 0,
        "sale_documents": 0,
        "rent_documents": 0,
        "documents_with_city": 0,
        "documents_with_bedrooms": 0,
        "documents_with_area": 0,
        "documents_with_price": 0
    }

    for page in raw_documents:

        original_url = (
            page.get("url")
            or page.get("source_url")
            or ""
        )

        if not original_url:
            continue

        canonical_url = canonicalize_url(original_url)

        if canonical_url in seen_urls:

            stats["duplicate_urls"] += 1
            continue

        seen_urls.add(canonical_url)

        website = clean_text(
            page.get("website", "")
        )

        source_type = clean_text(
            page.get("source_type", "website")
        )

        published_date = clean_text(
            page.get("published_date", "")
        )

        title = clean_text(
            page.get("title", "")
        )

        description = clean_text(
            page.get("meta_description", "")
        )

        content = clean_text(
            page.get("content", "")
        )

        json_ld = page.get("json_ld", [])

        structured_text = extract_structured_text(json_ld)

        property_metadata = extract_property_metadata(
            json_ld=json_ld,
            title=title,
            content=content
        )

        # Handle both string and dictionary headings.

        headings = page.get("headings", [])

        heading_items = []

        for item in headings:

            if isinstance(item, dict):
                heading_items.append(
                    clean_text(item.get("text", ""))
                )

            elif isinstance(item, str):
                heading_items.append(clean_text(item))

        heading_text = "\n".join(
            item for item in heading_items if item
        )

        # Skip empty documents.

        if not content and not structured_text:

            stats["empty_documents"] += 1
            continue

        # Duplicate content detection.

        content_signature = (
            content + " " + structured_text
        ).lower()

        if content_signature in seen_content:

            stats["duplicate_content"] += 1
            continue

        seen_content.add(content_signature)

        # Determine page type.

        page_type = page.get("page_type", "")

        if not page_type:

            page_type = (
                "property"
                if "/property/" in urlsplit(original_url).path
                else "general"
            )

        # Listing intent only applies to property pages.

        listing_intent = None

        if page_type == "property":

            listing_intent = extract_listing_intent(
                title,
                content
            )

        # Build full document text.

        full_text_parts = [

            f"Website: {website}",

            f"Source type: {source_type}",

            f"Published date: {published_date}",

            f"Page type: {page_type}",

            f"Title: {title}",

            f"Description: {description}",

            f"Headings: {heading_text}",

            f"Page content: {content}",

            f"Property information: {structured_text}"

        ]

        full_text = clean_text(
            "\n".join(
                part for part in full_text_parts
                if part.strip()
            )
        )

        is_short = len(content) < MIN_CONTENT_LENGTH

        if is_short:
            stats["short_documents"] += 1

        if page_type == "property":

            stats["property_documents"] += 1

            if listing_intent == "SALE":
                stats["sale_documents"] += 1

            elif listing_intent == "RENT":
                stats["rent_documents"] += 1

            if property_metadata.get("city"):
                stats["documents_with_city"] += 1

            if property_metadata.get("bedrooms") is not None:
                stats["documents_with_bedrooms"] += 1

            if property_metadata.get("area") is not None:
                stats["documents_with_area"] += 1

            if property_metadata.get("price") is not None:
                stats["documents_with_price"] += 1

        cleaned_documents.append({

            "document_id": (
                f"doc_{len(cleaned_documents) + 1:04d}"
            ),

            "website": website,

            "source_type": source_type,

            "published_date": published_date,

            "url": original_url,

            "canonical_url": canonical_url,

            "page_type": page_type,

            "listing_intent": listing_intent,

            "title": title,

            "description": description,

            "headings": heading_items,

            "content": content,

            "json_ld": json_ld,

            "structured_text": structured_text,

            "property_metadata": property_metadata,

            "full_text": full_text,

            "content_length": len(content),

            "needs_review": is_short

        })

    return cleaned_documents, stats


# --------------------------------------------------
# SENTENCE-AWARE CHUNKING
# --------------------------------------------------

def split_long_text(text, max_length):

    words = text.split()

    pieces = []

    current = ""

    for word in words:

        candidate = f"{current} {word}".strip()

        if len(candidate) > max_length and current:

            pieces.append(current)
            current = word

        else:

            current = candidate

    if current:
        pieces.append(current)

    return pieces


def split_into_sentences(text):

    parts = re.split(
        r"(?<=[.!?])\s+|\n+",
        text
    )

    sentences = []

    for part in parts:

        part = part.strip()

        if not part:
            continue

        if len(part) > CHUNK_SIZE:

            sentences.extend(
                split_long_text(part, CHUNK_SIZE)
            )

        else:

            sentences.append(part)

    return sentences


def create_chunks(documents):

    chunks = []

    for document in documents:

        text = document["full_text"]

        sentences = split_into_sentences(text)

        current_sentences = []

        current_length = 0

        for sentence in sentences:

            sentence_length = len(sentence) + 1

            if (
                current_sentences
                and current_length + sentence_length > CHUNK_SIZE
            ):

                chunk_text = " ".join(
                    current_sentences
                ).strip()

                chunks.append({

                    "chunk_id": (
                        f"chunk_{len(chunks) + 1:05d}"
                    ),

                    "document_id": document["document_id"],

                    "website": document["website"],

                    "source_type": document.get(
                        "source_type", "website"
                    ),

                    "published_date": document.get(
                        "published_date", ""
                    ),

                    "page_type": document["page_type"],

                    "listing_intent": document.get(
                        "listing_intent"
                    ),

                    "title": document["title"],

                    "source_url": document["url"],

                    "property_metadata": document.get(
                        "property_metadata", {}
                    ),

                    "text": chunk_text,

                    "chunk_length": len(chunk_text)

                })

                # Retain recent sentences for overlap.

                overlap_sentences = []

                overlap_length = 0

                for previous in reversed(current_sentences):

                    if (
                        overlap_length + len(previous) + 1
                        > CHUNK_OVERLAP
                    ):
                        break

                    overlap_sentences.insert(0, previous)

                    overlap_length += len(previous) + 1

                current_sentences = overlap_sentences

                current_length = overlap_length

            current_sentences.append(sentence)

            current_length += sentence_length

        # Save remaining content.

        if current_sentences:

            chunk_text = " ".join(
                current_sentences
            ).strip()

            chunks.append({

                "chunk_id": (
                    f"chunk_{len(chunks) + 1:05d}"
                ),

                "document_id": document["document_id"],

                "website": document["website"],

                "source_type": document.get(
                    "source_type", "website"
                ),

                "published_date": document.get(
                    "published_date", ""
                ),

                "page_type": document["page_type"],

                "listing_intent": document.get(
                    "listing_intent"
                ),

                "title": document["title"],

                "source_url": document["url"],

                "property_metadata": document.get(
                    "property_metadata", {}
                ),

                "text": chunk_text,

                "chunk_length": len(chunk_text)

            })

    return chunks


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    print("=" * 60)
    print("MULTI-SOURCE DATA CLEANING AND CHUNKING")
    print("=" * 60)

    raw_documents, source_counts = load_raw_documents()

    print("\nTOTAL RAW DOCUMENTS:", len(raw_documents))

    documents, stats = clean_documents(raw_documents)

    chunks = create_chunks(documents)

    generated_at = datetime.now(
        timezone.utc
    ).isoformat()

    # Save cleaned documents.

    with open(
        DOCUMENTS_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump({

            "generated_at": generated_at,

            "total_documents": len(documents),

            "documents": documents

        }, file, indent=4, ensure_ascii=False)

    # Save chunks.

    with open(
        CHUNKS_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump({

            "generated_at": generated_at,

            "total_chunks": len(chunks),

            "chunk_size": CHUNK_SIZE,

            "chunk_overlap": CHUNK_OVERLAP,

            "chunks": chunks

        }, file, indent=4, ensure_ascii=False)

    # Source distribution.

    website_counts = Counter(
        document["website"]
        for document in documents
    )

    source_type_counts = Counter(
        document["source_type"]
        for document in documents
    )

    print("\nCLEANING SUMMARY")
    print("-" * 45)

    print("Raw documents:", len(raw_documents))
    print("Cleaned documents:", len(documents))
    print("Generated chunks:", len(chunks))

    print("\nDOCUMENTS BY WEBSITE")

    for key, value in website_counts.items():
        print(f"{key}: {value}")

    print("\nDOCUMENTS BY SOURCE TYPE")

    for key, value in source_type_counts.items():
        print(f"{key}: {value}")

    print("\nPROPERTY STATISTICS")

    for key, value in stats.items():
        print(f"{key}: {value}")

    print("\nOUTPUT FILES")
    print(DOCUMENTS_FILE)
    print(CHUNKS_FILE)

    print("\nData preparation completed successfully!")


if __name__ == "__main__":
    main()
