// Lightbox functionality

document.addEventListener('DOMContentLoaded', () => {
    const lightbox = document.createElement('div');
    lightbox.id = 'lightbox';
    lightbox.classList.add('lightbox');
    document.body.appendChild(lightbox);

    const galleryLinks = document.querySelectorAll('.gallery-item');
    let currentImageIndex = 0;
    let galleryImages = []; // Array of objects: { thumb, full }

    // Initialize gallery images array
    galleryLinks.forEach((link, index) => {
        const img = link.querySelector('img');
        galleryImages.push({
            thumb: img.src,
            full: link.getAttribute('href')
        });

        link.addEventListener('click', (e) => {
            e.preventDefault();
            currentImageIndex = index;
            showImage(currentImageIndex);
            lightbox.style.display = 'block';
            document.body.style.overflow = 'hidden';

            const hint = document.createElement('div');
            hint.className = 'keyboard-hint';
            hint.textContent = '← → nawigacja    esc zamknij';
            lightbox.appendChild(hint);
        });
    });

    lightbox.addEventListener('click', (e) => {
        if (e.target === lightbox) {
            closeLightbox();
        }
    });

    function closeLightbox() {
        lightbox.style.display = 'none';
        document.body.style.overflow = '';
    }

    function showImage(index) {
        if (index < 0) {
            currentImageIndex = galleryImages.length - 1;
        } else if (index >= galleryImages.length) {
            currentImageIndex = 0;
        } else {
            currentImageIndex = index;
        }

        const data = galleryImages[currentImageIndex];
        
        lightbox.innerHTML = '';

        // Close button
        const closeBtn = document.createElement('span');
        closeBtn.className = 'close-button';
        closeBtn.innerHTML = '&times;';
        closeBtn.onclick = closeLightbox;
        lightbox.appendChild(closeBtn);

        // Prev/Next buttons
        const prevBtn = document.createElement('a');
        prevBtn.className = 'prev-button';
        prevBtn.innerHTML = '&#10094;';
        prevBtn.onclick = (e) => { e.stopPropagation(); showImage(currentImageIndex - 1); };
        lightbox.appendChild(prevBtn);

        const nextBtn = document.createElement('a');
        nextBtn.className = 'next-button';
        nextBtn.innerHTML = '&#10095;';
        nextBtn.onclick = (e) => { e.stopPropagation(); showImage(currentImageIndex + 1); };
        lightbox.appendChild(nextBtn);

        // Main Image
        const imgElement = document.createElement('img');
        imgElement.src = data.full;
        imgElement.classList.add('lightbox-content');
        lightbox.appendChild(imgElement);
    }

    // Touch events
    let touchStartX = 0;
    let touchEndX = 0;

    lightbox.addEventListener('touchstart', (e) => {
        touchStartX = e.changedTouches[0].clientX;
    }, { passive: true });

    lightbox.addEventListener('touchend', (e) => {
        touchEndX = e.changedTouches[0].clientX;
        const diff = touchStartX - touchEndX;
        if (Math.abs(diff) > 50) {
            if (diff > 0) showImage(currentImageIndex + 1); // Swipe left -> next
            else showImage(currentImageIndex - 1); // Swipe right -> prev
        }
    }, { passive: true });

    // Keyboard
    document.addEventListener('keydown', (e) => {
        if (lightbox.style.display === 'block') {
            if (e.key === 'ArrowLeft') showImage(currentImageIndex - 1);
            else if (e.key === 'ArrowRight') showImage(currentImageIndex + 1);
            else if (e.key === 'Escape') closeLightbox();
        }
    });
});
