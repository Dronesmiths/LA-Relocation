# SEO Worker Engine - LA Relocation

This is a portable SEO orchestration suite used to manage technical SEO, programmatic content growth, and search authority.

## 🚀 Setup Instructions

1. **Google Identity**: Place your `service-account.json` in this root folder (`seo-worker-engine/`).
2. **Sheet ID**: Update the `SPREADSHEET_ID` in `config.json` with your SEO Brain Sheet ID.
3. **Dependencies**: Ensure `bs4` and `google-api-python-client` are installed.
   ```bash
   pip install beautifulsoup4 google-api-python-client google-auth-oauthlib
   ```

## 🛠️ Usage

### 🗺️ Regenerate Sitemap
Crawls local files and updates the root `sitemap.xml`.
```bash
python3 core/seo_factory.py --sitemap
```

### 🔄 Sync with Google Sheet
Audits local pages, fetches GSC data, and updates the SEO Brain Sheet.
```bash
python3 core/seo_factory.py --sync
```

## 📂 Structure
- `config.json`: Project settings and URL mappings.
- `core/`: Engine logic and templates.
- `core/registries/`: JSON strategy data (Cornerstones, Plans).
- `core/templates/`: HTML components for content generation.
