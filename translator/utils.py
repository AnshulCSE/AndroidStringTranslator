"""
Utility functions for Android string resource translation.
"""

import logging
import os
import sys
from datetime import datetime
from typing import List, Dict, Any
import click


def setup_logging(log_level: int = logging.INFO, log_file: str = None) -> None:
    """
    Set up logging for the application.
    
    Args:
        log_level: Logging level (e.g., logging.INFO, logging.DEBUG)
        log_file: Path to log file, if None, logs will only go to console
    """
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create handlers
    handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)
    
    # File handler if log_file is specified
    if log_file:
        # If log_file doesn't specify a timestamp, add one
        if not _has_timestamp(log_file):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_file = f"{os.path.splitext(log_file)[0]}_{timestamp}{os.path.splitext(log_file)[1]}"
        
        # Create directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        force=True  # Override any existing configuration
    )


def _has_timestamp(filename: str) -> bool:
    """Check if a filename already contains a timestamp."""
    import re
    return bool(re.search(r'\d{8}_\d{6}', filename))


def get_language_codes(languages_str: str) -> List[str]:
    """
    Parse a comma-separated list of language codes.
    
    Args:
        languages_str: Comma-separated language codes (e.g., 'en,fr,de')
        
    Returns:
        List of language codes
    """
    langs = [lang.strip() for lang in languages_str.split(',') if lang.strip()]
    if not langs:
        raise ValueError("No valid language codes provided")
    return langs


def print_summary(stats: Dict[str, Dict[str, int]]) -> None:
    """
    Print a summary of the translation process.
    
    Args:
        stats: Dictionary with language codes as keys and statistics as values
    """
    click.echo("\n===== Translation Summary =====")
    click.echo(f"Translated to {len(stats)} languages:")
    
    for lang, lang_stats in sorted(stats.items()):
        total = lang_stats.get('total', 0)
        translated = lang_stats.get('translated', 0)
        skipped = lang_stats.get('skipped', 0)
        
        click.echo(f"  {lang}: {total} strings total, {translated} translated, {skipped} skipped")
    
    click.echo("=============================")


def format_duration(seconds: float) -> str:
    """Format a duration in seconds to a human-readable string."""
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{int(minutes)} minutes, {int(secs)} seconds"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{int(hours)} hours, {int(minutes)} minutes"
