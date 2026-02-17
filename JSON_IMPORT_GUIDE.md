# 📥 JSON Import Guide

## Quick Start

### 1. Prepare Your JSON File

Create or edit `companies.json` with this format:

```json
{
  "greenhouse": [
    "stripe",
    "airbnb",
    "coinbase"
  ],
  "lever": [
    "spotify",
    "atlassian",
    "netflix"
  ],
  "ashby": [
    "notion",
    "linear",
    "openai"
  ],
  "workable": [
    "canva",
    "hubspot"
  ],
  "bamboohr": [
    "example-company"
  ]
}
```

### 2. Run the Import

```bash
python import_from_json.py
```

Or specify a custom JSON file:

```bash
python import_from_json.py my_companies.json
```

### 3. Fetch Jobs

```bash
python us_ats_jobs/main.py
```

---

## 🎯 JSON Structure

The JSON file should be an object with **ATS provider names as keys** and **arrays of company slugs as values**.

### Supported ATS Providers:

- `greenhouse` - https://boards.greenhouse.io/[slug]
- `lever` - https://jobs.lever.co/[slug]
- `ashby` - https://jobs.ashbyhq.com/[slug]
- `workable` - https://apply.workable.com/[slug]
- `bamboohr` - https://[slug].bamboohr.com/jobs ✨ NEW!

---

## 📋 Finding Company Slugs

### Greenhouse
Visit: `https://boards.greenhouse.io/[company-name]`
- Example: `https://boards.greenhouse.io/stripe` → slug is `stripe`

### Lever
Visit: `https://jobs.lever.co/[company-name]`
- Example: `https://jobs.lever.co/netflix` → slug is `netflix`

### Ashby
Visit: `https://jobs.ashbyhq.com/[company-name]`
- Example: `https://jobs.ashbyhq.com/notion` → slug is `notion`

### Workable
Visit: `https://apply.workable.com/[company-name]`
- Example: `https://apply.workable.com/canva` → slug is `canva`

### BambooHR
Visit: `https://[company-name].bamboohr.com/jobs`
- Example: `https://acme.bamboohr.com/jobs` → slug is `acme`

---

## 💡 Tips

### 1. Use Multiple Files

Organize by category:
```bash
python import_from_json.py tech_giants.json
python import_from_json.py startups.json
python import_from_json.py fintech.json
```

### 2. Mix and Match

Your JSON can include all ATS types in one file:
```json
{
  "greenhouse": ["company1", "company2", ...],
  "lever": ["company3", "company4", ...],
  "ashby": ["company5", "company6", ...],
  "workable": ["company7", "company8", ...],
  "bamboohr": ["company9", "company10", ...]
}
```

### 3. Duplicate Safety

The import script automatically skips companies already in the database. Run it multiple times without worry!

---

## 📊 Example Import Session

```bash
$ python import_from_json.py

================================================================================
📥 IMPORTING COMPANIES FROM JSON
================================================================================

Reading from: companies.json

📦 Processing GREENHOUSE (50 companies)
--------------------------------------------------------------------------------
  ✅ Added: stripe
  ✅ Added: airbnb
  ⏭️  Skipped (already exists): coinbase
  ...

📦 Processing LEVER (30 companies)
--------------------------------------------------------------------------------
  ✅ Added: spotify
  ✅ Added: netflix
  ...

📦 Processing BAMBOOHR (10 companies)
--------------------------------------------------------------------------------
  ✅ Added: acme
  ✅ Added: example-co
  ...

================================================================================
📊 IMPORT SUMMARY
================================================================================

✅ Total Added: 78
⏭️  Total Skipped: 12
📈 Total Processed: 90

📊 Breakdown by ATS:

  GREENHOUSE:
    - Total: 50
    - Added: 45
    - Skipped: 5

  LEVER:
    - Total: 30
    - Added: 28
    - Skipped: 2

  BAMBOOHR:
    - Total: 10
    - Added: 5
    - Skipped: 5

================================================================================
🎉 Import Complete!
================================================================================

💡 Next Steps:
   1. Run 'python us_ats_jobs/main.py' to fetch jobs
   2. Run 'python diag_db.py' to verify imports
```

---

## 🆕 BambooHR Support

BambooHR is now fully integrated! 🎉

### What was added:
- ✅ BambooHR job fetcher (`sources/bamboohr.py`)
- ✅ BambooHR normalizer (`normalizer.py`)
- ✅ BambooHR integration in main.py
- ✅ BambooHR discovery support
- ✅ BambooHR JSON import support

### BambooHR Slug Format:
Unlike other ATS systems, BambooHR uses **subdomains**:
- URL: `https://[SLUG].bamboohr.com/jobs`
- Example: `https://acme.bamboohr.com/jobs`
- Slug: `acme`

---

## 🔍 How to Find If a Company Uses BambooHR

1. **Google Search:** "[Company Name] careers"
2. **Check Career Page:** Look for URLs like `*.bamboohr.com/jobs`
3. **Use Discovery:** `python us_ats_jobs/scripts/discover_companies.py "Company Name"`

---

## 🚨 Common Issues

### "Unknown ATS provider"
- Check spelling in your JSON (must be lowercase)
- Supported: `greenhouse`, `lever`, `ashby`, `workable`, `bamboohr`

### "Invalid JSON format"
- Validate your JSON at jsonlint.com
- Make sure to use double quotes `"` not single quotes `'`
- Don't forget commas between items

### "File not found"
- Make sure `companies.json` is in the same directory as `import_from_json.py`
- Or provide the full path: `python import_from_json.py "c:/path/to/file.json"`

---

## 📁 Template Files

I've created `companies.json` with examples for each ATS type. 

**Edit this file** and add your own companies!

---

## 🎬 Complete Workflow

```bash
# 1. Edit your JSON file with company slugs
notepad companies.json

# 2. Import companies to database
python import_from_json.py

# 3. Verify import
python diag_db.py

# 4. Fetch jobs from all companies
python us_ats_jobs/main.py

# 5. View results! 🎉
```

---

**Ready to import? Edit `companies.json` and run `python import_from_json.py`!**
