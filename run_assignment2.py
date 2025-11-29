#!/usr/bin/env python3
"""
Quick start script for Assignment 2 Enhanced Evaluation
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.evaluation.enhanced_evaluation import main

if __name__ == '__main__':
    main()
