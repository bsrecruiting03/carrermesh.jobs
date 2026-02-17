
import sys
import os

# Add root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intelligence.skill_normalizer import SkillNormalizer

def test_normalization():
    print("--- Testing Skill Normalizer ---")
    normalizer = SkillNormalizer()
    
    test_cases = [
        "React", "React.js", "reactjs", "ReactJS", 
        "Python", "python 3", 
        "AWS", "amazon web services",
        "UnknownSkill123"
    ]
    
    for raw in test_cases:
        norm = normalizer.normalize(raw)
        print(f"'{raw}' -> '{norm}'")

    print("\n--- List Test ---")
    raw_list = ["ReactJS", "Node.js", "Python", "UnknownThing"]
    norm_list = normalizer.normalize_list(raw_list)
    print(f"Input: {raw_list}")
    print(f"Output: {norm_list}")

if __name__ == "__main__":
    test_normalization()
