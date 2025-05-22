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
            return jsonify({'error': 'Invalid Instagram URL. Please provide a valid Instagram post, reel, or TV URL.'}), 400
        
        print(f"Processing Instagram URL: {instagram_url}")
            
        # Get video URL
        video_info = extract_video_info(instagram_url)
        
        if not video_info:
            # Try one more time with a different approach - add www if not present
            if 'www.' not in instagram_url:
                modified_url = instagram_url.replace('https://', 'https://www.')
                print(f"Retrying with modified URL: {modified_url}")
                video_info = extract_video_info(modified_url)
            
            if not video_info:
                return jsonify({
                    'error': 'Could not extract video information. This could be due to:\n'
                            '1. The post may not contain a video\n'
                            '2. The post may be from a private account\n'
                            '3. Instagram may have changed their page structure\n'
                            'Please try again with a different video URL.'
                }), 400
            
        # Download and save the video
        try:
            video_path, filename = download_video_file(video_info['video_url'])
            
            # Return the video URL for the client
            video_url = f'/video/{os.path.basename(video_path)}'
            
            return jsonify({
                'success': True,
                'video_url': video_url,
                'filename': filename,
                'source_url': instagram_url
            })
        except Exception as download_error:
            print(f"Error downloading video: {str(download_error)}")
            return jsonify({
                'error': f'Error downloading video: {str(download_error)}. The video URL was found but could not be downloaded.'
            }), 500
        
    except Exception as e:
        print(f"Unexpected error in download route: {str(e)}")
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'sec-ch-ua': '"Not A(Brand";v="99", "Google Chrome";v="120", "Chromium";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Referer': 'https://www.instagram.com/',
            'Origin': 'https://www.instagram.com',
        }
        
        # Add cookies to simulate a logged-in session
        cookies = {
            'ig_did': str(uuid.uuid4()),
            'ig_nrcb': '1',
            'csrftoken': str(uuid.uuid4()),
        }
        
        response = requests.get(url, headers=headers, cookies=cookies)
        response.raise_for_status()
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Method 1: Try to find video URL in meta tags
        meta_tags = soup.find_all('meta', property='og:video')
        if meta_tags and len(meta_tags) > 0:
            video_url = meta_tags[0].get('content')
            if video_url:
                return {'video_url': video_url}
        
        # Method 2: Try to find video URL in the page source using multiple patterns
        video_patterns = [
            r'"video_url":"([^"]+)"',
            r'"video_url"\s*:\s*"([^"]+)"',
            r'property="og:video" content="([^"]+)"',
            r'<meta property="og:video" content="([^"]+)"',
            r'"contentUrl"\s*:\s*"([^"]+)"',
        ]
        
        for pattern in video_patterns:
            video_matches = re.findall(pattern, response.text)
            if video_matches and len(video_matches) > 0:
                video_url = video_matches[0].replace('\\u0026', '&')
                return {'video_url': video_url}
        
        # Method 3: Look for shared_data JSON
        shared_data_patterns = [
            r'<script type="text/javascript">window\._sharedData = (.+?);</script>',
            r'window\.__additionalDataLoaded\(\'[^\']+\',(.+?)\);</script>',
            r'window\._sharedData = (.+?);</script>',
        ]
        
        for pattern in shared_data_patterns:
            shared_data_match = re.search(pattern, response.text)
            if shared_data_match:
                try:
                    shared_data = json.loads(shared_data_match.group(1))
                    
                    # Navigate through the JSON structure to find video URL
                    # Method 3.1: Check for PostPage structure
                    if 'entry_data' in shared_data and 'PostPage' in shared_data['entry_data']:
                        try:
                            post = shared_data['entry_data']['PostPage'][0]['graphql']['shortcode_media']
                            
                            if 'video_url' in post:
                                return {'video_url': post['video_url']}
                                
                            if 'edge_sidecar_to_children' in post:
                                # Handle carousel posts
                                for edge in post['edge_sidecar_to_children']['edges']:
                                    node = edge['node']
                                    if node['is_video'] and 'video_url' in node:
                                        return {'video_url': node['video_url']}
                        except (KeyError, IndexError):
                            pass
                    
                    # Method 3.2: Check for items structure (newer Instagram format)
                    if 'items' in shared_data:
                        for item in shared_data['items']:
                            if 'video_versions' in item and len(item['video_versions']) > 0:
                                return {'video_url': item['video_versions'][0]['url']}
                except json.JSONDecodeError:
                    pass
        
        # Method 4: Look for additional data in script tags
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                json_data = json.loads(script.string)
                if isinstance(json_data, dict) and 'contentUrl' in json_data:
                    return {'video_url': json_data['contentUrl']}
                elif isinstance(json_data, list):
                    for item in json_data:
                        if isinstance(item, dict) and 'contentUrl' in item:
                            return {'video_url': item['contentUrl']}
            except (json.JSONDecodeError, AttributeError):
                pass
        
        # Method 5: Try to find video element directly
        video_elements = soup.find_all('video')
        for video in video_elements:
            if video.get('src'):
                return {'video_url': video['src']}
            
            # Check for source elements inside video
            sources = video.find_all('source')
            for source in sources:
                if source.get('src'):
                    return {'video_url': source['src']}
        
        print(f"Could not extract video URL from: {url}")
        return None
        
    except Exception as e:
        print(f"Error extracting video info: {str(e)}")
        return None

def download_video_file(video_url):
    try:
        # Generate a unique filename
        filename = f"instagram_video_{uuid.uuid4().hex}.mp4"
        file_path = os.path.join(TEMP_DIR, filename)
        
        # Set up headers for the download request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Range': 'bytes=0-',
            'Referer': 'https://www.instagram.com/',
            'Origin': 'https://www.instagram.com',
        }
        
        # Download the video with a timeout and retry mechanism
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                response = requests.get(video_url, stream=True, headers=headers, timeout=30)
                response.raise_for_status()
                
                # Check if we got a valid video file (content type check)
                content_type = response.headers.get('Content-Type', '')
                if not content_type.startswith(('video/', 'application/octet-stream')):
                    print(f"Warning: Unexpected content type: {content_type}")
                
                # Check if we got a reasonable file size
                content_length = int(response.headers.get('Content-Length', 0))
                if content_length > 0 and content_length < 10000:  # Less than 10KB is suspicious
                    print(f"Warning: File size too small: {content_length} bytes")
                
                # Download the file
                with open(file_path, 'wb') as f:
                    downloaded_size = 0
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)
                
                # Verify the file was downloaded successfully
                if os.path.getsize(file_path) < 10000:  # Less than 10KB is suspicious
                    print(f"Warning: Downloaded file size too small: {os.path.getsize(file_path)} bytes")
                    if retry_count < max_retries - 1:
                        retry_count += 1
                        print(f"Retrying download ({retry_count}/{max_retries})...")
                        continue
                
                return file_path, filename
                
            except requests.exceptions.RequestException as e:
                print(f"Download attempt {retry_count + 1} failed: {str(e)}")
                if retry_count < max_retries - 1:
                    retry_count += 1
                    print(f"Retrying download ({retry_count}/{max_retries})...")
                    time.sleep(2)  # Wait before retrying
                else:
                    raise
        
        raise Exception(f"Failed to download video after {max_retries} attempts")
        
    except Exception as e:
        print(f"Error downloading video: {str(e)}")
        # Clean up any partially downloaded file
        if 'file_path' in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"Removed partial download: {file_path}")
            except:
                pass
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