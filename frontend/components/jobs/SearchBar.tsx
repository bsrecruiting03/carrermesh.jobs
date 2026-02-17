import { Search, History, X, Briefcase, Building2 } from 'lucide-react';
import LocationAutocomplete from '../inputs/LocationAutocomplete';
import { SearchParams } from '@/lib/types';
import { useState, useRef, useEffect } from 'react';

interface SearchBarProps {
    compact?: boolean;
    params: SearchParams;
    onSearch: (e: React.FormEvent<HTMLFormElement>) => void;
    recentSearches: string[];
    showRecent: boolean;
    setShowRecent: (show: boolean) => void;
    onRemoveRecent: (e: React.MouseEvent, term: string) => void;
    onSelectRecent: (term: string) => void;
    locationType: string;
    setLocationType: (type: string) => void;
    setParams: React.Dispatch<React.SetStateAction<SearchParams>>;
}

interface JobSuggestion {
    text: string;
    type: 'role' | 'company';
    count: number;
}

export function SearchBar({
    compact = false,
    params,
    onSearch,
    recentSearches,
    showRecent,
    setShowRecent,
    onRemoveRecent,
    onSelectRecent,
    locationType,
    setLocationType,
    setParams
}: SearchBarProps) {
    const searchInputRef = useRef<HTMLDivElement>(null);
    const [jobSuggestions, setJobSuggestions] = useState<JobSuggestion[]>([]);
    const [isSearchingJobs, setIsSearchingJobs] = useState(false);
    const [query, setQuery] = useState(params.q || '');

    // Sync query with params
    useEffect(() => {
        setQuery(params.q || '');
    }, [params.q]);

    // Cleanup click outside
    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            if (searchInputRef.current && !searchInputRef.current.contains(e.target as Node)) {
                setShowRecent(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [setShowRecent]);

    const handleInput = (e: React.ChangeEvent<HTMLInputElement>) => {
        const val = e.target.value;
        setQuery(val);

        if (val.length >= 2) {
            setIsSearchingJobs(true);
            setShowRecent(true);
            fetch(`http://localhost:8000/api/jobs/suggest?q=${encodeURIComponent(val)}`)
                .then(res => res.json())
                .then(data => {
                    if (data.results) {
                        setJobSuggestions(data.results);
                    }
                })
                .catch(err => console.error(err))
                .finally(() => setIsSearchingJobs(false));
        } else {
            setJobSuggestions([]);
        }
    };

    return (
        <form onSubmit={onSearch} className={`${compact ? 'flex-1 max-w-2xl' : 'max-w-4xl mx-auto'} glass-panel p-2 rounded-2xl flex gap-2 shadow-2xl relative z-20`}>
            <div className="relative flex-1" ref={searchInputRef}>
                <Search className={`absolute left-4 top-1/2 -translate-y-1/2 ${compact ? 'h-4 w-4' : 'h-5 w-5'} text-slate-500`} />
                <input
                    name="q"
                    type="text"
                    value={query}
                    onChange={handleInput}
                    placeholder="Search roles, skills, companies..."
                    autoComplete="off"
                    onFocus={() => setShowRecent(true)}
                    className={`w-full ${compact ? 'pl-10 pr-4 py-2.5 text-sm' : 'pl-12 pr-4 py-4 text-lg'} bg-transparent outline-none text-white placeholder:text-slate-500 font-medium`}
                />

                {/* Dropdown: Shows Recent OR Job Suggestions */}
                {showRecent && !compact && (
                    <div className="absolute top-full left-0 right-0 mt-2 bg-[#0f172a] border border-white/10 rounded-xl shadow-xl overflow-hidden animate-in fade-in slide-in-from-top-2 z-50">
                        {/* Case 1: Job Suggestions (User is typing) */}
                        {query.length >= 2 && jobSuggestions.length > 0 && (
                            <>
                                <div className="px-4 py-2 text-xs font-bold text-slate-500 uppercase tracking-widest bg-white/5 flex justify-between">
                                    <span>Suggestions</span>
                                    {isSearchingJobs && <span className="animate-pulse">Loading...</span>}
                                </div>
                                {jobSuggestions.map((item, i) => (
                                    <button
                                        key={i}
                                        type="button"
                                        onClick={() => {
                                            setQuery(item.text);
                                            setParams(p => ({ ...p, q: item.text })); // Sync parent
                                            setShowRecent(false);
                                        }}
                                        className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/5 cursor-pointer group transition-colors text-left"
                                    >
                                        <div className="flex items-center gap-3 text-slate-300 group-hover:text-cyan-400">
                                            {item.type === 'company' ? (
                                                <Building2 className="h-4 w-4 text-indigo-400" />
                                            ) : (
                                                <Briefcase className="h-4 w-4 text-cyan-400" />
                                            )}
                                            <span className="font-medium">{item.text}</span>
                                        </div>
                                        <span className="text-xs text-slate-600 bg-white/5 px-2 py-0.5 rounded">
                                            {item.count} jobs
                                        </span>
                                    </button>
                                ))}
                            </>
                        )}

                        {/* Case 2: Recent Searches (User clicked empty box OR no suggestions yet) */}
                        {(query.length < 2 || jobSuggestions.length === 0) && recentSearches.length > 0 && (
                            <>
                                <div className="px-4 py-2 text-xs font-bold text-slate-500 uppercase tracking-widest bg-white/5">
                                    Recent Searches
                                </div>
                                {recentSearches.map(term => (
                                    <div
                                        key={term}
                                        onClick={() => onSelectRecent(term)}
                                        className="flex items-center justify-between px-4 py-3 hover:bg-white/5 cursor-pointer group transition-colors"
                                    >
                                        <div className="flex items-center gap-3 text-slate-300 group-hover:text-cyan-400">
                                            <History className="h-4 w-4" />
                                            <span className="font-medium">{term}</span>
                                        </div>
                                        <button
                                            onClick={(e) => onRemoveRecent(e, term)}
                                            className="text-slate-600 hover:text-rose-400 p-1 rounded-full hover:bg-rose-500/10 transition-colors"
                                        >
                                            <X className="h-3.5 w-3.5" />
                                        </button>
                                    </div>
                                ))}
                            </>
                        )}

                        {/* Empty State for no results */}
                        {query.length >= 2 && jobSuggestions.length === 0 && !isSearchingJobs && (
                            <div className="px-4 py-3 text-slate-500 text-sm text-center">
                                No suggestions found
                            </div>
                        )}
                    </div>
                )}
            </div>

            {!compact && (
                <>
                    <div className="hidden md:block w-px h-10 bg-white/10 self-center" />

                    {/* Custom Autocomplete */}
                    <LocationAutocomplete
                        value={params.location} // This can be undefined, component handles it now
                        onChange={(val) => {
                            // Only update location, leave remote flag alone unless explicitly toggled
                            setParams(p => ({ ...p, location: val }));
                        }}
                        onSelect={(val, isRemote) => {
                            if (isRemote) {
                                // Smart Remote Logic: 
                                // User picked "Remote" -> Clear text, set remote=true
                                setLocationType('remote');
                                setParams(p => ({
                                    ...p,
                                    location: '', // Clear text so we don't double filter
                                    remote: true
                                }));
                            } else {
                                // Standard Location Logic
                                setLocationType('all');
                                setParams(p => ({
                                    ...p,
                                    location: val,
                                    remote: undefined // Reset remote flag
                                }));
                            }
                        }}
                    />
                </>
            )}

            {
                compact && (
                    <div className="hidden md:flex items-center border-[0.5px] border-white/10 rounded-lg bg-white/5 p-1 mr-2">
                        {['all', 'remote', 'onsite'].map(type => (
                            <button
                                key={type}
                                type="button"
                                onClick={() => {
                                    setLocationType(type);
                                    setParams(p => ({ ...p, remote: type === 'remote' ? true : undefined }));
                                }}
                                className={`px-3 py-1.5 text-xs font-bold uppercase tracking-wider rounded-md transition-all ${locationType === type
                                    ? 'bg-cyan-500 shadow-lg text-white'
                                    : 'text-slate-400 hover:text-white hover:bg-white/5'
                                    }`}
                            >
                                {type}
                            </button>
                        ))}
                    </div>
                )
            }

            <button type="submit" className={`bg-gradient-to-r from-cyan-600 to-indigo-600 text-white ${compact ? 'px-6 py-2.5 text-sm' : 'px-10 py-4 text-lg'} rounded-xl font-bold hover:scale-[1.02] active:scale-95 transition-all shadow-lg shadow-indigo-500/20`}>
                Search
            </button>
        </form >
    );
}
