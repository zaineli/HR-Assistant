"""
Coherence modeling for resume evaluation.
Evaluates timeline consistency, field alignment, and career progression.
"""
from typing import Dict, List, Any, Tuple
from datetime import datetime
from dateutil import parser as date_parser
import re


class CoherenceEvaluator:
    """
    Evaluates the coherence and consistency of resume information.
    Checks timeline gaps, field alignment, and career progression.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize coherence evaluator with configuration.
        
        Args:
            config: Evaluation configuration dictionary
        """
        self.config = config
        self.coherence_checks = config.get('coherence_checks', {})
        self.timeline_gap_penalty = self.coherence_checks.get('timeline_gaps_penalty', 0.1)
        self.max_gap_months = self.coherence_checks.get('max_acceptable_gap_months', 6)
        self.field_mismatch_penalty = self.coherence_checks.get('field_mismatch_penalty', 0.15)
        self.progression_bonus = self.coherence_checks.get('career_progression_bonus', 0.1)
    
    def evaluate_coherence(self, resume: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate overall coherence of resume.
        
        Args:
            resume: Resume data dictionary
            
        Returns:
            Dictionary with coherence score and details
        """
        # Start with perfect score
        coherence_score = 1.0
        issues = []
        details = {}
        
        # Evaluate timeline consistency
        timeline_result = self._evaluate_timeline_consistency(resume)
        coherence_score -= timeline_result['penalty']
        details['timeline_issues'] = timeline_result['issues']
        details['timeline_score'] = timeline_result['score']
        
        # Evaluate field alignment
        field_result = self._evaluate_field_alignment(resume)
        coherence_score -= field_result['penalty']
        details['field_alignment'] = field_result['alignment']
        details['field_score'] = field_result['score']
        
        # Evaluate career progression
        progression_result = self._evaluate_career_progression(resume)
        coherence_score += progression_result['bonus']
        details['progression_detected'] = progression_result['detected']
        details['progression_score'] = progression_result['score']
        
        # Ensure score stays in [0, 1]
        coherence_score = max(0.0, min(1.0, coherence_score))
        
        details['score'] = coherence_score
        details['issues'] = timeline_result['issues'] + field_result['issues']
        
        return details
    
    def _evaluate_timeline_consistency(self, resume: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate timeline consistency across education and experience.
        
        Returns:
            Dictionary with penalty, issues, and score
        """
        issues = []
        total_penalty = 0.0
        
        # Parse all dates
        education_periods = self._parse_education_periods(resume.get('education', []))
        experience_periods = self._parse_experience_periods(resume.get('experience', []))
        
        # Check for gaps in experience timeline
        if len(experience_periods) > 1:
            experience_periods.sort(key=lambda x: x['start_date'] if x['start_date'] else datetime.min)
            
            for i in range(len(experience_periods) - 1):
                current = experience_periods[i]
                next_exp = experience_periods[i + 1]
                
                if current['end_date'] and next_exp['start_date']:
                    # Calculate gap in months
                    gap_months = self._calculate_month_difference(current['end_date'], next_exp['start_date'])
                    
                    if gap_months > self.max_gap_months:
                        issues.append({
                            'type': 'timeline_gap',
                            'severity': 'medium',
                            'description': f'Gap of {gap_months} months between {current["title"]} and {next_exp["title"]}',
                            'gap_months': gap_months
                        })
                        total_penalty += self.timeline_gap_penalty
                    elif gap_months < -1:  # Overlap
                        issues.append({
                            'type': 'timeline_overlap',
                            'severity': 'low',
                            'description': f'Overlap of {abs(gap_months)} months between {current["title"]} and {next_exp["title"]}',
                            'overlap_months': abs(gap_months)
                        })
                        # Small penalty for overlaps (might be legitimate part-time work)
                        total_penalty += self.timeline_gap_penalty * 0.3
        
        # Check for overlaps between education and experience
        for edu in education_periods:
            for exp in experience_periods:
                if edu['start_date'] and edu['end_date'] and exp['start_date']:
                    # Check if experience is fully within education period
                    if exp['start_date'] >= edu['start_date'] and exp['start_date'] <= edu['end_date']:
                        # This is common and acceptable (working while studying)
                        pass
        
        # Cap total penalty
        total_penalty = min(total_penalty, 0.4)
        
        return {
            'penalty': total_penalty,
            'issues': issues,
            'score': 1.0 - total_penalty
        }
    
    def _evaluate_field_alignment(self, resume: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate field alignment between education and experience.
        
        Returns:
            Dictionary with penalty, alignment description, and issues
        """
        issues = []
        penalty = 0.0
        
        education = resume.get('education', [])
        experience = resume.get('experience', [])
        
        if not education or not experience:
            return {
                'penalty': 0.0,
                'alignment': 'Cannot determine - insufficient data',
                'score': 1.0,
                'issues': []
            }
        
        # Extract fields from education
        education_fields = set()
        for edu in education:
            field = edu.get('field', '')
            if field and field.lower() != 'unknown':
                education_fields.add(field.lower().strip())
        
        # Extract domains from experience
        experience_domains = set()
        for exp in experience:
            domain = exp.get('domain', '')
            if domain and domain.lower() != 'unknown':
                experience_domains.add(domain.lower().strip())
        
        if not education_fields or not experience_domains:
            return {
                'penalty': 0.0,
                'alignment': 'Cannot determine - missing field/domain information',
                'score': 1.0,
                'issues': []
            }
        
        # Check for alignment
        alignment_found = False
        for edu_field in education_fields:
            for exp_domain in experience_domains:
                # Check for common keywords
                edu_keywords = set(edu_field.split())
                exp_keywords = set(exp_domain.split())
                
                # Common technical fields
                common_fields = {
                    'computer', 'software', 'engineering', 'science',
                    'nlp', 'ai', 'ml', 'data', 'analytics'
                }
                
                if edu_keywords & exp_keywords:
                    alignment_found = True
                    break
                
                # Check for common technical terms
                if (edu_keywords & common_fields) and (exp_keywords & common_fields):
                    alignment_found = True
                    break
            
            if alignment_found:
                break
        
        if not alignment_found:
            issues.append({
                'type': 'field_mismatch',
                'severity': 'medium',
                'description': f'Education fields ({", ".join(education_fields)}) do not align with experience domains ({", ".join(experience_domains)})',
                'education_fields': list(education_fields),
                'experience_domains': list(experience_domains)
            })
            penalty = self.field_mismatch_penalty
            alignment = 'Misaligned'
        else:
            alignment = 'Aligned'
        
        return {
            'penalty': penalty,
            'alignment': alignment,
            'score': 1.0 - penalty,
            'issues': issues
        }
    
    def _evaluate_career_progression(self, resume: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate career progression (seniority increase over time).
        
        Returns:
            Dictionary with bonus, detection flag, and score
        """
        experience = resume.get('experience', [])
        
        if len(experience) < 2:
            return {
                'bonus': 0.0,
                'detected': False,
                'score': 0.0
            }
        
        # Parse experience with dates
        exp_with_dates = self._parse_experience_periods(experience)
        
        if len(exp_with_dates) < 2:
            return {
                'bonus': 0.0,
                'detected': False,
                'score': 0.0
            }
        
        # Sort by start date
        exp_with_dates.sort(key=lambda x: x['start_date'] if x['start_date'] else datetime.min)
        
        # Define seniority levels
        seniority_keywords = {
            'senior': 3,
            'sr': 3,
            'lead': 3,
            'principal': 4,
            'chief': 5,
            'head': 4,
            'director': 4,
            'vp': 5,
            'vice president': 5,
            'manager': 3,
            'junior': 1,
            'jr': 1,
            'associate': 1,
            'intern': 0,
            'trainee': 0
        }
        
        # Assign seniority scores
        for exp in exp_with_dates:
            title = exp['title'].lower()
            exp['seniority_score'] = 2  # Default mid-level
            
            for keyword, score in seniority_keywords.items():
                if keyword in title:
                    exp['seniority_score'] = score
                    break
        
        # Check for progression
        progression_detected = False
        for i in range(len(exp_with_dates) - 1):
            if exp_with_dates[i + 1]['seniority_score'] > exp_with_dates[i]['seniority_score']:
                progression_detected = True
                break
        
        bonus = self.progression_bonus if progression_detected else 0.0
        
        return {
            'bonus': bonus,
            'detected': progression_detected,
            'score': 1.0 if progression_detected else 0.5
        }
    
    def _parse_education_periods(self, education: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse education entries into time periods."""
        periods = []
        
        for edu in education:
            start_date = self._parse_date(edu.get('start'))
            end_date = self._parse_date(edu.get('end'))
            
            periods.append({
                'degree': edu.get('degree', 'Unknown'),
                'university': edu.get('university', 'Unknown'),
                'start_date': start_date,
                'end_date': end_date,
                'start_str': edu.get('start', '?'),
                'end_str': edu.get('end', '?')
            })
        
        return periods
    
    def _parse_experience_periods(self, experience: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse experience entries into time periods."""
        periods = []
        
        for exp in experience:
            start_date = self._parse_date(exp.get('start'))
            end_date = self._parse_date(exp.get('end'))
            
            # Handle "currently working"
            if not end_date:
                end_str = str(exp.get('end', '')).lower()
                if 'current' in end_str or 'present' in end_str or 'working' in end_str:
                    end_date = datetime.now()
            
            periods.append({
                'title': exp.get('title', 'Unknown'),
                'org': exp.get('org', 'Unknown'),
                'start_date': start_date,
                'end_date': end_date,
                'start_str': exp.get('start', '?'),
                'end_str': exp.get('end', '?')
            })
        
        return periods
    
    def _parse_date(self, date_value: Any) -> datetime:
        """
        Parse date from various formats.
        
        Returns:
            datetime object or None
        """
        if not date_value:
            return None
        
        date_str = str(date_value).strip().lower()
        
        # Handle "currently working"
        if 'current' in date_str or 'present' in date_str or 'working' in date_str:
            return datetime.now()
        
        # Try to parse as year only
        if re.match(r'^\d{4}$', date_str):
            try:
                return datetime(int(date_str), 1, 1)
            except ValueError:
                return None
        
        # Try various date formats
        try:
            return date_parser.parse(date_str, fuzzy=True)
        except (ValueError, TypeError):
            return None
    
    def _calculate_month_difference(self, date1: datetime, date2: datetime) -> int:
        """
        Calculate difference in months between two dates.
        Positive if date2 is after date1.
        """
        if not date1 or not date2:
            return 0
        
        month_diff = (date2.year - date1.year) * 12 + (date2.month - date1.month)
        return month_diff
