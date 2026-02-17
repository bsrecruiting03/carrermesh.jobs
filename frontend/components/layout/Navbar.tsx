
'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Briefcase, LogIn, Upload } from 'lucide-react';

import { ResumeUploadModal } from '../resume/ResumeUploadModal';

export function Navbar() {
    const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

    return (
        <header className="fixed top-4 left-1/2 -translate-x-1/2 z-50 w-[calc(100%-2rem)] max-w-7xl">
            <div className="glass-panel px-6 h-16 rounded-2xl flex items-center justify-between">
                <Link href="/" className="flex items-center gap-2 text-xl font-bold tracking-tight">
                    <div className="bg-gradient-to-br from-cyan-500 to-indigo-600 p-1.5 rounded-lg shadow-lg shadow-cyan-500/20">
                        <Briefcase className="h-5 w-5 text-white" />
                    </div>
                    <span className="text-gradient font-black uppercase tracking-tighter">TechJobs</span>
                </Link>

                <nav className="hidden md:flex items-center gap-8">
                    <Link href="/jobs" className="text-sm font-semibold text-slate-300 hover:text-cyan-400 transition-all duration-300">
                        Explore Jobs
                    </Link>
                    <Link href="/companies" className="text-sm font-semibold text-slate-300 hover:text-cyan-400 transition-all duration-300">
                        Companies
                    </Link>
                </nav>

                <div className="flex items-center gap-4">
                    <button
                        onClick={() => setIsUploadModalOpen(true)}
                        className="hidden sm:inline-flex px-4 py-2 rounded-xl text-sm font-bold text-cyan-400 bg-cyan-950/30 border border-cyan-500/20 hover:bg-cyan-900/40 hover:border-cyan-500/40 transition-all gap-2 items-center"
                    >
                        <Upload className="h-4 w-4" />
                        Smart Match
                    </button>

                    <button className="hidden sm:inline-flex text-sm font-bold text-slate-300 hover:text-white transition-colors gap-2 items-center">
                        <LogIn className="h-4 w-4" />
                        Login
                    </button>
                    <button className="glass-button px-6 py-2.5 rounded-xl text-sm font-bold text-white shadow-lg shadow-indigo-500/10 hover:shadow-cyan-500/20 active:scale-95">
                        Post a Job
                    </button>
                </div>
            </div>

            <ResumeUploadModal
                isOpen={isUploadModalOpen}
                onClose={() => setIsUploadModalOpen(false)}
            />
        </header>
    );
}
