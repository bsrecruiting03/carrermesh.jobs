'use client';

import { useMemo } from 'react';
import { Job } from '@/lib/types';
import { extractJobInsights, formatCompanyName } from '@/lib/job-parsing';
import { Building2, MapPin, Clock, ExternalLink, FileText, Wrench, Globe, CheckCircle2, Bookmark, Eye, ThumbsDown, Flag } from 'lucide-react';
import { formatRelativeTime } from '@/lib/utils';
import Link from 'next/link';

interface JobCardProps {
    job: Job;
}

export function JobCard({ job }: JobCardProps) {
    const insights = useMemo(() => extractJobInsights(job), [job]);
    const formattedCompany = formatCompanyName(job.company);

    // Format Salary
    const salaryDisplay = useMemo(() => {
        if (!job.salary_min && !job.salary_max) return null;

        const currencyMap: Record<string, string> = {
            'USD': '$',
            'EUR': '€',
            'GBP': '£',
            'CAD': 'C$',
            'AUD': 'A$',
            'INR': '₹'
        };

        const currencyCode = job.salary_currency || 'USD';
        const currency = currencyMap[currencyCode] || currencyCode;

        const min = job.salary_min;
        const max = job.salary_max;

        // Helper to format number
        const fmt = (val: number) => {
            if (val >= 1000) {
                // Annual Salary (e.g. 150000 -> 150k)
                const inK = Math.round(val / 1000);
                return `${inK}k`;
            } else {
                // Hourly/Monthly (e.g. 50 -> 50)
                return val.toString();
            }
        };

        // Heuristic: If max salary is small (< 200), it's likely hourly
        const isHourly = (max && max < 200) || (min && min < 200);
        const period = isHourly ? '/hr' : '/yr';

        if (min && max) {
            if (min === max) return `${currency}${fmt(min)}${period}`;
            return `${currency}${fmt(min)}-${currency}${fmt(max)}${period}`;
        }
        if (min) return `${currency}${fmt(min)}${period}`;
        if (max) return `Up to ${currency}${fmt(max)}${period}`;

        return null;
    }, [job]);

    const companyLink = job.company_details?.domain
        ? `https://${job.company_details.domain}`
        : null;

    return (
        <article className="group relative flex flex-col bg-[#1e293b] hover:bg-[#1e293b] border border-slate-700/50 rounded-xl overflow-hidden transition-all duration-300 hover:shadow-xl hover:shadow-cyan-900/10 hover:border-cyan-500/30">

            {/* Hover Overlay Actions */}
            <div className="absolute inset-0 bg-[#0f172a]/80 backdrop-blur-[2px] opacity-0 group-hover:opacity-100 flex flex-col items-center justify-center gap-3 z-20 transition-all duration-300 pointer-events-none group-hover:pointer-events-auto">
                <div className="flex gap-2">
                    <button className="flex items-center gap-2 px-6 py-2.5 bg-pink-600 hover:bg-pink-500 text-white font-bold rounded-full shadow-lg transform hover:scale-105 transition-all">
                        <Bookmark className="w-4 h-4" />
                        Save
                    </button>
                    <button className="flex items-center gap-2 px-4 py-2.5 bg-white text-slate-900 font-bold rounded-full shadow-lg hover:bg-slate-200 transform hover:scale-105 transition-all">
                        Mark Applied
                    </button>
                </div>

                <div className="flex gap-2 mt-2">
                    <a
                        href={job.job_link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="px-6 py-2 bg-slate-700 hover:bg-slate-600 text-white text-sm font-bold rounded-full border border-slate-600 hover:border-slate-500 transition-colors"
                    >
                        Apply Directly
                    </a>
                    <button className="p-2 rounded-full bg-slate-800 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors">
                        <ThumbsDown className="w-4 h-4" />
                    </button>
                    <button className="p-2 rounded-full bg-slate-800 text-slate-400 hover:text-amber-400 hover:bg-amber-500/10 transition-colors">
                        <Flag className="w-4 h-4" />
                    </button>
                </div>
            </div>

            <div className="p-5 flex flex-col h-full relative z-10">
                {/* 1. Header: Title & Time */}
                <div className="flex justify-between items-start mb-1.5">
                    <Link href={`/jobs/${job.job_id}`} className="block">
                        <h3 className="text-[17px] font-bold text-slate-100 leading-tight hover:text-cyan-400 transition-colors line-clamp-2">
                            {job.title}
                        </h3>
                    </Link>
                    <div className="shrink-0 flex items-center gap-1 text-[11px] font-medium text-slate-500 ml-3">
                        <Clock className="w-3 h-3" />
                        {/* Use ingestion time if available for real-time freshness */}
                        {formatRelativeTime(job.ingested_at || job.date_posted || '')}
                    </div>
                </div>

                {/* 2. Subheader: Location */}
                <div className="flex items-center gap-1.5 text-slate-400 text-[13px] mb-3">
                    <MapPin className="w-3.5 h-3.5 shrink-0" />
                    <span className="truncate">{job.normalized_location || job.location || 'Remote'}</span>
                </div>

                {/* 3. Tags Row (Salary, Work Type) */}
                <div className="flex flex-wrap items-center gap-2 mb-4">
                    {salaryDisplay && (
                        <span className="px-2 py-0.5 rounded text-[11px] font-bold border border-emerald-500/30 text-emerald-400 bg-emerald-500/5">
                            {salaryDisplay}
                        </span>
                    )}
                    <span className="px-2 py-0.5 rounded text-[11px] font-medium border border-slate-700 text-slate-300 bg-slate-800/50">
                        {job.is_remote ? 'Remote' : (job.work_mode || 'Onsite')}
                    </span>
                    <span className="px-2 py-0.5 rounded text-[11px] font-medium border border-slate-700 text-slate-300 bg-slate-800/50">
                        {job.employment_type || insights.jobType || 'Full Time'}
                    </span>
                </div>

                {/* 4. Company Section */}
                <div className="flex items-start gap-3 mb-4 group/company">
                    <div className="w-10 h-10 shrink-0 rounded-lg bg-white p-0.5 flex items-center justify-center overflow-hidden">
                        {job.logo_url ? (
                            <img
                                src={job.logo_url}
                                alt={formattedCompany}
                                className="w-full h-full object-contain"
                                onError={(e) => {
                                    // Fallback to Icon on error
                                    e.currentTarget.style.display = 'none';
                                    e.currentTarget.nextElementSibling?.classList.remove('hidden');
                                }}
                            />
                        ) : null}
                        {/* Fallback Icon */}
                        <div className={`w-full h-full rounded bg-slate-100 flex items-center justify-center text-slate-400 ${job.logo_url ? 'hidden' : ''}`}>
                            <Building2 className="w-5 h-5 text-slate-600" />
                        </div>
                    </div>
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                            <span className="text-sm font-bold text-slate-200 truncate">{formattedCompany}</span>
                            {companyLink && (
                                <a href={companyLink} target="_blank" rel="noopener noreferrer" className="opacity-0 group-hover/company:opacity-100 transition-opacity">
                                    <ExternalLink className="w-3 h-3 text-slate-500 hover:text-cyan-400" />
                                </a>
                            )}
                        </div>
                        <p className="text-[11px] text-slate-500 leading-snug line-clamp-2 mt-0.5">
                            {job.company_details?.ats_provider
                                ? `Hiring via ${job.company_details.ats_provider}`
                                : 'View company details for more info.'}
                        </p>
                    </div>
                </div>

                {/* 5. Insights Section (YOE, Summary, Stack) */}
                <div className="space-y-2.5 mb-2 flex-1">
                    {/* YOE / Requirements */}
                    {(insights.yoe || insights.education || insights.requirements.length > 0) && (
                        <div className="flex items-start gap-2.5">
                            <FileText className="w-3.5 h-3.5 text-slate-500 mt-0.5 shrink-0" />
                            <div className="text-[12px] text-slate-400 leading-relaxed line-clamp-2">
                                {insights.yoe && <span className="font-bold text-indigo-400 mr-1">{insights.yoe}</span>}
                                {insights.education && <span className="font-medium text-slate-300 mr-1">{insights.education} •</span>}
                                {insights.requirements[0] || "Bachelor's degree in Computer Science or equivalent experience."}
                            </div>
                        </div>
                    )}

                    {/* Tech Stack - Prioritize structured skills */}
                    <div className="flex items-start gap-2.5">
                        <Wrench className="w-3.5 h-3.5 text-slate-500 mt-0.5 shrink-0" />
                        <div className="text-[12px] text-slate-400 leading-relaxed line-clamp-2">
                            {(job.skills && job.skills.length > 0) ? (
                                <div className="flex flex-wrap gap-1">
                                    {job.skills.slice(0, 4).map(skill => (
                                        <span key={skill} className="px-1.5 py-0.5 rounded-sm bg-slate-800 text-slate-300 text-[10px] border border-slate-700">
                                            {skill}
                                        </span>
                                    ))}
                                    {job.skills.length > 4 && (
                                        <span className="text-[10px] text-slate-500 self-center">+{job.skills.length - 4} more</span>
                                    )}
                                </div>
                            ) : (
                                <span>
                                    {insights.tools.length > 0
                                        ? insights.tools.join(', ')
                                        : "Check job description for tech stack."}
                                </span>
                            )}
                        </div>
                    </div>
                </div>

            </div>

            {/* 6. Footer */}
            <div className="px-5 py-3 border-t border-slate-700/50 bg-[#162032] flex items-center justify-between text-[11px] font-medium text-slate-500">
                <a
                    href={job.job_link || '#'}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 hover:text-cyan-400 transition-colors"
                >
                    Job Posting <ExternalLink className="w-2.5 h-2.5" />
                </a>

                {/* Decorative Carousel Dots */}
                <div className="flex gap-1">
                    <div className="w-1.5 h-1.5 rounded-full bg-slate-600"></div>
                    <div className="w-1.5 h-1.5 rounded-full bg-slate-800"></div>
                    <div className="w-1.5 h-1.5 rounded-full bg-slate-800"></div>
                    <div className="w-1.5 h-1.5 rounded-full bg-slate-800"></div>
                </div>

                <Link
                    href={`/jobs/${job.job_id}`}
                    className="hover:text-white transition-colors"
                >
                    View all
                </Link>
            </div>

            {/* "See views" pseudo-element at bottom center */}
            <div className="absolute bottom-0 left-1/2 -translate-x-1/2 -translate-y-1/2 text-[10px] text-slate-600 font-medium flex items-center gap-1 bg-[#162032] px-2">
                <Eye className="w-3 h-3" />
                See views
            </div>

        </article>
    );
}
