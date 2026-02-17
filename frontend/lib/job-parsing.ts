
import { Job } from './types';

export interface JobInsights {
    responsibilities: string[];
    requirements: string[];
    yoe: string | null;
    tools: string[];
    education: string | null;
    jobType: string | null;
}


/**
 * Formats a company name/slug into a readable string.
 * e.g. "google-inc" -> "Google Inc", "amazon_web_services" -> "Amazon Web Services"
 */
export function formatCompanyName(name: string): string {
    if (!name) return '';

    // If it looks like a domain (has .com, .io, etc), leave it or strip protocol
    if (name.includes('.') && !name.includes(' ')) return name;

    return name
        .replace(/[-_]/g, ' ')
        .split(' ')
        .map(word => {
            // Keep specific small words lowercase unless they are the first word
            const lowercaseWords = ['of', 'and', 'the', 'in', 'at', 'for'];
            if (lowercaseWords.includes(word.toLowerCase())) return word.toLowerCase();
            return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
        })
        .join(' ')
        // Fix Capitalization for first word if it was a small word
        .replace(/^\w/, c => c.toUpperCase());
}

/**
 * Heuristically extracts years of experience from text.
 * Looks for patterns like "3+ years", "5-7 years", etc.
 */
export function extractYOE(text: string): string | null {
    if (!text) return null;

    // Regex for common YOE patterns
    // 1. "5+ years", "5 + years"
    // 2. "3-5 years", "3 - 5 years"
    // 3. "at least 3 years"
    // 4. "minimum of 3 years"
    const patterns = [
        /(\d+)\s*\+\s*years?/i,
        /(\d+)\s*[-–to]\s*(\d+)\s*years?/i,
        /at\s*least\s*(\d+)\s*years?/i,
        /minimum\s*(?:of\s*)?(\d+)\s*years?/i,
        /(\d+)\s*years?\s*of\s*experience/i
    ];

    for (const pattern of patterns) {
        const match = text.match(pattern);
        if (match) {
            if (match[2]) {
                // Range match (e.g., 3-5)
                return `${match[1]}-${match[2]} YOE`;
            }
            // Single value match (e.g., 5+)
            return `${match[1]}+ YOE`;
        }
    }

    return null;
}

/**
 * Extracts approximate salary if strictly mentioned in format $100k-$150k or $100,000
 */
export function extractSalary(text: string): string | null {
    if (!text) return null;

    // Look for "$100k - $150k" or "$100,000 - $150,000"
    // This is very heuristic and conservative to avoid false positives
    const rangePattern = /\$(\d{1,3}(?:,\d{3})*|(?:\d{2,3}k))\s*[-–to]\s*\$(\d{1,3}(?:,\d{3})*|(?:\d{2,3}k))/i;
    const match = text.match(rangePattern);

    if (match) {
        return `${match[1]} - ${match[2]}`;
    }
    return null;
}

/**
 * Detects Visa Sponsorship mentions
 */
export function extractVisaInfo(text: string): string | null {
    const lower = text.toLowerCase();
    if (lower.includes('visa sponsorship') || lower.includes('sponsorship available') || lower.includes('will sponsor')) {
        return "Sponsorship Available";
    }
    if (lower.includes('no sponsorship') || lower.includes('cannot sponsor') || lower.includes('requires us citizenship')) {
        return "No Sponsorship";
    }
    return null;
}

/**
 * Cleans HTML tags from text
 */
function stripHtml(html: string): string {
    if (!html) return '';
    return html.replace(/<[^>]*>?/gm, ' ')
        .replace(/&nbsp;/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
}

/**
 * Extracts bullet points from a section of text
 */
function extractBulletPoints(text: string, maxItems: number = 2): string[] {
    // Split by common bullet delimiters
    // Improved split to handle <br>, <li> if they leaked through parsing or plain text bullets
    const lines = text.split(/•|·|-|\*|\d+\.|<br\s*\/?>|\n/);

    // Filter out empty lines or lines that are likely just headers
    const points = lines
        .map(line => line.trim())
        .filter(line => line.length > 20 && line.length < 200) // Filter too short (garbage) or too long (paragraphs)
        .slice(0, maxItems);

    return points;
}

/**
 * Main parser function to extract insights from raw job description
 */
export function extractJobInsights(job: Job): JobInsights {
    // Use job_summary from API if available, otherwise use full description
    const description = job.job_summary || job.job_description || '';

    // Normalize company name (fix slugs)
    // const formattedCompany = formatCompanyName(job.company); // Unused

    const cleanDesc = stripHtml(description); // Simple plain text version for easier regex
    const lowerDesc = cleanDesc.toLowerCase();

    const insights: JobInsights = {
        responsibilities: [],
        requirements: [],
        yoe: null,
        tools: job.tech_stack || [], // Use pre-computed stack if available
        education: null,
        jobType: null
    };

    // 1. Extract YOE
    // Check enrichment and direct fields first, then parse description
    if (job.experience_years) {
        insights.yoe = `${job.experience_years}+ YOE`;
    } else if (job.enrichment?.experience_years) {
        insights.yoe = `${job.enrichment.experience_years}+ YOE`;
    } else {
        // Search in the first 1000 chars first (usually in summary/requirements), then full text
        insights.yoe = extractYOE(cleanDesc.substring(0, 1000)) || extractYOE(cleanDesc);
    }

    // 2. Extract Responsibilities
    // Strategy: Find "Responsibilities" keyword and take the next few plausible bullet points from the HTML
    const respKeywords = ['responsibilities', 'what you will do', 'duties', 'role overview', 'about the role'];
    let respSection = '';

    for (const keyword of respKeywords) {
        const idx = description.toLowerCase().indexOf(keyword);
        if (idx !== -1) {
            // Take the next 1500 characters
            respSection = stripHtml(description.substring(idx + keyword.length, idx + 1500));
            break;
        }
    }

    if (respSection) {
        insights.responsibilities = extractBulletPoints(respSection, 2);
    }

    // 3. Extract Requirements
    const reqKeywords = ['requirements', 'qualifications', 'who you are', 'what you need', 'what we look for', 'skills'];
    let reqSection = '';

    for (const keyword of reqKeywords) {
        const idx = description.toLowerCase().indexOf(keyword);
        if (idx !== -1) {
            reqSection = stripHtml(description.substring(idx + keyword.length, idx + 1500));
            break;
        }
    }

    if (reqSection) {
        insights.requirements = extractBulletPoints(reqSection, 2);
    }

    // 4. Extract Education / Degree
    if (job.enrichment?.education_level) {
        insights.education = job.enrichment.education_level;
    } else {
        if (lowerDesc.includes('phd') || lowerDesc.includes('ph.d')) insights.education = 'PhD';
        else if (lowerDesc.includes('master')) insights.education = 'Master\'s';
        else if (lowerDesc.includes('bachelor') || lowerDesc.includes('bs degree') || lowerDesc.includes('computer science degree')) insights.education = 'Bachelor\'s';
    }

    // 5. Extract Job Type
    if (lowerDesc.includes('contract') || lowerDesc.includes('contractor') || lowerDesc.includes('freelance')) insights.jobType = 'Contract';
    else if (lowerDesc.includes('intern') || lowerDesc.includes('internship')) insights.jobType = 'Internship';
    else if (lowerDesc.includes('part-time') || lowerDesc.includes('part time')) insights.jobType = 'Part Time';
    else insights.jobType = 'Full Time'; // Default to Full Time if nothing else found


    // Fallback: If tech stack is empty, look for common keywords in description
    if (insights.tools.length === 0) {
        const commonTools = ['React', 'Python', 'Java', 'AWS', 'Node', 'TypeScript', 'SQL', 'Docker', 'Kubernetes', 'Go', 'C++', 'Rust', 'Azure', 'GCP'];
        const foundTools = new Set<string>();
        commonTools.forEach(tool => {
            // Escape special regex characters (e.g., the + in C++)
            const escapedTool = tool.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            const regex = new RegExp(`\\b${escapedTool}\\b`, 'i');
            if (regex.test(cleanDesc)) {
                foundTools.add(tool);
            }
        });
        insights.tools = Array.from(foundTools);
    }

    return insights;
}

