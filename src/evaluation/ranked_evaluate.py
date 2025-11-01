"""
Enhanced weighted evaluation with ranking, comparison, and evidence-backed explanations.
"""
import json
import os
from typing import Dict, List, Any, Tuple
from .weighted_evaluate import WeightedResumeEvaluator


class RankedResumeEvaluator(WeightedResumeEvaluator):
    """
    Extended evaluator that ranks candidates and provides detailed comparisons
    with evidence-backed explanations.
    """
    
    def __init__(self, generated_path: str, ground_truth_path: str, config_path: str = "evaluation_config.json"):
        super().__init__(generated_path, ground_truth_path, config_path)
        self.evidence = {}  # Store evidence for explanations
    
    def _extract_evidence(self, resume: Dict, resume_key: str) -> Dict[str, Any]:
        """
        Extract key evidence from resume for explanations.
        
        Returns:
            Dict with evidence spans and highlights
        """
        evidence = {
            'education_highlights': [],
            'experience_highlights': [],
            'publications_highlights': [],
            'awards_highlights': [],
            'name': resume.get('name', 'Unknown')
        }
        
        # Education evidence
        for edu in resume.get('education', []):
            highlight = {
                'degree': edu.get('degree', ''),
                'field': edu.get('field', ''),
                'university': edu.get('university', ''),
                'gpa': edu.get('gpa'),
                'country': edu.get('country', ''),
                'span': f"{edu.get('degree', '')} in {edu.get('field', '')} from {edu.get('university', '')}"
            }
            if edu.get('gpa'):
                highlight['span'] += f" (GPA: {edu.get('gpa')})"
            evidence['education_highlights'].append(highlight)
        
        # Experience evidence
        for exp in resume.get('experience', []):
            months = exp.get('duration_months', 0)
            highlight = {
                'title': exp.get('title', ''),
                'org': exp.get('org', ''),
                'domain': exp.get('domain', ''),
                'duration_months': months,
                'span': f"{exp.get('title', '')} at {exp.get('org', '')} ({months} months)"
            }
            if exp.get('domain'):
                highlight['span'] += f" - {exp.get('domain')}"
            evidence['experience_highlights'].append(highlight)
        
        # Publications evidence
        for pub in resume.get('publications', []):
            highlight = {
                'title': pub.get('title', ''),
                'venue': pub.get('venue', ''),
                'journal_if': pub.get('journal_if'),
                'author_position': pub.get('author_position'),
                'span': f"\"{pub.get('title', '')}\" in {pub.get('venue', '')}"
            }
            if pub.get('journal_if'):
                highlight['span'] += f" (IF: {pub.get('journal_if')})"
            if pub.get('author_position'):
                pos_str = 'First' if pub.get('author_position') in [1, '1'] else f"{pub.get('author_position')}"
                highlight['span'] += f" [{pos_str} author]"
            evidence['publications_highlights'].append(highlight)
        
        # Awards evidence
        for award in resume.get('awards', []):
            highlight = {
                'title': award.get('title', ''),
                'issuer': award.get('issuer', ''),
                'year': award.get('year'),
                'span': award.get('title', '')
            }
            if award.get('issuer'):
                highlight['span'] += f" from {award.get('issuer')}"
            if award.get('year'):
                highlight['span'] += f" ({award.get('year')})"
            evidence['awards_highlights'].append(highlight)
        
        self.evidence[resume_key] = evidence
        return evidence
    
    def rank_resumes(self, results: Dict[str, Any]) -> List[Tuple[str, float, str]]:
        """
        Rank resumes by final score in descending order.
        
        Returns:
            List of tuples: (resume_key, score, grade)
        """
        rankings = []
        for resume_key, resume_result in results['per_resume'].items():
            rankings.append((
                resume_key,
                resume_result['final_score'],
                resume_result['grade']
            ))
        
        # Sort by score descending
        rankings.sort(key=lambda x: x[1], reverse=True)
        return rankings
    
    def compare_resumes(self, resume_a_key: str, resume_b_key: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare two resumes and generate delta table with explanations.
        
        Args:
            resume_a_key: Key for first resume (higher ranked)
            resume_b_key: Key for second resume (lower ranked)
            results: Full evaluation results
            
        Returns:
            Dict with comparison details and top-3 reasons
        """
        resume_a = results['per_resume'].get(resume_a_key)
        resume_b = results['per_resume'].get(resume_b_key)
        
        if not resume_a or not resume_b:
            return {'error': 'One or both resumes not found'}
        
        # Get evidence
        evidence_a = self.evidence.get(resume_a_key, {})
        evidence_b = self.evidence.get(resume_b_key, {})
        
        # Calculate deltas for each component
        deltas = {
            'final_score': {
                'resume_a': resume_a['final_score'],
                'resume_b': resume_b['final_score'],
                'delta': resume_a['final_score'] - resume_b['final_score'],
                'delta_pct': (resume_a['final_score'] - resume_b['final_score']) * 100
            },
            'education': {
                'resume_a': resume_a['component_scores']['education'],
                'resume_b': resume_b['component_scores']['education'],
                'delta': resume_a['component_scores']['education'] - resume_b['component_scores']['education'],
                'weighted_impact': (resume_a['component_scores']['education'] - resume_b['component_scores']['education']) * self.weights.get('education', 0.30)
            },
            'experience': {
                'resume_a': resume_a['component_scores']['experience'],
                'resume_b': resume_b['component_scores']['experience'],
                'delta': resume_a['component_scores']['experience'] - resume_b['component_scores']['experience'],
                'weighted_impact': (resume_a['component_scores']['experience'] - resume_b['component_scores']['experience']) * self.weights.get('experience', 0.30)
            },
            'publications': {
                'resume_a': resume_a['component_scores']['publications'],
                'resume_b': resume_b['component_scores']['publications'],
                'delta': resume_a['component_scores']['publications'] - resume_b['component_scores']['publications'],
                'weighted_impact': (resume_a['component_scores']['publications'] - resume_b['component_scores']['publications']) * self.weights.get('publications', 0.25)
            },
            'coherence': {
                'resume_a': resume_a['component_scores']['coherence'],
                'resume_b': resume_b['component_scores']['coherence'],
                'delta': resume_a['component_scores']['coherence'] - resume_b['component_scores']['coherence'],
                'weighted_impact': (resume_a['component_scores']['coherence'] - resume_b['component_scores']['coherence']) * self.weights.get('coherence', 0.10)
            },
            'awards': {
                'resume_a': resume_a['component_scores']['awards'],
                'resume_b': resume_b['component_scores']['awards'],
                'delta': resume_a['component_scores']['awards'] - resume_b['component_scores']['awards'],
                'weighted_impact': (resume_a['component_scores']['awards'] - resume_b['component_scores']['awards']) * self.weights.get('awards_other', 0.05)
            }
        }
        
        # Generate top-3 reasons with evidence
        reasons = self._generate_top_reasons(resume_a, resume_b, evidence_a, evidence_b, deltas)
        
        return {
            'resume_a': {
                'key': resume_a_key,
                'name': evidence_a.get('name', 'Unknown'),
                'score': resume_a['final_score'],
                'grade': resume_a['grade']
            },
            'resume_b': {
                'key': resume_b_key,
                'name': evidence_b.get('name', 'Unknown'),
                'score': resume_b['final_score'],
                'grade': resume_b['grade']
            },
            'deltas': deltas,
            'top_reasons': reasons
        }
    
    def _generate_top_reasons(self, resume_a: Dict, resume_b: Dict, 
                             evidence_a: Dict, evidence_b: Dict,
                             deltas: Dict) -> List[Dict[str, Any]]:
        """
        Generate top-3 evidence-backed reasons why Resume A > Resume B.
        
        Returns:
            List of reason dicts with evidence spans
        """
        reasons = []
        
        # Collect all component impacts
        impacts = []
        
        # Education
        if deltas['education']['weighted_impact'] != 0:
            impacts.append({
                'component': 'education',
                'impact': abs(deltas['education']['weighted_impact']),
                'delta': deltas['education']['delta'],
                'weighted_impact': deltas['education']['weighted_impact']
            })
        
        # Experience
        if deltas['experience']['weighted_impact'] != 0:
            impacts.append({
                'component': 'experience',
                'impact': abs(deltas['experience']['weighted_impact']),
                'delta': deltas['experience']['delta'],
                'weighted_impact': deltas['experience']['weighted_impact']
            })
        
        # Publications
        if deltas['publications']['weighted_impact'] != 0:
            impacts.append({
                'component': 'publications',
                'impact': abs(deltas['publications']['weighted_impact']),
                'delta': deltas['publications']['delta'],
                'weighted_impact': deltas['publications']['weighted_impact']
            })
        
        # Coherence
        if deltas['coherence']['weighted_impact'] != 0:
            impacts.append({
                'component': 'coherence',
                'impact': abs(deltas['coherence']['weighted_impact']),
                'delta': deltas['coherence']['delta'],
                'weighted_impact': deltas['coherence']['weighted_impact']
            })
        
        # Awards
        if deltas['awards']['weighted_impact'] != 0:
            impacts.append({
                'component': 'awards',
                'impact': abs(deltas['awards']['weighted_impact']),
                'delta': deltas['awards']['delta'],
                'weighted_impact': deltas['awards']['weighted_impact']
            })
        
        # Sort by impact (absolute value)
        impacts.sort(key=lambda x: x['impact'], reverse=True)
        
        # Generate top-3 reasons with evidence
        for i, impact in enumerate(impacts[:3], 1):
            component = impact['component']
            reason = self._generate_reason_text(
                component,
                resume_a[component],
                resume_b[component],
                evidence_a,
                evidence_b,
                impact['weighted_impact']
            )
            reasons.append(reason)
        
        return reasons
    
    def _generate_reason_text(self, component: str, data_a: Dict, data_b: Dict,
                             evidence_a: Dict, evidence_b: Dict,
                             weighted_impact: float) -> Dict[str, Any]:
        """Generate detailed reason text with evidence for a component."""
        
        if component == 'education':
            return self._reason_education(data_a, data_b, evidence_a, evidence_b, weighted_impact)
        elif component == 'experience':
            return self._reason_experience(data_a, data_b, evidence_a, evidence_b, weighted_impact)
        elif component == 'publications':
            return self._reason_publications(data_a, data_b, evidence_a, evidence_b, weighted_impact)
        elif component == 'coherence':
            return self._reason_coherence(data_a, data_b, evidence_a, evidence_b, weighted_impact)
        elif component == 'awards':
            return self._reason_awards(data_a, data_b, evidence_a, evidence_b, weighted_impact)
        
        return {'reason': 'Unknown component', 'evidence': [], 'impact': weighted_impact}
    
    def _reason_education(self, data_a: Dict, data_b: Dict, 
                         evidence_a: Dict, evidence_b: Dict,
                         weighted_impact: float) -> Dict[str, Any]:
        """Generate education comparison reason."""
        score_a = data_a['weighted_score']
        score_b = data_b['weighted_score']
        
        highlights = []
        
        # GPA comparison
        if data_a['gpa_score'] > data_b['gpa_score']:
            highlights.append(f"Higher GPA score ({data_a['gpa_score']:.1%} vs {data_b['gpa_score']:.1%})")
        
        # Degree level
        if data_a['degree_level_score'] > data_b['degree_level_score']:
            highlights.append(f"More advanced degree level ({data_a['degree_level_score']:.1%} vs {data_b['degree_level_score']:.1%})")
        
        # University tier
        if data_a['university_tier_score'] > data_b['university_tier_score']:
            highlights.append(f"Higher-tier university ({data_a['university_tier_score']:.1%} vs {data_b['university_tier_score']:.1%})")
        
        # Get education spans
        edu_spans_a = [edu['span'] for edu in evidence_a.get('education_highlights', [])]
        edu_spans_b = [edu['span'] for edu in evidence_b.get('education_highlights', [])]
        
        reason_text = f"Superior education credentials ({score_a:.1%} vs {score_b:.1%})"
        if highlights:
            reason_text += f": {'; '.join(highlights)}"
        
        return {
            'component': 'Education',
            'reason': reason_text,
            'resume_a_score': score_a,
            'resume_b_score': score_b,
            'weighted_impact': weighted_impact,
            'evidence_a': edu_spans_a,
            'evidence_b': edu_spans_b,
            'highlights': highlights
        }
    
    def _reason_experience(self, data_a: Dict, data_b: Dict,
                          evidence_a: Dict, evidence_b: Dict,
                          weighted_impact: float) -> Dict[str, Any]:
        """Generate experience comparison reason."""
        score_a = data_a['weighted_score']
        score_b = data_b['weighted_score']
        
        highlights = []
        
        # Total months
        months_a = data_a['total_months']
        months_b = data_b['total_months']
        if months_a > months_b:
            highlights.append(f"More experience ({months_a} months vs {months_b} months)")
        
        # Domain relevance
        if data_a['domain_match_score'] > data_b['domain_match_score']:
            highlights.append(f"Higher domain relevance ({data_a['domain_match_score']:.1%} vs {data_b['domain_match_score']:.1%})")
        
        # Experience bonus
        if data_a['experience_bonus'] > data_b['experience_bonus']:
            highlights.append(f"Qualifies for experience bonus ({data_a['experience_bonus']:.1%})")
        
        # Get experience spans
        exp_spans_a = [exp['span'] for exp in evidence_a.get('experience_highlights', [])]
        exp_spans_b = [exp['span'] for exp in evidence_b.get('experience_highlights', [])]
        
        reason_text = f"Stronger work experience ({score_a:.1%} vs {score_b:.1%})"
        if highlights:
            reason_text += f": {'; '.join(highlights)}"
        
        return {
            'component': 'Experience',
            'reason': reason_text,
            'resume_a_score': score_a,
            'resume_b_score': score_b,
            'weighted_impact': weighted_impact,
            'evidence_a': exp_spans_a,
            'evidence_b': exp_spans_b,
            'highlights': highlights
        }
    
    def _reason_publications(self, data_a: Dict, data_b: Dict,
                            evidence_a: Dict, evidence_b: Dict,
                            weighted_impact: float) -> Dict[str, Any]:
        """Generate publications comparison reason."""
        score_a = data_a['weighted_score']
        score_b = data_b['weighted_score']
        
        highlights = []
        
        # Count
        count_a = data_a['count']
        count_b = data_b['count']
        if count_a > count_b:
            highlights.append(f"More publications ({count_a} vs {count_b})")
        
        # Impact factor
        if data_a['if_score'] > data_b['if_score']:
            highlights.append(f"Higher impact factor ({data_a['if_score']:.1%} vs {data_b['if_score']:.1%})")
        
        # Author position
        if data_a['author_position_score'] > data_b['author_position_score']:
            highlights.append(f"Better author positions ({data_a['author_position_score']:.1%} vs {data_b['author_position_score']:.1%})")
        
        # First author bonus
        if data_a['first_author_bonus'] > data_b['first_author_bonus']:
            highlights.append("Has first-author publications")
        
        # Get publication spans
        pub_spans_a = [pub['span'] for pub in evidence_a.get('publications_highlights', [])]
        pub_spans_b = [pub['span'] for pub in evidence_b.get('publications_highlights', [])]
        
        reason_text = f"Better publication record ({score_a:.1%} vs {score_b:.1%})"
        if highlights:
            reason_text += f": {'; '.join(highlights)}"
        
        return {
            'component': 'Publications',
            'reason': reason_text,
            'resume_a_score': score_a,
            'resume_b_score': score_b,
            'weighted_impact': weighted_impact,
            'evidence_a': pub_spans_a,
            'evidence_b': pub_spans_b,
            'highlights': highlights
        }
    
    def _reason_coherence(self, data_a: Dict, data_b: Dict,
                         evidence_a: Dict, evidence_b: Dict,
                         weighted_impact: float) -> Dict[str, Any]:
        """Generate coherence comparison reason."""
        score_a = data_a['weighted_score']
        score_b = data_b['weighted_score']
        
        highlights = []
        
        if data_a['section_coherence'] > data_b['section_coherence']:
            highlights.append(f"Better section completeness ({data_a['section_coherence']:.1%} vs {data_b['section_coherence']:.1%})")
        
        if data_a['name_accuracy'] > data_b['name_accuracy']:
            highlights.append(f"More accurate name extraction ({data_a['name_accuracy']:.1%} vs {data_b['name_accuracy']:.1%})")
        
        reason_text = f"Higher extraction accuracy ({score_a:.1%} vs {score_b:.1%})"
        if highlights:
            reason_text += f": {'; '.join(highlights)}"
        
        return {
            'component': 'Coherence',
            'reason': reason_text,
            'resume_a_score': score_a,
            'resume_b_score': score_b,
            'weighted_impact': weighted_impact,
            'evidence_a': [f"Name: {evidence_a.get('name', 'Unknown')}"],
            'evidence_b': [f"Name: {evidence_b.get('name', 'Unknown')}"],
            'highlights': highlights
        }
    
    def _reason_awards(self, data_a: Dict, data_b: Dict,
                      evidence_a: Dict, evidence_b: Dict,
                      weighted_impact: float) -> Dict[str, Any]:
        """Generate awards comparison reason."""
        score_a = data_a['weighted_score']
        score_b = data_b['weighted_score']
        count_a = data_a['count']
        count_b = data_b['count']
        
        highlights = [f"More awards/certifications ({count_a} vs {count_b})"]
        
        # Get award spans
        award_spans_a = [awd['span'] for awd in evidence_a.get('awards_highlights', [])]
        award_spans_b = [awd['span'] for awd in evidence_b.get('awards_highlights', [])]
        
        reason_text = f"More awards and certifications ({score_a:.1%} vs {score_b:.1%})"
        
        return {
            'component': 'Awards',
            'reason': reason_text,
            'resume_a_score': score_a,
            'resume_b_score': score_b,
            'weighted_impact': weighted_impact,
            'evidence_a': award_spans_a,
            'evidence_b': award_spans_b,
            'highlights': highlights
        }
    
    def evaluate_all_with_ranking(self) -> Dict[str, Any]:
        """
        Evaluate all resumes, rank them, and generate comparisons.
        
        Returns:
            Dict with evaluations, rankings, and pairwise comparisons
        """
        # First, extract evidence for all resumes
        for key in self.generated_map.keys():
            resume = self.generated_map[key]
            self._extract_evidence(resume, key)
        
        # Run standard evaluation
        results = self.evaluate_all()
        
        # Rank resumes
        rankings = self.rank_resumes(results)
        results['rankings'] = rankings
        
        # Generate pairwise comparisons for top candidates
        comparisons = []
        for i in range(min(3, len(rankings))):  # Top 3 candidates
            for j in range(i + 1, min(5, len(rankings))):  # Compare with next few
                resume_a_key = rankings[i][0]
                resume_b_key = rankings[j][0]
                comparison = self.compare_resumes(resume_a_key, resume_b_key, results)
                comparisons.append(comparison)
        
        results['comparisons'] = comparisons
        
        return results
    
    def print_ranking_report(self, results: Dict[str, Any]):
        """Print ranking and comparison report."""
        print("\n" + "=" * 80)
        print("CANDIDATE RANKINGS")
        print("=" * 80)
        print()
        
        rankings = results.get('rankings', [])
        print(f"{'Rank':<6} {'Score':<8} {'Grade':<7} {'Candidate'}")
        print("-" * 80)
        for rank, (key, score, grade) in enumerate(rankings, 1):
            name = self.evidence.get(key, {}).get('name', key)
            print(f"{rank:<6} {score:>6.1%} {grade:<7} {name}")
        
        print("\n" + "=" * 80)
        print("PAIRWISE COMPARISONS - WHY A > B")
        print("=" * 80)
        
        comparisons = results.get('comparisons', [])
        for i, comp in enumerate(comparisons, 1):
            print(f"\n{'=' * 80}")
            print(f"Comparison #{i}: {comp['resume_a']['name']} vs {comp['resume_b']['name']}")
            print(f"{'=' * 80}")
            print(f"{comp['resume_a']['name']}: {comp['resume_a']['score']:.1%} (Grade {comp['resume_a']['grade']})")
            print(f"{comp['resume_b']['name']}: {comp['resume_b']['score']:.1%} (Grade {comp['resume_b']['grade']})")
            print(f"Score Difference: +{comp['deltas']['final_score']['delta_pct']:.1f} percentage points")
            print()
            
            # Delta table
            print("Component Breakdown:")
            print(f"{'Component':<15} {'A Score':<10} {'B Score':<10} {'Delta':<10} {'Impact'}")
            print("-" * 80)
            for component in ['education', 'experience', 'publications', 'coherence', 'awards']:
                delta = comp['deltas'][component]
                print(f"{component.title():<15} {delta['resume_a']:>8.1%} {delta['resume_b']:>8.1%} "
                      f"{delta['delta']:>+8.1%} {delta['weighted_impact']:>+8.1%}")
            print()
            
            # Top reasons
            print("Top 3 Reasons Why A > B:")
            print("-" * 80)
            for j, reason in enumerate(comp['top_reasons'], 1):
                print(f"\n{j}. {reason['component'].upper()}")
                print(f"   {reason['reason']}")
                print(f"   Weighted Impact: {reason['weighted_impact']:+.1%}")
                
                if reason.get('evidence_a'):
                    print(f"   Evidence (A):")
                    for evidence in reason['evidence_a'][:3]:  # Show top 3
                        print(f"     • {evidence}")
                
                if reason.get('evidence_b'):
                    print(f"   Evidence (B):")
                    for evidence in reason['evidence_b'][:3]:  # Show top 3
                        print(f"     • {evidence}")


def main():
    """Main function for ranked evaluation."""
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python ranked_evaluate.py <generated_json> <ground_truth_json> [config_json]")
        print("\nExample:")
        print("  python ranked_evaluate.py results/parsed.json ground_truth/truth.json")
        sys.exit(1)
    
    generated_path = sys.argv[1]
    ground_truth_path = sys.argv[2]
    config_path = sys.argv[3] if len(sys.argv) > 3 else "evaluation_config.json"
    
    # Run ranked evaluation
    evaluator = RankedResumeEvaluator(generated_path, ground_truth_path, config_path)
    results = evaluator.evaluate_all_with_ranking()
    
    # Print standard weighted report
    evaluator.print_report(results)
    
    # Print ranking and comparison report
    evaluator.print_ranking_report(results)
    
    # Save results
    output_path = "ranked_evaluation_results.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'=' * 80}")
    print(f"Detailed results saved to: {output_path}")
    print("=" * 80)


if __name__ == '__main__':
    main()
