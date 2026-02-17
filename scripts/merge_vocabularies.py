import json
import os

def merge_vocabularies():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    intelligence_dir = os.path.join(base_dir, "us_ats_jobs", "intelligence")
    
    master_file = os.path.join(intelligence_dir, "job_description_vocabulary.json")
    expansion_files = [
        os.path.join(intelligence_dir, "massive_vocabulary_expansion.json"),
        os.path.join(intelligence_dir, "technical_ecosystems_expansion.json"),
        os.path.join(intelligence_dir, "specialized_domains_expansion.json"),
        os.path.join(intelligence_dir, "programmatic_expansion.json"),
        os.path.join(intelligence_dir, "grand_scale_expansion.json"),
        os.path.join(intelligence_dir, "scaling_to_5k_today.json"),
        os.path.join(intelligence_dir, "reach_5000_skills.json"),
        os.path.join(intelligence_dir, "mega_skill_generator.json"),
        os.path.join(intelligence_dir, "final_strike_to_5000.json"),
        os.path.join(intelligence_dir, "reach_5k_final.json")
    ]
    
    # Load Master
    with open(master_file, "r") as f:
        master_data = json.load(f)
    
    existing_categories = {cat["category"]: cat for cat in master_data["job_terminology"]}
    
    for exp_file in expansion_files:
        if not os.path.exists(exp_file):
            print(f"⚠️ Skipping missing file: {exp_file}")
            continue
            
        with open(exp_file, "r") as f:
            exp_data = json.load(f)
            
        for exp_cat in exp_data["job_terminology"]:
            cat_name = exp_cat["category"]
            if cat_name in existing_categories:
                # Merge items into existing category
                existing_items = {item["name"]: item for item in existing_categories[cat_name]["items"]}
                for item in exp_cat["items"]:
                    if item["name"] not in existing_items:
                        existing_categories[cat_name]["items"].append(item)
                    else:
                        # Optionally merge synonyms
                        existing_syns = set(existing_items[item["name"]].get("synonyms", []))
                        new_syns = set(item.get("synonyms", []))
                        merged_syns = list(existing_syns.union(new_syns))
                        existing_items[item["name"]]["synonyms"] = merged_syns
            else:
                # Add new category
                master_data["job_terminology"].append(exp_cat)
                existing_categories[cat_name] = exp_cat
    
    # Save Master
    with open(master_file, "w") as f:
        json.dump(master_data, f, indent=4)
    
    print(f"✅ Master vocabulary merged. Total categories: {len(master_data['job_terminology'])}")

if __name__ == "__main__":
    merge_vocabularies()
