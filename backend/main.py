import os
import csv
import io
import json
import re
import requests
import google.generativeai as genai
from bs4 import BeautifulSoup
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

# -------------------------
# Configure Gemini API
# -------------------------
genai.configure(api_key=os.getenv("GEMINI_API_KEY", "AIzaSyDpC33Ll9AuGg1cqZIr0Ay--rwEPKAtJuk"))

# -------------------------
# FastAPI app
# -------------------------
app = FastAPI()

# Allow frontend calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store guides in memory
guides_data = []

# -------------------------
# Scrape page
# -------------------------
def scrape_requests(url: str):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        html = response.text
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string.strip() if soup.title else "No Title Found"
        text = soup.get_text(separator=" ", strip=True)[:1200]
        return title, text
    except Exception as e:
        return None, f"Scraping error: {str(e)}"

# -------------------------
# Generate buying guide
# -------------------------
import json

def generate_buying_guide(product_data: dict):
    prompt = f"""
    Create a structured buying guide in valid JSON format (no markdown, no code block) with these keys:

    - productTitle
    - productOverview
    - keySpecifications
    - targetAudience
    - prosAndCons
    - useCases
    - valueForMoney
    - buyingRecommendation
    - alternativeOptions

    Include the product price clearly inside keySpecifications.
    Avoid repeating keys like 'url' or 'title' inside nested objects.

    Product Title: {product_data['title']}
    URL: {product_data['url']}
    Description: {product_data['description']}
    Price: {product_data.get('price', 'N/A')}
    """
    try:
        model = genai.GenerativeModel("gemini-2.0-flash-lite")
        response = model.generate_content(prompt)

        # Clean markdown if present
        cleaned = response.text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```json")[-1].split("```")[0].strip()

        try:
            guide_json = json.loads(cleaned)
        except json.JSONDecodeError:
            guide_json = {"raw_text": cleaned}

        # Ensure price is present
        if "keySpecifications" not in guide_json:
            guide_json["keySpecifications"] = {}
        guide_json["keySpecifications"]["price"] = product_data.get("price", "N/A")

        # Flattened output
        final_guide = {"url": product_data["url"]}
        final_guide.update(guide_json)  # merge guide fields directly, no extra nested 'guide'

        return final_guide

    except Exception as e:
        return {"url": product_data["url"], "error": f"Gemini error: {str(e)}"}



# -------------------------
# Routes
# -------------------------
@app.get("/")
def read_root():
    return {"message": "Hello, Please use our guide generator"}

@app.post("/upload/")
async def upload(file: UploadFile = File(...)):
    global guides_data
    try:
        content = await file.read()
        decoded = content.decode("utf-8")
        reader = csv.DictReader(io.StringIO(decoded))

        results = []
        for row in reader:
            url = row.get("url", "")
            title_input = row.get("title", "")
            price_input = row.get("price", "")

            title, text = scrape_requests(url)
            if not text or "Scraping error" in text:
                results.append({"url": url, "error": text})
                continue

            product_data = {
                "url": url,
                "title": title_input or title,
                "description": text,
                "price": price_input
            }

            guide = generate_buying_guide(product_data)
            results.append({"url": url, "guide": guide})

        guides_data = results  # save in memory
        return {"buying_guides": results}

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get("/export/")
async def export_json():
    global guides_data
    if not guides_data:
        return JSONResponse(status_code=400, content={"error": "No guides generated yet"})

    file_path = "buying_guides.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(guides_data, f, indent=4, ensure_ascii=False)

    return FileResponse(file_path, media_type="application/json", filename="buying_guides.json")

from fastapi import BackgroundTasks
from fastapi.responses import StreamingResponse
import time

@app.get("/progress")
async def progress():
    def event_stream():
        for i in range(0, 101, 10):  # progress in 10% steps
            yield f"data: {i}\n\n"
            time.sleep(1)  # simulate work (replace with real logic)
    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/export-txt/")
async def export_txt():
    global guides_data
    if not guides_data:
        return JSONResponse(status_code=400, content={"error": "No guides generated yet"})

    def format_guide(guide):
        g = guide.get("guide", guide)  # handle nested 'guide' if exists
        lines = [
            f"URL: {guide.get('url', 'N/A')}",
            f"Product Title: {g.get('productTitle', 'N/A')}",
            f"Product Overview: {g.get('productOverview', 'N/A')}",
            "Key Specifications:"
        ]
        key_specs = g.get("keySpecifications", {})
        for k, v in key_specs.items():
            lines.append(f"  {k}: {v}")

        lines.append(f"Target Audience: {g.get('targetAudience', 'N/A')}")
        pros_cons = g.get("prosAndCons", {})
        lines.append("Pros:")
        for item in pros_cons.get("pros", []):
            lines.append(f"  - {item}")
        lines.append("Cons:")
        for item in pros_cons.get("cons", []):
            lines.append(f"  - {item}")

        lines.append("Use Cases:")
        for item in g.get("useCases", []):
            lines.append(f"  - {item}")

        lines.append(f"Value for Money: {g.get('valueForMoney', 'N/A')}")
        lines.append(f"Buying Recommendation: {g.get('buyingRecommendation', 'N/A')}")

        alternatives = g.get("alternativeOptions", [])
        if alternatives:
            lines.append("Alternative Options:")
            for alt in alternatives:
                if isinstance(alt, dict):
                    name = alt.get("productName") or alt.get("name") or alt.get("product") or "N/A"
                    reason = alt.get("reason") or alt.get("considerations") or "N/A"
                    lines.append(f"  - {name}: {reason}")
                else:
                    lines.append(f"  - {alt}")
        lines.append("\n" + "-"*50 + "\n")
        return "\n".join(lines)

    # Combine all guides
    txt_content = "\n".join([format_guide(g) for g in guides_data])

    # Save to file
    file_path = "buying_guides.txt"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(txt_content)

    return FileResponse(file_path, media_type="text/plain", filename="buying_guides.txt")
