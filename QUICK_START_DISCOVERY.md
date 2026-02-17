# 🎯 Quick Reference: Company Discovery

## ✅ You're Ready to Use Discovery!

### 📦 What I Created for You:

1. **`bulk_discover.py`** - Main script for discovering multiple companies
2. **`quick_discover_demo.py`** - Test script with 3 example companies
3. **`DISCOVERY_GUIDE.md`** - Complete documentation

---

## 🚀 Start Here (3 Steps):

### Step 1: Test Discovery (1 minute)
```bash
python quick_discover_demo.py
```
This will discover 3 companies: Vercel, Supabase, Railway

### Step 2: Add Your Companies (5 minutes)
Open `bulk_discover.py` and modify this section:
```python
COMPANIES_TO_DISCOVER = [
    "Your Company 1",
    "Your Company 2",
    # Add as many as you want!
]
```

### Step 3: Run Bulk Discovery
```bash
python bulk_discover.py
```

---

## 📊 Company Ideas (Copy & Paste)

### AI Companies (Hot Right Now! 🔥)
```
Meta, Anthropic, Hugging Face, Stability AI, Cohere, Midjourney, Replicate, Runway, Character.AI, Perplexity
```

### Top YC Startups
```
Vercel, Supabase, Railway, PlanetScale, Neon, Convex, Clerk, Resend, Upstash, Turso
```

### FAANG+
```
Meta, Amazon, Apple, Netflix, Microsoft, Tesla, Uber, Lyft, Airbnb, Spotify
```

### Fintech
```
Stripe, Square, Plaid, Coinbase, Brex, Ramp, Mercury, Chime, Robinhood, Affirm
```

### Gaming
```
Epic Games, Riot Games, Unity, Roblox, Discord, Supercell, Valve, Activision Blizzard
```

---

## 🎬 Example: Add 10 AI Companies

1. Open `bulk_discover.py`
2. Replace the list with:
```python
COMPANIES_TO_DISCOVER = [
    "Anthropic",
    "Hugging Face", 
    "Stability AI",
    "Cohere",
    "Replicate",
    "Runway",
    "Character.AI",
    "Perplexity",
    "Together AI",
    "Mistral AI",
]
```
3. Run: `python bulk_discover.py`
4. Wait 2-3 minutes
5. Run: `python us_ats_jobs/main.py` to fetch jobs!

---

## ⚡ What Discovery Does

```
Company Name → Google Search → Find Career Page → Detect ATS → Save to Database
```

**Supported ATS:**
- ✅ Greenhouse
- ✅ Lever  
- ✅ Ashby
- ✅ Workable

---

## 💡 Pro Tips

1. **Start small** - Test with 5-10 companies first
2. **Check results** - Run `python diag_db.py` to see what was added
3. **Run overnight** - Add 100+ companies and let it run while you sleep
4. **No duplicates** - Discovery automatically skips companies already in database

---

## 🐛 Common Issues

**"googlesearch-python not installed"**
```bash
pip install googlesearch-python
```
✅ Already installed for you!

**Rate limiting**
- Discovery has built-in delays (2 sec between companies)
- Just let it run, it will retry automatically

**Company not found**
- Try different name variations
- Some companies don't use supported ATS systems
- Check their careers page manually

---

## 📈 After Discovery

1. **Verify**: `python diag_db.py`
2. **Fetch Jobs**: `python us_ats_jobs/main.py`
3. **Check Output**: Look for new companies in the job breakdown!

---

**Ready? Run this to get started:**
```bash
python quick_discover_demo.py
```

🎉 **Happy Discovering!**
