#!/usr/bin/env python3
"""
Quick test script to run the enhanced evaluation on a sample of 10 CVs.
This tests the Assignment 2 implementation without requiring API key (uses existing parsed data).
"""
import json
import sys
from pathlib import Path

def main():
    print("=" * 80)
    print("QUICK TEST - Enhanced Evaluation on Sample CVs")
    print("=" * 80)
    print()
    
    # Check if parsed.json exists
    parsed_file = Path("data/output/results/parsed.json")
    ground_truth = Path("config/ground_truth/parsed.json")
    
    if not parsed_file.exists():
        print("❌ Error: parsed.json not found!")
        print("   Please run the full pipeline first to parse CVs:")
        print("   python pipeline.py --ground-truth config/ground_truth/parsed.json")
        return 1
    
    # Load and sample 10 candidates
    print("📂 Loading existing parsed data...")
    with open(parsed_file, 'r', encoding='utf-8') as f:
        all_candidates = json.load(f)
    
    print(f"   Found {len(all_candidates)} candidates")
    
    # Take first 10 candidates
    sample_candidates = all_candidates[:10]
    sample_file = Path("data/output/results/sample_10_parsed.json")
    
    print(f"   Creating sample of 10 candidates: {sample_file}")
    with open(sample_file, 'w', encoding='utf-8') as f:
        json.dump(sample_candidates, f, indent=2, ensure_ascii=False)
    
    print("\n🚀 Running enhanced evaluation on 10 candidates...")
    print()
    
    # Run enhanced evaluation
    from src.evaluation.enhanced_evaluation import main as run_evaluation
    
    # Temporarily replace sys.argv
    old_argv = sys.argv
    sys.argv = [
        'run_assignment2.py',
        str(sample_file),
        str(ground_truth)
    ]
    
    try:
        run_evaluation()
        print("\n✅ Test completed successfully!")
        print("\n📊 Results saved to data/output/results/")
        print("   - enhanced_evaluation_results.json")
        print("   - explanations.json")
        print("   - rankings.json")
        print("   - ranking_metrics.json")
        print("   - faithfulness_evaluation.json")
        print("   - ablation_studies.json")
        return 0
    except Exception as e:
        print(f"\n❌ Error during evaluation: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        sys.argv = old_argv

if __name__ == "__main__":
    sys.exit(main())
