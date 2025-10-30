"""
Evaluation script to compare generated resume JSON with ground truth.
Calculates precision, recall, F1 score, and field-level accuracy.
"""
import json
import os
from typing import Dict, List, Any, Tuple
from collections import defaultdict
import re


class ResumeEvaluator:
    """Evaluator for comparing generated resume data with ground truth."""
    
    def __init__(self, generated_path: str, ground_truth_path: str):
        """
        Initialize evaluator with paths to generated and ground truth JSON files.
        
        Args:
            generated_path: Path to generated JSON file
            ground_truth_path: Path to ground truth JSON file
        """
        self.generated = self._load_json(generated_path)
        self.ground_truth = self._load_json(ground_truth_path)
        
        # Map filenames/names to resumes for comparison
        self.generated_map = self._create_resume_map(self.generated)
        self.ground_truth_map = self._create_resume_map(self.ground_truth)
    
    def _load_json(self, path: str) -> List[Dict]:
        """Load JSON file."""
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _create_resume_map(self, resumes: List[Dict]) -> Dict[str, Dict]:
        """Create a mapping of resume identifiers to resume data."""
        resume_map = {}
        for resume in resumes:
            # Use filename or name as key
            key = resume.get('filename', resume.get('name', ''))
            if key:
                resume_map[key] = resume
        return resume_map
    
    def _normalize_string(self, text: Any) -> str:
        """Normalize string for comparison."""
        if text is None:
            return ""
        text = str(text).lower().strip()
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        return text
    
    def _normalize_date(self, date: Any) -> str:
        """Normalize date strings for comparison."""
        if date is None:
            return ""
        date_str = str(date).lower().strip()
        # Handle "currently working"
        if "current" in date_str:
            return "currently working"
        # Remove spaces, normalize format
        date_str = re.sub(r'\s+', '', date_str)
        return date_str
    
    def _compare_strings(self, gen: Any, truth: Any, fuzzy: bool = True) -> float:
        """
        Compare two strings with optional fuzzy matching.
        
        Returns:
            float: Similarity score between 0 and 1
        """
        gen_str = self._normalize_string(gen)
        truth_str = self._normalize_string(truth)
        
        if not truth_str:
            return 1.0 if not gen_str else 0.0
        
        if gen_str == truth_str:
            return 1.0
        
        if fuzzy:
            # Check if one contains the other (partial match)
            if gen_str in truth_str or truth_str in gen_str:
                return 0.8
            
            # Calculate word overlap
            gen_words = set(gen_str.split())
            truth_words = set(truth_str.split())
            if truth_words:
                overlap = len(gen_words & truth_words) / len(truth_words)
                return overlap * 0.7
        
        return 0.0
    
    def _compare_lists(self, gen_list: List[Dict], truth_list: List[Dict], 
                       key_fields: List[str]) -> Dict[str, float]:
        """
        Compare two lists of dictionaries (e.g., education, experience).
        
        Args:
            gen_list: Generated list
            truth_list: Ground truth list
            key_fields: Fields to use for matching items
            
        Returns:
            Dict with precision, recall, F1 score
        """
        if not truth_list:
            return {
                'precision': 1.0 if not gen_list else 0.0,
                'recall': 1.0,
                'f1': 1.0 if not gen_list else 0.0,
                'count_generated': len(gen_list),
                'count_truth': 0,
                'count_matched': 0
            }
        
        if not gen_list:
            return {
                'precision': 0.0,
                'recall': 0.0,
                'f1': 0.0,
                'count_generated': 0,
                'count_truth': len(truth_list),
                'count_matched': 0
            }
        
        # Match generated items to truth items
        matched_truth = set()
        matched_gen = set()
        match_scores = []
        
        for i, gen_item in enumerate(gen_list):
            best_match_idx = -1
            best_match_score = 0.0
            
            for j, truth_item in enumerate(truth_list):
                if j in matched_truth:
                    continue
                
                # Calculate similarity based on key fields
                scores = []
                for field in key_fields:
                    gen_val = gen_item.get(field)
                    truth_val = truth_item.get(field)
                    score = self._compare_strings(gen_val, truth_val)
                    scores.append(score)
                
                avg_score = sum(scores) / len(scores) if scores else 0.0
                
                if avg_score > best_match_score and avg_score > 0.5:
                    best_match_score = avg_score
                    best_match_idx = j
            
            if best_match_idx >= 0:
                matched_truth.add(best_match_idx)
                matched_gen.add(i)
                match_scores.append(best_match_score)
        
        num_matched = len(matched_truth)
        precision = num_matched / len(gen_list) if gen_list else 0.0
        recall = num_matched / len(truth_list) if truth_list else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        return {
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'count_generated': len(gen_list),
            'count_truth': len(truth_list),
            'count_matched': num_matched,
            'avg_match_quality': sum(match_scores) / len(match_scores) if match_scores else 0.0
        }
    
    def _evaluate_field(self, gen_val: Any, truth_val: Any, field_type: str = 'string') -> float:
        """
        Evaluate a single field value.
        
        Args:
            gen_val: Generated value
            truth_val: Ground truth value
            field_type: Type of field ('string', 'number', 'date')
            
        Returns:
            float: Accuracy score (0-1)
        """
        if field_type == 'date':
            gen_norm = self._normalize_date(gen_val)
            truth_norm = self._normalize_date(truth_val)
            return 1.0 if gen_norm == truth_norm else 0.0
        
        elif field_type == 'number':
            try:
                gen_num = float(gen_val) if gen_val is not None else None
                truth_num = float(truth_val) if truth_val is not None else None
                if gen_num is None and truth_num is None:
                    return 1.0
                if gen_num is None or truth_num is None:
                    return 0.0
                # Allow small tolerance for numbers
                return 1.0 if abs(gen_num - truth_num) < 0.01 else 0.0
            except (ValueError, TypeError):
                return 0.0
        
        else:  # string
            return self._compare_strings(gen_val, truth_val)
    
    def evaluate_name(self, resume_key: str) -> Dict[str, Any]:
        """Evaluate name extraction."""
        gen = self.generated_map.get(resume_key, {})
        truth = self.ground_truth_map.get(resume_key, {})
        
        gen_name = gen.get('name', '')
        truth_name = truth.get('name', '')
        
        accuracy = self._compare_strings(gen_name, truth_name)
        
        return {
            'accuracy': accuracy,
            'generated': gen_name,
            'truth': truth_name,
            'correct': accuracy >= 0.9
        }
    
    def evaluate_education(self, resume_key: str) -> Dict[str, Any]:
        """Evaluate education section."""
        gen = self.generated_map.get(resume_key, {})
        truth = self.ground_truth_map.get(resume_key, {})
        
        gen_edu = gen.get('education', [])
        truth_edu = truth.get('education', [])
        
        # Overall list comparison
        list_metrics = self._compare_lists(gen_edu, truth_edu, ['degree', 'university'])
        
        # Field-level accuracy
        field_accuracy = defaultdict(list)
        fields = ['degree', 'field', 'university', 'country', 'start', 'end', 'gpa']
        
        for truth_item in truth_edu:
            # Find best match in generated
            best_match = None
            best_score = 0.0
            
            for gen_item in gen_edu:
                score = (
                    self._compare_strings(gen_item.get('degree'), truth_item.get('degree')) +
                    self._compare_strings(gen_item.get('university'), truth_item.get('university'))
                ) / 2
                if score > best_score:
                    best_score = score
                    best_match = gen_item
            
            if best_match and best_score > 0.5:
                for field in fields:
                    field_type = 'date' if field in ['start', 'end'] else 'number' if field == 'gpa' else 'string'
                    acc = self._evaluate_field(best_match.get(field), truth_item.get(field), field_type)
                    field_accuracy[field].append(acc)
        
        # Calculate average field accuracy
        avg_field_accuracy = {}
        for field, scores in field_accuracy.items():
            avg_field_accuracy[field] = sum(scores) / len(scores) if scores else 0.0
        
        return {
            **list_metrics,
            'field_accuracy': avg_field_accuracy
        }
    
    def evaluate_experience(self, resume_key: str) -> Dict[str, Any]:
        """Evaluate experience section."""
        gen = self.generated_map.get(resume_key, {})
        truth = self.ground_truth_map.get(resume_key, {})
        
        gen_exp = gen.get('experience', [])
        truth_exp = truth.get('experience', [])
        
        # Overall list comparison
        list_metrics = self._compare_lists(gen_exp, truth_exp, ['title', 'org'])
        
        # Field-level accuracy
        field_accuracy = defaultdict(list)
        fields = ['title', 'org', 'start', 'end', 'domain', 'duration_months']
        
        for truth_item in truth_exp:
            # Find best match in generated
            best_match = None
            best_score = 0.0
            
            for gen_item in gen_exp:
                score = (
                    self._compare_strings(gen_item.get('title'), truth_item.get('title')) +
                    self._compare_strings(gen_item.get('org'), truth_item.get('org'))
                ) / 2
                if score > best_score:
                    best_score = score
                    best_match = gen_item
            
            if best_match and best_score > 0.5:
                for field in fields:
                    field_type = 'date' if field in ['start', 'end'] else 'number' if field == 'duration_months' else 'string'
                    acc = self._evaluate_field(best_match.get(field), truth_item.get(field), field_type)
                    field_accuracy[field].append(acc)
        
        # Calculate average field accuracy
        avg_field_accuracy = {}
        for field, scores in field_accuracy.items():
            avg_field_accuracy[field] = sum(scores) / len(scores) if scores else 0.0
        
        return {
            **list_metrics,
            'field_accuracy': avg_field_accuracy
        }
    
    def evaluate_publications(self, resume_key: str) -> Dict[str, Any]:
        """Evaluate publications section."""
        gen = self.generated_map.get(resume_key, {})
        truth = self.ground_truth_map.get(resume_key, {})
        
        gen_pubs = gen.get('publications', [])
        truth_pubs = truth.get('publications', [])
        
        return self._compare_lists(gen_pubs, truth_pubs, ['title', 'venue'])
    
    def evaluate_awards(self, resume_key: str) -> Dict[str, Any]:
        """Evaluate awards section."""
        gen = self.generated_map.get(resume_key, {})
        truth = self.ground_truth_map.get(resume_key, {})
        
        gen_awards = gen.get('awards', [])
        truth_awards = truth.get('awards', [])
        
        return self._compare_lists(gen_awards, truth_awards, ['title', 'issuer'])
    
    def evaluate_all(self) -> Dict[str, Any]:
        """
        Evaluate all resumes and calculate overall metrics.
        
        Returns:
            Dict containing detailed evaluation results
        """
        results = {
            'per_resume': {},
            'overall': {
                'name': [],
                'education': defaultdict(list),
                'experience': defaultdict(list),
                'publications': defaultdict(list),
                'awards': defaultdict(list)
            }
        }
        
        # Get all resume keys
        all_keys = set(self.generated_map.keys()) | set(self.ground_truth_map.keys())
        
        for key in all_keys:
            resume_results = {}
            
            # Evaluate each section
            name_eval = self.evaluate_name(key)
            edu_eval = self.evaluate_education(key)
            exp_eval = self.evaluate_experience(key)
            pub_eval = self.evaluate_publications(key)
            award_eval = self.evaluate_awards(key)
            
            resume_results['name'] = name_eval
            resume_results['education'] = edu_eval
            resume_results['experience'] = exp_eval
            resume_results['publications'] = pub_eval
            resume_results['awards'] = award_eval
            
            results['per_resume'][key] = resume_results
            
            # Aggregate for overall metrics
            results['overall']['name'].append(name_eval['accuracy'])
            
            for metric in ['precision', 'recall', 'f1']:
                results['overall']['education'][metric].append(edu_eval[metric])
                results['overall']['experience'][metric].append(exp_eval[metric])
                results['overall']['publications'][metric].append(pub_eval[metric])
                results['overall']['awards'][metric].append(award_eval[metric])
        
        # Calculate overall averages
        results['overall']['name_avg'] = sum(results['overall']['name']) / len(results['overall']['name']) if results['overall']['name'] else 0.0
        
        for section in ['education', 'experience', 'publications', 'awards']:
            for metric in ['precision', 'recall', 'f1']:
                values = results['overall'][section][metric]
                results['overall'][section][f'{metric}_avg'] = sum(values) / len(values) if values else 0.0
        
        return results
    
    def print_report(self, results: Dict[str, Any]):
        """Print a formatted evaluation report."""
        print("=" * 80)
        print("RESUME PARSING EVALUATION REPORT")
        print("=" * 80)
        print()
        
        print(f"Total Resumes Evaluated: {len(results['per_resume'])}")
        print(f"Generated Resumes: {len(self.generated)}")
        print(f"Ground Truth Resumes: {len(self.ground_truth)}")
        print()
        
        print("-" * 80)
        print("OVERALL METRICS")
        print("-" * 80)
        
        # Name accuracy
        print(f"\nName Extraction:")
        print(f"  Accuracy: {results['overall']['name_avg']:.2%}")
        
        # Section metrics
        sections = ['education', 'experience', 'publications', 'awards']
        for section in sections:
            print(f"\n{section.title()}:")
            metrics = results['overall'][section]
            print(f"  Precision: {metrics['precision_avg']:.2%}")
            print(f"  Recall:    {metrics['recall_avg']:.2%}")
            print(f"  F1 Score:  {metrics['f1_avg']:.2%}")
        
        print()
        print("-" * 80)
        print("PER-RESUME RESULTS")
        print("-" * 80)
        
        for resume_key, resume_result in results['per_resume'].items():
            print(f"\nResume: {resume_key}")
            print(f"  Name: {resume_result['name']['accuracy']:.2%} - '{resume_result['name']['generated']}' vs '{resume_result['name']['truth']}'")
            
            for section in sections:
                metrics = resume_result[section]
                print(f"  {section.title()}: P={metrics['precision']:.2%}, R={metrics['recall']:.2%}, F1={metrics['f1']:.2%}")
                if 'field_accuracy' in metrics and metrics['field_accuracy']:
                    print(f"    Field Accuracy: {', '.join([f'{k}={v:.2%}' for k, v in metrics['field_accuracy'].items()])}")
        
        print()
        print("=" * 80)


def main():
    """Main function to run evaluation."""
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python evaluate.py <generated_json> <ground_truth_json>")
        print("\nExample:")
        print("  python evaluate.py results/parsed.json ground_truth/truth.json")
        sys.exit(1)
    
    generated_path = sys.argv[1]
    ground_truth_path = sys.argv[2]
    
    if not os.path.exists(generated_path):
        print(f"Error: Generated JSON not found: {generated_path}")
        sys.exit(1)
    
    if not os.path.exists(ground_truth_path):
        print(f"Error: Ground truth JSON not found: {ground_truth_path}")
        sys.exit(1)
    
    # Run evaluation
    evaluator = ResumeEvaluator(generated_path, ground_truth_path)
    results = evaluator.evaluate_all()
    evaluator.print_report(results)
    
    # Optionally save detailed results
    output_path = "evaluation_results.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nDetailed results saved to: {output_path}")


if __name__ == '__main__':
    main()
