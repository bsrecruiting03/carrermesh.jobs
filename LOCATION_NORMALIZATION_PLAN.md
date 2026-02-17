# Location Normalization Plan

## Goal
Standardize location data so that searches for "USA" or "United States" return all relevant results, regardless of formatting (e.g., "New York, NY", "Remote, USA").

## 1. Libraries
We will use:
- **`pycountry`**: For Country standarization (ISO 3166). Matches "United States", "USA", "US" -> "US" (or "United States" depending on preference).
- **`us`**: A powerful library for parsing US state abbreviations and names ("California" <-> "CA").

## 2. Database Schema
The `jobs` table already has `city`, `state`, `country` columns (as seen in `api/database.py`).
We will populate these columns which are currently likely inconsistent or empty.

## 3. Normalization Logic (The "Ontology")
We will implement a `LocationNormalizer` class:
1.  **Parse String**: Split "City, State, Country" or "City, State".
2.  **Country Detection**:
    -   Detect "United States", "USA", "US".
    -   Normalize to **`USA`** (User preferred format).
3.  **State Detection**:
    -   Use `us` library to identify state codes (e.g., "FL", "Florida") -> "FL".
4.  **City Detection**:
    -   Remainder is City.

## 4. Execution Steps
1.  Install `pycountry`, `us`.
2.  Create `scripts/normalize_locations.py`.
3.  Run script to backfill `jobs` table.
4.  Verify search with `/api/jobs/suggest`.
