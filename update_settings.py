import meilisearch
import os

MEILI_URL = os.getenv("MEILI_URL", "http://localhost:7700")
MEILI_KEY = os.getenv("MEILI_MASTER_KEY", "masterKey")

client = meilisearch.Client(MEILI_URL, MEILI_KEY)
index = client.index('jobs')

settings = {
    'filterableAttributes': [
        'is_remote',
        'work_mode',
        'salary_min',
        'salary_max',
        'department',
        'department_category',
        'department_subcategory',
        'tech_languages',
        'tech_frameworks',
        'tech_tools',
        'tech_cloud',
        'seniority',
        'visa_sponsorship',
        'city',
        'state',
        'country',
        'date_posted',
        'posted_bucket',
        'company',
        'is_active',
        'soft_skills'
    ],
    'sortableAttributes': [
        'date_posted',
        'salary_max',
        'salary_min',
        'title',
        'company'
    ],
    'searchableAttributes': [
        'title',
        'company',
        'job_description',
        'job_summary',
        'tech_languages',
        'tech_frameworks',
        'department',
        'location'
    ]
}

print("Updating Meilisearch settings...")
task = index.update_settings(settings)
task_uid = getattr(task, 'task_uid', None) or task.get('taskUid')
print(f"Update started. Task UID: {task_uid}")
print("Waiting for task completion...")
res = client.wait_for_task(task_uid)
print(f"Status: {res.status if hasattr(res, 'status') else res.get('status')}")
if (hasattr(res, 'status') and res.status == 'failed') or res.get('status') == 'failed':
    print(f"Error: {res.error if hasattr(res, 'error') else res.get('error')}")
