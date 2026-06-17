# Deployment — krok po kroku

## Jak to działa

```
master branch          gh-pages branch
──────────────         ───────────────
local_engine/          index.html
design_template/  →    style.css
build.py          →    main.js
photos/           →    photos/
articles/         →    (tylko media/)
*.py, *.toml           tymancjo/
*_template.html        .nojekyll
```

Każdy push do `master` → GitHub Actions uruchamia `build.py` → wysyła tylko pliki publiczne na branch `gh-pages` → GitHub Pages serwuje `gh-pages`.

Silnik lokalny (`local_engine/`) nigdy nie trafia na publiczną stronę.

---

## Pierwsze uruchomienie (jednorazowo)

### Krok 1 — wypchnij zmiany na GitHub

```bash
git add .
git commit -m "Add GitHub Actions deploy workflow"
git push origin master
```

### Krok 2 — poczekaj na Actions

1. Otwórz repo na GitHub
2. Kliknij zakładkę **Actions**
3. Poczekaj, aż workflow `Build & Deploy` się ukończy (zielony ptaszek ✓)
4. Po sukcesie automatycznie pojawi się branch `gh-pages`

### Krok 3 — skonfiguruj GitHub Pages

1. Otwórz repo na GitHub → **Settings**
2. Lewy panel → **Pages**
3. W sekcji **Build and deployment** ustaw:
   - Source: **Deploy from a branch**
   - Branch: **gh-pages** / **(root)**
4. Kliknij **Save**

Po chwili (1–2 minuty) strona będzie dostępna pod adresem:
```
https://tymancjo.github.io/portfolio/
```

---

## Codzienna praca

### Dodaj zdjęcia / edytuj treść lokalnie

```bash
# Uruchom silnik lokalny
uv run --extra local python local_engine/app.py
# → http://127.0.0.1:5001
```

### Zbuduj i wypchnij

```bash
uv run python build.py          # przebuduj HTML lokalnie (opcjonalne)
git add .
git commit -m "Opis zmian"
git push origin master          # Actions automatycznie buduje i deployuje
```

Nie musisz ręcznie uruchamiać `build.py` przed pushem — Actions robi to za Ciebie w CI.

---

## Zdjęcia w artykułach

Zdjęcia wgrane przez edytor artykułów lądują w `articles/<slug>/media/` i są automatycznie kopiowane na `gh-pages` podczas deploymentu.

**Ważne:** Stare artykuły, które zawierają ścieżki `/article-media/slug/plik.jpg` (stary format), wymagają ręcznej korekty w Markdown — zamień na:
```
articles/slug/media/plik.jpg
```
Nowe wgrania już używają poprawnego formatu.

---

## Troubleshooting

| Problem | Rozwiązanie |
|---------|-------------|
| Actions workflow nie startuje | Sprawdź, czy plik `.github/workflows/deploy.yml` jest w repo |
| Strona pokazuje stary content | Actions może być w trakcie — odczekaj ~2 min i odśwież |
| 404 na GitHub Pages | Sprawdź Settings → Pages czy branch to `gh-pages` |
| Zdjęcia nie ładują się | Upewnij się, że `uv run python build.py` przeszło bez błędów (generuje miniaturki) |
