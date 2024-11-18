from flask import Flask, render_template, request
from googleapiclient.discovery import build
import re

app = Flask(__name__)

# Replace with your actual YouTube API key
API_KEY = "AIzaSyCOEwuQ2vJm4XFxKbMrOSwQHXgjBihAa6Y"

def extract_channel_id_or_handle(channel_url):
    """Extracts channel ID or handle from a YouTube channel URL."""
    if "@" in channel_url:
        pattern = r"@([A-Za-z0-9_-]+)"
    else:
        pattern = r"(?:youtube\.com\/(?:user|channel|c)\/|youtu\.be\/)([A-Za-z0-9_-]+)"
    
    match = re.search(pattern, channel_url)
    return match.group(1) if match else None

def estimate_watch_time(video_count, average_views, avg_video_length=10):
    """Estimates watch time based on video count and average views."""
    return video_count * average_views * avg_video_length

def is_channel_monetized(subscriber_count, view_count, video_count):
    """Check for monetization eligibility based on simplified criteria."""
    try:
        subscriber_count = int(subscriber_count)
        view_count = int(view_count)
        video_count = int(video_count)
    except ValueError:
        return False  # Invalid counts, assume not monetized

    # Average video length (can adjust as needed)
    avg_video_length = 10  # Average video length in minutes

    # Calculate approximate watch time in minutes
    watch_time = estimate_watch_time(video_count, view_count / video_count if video_count > 0 else 0, avg_video_length)

    # Monetization criteria
    return subscriber_count >= 1000 and watch_time >= 240000

def get_channel_info(channel_url):
    youtube = build("youtube", "v3", developerKey=API_KEY)
    identifier = extract_channel_id_or_handle(channel_url)

    if not identifier:
        return {"error": "Invalid YouTube channel URL."}

    if "@" in channel_url:
        request = youtube.search().list(
            part="snippet",
            q=identifier,
            type="channel",
            maxResults=1
        )
        response = request.execute()
        
        if "items" in response and response["items"]:
            channel_id = response["items"][0]["snippet"]["channelId"]
        else:
            return {"error": "Channel not found."}
    else:
        channel_id = identifier

    request = youtube.channels().list(
        part="snippet,statistics",
        id=channel_id
    )
    response = request.execute()

    if "items" in response and response["items"]:
        channel_info = response["items"][0]
        title = channel_info["snippet"]["title"]
        country = channel_info["snippet"].get("country", "N/A")
        subscriber_count = channel_info["statistics"].get("subscriberCount", "0")
        video_count = channel_info["statistics"].get("videoCount", "0")
        view_count = channel_info["statistics"].get("viewCount", "0")
        creation_date = channel_info["snippet"]["publishedAt"]

        # Check monetization eligibility
        monetized = is_channel_monetized(subscriber_count, view_count, video_count)

        return {
            "Channel Name": title,
            "Subscribers": subscriber_count,
            "Videos": video_count,
            "Views": view_count,
            "Creation Date": creation_date,
            "Country": country,
            "Monetized": "Likely" if monetized else "Unlikely",
            "Diagnostics": {
                "Watch Time (minutes)": estimate_watch_time(int(video_count), int(view_count) / int(video_count) if int(video_count) > 0 else 0),
            }
        }
    else:
        return {"error": "Channel not found."}

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        channel_url = request.form.get("channel_url")
        if channel_url:
            channel_info = get_channel_info(channel_url)
            return render_template("index.html", channel_info=channel_info)
    return render_template("index.html", channel_info=None)

if __name__ == "__main__":
    app.run(debug=True)
