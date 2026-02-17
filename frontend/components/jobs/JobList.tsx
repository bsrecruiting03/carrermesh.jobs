
'use client';

import { Job } from '@/lib/types';
import { JobCard } from './JobCard';

interface Props {
    jobs: Job[];
    total: number;
    isLoading: boolean;
}

export function JobList({ jobs, total, isLoading }: Props) {
    if (isLoading) {
        return (
            <div className="space-y-4">
                {[...Array(8)].map((_, i) => (
                    <div key={i} className="h-32 glass-panel animate-pulse rounded-2xl" />
                ))}
            </div>
        );
    }

    if (jobs.length === 0) {
        return (
            <div className="text-center py-32 glass-panel rounded-3xl border-dashed">
                <div className="inline-flex p-4 rounded-full bg-slate-800/50 mb-6 font-mono text-cyan-400">0x404</div>
                <h3 className="text-2xl font-bold text-white mb-2">No matching roles found</h3>
                <p className="text-slate-500 max-w-sm mx-auto">Adjust your filters or search keywords to explore other opportunities.</p>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Results Header */}
            <div className="flex justify-between items-center px-2">
                <span className="text-sm font-bold text-slate-400 uppercase tracking-widest">
                    <span className="text-cyan-400">{total.toLocaleString()}</span> opportunities
                </span>
                <div className="flex items-center gap-2">
                    <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                    <span className="text-xs font-bold text-slate-500 uppercase tracking-tighter">Live</span>
                </div>
            </div>

            {/* Job Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                {jobs.map((job) => (
                    <JobCard key={job.job_id} job={job} />
                ))}
            </div>
        </div>
    );
}

