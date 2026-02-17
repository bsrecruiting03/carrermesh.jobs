import json

def try_fix_slug(broken_slug):
    # broken: wd5|wd1|earlywarningcareers
    # goal: earlywarning|wd5|earlywarningcareers
    
    parts = broken_slug.split('|')
    if len(parts) != 3: 
        return broken_slug
        
    if not parts[0].startswith('wd'):
        return broken_slug
        
    shard_candidate = parts[0] # wd5
    site_id = parts[2] # earlywarningcareers
    
    # Heuristic: Extract simple name from site_id
    company_candidate = site_id.lower()
    for suffix in ["careers", "_careers", "career", "_career", "jobs", "_jobs", "external", "_external"]:
        if company_candidate.endswith(suffix):
            company_candidate = company_candidate.replace(suffix, "")
            break
            
    # Fix: generic 'external' is useless format on its own, skip repair if candidate is too generic
    if len(company_candidate) < 3 or company_candidate in ["external", "search", "careers"]:
        return broken_slug 

    # Construct: company_candidate|shard_candidate|site_id
    return f"{company_candidate}|{shard_candidate}|{site_id}"

def main():
    json_path = 'companies.json'
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
            
        workday_list = data.get('workday', [])
        new_list = []
        fixed_count = 0
        
        for item in workday_list:
            if item.startswith('wd'):
                fixed = try_fix_slug(item)
                if fixed != item:
                    fixed_count += 1
                new_list.append(fixed)
            else:
                new_list.append(item)
                
        data['workday'] = new_list
        
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=4)
            
        print(f"Repaired {fixed_count} slugs in companies.json")
        
    except Exception as e:
        print(f"Failed to update companies.json: {e}")

if __name__ == "__main__":
    main()
