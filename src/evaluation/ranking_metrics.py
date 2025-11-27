"""
Ranking metrics evaluation: Kendall's tau, Spearman's rho, pairwise accuracy, nDCG@k.
Compares system rankings against ground truth rankings.
"""
from typing import Dict, List, Any, Tuple
import math
from scipy import stats
import numpy as np


class RankingMetricsEvaluator:
    """
    Evaluates ranking quality using standard IR metrics.
    Compares system-generated rankings to ground truth rankings.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize ranking metrics evaluator.
        
        Args:
            config: Evaluation configuration dictionary
        """
        self.config = config
        self.ranking_config = config.get('ranking_metrics', {})
        self.ndcg_k_values = self.ranking_config.get('ndcg_k_values', [3, 5, 10])
        self.pairwise_threshold = self.ranking_config.get('pairwise_threshold', 0.05)
    
    def evaluate_ranking(self, 
                        system_scores: Dict[str, float],
                        ground_truth_scores: Dict[str, float]) -> Dict[str, Any]:
        """
        Evaluate ranking quality using multiple metrics.
        
        Args:
            system_scores: Dictionary mapping resume ID to system score
            ground_truth_scores: Dictionary mapping resume ID to ground truth score
            
        Returns:
            Dictionary with all ranking metrics
        """
        # Get common resume IDs
        common_ids = set(system_scores.keys()) & set(ground_truth_scores.keys())
        
        if len(common_ids) < 2:
            return {
                'error': 'Insufficient common resumes for ranking evaluation',
                'common_count': len(common_ids)
            }
        
        # Convert to lists maintaining correspondence
        common_ids = list(common_ids)
        system_scores_list = [system_scores[rid] for rid in common_ids]
        gt_scores_list = [ground_truth_scores[rid] for rid in common_ids]
        
        # Calculate all metrics
        results = {
            'num_candidates': len(common_ids),
            'candidate_ids': common_ids,
            'kendall_tau': self._calculate_kendall_tau(system_scores_list, gt_scores_list),
            'spearman_rho': self._calculate_spearman_rho(system_scores_list, gt_scores_list),
            'pairwise_accuracy': self._calculate_pairwise_accuracy(
                system_scores_list, gt_scores_list, common_ids
            ),
            'ndcg': {}
        }
        
        # Calculate nDCG@k for different k values
        for k in self.ndcg_k_values:
            if k <= len(common_ids):
                results['ndcg'][f'nDCG@{k}'] = self._calculate_ndcg_at_k(
                    system_scores_list, gt_scores_list, common_ids, k
                )
        
        # Add interpretation
        results['interpretation'] = self._interpret_metrics(results)
        
        return results
    
    def _calculate_kendall_tau(self, system_scores: List[float], gt_scores: List[float]) -> Dict[str, Any]:
        """
        Calculate Kendall's tau rank correlation coefficient.
        
        Measures the ordinal association between two rankings.
        Range: [-1, 1], where 1 = perfect agreement, 0 = no correlation, -1 = perfect disagreement
        
        Returns:
            Dictionary with tau value, p-value, and interpretation
        """
        try:
            tau, p_value = stats.kendalltau(system_scores, gt_scores)
            
            return {
                'tau': round(float(tau), 4),
                'p_value': round(float(p_value), 6),
                'significant': p_value < 0.05,
                'interpretation': self._interpret_tau(tau)
            }
        except Exception as e:
            return {
                'tau': None,
                'error': str(e)
            }
    
    def _calculate_spearman_rho(self, system_scores: List[float], gt_scores: List[float]) -> Dict[str, Any]:
        """
        Calculate Spearman's rho rank correlation coefficient.
        
        Measures the monotonic relationship between two rankings.
        Range: [-1, 1], where 1 = perfect positive correlation
        
        Returns:
            Dictionary with rho value, p-value, and interpretation
        """
        try:
            rho, p_value = stats.spearmanr(system_scores, gt_scores)
            
            return {
                'rho': round(float(rho), 4),
                'p_value': round(float(p_value), 6),
                'significant': p_value < 0.05,
                'interpretation': self._interpret_rho(rho)
            }
        except Exception as e:
            return {
                'rho': None,
                'error': str(e)
            }
    
    def _calculate_pairwise_accuracy(self, 
                                    system_scores: List[float], 
                                    gt_scores: List[float],
                                    ids: List[str]) -> Dict[str, Any]:
        """
        Calculate pairwise ranking accuracy.
        
        For all pairs of candidates, checks if system ranking agrees with ground truth.
        
        Returns:
            Dictionary with accuracy, agreement counts, and sample disagreements
        """
        n = len(system_scores)
        total_pairs = 0
        correct_pairs = 0
        disagreements = []
        
        for i in range(n):
            for j in range(i + 1, n):
                # Skip pairs with very similar ground truth scores (within threshold)
                if abs(gt_scores[i] - gt_scores[j]) < self.pairwise_threshold:
                    continue
                
                total_pairs += 1
                
                # Check if order is preserved
                gt_order = gt_scores[i] > gt_scores[j]
                sys_order = system_scores[i] > system_scores[j]
                
                if gt_order == sys_order:
                    correct_pairs += 1
                else:
                    # Record disagreement
                    disagreements.append({
                        'candidate_1': ids[i],
                        'candidate_2': ids[j],
                        'gt_scores': [gt_scores[i], gt_scores[j]],
                        'system_scores': [system_scores[i], system_scores[j]],
                        'gt_winner': ids[i] if gt_order else ids[j],
                        'system_winner': ids[i] if sys_order else ids[j]
                    })
        
        accuracy = correct_pairs / total_pairs if total_pairs > 0 else 0.0
        
        return {
            'accuracy': round(accuracy, 4),
            'correct_pairs': correct_pairs,
            'total_pairs': total_pairs,
            'incorrect_pairs': total_pairs - correct_pairs,
            'sample_disagreements': disagreements[:5],  # Show first 5 disagreements
            'interpretation': self._interpret_pairwise_accuracy(accuracy)
        }
    
    def _calculate_ndcg_at_k(self, 
                            system_scores: List[float], 
                            gt_scores: List[float],
                            ids: List[str],
                            k: int) -> Dict[str, Any]:
        """
        Calculate Normalized Discounted Cumulative Gain at k (nDCG@k).
        
        Measures ranking quality with position-based discounting.
        Range: [0, 1], where 1 = perfect ranking
        
        Args:
            system_scores: System-generated scores
            gt_scores: Ground truth scores (used as relevance)
            ids: Resume IDs
            k: Cutoff position
            
        Returns:
            Dictionary with nDCG@k value and details
        """
        # Create ranking based on system scores
        ranked_indices = sorted(range(len(system_scores)), 
                               key=lambda i: system_scores[i], 
                               reverse=True)
        
        # Get top k
        top_k_indices = ranked_indices[:k]
        
        # Calculate DCG@k using ground truth scores as relevance
        dcg = 0.0
        for rank_pos, idx in enumerate(top_k_indices, start=1):
            relevance = gt_scores[idx]
            # DCG formula: rel_i / log2(i + 1)
            dcg += relevance / math.log2(rank_pos + 1)
        
        # Calculate IDCG@k (ideal DCG with perfect ranking)
        ideal_indices = sorted(range(len(gt_scores)), 
                              key=lambda i: gt_scores[i], 
                              reverse=True)
        ideal_top_k = ideal_indices[:k]
        
        idcg = 0.0
        for rank_pos, idx in enumerate(ideal_top_k, start=1):
            relevance = gt_scores[idx]
            idcg += relevance / math.log2(rank_pos + 1)
        
        # Calculate nDCG
        ndcg = dcg / idcg if idcg > 0 else 0.0
        
        # Get details of top k
        top_k_details = []
        for rank_pos, idx in enumerate(top_k_indices, start=1):
            top_k_details.append({
                'rank': rank_pos,
                'candidate': ids[idx],
                'system_score': round(system_scores[idx], 4),
                'gt_score': round(gt_scores[idx], 4),
                'ideal_rank': ideal_indices.index(idx) + 1
            })
        
        return {
            'ndcg': round(ndcg, 4),
            'dcg': round(dcg, 4),
            'idcg': round(idcg, 4),
            'k': k,
            'top_k_ranking': top_k_details,
            'interpretation': self._interpret_ndcg(ndcg)
        }
    
    def _interpret_tau(self, tau: float) -> str:
        """Interpret Kendall's tau value."""
        if tau >= 0.9:
            return "Excellent agreement"
        elif tau >= 0.7:
            return "Strong agreement"
        elif tau >= 0.5:
            return "Moderate agreement"
        elif tau >= 0.3:
            return "Weak agreement"
        elif tau >= 0:
            return "Very weak or no agreement"
        else:
            return "Negative correlation (disagreement)"
    
    def _interpret_rho(self, rho: float) -> str:
        """Interpret Spearman's rho value."""
        if rho >= 0.9:
            return "Very strong positive correlation"
        elif rho >= 0.7:
            return "Strong positive correlation"
        elif rho >= 0.5:
            return "Moderate positive correlation"
        elif rho >= 0.3:
            return "Weak positive correlation"
        elif rho >= 0:
            return "Very weak or no correlation"
        else:
            return "Negative correlation"
    
    def _interpret_pairwise_accuracy(self, accuracy: float) -> str:
        """Interpret pairwise accuracy."""
        if accuracy >= 0.95:
            return "Excellent pairwise agreement"
        elif accuracy >= 0.85:
            return "Very good pairwise agreement"
        elif accuracy >= 0.75:
            return "Good pairwise agreement"
        elif accuracy >= 0.65:
            return "Moderate pairwise agreement"
        elif accuracy >= 0.5:
            return "Fair pairwise agreement"
        else:
            return "Poor pairwise agreement"
    
    def _interpret_ndcg(self, ndcg: float) -> str:
        """Interpret nDCG value."""
        if ndcg >= 0.95:
            return "Excellent ranking quality"
        elif ndcg >= 0.85:
            return "Very good ranking quality"
        elif ndcg >= 0.75:
            return "Good ranking quality"
        elif ndcg >= 0.65:
            return "Moderate ranking quality"
        elif ndcg >= 0.5:
            return "Fair ranking quality"
        else:
            return "Poor ranking quality"
    
    def _interpret_metrics(self, results: Dict[str, Any]) -> Dict[str, str]:
        """Generate overall interpretation of all metrics."""
        interpretations = {
            'summary': '',
            'strengths': [],
            'weaknesses': []
        }
        
        # Analyze tau
        tau = results.get('kendall_tau', {}).get('tau')
        if tau and tau >= 0.7:
            interpretations['strengths'].append('Strong rank correlation (Kendall\'s tau)')
        elif tau and tau < 0.5:
            interpretations['weaknesses'].append('Weak rank correlation (Kendall\'s tau)')
        
        # Analyze rho
        rho = results.get('spearman_rho', {}).get('rho')
        if rho and rho >= 0.7:
            interpretations['strengths'].append('Strong monotonic relationship (Spearman\'s rho)')
        elif rho and rho < 0.5:
            interpretations['weaknesses'].append('Weak monotonic relationship (Spearman\'s rho)')
        
        # Analyze pairwise accuracy
        pairwise = results.get('pairwise_accuracy', {}).get('accuracy')
        if pairwise and pairwise >= 0.85:
            interpretations['strengths'].append('High pairwise ranking accuracy')
        elif pairwise and pairwise < 0.7:
            interpretations['weaknesses'].append('Low pairwise ranking accuracy')
        
        # Analyze nDCG
        ndcg_results = results.get('ndcg', {})
        if ndcg_results:
            avg_ndcg = np.mean([v['ndcg'] for v in ndcg_results.values() if isinstance(v, dict)])
            if avg_ndcg >= 0.85:
                interpretations['strengths'].append('High nDCG scores across all k values')
            elif avg_ndcg < 0.7:
                interpretations['weaknesses'].append('Low nDCG scores')
        
        # Generate summary
        if len(interpretations['strengths']) > len(interpretations['weaknesses']):
            interpretations['summary'] = 'Overall good ranking performance'
        elif len(interpretations['weaknesses']) > len(interpretations['strengths']):
            interpretations['summary'] = 'Ranking performance needs improvement'
        else:
            interpretations['summary'] = 'Mixed ranking performance'
        
        return interpretations


def calculate_ranking_metrics_from_results(system_results: Dict[str, Any],
                                          ground_truth_results: Dict[str, Any],
                                          config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Helper function to calculate ranking metrics from evaluation results.
    
    Args:
        system_results: System evaluation results with per-resume scores
        ground_truth_results: Ground truth evaluation results
        config: Configuration dictionary
        
    Returns:
        Dictionary with ranking metrics
    """
    evaluator = RankingMetricsEvaluator(config)
    
    # Extract scores
    system_scores = {}
    for resume_key, resume_data in system_results.get('per_resume', {}).items():
        system_scores[resume_key] = resume_data.get('final_score', 0.0)
    
    gt_scores = {}
    for resume_key, resume_data in ground_truth_results.get('per_resume', {}).items():
        gt_scores[resume_key] = resume_data.get('final_score', 0.0)
    
    return evaluator.evaluate_ranking(system_scores, gt_scores)
