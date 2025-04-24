import time
import threading
import schedule
import requests
from io import BytesIO
from PIL import Image, ImageTk
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta
import tzlocal
import re
from bs4 import BeautifulSoup
import sys
import os

def resource_path(filename):
    """Get absolute path to resource (for PyInstaller)."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.abspath("."), filename)

ICON_MAP = {
    'High': resource_path('red_folder.png'),
    'Medium': resource_path('orange_folder.png')
}


icon_images = {}
selected_date = datetime.today()

def download_icons():
    for impact, path in ICON_MAP.items():
        try:
            img_data = Image.open(path).resize((20, 20))
            icon_images[impact] = ImageTk.PhotoImage(img_data)
        except Exception as e:
            print(f"Failed to load {impact} icon: {e}")

def date_to_url(date_obj):
    return f"https://www.forexfactory.com/calendar?day={date_obj.strftime('%b%d.%Y').lower()}"

def scrape_forex_factory(date_obj):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920x1080')
    options.add_argument('--no-sandbox')
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    )

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    url = date_to_url(date_obj)
    driver.get(url)
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "tr.calendar__row"))
    )

    rows = driver.find_elements(By.CSS_SELECTOR, "tr.calendar__row")
    events = []

    rows = driver.find_elements(By.CSS_SELECTOR, "tr.calendar__row")
    events = []
    last_time_text = ""

    for row in rows:
        try:
            currency = row.find_element(By.CSS_SELECTOR, '.calendar__cell.calendar__currency span').text.strip()
            if currency != "USD":
                continue

            # Use last known time if current row has none
            try:
                time_text = row.find_element(By.CSS_SELECTOR, '.calendar__cell.calendar__time span').text.strip()
                last_time_text = time_text
            except:
                time_text = last_time_text  # Use previous time if none shown

            # Only keep high/medium impact events
            impact_el = row.find_element(By.CSS_SELECTOR, '.calendar__cell.calendar__impact span')
            impact_title = impact_el.get_attribute("title").lower()
            if "high" in impact_title:
                impact = "High"
            elif "medium" in impact_title:
                impact = "Medium"
            else:
                continue

            # Support multiple events per row
            event_els = row.find_elements(By.CSS_SELECTOR, '.calendar__event-title')
            for ev in event_els:
                event_name = ev.text.strip()
                if event_name:
                    events.append({
                        "time": time_text,
                        "event": event_name,
                        "impact": impact
                    })
        except Exception:
            continue

    # Deduplicate final list
    seen = set()
    deduped = []
    for e in events:
        key = (e['time'], e['event'], e['impact'])
        if key not in seen:
            seen.add(key)
            deduped.append(e)

    events = deduped

    driver.quit()

    print(f"✅ {len(events)} USD events found.")
    for e in events:
        print(f" - {e['time']} | {e['event']} ({e['impact']})")
    return events



def update_ui():
    for widget in frame.winfo_children():
        widget.destroy()

    date_label.config(text=f"Events for {selected_date.strftime('%A, %B %d, %Y')}")

    # Get local timezone abbreviation (like PDT)
    try:
        tz_abbr = time.tzname[time.localtime().tm_isdst]
    except Exception:
        tz_abbr = "Local Time"

    events = scrape_forex_factory(selected_date)

    if not events:
        tk.Label(frame, text="No high or medium impact USD events found.", font=('Arial', 12)).pack()

    for event in events:
        row = tk.Frame(frame)
        icon = icon_images.get(event['impact'])
        if icon:
            tk.Label(row, image=icon).pack(side=tk.LEFT, padx=5)
        display_time = f"{event['time']} {tz_abbr}"
        tk.Label(row, text=f"{display_time} - {event['event']} ({event['impact']})", font=('Arial', 11)).pack(side=tk.LEFT, padx=5)
        row.pack(fill='x', pady=2)

def prev_day():
    global selected_date
    selected_date -= timedelta(days=1)
    update_ui()

def next_day():
    global selected_date
    selected_date += timedelta(days=1)
    update_ui()

def scheduled_update():
    update_ui()

def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)

# GUI Setup
root = tk.Tk()
root.title("USD Events - Forex Factory")
root.geometry("700x450")

top_frame = tk.Frame(root)
top_frame.pack(pady=10)

prev_button = tk.Button(top_frame, text="← Previous", command=prev_day)
prev_button.pack(side=tk.LEFT, padx=10)

date_label = tk.Label(top_frame, font=('Arial', 14))
date_label.pack(side=tk.LEFT, padx=10)

next_button = tk.Button(top_frame, text="Next →", command=next_day)
next_button.pack(side=tk.LEFT, padx=10)

frame = tk.Frame(root)
frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

download_icons()
update_ui()

schedule.every(8).hours.do(scheduled_update)
threading.Thread(target=run_schedule, daemon=True).start()

root.mainloop()
