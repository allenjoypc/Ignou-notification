import requests
from bs4 import BeautifulSoup
import firebase_admin
from firebase_admin import credentials, firestore, messaging
import hashlib
import json
import os

# Firebase Initialization
try:
    if not firebase_admin._apps:
        firebase_key = os.environ.get("FIREBASE_KEY")
        if not firebase_key:
            raise Exception("FIREBASE_KEY not found")
        cred = credentials.Certificate(json.loads(firebase_key))
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase Connected")
except Exception as e:
    print(f"❌ Firebase Error: {e}")
    exit()

URL = "https://www.ignou.ac.in/announcements/0?nav=6"
COLLECTION_NAME = "notifications"

def send_push_notification(title, body):
    """Sends a real-time push notification to all app users"""
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            topic="new_assignments",  # This matches the topic in your MainActivity
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    sound='default',
                    color='#0D47A1'
                ),
            ),
        )
        response = messaging.send(message)
        print(f"🚀 Push Notification Sent: {response}")
    except Exception as e:
        print(f"❌ FCM Error: {e}")

def create_id(title, date):
    return hashlib.md5(f"{title}_{date}".encode("utf-8")).hexdigest()

def detect_type(title):
    t = title.lower()
    if "notification" in t: return "Notification"
    if "news" in t: return "News"
    return "Announcement"

def run_scraper():
    print("🚀 Starting Scraper...")
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(URL, headers=headers, timeout=30)
        if response.status_code != 200: return

        soup = BeautifulSoup(response.text, "html.parser")
        rows = soup.find_all("tr")[1:51] # Top 50 notifications

        added = 0
        for row in reversed(rows):
            cols = row.find_all("td")
            if len(cols) < 4: continue

            issued_by = cols[1].get_text(strip=True) or "IGNOU HQ"
            title = cols[2].get_text(strip=True)
            date = cols[3].get_text(strip=True)
            
            link = ""
            a_tag = cols[2].find("a")
            if a_tag:
                href = a_tag.get("href", "")
                link = href if href.startswith("http") else f"https://www.ignou.ac.in{href}"

            doc_id = create_id(title, date)
            doc_ref = db.collection(COLLECTION_NAME).document(doc_id)

            if not doc_ref.get().exists:
                doc_type = detect_type(title)
                doc_ref.set({
                    "title": title,
                    "date": date,
                    "link": link,
                    "issuedBy": issued_by,
                    "type": doc_type,
                    "timestamp": firestore.SERVER_TIMESTAMP
                })
                
                # SEND PUSH NOTIFICATION
                send_push_notification(
                    title=f"New {doc_type} from IGNOU",
                    body=title[:100] + "..."
                )
                added += 1
                print(f"✅ Added & Notified: {title[:50]}...")

        print(f"🎉 Completed. {added} new notifications added.")
    except Exception as e:
        print(f"❌ Scraper Error: {e}")

if __name__ == "__main__":
    run_scraper()
