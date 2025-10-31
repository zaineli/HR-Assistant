"""
Weighted evaluation system for resume parsing with configurable weights and policies.
Calculates scores based on education, experience, publications, coherence, and awards.
"""
import json
import os
from typing import Dict, List, Any, Tuple
from collections import defaultdict
import re
from datetime import datetime
from dateutil import parser as date_parser


class WeightedResumeEvaluator:
    """
    Evaluator that calculates weighted scores based on extraction accuracy
    and quality metrics defined in configuration.
    """
    
    def __init__(self, generated_path: str, ground_truth_path: str, config_path: str = "evaluation_config.json"):
        """
        Initialize weighted evaluator.
        
        Args:
            generated_path: Path to generated JSON file
            ground_truth_path: Path to ground truth JSON file
            config_path: Path to configuration JSON with weights and policies
        """
        self.generated = self._load_json(generated_path)
        self.ground_truth = self._load_json(ground_truth_path)
        self.config = self._load_json(config_path)
        
        # Extract configuration
        self.weights = self.config.get('weights', {})
        self.subweights = self.config.get('subweights', {})
        self.policies = self.config.get('policies', {})
        
        # Map resumes
        self.generated_map = self._create_resume_map(self.generated)
        self.ground_truth_map = self._create_resume_map(self.ground_truth)
        
        # University tiers (can be extended)
        self.university_tiers = {
            'tier1': ['MIT', 'Stanford', 'Harvard', 'Cambridge', 'Oxford', 'Caltech', 'Princeton'],
            'tier2': ['National University of Sciences and Technology', 'NUST', 'IIT', 'Carnegie Mellon', 
                     'UC Berkeley', 'Cornell', 'Yale', 'Columbia', 'ETH Zurich'],
            'tier3': []  # Default tier
        }
        
        # Degree levels
        self.degree_levels = {
            'PhD': 1.0,
            'Ph.D': 1.0,
            'Doctorate': 1.0,
            'Master': 0.8,
            'MS': 0.8,
            'M.S.': 0.8,
            'MBA': 0.8,
            'Bachelor': 0.6,
            'BS': 0.6,
            'B.S.': 0.6,
            'BA': 0.6,
            'BE': 0.6
        }
    
    def _load_json(self, path: str) -> Any:
        """Load JSON file."""
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _create_resume_map(self, resumes: List[Dict]) -> Dict[str, Dict]:
        """Create a mapping of resume identifiers to resume data."""
        resume_map = {}
        for resume in resumes:
            key = resume.get('filename', resume.get('name', ''))
            if key:
                resume_map[key] = resume
        return resume_map
    
    def _normalize_string(self, text: Any) -> str:
        """Normalize string for comparison."""
        if text is None:
            return ""
        text = str(text).lower().strip()
        text = re.sub(r'\s+', ' ', text)
        return text
    
    def _calculate_string_similarity(self, gen: Any, truth: Any) -> float:
        """Calculate similarity between two strings (0-1)."""
        gen_str = self._normalize_string(gen)
        truth_str = self._normalize_string(truth)
        
        if not truth_str:
            return 1.0 if not gen_str else 0.0
        
        if gen_str == truth_str:
            return 1.0
        
        # Partial match
        if gen_str in truth_str or truth_str in gen_str:
            return 0.9
        
        # Word overlap
        gen_words = set(gen_str.split())
        truth_words = set(truth_str.split())
        if truth_words:
            overlap = len(gen_words & truth_words) / len(truth_words)
            return overlap * 0.8
        
        return 0.0
    
    def _get_university_tier_score(self, university: str) -> float:
        """Get university tier score (0-1)."""
        if not university:
            return 0.3
        
        uni_normalized = self._normalize_string(university)
        
        # Check tier 1
        for tier1_uni in self.university_tiers['tier1']:
            if self._normalize_string(tier1_uni) in uni_normalized:
                return 1.0
        
        # Check tier 2
        for tier2_uni in self.university_tiers['tier2']:
            if self._normalize_string(tier2_uni) in uni_normalized:
                return 0.7
        
        # Default tier 3
        return 0.4
    
    def _get_degree_level_score(self, degree: str) -> float:
        """Get degree level score based on degree type."""
        if not degree:
            return 0.0
        
        degree_normalized = self._normalize_string(degree)
        
        for degree_type, score in self.degree_levels.items():
            if self._normalize_string(degree_type) in degree_normalized:
                return score
        
        return 0.3  # Unknown degree type
    
    def _calculate_gpa_score(self, gpa: Any, scale: Any = None) -> float:
        """Calculate GPA score normalized to 0-1."""
        if gpa is None:
            return 0.0
        
        try:
            gpa_val = float(gpa)
            scale_val = float(scale) if scale else 4.0
            
            # Normalize to 0-1 scale
            normalized = gpa_val / scale_val
            return min(1.0, max(0.0, normalized))
        except (ValueError, TypeError, ZeroDivisionError):
            return 0.0
    
    def _evaluate_education_quality(self, education_list: List[Dict]) -> Dict[str, float]:
        """
        Evaluate education quality based on subweights.
        
        Returns:
            Dict with component scores and weighted total
        """
        if not education_list:
            return {
                'gpa_score': 0.0,
                'degree_level_score': 0.0,
                'university_tier_score': 0.0,
                'weighted_score': 0.0
            }
        
        # Take the highest scoring education (typically the most advanced degree)
        best_scores = {
            'gpa': 0.0,
            'degree_level': 0.0,
            'university_tier': 0.0
        }
        
        for edu in education_list:
            gpa_score = self._calculate_gpa_score(edu.get('gpa'), edu.get('scale'))
            degree_score = self._get_degree_level_score(edu.get('degree'))
            uni_score = self._get_university_tier_score(edu.get('university'))
            
            best_scores['gpa'] = max(best_scores['gpa'], gpa_score)
            best_scores['degree_level'] = max(best_scores['degree_level'], degree_score)
            best_scores['university_tier'] = max(best_scores['university_tier'], uni_score)
        
        # Calculate weighted score
        edu_subweights = self.subweights.get('education', {})
        weighted_score = (
            best_scores['gpa'] * edu_subweights.get('gpa', 0.5) +
            best_scores['degree_level'] * edu_subweights.get('degree_level', 0.2) +
            best_scores['university_tier'] * edu_subweights.get('university_tier', 0.3)
        )
        
        return {
            'gpa_score': best_scores['gpa'],
            'degree_level_score': best_scores['degree_level'],
            'university_tier_score': best_scores['university_tier'],
            'weighted_score': weighted_score
        }
    
    def _calculate_duration_months(self, start: Any, end: Any) -> int:
        """Calculate duration in months from start and end dates."""
        if not start:
            return 0
        
        try:
            # Handle "currently working"
            if end and isinstance(end, str) and "current" in end.lower():
                end_date = datetime.now()
            elif end:
                # Try to parse end date
                if isinstance(end, (int, float)):
                    end_date = datetime(int(end), 12, 31)
                else:
                    end_date = date_parser.parse(str(end), fuzzy=True)
            else:
                end_date = datetime.now()
            
            # Parse start date
            if isinstance(start, (int, float)):
                start_date = datetime(int(start), 1, 1)
            else:
                start_date = date_parser.parse(str(start), fuzzy=True)
            
            # Calculate months
            months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
            return max(0, months)
        except Exception:
            # Fallback: estimate years if we have numeric values
            try:
                start_year = int(str(start)[:4]) if start else 0
                if end and isinstance(end, str) and "current" in end.lower():
                    end_year = datetime.now().year
                else:
                    end_year = int(str(end)[:4]) if end else datetime.now().year
                
                years = max(0, end_year - start_year)
                return years * 12
            except Exception:
                return 0
    
    def _evaluate_experience_quality(self, experience_list: List[Dict]) -> Dict[str, float]:
        """
        Evaluate experience quality.
        
        Returns:
            Dict with experience metrics
        """
        if not experience_list:
            return {
                'total_months': 0,
                'relevant_months': 0,
                'domain_match_score': 0.0,
                'experience_bonus': 0.0,
                'weighted_score': 0.0
            }
        
        total_months = 0
        relevant_months = 0
        domain_match_scores = []
        target_domain = self.policies.get('domain', '').lower()
        
        for exp in experience_list:
            # Try to get duration_months, or calculate from start/end
            months = exp.get('duration_months')
            if not months:
                months = self._calculate_duration_months(exp.get('start'), exp.get('end'))
            
            if months:
                total_months += months
                
                # Check domain relevance
                exp_domain = self._normalize_string(exp.get('domain', ''))
                if target_domain and (target_domain in exp_domain or exp_domain in target_domain):
                    relevant_months += months
                    domain_match_scores.append(1.0)
                else:
                    # Partial credit for any domain specified
                    domain_match_scores.append(0.3 if exp_domain else 0.0)
        
        # Calculate domain match score
        avg_domain_score = sum(domain_match_scores) / len(domain_match_scores) if domain_match_scores else 0.0
        
        # Experience bonus for long tenure
        min_months = self.policies.get('min_months_experience_for_bonus', 24)
        experience_bonus = 0.15 if total_months >= min_months else 0.0
        
        # Weighted score (months normalized + domain relevance + bonus)
        months_score = min(1.0, total_months / 60)  # Normalize to 5 years max
        weighted_score = (months_score * 0.5 + avg_domain_score * 0.5) * (1 + experience_bonus)
        weighted_score = min(1.0, weighted_score)
        
        return {
            'total_months': total_months,
            'relevant_months': relevant_months,
            'domain_match_score': avg_domain_score,
            'experience_bonus': experience_bonus,
            'weighted_score': weighted_score
        }
    
    def _evaluate_publications_quality(self, publications_list: List[Dict]) -> Dict[str, float]:
        """
        Evaluate publications quality based on impact factor, author position, venue.
        
        Returns:
            Dict with publication metrics
        """
        if not publications_list:
            return {
                'count': 0,
                'if_score': 0.0,
                'author_position_score': 0.0,
                'venue_quality_score': 0.0,
                'first_author_bonus': 0.0,
                'weighted_score': 0.0
            }
        
        if_scores = []
        author_position_scores = []
        venue_scores = []
        has_first_author = False
        
        pub_subweights = self.subweights.get('publications', {})
        
        for pub in publications_list:
            # Impact factor score (normalize to 0-1, assuming max IF of 50)
            journal_if = pub.get('journal_if')
            if journal_if:
                try:
                    if_score = min(1.0, float(journal_if) / 50.0)
                    if_scores.append(if_score)
                except (ValueError, TypeError):
                    if_scores.append(0.0)
            else:
                if_scores.append(0.0)
            
            # Author position score
            author_pos = pub.get('author_position')
            if author_pos == 1 or author_pos == '1' or str(author_pos).lower() == 'first':
                author_position_scores.append(1.0)
                has_first_author = True
            elif author_pos == 2 or author_pos == '2':
                author_position_scores.append(0.7)
            elif author_pos:
                author_position_scores.append(0.4)
            else:
                author_position_scores.append(0.0)
            
            # Venue quality (simplified - can be extended with venue rankings)
            venue = self._normalize_string(pub.get('venue', ''))
            if any(term in venue for term in ['nature', 'science', 'cell', 'nejm']):
                venue_scores.append(1.0)
            elif any(term in venue for term in ['ieee', 'acm', 'springer']):
                venue_scores.append(0.7)
            elif venue:
                venue_scores.append(0.4)
            else:
                venue_scores.append(0.0)
        
        # Calculate averages
        avg_if = sum(if_scores) / len(if_scores) if if_scores else 0.0
        avg_author_pos = sum(author_position_scores) / len(author_position_scores) if author_position_scores else 0.0
        avg_venue = sum(venue_scores) / len(venue_scores) if venue_scores else 0.0
        
        # First author bonus
        first_author_bonus = self.policies.get('first_author_bonus', 0.15) if has_first_author else 0.0
        
        # Weighted score
        weighted_score = (
            avg_if * pub_subweights.get('if', 0.5) +
            avg_author_pos * pub_subweights.get('author_position', 0.3) +
            avg_venue * pub_subweights.get('venue_quality', 0.2)
        ) * (1 + first_author_bonus)
        weighted_score = min(1.0, weighted_score)
        
        return {
            'count': len(publications_list),
            'if_score': avg_if,
            'author_position_score': avg_author_pos,
            'venue_quality_score': avg_venue,
            'first_author_bonus': first_author_bonus,
            'weighted_score': weighted_score
        }
    
    def _evaluate_awards_quality(self, awards_list: List[Dict]) -> Dict[str, float]:
        """
        Evaluate awards and certifications.
        
        Returns:
            Dict with awards metrics
        """
        if not awards_list:
            return {
                'count': 0,
                'weighted_score': 0.0
            }
        
        # Simple count-based scoring (can be enhanced with award prestige)
        count = len(awards_list)
        # Normalize to 0-1 (assuming 5+ awards is excellent)
        weighted_score = min(1.0, count / 5.0)
        
        return {
            'count': count,
            'weighted_score': weighted_score
        }
    
    def _evaluate_coherence(self, resume: Dict, ground_truth: Dict) -> Dict[str, float]:
        """
        Evaluate coherence - how well the extracted data matches ground truth structure.
        This measures extraction accuracy.
        
        Returns:
            Dict with coherence metrics
        """
        scores = []
        
        # Check each major section
        sections = ['education', 'experience', 'publications', 'awards']
        
        for section in sections:
            gen_section = resume.get(section, [])
            truth_section = ground_truth.get(section, [])
            
            if not truth_section:
                # No ground truth - perfect score if nothing generated
                scores.append(1.0 if not gen_section else 0.5)
                continue
            
            if not gen_section:
                # Missing section
                scores.append(0.0)
                continue
            
            # Calculate basic precision/recall for the section
            gen_count = len(gen_section)
            truth_count = len(truth_section)
            
            # Simplified accuracy based on count difference
            count_diff = abs(gen_count - truth_count)
            section_score = max(0.0, 1.0 - (count_diff / max(truth_count, gen_count)))
            scores.append(section_score)
        
        # Name matching
        name_similarity = self._calculate_string_similarity(
            resume.get('name'), 
            ground_truth.get('name')
        )
        scores.append(name_similarity)
        
        weighted_score = sum(scores) / len(scores) if scores else 0.0
        
        return {
            'section_coherence': sum(scores[:4]) / 4 if len(scores) >= 4 else 0.0,
            'name_accuracy': name_similarity,
            'weighted_score': weighted_score
        }
    
    def _calculate_missing_values_penalty(self, resume: Dict) -> float:
        """
        Calculate penalty for missing important values.
        
        Returns:
            Penalty value (0-1, where higher is more penalty)
        """
        missing_count = 0
        total_expected = 0
        
        # Check education fields
        for edu in resume.get('education', []):
            fields = ['degree', 'field', 'university', 'start', 'end']
            for field in fields:
                total_expected += 1
                if not edu.get(field):
                    missing_count += 1
        
        # Check experience fields
        for exp in resume.get('experience', []):
            fields = ['title', 'org', 'start', 'end', 'domain']
            for field in fields:
                total_expected += 1
                if not exp.get(field):
                    missing_count += 1
        
        if total_expected == 0:
            return 0.0
        
        missing_ratio = missing_count / total_expected
        penalty = missing_ratio * self.policies.get('missing_values_penalty', 0.10)
        
        return penalty
    
    def evaluate_resume(self, resume_key: str) -> Dict[str, Any]:
        """
        Evaluate a single resume with weighted scoring.
        
        Returns:
            Dict with detailed scores and final weighted score
        """
        gen = self.generated_map.get(resume_key, {})
        truth = self.ground_truth_map.get(resume_key, {})
        
        # Evaluate each component
        education_eval = self._evaluate_education_quality(gen.get('education', []))
        experience_eval = self._evaluate_experience_quality(gen.get('experience', []))
        publications_eval = self._evaluate_publications_quality(gen.get('publications', []))
        awards_eval = self._evaluate_awards_quality(gen.get('awards', []))
        coherence_eval = self._evaluate_coherence(gen, truth)
        
        # Calculate missing values penalty
        missing_penalty = self._calculate_missing_values_penalty(gen)
        
        # Calculate final weighted score
        final_score = (
            education_eval['weighted_score'] * self.weights.get('education', 0.30) +
            experience_eval['weighted_score'] * self.weights.get('experience', 0.30) +
            publications_eval['weighted_score'] * self.weights.get('publications', 0.25) +
            coherence_eval['weighted_score'] * self.weights.get('coherence', 0.10) +
            awards_eval['weighted_score'] * self.weights.get('awards_other', 0.05)
        )
        
        # Apply missing values penalty
        final_score = max(0.0, final_score - missing_penalty)
        
        return {
            'education': education_eval,
            'experience': experience_eval,
            'publications': publications_eval,
            'awards': awards_eval,
            'coherence': coherence_eval,
            'missing_penalty': missing_penalty,
            'component_scores': {
                'education': education_eval['weighted_score'],
                'experience': experience_eval['weighted_score'],
                'publications': publications_eval['weighted_score'],
                'coherence': coherence_eval['weighted_score'],
                'awards': awards_eval['weighted_score']
            },
            'final_score': final_score,
            'grade': self._get_grade(final_score)
        }
    
    def _get_grade(self, score: float) -> str:
        """Convert score to letter grade with adjusted scale for resume evaluation."""
        if score >= 0.60:
            return 'A'
        elif score >= 0.40:
            return 'B'
        elif score >= 0.25:
            return 'C'
        elif score >= 0.15:
            return 'D'
        else:
            return 'F'
    
    def evaluate_all(self) -> Dict[str, Any]:
        """
        Evaluate all resumes.
        
        Returns:
            Dict with per-resume and aggregate results
        """
        results = {
            'per_resume': {},
            'aggregate': {
                'education': [],
                'experience': [],
                'publications': [],
                'awards': [],
                'coherence': [],
                'final_scores': []
            }
        }
        
        all_keys = set(self.generated_map.keys()) | set(self.ground_truth_map.keys())
        
        for key in all_keys:
            resume_eval = self.evaluate_resume(key)
            results['per_resume'][key] = resume_eval
            
            # Aggregate
            results['aggregate']['education'].append(resume_eval['component_scores']['education'])
            results['aggregate']['experience'].append(resume_eval['component_scores']['experience'])
            results['aggregate']['publications'].append(resume_eval['component_scores']['publications'])
            results['aggregate']['awards'].append(resume_eval['component_scores']['awards'])
            results['aggregate']['coherence'].append(resume_eval['component_scores']['coherence'])
            results['aggregate']['final_scores'].append(resume_eval['final_score'])
        
        # Calculate averages
        keys_to_average = list(results['aggregate'].keys())  # Create a list to avoid dict size change during iteration
        for key in keys_to_average:
            values = results['aggregate'][key]
            results['aggregate'][f'{key}_avg'] = sum(values) / len(values) if values else 0.0
        
        return results
    
    def print_report(self, results: Dict[str, Any]):
        """Print formatted weighted evaluation report."""
        print("=" * 80)
        print("WEIGHTED RESUME PARSING EVALUATION REPORT")
        print("=" * 80)
        print()
        
        print("Configuration:")
        print(f"  Weights: Education={self.weights.get('education'):.0%}, "
              f"Experience={self.weights.get('experience'):.0%}, "
              f"Publications={self.weights.get('publications'):.0%}")
        print(f"  Target Domain: {self.policies.get('domain', 'N/A')}")
        print(f"  Min Experience for Bonus: {self.policies.get('min_months_experience_for_bonus', 0)} months")
        print()
        
        print("-" * 80)
        print("AGGREGATE SCORES")
        print("-" * 80)
        agg = results['aggregate']
        print(f"Education:     {agg['education_avg']:.1%} (weight: {self.weights.get('education'):.0%})")
        print(f"Experience:    {agg['experience_avg']:.1%} (weight: {self.weights.get('experience'):.0%})")
        print(f"Publications:  {agg['publications_avg']:.1%} (weight: {self.weights.get('publications'):.0%})")
        print(f"Coherence:     {agg['coherence_avg']:.1%} (weight: {self.weights.get('coherence'):.0%})")
        print(f"Awards:        {agg['awards_avg']:.1%} (weight: {self.weights.get('awards_other'):.0%})")
        print()
        print(f"Overall Score: {agg['final_scores_avg']:.1%} (Grade: {self._get_grade(agg['final_scores_avg'])})")
        print()
        
        print("-" * 80)
        print("PER-RESUME DETAILED RESULTS")
        print("-" * 80)
        
        for resume_key, resume_result in results['per_resume'].items():
            print(f"\n{'=' * 80}")
            print(f"Resume: {resume_key}")
            print(f"{'=' * 80}")
            print(f"Final Score: {resume_result['final_score']:.1%} (Grade: {resume_result['grade']})")
            print()
            
            # Education
            edu = resume_result['education']
            print(f"Education ({edu['weighted_score']:.1%}):")
            print(f"  GPA Score:        {edu['gpa_score']:.1%}")
            print(f"  Degree Level:     {edu['degree_level_score']:.1%}")
            print(f"  University Tier:  {edu['university_tier_score']:.1%}")
            print()
            
            # Experience
            exp = resume_result['experience']
            print(f"Experience ({exp['weighted_score']:.1%}):")
            print(f"  Total Months:     {exp['total_months']}")
            print(f"  Relevant Months:  {exp['relevant_months']}")
            print(f"  Domain Match:     {exp['domain_match_score']:.1%}")
            print(f"  Experience Bonus: {exp['experience_bonus']:.1%}")
            print()
            
            # Publications
            pub = resume_result['publications']
            print(f"Publications ({pub['weighted_score']:.1%}):")
            print(f"  Count:            {pub['count']}")
            print(f"  IF Score:         {pub['if_score']:.1%}")
            print(f"  Author Position:  {pub['author_position_score']:.1%}")
            print(f"  Venue Quality:    {pub['venue_quality_score']:.1%}")
            print(f"  First Author Bonus: {pub['first_author_bonus']:.1%}")
            print()
            
            # Awards
            awd = resume_result['awards']
            print(f"Awards ({awd['weighted_score']:.1%}):")
            print(f"  Count:            {awd['count']}")
            print()
            
            # Coherence
            coh = resume_result['coherence']
            print(f"Coherence ({coh['weighted_score']:.1%}):")
            print(f"  Section Coherence: {coh['section_coherence']:.1%}")
            print(f"  Name Accuracy:     {coh['name_accuracy']:.1%}")
            print()
            
            # Penalty
            print(f"Missing Values Penalty: -{resume_result['missing_penalty']:.1%}")
        
        print()
        print("=" * 80)


def main():
    """Main function to run weighted evaluation."""
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python weighted_evaluate.py <generated_json> <ground_truth_json> [config_json]")
        print("\nExample:")
        print("  python weighted_evaluate.py results/parsed.json ground_truth/truth.json")
        print("  python weighted_evaluate.py results/parsed.json ground_truth/truth.json evaluation_config.json")
        sys.exit(1)
    
    generated_path = sys.argv[1]
    ground_truth_path = sys.argv[2]
    config_path = sys.argv[3] if len(sys.argv) > 3 else "evaluation_config.json"
    
    if not os.path.exists(generated_path):
        print(f"Error: Generated JSON not found: {generated_path}")
        sys.exit(1)
    
    if not os.path.exists(ground_truth_path):
        print(f"Error: Ground truth JSON not found: {ground_truth_path}")
        sys.exit(1)
    
    if not os.path.exists(config_path):
        print(f"Error: Config JSON not found: {config_path}")
        sys.exit(1)
    
    # Run evaluation
    evaluator = WeightedResumeEvaluator(generated_path, ground_truth_path, config_path)
    results = evaluator.evaluate_all()
    evaluator.print_report(results)
    
    # Save detailed results
    output_path = "weighted_evaluation_results.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nDetailed results saved to: {output_path}")


if __name__ == '__main__':
    main()
