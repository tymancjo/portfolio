// Lightbox functionality

document.addEventListener('DOMContentLoaded', () => {
    const lightbox = document.createElement('div');
    lightbox.id = 'lightbox';
    lightbox.classList.add('lightbox');
    document.body.appendChild(lightbox);

    const galleryLinks = document.querySelectorAll('.gallery-item');
    let currentImageIndex = 0;
    let galleryImages = []; // [{thumb, full, id, title, description}]

    galleryLinks.forEach((link, index) => {
        const img = link.querySelector('img');
        galleryImages.push({
            thumb: img.src,
            full: link.getAttribute('href'),
            id: link.id,
            title: link.dataset.title || '',
            description: link.dataset.description || '',
        });

        link.addEventListener('click', (e) => {
            e.preventDefault();
            currentImageIndex = index;
            showImage(currentImageIndex);
            lightbox.style.display = 'block';
            document.body.style.overflow = 'hidden';
            history.replaceState(null, '', '#' + link.id);
        });
    });

    // Open lightbox if URL contains a hash matching a photo id
    const initialHash = window.location.hash.slice(1);
    if (initialHash) {
        const idx = galleryImages.findIndex(img => img.id === initialHash);
        if (idx !== -1) {
            currentImageIndex = idx;
            showImage(currentImageIndex);
            lightbox.style.display = 'block';
            document.body.style.overflow = 'hidden';
        }
    }

    lightbox.addEventListener('click', (e) => {
        if (e.target === lightbox) {
            closeLightbox();
        }
    });

    function closeLightbox() {
        lightbox.style.display = 'none';
        document.body.style.overflow = '';
        history.replaceState(null, '', window.location.pathname);
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

        // Main image
        const imgElement = document.createElement('img');
        imgElement.src = data.full;
        imgElement.classList.add('lightbox-content');
        lightbox.appendChild(imgElement);

        // Caption (title + optional description)
        if (data.title) {
            const caption = document.createElement('div');
            caption.className = 'lightbox-caption';
            caption.textContent = data.title;
            if (data.description) {
                const sub = document.createElement('span');
                sub.className = 'lightbox-caption-sub';
                sub.textContent = data.description;
                caption.appendChild(sub);
            }
            lightbox.appendChild(caption);
        }

        // Update URL hash on navigation
        if (data.id) {
            history.replaceState(null, '', '#' + data.id);
        }

        // Keyboard hint (first open only, fades out)
        const hint = document.createElement('div');
        hint.className = 'keyboard-hint';
        hint.textContent = '← → nawigacja    esc zamknij';
        lightbox.appendChild(hint);
    }

    // Touch swipe
    let touchStartX = 0;
    let touchEndX = 0;

    lightbox.addEventListener('touchstart', (e) => {
        touchStartX = e.changedTouches[0].clientX;
    }, { passive: true });

    lightbox.addEventListener('touchend', (e) => {
        touchEndX = e.changedTouches[0].clientX;
        const diff = touchStartX - touchEndX;
        if (Math.abs(diff) > 50) {
            if (diff > 0) showImage(currentImageIndex + 1);
            else showImage(currentImageIndex - 1);
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
