# Instagram Video Downloader

A simple web application that allows users to download videos from Instagram by providing the URL of the post.

## Features

- Easy-to-use interface
- Support for Instagram posts, reels, and TV videos
- Video preview before downloading
- Responsive design for mobile and desktop

## Technologies Used

- **Frontend**: HTML, CSS, JavaScript
- **Backend**: Python with Flask
- **Parsing**: BeautifulSoup4 for HTML parsing

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/Joybabu8/OpenH.git
   cd OpenH
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   python app.py
   ```

4. Open your browser and navigate to:
   ```
   http://localhost:12000
   ```

## How It Works

1. The user enters an Instagram video URL in the input field
2. The application validates the URL format
3. The backend extracts the video URL from the Instagram page
4. The video is temporarily stored on the server
5. The user can preview and download the video

## Limitations

- Instagram frequently updates their website structure, which may break the extraction process
- Private Instagram accounts are not supported
- Some videos may not be downloadable due to Instagram's restrictions

## Disclaimer

This tool is for educational purposes only. Please respect copyright and Instagram's terms of service when using this application. Always obtain permission before downloading and using content that doesn't belong to you.

## License

This project is open source and available under the MIT License.