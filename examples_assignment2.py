"""
Example: Using the Enhanced Evaluation System

This script demonstrates how to use the Assignment 2 components individually.
"""
import json
from pathlib import Path

# Import evaluation components
from src.evaluation.weighted_evaluate import WeightedResumeEvaluator
from src.evaluation.explanations import ExplanationGenerator
from src.evaluation.ranking_metrics import RankingMetricsEvaluator
from src.evaluation.faithfulness import FaithfulnessEvaluator
from src.evaluation.ablation import AblationStudy


def example_1_transparent_scoring():
    """Example 1: Transparent scoring with config"""
    print("=" * 80)
    print("Example 1: Transparent Scoring")
    print("=" * 80)
    
    # Load config
    with open('config/evaluation_config.json', 'r') as f:
        config = json.load(f)
    
    # Show configuration
    print("\nComponent Weights:")
    for component, weight in config['weights'].items():
        print(f"  {component}: {weight:.1%}")
    
    print("\nUniversity Tiers (sample):")
    for tier, data in config['university_tiers'].items():
        if not tier.startswith('_'):
            print(f"  {tier}: score={data['score']}, universities={len(data['universities'])}")
    
    print("\nUnknown Value Handling:")
    for field, policy in config['unknown_handling'].items():
        print(f"  {field}: {policy['strategy']} (score={policy['score']}) - {policy['explanation']}")
    
    print("\n✓ Configuration is transparent and documented!")


def example_2_evidence_extraction():
    """Example 2: Extract evidence from a resume"""
    print("\n" + "=" * 80)
    print("Example 2: Evidence-Linked Explanations")
    print("=" * 80)
    
    # Load config and resume
    with open('config/evaluation_config.json', 'r') as f:
        config = json.load(f)
    
    with open('data/output/results/parsed.json', 'r') as f:
        resumes = json.load(f)
    
    if not resumes:
        print("No resumes found. Run pipeline first!")
        return
    
    # Take first resume as example
    resume = resumes[0]
    
    # Create dummy scores for demonstration
    dummy_scores = {
        'component_scores': {
            'education': 0.75,
            'experience': 0.60,
            'publications': 0.30,
            'coherence': 0.80,
            'awards_other': 0.20
        },
        'final_score': 0.65,
        'grade': 'B'
    }
    
    # Generate evidence
    explainer = ExplanationGenerator(config)
    evidence = explainer.extract_evidence(resume, dummy_scores)
    
    print(f"\nCandidate: {evidence['candidate_name']}")
    print(f"Final Score: {evidence['score_summary']['final_score']:.2%} (Grade: {evidence['score_summary']['grade']})")
    
    print("\nEducation Evidence:")
    for edu in evidence['education_evidence'][:2]:  # Show first 2
        if not edu.get('missing'):
            print(f"  • {edu['evidence_span']}")
            print(f"    Tier: {edu['scoring_breakdown']['university_tier']['tier']} "
                  f"(score: {edu['scoring_breakdown']['university_tier']['score']:.2f})")
    
    print("\nExperience Evidence:")
    for exp in evidence['experience_evidence'][:2]:
        if not exp.get('missing'):
            print(f"  • {exp['evidence_span']}")
            print(f"    Seniority: {exp['scoring_breakdown']['seniority']['level']} "
                  f"(score: {exp['scoring_breakdown']['seniority']['score']:.2f})")
    
    print("\n✓ Evidence is linked to specific resume content!")


def example_3_ranking_metrics():
    """Example 3: Calculate ranking metrics"""
    print("\n" + "=" * 80)
    print("Example 3: Ranking Metrics (τ, ρ, nDCG@k)")
    print("=" * 80)
    
    # Example scores (in real usage, these come from evaluation)
    system_scores = {
        'candidate_1': 0.85,
        'candidate_2': 0.72,
        'candidate_3': 0.68,
        'candidate_4': 0.55,
        'candidate_5': 0.50
    }
    
    ground_truth_scores = {
        'candidate_1': 0.90,
        'candidate_2': 0.70,
        'candidate_3': 0.65,
        'candidate_4': 0.60,
        'candidate_5': 0.45
    }
    
    # Load config
    with open('config/evaluation_config.json', 'r') as f:
        config = json.load(f)
    
    # Calculate metrics
    evaluator = RankingMetricsEvaluator(config)
    metrics = evaluator.evaluate_ranking(system_scores, ground_truth_scores)
    
    print(f"\nNumber of candidates: {metrics['num_candidates']}")
    
    print(f"\nKendall's τ: {metrics['kendall_tau']['tau']:.4f}")
    print(f"  Interpretation: {metrics['kendall_tau']['interpretation']}")
    print(f"  Significant: {metrics['kendall_tau']['significant']}")
    
    print(f"\nSpearman's ρ: {metrics['spearman_rho']['rho']:.4f}")
    print(f"  Interpretation: {metrics['spearman_rho']['interpretation']}")
    
    print(f"\nPairwise Accuracy: {metrics['pairwise_accuracy']['accuracy']:.1%}")
    print(f"  Correct pairs: {metrics['pairwise_accuracy']['correct_pairs']}/{metrics['pairwise_accuracy']['total_pairs']}")
    
    print("\nnDCG@k:")
    for k_metric, data in metrics['ndcg'].items():
        print(f"  {k_metric}: {data['ndcg']:.4f} - {data['interpretation']}")
    
    print("\n✓ Multiple ranking metrics calculated!")


def example_4_ablation_study():
    """Example 4: Run ablation study"""
    print("\n" + "=" * 80)
    print("Example 4: Ablation Studies")
    print("=" * 80)
    
    # Load config
    with open('config/evaluation_config.json', 'r') as f:
        config = json.load(f)
    
    # Create ablation study
    ablation = AblationStudy(config)
    
    print("\nAvailable Ablations:")
    for name in ablation.get_all_ablation_names():
        spec = ablation.ABLATION_CONFIGS[name]
        print(f"  • {spec['name']}")
        print(f"    {spec['description']}")
    
    print("\nGenerating ablation config: no_coherence")
    no_coh_config = ablation.generate_ablation_config('no_coherence')
    
    print(f"  Modified weights:")
    for component, weight in no_coh_config['weights'].items():
        original = config['weights'].get(component, 0)
        if weight != original:
            print(f"    {component}: {original:.2f} → {weight:.2f}")
    
    print("\n✓ Ablation configurations can be generated!")


def example_5_faithfulness():
    """Example 5: Evaluate explanation faithfulness"""
    print("\n" + "=" * 80)
    print("Example 5: Explanation Faithfulness")
    print("=" * 80)
    
    # Example comparison explanation
    comparison = {
        'candidate_a': 'John Doe',
        'candidate_b': 'Jane Smith',
        'final_score_a': 0.85,
        'final_score_b': 0.72,
        'score_delta': 0.13,
        'component_deltas': [
            {
                'component': 'education',
                'score_a': 0.90,
                'score_b': 0.70,
                'delta': 0.20,
                'weighted_delta': 0.06,
                'weight': 0.30
            }
        ],
        'top_3_reasons': [
            {
                'rank': 1,
                'component': 'education',
                'delta': 0.20,
                'weighted_impact': 0.06,
                'reason': 'Better education',
                'evidence_a': ['PhD from MIT'],
                'evidence_b': ['BS from Local U']
            }
        ]
    }
    
    # Example actual scores (these should match comparison)
    scores_a = {
        'final_score': 0.85,
        'component_scores': {'education': 0.90}
    }
    scores_b = {
        'final_score': 0.72,
        'component_scores': {'education': 0.70}
    }
    
    # Load config
    with open('config/evaluation_config.json', 'r') as f:
        config = json.load(f)
    
    # Evaluate faithfulness
    evaluator = FaithfulnessEvaluator(config)
    result = evaluator.evaluate_explanation_faithfulness(
        comparison, scores_a, scores_b, {}, {}
    )
    
    print(f"\nFaithfulness Score: {result['faithfulness_score']:.2f}/1.00")
    print(f"Overall Faithful: {result['overall_faithful']}")
    print(f"Interpretation: {result['interpretation']}")
    
    print("\nChecks Performed:")
    for check in result['checks']:
        status = "✓" if check['passed'] else "✗"
        print(f"  {status} {check['check']}")
    
    if result['issues']:
        print("\nIssues Found:")
        for issue in result['issues']:
            print(f"  • {issue}")
    else:
        print("\n✓ No issues found - explanations are faithful!")


def main():
    """Run all examples"""
    print("\n" + "=" * 80)
    print("ASSIGNMENT 2: Enhanced Evaluation Examples")
    print("=" * 80)
    print("\nThis script demonstrates the key features of Assignment 2.\n")
    
    # Check if required files exist
    required_files = [
        'config/evaluation_config.json',
        'data/output/results/parsed.json'
    ]
    
    for file_path in required_files:
        if not Path(file_path).exists():
            print(f"⚠️  Warning: {file_path} not found")
            print("   Run 'python pipeline.py --ground-truth config/ground_truth/parsed.json' first")
            print()
    
    try:
        # Run examples
        example_1_transparent_scoring()
        example_2_evidence_extraction()
        example_3_ranking_metrics()
        example_4_ablation_study()
        example_5_faithfulness()
        
        print("\n" + "=" * 80)
        print("All examples completed successfully!")
        print("=" * 80)
        print("\nTo run the full evaluation pipeline:")
        print("  python run_assignment2.py data/output/results/parsed.json config/ground_truth/parsed.json")
        print()
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
