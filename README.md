# Kalendarz Wydarzeń — Rabka-Zdrój

Statyczna strona z kalendarzem wydarzeń w Rabce-Zdroju, tworzona dla Fundacji Rozwoju Regionu Rabka (https://frrr.pl/), łącząca:

- **dane importowane automatycznie** co tydzień z [rabka.pl/kalendarz-wydarzen/](https://rabka.pl/kalendarz-wydarzen/) (`data/events-auto.json`),
- **dane importowane automatycznie** co tydzień z [centrum-kultury.rabka.pl](https://centrum-kultury.rabka.pl/) — CKSiP, faktyczny organizator większości wydarzeń kulturalnych (`data/events-cksip.json`),
- **dane importowane automatycznie** co tydzień z repertuaru [Teatru Lalek Rabcio](https://teatr.rabcio.pl/) — terminy spektakli z systemu biletowego Bilety24 (`data/events-rabcio.json`),
- **dane wpisywane ręcznie** przez Fundację (`data/events-manual.json`).

Wydarzenia ze wszystkich automatycznych źródeł są łączone i odduplikowywane (po tytule + dacie startu) zarówno na stronie, jak i w pliku `.ics`.

Strona jest w 100% statyczna (HTML/CSS/JS, bez backendu) — można ją hostować bezpłatnie na GitHub Pages.

## Struktura projektu

```
index.html                          strona główna (kalendarz)
style.css                           style
app.js                              logika kalendarza (pobiera i łączy pliki JSON)
data/events-auto.json               wydarzenia z Urzędu (nadpisywane co tydzień przez scraper)
data/events-cksip.json              wydarzenia z CKSiP (nadpisywane co tydzień przez scraper)
data/events-rabcio.json             spektakle Teatru Lalek Rabcio (nadpisywane co tydzień)
data/events-manual.json             wydarzenia dodane ręcznie — EDYTUJ TEN PLIK
events.ics                          wygenerowany plik subskrypcji kalendarza (wszystkie źródła)
scraper/scraper.py                  skrypt pobierający dane z rabka.pl
scraper/scraper_cksip.py            skrypt pobierający dane z centrum-kultury.rabka.pl
scraper/scraper_rabcio.py           skrypt pobierający repertuar Rabcia (Bilety24)
scraper/generate_ics.py             łączy wszystkie pliki JSON w events.ics
.github/workflows/update-events.yml automatyzacja: uruchamia scrapery + generator .ics co poniedziałek
```

## Jak dodać wydarzenie ręcznie (bez znajomości kodu)

1. Otwórz stronę i kliknij **„+ Dodaj wydarzenie”**, wypełnij formularz i kliknij **„Wygeneruj wpis”**.
2. Skopiuj wygenerowany fragment JSON.
3. Kliknij **„Otwórz events-manual.json na GitHub”** — otworzy się prosty edytor tekstowy w przeglądarce.
4. Wklej skopiowany fragment do tablicy `"events"` (jako kolejny element, pamiętaj o przecinku między wpisami).
5. Na dole strony kliknij **„Commit changes”**.
6. Strona (GitHub Pages) zaktualizuje się automatycznie w ciągu ok. 1 minuty.

Możesz też edytować `data/events-manual.json` bezpośrednio — to zwykły plik JSON, każdy wpis ma pola: `id`, `title`, `category` (`kultura` / `sport` / `dzieci` / `historia` / `samorzad`), `start`, `end`, `time`, `location`, `url`, `desc`.

## Jak działa import automatyczny

`scraper/scraper.py` pobiera stronę `rabka.pl/kalendarz-wydarzen/` i heurystycznie wyciąga z niej wydarzenia (nie ma tam publicznego API ani RSS). GitHub Actions uruchamia ten skrypt co poniedziałek i commituje zmiany do `data/events-auto.json` automatycznie.

**Ograniczenie, o którym warto wiedzieć:** ten typ scrapowania jest z natury kruchy — jeśli Urząd zmieni szablon strony, skrypt przestanie poprawnie wyciągać dane (zwykle nie "zepsuje się" cicho — zobaczysz brak nowych wydarzeń albo błąd w logach GitHub Actions). Zdecydowanie warto zapytać opiekuna projektu w Urzędzie, czy mogliby udostępniać prosty eksport (CSV/JSON) wydarzeń — to dużo trwalsze rozwiązanie niż scraping.

Żeby ręcznie uruchomić import (np. po zmianach w skrypcie): zakładka **Actions** w repozytorium → **Update events from rabka.pl** → **Run workflow**.

## Subskrypcja kalendarza (.ics)

Przycisk **„📅 Subskrybuj kalendarz”** na stronie prowadzi do pliku `events.ics`, wygenerowanego z połączonych danych ze wszystkich źródeł. Każdy może:

1. Skopiować link do tego pliku (po opublikowaniu na GitHub Pages będzie to np. `https://extraterestra.github.io/rabka-wydarzenia-kalendarz/events.ics`).
2. Dodać go w Google Calendar (**Inne kalendarze → Z adresu URL**), Apple Calendar (**Plik → Nowa subskrypcja kalendarza**) lub Outlooku.
3. Kalendarz w ich aplikacji będzie się odświeżał automatycznie za każdym razem, gdy GitHub Actions zaktualizuje `events.ics` (czyli co poniedziałek).

Plik jest regenerowany automatycznie przy każdym uruchomieniu workflow — nie trzeba go edytować ręcznie.

## Uruchomienie lokalne

```bash
# podgląd strony lokalnie
python3 -m http.server 8000
# otwórz http://localhost:8000

# ręczne uruchomienie scrapera
pip install requests beautifulsoup4
python scraper/scraper.py
```

## Publikacja na GitHub Pages

1. W ustawieniach repozytorium: **Settings → Pages**.
2. **Source**: `Deploy from a branch`, branch: `main`, folder: `/ (root)`.
3. Po chwili strona będzie dostępna pod adresem `https://<użytkownik>.github.io/<repo>/`.

## Rozwój na przyszłość

- Dodanie eksportu `.ics` (subskrypcja kalendarza w Google/Apple Calendar).
- Zamiana ręcznego workflow "generuj JSON → wklej na GitHub" na formularz GitHub Issue + automatyczne przetwarzanie (mniej kliknięć dla osób nietechnicznych).
- Jeśli Urząd udostępni oficjalny feed danych — podmiana `scraper.py` na prosty import tego feedu (mniej kruche niż scraping HTML).
