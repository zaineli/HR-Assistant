"""
Faithfulness evaluation for explanations.
Verifies that explanations accurately reflect actual scoring decisions.
"""
from typing import Dict, List, Any, Tuple


class FaithfulnessEvaluator:
    """
    Evaluates faithfulness of explanations to actual scoring decisions.
    Ensures that cited evidence truly contributed to score differences.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize faithfulness evaluator.
        
        Args:
            config: Evaluation configuration dictionary
        """
        self.config = config
        self.weights = config.get('weights', {})
    
    def evaluate_explanation_faithfulness(self,
                                         comparison: Dict[str, Any],
                                         scores_a: Dict[str, Any],
                                         scores_b: Dict[str, Any],
                                         evidence_a: Dict[str, Any],
                                         evidence_b: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate faithfulness of comparison explanation.
        
        Args:
            comparison: Generated comparison explanation
            scores_a: Actual scores for candidate A
            scores_b: Actual scores for candidate B
            evidence_a: Evidence for candidate A
            evidence_b: Evidence for candidate B
            
        Returns:
            Dictionary with faithfulness metrics and issues
        """
        faithfulness_results = {
            'overall_faithful': True,
            'faithfulness_score': 1.0,
            'checks': [],
            'issues': []
        }
        
        # Check 1: Score delta matches reported delta
        score_check = self._verify_score_delta(comparison, scores_a, scores_b)
        faithfulness_results['checks'].append(score_check)
        if not score_check['passed']:
            faithfulness_results['issues'].append(score_check['issue'])
            faithfulness_results['overall_faithful'] = False
            faithfulness_results['faithfulness_score'] -= 0.2
        
        # Check 2: Component deltas are accurate
        component_check = self._verify_component_deltas(comparison, scores_a, scores_b)
        faithfulness_results['checks'].append(component_check)
        if not component_check['passed']:
            faithfulness_results['issues'].append(component_check['issue'])
            faithfulness_results['overall_faithful'] = False
            faithfulness_results['faithfulness_score'] -= 0.2
        
        # Check 3: Top reasons reflect actual weighted impacts
        reasons_check = self._verify_top_reasons(comparison, scores_a, scores_b)
        faithfulness_results['checks'].append(reasons_check)
        if not reasons_check['passed']:
            faithfulness_results['issues'].append(reasons_check['issue'])
            faithfulness_results['overall_faithful'] = False
            faithfulness_results['faithfulness_score'] -= 0.3
        
        # Check 4: Evidence corresponds to cited components
        evidence_check = self._verify_evidence_correspondence(comparison, evidence_a, evidence_b)
        faithfulness_results['checks'].append(evidence_check)
        if not evidence_check['passed']:
            faithfulness_results['issues'].append(evidence_check['issue'])
            faithfulness_results['faithfulness_score'] -= 0.2
        
        # Check 5: Rankings are consistent with scores
        ranking_check = self._verify_ranking_consistency(comparison)
        faithfulness_results['checks'].append(ranking_check)
        if not ranking_check['passed']:
            faithfulness_results['issues'].append(ranking_check['issue'])
            faithfulness_results['overall_faithful'] = False
            faithfulness_results['faithfulness_score'] -= 0.1
        
        # Ensure score doesn't go below 0
        faithfulness_results['faithfulness_score'] = max(0.0, faithfulness_results['faithfulness_score'])
        
        # Add interpretation
        faithfulness_results['interpretation'] = self._interpret_faithfulness(
            faithfulness_results['faithfulness_score']
        )
        
        return faithfulness_results
    
    def _verify_score_delta(self, 
                           comparison: Dict[str, Any],
                           scores_a: Dict[str, Any],
                           scores_b: Dict[str, Any]) -> Dict[str, Any]:
        """Verify that reported score delta matches actual delta."""
        reported_delta = comparison.get('score_delta', 0.0)
        reported_score_a = comparison.get('final_score_a', 0.0)
        reported_score_b = comparison.get('final_score_b', 0.0)
        
        actual_score_a = scores_a.get('final_score', 0.0)
        actual_score_b = scores_b.get('final_score', 0.0)
        actual_delta = actual_score_a - actual_score_b
        
        # Allow small floating point tolerance
        tolerance = 0.0001
        
        scores_match = (abs(reported_score_a - actual_score_a) < tolerance and
                       abs(reported_score_b - actual_score_b) < tolerance)
        delta_matches = abs(reported_delta - actual_delta) < tolerance
        
        passed = scores_match and delta_matches
        
        return {
            'check': 'score_delta_verification',
            'passed': passed,
            'reported_delta': reported_delta,
            'actual_delta': round(actual_delta, 4),
            'error': abs(reported_delta - actual_delta),
            'issue': f'Score delta mismatch: reported {reported_delta:.4f}, actual {actual_delta:.4f}' if not passed else None
        }
    
    def _verify_component_deltas(self,
                                 comparison: Dict[str, Any],
                                 scores_a: Dict[str, Any],
                                 scores_b: Dict[str, Any]) -> Dict[str, Any]:
        """Verify that component deltas are correctly calculated."""
        component_deltas = comparison.get('component_deltas', [])
        issues_found = []
        tolerance = 0.0001
        
        for comp_delta in component_deltas:
            component = comp_delta['component']
            reported_delta = comp_delta['delta']
            reported_weighted = comp_delta['weighted_delta']
            weight = comp_delta['weight']
            
            # Get actual component scores
            actual_score_a = scores_a.get('component_scores', {}).get(component, 0.0)
            actual_score_b = scores_b.get('component_scores', {}).get(component, 0.0)
            actual_delta = actual_score_a - actual_score_b
            actual_weighted = actual_delta * weight
            
            # Check delta
            if abs(reported_delta - actual_delta) > tolerance:
                issues_found.append(
                    f'{component}: delta mismatch (reported {reported_delta:.4f}, actual {actual_delta:.4f})'
                )
            
            # Check weighted delta
            if abs(reported_weighted - actual_weighted) > tolerance:
                issues_found.append(
                    f'{component}: weighted delta mismatch (reported {reported_weighted:.4f}, actual {actual_weighted:.4f})'
                )
        
        passed = len(issues_found) == 0
        
        return {
            'check': 'component_deltas_verification',
            'passed': passed,
            'components_checked': len(component_deltas),
            'mismatches_found': len(issues_found),
            'details': issues_found if issues_found else None,
            'issue': f'Found {len(issues_found)} component delta mismatches' if not passed else None
        }
    
    def _verify_top_reasons(self,
                           comparison: Dict[str, Any],
                           scores_a: Dict[str, Any],
                           scores_b: Dict[str, Any]) -> Dict[str, Any]:
        """Verify that top reasons correspond to largest weighted impacts."""
        top_reasons = comparison.get('top_3_reasons', [])
        component_deltas = comparison.get('component_deltas', [])
        
        if not top_reasons or not component_deltas:
            return {
                'check': 'top_reasons_verification',
                'passed': False,
                'issue': 'Missing top reasons or component deltas'
            }
        
        # Sort component deltas by absolute weighted impact
        sorted_deltas = sorted(component_deltas, 
                              key=lambda x: abs(x['weighted_delta']), 
                              reverse=True)
        
        # Check if top 3 reasons match top 3 weighted impacts
        mismatches = []
        for i, reason in enumerate(top_reasons[:3]):
            reason_component = reason['component']
            expected_component = sorted_deltas[i]['component']
            
            if reason_component != expected_component:
                mismatches.append({
                    'rank': i + 1,
                    'reported': reason_component,
                    'expected': expected_component,
                    'reported_impact': reason['weighted_impact'],
                    'expected_impact': sorted_deltas[i]['weighted_delta']
                })
        
        passed = len(mismatches) == 0
        
        return {
            'check': 'top_reasons_verification',
            'passed': passed,
            'reasons_checked': len(top_reasons),
            'mismatches': mismatches if mismatches else None,
            'issue': f'Top reasons do not match largest weighted impacts: {len(mismatches)} mismatches' if not passed else None
        }
    
    def _verify_evidence_correspondence(self,
                                       comparison: Dict[str, Any],
                                       evidence_a: Dict[str, Any],
                                       evidence_b: Dict[str, Any]) -> Dict[str, Any]:
        """Verify that cited evidence exists in actual evidence."""
        top_reasons = comparison.get('top_3_reasons', [])
        missing_evidence = []
        
        for reason in top_reasons:
            component = reason['component']
            cited_evidence_a = reason.get('evidence_a', [])
            cited_evidence_b = reason.get('evidence_b', [])
            
            # Get actual evidence for component
            evidence_key = f"{component}_evidence"
            actual_evidence_a = evidence_a.get(evidence_key, [])
            actual_evidence_b = evidence_b.get(evidence_key, [])
            
            # Extract actual evidence spans
            actual_spans_a = [item.get('evidence_span', '') for item in actual_evidence_a if not item.get('missing')]
            actual_spans_b = [item.get('evidence_span', '') for item in actual_evidence_b if not item.get('missing')]
            
            # Check if cited evidence exists in actual evidence
            for cited in cited_evidence_a:
                if cited != "No evidence available" and cited not in actual_spans_a:
                    # Check partial match
                    if not any(cited in span or span in cited for span in actual_spans_a):
                        missing_evidence.append({
                            'candidate': 'A',
                            'component': component,
                            'cited': cited,
                            'reason': 'Not found in actual evidence'
                        })
            
            for cited in cited_evidence_b:
                if cited != "No evidence available" and cited not in actual_spans_b:
                    if not any(cited in span or span in cited for span in actual_spans_b):
                        missing_evidence.append({
                            'candidate': 'B',
                            'component': component,
                            'cited': cited,
                            'reason': 'Not found in actual evidence'
                        })
        
        # We allow some flexibility here - not a hard failure
        passed = len(missing_evidence) == 0
        
        return {
            'check': 'evidence_correspondence_verification',
            'passed': passed,
            'total_evidence_checked': sum(len(r.get('evidence_a', [])) + len(r.get('evidence_b', [])) for r in top_reasons),
            'missing_count': len(missing_evidence),
            'missing_details': missing_evidence[:5] if missing_evidence else None,  # Show first 5
            'issue': f'{len(missing_evidence)} cited evidence items not found in actual evidence' if not passed else None
        }
    
    def _verify_ranking_consistency(self, comparison: Dict[str, Any]) -> Dict[str, Any]:
        """Verify that ranking is consistent with scores."""
        score_a = comparison.get('final_score_a', 0.0)
        score_b = comparison.get('final_score_b', 0.0)
        score_delta = comparison.get('score_delta', 0.0)
        
        # Check if A is ranked higher (positive delta) when it has higher score
        if score_delta > 0 and score_a > score_b:
            passed = True
        elif score_delta < 0 and score_b > score_a:
            # This shouldn't happen if A is supposed to be higher
            passed = False
        elif abs(score_delta) < 0.0001:  # Essentially tied
            passed = True
        else:
            passed = False
        
        return {
            'check': 'ranking_consistency_verification',
            'passed': passed,
            'score_a': score_a,
            'score_b': score_b,
            'delta': score_delta,
            'consistent': score_delta > 0 and score_a > score_b,
            'issue': 'Ranking inconsistent with scores' if not passed else None
        }
    
    def _interpret_faithfulness(self, score: float) -> str:
        """Interpret faithfulness score."""
        if score >= 0.95:
            return "Highly faithful - explanations accurately reflect scoring"
        elif score >= 0.85:
            return "Faithful - minor discrepancies only"
        elif score >= 0.70:
            return "Moderately faithful - some issues detected"
        elif score >= 0.50:
            return "Somewhat faithful - multiple issues detected"
        else:
            return "Unfaithful - significant discrepancies in explanations"
    
    def evaluate_global_faithfulness(self, 
                                    all_comparisons: List[Dict[str, Any]],
                                    all_scores: Dict[str, Dict[str, Any]],
                                    all_evidence: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluate faithfulness across all comparisons.
        
        Args:
            all_comparisons: List of all comparison explanations
            all_scores: Dictionary mapping resume ID to scores
            all_evidence: Dictionary mapping resume ID to evidence
            
        Returns:
            Dictionary with global faithfulness metrics
        """
        individual_faithfulness = []
        total_checks = 0
        passed_checks = 0
        all_issues = []
        
        for comparison in all_comparisons:
            candidate_a = comparison.get('candidate_a')
            candidate_b = comparison.get('candidate_b')
            
            # Get corresponding data
            # Note: We'd need to map candidate names to IDs
            # For now, assume comparison has the IDs
            scores_a = all_scores.get(candidate_a, {})
            scores_b = all_scores.get(candidate_b, {})
            evidence_a = all_evidence.get(candidate_a, {})
            evidence_b = all_evidence.get(candidate_b, {})
            
            if not scores_a or not scores_b:
                continue
            
            # Evaluate this comparison
            faithfulness = self.evaluate_explanation_faithfulness(
                comparison, scores_a, scores_b, evidence_a, evidence_b
            )
            
            individual_faithfulness.append({
                'comparison': f"{candidate_a} vs {candidate_b}",
                'score': faithfulness['faithfulness_score'],
                'passed': faithfulness['overall_faithful'],
                'issues': faithfulness['issues']
            })
            
            # Aggregate checks
            for check in faithfulness['checks']:
                total_checks += 1
                if check['passed']:
                    passed_checks += 1
            
            # Aggregate issues
            all_issues.extend(faithfulness['issues'])
        
        # Calculate global metrics
        avg_faithfulness = sum(f['score'] for f in individual_faithfulness) / len(individual_faithfulness) if individual_faithfulness else 0.0
        pass_rate = passed_checks / total_checks if total_checks > 0 else 0.0
        
        return {
            'global_faithfulness_score': round(avg_faithfulness, 4),
            'check_pass_rate': round(pass_rate, 4),
            'total_comparisons': len(individual_faithfulness),
            'total_checks': total_checks,
            'passed_checks': passed_checks,
            'failed_checks': total_checks - passed_checks,
            'total_issues': len(all_issues),
            'individual_scores': individual_faithfulness,
            'sample_issues': all_issues[:10],  # Show first 10 issues
            'interpretation': self._interpret_faithfulness(avg_faithfulness)
        }
