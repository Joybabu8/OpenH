document.addEventListener('DOMContentLoaded', () => {
    const downloadForm = document.getElementById('download-form');
    const instagramUrlInput = document.getElementById('instagram-url');
    const resultContainer = document.getElementById('result');
    const loader = document.querySelector('.loader');
    const videoPreview = document.querySelector('.video-preview');
    const previewVideo = document.getElementById('preview-video');
    const downloadLink = document.getElementById('download-link');
    const errorMessage = document.querySelector('.error-message');
    const errorText = document.getElementById('error-text');

    downloadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const instagramUrl = instagramUrlInput.value.trim();
        
        // Validate URL
        if (!isValidInstagramUrl(instagramUrl)) {
            showError('Please enter a valid Instagram URL');
            return;
        }
        
        // Show loader
        resultContainer.classList.remove('hidden');
        loader.classList.remove('hidden');
        videoPreview.classList.add('hidden');
        errorMessage.classList.add('hidden');
        
        try {
            // Send request to backend
            const response = await fetch('/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url: instagramUrl }),
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Failed to download video');
            }
            
            // Show video preview
            loader.classList.add('hidden');
            videoPreview.classList.remove('hidden');
            
            // Set video source
            previewVideo.src = data.video_url;
            
            // Set download link
            downloadLink.href = data.video_url;
            downloadLink.download = data.filename || 'instagram-video.mp4';
            
        } catch (error) {
            loader.classList.add('hidden');
            showError(error.message || 'An error occurred while processing your request');
        }
    });
    
    function isValidInstagramUrl(url) {
        // Basic validation for Instagram URLs
        const regex = /^https?:\/\/(www\.)?instagram\.com\/(p|reel|tv)\/[^\/]+\/?/;
        return regex.test(url);
    }
    
    function showError(message) {
        errorMessage.classList.remove('hidden');
        errorText.textContent = message;
    }
});