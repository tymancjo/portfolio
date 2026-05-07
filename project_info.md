# Informacje o projekcie 

## Podsumowanie
Projekt dotyczy strony www, która jest hostowana na GitHub jako statyczne portfolio fotograficzne.

## Aktualny Status (Maj 2026)
Strona została zmodernizowana, przechodząc z prostego układu siatki na nowoczesny design typu "masonry" z optymalizacją wydajności.

## Kluczowe Funkcje i Architektura

- **System Szablonów:** Rozdzielono logikę od wyglądu. Skrypt `build.py` korzysta z `index_template.html` oraz `gallery_template.html`.
- **Automatyczna Optymalizacja:** Skrypt `build.py` automatycznie generuje miniatury (thumbnails) w podkatalogach `_thumbs` przy użyciu biblioteki Pillow (LANCZOS downsampling).
- **Design:**
    - Styl: Minimalistyczny, jasny (light-themed).
    - Układ: Masonry grid dla galerii (zachowanie proporcji zdjęć).
    - Typografia: Playfair Display (nagłówki) oraz Inter (tekst).
- **Technologia:**
    - Python: `build.py` do generowania statycznych plików HTML.
    - JavaScript: `main.js` obsługujący lightbox z nawigacją klawiszową i gestami dotykowymi.
    - CSS: Nowoczesny arkusz `style.css` z wykorzystaniem CSS Variables i Flexbox/Grid.
- **Kontakt:** Odświeżona strona kontaktowa z osobistym zdjęciem i dopasowaną typografią.

## Założenia

- Strona to statyczny html bez żadnych automatyzacji po stronie serwera.
- Design ma być ładny, przejżysty i minimalistyczny (inspiracje: Pixieset/Montana/Torres).
- Skrypt ma analizować podkatalog `photos` i na jego podstawie tworzyć galerie.
- W każdym podkatalogu w `photos` plik `info.md` dostarcza tekst dla galerii.
- Zdjęcia po kliknięciu wyświetlają się w lightboxie na białym tle.

## Instrukcja Aktualizacji
Po dodaniu nowych zdjęć do folderów w `photos/`, należy uruchomić skrypt:
`python3 build.py`
Skrypt wygeneruje brakujące miniatury i zaktualizuje wszystkie pliki HTML.

