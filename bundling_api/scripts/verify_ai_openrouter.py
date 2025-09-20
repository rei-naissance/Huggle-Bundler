from app.services.ai import maybe_enhance_bundle_text

if __name__ == "__main__":
    res = maybe_enhance_bundle_text(
        "Breakfast Essentials Pack",
        ["Eggs", "Bacon", "Bread"],
        12,
    )
    print("RESULT:", res)
