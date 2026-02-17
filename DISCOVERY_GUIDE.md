# 🤖 Company Discovery System Guide

## Overview

Your job board has an **automatic company discovery system** that:
- 🔍 Uses Google Search to find company career pages
- 🎯 Detects which ATS system they use (Greenhouse, Lever, Ashby, Workable)
- 💾 Automatically adds them to your database
- ✅ Verifies the ATS URL works before saving

---

## 🚀 Quick Start

### Method 1: Single Company Discovery

```bash
# Discover one company at a time
python us_ats_jobs/scripts/discover_companies.py "Stripe"
python us_ats_jobs/scripts/discover_companies.py "Netflix"
```

### Method 2: Multiple Companies (Command Line)

```bash
# Discover multiple companies in one command
python us_ats_jobs/scripts/discover_companies.py "Stripe" "Netflix" "Uber" "Lyft"
```

### Method 3: Bulk Discovery (Recommended)

```bash
# 1. Edit bulk_discover.py and add your company names
# 2. Run the bulk discovery script
python bulk_discover.py
```

### Method 4: Quick Demo

```bash
# Test the discovery system with 3 example companies
python quick_discover_demo.py
```

---

## 📝 How to Add Companies to Bulk Discovery

1. **Open** `bulk_discover.py`

2. **Add company names** to the `COMPANIES_TO_DISCOVER` list:

```python
COMPANIES_TO_DISCOVER = [
    # Your companies here
    "Stripe",
    "Shopify",
    "Square",
    "Your Company Name",
    # ... add more
]
```

3. **Run** the script:

```bash
python bulk_discover.py
```

---

## 🔧 How Discovery Works

### Step 1: Google Search
- Searches for `"Company Name careers"`
- Gets top 3 results

### Step 2: ATS Detection
The system checks for these ATS providers:
- **Greenhouse**: `boards.greenhouse.io/[slug]`
- **Lever**: `jobs.lever.co/[slug]`
- **Ashby**: `jobs.ashbyhq.com/[slug]`
- **Workable**: `apply.workable.com/[slug]`

### Step 3: Verification
- Attempts to access the ATS URL
- Returns HTTP 200 = ✅ Valid
- Returns HTTP 404 = ❌ Invalid

### Step 4: Database Save
- Saves company name, ATS URL, provider type
- Marks company as "active" by default
- Skips if already in database

---

## 📊 What Gets Saved

For each discovered company, the database stores:

| Field | Example |
|-------|---------|
| **Name** | Stripe |
| **ATS URL** | https://boards-api.greenhouse.io/v1/boards/stripe/jobs |
| **ATS Provider** | greenhouse |
| **Career Page** | https://stripe.com/careers |
| **Domain** | stripe.com |
| **Active** | True |

---

## 🎯 Company Suggestions by Category

### Tech Giants
```python
"Meta", "Amazon", "Apple", "Google", "Microsoft", 
"Netflix", "Tesla", "Uber", "Lyft", "Airbnb"
```

### AI/ML Companies
```python
"OpenAI", "Anthropic", "Hugging Face", "Stability AI",
"Cohere", "Midjourney", "Replicate", "Runway"
```

### Fintech
```python
"Stripe", "Square", "PayPal", "Coinbase", "Plaid",
"Brex", "Ramp", "Mercury", "Mercury"
```

### Startups (YC)
```python
"Vercel", "Supabase", "Railway", "Fly.io", "Render",
"PlanetScale", "Neon", "Convex", "Clerk"
```

### Enterprise SaaS
```python
"Salesforce", "ServiceNow", "Workday", "SAP", "Oracle",
"Atlassian", "HubSpot", "Zendesk", "Twilio"
```

### Gaming
```python
"Epic Games", "Riot Games", "Unity", "Roblox", 
"Discord", "Supercell", "Valve"
```

### E-commerce
```python
"Shopify", "Etsy", "Wayfair", "Instacart", "DoorDash",
"Postmates", "GrubHub", "Deliveroo"
```

### Security
```python
"Palo Alto Networks", "Crowdstrike", "Okta", "Auth0",
"1Password", "Bitwarden", "Snyk"
```

---

## 🐛 Troubleshooting

### Error: "googlesearch-python not installed"

**Solution:**
```bash
pip install googlesearch-python
```

### Rate Limiting (429 Error)

The script has built-in rate limiting protection:
- Waits 2 seconds between companies
- Exponential backoff for 429 errors
- Retries up to 3 times

**If you still get rate limited:**
- Add more delay between companies
- Use smaller batches
- Run discovery overnight

### Company Not Found

**Reasons:**
1. Company doesn't use a supported ATS
2. Career page is behind login
3. Company name spelling is different

**Solutions:**
- Try alternative company names
- Check their careers page manually
- Add manually to config.py if you know their ATS

---

## 💡 Pro Tips

### 1. Run Discovery Overnight
```python
# Add 500+ companies to bulk_discover.py
# Run before bed
# Wake up to a full database!
python bulk_discover.py
```

### 2. Discover from Lists
Find company lists online:
- YCombinator companies
- Forbes Cloud 100
- Fortune 500 tech companies
- Breakout List startups

### 3. Use with JSearch
Your main.py already has a feeder system that discovers new companies found via JSearch!

### 4. Verify After Discovery
```bash
# Check what was added
python show_cb_status.py
```

---

## 📈 Next Steps After Discovery

1. **Verify companies were added:**
   ```bash
   python diag_db.py
   ```

2. **Fetch jobs from new companies:**
   ```bash
   python us_ats_jobs/main.py
   ```

3. **View results:**
   - Jobs are saved to the database
   - Circuit breaker prevents failed companies from being retried
   - Successfully fetched companies will show job counts

---

## 🔗 Related Files

- **Discovery Script**: `us_ats_jobs/scripts/discover_companies.py`
- **Bulk Discovery**: `bulk_discover.py`
- **Database**: `us_ats_jobs/db/jobs.db`
- **Config**: `us_ats_jobs/config.py`

---

## ⚡ Example Workflow

```bash
# 1. Add 50 companies to bulk_discover.py
# 2. Run discovery
python bulk_discover.py

# 3. Check database
python diag_db.py

# 4. Fetch jobs
python us_ats_jobs/main.py

# 5. View results - You should see new companies in the job breakdown!
```

---

**Happy Discovering! 🎉**
