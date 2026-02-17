
export interface JobEnrichment {
    tech_languages?: string;
    tech_frameworks?: string;
    tech_cloud?: string;
    tech_data?: string;
    tech_tools?: string;
    experience_years?: number;
    education_level?: string;
    seniority_tier?: string;
    seniority_level?: number;
    certifications?: string;
    soft_skills?: string;
    job_summary?: string;
}

export interface CompanyDetails {
    name: string;
    domain?: string;
    ats_provider?: string;
}

export interface Job {
    job_id: string;
    title: string;
    company: string;
    location?: string;
    normalized_location?: string;
    city?: string;
    state?: string;
    country?: string;
    job_description?: string;
    job_summary?: string;  // Short summary for cards
    job_link: string;
    source: string;
    date_posted?: string;
    posted_bucket?: string;
    is_remote: boolean;
    work_mode?: string;
    seniority?: string;
    department?: string;
    department_category?: string;
    department_subcategory?: string;
    salary_min?: number;
    salary_max?: number;
    salary_currency?: string;
    visa_sponsorship?: string;
    visa_confidence?: number;
    experience_years?: number;  // From enrichment
    enrichment?: JobEnrichment;
    company_details?: CompanyDetails;

    // New Fields for Job Card
    logo_url?: string;
    skills?: string[];
    ingested_at?: string;
    employment_type?: string;

    // Computed helpers (will often come from parsing enrichment string)
    tech_stack?: string[];
}

export interface CompanyListItem {
    id: number;
    name: string;
    domain?: string;
    ats_provider?: string;
    active_jobs_count: number;
    last_scraped_at?: string;
}

export interface FilterOptions {
    locations: string[];
    departments: Record<string, string[]>;
    tech_languages: string[];
    tech_frameworks: string[];
    ats_providers: string[];
    seniority_levels: string[];
    work_modes: string[];
}

export interface SearchParams {
    q?: string;
    location?: string;
    remote?: boolean;
    tech_stack?: string;
    department?: string;
    department_category?: string;
    department_subcategory?: string;
    min_salary?: number;
    max_salary?: number;
    visa_sponsorship?: string;
    remote_policy?: string;
    seniority?: string;
    posted_since?: string;
    sort?: string;
    page?: number;
    limit?: number;
}
