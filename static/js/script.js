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

    // Auto-focus the URL input field
    instagramUrlInput.focus();

    downloadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const instagramUrl = instagramUrlInput.value.trim();
        
        // Validate URL
        if (!isValidInstagramUrl(instagramUrl)) {
            showError('Please enter a valid Instagram URL (post, reel, or TV)');
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
            previewVideo.addEventListener('error', () => {
                showError('Error loading video preview. You can still try downloading the video directly.');
            });
            
            // Set download link
            downloadLink.href = data.video_url;
            downloadLink.download = data.filename || 'instagram-video.mp4';
            
            // Add event listener for download completion
            downloadLink.addEventListener('click', () => {
                showDownloadStartedMessage();
            });
            
        } catch (error) {
            loader.classList.add('hidden');
            showError(error.message || 'An error occurred while processing your request');
        }
    });
    
    function isValidInstagramUrl(url) {
        // Enhanced validation for Instagram URLs
        const regex = /^https?:\/\/(www\.)?instagram\.com\/(p|reel|tv)\/[^\/]+\/?/;
        
        // Basic validation
        if (!regex.test(url)) {
            return false;
        }
        
        // Additional checks
        try {
            const urlObj = new URL(url);
            return urlObj.hostname.includes('instagram.com');
        } catch (e) {
            return false;
        }
    }
    
    function showError(message) {
        errorMessage.classList.remove('hidden');
        videoPreview.classList.add('hidden');
        errorText.innerHTML = message.replace(/\n/g, '<br>');
    }
    
    function showDownloadStartedMessage() {
        // You could add a toast notification here if desired
        console.log('Download started');
    }
    
    // Handle paste event for convenience
    instagramUrlInput.addEventListener('paste', (e) => {
        // Short timeout to allow the paste to complete
        setTimeout(() => {
            const pastedUrl = instagramUrlInput.value.trim();
            if (pastedUrl && isValidInstagramUrl(pastedUrl)) {
                // Auto-submit if a valid URL is pasted
                downloadForm.dispatchEvent(new Event('submit'));
            }
        }, 100);
    });
    
    // Add error handling for video playback
    previewVideo.addEventListener('error', (e) => {
        console.error('Video error:', e);
        showError('Error playing the video. You can still try downloading it directly using the download button.');
    });
});