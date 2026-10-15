# Répertoire postal marocain — Android/Kivy

Projet préparé à partir du classeur fourni `codes_postaux_localites_avec_site_destination.xlsx`.

## Données intégrées
- Lignes importées du classeur : 1770
- CSV embarqué : `data/localites_postales.csv`
- Champs : région, province, localité, code postal, site de destination.
- La colonne « site de destination » reste vide dans les données d'origine, prête à être complétée.

Le nombre de lignes reflète les enregistrements importés du classeur, pas une certification d'exhaustivité ni d'actualité du répertoire national.

## Compilation APK avec GitHub Actions
1. Créez un dépôt GitHub.
2. Téléversez tous les fichiers et dossiers de cette archive en conservant `.github/workflows/build-apk.yml`.
3. Faites un commit sur `main`.
4. Ouvrez **Actions** → **Compiler APK Android** → **Run workflow** (ou attendez le déclenchement après un push).
5. Quand le workflow est terminé, ouvrez le run puis téléchargez l'artefact `repertoire-postal-marocain-apk` dans **Artifacts**.
6. Décompressez l'archive téléchargée pour récupérer le `.apk`, puis transférez-le sur Android.

## Lancer sur ordinateur pour développement
Installez Python puis :
```bash
python -m venv .venv
# Windows : .venv\\Scripts\\activate
# Linux/macOS : source .venv/bin/activate
python -m pip install kivy
python main.py
```

La compilation APK se fait sur Linux via GitHub Actions, pas directement dans l'environnement Python Windows.

## Limites
- L'application permet la recherche hors ligne et le filtre par région.
- Vous pouvez ajouter une localité ou modifier ses cinq champs : localité, code postal, province, région et site de destination.
- Les modifications sont enregistrées dans SQLite sur le téléphone et persistent entre les lancements.
- Le bouton « Exporter CSV » crée un export des données modifiées dans le dossier privé de l'application. Selon Android, ce fichier n'est pas automatiquement visible dans le gestionnaire de fichiers.
- Le bouton « Réimporter CSV » explique la procédure manuelle et n'écrase pas les données, pour éviter une perte accidentelle.
- APK généré en mode debug, destiné aux tests et à l'installation manuelle, pas à la publication Play Store.
