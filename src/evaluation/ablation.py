"""
Ablation studies for scoring system.
Tests impact of different components on ranking performance.
"""
import json
import copy
from typing import Dict, List, Any, Tuple


class AblationStudy:
    """
    Conducts ablation studies to understand component contributions.
    Tests system performance with different features removed.
    """
    
    ABLATION_CONFIGS = {
        'baseline': {
            'name': 'Baseline (Full System)',
            'description': 'Complete system with all features enabled',
            'modifications': {}
        },
        'no_coherence': {
            'name': 'Without Coherence',
            'description': 'Remove coherence scoring component',
            'modifications': {
                'weights': {
                    'coherence': 0.0,
                    # Redistribute weight proportionally
                    'education': 0.32,
                    'experience': 0.32,
                    'publications': 0.27,
                    'awards_other': 0.09
                }
            }
        },
        'no_university_tiers': {
            'name': 'Without University Tiers',
            'description': 'Remove university tier-based scoring (all universities equal)',
            'modifications': {
                'university_tiers': {
                    'tier1': {'score': 0.6, 'universities': []},
                    'tier2': {'score': 0.6, 'universities': []},
                    'tier3': {'score': 0.6, 'universities': []}
                },
                'policies': {
                    'unknown_university_score': 0.6
                }
            }
        },
        'no_if_weighting': {
            'name': 'Without Impact Factor Weighting',
            'description': 'Remove journal impact factor weighting (all publications equal)',
            'modifications': {
                'publication_if_thresholds': {
                    'high': {'min': 5.0, 'score': 0.5},
                    'medium': {'min': 2.0, 'max': 5.0, 'score': 0.5},
                    'low': {'min': 0.0, 'max': 2.0, 'score': 0.5},
                    'unknown': {'score': 0.5}
                }
            }
        },
        'no_seniority': {
            'name': 'Without Seniority Detection',
            'description': 'Remove seniority-based scoring for experience',
            'modifications': {
                'experience_seniority_keywords': {
                    'senior': [],
                    'mid': [],
                    'junior': []
                }
            }
        },
        'uniform_weights': {
            'name': 'Uniform Component Weights',
            'description': 'Equal weights for all components',
            'modifications': {
                'weights': {
                    'education': 0.20,
                    'experience': 0.20,
                    'publications': 0.20,
                    'coherence': 0.20,
                    'awards_other': 0.20
                }
            }
        }
    }
    
    def __init__(self, base_config: Dict[str, Any]):
        """
        Initialize ablation study with base configuration.
        
        Args:
            base_config: Base evaluation configuration
        """
        self.base_config = base_config
    
    def generate_ablation_config(self, ablation_name: str) -> Dict[str, Any]:
        """
        Generate configuration for specific ablation.
        
        Args:
            ablation_name: Name of ablation (key from ABLATION_CONFIGS)
            
        Returns:
            Modified configuration dictionary
        """
        if ablation_name not in self.ABLATION_CONFIGS:
            raise ValueError(f"Unknown ablation: {ablation_name}")
        
        ablation_spec = self.ABLATION_CONFIGS[ablation_name]
        
        # Deep copy base config
        ablation_config = copy.deepcopy(self.base_config)
        
        # Apply modifications
        modifications = ablation_spec.get('modifications', {})
        for key, value in modifications.items():
            if isinstance(value, dict) and key in ablation_config:
                # Merge dictionaries
                ablation_config[key].update(value)
            else:
                ablation_config[key] = value
        
        # Add metadata
        ablation_config['_ablation'] = {
            'name': ablation_spec['name'],
            'description': ablation_spec['description'],
            'ablation_id': ablation_name
        }
        
        return ablation_config
    
    def get_all_ablation_names(self) -> List[str]:
        """Get list of all ablation study names."""
        return list(self.ABLATION_CONFIGS.keys())
    
    def compare_ablations(self, ablation_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compare results across different ablations.
        
        Args:
            ablation_results: Dictionary mapping ablation name to evaluation results
            
        Returns:
            Dictionary with comparative analysis
        """
        if 'baseline' not in ablation_results:
            return {
                'error': 'Baseline results required for comparison'
            }
        
        baseline = ablation_results['baseline']
        comparisons = []
        
        # Extract baseline metrics
        baseline_metrics = self._extract_metrics(baseline)
        
        for ablation_name, results in ablation_results.items():
            if ablation_name == 'baseline':
                continue
            
            ablation_metrics = self._extract_metrics(results)
            
            # Calculate deltas
            delta = {
                'ablation': ablation_name,
                'name': self.ABLATION_CONFIGS[ablation_name]['name'],
                'description': self.ABLATION_CONFIGS[ablation_name]['description'],
                'metric_changes': {}
            }
            
            for metric_name, baseline_value in baseline_metrics.items():
                ablation_value = ablation_metrics.get(metric_name, 0.0)
                change = ablation_value - baseline_value
                pct_change = (change / baseline_value * 100) if baseline_value != 0 else 0.0
                
                delta['metric_changes'][metric_name] = {
                    'baseline': round(baseline_value, 4),
                    'ablation': round(ablation_value, 4),
                    'absolute_change': round(change, 4),
                    'percent_change': round(pct_change, 2)
                }
            
            # Calculate overall impact
            delta['overall_impact'] = self._calculate_overall_impact(delta['metric_changes'])
            
            comparisons.append(delta)
        
        # Sort by overall impact (descending)
        comparisons.sort(key=lambda x: abs(x['overall_impact']), reverse=True)
        
        # Generate insights
        insights = self._generate_insights(comparisons, baseline_metrics)
        
        return {
            'baseline_metrics': baseline_metrics,
            'ablation_comparisons': comparisons,
            'insights': insights,
            'summary': self._generate_summary(comparisons)
        }
    
    def _extract_metrics(self, results: Dict[str, Any]) -> Dict[str, float]:
        """Extract key metrics from results."""
        metrics = {}
        
        # Extract ranking metrics
        ranking_metrics = results.get('ranking_metrics', {})
        if ranking_metrics:
            # Kendall's tau
            tau_data = ranking_metrics.get('kendall_tau', {})
            if tau_data and 'tau' in tau_data:
                metrics['kendall_tau'] = tau_data['tau']
            
            # Spearman's rho
            rho_data = ranking_metrics.get('spearman_rho', {})
            if rho_data and 'rho' in rho_data:
                metrics['spearman_rho'] = rho_data['rho']
            
            # Pairwise accuracy
            pairwise_data = ranking_metrics.get('pairwise_accuracy', {})
            if pairwise_data and 'accuracy' in pairwise_data:
                metrics['pairwise_accuracy'] = pairwise_data['accuracy']
            
            # nDCG (average across k values)
            ndcg_data = ranking_metrics.get('ndcg', {})
            if ndcg_data:
                ndcg_values = [v['ndcg'] for v in ndcg_data.values() if isinstance(v, dict)]
                if ndcg_values:
                    metrics['avg_ndcg'] = sum(ndcg_values) / len(ndcg_values)
        
        # Extract evaluation metrics
        eval_results = results.get('evaluation_results', {})
        if eval_results:
            overall = eval_results.get('overall', {})
            if overall:
                metrics['precision'] = overall.get('precision', 0.0)
                metrics['recall'] = overall.get('recall', 0.0)
                metrics['f1'] = overall.get('f1', 0.0)
        
        return metrics
    
    def _calculate_overall_impact(self, metric_changes: Dict[str, Dict[str, Any]]) -> float:
        """
        Calculate overall impact score from metric changes.
        Positive = improvement, Negative = degradation
        """
        # Weight different metrics
        weights = {
            'kendall_tau': 0.25,
            'spearman_rho': 0.25,
            'pairwise_accuracy': 0.25,
            'avg_ndcg': 0.25
        }
        
        total_impact = 0.0
        total_weight = 0.0
        
        for metric_name, change_data in metric_changes.items():
            if metric_name in weights:
                weight = weights[metric_name]
                change = change_data['absolute_change']
                total_impact += change * weight
                total_weight += weight
        
        return total_impact / total_weight if total_weight > 0 else 0.0
    
    def _generate_insights(self, comparisons: List[Dict[str, Any]], baseline_metrics: Dict[str, float]) -> List[str]:
        """Generate insights from ablation comparisons."""
        insights = []
        
        # Find most impactful ablation
        if comparisons:
            most_impactful = comparisons[0]
            impact = most_impactful['overall_impact']
            
            if abs(impact) > 0.05:
                direction = "degraded" if impact < 0 else "improved"
                insights.append(
                    f"Removing {most_impactful['name']} had the largest impact, "
                    f"{direction} performance by {abs(impact):.4f}"
                )
            else:
                insights.append(
                    f"Removing {most_impactful['name']} had minimal impact on overall performance"
                )
        
        # Find ablations with positive impact (removing component improved performance)
        positive_ablations = [c for c in comparisons if c['overall_impact'] > 0.01]
        if positive_ablations:
            insights.append(
                f"Surprisingly, removing {', '.join([c['name'] for c in positive_ablations])} "
                f"improved performance, suggesting potential over-fitting or redundancy"
            )
        
        # Find critical components (removing them significantly hurt performance)
        critical_ablations = [c for c in comparisons if c['overall_impact'] < -0.05]
        if critical_ablations:
            insights.append(
                f"Critical components: {', '.join([c['name'] for c in critical_ablations])} - "
                f"removing these significantly degraded performance"
            )
        
        # Analyze specific metrics
        for comparison in comparisons:
            metric_changes = comparison['metric_changes']
            
            # Check if specific metrics were heavily affected
            for metric_name, change_data in metric_changes.items():
                pct_change = change_data.get('percent_change', 0.0)
                if abs(pct_change) > 20:
                    insights.append(
                        f"{comparison['name']}: {metric_name} changed by {pct_change:.1f}% "
                        f"({change_data['baseline']:.4f} → {change_data['ablation']:.4f})"
                    )
        
        return insights
    
    def _generate_summary(self, comparisons: List[Dict[str, Any]]) -> str:
        """Generate overall summary of ablation studies."""
        if not comparisons:
            return "No ablation comparisons available"
        
        # Count significant impacts
        significant_negative = sum(1 for c in comparisons if c['overall_impact'] < -0.05)
        significant_positive = sum(1 for c in comparisons if c['overall_impact'] > 0.05)
        minimal_impact = len(comparisons) - significant_negative - significant_positive
        
        summary_parts = [
            f"Conducted {len(comparisons)} ablation studies.",
            f"{significant_negative} components are critical (removing hurts performance),",
            f"{minimal_impact} have minimal impact,",
            f"{significant_positive} may be redundant (removing helps)."
        ]
        
        return " ".join(summary_parts)
    
    def export_ablation_configs(self, output_dir: str):
        """
        Export all ablation configurations to JSON files.
        
        Args:
            output_dir: Directory to save configuration files
        """
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        for ablation_name in self.get_all_ablation_names():
            config = self.generate_ablation_config(ablation_name)
            output_path = os.path.join(output_dir, f'config_{ablation_name}.json')
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
