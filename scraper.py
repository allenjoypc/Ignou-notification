import requests
from bs4 import BeautifulSoup
import firebase_admin
from firebase_admin import credentials, firestore
import hashlib
import json
import os

# Firebase Connection
try:
    if not firebase_admin._apps:
        firebase_key = os.environ.get("FIREBASE_KEY")
        if not firebase_key:
            raise Exception("FIREBASE_KEY missing in GitHub Secrets")
        cred = credentials.Certificate(json.loads(firebase_key))
        firebase_admin.initialize_app(cred)
    db = firestore.client()
except Exception as e:
    print(f"Error: {e}")
    exit()

URL = "https://www.ignou.ac.in/announcements/0?nav=6"
COLLECTION = "notifications"

def create_id(title, date):
    return hashlib.md5(f"{title}_{date}".encode()).hexdigest()

def detect_type(t):
    t = t.lower()
    if "notification" in t: return "Notification"
    if "news" in t: return "News"
    return "Announcement"

def run():
    print("Scraping IGNOU...")
    res = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    soup = BeautifulSoup(res.text, "html.parser")
    rows = soup.find_all("tr")[1:51] # Top 50

    for row in reversed(rows):
        cols = row.find_all("td")
        if len(cols) < 4: continue
        
        issued = cols[1].text.strip() or "IGNOU HQ"
        title_col = cols[2]
        title = title_col.text.strip()
        date = cols[3].text.strip()
        
        link = ""
        a = title_col.find("a")
        if a:
            href = a.get("href", "")
            link = href if href.startswith("http") else f"https://www.ignou.ac.in{href}"

        doc_id = create_id(title, date)
        doc_ref = db.collection(COLLECTION).document(doc_id)
        
        if not doc_ref.get().exists:
            doc_ref.set({
                "title": title, "date": date, "link": link,
                "issuedBy": issued, "type": detect_type(title),
                "timestamp": firestore.SERVER_TIMESTAMP
            })
            print(f"Added: {title[:50]}...")

if __name__ == "__main__":
    run()
