
import { jobsApi } from '@/lib/api';
import { JobSearchContainer } from '@/components/jobs/JobSearchContainer';
import { Job } from '@/lib/types';

export default async function Home() {
  // Fetch initial jobs (server-side) for SEO and fast FCP
  let initialJobs: Job[] = [];
  try {
    const data = await jobsApi.search({ limit: 20 });
    initialJobs = data.jobs;

  } catch (e) {
    console.error("Failed to fetch jobs:", e);
  }

  return (
    <JobSearchContainer initialJobs={initialJobs} />
  );
}
