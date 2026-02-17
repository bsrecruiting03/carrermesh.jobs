'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useInfiniteQuery } from '@tanstack/react-query';
import { useInView } from 'react-intersection-observer';
import { jobsApi } from '@/lib/api';
import { Job, SearchParams } from '@/lib/types';
import { JobList } from './JobList';
import { JobFilters } from './JobFilters';
import { Sparkles, Loader2 } from 'lucide-react';
import { SearchBar } from './SearchBar';

interface Props {
    initialJobs: Job[];
}

export function JobSearchContainer({ initialJobs }: Props) {
    const [params, setParams] = useState<SearchParams>({
        q: '',
        location: '',
        limit: 20
    });
    const [isScrolled, setIsScrolled] = useState(false);
    const [recentSearches, setRecentSearches] = useState<string[]>([]);
    const [showRecent, setShowRecent] = useState(false);
    const [locationType, setLocationType] = useState<string>('all');

    const heroRef = useRef<HTMLElement>(null);
    const searchInputRef = useRef<HTMLInputElement>(null);

    // Scroll detection
    useEffect(() => {
        const handleScroll = () => {
            const scrollY = window.scrollY;
            setIsScrolled(scrollY > 300);
        };
        window.addEventListener('scroll', handleScroll, { passive: true });
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    // Load recent searches
    useEffect(() => {
        const saved = localStorage.getItem('recentSearches');
        if (saved) {
            setRecentSearches(JSON.parse(saved));
        }
    }, []);

    const saveRecentSearch = (query: string) => {
        if (!query.trim()) return;
        const newSearches = [query, ...recentSearches.filter(s => s !== query)].slice(0, 5);
        setRecentSearches(newSearches);
        localStorage.setItem('recentSearches', JSON.stringify(newSearches));
    };

    const removeRecentSearch = (e: React.MouseEvent, term: string) => {
        e.stopPropagation();
        const newSearches = recentSearches.filter(s => s !== term);
        setRecentSearches(newSearches);
        localStorage.setItem('recentSearches', JSON.stringify(newSearches));
    };

    // Infinite query
    const {
        data,
        isLoading,
        isFetchingNextPage,
        hasNextPage,
        fetchNextPage,
    } = useInfiniteQuery({
        queryKey: ['jobs', params],
        queryFn: ({ pageParam = 1 }) => jobsApi.search({ ...params, page: pageParam }),
        getNextPageParam: (lastPage) => lastPage.page < lastPage.pages ? lastPage.page + 1 : undefined,
        initialPageParam: 1,
        initialData: !params.q && !params.location ? {
            pages: [{ jobs: initialJobs, total: initialJobs.length, page: 1, limit: 20, pages: 1 }],
            pageParams: [1],
        } : undefined,
    });

    const { ref: loadMoreRef, inView } = useInView({ threshold: 0, rootMargin: '200px' });

    useEffect(() => {
        if (inView && hasNextPage && !isFetchingNextPage) {
            fetchNextPage();
        }
    }, [inView, hasNextPage, isFetchingNextPage, fetchNextPage]);

    const allJobs = data?.pages.flatMap(page => page.jobs) || [];
    const totalJobs = data?.pages[0]?.total || 0;

    const handleSearch = useCallback((e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        const formData = new FormData(e.currentTarget);
        const q = formData.get('q') as string;
        // Location is handled by state now via LocationAutocomplete, but fallback to form data

        saveRecentSearch(q);
        setShowRecent(false);

        setParams(prev => ({
            ...prev,
            q,
            remote: locationType === 'remote' ? true : undefined,
        }));
    }, [recentSearches, locationType]);

    // Cleanup click outside
    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            if (searchInputRef.current && !searchInputRef.current.contains(e.target as Node)) {
                setShowRecent(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    return (
        <>
            {/* Sticky Header Search Bar (appears on scroll) */}
            <div className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${isScrolled ? 'translate-y-0 opacity-100' : '-translate-y-full opacity-0'}`}>
                <div className="glass-panel border-b border-white/5 px-4 py-3">
                    <div className="container mx-auto flex items-center gap-4">
                        <span className="text-gradient font-black text-lg tracking-tighter hidden md:block">TechJobs</span>
                        <SearchBar
                            compact
                            params={params}
                            setParams={setParams}
                            onSearch={handleSearch}
                            recentSearches={recentSearches}
                            showRecent={showRecent}
                            setShowRecent={setShowRecent}
                            onRemoveRecent={removeRecentSearch}
                            onSelectRecent={(term) => {
                                setParams(p => ({ ...p, q: term }));
                                setShowRecent(false);
                            }}
                            locationType={locationType}
                            setLocationType={setLocationType}
                        />
                    </div>
                </div>
            </div>

            <div className="container mx-auto px-4 pt-32 pb-20">
                {/* Hero Section (hidden when scrolled) */}
                <section ref={heroRef} className={`mb-16 text-center relative transition-all duration-500 ${isScrolled ? 'opacity-0 h-0 mb-0 overflow-hidden' : 'opacity-100'}`}>
                    <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full -z-10 opacity-20 blur-[120px] bg-gradient-to-r from-cyan-500 via-indigo-500 to-purple-600 rounded-full" />

                    <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass-panel mb-8 animate-fade-in">
                        <Sparkles className="h-4 w-4 text-cyan-400" />
                        <span className="text-xs font-bold tracking-widest uppercase text-cyan-100">The Future of Talent Discovery</span>
                    </div>

                    <h1 className="text-5xl md:text-7xl font-black tracking-tighter text-white mb-8 max-w-4xl mx-auto leading-[1.1]">
                        Elevate your <span className="text-gradient">engineering</span> career.
                    </h1>

                    <p className="text-slate-400 text-lg md:text-xl max-w-2xl mx-auto mb-12 font-medium">
                        Discover high-impact roles at the world's most innovative tech companies.
                    </p>

                    <SearchBar
                        params={params}
                        setParams={setParams}
                        onSearch={handleSearch}
                        recentSearches={recentSearches}
                        showRecent={showRecent}
                        setShowRecent={setShowRecent}
                        onRemoveRecent={removeRecentSearch}
                        onSelectRecent={(term) => {
                            setParams(p => ({ ...p, q: term }));
                            setShowRecent(false);
                        }}
                        locationType={locationType}
                        setLocationType={setLocationType}
                    />
                </section>

                <div className="flex flex-col lg:flex-row gap-8 items-start">
                    {/* Filters */}
                    <aside className="lg:w-72 shrink-0 sticky top-24 hidden lg:block">
                        <JobFilters params={params} setParams={setParams} />
                    </aside>

                    {/* Job List */}
                    <div className="flex-1 w-full">
                        <JobList
                            jobs={allJobs}
                            total={totalJobs}
                            isLoading={isLoading}
                        />

                        {/* Infinite Scroll Trigger */}
                        <div ref={loadMoreRef} className="py-8 flex justify-center">
                            {isFetchingNextPage && (
                                <div className="flex items-center gap-3 text-slate-500">
                                    <Loader2 className="h-5 w-5 animate-spin" />
                                    <span className="text-sm font-medium">Loading more opportunities...</span>
                                </div>
                            )}
                            {!hasNextPage && allJobs.length > 0 && (
                                <span className="text-sm text-slate-600 font-medium">You've reached the end</span>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </>
    );
}
