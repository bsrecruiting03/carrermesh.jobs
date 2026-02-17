
import axios from 'axios';
import { Job, CompanyListItem, FilterOptions, SearchParams } from './types';

// Create Axios instance
// Create Axios instance
// Create Axios instance
const api = axios.create({
    // Force IPv4 to avoid Node 18+ dual-stack issues with localhost
    baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000',
    headers: {
        'Content-Type': 'application/json',
    },
});

// Add response interceptor for debugging
api.interceptors.response.use(
    response => response,
    error => {
        const errorDetails = {
            url: error.config?.url,
            baseURL: error.config?.baseURL,
            status: error.response?.status,
            statusText: error.response?.statusText,
            data: error.response?.data,
            message: error.message
        };
        console.error('❌ [API Error]', error.message, errorDetails);
        return Promise.reject(error);
    }
);

export interface JobSearchResponse {
    jobs: Job[];
    total: number;
    pages: number;
    page: number;
    limit: number;
}

export interface CompanyListResponse {
    companies: CompanyListItem[];
    total: number;
    page: number;
    limit: number;
}

export const jobsApi = {
    // Search jobs
    search: async (params: SearchParams) => {
        const { data } = await api.get<JobSearchResponse>('/api/jobs', { params });
        return data;
    },

    // Get single job by ID
    getById: async (id: string) => {
        const { data } = await api.get<Job>(`/api/jobs/${id}`);
        return data;
    },
};

export const companiesApi = {
    // Get all companies
    getAll: async (page = 1, limit = 20) => {
        const { data } = await api.get<CompanyListResponse>('/api/companies', {
            params: { page, limit },
        });
        return data;
    },

    // Get company details
    getById: async (id: number) => {
        const { data } = await api.get(`/api/companies/${id}`);
        return data;
    },
};

export const filtersApi = {
    // Get available filters
    getOptions: async () => {
        const { data } = await api.get<FilterOptions>('/api/filters');
        return data;
    },
};

export const resumeApi = {
    // Match resume
    match: async (file: File) => {
        const formData = new FormData();
        formData.append('file', file);

        const { data } = await api.post('/api/match-resume', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
        return data;
    },
};

export default api;
