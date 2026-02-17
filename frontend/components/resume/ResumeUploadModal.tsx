'use client';

import { useState, useRef } from 'react';
import { Upload, FileText, X, Loader2, AlertCircle, Briefcase } from 'lucide-react';
import { resumeApi } from '@/lib/api';
import { cn } from '@/lib/utils';
import Link from 'next/link';

interface MatchResult {
    resume_metadata: Record<string, unknown>;
    extracted_skills: string[];
    matches: {
        job: {
            id: string; // or job_id depending on API
            job_id?: string;
            title: string;
            company: string;
            location: string;
            salary_min?: number;
            salary_max?: number;
            salary_currency?: string;
            job_url?: string; // or job_link
            job_link?: string;
            tech_languages?: string;
        };
        score: {
            total_score: number;
            breakdown: {
                seniority: number;
                technical: number;
                semantic: number;
                education: number;
                location: number;
            };
        };
    }[];
}

interface ResumeUploadModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export function ResumeUploadModal({ isOpen, onClose }: ResumeUploadModalProps) {
    const [file, setFile] = useState<File | null>(null);
    const [isUploading, setIsUploading] = useState(false);
    const [results, setResults] = useState<MatchResult | null>(null);
    const [error, setError] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    if (!isOpen) return null;

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
            setError(null);
        }
    };

    const handleUpload = async () => {
        if (!file) return;

        setIsUploading(true);
        setError(null);
        try {
            const data = await resumeApi.match(file);
            setResults(data);
        } catch (err: unknown) {
            console.error(err);
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            setError((err as any).response?.data?.detail || "Failed to process resume. Please try again.");
        } finally {
            setIsUploading(false);
        }
    };

    const reset = () => {
        setFile(null);
        setResults(null);
        setError(null);
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
            <div className="bg-[#0f172a] border border-slate-800 rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl animate-in zoom-in-95 duration-200 overflow-hidden">

                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-slate-800 bg-slate-900/50">
                    <div className="flex items-center gap-3">
                        <div className="bg-cyan-500/10 p-2 rounded-lg">
                            <Upload className="h-6 w-6 text-cyan-400" />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-white">Smart Resume Match</h2>
                            <p className="text-slate-400 text-sm">Upload your resume to find your perfect job match</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-slate-800 rounded-full text-slate-400 hover:text-white transition-colors"
                    >
                        <X className="h-5 w-5" />
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6 custom-scrollbar">

                    {error && (
                        <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center gap-3 text-red-400">
                            <AlertCircle className="h-5 w-5 shrink-0" />
                            <p>{error}</p>
                        </div>
                    )}

                    {!results ? (
                        <div className="flex flex-col items-center justify-center py-12">
                            <div
                                onClick={() => fileInputRef.current?.click()}
                                className={cn(
                                    "w-full max-w-xl border-2 border-dashed rounded-3xl p-12 flex flex-col items-center justify-center cursor-pointer transition-all duration-300 group",
                                    file ? "border-cyan-500/50 bg-cyan-500/5" : "border-slate-700 hover:border-cyan-400 hover:bg-slate-800/50"
                                )}
                            >
                                <input
                                    type="file"
                                    ref={fileInputRef}
                                    className="hidden"
                                    accept=".pdf,.docx,.doc"
                                    onChange={handleFileChange}
                                />

                                {file ? (
                                    <>
                                        <div className="bg-cyan-500/20 p-4 rounded-full mb-4 group-hover:scale-110 transition-transform">
                                            <FileText className="h-10 w-10 text-cyan-400" />
                                        </div>
                                        <p className="text-lg font-medium text-white mb-1">{file.name}</p>
                                        <p className="text-slate-400 text-sm">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                                        <button
                                            onClick={(e) => { e.stopPropagation(); setFile(null); }}
                                            className="mt-4 text-sm text-red-400 hover:text-red-300 hover:underline"
                                        >
                                            Remove
                                        </button>
                                    </>
                                ) : (
                                    <>
                                        <div className="bg-slate-800 p-4 rounded-full mb-4 group-hover:scale-110 transition-transform group-hover:bg-cyan-500/20">
                                            <Upload className="h-10 w-10 text-slate-400 group-hover:text-cyan-400 transition-colors" />
                                        </div>
                                        <p className="text-lg font-medium text-slate-200 mb-2">Click to upload or drag and drop</p>
                                        <p className="text-slate-500 text-sm">PDF, DOCX (Max 5MB)</p>
                                    </>
                                )}
                            </div>

                            {file && (
                                <button
                                    onClick={handleUpload}
                                    disabled={isUploading}
                                    className="mt-8 bg-cyan-500 hover:bg-cyan-600 text-white font-bold py-3 px-8 rounded-xl shadow-lg shadow-cyan-500/20 active:scale-95 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                                >
                                    {isUploading ? (
                                        <>
                                            <Loader2 className="h-5 w-5 animate-spin" />
                                            Analyzing Resume...
                                        </>
                                    ) : (
                                        <>
                                            Find Matches
                                            <Briefcase className="h-5 w-5" />
                                        </>
                                    )}
                                </button>
                            )}
                        </div>
                    ) : (
                        <div className="space-y-6">
                            {/* Results Header */}
                            <div className="flex items-center justify-between">
                                <h3 className="text-lg font-semibold text-white">
                                    Top Matches for you
                                </h3>
                                <button
                                    onClick={reset}
                                    className="text-sm text-cyan-400 hover:text-cyan-300 hover:underline"
                                >
                                    Upload New Resume
                                </button>
                            </div>

                            {/* Skills Found */}
                            <div className="flex flex-wrap gap-2">
                                {results.extracted_skills.slice(0, 10).map((skill, i) => (
                                    <span key={i} className="px-2.5 py-1 rounded-md bg-slate-800 text-slate-300 text-xs font-medium border border-slate-700">
                                        {skill}
                                    </span>
                                ))}
                                {results.extracted_skills.length > 10 && (
                                    <span className="px-2.5 py-1 rounded-md bg-slate-800 text-slate-400 text-xs border border-slate-700">
                                        +{results.extracted_skills.length - 10} more
                                    </span>
                                )}
                            </div>

                            {/* Job List */}
                            <div className="grid gap-4">
                                {results.matches.length === 0 ? (
                                    <div className="text-center py-12 text-slate-400">
                                        No strong matches found. Try updating your resume or broadening criteria.
                                    </div>
                                ) : (
                                    results.matches.map((match, idx) => (
                                        <div key={idx} className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5 hover:border-cyan-500/30 transition-colors group">
                                            <div className="flex justify-between items-start gap-4">
                                                <div className="flex-1">
                                                    <h4 className="font-bold text-lg text-white group-hover:text-cyan-400 transition-colors">
                                                        <Link href={`/jobs/${match.job.job_id || match.job.id}`} target="_blank">
                                                            {match.job.title}
                                                        </Link>
                                                    </h4>
                                                    <p className="text-slate-400 text-sm mb-2">{match.job.company} • {match.job.location}</p>

                                                    {/* Score Badges */}
                                                    <div className="flex flex-wrap gap-2 mt-3">
                                                        <ScoreBadge label="Technical" score={match.score.breakdown.technical} />
                                                        <ScoreBadge label="Experience" score={match.score.breakdown.seniority} />
                                                        <ScoreBadge label="Similarity" score={match.score.breakdown.semantic} />
                                                    </div>
                                                </div>

                                                <div className="flex flex-col items-end">
                                                    <div className="text-2xl font-black text-cyan-400">
                                                        {match.score.total_score}%
                                                    </div>
                                                    <span className="text-xs text-slate-500 font-medium uppercase tracking-wider">Match</span>
                                                </div>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

function ScoreBadge({ label, score }: { label: string, score: number }) {
    let color = "bg-slate-700 text-slate-300";
    if (score >= 80) color = "bg-green-500/10 text-green-400 border-green-500/20";
    else if (score >= 50) color = "bg-yellow-500/10 text-yellow-400 border-yellow-500/20";
    else color = "bg-red-500/10 text-red-400 border-red-500/20";

    return (
        <span className={cn("px-2 py-0.5 rounded text-xs font-semibold border", color)}>
            {label}: {score}%
        </span>
    );
}
