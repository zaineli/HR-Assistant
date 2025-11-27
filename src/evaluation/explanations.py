"""
Evidence-linked explanation generator for resume rankings.
Provides transparent, traceable explanations for scoring decisions.
"""
import json
from typing import Dict, List, Any, Tuple


class ExplanationGenerator:
    """
    Generates evidence-backed explanations for resume scores and rankings.
    Links all scoring decisions to specific resume content.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize explanation generator with configuration.
        
        Args:
            config: Evaluation configuration dictionary
        """
        self.config = config
        self.weights = config.get('weights', {})
        self.subweights = config.get('subweights', {})
        self.policies = config.get('policies', {})
        self.unknown_handling = config.get('unknown_handling', {})
        
    def extract_evidence(self, resume: Dict[str, Any], scores: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract evidence spans from resume and link to scores.
        
        Args:
            resume: Resume data dictionary
            scores: Computed scores for this resume
            
        Returns:
            Dictionary containing evidence for each scoring component
        """
        evidence = {
            'candidate_name': resume.get('name', 'Unknown'),
            'filename': resume.get('filename', 'Unknown'),
            'education_evidence': self._extract_education_evidence(resume, scores),
            'experience_evidence': self._extract_experience_evidence(resume, scores),
            'publications_evidence': self._extract_publications_evidence(resume, scores),
            'awards_evidence': self._extract_awards_evidence(resume, scores),
            'coherence_evidence': self._extract_coherence_evidence(resume, scores),
            'score_summary': {
                'education': scores.get('component_scores', {}).get('education', 0),
                'experience': scores.get('component_scores', {}).get('experience', 0),
                'publications': scores.get('component_scores', {}).get('publications', 0),
                'coherence': scores.get('component_scores', {}).get('coherence', 0),
                'awards_other': scores.get('component_scores', {}).get('awards_other', 0),
                'final_score': scores.get('final_score', 0),
                'grade': scores.get('grade', 'N/A')
            }
        }
        
        return evidence
    
    def _extract_education_evidence(self, resume: Dict[str, Any], scores: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract evidence from education section."""
        evidence_items = []
        education_list = resume.get('education', [])
        
        for idx, edu in enumerate(education_list):
            degree = edu.get('degree', 'Unknown')
            field = edu.get('field', 'Unknown')
            university = edu.get('university', 'Unknown')
            gpa = edu.get('gpa')
            
            # Get tier information
            tier_info = self._get_university_tier_info(university)
            degree_score = self._get_degree_score_info(degree)
            gpa_score_info = self._get_gpa_score_info(gpa, edu.get('scale'))
            
            evidence = {
                'index': idx,
                'degree': degree,
                'field': field,
                'university': university,
                'gpa': gpa,
                'scale': edu.get('scale'),
                'years': f"{edu.get('start', '?')} - {edu.get('end', '?')}",
                'evidence_span': f"{degree} in {field} from {university}",
                'scoring_breakdown': {
                    'university_tier': tier_info,
                    'degree_level': degree_score,
                    'gpa_score': gpa_score_info
                },
                'contribution_to_total': self._calculate_component_contribution(
                    scores, 'education', idx, len(education_list)
                )
            }
            
            if gpa:
                evidence['evidence_span'] += f" (GPA: {gpa})"
            
            evidence_items.append(evidence)
        
        if not evidence_items:
            evidence_items.append({
                'missing': True,
                'explanation': 'No education information found',
                'impact': 'Education component receives zero score'
            })
        
        return evidence_items
    
    def _extract_experience_evidence(self, resume: Dict[str, Any], scores: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract evidence from experience section."""
        evidence_items = []
        experience_list = resume.get('experience', [])
        
        for idx, exp in enumerate(experience_list):
            title = exp.get('title', 'Unknown')
            org = exp.get('org', 'Unknown')
            domain = exp.get('domain', 'Unknown')
            duration = exp.get('duration_months', 0) or 0
            
            # Analyze seniority
            seniority_info = self._analyze_seniority(title)
            domain_match = self._check_domain_match(domain)
            
            evidence = {
                'index': idx,
                'title': title,
                'organization': org,
                'domain': domain,
                'duration_months': duration,
                'duration_years': round(duration / 12, 1) if duration else 0,
                'period': f"{exp.get('start', '?')} - {exp.get('end', '?')}",
                'evidence_span': f"{title} at {org} ({duration} months)",
                'scoring_breakdown': {
                    'duration_score': min(duration / 60, 1.0) if duration else 0,  # Max at 5 years
                    'seniority': seniority_info,
                    'domain_match': domain_match
                },
                'contribution_to_total': self._calculate_component_contribution(
                    scores, 'experience', idx, len(experience_list)
                )
            }
            
            if domain and domain != 'Unknown':
                evidence['evidence_span'] += f" - {domain}"
            
            evidence_items.append(evidence)
        
        if not evidence_items:
            evidence_items.append({
                'missing': True,
                'explanation': 'No experience information found',
                'impact': 'Experience component receives zero score'
            })
        
        return evidence_items
    
    def _extract_publications_evidence(self, resume: Dict[str, Any], scores: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract evidence from publications section."""
        evidence_items = []
        publications_list = resume.get('publications', [])
        
        for idx, pub in enumerate(publications_list):
            title = pub.get('title', 'Unknown')
            venue = pub.get('venue', 'Unknown')
            journal_if = pub.get('journal_if')
            author_position = pub.get('author_position', 'Unknown')
            
            # Analyze IF and position
            if_info = self._analyze_impact_factor(journal_if)
            position_info = self._analyze_author_position(author_position)
            
            evidence = {
                'index': idx,
                'title': title,
                'venue': venue,
                'journal_if': journal_if,
                'author_position': author_position,
                'evidence_span': f'"{title}" in {venue}',
                'scoring_breakdown': {
                    'impact_factor': if_info,
                    'author_position': position_info,
                    'venue_quality': 0.8 if venue and venue != 'Unknown' else 0.2
                },
                'contribution_to_total': self._calculate_component_contribution(
                    scores, 'publications', idx, len(publications_list)
                )
            }
            
            if journal_if:
                evidence['evidence_span'] += f" (IF: {journal_if})"
            if author_position and author_position != 'Unknown':
                pos_str = 'First' if str(author_position) == '1' else f"{author_position}"
                evidence['evidence_span'] += f" [{pos_str} author]"
            
            evidence_items.append(evidence)
        
        if not evidence_items:
            evidence_items.append({
                'missing': True,
                'explanation': 'No publications found',
                'impact': 'Publications component receives zero score'
            })
        
        return evidence_items
    
    def _extract_awards_evidence(self, resume: Dict[str, Any], scores: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract evidence from awards section."""
        evidence_items = []
        awards_list = resume.get('awards', [])
        
        for idx, award in enumerate(awards_list):
            title = award.get('title', 'Unknown')
            issuer = award.get('issuer', 'Unknown')
            year = award.get('year')
            
            evidence = {
                'index': idx,
                'title': title,
                'issuer': issuer,
                'year': year,
                'evidence_span': title,
                'contribution_to_total': self._calculate_component_contribution(
                    scores, 'awards_other', idx, len(awards_list)
                )
            }
            
            if issuer and issuer != 'Unknown':
                evidence['evidence_span'] += f" from {issuer}"
            if year:
                evidence['evidence_span'] += f" ({year})"
            
            evidence_items.append(evidence)
        
        if not evidence_items:
            evidence_items.append({
                'missing': True,
                'explanation': 'No awards found',
                'impact': 'Awards component receives minimal score'
            })
        
        return evidence_items
    
    def _extract_coherence_evidence(self, resume: Dict[str, Any], scores: Dict[str, Any]) -> Dict[str, Any]:
        """Extract evidence for coherence scoring."""
        coherence_details = scores.get('component_details', {}).get('coherence', {})
        
        evidence = {
            'timeline_consistency': coherence_details.get('timeline_issues', []),
            'field_alignment': coherence_details.get('field_alignment', 'Not analyzed'),
            'career_progression': coherence_details.get('progression_detected', False),
            'overall_score': coherence_details.get('score', 0),
            'explanation': self._generate_coherence_explanation(coherence_details)
        }
        
        return evidence
    
    def _generate_coherence_explanation(self, details: Dict[str, Any]) -> str:
        """Generate human-readable explanation for coherence score."""
        explanations = []
        
        timeline_issues = details.get('timeline_issues', [])
        if timeline_issues:
            explanations.append(f"Found {len(timeline_issues)} timeline gaps or overlaps")
        else:
            explanations.append("Timeline is consistent with no significant gaps")
        
        if details.get('progression_detected'):
            explanations.append("Career progression detected (seniority increase)")
        
        field_alignment = details.get('field_alignment')
        if field_alignment:
            explanations.append(f"Field alignment: {field_alignment}")
        
        return "; ".join(explanations) if explanations else "Coherence analysis incomplete"
    
    def generate_comparison_explanation(self, 
                                       resume_a: Dict[str, Any], 
                                       scores_a: Dict[str, Any],
                                       evidence_a: Dict[str, Any],
                                       resume_b: Dict[str, Any], 
                                       scores_b: Dict[str, Any],
                                       evidence_b: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate 'Why A > B' comparison explanation.
        
        Args:
            resume_a: Higher-ranked resume
            scores_a: Scores for resume A
            evidence_a: Evidence for resume A
            resume_b: Lower-ranked resume
            scores_b: Scores for resume B
            evidence_b: Evidence for resume B
            
        Returns:
            Dictionary with comparison details and top reasons
        """
        name_a = evidence_a.get('candidate_name', 'Candidate A')
        name_b = evidence_b.get('candidate_name', 'Candidate B')
        
        score_delta = scores_a.get('final_score', 0) - scores_b.get('final_score', 0)
        
        # Calculate component deltas
        component_deltas = []
        for component in ['education', 'experience', 'publications', 'coherence', 'awards_other']:
            score_a = scores_a.get('component_scores', {}).get(component, 0)
            score_b = scores_b.get('component_scores', {}).get(component, 0)
            delta = score_a - score_b
            weighted_delta = delta * self.weights.get(component, 0)
            
            component_deltas.append({
                'component': component,
                'score_a': round(score_a, 4),
                'score_b': round(score_b, 4),
                'delta': round(delta, 4),
                'weighted_delta': round(weighted_delta, 4),
                'weight': self.weights.get(component, 0)
            })
        
        # Sort by weighted impact
        component_deltas.sort(key=lambda x: abs(x['weighted_delta']), reverse=True)
        
        # Generate top 3 reasons
        top_reasons = []
        for i, comp_delta in enumerate(component_deltas[:3], 1):
            component = comp_delta['component']
            reason = self._generate_component_comparison_reason(
                component, evidence_a, evidence_b, comp_delta
            )
            top_reasons.append({
                'rank': i,
                'component': component,
                'delta': comp_delta['delta'],
                'weighted_impact': comp_delta['weighted_delta'],
                'reason': reason,
                'evidence_a': self._extract_key_evidence(component, evidence_a),
                'evidence_b': self._extract_key_evidence(component, evidence_b)
            })
        
        comparison = {
            'candidate_a': name_a,
            'candidate_b': name_b,
            'final_score_a': round(scores_a.get('final_score', 0), 4),
            'final_score_b': round(scores_b.get('final_score', 0), 4),
            'score_delta': round(score_delta, 4),
            'grade_a': scores_a.get('grade', 'N/A'),
            'grade_b': scores_b.get('grade', 'N/A'),
            'summary': f"{name_a} scores {score_delta:.4f} points higher than {name_b}",
            'component_deltas': component_deltas,
            'top_3_reasons': top_reasons
        }
        
        return comparison
    
    def _generate_component_comparison_reason(self, 
                                             component: str, 
                                             evidence_a: Dict[str, Any],
                                             evidence_b: Dict[str, Any],
                                             delta_info: Dict[str, Any]) -> str:
        """Generate human-readable reason for component difference."""
        delta = delta_info['delta']
        
        if component == 'education':
            edu_a = evidence_a.get('education_evidence', [])
            edu_b = evidence_b.get('education_evidence', [])
            
            if not edu_a or (edu_a and edu_a[0].get('missing')):
                return "Candidate A has no education information"
            if not edu_b or (edu_b and edu_b[0].get('missing')):
                return "Candidate B has no education information"
            
            # Compare best education
            best_a = max(edu_a, key=lambda x: sum(x.get('scoring_breakdown', {}).get(k, {}).get('score', 0) for k in ['university_tier', 'degree_level', 'gpa_score']) if not x.get('missing') else 0)
            best_b = max(edu_b, key=lambda x: sum(x.get('scoring_breakdown', {}).get(k, {}).get('score', 0) for k in ['university_tier', 'degree_level', 'gpa_score']) if not x.get('missing') else 0)
            
            reasons = []
            if best_a['scoring_breakdown']['university_tier']['score'] > best_b['scoring_breakdown']['university_tier']['score']:
                reasons.append(f"higher tier university ({best_a['university']} vs {best_b['university']})")
            if best_a['scoring_breakdown']['degree_level']['score'] > best_b['scoring_breakdown']['degree_level']['score']:
                reasons.append(f"higher degree level ({best_a['degree']} vs {best_b['degree']})")
            if best_a['scoring_breakdown']['gpa_score']['score'] > best_b['scoring_breakdown']['gpa_score']['score']:
                reasons.append(f"better GPA ({best_a.get('gpa', 'N/A')} vs {best_b.get('gpa', 'N/A')})")
            
            return f"Candidate A has {', '.join(reasons)}" if reasons else "Better overall education credentials"
        
        elif component == 'experience':
            exp_a = evidence_a.get('experience_evidence', [])
            exp_b = evidence_b.get('experience_evidence', [])
            
            if not exp_a or (exp_a and exp_a[0].get('missing')):
                return "Candidate A has no experience information"
            if not exp_b or (exp_b and exp_b[0].get('missing')):
                return "Candidate B has no experience information"
            
            total_months_a = sum(e.get('duration_months', 0) or 0 for e in exp_a if not e.get('missing'))
            total_months_b = sum(e.get('duration_months', 0) or 0 for e in exp_b if not e.get('missing'))
            
            return f"Candidate A has more experience ({total_months_a} months vs {total_months_b} months)"
        
        elif component == 'publications':
            pubs_a = evidence_a.get('publications_evidence', [])
            pubs_b = evidence_b.get('publications_evidence', [])
            
            count_a = len([p for p in pubs_a if not p.get('missing')])
            count_b = len([p for p in pubs_b if not p.get('missing')])
            
            if count_a > count_b:
                return f"Candidate A has more publications ({count_a} vs {count_b})"
            elif count_a == count_b:
                return "Candidate A has higher quality publications (better IF or author positions)"
            else:
                return f"Candidate B has more publications ({count_b} vs {count_a})"
        
        elif component == 'coherence':
            if delta > 0:
                return "Candidate A has better timeline consistency and career progression"
            else:
                return "Candidate B has better timeline consistency and career progression"
        
        elif component == 'awards_other':
            awards_a = evidence_a.get('awards_evidence', [])
            awards_b = evidence_b.get('awards_evidence', [])
            
            count_a = len([a for a in awards_a if not a.get('missing')])
            count_b = len([a for a in awards_b if not a.get('missing')])
            
            return f"Candidate A has {'more' if count_a > count_b else 'fewer'} awards ({count_a} vs {count_b})"
        
        return f"Component {component} contributes {delta:.4f} to the difference"
    
    def _extract_key_evidence(self, component: str, evidence: Dict[str, Any]) -> List[str]:
        """Extract key evidence spans for a component."""
        key_evidence = []
        
        evidence_key = f"{component}_evidence"
        items = evidence.get(evidence_key, [])
        
        for item in items[:3]:  # Top 3 items
            if not item.get('missing'):
                key_evidence.append(item.get('evidence_span', 'N/A'))
        
        return key_evidence if key_evidence else ["No evidence available"]
    
    def _get_university_tier_info(self, university: str) -> Dict[str, Any]:
        """Get university tier information."""
        if not university or university == 'Unknown':
            return {
                'tier': 'unknown',
                'score': self.unknown_handling.get('university', {}).get('score', 0.4),
                'explanation': 'University not specified or unknown'
            }
        
        uni_tiers = self.config.get('university_tiers', {})
        uni_lower = university.lower()
        
        for tier_name, tier_data in uni_tiers.items():
            if tier_name.startswith('_'):
                continue
            universities = tier_data.get('universities', [])
            for uni in universities:
                if uni.lower() in uni_lower or uni_lower in uni.lower():
                    return {
                        'tier': tier_name,
                        'score': tier_data.get('score', 0.5),
                        'explanation': f'{university} is a {tier_name} university'
                    }
        
        # Default tier 3
        return {
            'tier': 'tier3',
            'score': 0.4,
            'explanation': f'{university} is classified as tier3 (default)'
        }
    
    def _get_degree_score_info(self, degree: str) -> Dict[str, Any]:
        """Get degree level score information."""
        if not degree or degree == 'Unknown':
            return {
                'level': 'unknown',
                'score': self.unknown_handling.get('degree', {}).get('score', 0.3),
                'explanation': 'Degree level not specified'
            }
        
        degree_levels = self.config.get('degree_levels', {})
        degree_lower = degree.lower()
        
        for deg_type, score in degree_levels.items():
            if deg_type.startswith('_'):
                continue
            if deg_type.lower() in degree_lower:
                return {
                    'level': deg_type,
                    'score': score,
                    'explanation': f'{degree} classified as {deg_type}'
                }
        
        return {
            'level': 'unknown',
            'score': 0.3,
            'explanation': f'Degree {degree} not in known categories'
        }
    
    def _get_gpa_score_info(self, gpa: Any, scale: Any) -> Dict[str, Any]:
        """Get GPA score information."""
        if gpa is None:
            return {
                'score': self.unknown_handling.get('gpa', {}).get('score', 0.5),
                'normalized': None,
                'explanation': 'GPA not provided - neutral score applied'
            }
        
        try:
            gpa_val = float(gpa)
            scale_val = float(scale) if scale else 4.0
            normalized = gpa_val / scale_val
            
            return {
                'score': min(normalized, 1.0),
                'normalized': round(normalized, 2),
                'raw': gpa_val,
                'scale': scale_val,
                'explanation': f'GPA {gpa_val}/{scale_val} = {normalized:.2f} normalized'
            }
        except (ValueError, TypeError):
            return {
                'score': 0.5,
                'normalized': None,
                'explanation': f'Invalid GPA format: {gpa}'
            }
    
    def _analyze_seniority(self, title: str) -> Dict[str, Any]:
        """Analyze job title for seniority level."""
        if not title or title == 'Unknown':
            return {
                'level': 'unknown',
                'score': 0.5,
                'explanation': 'Job title not provided'
            }
        
        title_lower = title.lower()
        seniority_keywords = self.config.get('experience_seniority_keywords', {})
        
        for level in ['senior', 'mid', 'junior']:
            keywords = seniority_keywords.get(level, [])
            for keyword in keywords:
                if keyword in title_lower:
                    scores = {'senior': 1.0, 'mid': 0.7, 'junior': 0.4}
                    return {
                        'level': level,
                        'score': scores.get(level, 0.5),
                        'keyword': keyword,
                        'explanation': f'Detected {level} level via keyword "{keyword}"'
                    }
        
        return {
            'level': 'mid',
            'score': 0.7,
            'explanation': 'Default to mid-level (no seniority keywords detected)'
        }
    
    def _check_domain_match(self, domain: str) -> Dict[str, Any]:
        """Check if domain matches target domain."""
        target_domain = self.policies.get('domain', 'NLP')
        
        if not domain or domain == 'Unknown':
            return {
                'matches': False,
                'score': 0.3,
                'explanation': 'Domain not specified'
            }
        
        domain_lower = domain.lower()
        target_lower = target_domain.lower()
        
        if target_lower in domain_lower:
            return {
                'matches': True,
                'score': 1.0,
                'explanation': f'Domain {domain} matches target {target_domain}'
            }
        
        return {
            'matches': False,
            'score': 0.5,
            'explanation': f'Domain {domain} does not match target {target_domain}'
        }
    
    def _analyze_impact_factor(self, journal_if: Any) -> Dict[str, Any]:
        """Analyze publication impact factor."""
        if journal_if is None:
            unknown_if = self.config.get('publication_if_thresholds', {}).get('unknown', {})
            return {
                'category': 'unknown',
                'score': unknown_if.get('score', 0.3),
                'explanation': 'Impact factor not provided'
            }
        
        try:
            if_val = float(journal_if)
            thresholds = self.config.get('publication_if_thresholds', {})
            
            high = thresholds.get('high', {})
            if if_val >= high.get('min', 5.0):
                return {
                    'category': 'high',
                    'score': high.get('score', 1.0),
                    'value': if_val,
                    'explanation': f'High impact (IF={if_val} ≥ {high.get("min")})'
                }
            
            medium = thresholds.get('medium', {})
            if if_val >= medium.get('min', 2.0):
                return {
                    'category': 'medium',
                    'score': medium.get('score', 0.7),
                    'value': if_val,
                    'explanation': f'Medium impact (IF={if_val}, range {medium.get("min")}-{medium.get("max")})'
                }
            
            low = thresholds.get('low', {})
            return {
                'category': 'low',
                'score': low.get('score', 0.4),
                'value': if_val,
                'explanation': f'Low impact (IF={if_val} < {medium.get("min")})'
            }
        except (ValueError, TypeError):
            return {
                'category': 'invalid',
                'score': 0.2,
                'explanation': f'Invalid IF value: {journal_if}'
            }
    
    def _analyze_author_position(self, position: Any) -> Dict[str, Any]:
        """Analyze author position."""
        if position is None or position == 'Unknown':
            return {
                'position': 'unknown',
                'score': self.config.get('author_position_scoring', {}).get('unknown', 0.2),
                'explanation': 'Author position not specified'
            }
        
        try:
            pos_val = int(position)
            position_scores = self.config.get('author_position_scoring', {})
            
            if pos_val == 1:
                return {
                    'position': '1st',
                    'score': position_scores.get('1', 1.0),
                    'explanation': 'First author (primary contributor)'
                }
            elif pos_val == 2:
                return {
                    'position': '2nd',
                    'score': position_scores.get('2', 0.7),
                    'explanation': 'Second author'
                }
            elif pos_val == 3:
                return {
                    'position': '3rd',
                    'score': position_scores.get('3', 0.5),
                    'explanation': 'Third author'
                }
            else:
                return {
                    'position': f'{pos_val}th',
                    'score': position_scores.get('4+', 0.3),
                    'explanation': f'Author position {pos_val} (lower contribution weight)'
                }
        except (ValueError, TypeError):
            return {
                'position': 'invalid',
                'score': 0.2,
                'explanation': f'Invalid position value: {position}'
            }
    
    def _calculate_component_contribution(self, scores: Dict[str, Any], component: str, idx: int, total: int) -> float:
        """Calculate individual item contribution to component score."""
        if total == 0:
            return 0.0
        
        component_score = scores.get('component_scores', {}).get(component, 0)
        # Approximate equal contribution from each item
        return component_score / total
