"""
Complete Resume Processing Pipeline
Processes resumes → Parses → Evaluates → Logs results
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Import pipeline components
from src.extraction.extraction import extract_text_pdf, extract_text_docx, extract_text_image
from src.processing.cleaning import clean_whitespace, redact_pii, normalize_text
from src.processing.parsing import parse_cv_with_gemini
from src.logging_utils import log_step
from src.evaluation.evaluate import ResumeEvaluator
from src.evaluation.weighted_evaluate import WeightedResumeEvaluator
from src.evaluation.ranked_evaluate import RankedResumeEvaluator


class ResumePipeline:
    """Complete resume processing pipeline."""
    
    SUPPORTED_EXTENSIONS = {
        '.pdf': extract_text_pdf,
        '.docx': extract_text_docx,
        '.png': extract_text_image,
        '.jpg': extract_text_image,
        '.jpeg': extract_text_image
    }
    
    def __init__(self, 
                 input_dir: str = "data/input/CVs",
                 output_dir: str = "data/output/results",
                 ground_truth_path: str = None,
                 config_path: str = "config/evaluation_config.json",
                 log_file: str = "pipeline_results.txt"):
        """
        Initialize pipeline.
        
        Args:
            input_dir: Directory containing resumes
            output_dir: Directory for output files
            ground_truth_path: Path to ground truth JSON (optional)
            config_path: Path to evaluation config
            log_file: Path to results log file
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.ground_truth_path = ground_truth_path
        self.config_path = config_path
        self.log_file = Path(log_file)
        
        # Create directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Results storage
        self.parsed_results = []
        self.evaluation_results = {}
        self.pipeline_log = []
        
    def log(self, message: str, level: str = "INFO"):
        """Log message to both console and internal log."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(log_entry)
        self.pipeline_log.append(log_entry)
        log_step(message)
    
    def get_resume_files(self) -> List[Path]:
        """Get all supported resume files from input directory."""
        files = []
        for ext in self.SUPPORTED_EXTENSIONS.keys():
            files.extend(self.input_dir.glob(f"*{ext}"))
        return sorted(files)
    
    def extract_text(self, file_path: Path) -> str:
        """Extract text from resume file."""
        ext = file_path.suffix.lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {ext}")
        
        extractor = self.SUPPORTED_EXTENSIONS[ext]
        
        self.log(f"Extracting text from {file_path.name}...")
        text = extractor(str(file_path), file_path.name)
        self.log(f"Extracted {len(text)} characters from {file_path.name}")
        
        return text
    
    def process_text(self, text: str, filename: str) -> str:
        """Clean and normalize extracted text."""
        self.log(f"Processing text for {filename}...")
        
        # Clean whitespace
        cleaned = clean_whitespace(text)
        
        # Redact PII
        redacted = redact_pii(cleaned)
        
        # Normalize
        normalized = normalize_text(redacted)
        
        self.log(f"Text processing complete for {filename}")
        return normalized
    
    def parse_resume(self, text: str, filename: str) -> Dict[str, Any]:
        """Parse resume using Gemini API."""
        self.log(f"Parsing {filename} with Gemini API...")
        
        try:
            parsed = parse_cv_with_gemini(text)
            # Add filename if not present
            if 'filename' not in parsed:
                parsed['filename'] = filename
            self.log(f"Successfully parsed {filename}")
            return parsed
        except Exception as e:
            self.log(f"Error parsing {filename}: {str(e)}", "ERROR")
            return {
                "filename": filename,
                "name": "",
                "education": [],
                "experience": [],
                "publications": [],
                "awards": [],
                "error": str(e)
            }
    
    def process_all_resumes(self) -> List[Dict[str, Any]]:
        """Process all resumes in input directory."""
        self.log("=" * 80)
        self.log("STARTING RESUME PROCESSING PIPELINE")
        self.log("=" * 80)
        
        files = self.get_resume_files()
        self.log(f"Found {len(files)} resume(s) to process")
        
        results = []
        
        for i, file_path in enumerate(files, 1):
            self.log("")
            self.log(f"Processing resume {i}/{len(files)}: {file_path.name}")
            self.log("-" * 80)
            
            try:
                # Extract
                text = self.extract_text(file_path)
                
                # Process
                processed_text = self.process_text(text, file_path.name)
                
                # Parse
                parsed = self.parse_resume(processed_text, file_path.name)
                
                results.append(parsed)
                self.log(f"✓ Successfully processed {file_path.name}")
                
            except Exception as e:
                self.log(f"✗ Failed to process {file_path.name}: {str(e)}", "ERROR")
                results.append({
                    "filename": file_path.name,
                    "name": "",
                    "education": [],
                    "experience": [],
                    "publications": [],
                    "awards": [],
                    "error": str(e)
                })
        
        self.parsed_results = results
        
        # Save parsed results
        parsed_output = self.output_dir / "parsed.json"
        with open(parsed_output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        self.log("")
        self.log(f"Saved parsed results to {parsed_output}")
        self.log(f"Successfully processed {len(results)} resume(s)")
        
        return results
    
    def run_evaluation(self):
        """Run evaluation if ground truth is provided."""
        if not self.ground_truth_path:
            self.log("")
            self.log("No ground truth provided, skipping evaluation")
            return
        
        if not os.path.exists(self.ground_truth_path):
            self.log(f"Ground truth file not found: {self.ground_truth_path}", "WARNING")
            return
        
        parsed_path = self.output_dir / "parsed.json"
        
        self.log("")
        self.log("=" * 80)
        self.log("STARTING EVALUATION")
        self.log("=" * 80)
        
        try:
            # Standard evaluation
            self.log("")
            self.log("Running standard evaluation (Precision/Recall/F1)...")
            std_evaluator = ResumeEvaluator(str(parsed_path), self.ground_truth_path)
            std_results = std_evaluator.evaluate_all()
            
            std_output = self.output_dir / "evaluation_results.json"
            with open(std_output, 'w', encoding='utf-8') as f:
                json.dump(std_results, f, indent=2, ensure_ascii=False)
            self.log(f"Standard evaluation saved to {std_output}")
            
            # Weighted evaluation
            self.log("")
            self.log("Running weighted evaluation (Quality scoring)...")
            weighted_evaluator = WeightedResumeEvaluator(
                str(parsed_path), 
                self.ground_truth_path,
                self.config_path
            )
            weighted_results = weighted_evaluator.evaluate_all()
            
            weighted_output = self.output_dir / "weighted_evaluation_results.json"
            with open(weighted_output, 'w', encoding='utf-8') as f:
                json.dump(weighted_results, f, indent=2, ensure_ascii=False)
            self.log(f"Weighted evaluation saved to {weighted_output}")
            
            # Ranked evaluation
            self.log("")
            self.log("Running ranked evaluation (Rankings & Comparisons)...")
            ranked_evaluator = RankedResumeEvaluator(
                str(parsed_path),
                self.ground_truth_path,
                self.config_path
            )
            ranked_results = ranked_evaluator.evaluate_all_with_ranking()
            
            ranked_output = self.output_dir / "ranked_evaluation_results.json"
            with open(ranked_output, 'w', encoding='utf-8') as f:
                json.dump(ranked_results, f, indent=2, ensure_ascii=False)
            self.log(f"Ranked evaluation saved to {ranked_output}")
            
            # Store for summary
            self.evaluation_results = {
                'standard': std_results,
                'weighted': weighted_results,
                'ranked': ranked_results
            }
            
            self.log("")
            self.log("✓ Evaluation complete")
            
        except Exception as e:
            self.log(f"Error during evaluation: {str(e)}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
    
    def generate_summary(self) -> str:
        """Generate text summary of all results."""
        lines = []
        lines.append("=" * 80)
        lines.append("RESUME PROCESSING PIPELINE - COMPLETE RESULTS")
        lines.append("=" * 80)
        lines.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # Processing summary
        lines.append("-" * 80)
        lines.append("PARSING RESULTS")
        lines.append("-" * 80)
        lines.append(f"Total Resumes Processed: {len(self.parsed_results)}")
        lines.append("")
        
        for i, result in enumerate(self.parsed_results, 1):
            lines.append(f"{i}. {result.get('filename', 'Unknown')}")
            lines.append(f"   Name: {result.get('name', 'Not extracted')}")
            lines.append(f"   Education: {len(result.get('education', []))} entries")
            lines.append(f"   Experience: {len(result.get('experience', []))} entries")
            lines.append(f"   Publications: {len(result.get('publications', []))} entries")
            lines.append(f"   Awards: {len(result.get('awards', []))} entries")
            if 'error' in result:
                lines.append(f"   ERROR: {result['error']}")
            lines.append("")
        
        # Evaluation summary
        if self.evaluation_results:
            lines.append("-" * 80)
            lines.append("EVALUATION RESULTS")
            lines.append("-" * 80)
            lines.append("")
            
            # Standard metrics
            if 'standard' in self.evaluation_results:
                std = self.evaluation_results['standard']
                lines.append("Standard Evaluation (Precision/Recall/F1):")
                overall = std.get('overall', {})
                
                # Calculate weighted average across all sections
                sections = ['education', 'experience', 'publications', 'awards']
                total_precision = 0
                total_recall = 0
                total_f1 = 0
                section_count = 0
                
                for section in sections:
                    if section in overall:
                        section_data = overall[section]
                        if f'{section.rstrip("s")}_avg' in section_data or 'precision_avg' in section_data:
                            # Handle both naming conventions
                            prec = section_data.get('precision_avg', section_data.get(f'precision', 0))
                            rec = section_data.get('recall_avg', section_data.get(f'recall', 0))
                            f1 = section_data.get('f1_avg', section_data.get(f'f1', 0))
                            
                            total_precision += prec
                            total_recall += rec
                            total_f1 += f1
                            section_count += 1
                
                # Calculate averages
                avg_precision = total_precision / section_count if section_count > 0 else 0
                avg_recall = total_recall / section_count if section_count > 0 else 0
                avg_f1 = total_f1 / section_count if section_count > 0 else 0
                
                lines.append(f"  Overall Precision: {avg_precision:.1%}")
                lines.append(f"  Overall Recall:    {avg_recall:.1%}")
                lines.append(f"  Overall F1 Score:  {avg_f1:.1%}")
                lines.append("")
            
            # Weighted scores
            if 'weighted' in self.evaluation_results:
                weighted = self.evaluation_results['weighted']
                lines.append("Weighted Evaluation (Quality Scoring):")
                agg = weighted.get('aggregate', {})
                lines.append(f"  Education Score:   {agg.get('education_avg', 0):.1%}")
                lines.append(f"  Experience Score:  {agg.get('experience_avg', 0):.1%}")
                lines.append(f"  Publications:      {agg.get('publications_avg', 0):.1%}")
                lines.append(f"  Coherence:         {agg.get('coherence_avg', 0):.1%}")
                lines.append(f"  Awards:            {agg.get('awards_avg', 0):.1%}")
                lines.append(f"  Overall Score:     {agg.get('final_scores_avg', 0):.1%}")
                lines.append("")
            
            # Rankings
            if 'ranked' in self.evaluation_results:
                ranked = self.evaluation_results['ranked']
                rankings = ranked.get('rankings', [])
                
                lines.append("Candidate Rankings:")
                lines.append(f"{'Rank':<6} {'Score':<10} {'Grade':<8} {'Candidate'}")
                lines.append("-" * 80)
                
                for rank, (key, score, grade) in enumerate(rankings, 1):
                    lines.append(f"{rank:<6} {score:>8.1%} {grade:<8} {key}")
                lines.append("")
                
                # Top comparison
                comparisons = ranked.get('comparisons', [])
                if comparisons:
                    lines.append("Top Comparison (Rank #1 vs #2):")
                    comp = comparisons[0]
                    lines.append(f"  {comp['resume_a']['name']} ({comp['resume_a']['score']:.1%}) vs")
                    lines.append(f"  {comp['resume_b']['name']} ({comp['resume_b']['score']:.1%})")
                    lines.append(f"  Score Difference: +{comp['deltas']['final_score']['delta_pct']:.1f}pp")
                    lines.append("")
                    lines.append("  Top 3 Reasons:")
                    for i, reason in enumerate(comp['top_reasons'][:3], 1):
                        lines.append(f"    {i}. {reason['component']}: {reason['reason']}")
                        lines.append(f"       Impact: {reason['weighted_impact']:+.1%}")
                    lines.append("")
        
        # Pipeline log
        lines.append("-" * 80)
        lines.append("PIPELINE LOG")
        lines.append("-" * 80)
        for log_entry in self.pipeline_log:
            lines.append(log_entry)
        lines.append("")
        
        lines.append("=" * 80)
        lines.append("END OF REPORT")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def save_results(self):
        """Save complete results to text file."""
        summary = self.generate_summary()
        
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(summary)
        
        self.log("")
        self.log("=" * 80)
        self.log(f"Complete results saved to {self.log_file}")
        self.log("=" * 80)
    
    def run(self):
        """Run complete pipeline."""
        try:
            # Process resumes
            self.process_all_resumes()
            
            # Run evaluation
            self.run_evaluation()
            
            # Save results
            self.save_results()
            
            self.log("")
            self.log("✓ Pipeline completed successfully")
            
            return True
            
        except Exception as e:
            self.log(f"Pipeline failed: {str(e)}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
            
            # Save partial results
            self.save_results()
            
            return False


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Complete Resume Processing Pipeline")
    parser.add_argument(
        '--input-dir',
        default='data/input/CVs',
        help='Directory containing resumes (default: data/input/CVs)'
    )
    parser.add_argument(
        '--output-dir',
        default='data/output/results',
        help='Output directory (default: data/output/results)'
    )
    parser.add_argument(
        '--ground-truth',
        help='Path to ground truth JSON file (optional)'
    )
    parser.add_argument(
        '--config',
        default='config/evaluation_config.json',
        help='Path to evaluation config (default: config/evaluation_config.json)'
    )
    parser.add_argument(
        '--log-file',
        default='pipeline_results.txt',
        help='Output log file (default: pipeline_results.txt)'
    )
    
    args = parser.parse_args()
    
    # Create and run pipeline
    pipeline = ResumePipeline(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        ground_truth_path=args.ground_truth,
        config_path=args.config,
        log_file=args.log_file
    )
    
    success = pipeline.run()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

# run with: python pipeline.py --ground-truth config/ground_truth/sample_truth.json