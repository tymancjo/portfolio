// Lightbox functionality

document.addEventListener('DOMContentLoaded', () => {
    const lightbox = document.createElement('div');
    lightbox.id = 'lightbox';
    lightbox.classList.add('lightbox');
    document.body.appendChild(lightbox);

    const images = document.querySelectorAll('.gallery-item img');
    let currentImageIndex = 0;
    let galleryImages = []; // To store all images in the current gallery

    images.forEach((image, index) => {
        image.addEventListener('click', (e) => {
            e.preventDefault(); // Prevent the link from opening the image file directly
            // Populate galleryImages with all images from the current gallery
            galleryImages = Array.from(document.querySelectorAll('.gallery-grid img'));
            currentImageIndex = galleryImages.findIndex(img => img.src === e.target.src);
            
            showImage(currentImageIndex);
            lightbox.style.display = 'block';
        });
    });

    lightbox.addEventListener('click', (e) => {
        if (e.target === lightbox) {
            lightbox.style.display = 'none';
        }
    });

    function showImage(index) {
        if (index < 0) {
            currentImageIndex = galleryImages.length - 1;
        } else if (index >= galleryImages.length) {
            currentImageIndex = 0;
        } else {
            currentImageIndex = index;
        }

        const imgElement = document.createElement('img');
        imgElement.src = galleryImages[currentImageIndex].src;
        imgElement.classList.add('lightbox-content');

        // Clear previous content
        lightbox.innerHTML = '';

        // Add close button
        const closeButton = document.createElement('span');
        closeButton.classList.add('close-button');
        closeButton.innerHTML = '&times;';
        closeButton.addEventListener('click', () => {
            lightbox.style.display = 'none';
        });
        lightbox.appendChild(closeButton);

        // Add navigation buttons
        const prevButton = document.createElement('a');
        prevButton.classList.add('prev-button');
        prevButton.innerHTML = '&#10094;'; // Left arrow
        prevButton.addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent lightbox from closing
            showImage(currentImageIndex - 1);
        });
        lightbox.appendChild(prevButton);

        const nextButton = document.createElement('a');
        nextButton.classList.add('next-button');
        nextButton.innerHTML = '&#10095;'; // Right arrow
        nextButton.addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent lightbox from closing
            showImage(currentImageIndex + 1);
        });
        lightbox.appendChild(nextButton);

        lightbox.appendChild(imgElement);
    }

    // Keyboard navigation
    document.addEventListener('keydown', (e) => {
        if (lightbox.style.display === 'block') {
            if (e.key === 'ArrowLeft') {
                showImage(currentImageIndex - 1);
            } else if (e.key === 'ArrowRight') {
                showImage(currentImageIndex + 1);
            } else if (e.key === 'Escape') {
                lightbox.style.display = 'none';
            }
        }
    });
});