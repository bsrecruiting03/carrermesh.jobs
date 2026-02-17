import { useState, useEffect, useRef } from 'react';
import { MapPin, Globe, History, TrendingUp, X, Building2, Flag } from 'lucide-react';

interface LocationAutocompleteProps {
    value: string | undefined;
    onChange: (value: string) => void;
    onSelect: (value: string, isRemote?: boolean) => void;
}

interface Suggestion {
    name: string;
    count?: number;
    type?: 'location' | 'remote' | 'history' | 'trending' | 'country' | 'state' | 'city';
}

export default function LocationAutocomplete({ value = '', onChange, onSelect }: LocationAutocompleteProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [query, setQuery] = useState(value);
    const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
    const [loading, setLoading] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);

    // Initial "Trending" suggestions (could fetch from API later)
    const defaultSuggestions: Suggestion[] = [
        { name: 'Remote', type: 'remote', count: 0 }, // Count 0 as placeholder
        { name: 'San Francisco, CA', type: 'trending', count: 2400 },
        { name: 'New York, NY', type: 'trending', count: 1800 },
        { name: 'London, UK', type: 'trending', count: 1200 },
    ];

    useEffect(() => {
        setQuery(value);
    }, [value]);

    useEffect(() => {
        // Click outside to close
        const handleClickOutside = (event: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const fetchSuggestions = async (text: string) => {
        if (text.length < 2) {
            setSuggestions(defaultSuggestions);
            return;
        }

        setLoading(true);
        try {
            const res = await fetch(`http://localhost:8000/api/locations/suggest?q=${encodeURIComponent(text)}`);
            const data = await res.json();

            if (data.results) {
                // Transform API results to suggestions
                const apiSuggestions = data.results.map((loc: any) => ({
                    name: loc.name,
                    count: loc.count,
                    type: loc.type || (loc.name.toLowerCase().includes('remote') ? 'remote' : 'location')
                }));
                setSuggestions(apiSuggestions);
            }
        } catch (error) {
            console.error('Failed to fetch suggestions', error);
        } finally {
            setLoading(false);
        }
    };

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const text = e.target.value;
        setQuery(text);
        onChange(text);
        setIsOpen(true);
        fetchSuggestions(text);
    };

    const handleSelect = (s: Suggestion) => {
        setQuery(s.name);
        setIsOpen(false);
        onSelect(s.name, s.type === 'remote');
    };

    const clearInput = () => {
        setQuery('');
        onChange('');
        setSuggestions(defaultSuggestions);
        setIsOpen(true);
    };

    return (
        <div className="relative flex-1" ref={containerRef}>
            <MapPin className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-500 pointer-events-none" />

            <input
                type="text"
                value={query}
                onChange={handleInputChange}
                onFocus={() => {
                    setIsOpen(true);
                    if (suggestions.length === 0) setSuggestions(defaultSuggestions);
                }}
                placeholder="City, State, or 'Remote'"
                className="w-full pl-12 pr-10 py-4 bg-transparent outline-none text-white placeholder:text-slate-500 font-medium text-lg border-none"
            />

            {query && (
                <button
                    onClick={clearInput}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white transition-colors"
                >
                    <X className="h-4 w-4" />
                </button>
            )}

            {/* Dropdown */}
            {isOpen && (
                <div className="absolute top-full left-0 right-0 mt-2 bg-[#0f172a]/95 backdrop-blur-xl border border-white/10 rounded-xl shadow-2xl overflow-hidden z-50">
                    <div className="max-h-[300px] overflow-y-auto custom-scrollbar">
                        {loading ? (
                            <div className="p-4 text-center text-slate-400 text-sm animate-pulse">
                                Finding locations...
                            </div>
                        ) : (
                            <div>
                                {suggestions.length > 0 ? (
                                    suggestions.map((s, i) => (
                                        <button
                                            key={i}
                                            onClick={() => handleSelect(s)}
                                            className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-white/5 transition-colors border-b border-white/5 last:border-0 group"
                                        >
                                            <div className="flex items-center gap-3">
                                                <div className="p-2 rounded-lg bg-white/5 group-hover:bg-white/10 transition-colors text-slate-400 group-hover:text-cyan-400">
                                                    {s.type === 'remote' && <Globe className="h-4 w-4" />}
                                                    {s.type === 'trending' && <TrendingUp className="h-4 w-4" />}
                                                    {s.type === 'history' && <History className="h-4 w-4" />}
                                                    {s.type === 'location' && <MapPin className="h-4 w-4" />}
                                                    {s.type === 'country' && <Flag className="h-4 w-4" />}
                                                    {s.type === 'state' && <MapPin className="h-4 w-4" />}
                                                    {s.type === 'city' && <Building2 className="h-4 w-4" />}
                                                </div>
                                                <div>
                                                    <div className="font-medium text-slate-200 group-hover:text-white transition-colors">
                                                        {s.name}
                                                    </div>
                                                    {s.type === 'trending' && (
                                                        <div className="text-[10px] uppercase tracking-wider font-bold text-cyan-500/70">
                                                            Popular Hub
                                                        </div>
                                                    )}
                                                </div>
                                            </div>

                                            {s.count !== undefined && s.count > 0 && (
                                                <span className="text-xs font-mono font-medium text-slate-500 bg-white/5 px-2 py-1 rounded-md">
                                                    {s.count.toLocaleString()} jobs
                                                </span>
                                            )}
                                        </button>
                                    ))
                                ) : (
                                    <div className="p-4 text-center text-slate-500 text-sm">
                                        No locations found
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    {/* Footer / Tip */}
                    <div className="bg-white/5 px-4 py-2 text-[10px] text-slate-500 border-t border-white/10 flex justify-between">
                        <span>💡 Tip: Type "Remote" for wfh jobs</span>
                        <span>{suggestions.length} results</span>
                    </div>
                </div>
            )}
        </div>
    );
}
