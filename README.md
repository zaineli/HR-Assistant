# Resume Parser & Evaluator# Resume Processing Pipeline# Resume Parser Backend



## Setup



```bash## SetupAn intelligent resume parsing system that extracts structured information from resumes in multiple formats (PDF, DOCX, PNG, JPG) using OCR and Google's Gemini API.

python -m venv venv

source venv/bin/activate  # On Windows: venv\Scripts\activate

pip install -r requirements.txt

``````bash## Features



Configure `.env` with your Google Gemini API key:python -m venv venv

```

GOOGLE_API_KEY=your_key_heresource venv/bin/activate  # Linux/Mac- **Multi-format Support**: Handles PDF, DOCX, PNG, JPG, and JPEG files

RAW_DIR=data/input/CVs

FINAL_JSON=data/output/results/parsed.json# venv\Scripts\activate   # Windows- **Advanced OCR**: High-quality text extraction using Tesseract with image preprocessing

LOG_FILE=logs/logs.txt

```pip install -r requirements.txt- **AI-Powered Parsing**: Uses Google Gemini API to structure resume data



## Usage```- **Comprehensive Logging**: Detailed pipeline logs for debugging and monitoring



```bash- **PII Protection**: Automatic redaction of emails and phone numbers

python pipeline.py --ground-truth config/ground_truth/sample_truth.json

```Create `.env` file:- **Smart Duration Calculation**: Automatically calculates work experience duration in months



Results saved to `data/output/results/` and `pipeline_results.txt````- **Evaluation System**: Calculate precision, recall, F1 scores against ground truth


GOOGLE_API_KEY=your_api_key_here

```## Supported File Formats



## Usage- **PDF** (`.pdf`) - Text-based and scanned/image-based PDFs

- **Word Documents** (`.docx`)

### Basic Processing (without evaluation)- **Images** (`.png`, `.jpg`, `.jpeg`)

```bash

python pipeline.py## Output Format

```

The system generates a JSON file with the following structure for each resume:

### With Evaluation

```bash```json

python pipeline.py --ground-truth ground_truth/sample_truth.json[

```  {

    "name": "resume.pdf",

### Custom Options    "education": [

```bash      {

python pipeline.py \        "degree": "BS.",

  --input-dir CVs \        "field": "Computer Science",

  --output-dir results \        "university": "University Name",

  --ground-truth ground_truth/truth.json \        "country": "Country",

  --config evaluation_config.json \        "start": "Sept 2022",

  --log-file pipeline_results.txt        "end": "Jun 2026",

```        "gpa": "3.5",

        "scale": null

## Output      }

    ],

- `results/parsed.json` - Parsed resume data    "experience": [

- `results/evaluation_results.json` - Standard metrics (P/R/F1)      {

- `results/weighted_evaluation_results.json` - Quality scores        "title": "Job Title",

- `results/ranked_evaluation_results.json` - Rankings & comparisons        "org": "Organization",

- `pipeline_results.txt` - Complete text summary        "start": "June 2024",

        "end": "currently working",

## Directory Structure        "duration_months": 17,

        "domain": "Domain"

```      }

backend/    ],

├── CVs/                    # Input: Place resumes here    "publications": [],

├── ground_truth/           # Ground truth for evaluation    "awards": []

├── results/                # Output: Parsed & evaluated results  }

├── pipeline.py             # Main pipeline script]

├── evaluation_config.json  # Weights & policies```

└── pipeline_results.txt    # Complete results log

```## Prerequisites



## Configuration### System Requirements



Edit `evaluation_config.json` to adjust:1. **Python 3.8+**

- Component weights (education, experience, publications, etc.)2. **Tesseract OCR** - Required for text extraction from images

- Subweights (GPA, degree level, university tier)

- Policies (domain, experience bonus threshold)#### Installing Tesseract



## Individual Scripts**On Ubuntu/Debian:**

```bash

If needed, run components separately:sudo apt-get update

sudo apt-get install tesseract-ocr

```bash```

# Parse only

python run.py**On macOS:**

```bash

# Standard evaluation onlybrew install tesseract

python evaluate.py results/parsed.json ground_truth/truth.json```



# Weighted evaluation only**On Windows:**

python weighted_evaluate.py results/parsed.json ground_truth/truth.json- Download installer from: https://github.com/UB-Mannheim/tesseract/wiki

- Add Tesseract to PATH or set path in `extraction.py`

# Ranked evaluation only

python ranked_evaluate.py results/parsed.json ground_truth/truth.json### API Keys

```

- **Google Gemini API Key**: Get from https://ai.google.dev/

## Installation

1. **Clone the repository** (if not already done):
```bash
cd backend
```

2. **Create a virtual environment** (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install Python dependencies**:
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**:
```bash
cp .env.example .env
```

Edit `.env` and set your values:
```env
RAW_DIR=CVs
FINAL_JSON=results/parsed.json
LOG_FILE=logs/logs.txt
GOOGLE_API_KEY=your_actual_api_key_here
```

5. **Create necessary directories**:
```bash
mkdir -p CVs logs results
```

## Usage

### Running the Pipeline

1. **Place resume files** in the `CVs` directory (or your configured `RAW_DIR`)

2. **Run the pipeline**:
```bash
python -m backend.main
```

Or if running from parent directory:
```bash
python -m backend.main
```

3. **Check results**:
   - **Parsed data**: `results/parsed.json`
   - **Detailed logs**: `logs/logs.txt`

### Understanding the Pipeline

The pipeline processes resumes in these steps:

1. **File Detection**: Scans the input directory for supported files
2. **Text Extraction**:
   - PDF: Direct text extraction or OCR for scanned pages
   - DOCX: Direct text extraction
   - Images: OCR with advanced preprocessing
3. **Image Preprocessing** (for images and scanned PDFs):
   - Grayscale conversion
   - Noise removal
   - Deskewing
   - Adaptive thresholding
   - Contrast enhancement
4. **Text Cleaning**:
   - PII redaction (emails, phone numbers)
   - Unicode normalization
   - Whitespace cleanup
5. **AI Parsing**: Gemini API structures the text into JSON
6. **Duration Calculation**: Calculates work experience durations
7. **Output Generation**: Saves final JSON with all results

## Evaluation System

### Comparing Results with Ground Truth

The evaluation system calculates comprehensive metrics to assess parser accuracy:

#### Running Evaluation

```bash
# Compare generated results with ground truth
python evaluate.py results/parsed.json ground_truth/truth.json

# Or run the demo
python demo_evaluation.py
```

#### Metrics Calculated

1. **Name Extraction Accuracy**: Percentage of correctly extracted names
2. **Section Metrics** (Education, Experience, Publications, Awards):
   - **Precision**: How many extracted items are correct
   - **Recall**: How many ground truth items were found
   - **F1 Score**: Harmonic mean of precision and recall
3. **Field-Level Accuracy**: Per-field accuracy for matched items

#### Example Output

```
OVERALL METRICS
Name Extraction:  95.00%
Education F1:     100.00%
Experience F1:    92.44%
Publications F1:  100.00%
Awards F1:        100.00%
```

#### Creating Ground Truth

Create a JSON file matching your generated structure with correct values:

```json
[
  {
    "filename": "resume.pdf",
    "name": "Correct Person Name",
    "education": [...],
    "experience": [...],
    "publications": [],
    "awards": []
  }
]
```

See `EVALUATION_README.md` for detailed documentation.

## Project Structure

```
backend/
├── __init__.py              # Package initialization
├── main.py                  # Main pipeline orchestrator
├── config.py                # Configuration loader
├── extraction.py            # Text extraction (PDF, DOCX, images)
├── image_processing.py      # Image preprocessing utilities
├── cleaning.py              # Text cleaning and normalization
├── parsing.py               # Gemini API integration
├── logging_utils.py         # Logging utilities
├── requirements.txt         # Python dependencies
├── .env.example             # Environment template
├── README.md               # This file
├── CVs/                    # Input resume files
├── logs/                   # Pipeline logs
└── results/                # Output JSON files
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `RAW_DIR` | Directory containing resume files | `CVs` |
| `FINAL_JSON` | Output JSON file path | `results/parsed.json` |
| `LOG_FILE` | Log file path | `logs/logs.txt` |
| `GOOGLE_API_KEY` | Gemini API key | Required |

### OCR Configuration

The OCR system uses:
- **Engine**: Tesseract OCR
- **Mode**: Automatic page segmentation (PSM 3)
- **Language**: English (configurable in `extraction.py`)
- **DPI**: 300 for PDF rendering

For better accuracy with specific languages, edit the `lang` parameter in `extraction.py`:
```python
text = pytesseract.image_to_string(processed_img, lang='eng+fra')  # English + French
```

## Troubleshooting

### Common Issues

1. **"Tesseract not found"**
   - Ensure Tesseract is installed and in PATH
   - On Windows, set the path explicitly in `extraction.py`

2. **Poor OCR quality**
   - Ensure images are high resolution (300 DPI minimum)
   - Check if images are properly oriented
   - Adjust preprocessing parameters in `image_processing.py`

3. **Gemini API errors**
   - Verify API key is correct
   - Check API quota limits
   - Review error messages in logs

4. **Empty extraction results**
   - Check log file for specific errors
   - Verify file is not corrupted
   - Ensure file format is supported

### Viewing Logs

Detailed logs are saved to `logs/logs.txt`. Each entry includes:
- Timestamp
- File being processed
- Pipeline step
- Success/error messages

```bash
# View recent logs
tail -f backend/logs/logs.txt

# Search for errors
grep "ERROR" backend/logs/logs.txt
```

## Advanced Usage

### Processing Specific Files

You can modify `main.py` to process specific files:

```python
files = ['resume1.pdf', 'resume2.png']  # Instead of os.listdir(RAW_DIR)
```

### Batch Processing

For large batches, consider:
1. Processing files in chunks
2. Implementing parallel processing
3. Adding retry logic for API failures

### Custom Fields

To extract additional fields, modify the prompt in `parsing.py`:

```python
prompt = f"""
Extract structured CV information including:
- Education
- Experience
- Skills  # Add this
- Certifications  # Add this
...
"""
```

## Performance Considerations

- **OCR Processing**: Image processing is CPU-intensive
- **API Calls**: Gemini API has rate limits
- **Memory**: Large PDFs may require significant RAM

Typical processing times:
- PDF (text-based): 2-5 seconds
- PDF (scanned): 10-30 seconds per page
- Images: 5-15 seconds
- DOCX: 1-2 seconds

## License

This project is part of the llmproject repository.

## Support

For issues or questions:
1. Check the logs in `logs/logs.txt`
2. Review troubleshooting section
3. Verify all dependencies are installed correctly
