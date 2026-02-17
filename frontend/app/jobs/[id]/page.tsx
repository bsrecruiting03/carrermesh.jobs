
import { jobsApi } from '@/lib/api';
import { extractJobInsights, formatCompanyName, extractVisaInfo, extractSalary } from '@/lib/job-parsing';
import { formatRelativeTime, formatCurrency } from '@/lib/utils';
import { Building2, MapPin, Clock, ExternalLink, Banknote, Calendar, BadgeCheck, Globe, CheckCircle2, FileText, ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { notFound } from 'next/navigation';

interface Props {
    params: Promise<{
        id: string;
    }>
}

export default async function JobDetailPage({ params }: Props) {
    // Next.js 16+: params is a Promise, must await before accessing
    const { id } = await params;

    let job = null;
    try {
        job = await jobsApi.getById(id);
    } catch (e) {
        console.error(`Failed to fetch job ${id}`, e);
        notFound();
    }

    if (!job) {
        notFound();
    }


    const insights = extractJobInsights(job);
    const companyName = formatCompanyName(job.company);
    const visaInfo = job.visa_sponsorship || extractVisaInfo(job.job_description || '');
    const salaryDisplay = job.salary_max
        ? `${formatCurrency(job.salary_min || 0)} - ${formatCurrency(job.salary_max)}`
        : extractSalary(job.job_description || '');

    return (
        <main className="min-h-screen pb-20 pt-24">
            {/* Navigation */}
            <div className="container mx-auto px-4 mb-8">
                <Link href="/" className="inline-flex items-center gap-2 text-slate-400 hover:text-white transition-colors font-medium">
                    <ArrowLeft className="h-4 w-4" />
                    Back to Jobs
                </Link>
            </div>

            <div className="container mx-auto px-4 grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Main Content */}
                <div className="lg:col-span-2 space-y-8">
                    {/* Header */}
                    <div className="glass-panel p-8 rounded-3xl relative overflow-hidden">
                        <div className="absolute top-0 right-0 p-8 opacity-10">
                            <Building2 className="h-48 w-48 text-white" />
                        </div>

                        <div className="relative z-10">
                            <div className="flex items-center gap-3 mb-4">
                                <span className="px-3 py-1 rounded-full bg-cyan-500/10 text-cyan-400 text-xs font-bold uppercase tracking-widest border border-cyan-500/20">
                                    {job.department_category || 'Engineering'}
                                </span>
                                {job.is_remote && (
                                    <span className="px-3 py-1 rounded-full bg-indigo-500/10 text-indigo-400 text-xs font-bold uppercase tracking-widest border border-indigo-500/20">
                                        Remote
                                    </span>
                                )}
                            </div>

                            <h1 className="text-3xl md:text-5xl font-black text-white mb-6 leading-tight tracking-tight">
                                {job.title}
                            </h1>

                            <div className="flex flex-wrap items-center gap-6 text-slate-300 font-medium text-lg">
                                <span className="flex items-center gap-2">
                                    <Building2 className="h-5 w-5 text-cyan-400" />
                                    {companyName}
                                </span>
                                <span className="flex items-center gap-2">
                                    <MapPin className="h-5 w-5 text-indigo-400" />
                                    {job.location || 'Remote'}
                                </span>
                                <span className="flex items-center gap-2">
                                    <Clock className="h-5 w-5 text-slate-500" />
                                    {job.date_posted ? formatRelativeTime(job.date_posted) : 'Recently'}
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* Quick Stats Grid */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                        <div className="glass-panel p-4 rounded-2xl flex flex-col gap-1 items-center text-center justify-center">
                            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 mb-1">
                                <Banknote className="h-5 w-5" />
                            </div>
                            <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">Salary</span>
                            <span className="font-bold text-white text-sm">{salaryDisplay || 'Competitive'}</span>
                        </div>
                        <div className="glass-panel p-4 rounded-2xl flex flex-col gap-1 items-center text-center justify-center">
                            <div className="p-2 rounded-xl bg-purple-500/10 text-purple-400 mb-1">
                                <BadgeCheck className="h-5 w-5" />
                            </div>
                            <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">Experience</span>
                            <span className="font-bold text-white text-sm">{insights.yoe || 'Not specified'}</span>
                        </div>
                        <div className="glass-panel p-4 rounded-2xl flex flex-col gap-1 items-center text-center justify-center">
                            <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400 mb-1">
                                <Globe className="h-5 w-5" />
                            </div>
                            <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">Visa Sponsor</span>
                            <span className="font-bold text-white text-sm">
                                {job.visa_confidence ? `${Math.round(job.visa_confidence * 100)}% Confidence` : (visaInfo || 'Unknown')}
                            </span>
                        </div>
                        <div className="glass-panel p-4 rounded-2xl flex flex-col gap-1 items-center text-center justify-center">
                            <div className="p-2 rounded-xl bg-blue-500/10 text-blue-400 mb-1">
                                <Calendar className="h-5 w-5" />
                            </div>
                            <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">Work Mode</span>
                            <span className="font-bold text-white text-sm">
                                {job.work_mode || (job.is_remote ? 'Remote' : 'Onsite')}
                            </span>
                        </div>
                    </div>

                    {/* Description Analysis */}
                    <div className="glass-panel p-8 rounded-3xl space-y-8">
                        {insights.responsibilities.length > 0 && (
                            <div>
                                <h3 className="flex items-center gap-2 text-xl font-bold text-white mb-4">
                                    <FileText className="h-5 w-5 text-cyan-400" />
                                    Key Responsibilities
                                </h3>
                                <ul className="space-y-3">
                                    {insights.responsibilities.map((item, i) => (
                                        <li key={i} className="flex items-start gap-3 text-slate-300 leading-relaxed">
                                            <span className="mt-2 h-1.5 w-1.5 rounded-full bg-cyan-400 shrink-0" />
                                            {item}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        {insights.requirements.length > 0 && (
                            <div>
                                <h3 className="flex items-center gap-2 text-xl font-bold text-white mb-4">
                                    <CheckCircle2 className="h-5 w-5 text-indigo-400" />
                                    Requirements
                                </h3>
                                <ul className="space-y-3">
                                    {insights.requirements.map((item, i) => (
                                        <li key={i} className="flex items-start gap-3 text-slate-300 leading-relaxed">
                                            <span className="mt-2 h-1.5 w-1.5 rounded-full bg-indigo-400 shrink-0" />
                                            {item}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        {/* Tech Stack */}
                        {insights.tools.length > 0 && (
                            <div>
                                <h3 className="text-lg font-bold text-white mb-4">Tech Stack & Tools</h3>
                                <div className="flex flex-wrap gap-2">
                                    {insights.tools.map(tool => (
                                        <span key={tool} className="px-3 py-1.5 bg-slate-800 text-slate-300 rounded-lg border border-slate-700 font-medium">
                                            {tool}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Raw Description Toggle (if needed) - Keeping it simple for now by showing the rest of description roughly processed */}
                        <div className="pt-8 border-t border-white/5">
                            <div className="prose prose-invert max-w-none text-slate-400" dangerouslySetInnerHTML={{ __html: job.job_description || '' }} />
                        </div>
                    </div>
                </div>

                {/* Sidebar */}
                <aside className="space-y-6">
                    {/* Apply Card */}
                    <div className="glass-panel p-6 rounded-3xl sticky top-24">
                        <h3 className="text-xl font-bold text-white mb-2">Interested?</h3>
                        <p className="text-slate-400 mb-6">
                            Apply directly on the company career page.
                        </p>

                        <a
                            href={job.job_link}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center justify-center gap-2 w-full bg-gradient-to-r from-cyan-600 to-indigo-600 text-white font-bold py-4 rounded-xl hover:scale-[1.02] active:scale-95 transition-all shadow-lg shadow-indigo-500/20 mb-4"
                        >
                            Apply Now <ExternalLink className="h-4 w-4" />
                        </a>

                        {job.company_details?.domain && (
                            <a
                                href={`https://${job.company_details.domain}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center justify-center gap-2 w-full bg-white/5 text-slate-300 font-bold py-3 rounded-xl hover:bg-white/10 transition-colors"
                            >
                                Visit {companyName} <Globe className="h-4 w-4" />
                            </a>
                        )}
                    </div>
                </aside>
            </div>
        </main>
    );
}
