"""
Enhanced Evaluation Pipeline with Ranking, Explanations, and Ablations
Integrates: Transparent scoring, Evidence-linked explanations, Ranking metrics, Faithfulness, Ablations
"""
import json
import os
import numpy as np
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# Import all evaluation components
from src.evaluation.weighted_evaluate import WeightedResumeEvaluator
from src.evaluation.explanations import ExplanationGenerator
from src.evaluation.ranking_metrics import RankingMetricsEvaluator
from src.evaluation.faithfulness import FaithfulnessEvaluator
from src.evaluation.ablation import AblationStudy


class NumpyJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle numpy types."""
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


class EnhancedEvaluationPipeline:
    """
    Complete evaluation pipeline for Assignment 2:
    - Configurable scoring with transparent unknowns handling
    - Evidence-linked explanations with "why A > B" comparisons
    - Ranking metrics (τ, ρ, pairwise acc., nDCG@k)
    - Faithfulness evaluation
    - Ablation studies
    """
    
    def __init__(self,
                 generated_path: str,
                 ground_truth_path: str,
                 config_path: str = "config/evaluation_config.json",
                 output_dir: str = "data/output/results"):
        """
        Initialize enhanced evaluation pipeline.
        
        Args:
            generated_path: Path to generated/parsed resumes JSON
            ground_truth_path: Path to ground truth JSON
            config_path: Path to evaluation configuration
            output_dir: Directory for output files
        """
        self.generated_path = generated_path
        self.ground_truth_path = ground_truth_path
        self.config_path = config_path
        self.output_dir = Path(output_dir)
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load configuration
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        # Initialize components
        self.explanation_generator = ExplanationGenerator(self.config)
        self.ranking_evaluator = RankingMetricsEvaluator(self.config)
        self.faithfulness_evaluator = FaithfulnessEvaluator(self.config)
        self.ablation_study = AblationStudy(self.config)
        
        # Results storage
        self.results = {}
    
    def run_full_evaluation(self) -> Dict[str, Any]:
        """
        Run complete evaluation pipeline.
        
        Returns:
            Dictionary with all evaluation results
        """
        print("=" * 80)
        print("ENHANCED EVALUATION PIPELINE - Assignment 2")
        print("=" * 80)
        print()
        
        # Step 1: Baseline evaluation with transparent scoring
        print("Step 1: Running baseline evaluation with transparent scoring...")
        baseline_results = self._run_baseline_evaluation()
        self.results['baseline_evaluation'] = baseline_results
        print(f"✓ Baseline evaluation complete")
        print(f"  Average score: {baseline_results['evaluation_results']['aggregate']['final_scores_avg']:.4f}")
        print()
        
        # Step 2: Generate evidence-linked explanations
        print("Step 2: Generating evidence-linked explanations...")
        explanations = self._generate_explanations(baseline_results)
        self.results['explanations'] = explanations
        print(f"✓ Generated explanations for {len(explanations.get('per_candidate', {}))} candidates")
        print()
        
        # Step 3: Generate ranking and comparisons
        print("Step 3: Generating rankings and pairwise comparisons...")
        rankings = self._generate_rankings(baseline_results, explanations)
        self.results['rankings'] = rankings
        print(f"✓ Ranked {len(rankings['ranking_list'])} candidates")
        print(f"  Top candidate: {rankings['ranking_list'][0]['candidate']} "
              f"(score: {rankings['ranking_list'][0]['score']:.4f})")
        print()
        
        # Step 4: Calculate ranking metrics
        print("Step 4: Calculating ranking metrics (τ, ρ, pairwise acc., nDCG@k)...")
        ranking_metrics = self._calculate_ranking_metrics(baseline_results)
        self.results['ranking_metrics'] = ranking_metrics
        print(f"✓ Ranking metrics calculated")
        if 'kendall_tau' in ranking_metrics:
            print(f"  Kendall's τ: {ranking_metrics['kendall_tau'].get('tau', 'N/A')}")
        if 'spearman_rho' in ranking_metrics:
            print(f"  Spearman's ρ: {ranking_metrics['spearman_rho'].get('rho', 'N/A')}")
        print()
        
        # Step 5: Evaluate explanation faithfulness
        print("Step 5: Evaluating explanation faithfulness...")
        faithfulness = self._evaluate_faithfulness(rankings, baseline_results, explanations)
        self.results['faithfulness'] = faithfulness
        print(f"✓ Faithfulness evaluation complete")
        print(f"  Global faithfulness score: {faithfulness.get('global_faithfulness_score', 'N/A')}")
        print()
        
        # Step 6: Run ablation studies
        print("Step 6: Running ablation studies...")
        ablations = self._run_ablation_studies()
        self.results['ablation_studies'] = ablations
        print(f"✓ Completed {len(ablations.get('ablation_results', {}))} ablation configurations")
        print()
        
        # Step 7: Save all results
        print("Step 7: Saving results...")
        self._save_results()
        print("✓ All results saved")
        print()
        
        # Generate summary
        self._print_summary()
        
        return self.results
    
    def _run_baseline_evaluation(self) -> Dict[str, Any]:
        """Run baseline weighted evaluation."""
        evaluator = WeightedResumeEvaluator(
            self.generated_path,
            self.ground_truth_path,
            self.config_path
        )
        
        evaluation_results = evaluator.evaluate_all()
        
        return {
            'evaluation_results': evaluation_results,
            'config_used': self.config
        }
    
    def _generate_explanations(self, baseline_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate evidence-linked explanations for all candidates."""
        eval_results = baseline_results['evaluation_results']
        per_resume = eval_results['per_resume']
        
        # Load resume data
        with open(self.generated_path, 'r', encoding='utf-8') as f:
            resumes = json.load(f)
        
        # Create resume map
        resume_map = {}
        for resume in resumes:
            key = resume.get('filename', resume.get('name', ''))
            if key:
                resume_map[key] = resume
        
        # Generate evidence for each candidate
        explanations_per_candidate = {}
        
        for resume_key, scores in per_resume.items():
            resume = resume_map.get(resume_key, {})
            evidence = self.explanation_generator.extract_evidence(resume, scores)
            explanations_per_candidate[resume_key] = evidence
        
        return {
            'per_candidate': explanations_per_candidate,
            'generation_timestamp': datetime.now().isoformat()
        }
    
    def _generate_rankings(self, baseline_results: Dict[str, Any], 
                          explanations: Dict[str, Any]) -> Dict[str, Any]:
        """Generate rankings and pairwise comparisons with explanations."""
        eval_results = baseline_results['evaluation_results']
        per_resume = eval_results['per_resume']
        
        # Create ranking list
        ranking_list = []
        for resume_key, scores in per_resume.items():
            ranking_list.append({
                'candidate': resume_key,
                'score': scores['final_score'],
                'grade': scores['grade'],
                'component_scores': scores['component_scores']
            })
        
        # Sort by score descending
        ranking_list.sort(key=lambda x: x['score'], reverse=True)
        
        # Add ranks
        for rank, item in enumerate(ranking_list, start=1):
            item['rank'] = rank
        
        # Generate pairwise comparisons for top candidates
        comparisons = []
        evidence_map = explanations['per_candidate']
        
        # Compare top 5 candidates pairwise
        top_candidates = ranking_list[:min(5, len(ranking_list))]
        
        for i in range(len(top_candidates)):
            for j in range(i + 1, len(top_candidates)):
                candidate_a = top_candidates[i]['candidate']
                candidate_b = top_candidates[j]['candidate']
                
                scores_a = per_resume[candidate_a]
                scores_b = per_resume[candidate_b]
                evidence_a = evidence_map.get(candidate_a, {})
                evidence_b = evidence_map.get(candidate_b, {})
                
                # Generate comparison
                comparison = self.explanation_generator.generate_comparison_explanation(
                    {}, scores_a, evidence_a,
                    {}, scores_b, evidence_b
                )
                
                comparisons.append(comparison)
        
        return {
            'ranking_list': ranking_list,
            'pairwise_comparisons': comparisons,
            'total_candidates': len(ranking_list)
        }
    
    def _calculate_ranking_metrics(self, baseline_results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate ranking metrics comparing to ground truth."""
        eval_results = baseline_results['evaluation_results']
        per_resume = eval_results['per_resume']
        
        # Extract system scores
        system_scores = {}
        for resume_key, scores in per_resume.items():
            system_scores[resume_key] = scores['final_score']
        
        # For ground truth scores, we use the same evaluation on ground truth
        # (In a real scenario, you'd have pre-computed ground truth rankings)
        # For this implementation, we'll use the scores themselves as ground truth
        # since we're evaluating extraction quality
        
        # Load ground truth and evaluate
        gt_evaluator = WeightedResumeEvaluator(
            self.ground_truth_path,  # Use ground truth as both source and reference
            self.ground_truth_path,
            self.config_path
        )
        gt_results = gt_evaluator.evaluate_all()
        
        gt_scores = {}
        for resume_key, scores in gt_results['per_resume'].items():
            gt_scores[resume_key] = scores['final_score']
        
        # Calculate ranking metrics
        return self.ranking_evaluator.evaluate_ranking(system_scores, gt_scores)
    
    def _evaluate_faithfulness(self, rankings: Dict[str, Any],
                               baseline_results: Dict[str, Any],
                               explanations: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate faithfulness of explanations."""
        comparisons = rankings.get('pairwise_comparisons', [])
        per_resume = baseline_results['evaluation_results']['per_resume']
        evidence_map = explanations['per_candidate']
        
        # Evaluate each comparison
        faithfulness_results = []
        
        for comparison in comparisons[:10]:  # Evaluate top 10 comparisons
            candidate_a = comparison.get('candidate_a')
            candidate_b = comparison.get('candidate_b')
            
            if not candidate_a or not candidate_b:
                continue
            
            scores_a = per_resume.get(candidate_a, {})
            scores_b = per_resume.get(candidate_b, {})
            evidence_a = evidence_map.get(candidate_a, {})
            evidence_b = evidence_map.get(candidate_b, {})
            
            if not scores_a or not scores_b:
                continue
            
            faithfulness = self.faithfulness_evaluator.evaluate_explanation_faithfulness(
                comparison, scores_a, scores_b, evidence_a, evidence_b
            )
            
            faithfulness_results.append({
                'comparison': f"{candidate_a} vs {candidate_b}",
                'faithfulness_score': faithfulness['faithfulness_score'],
                'issues': faithfulness['issues']
            })
        
        # Calculate global metrics
        if faithfulness_results:
            avg_faithfulness = sum(f['faithfulness_score'] for f in faithfulness_results) / len(faithfulness_results)
        else:
            avg_faithfulness = 0.0
        
        return {
            'global_faithfulness_score': round(avg_faithfulness, 4),
            'individual_faithfulness': faithfulness_results,
            'total_comparisons_evaluated': len(faithfulness_results)
        }
    
    def _run_ablation_studies(self) -> Dict[str, Any]:
        """Run ablation studies with different configurations."""
        ablation_names = ['baseline', 'no_coherence', 'no_university_tiers']
        ablation_results = {}
        
        for ablation_name in ablation_names:
            print(f"  Running ablation: {ablation_name}...")
            
            # Generate ablation config
            if ablation_name == 'baseline':
                ablation_config = self.config
            else:
                ablation_config = self.ablation_study.generate_ablation_config(ablation_name)
            
            # Save temporary config
            temp_config_path = self.output_dir / f"temp_config_{ablation_name}.json"
            with open(temp_config_path, 'w', encoding='utf-8') as f:
                json.dump(ablation_config, f, indent=2)
            
            # Run evaluation with this config
            evaluator = WeightedResumeEvaluator(
                self.generated_path,
                self.ground_truth_path,
                str(temp_config_path)
            )
            
            eval_results = evaluator.evaluate_all()
            
            # Calculate ranking metrics for this ablation
            system_scores = {k: v['final_score'] for k, v in eval_results['per_resume'].items()}
            
            # Use baseline ground truth scores for comparison
            gt_evaluator = WeightedResumeEvaluator(
                self.ground_truth_path,
                self.ground_truth_path,
                self.config_path
            )
            gt_results = gt_evaluator.evaluate_all()
            gt_scores = {k: v['final_score'] for k, v in gt_results['per_resume'].items()}
            
            ranking_metrics = self.ranking_evaluator.evaluate_ranking(system_scores, gt_scores)
            
            ablation_results[ablation_name] = {
                'evaluation_results': eval_results,
                'ranking_metrics': ranking_metrics
            }
            
            # Clean up temp config
            temp_config_path.unlink()
        
        # Compare ablations
        comparison = self.ablation_study.compare_ablations(ablation_results)
        
        return {
            'ablation_results': ablation_results,
            'comparison': comparison
        }
    
    def _save_results(self):
        """Save all results to JSON files."""
        # Save main results
        main_output = self.output_dir / "enhanced_evaluation_results.json"
        with open(main_output, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False, cls=NumpyJSONEncoder)
        
        # Save explanations separately (for readability)
        explanations_output = self.output_dir / "explanations.json"
        with open(explanations_output, 'w', encoding='utf-8') as f:
            json.dump(self.results.get('explanations', {}), f, indent=2, ensure_ascii=False, cls=NumpyJSONEncoder)
        
        # Save rankings
        rankings_output = self.output_dir / "rankings.json"
        with open(rankings_output, 'w', encoding='utf-8') as f:
            json.dump(self.results.get('rankings', {}), f, indent=2, ensure_ascii=False, cls=NumpyJSONEncoder)
        
        # Save ranking metrics
        metrics_output = self.output_dir / "ranking_metrics.json"
        with open(metrics_output, 'w', encoding='utf-8') as f:
            json.dump(self.results.get('ranking_metrics', {}), f, indent=2, ensure_ascii=False, cls=NumpyJSONEncoder)
        
        # Save faithfulness results
        faithfulness_output = self.output_dir / "faithfulness_evaluation.json"
        with open(faithfulness_output, 'w', encoding='utf-8') as f:
            json.dump(self.results.get('faithfulness', {}), f, indent=2, ensure_ascii=False, cls=NumpyJSONEncoder)
        
        # Save ablation studies
        ablation_output = self.output_dir / "ablation_studies.json"
        with open(ablation_output, 'w', encoding='utf-8') as f:
            json.dump(self.results.get('ablation_studies', {}), f, indent=2, ensure_ascii=False, cls=NumpyJSONEncoder)
        
        print(f"\n  Saved results to:")
        print(f"    - {main_output}")
        print(f"    - {explanations_output}")
        print(f"    - {rankings_output}")
        print(f"    - {metrics_output}")
        print(f"    - {faithfulness_output}")
        print(f"    - {ablation_output}")
    
    def _print_summary(self):
        """Print evaluation summary."""
        print("=" * 80)
        print("EVALUATION SUMMARY")
        print("=" * 80)
        print()
        
        # Baseline scores
        baseline = self.results.get('baseline_evaluation', {}).get('evaluation_results', {})
        if baseline:
            print("Baseline Performance:")
            agg = baseline.get('aggregate', {})
            print(f"  Average Score: {agg.get('final_scores_avg', 0):.4f}")
            print(f"  Education: {agg.get('education_avg', 0):.4f}")
            print(f"  Experience: {agg.get('experience_avg', 0):.4f}")
            print(f"  Publications: {agg.get('publications_avg', 0):.4f}")
            print(f"  Coherence: {agg.get('coherence_avg', 0):.4f}")
            print()
        
        # Ranking metrics
        ranking_metrics = self.results.get('ranking_metrics', {})
        if ranking_metrics:
            print("Ranking Metrics:")
            tau = ranking_metrics.get('kendall_tau', {})
            if tau:
                print(f"  Kendall's τ: {tau.get('tau', 'N/A')} ({tau.get('interpretation', '')})")
            rho = ranking_metrics.get('spearman_rho', {})
            if rho:
                print(f"  Spearman's ρ: {rho.get('rho', 'N/A')} ({rho.get('interpretation', '')})")
            pairwise = ranking_metrics.get('pairwise_accuracy', {})
            if pairwise:
                print(f"  Pairwise Accuracy: {pairwise.get('accuracy', 'N/A')} ({pairwise.get('interpretation', '')})")
            ndcg = ranking_metrics.get('ndcg', {})
            if ndcg:
                for k, v in ndcg.items():
                    if isinstance(v, dict):
                        print(f"  {k}: {v.get('ndcg', 'N/A')} ({v.get('interpretation', '')})")
            print()
        
        # Faithfulness
        faithfulness = self.results.get('faithfulness', {})
        if faithfulness:
            print("Explanation Faithfulness:")
            print(f"  Global Score: {faithfulness.get('global_faithfulness_score', 'N/A')}")
            print(f"  Comparisons Evaluated: {faithfulness.get('total_comparisons_evaluated', 0)}")
            print()
        
        # Ablations
        ablations = self.results.get('ablation_studies', {})
        if ablations:
            comparison = ablations.get('comparison', {})
            print("Ablation Studies:")
            print(f"  {comparison.get('summary', 'No summary available')}")
            insights = comparison.get('insights', [])
            if insights:
                print("\n  Key Insights:")
                for insight in insights[:3]:  # Top 3 insights
                    print(f"    • {insight}")
            print()
        
        print("=" * 80)


def main():
    """Main function to run enhanced evaluation pipeline."""
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python enhanced_evaluation.py <generated_json> <ground_truth_json> [config_json]")
        print("\nExample:")
        print("  python enhanced_evaluation.py data/output/results/parsed.json "
              "config/ground_truth/parsed.json config/evaluation_config.json")
        sys.exit(1)
    
    generated_path = sys.argv[1]
    ground_truth_path = sys.argv[2]
    config_path = sys.argv[3] if len(sys.argv) > 3 else "config/evaluation_config.json"
    
    # Validate paths
    if not os.path.exists(generated_path):
        print(f"Error: Generated JSON not found: {generated_path}")
        sys.exit(1)
    
    if not os.path.exists(ground_truth_path):
        print(f"Error: Ground truth JSON not found: {ground_truth_path}")
        sys.exit(1)
    
    if not os.path.exists(config_path):
        print(f"Error: Config JSON not found: {config_path}")
        sys.exit(1)
    
    # Run enhanced evaluation
    pipeline = EnhancedEvaluationPipeline(
        generated_path,
        ground_truth_path,
        config_path
    )
    
    results = pipeline.run_full_evaluation()
    
    print("\n✓ Enhanced evaluation pipeline complete!")
    print(f"\nAll results saved to: data/output/results/")


if __name__ == '__main__':
    main()
