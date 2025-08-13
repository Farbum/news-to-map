import requests, trafilatura

def extract_article_text(url):
    html = requests.get(url, timeout=20).text
    text = trafilatura.extract(
        html,
        favor_recall=False,
        include_comments=False,
        include_tables=False,
        deduplicate=True,   # <- built-in dedupe
    )
    if not text:
        raise RuntimeError("Extraction failed")
    return text



if __name__ == "__main__":
    url = input("Enter the article URL: ").strip()
    text = extract_article_text(url)
    if text:
        print(f"\nExtracted Article Text: character length: {len(text)} | word length: {len(text.split(" "))}\n")
        print(text)
    else:
        print("Failed to extract article text or the article is empty.")
