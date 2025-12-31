"""
Quick runner for the Goal Setting Crew
Run this file directly to start the goal setting conversation
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from goal_setting_crew.main import run

if __name__ == "__main__":
    run()
