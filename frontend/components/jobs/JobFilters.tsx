
'use client';

import { useQuery } from '@tanstack/react-query';
import { filtersApi } from '@/lib/api';
import { SearchParams } from '@/lib/types';
import { Filter, Sparkles, Globe, Cpu } from 'lucide-react';

interface Props {
    params: SearchParams;
    setParams: React.Dispatch<React.SetStateAction<SearchParams>>;
}

export function JobFilters({ params, setParams }: Props) {
    const { data: filters } = useQuery({
        queryKey: ['filters'],
        queryFn: () => filtersApi.getOptions(),
    });

    const toggleRemote = () => {
        setParams(prev => ({ ...prev, remote: !prev.remote, page: 1 }));
    };

    const handleFilterChange = (key: keyof SearchParams, value: any) => {
        setParams(prev => ({ ...prev, [key]: value, page: 1 }));
    };

    return (
        <div className="glass-panel p-8 rounded-3xl space-y-8 animate-fade-in group w-full">
            <div className="flex items-center justify-between pb-6 border-b border-white/5">
                <div className="flex items-center gap-3">
                    <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/20">
                        <Filter className="h-4 w-4 text-cyan-400" />
                    </div>
                    <h2 className="text-sm font-black uppercase tracking-widest text-white leading-none">Filters</h2>
                </div>
                {(params.remote || params.department_category) && (
                    <button
                        onClick={() => setParams({ q: '', location: '', page: 1, limit: 12 })}
                        className="text-[10px] font-black uppercase tracking-tighter text-slate-500 hover:text-white transition-colors"
                    >
                        Reset
                    </button>
                )}
            </div>

            {/* Workspace Preference */}
            <div className="space-y-4">
                <label className="text-[11px] font-black uppercase tracking-widest text-slate-500 flex items-center gap-2">
                    <Globe className="h-3 w-3" />
                    Workspace
                </label>
                <button
                    onClick={toggleRemote}
                    className={`w-full flex items-center justify-between px-4 py-3 rounded-xl text-sm font-bold transition-all duration-300 border ${params.remote
                            ? 'bg-cyan-500/20 text-cyan-100 border-cyan-500/30'
                            : 'bg-white/5 text-slate-400 border-white/5 hover:border-white/10'
                        }`}
                >
                    Remote Only
                    <div className={`w-8 h-4 rounded-full relative transition-colors ${params.remote ? 'bg-cyan-500' : 'bg-slate-700'}`}>
                        <div className={`absolute top-1 w-2 h-2 rounded-full bg-white transition-all ${params.remote ? 'left-5' : 'left-1'}`} />
                    </div>
                </button>
            </div>

            {/* Focus Area */}
            <div className="space-y-4">
                <label className="text-[11px] font-black uppercase tracking-widest text-slate-500 flex items-center gap-2">
                    <Cpu className="h-3 w-3" />
                    Focus Area
                </label>
                <div className="grid gap-2">
                    {['Engineering', 'Design', 'Product', 'Data'].map((cat) => (
                        <button
                            key={cat}
                            onClick={() => handleFilterChange('department_category', params.department_category === cat ? undefined : cat)}
                            className={`flex items-center justify-between px-4 py-3 rounded-xl text-sm font-bold transition-all duration-300 border ${params.department_category === cat
                                    ? 'bg-indigo-500/20 text-indigo-100 border-indigo-500/30'
                                    : 'bg-white/5 text-slate-400 border-white/5 hover:border-white/10'
                                }`}
                        >
                            {cat}
                            {params.department_category === cat && <div className="h-1.5 w-1.5 rounded-full bg-indigo-400 shadow-[0_0_8px_rgba(129,140,248,0.8)]" />}
                        </button>
                    ))}
                </div>
            </div>

            {/* Smart Tips */}
            <div className="pt-6 border-t border-white/5">
                <div className="p-4 rounded-2xl bg-gradient-to-br from-indigo-500/10 to-purple-500/10 border border-white/5">
                    <div className="flex items-center gap-2 mb-2">
                        <Sparkles className="h-3 w-3 text-indigo-400" />
                        <span className="text-[11px] font-black uppercase tracking-widest text-indigo-300">Discover</span>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed font-medium">
                        Try searching for specific stacks like <code className="text-cyan-400 bg-white/5 px-1 rounded">React</code> or <code className="text-cyan-400 bg-white/5 px-1 rounded">Rust</code>.
                    </p>
                </div>
            </div>
        </div>
    );
}

