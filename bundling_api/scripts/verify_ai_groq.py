from app.services.ai import maybe_enhance_bundle_text

if __name__ == "__main__":
    res = maybe_enhance_bundle_text(
        "Quick Lunch Bundle",
        ["Sandwich", "Chips", "Soda"],
        5,
    )
    print("RESULT:", res)
