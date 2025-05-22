from flask import Flask, render_template, request, jsonify, send_file
import requests
import re
import os
import json
import uuid
import time
from urllib.parse import urlparse
from bs4 import BeautifulSoup

app = Flask(__name__)

# Create a directory for temporary files
TEMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp')
os.makedirs(TEMP_DIR, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download_video():
    try:
        data = request.json
        instagram_url = data.get('url')
        
        if not instagram_url:
            return jsonify({'error': 'No URL provided'}), 400
            
        # Validate URL
        if not is_valid_instagram_url(instagram_url):
            return jsonify({'error': 'Invalid Instagram URL'}), 400
            
        # Get video URL
        video_info = extract_video_info(instagram_url)
        
        if not video_info:
            return jsonify({'error': 'Could not extract video information'}), 400
            
        # Download and save the video
        video_path, filename = download_video_file(video_info['video_url'])
        
        # Return the video URL for the client
        video_url = f'/video/{os.path.basename(video_path)}'
        
        return jsonify({
            'success': True,
            'video_url': video_url,
            'filename': filename
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/video/<filename>')
def serve_video(filename):
    video_path = os.path.join(TEMP_DIR, filename)
    if os.path.exists(video_path):
        return send_file(video_path, as_attachment=True)
    return jsonify({'error': 'Video not found'}), 404

def is_valid_instagram_url(url):
    pattern = r'^https?:\/\/(www\.)?instagram\.com\/(p|reel|tv)\/[^\/]+\/?'
    return re.match(pattern, url) is not None

def extract_video_info(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Method 1: Try to find video URL in meta tags
        meta_tags = soup.find_all('meta', property='og:video')
        if meta_tags and len(meta_tags) > 0:
            video_url = meta_tags[0].get('content')
            if video_url:
                return {'video_url': video_url}
        
        # Method 2: Try to find video URL in the page source
        video_pattern = r'"video_url":"([^"]+)"'
        video_matches = re.findall(video_pattern, response.text)
        
        if video_matches and len(video_matches) > 0:
            video_url = video_matches[0].replace('\\u0026', '&')
            return {'video_url': video_url}
            
        # Method 3: Look for shared_data JSON
        shared_data_pattern = r'<script type="text/javascript">window\._sharedData = (.+?);</script>'
        shared_data_match = re.search(shared_data_pattern, response.text)
        
        if shared_data_match:
            shared_data = json.loads(shared_data_match.group(1))
            
            # Navigate through the JSON structure to find video URL
            if 'entry_data' in shared_data and 'PostPage' in shared_data['entry_data']:
                post = shared_data['entry_data']['PostPage'][0]['graphql']['shortcode_media']
                
                if 'video_url' in post:
                    return {'video_url': post['video_url']}
                    
                if 'edge_sidecar_to_children' in post:
                    # Handle carousel posts
                    for edge in post['edge_sidecar_to_children']['edges']:
                        node = edge['node']
                        if node['is_video'] and 'video_url' in node:
                            return {'video_url': node['video_url']}
        
        return None
        
    except Exception as e:
        print(f"Error extracting video info: {str(e)}")
        return None

def download_video_file(video_url):
    try:
        # Generate a unique filename
        filename = f"instagram_video_{uuid.uuid4().hex}.mp4"
        file_path = os.path.join(TEMP_DIR, filename)
        
        # Download the video
        response = requests.get(video_url, stream=True)
        response.raise_for_status()
        
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        return file_path, filename
        
    except Exception as e:
        print(f"Error downloading video: {str(e)}")
        raise

# Clean up temporary files older than 1 hour
def cleanup_temp_files():
    current_time = time.time()
    for filename in os.listdir(TEMP_DIR):
        file_path = os.path.join(TEMP_DIR, filename)
        # If file is older than 1 hour (3600 seconds)
        if os.path.isfile(file_path) and current_time - os.path.getmtime(file_path) > 3600:
            os.remove(file_path)

if __name__ == '__main__':
    # Schedule cleanup to run periodically
    import threading
    import schedule
    
    def run_cleanup():
        while True:
            cleanup_temp_files()
            time.sleep(3600)  # Run every hour
    
    # Start cleanup thread
    cleanup_thread = threading.Thread(target=run_cleanup)
    cleanup_thread.daemon = True
    cleanup_thread.start()
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=12000, debug=True)