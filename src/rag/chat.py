
import re

from retrieve import SemanticRetriever, classify_query
from generate import generate_answer


# --------------------------------------------------
# QUERY INTENT DETECTION
# --------------------------------------------------

def is_comparison_query(query):
    keywords = [
        "cheapest",
        "lowest price",
        "least expensive",
        "most expensive",
        "highest price",
        "costliest",
        "price comparison",
    ]

    query = query.lower()

    return any(keyword in query for keyword in keywords)


def is_count_query(query):
    keywords = [
        "how many",
        "count",
        "number of properties",
        "total properties",
        "how much properties",
    ]

    query = query.lower()

    return any(keyword in query for keyword in keywords)


# --------------------------------------------------
# PROPERTY PRICE EXTRACTION
# --------------------------------------------------

def extract_price(property_data):
    """
    Convert a property's price into a numeric value.
    Returns None if the price is unavailable.
    """

    price = property_data.get("price")

    if price is None:
        return None

    try:
        cleaned_price = re.sub(
            r"[^\d.]",
            "",
            str(price)
        )

        if not cleaned_price:
            return None

        return float(cleaned_price)

    except (ValueError, TypeError):
        return None


# --------------------------------------------------
# PROPERTY RESULT FORMATTING
# --------------------------------------------------

def format_property(result, rank=None):

    metadata = result.get("property_metadata") or {}

    title = result.get("title") or "Property listing"
    city = metadata.get("city") or "Not specified"
    district = metadata.get("district")
    bedrooms = metadata.get("bedrooms")
    property_type = metadata.get("property_type") or "Not specified"
    area = metadata.get("area")
    listing_intent = metadata.get("listing_intent")
    price = metadata.get("price")
    currency = metadata.get("currency") or ""

    lines = []

    if rank is not None:
        lines.append(f"{rank}. {title}")
    else:
        lines.append(title)

    lines.append(f"City: {city}")

    if district:
        lines.append(f"District: {district}")

    lines.append(f"Property type: {property_type}")

    if listing_intent:
        lines.append(f"Listing type: {listing_intent}")

    lines.append(
        f"Bedrooms: {bedrooms if bedrooms is not None else 'Not specified'}"
    )

    if area is not None:
        lines.append(f"Area: {area} SQM")

    if price is not None:
        lines.append(f"Price: {price} {currency}".strip())
    else:
        lines.append("Price: Not available")

    source_url = result.get("source_url")

    if source_url:
        lines.append(f"Source: {source_url}")

    return "\n".join(lines)


# --------------------------------------------------
# DETERMINISTIC PROPERTY ANSWERS
# --------------------------------------------------

def generate_property_answer(query, results):

    if not results:
        return (
            "I couldn't find matching properties "
            "in the collected dataset."
        )

    # --------------------------------------------------
    # COUNT QUERY
    # --------------------------------------------------

    if is_count_query(query):

        return (
            f"I found {len(results)} matching property "
            f"listing(s) in the collected dataset.\n\n"
            "The count is based on unique property documents."
        )

    # --------------------------------------------------
    # PRICE COMPARISON QUERY
    # --------------------------------------------------

    if is_comparison_query(query):

        priced_properties = []

        for result in results:

            metadata = result.get("property_metadata") or {}

            price = extract_price(metadata)

            if price is not None:
                priced_properties.append(
                    (price, result)
                )

        if not priced_properties:
            return (
                "I found matching properties, but their "
                "prices are not available in the collected dataset."
            )

        query_lower = query.lower()

        # Detect cheapest and most expensive independently.
        # This supports queries asking for both in one comparison.

        asks_cheapest = any(
            word in query_lower
            for word in [
                "cheapest",
                "lowest price",
                "least expensive",
            ]
        )

        asks_most_expensive = any(
            word in query_lower
            for word in [
                "most expensive",
                "highest price",
                "costliest",
            ]
        )

        asks_general_comparison = (
            "price comparison" in query_lower
        )

        # --------------------------------------------------
        # BOTH CHEAPEST AND MOST EXPENSIVE
        # --------------------------------------------------

        if asks_cheapest and asks_most_expensive:

            cheapest_price, cheapest_property = min(
                priced_properties,
                key=lambda item: item[0]
            )

            expensive_price, expensive_property = max(
                priced_properties,
                key=lambda item: item[0]
            )

            cheapest_currency = (
                cheapest_property.get("property_metadata") or {}
            ).get("currency") or ""

            expensive_currency = (
                expensive_property.get("property_metadata") or {}
            ).get("currency") or ""

            return (
                "PROPERTY PRICE COMPARISON\n\n"

                "CHEAPEST PROPERTY\n"
                "------------------------------\n"
                f"{format_property(cheapest_property)}\n"
                f"Calculated price: {cheapest_price:,.2f} "
                f"{cheapest_currency}\n\n"

                "MOST EXPENSIVE PROPERTY\n"
                "------------------------------\n"
                f"{format_property(expensive_property)}\n"
                f"Calculated price: {expensive_price:,.2f} "
                f"{expensive_currency}\n\n"

                "COMPARISON SUMMARY\n"
                "------------------------------\n"
                f"Cheapest price: {cheapest_price:,.2f} "
                f"{cheapest_currency}\n"
                f"Most expensive price: {expensive_price:,.2f} "
                f"{expensive_currency}\n"
                f"Price difference: "
                f"{abs(expensive_price - cheapest_price):,.2f} "
                f"{cheapest_currency}\n\n"

                f"Compared against {len(priced_properties)} "
                "matching listings with available prices."
            )

        # --------------------------------------------------
        # CHEAPEST ONLY
        # --------------------------------------------------

        if asks_cheapest:

            selected_price, selected_property = min(
                priced_properties,
                key=lambda item: item[0]
            )

            currency = (
                selected_property.get("property_metadata") or {}
            ).get("currency") or ""

            return (
                "Cheapest matching property\n\n"
                f"{format_property(selected_property)}\n\n"
                f"Calculated price: {selected_price:,.2f} "
                f"{currency}\n\n"
                f"Compared against {len(priced_properties)} "
                "matching listings with available prices."
            )

        # --------------------------------------------------
        # MOST EXPENSIVE ONLY
        # --------------------------------------------------

        if asks_most_expensive:

            selected_price, selected_property = max(
                priced_properties,
                key=lambda item: item[0]
            )

            currency = (
                selected_property.get("property_metadata") or {}
            ).get("currency") or ""

            return (
                "Most expensive matching property\n\n"
                f"{format_property(selected_property)}\n\n"
                f"Calculated price: {selected_price:,.2f} "
                f"{currency}\n\n"
                f"Compared against {len(priced_properties)} "
                "matching listings with available prices."
            )

        if asks_general_comparison:
            return None

    return None


# --------------------------------------------------
# CHATBOT
# --------------------------------------------------

def run_chatbot():

    print("=" * 60)
    print("DARGLOBAL - WASALT AI REAL ESTATE CHATBOT")
    print("=" * 60)

    print("\nLoading retriever...")

    retriever = SemanticRetriever()

    print("\nChatbot is ready!")
    print("Ask about properties, prices, locations, sales or rentals.")
    print("Type 'exit' to stop.")

    while True:

        print("\n" + "-" * 60)

        query = input("You: ").strip()

        if query.lower() in ["exit", "quit"]:
            print("\nThank you for using DarGlobal Wasalt AI!")
            break

        if not query:
            print("Please enter a question.")
            continue

        try:

            print("\nSearching the knowledge base...")

            filters = classify_query(query)

            comparison_query = is_comparison_query(query)
            count_query = is_count_query(query)

            # --------------------------------------------------
            # STEP 1: RETRIEVE MATCHING PROPERTIES
            # --------------------------------------------------

            if comparison_query or count_query:

                structured_query = query

                if filters.get("page_type") != "property":
                    structured_query += " properties"

                results = retriever.search_all_properties(
                    structured_query
                )

            else:

                results = retriever.search(
                    query,
                    top_k=5
                )

            if not results:

                print(
                    "\nAI: No matching information was found "
                    "in the collected dataset."
                )

                continue

            print(f"Retrieved {len(results)} result(s).")

            # --------------------------------------------------
            # STEP 2: HANDLE PROPERTY CALCULATIONS
            # --------------------------------------------------

            answer = None

            if comparison_query or count_query:

                answer = generate_property_answer(
                    query,
                    results
                )

            # --------------------------------------------------
            # STEP 3: USE LLM WHEN NEEDED
            # --------------------------------------------------

            if answer is None:

                print("\nGenerating AI response...")

                answer = generate_answer(
                    query,
                    results
                )

            # --------------------------------------------------
            # STEP 4: DISPLAY RESPONSE
            # --------------------------------------------------

            print("\n" + "=" * 60)
            print("AI ASSISTANT")
            print("=" * 60)

            if answer:
                print(answer)
            else:
                print(
                    "I couldn't generate a response. "
                    "Please try rephrasing your question."
                )

            # --------------------------------------------------
            # STEP 5: SHOW SOURCES
            # --------------------------------------------------

            print("\n" + "-" * 60)
            print("RETRIEVED SOURCES")

            displayed_urls = set()

            for result in results:

                source_url = result.get("source_url")

                if source_url and source_url not in displayed_urls:

                    displayed_urls.add(source_url)

                    print(source_url)

        except Exception as error:

            print(f"\nError: {error}")


# --------------------------------------------------
# ENTRY POINT
# --------------------------------------------------

if __name__ == "__main__":
    run_chatbot()
