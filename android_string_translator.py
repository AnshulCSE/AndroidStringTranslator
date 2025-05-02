#!/usr/bin/env python3
"""
Android String Translator - Main CLI Application

This script automates the translation of Android string resources into multiple languages.
It parses XML string resources, uses a built-in dictionary-based translation system,
and generates properly formatted translated files.
"""

import os
import sys
import logging
from pathlib import Path
import click
from datetime import datetime

from translator.parser import StringResourceParser
from translator.api_client import FreeTranslateClient, DictionaryTranslator
from translator.writer import StringResourceWriter
from translator.utils import setup_logging, get_language_codes, print_summary

# Setup logging
logger = logging.getLogger(__name__)


@click.group()
@click.option('--debug/--no-debug', default=False, help='Enable debug logging')
@click.option('--log-file', default=None, help='Path to log file')
def cli(debug, log_file):
    """Android String Resources Translator

    This tool automates the translation of Android string resources (.xml) into multiple languages
    using a built-in dictionary-based translation system that doesn't require any external APIs.
    """
    log_level = logging.DEBUG if debug else logging.INFO
    setup_logging(log_level, log_file)


@cli.command()
@click.option('--source', '-s', required=True, help='Source strings.xml file path')
@click.option('--output-dir', '-o', required=True, help='Output directory for translated files')
@click.option('--languages', '-l', required=True, help='Comma-separated list of target language codes (e.g., fr,es,de)')
@click.option('--api', '-a', type=click.Choice(['free', 'dictionary']), default='free', 
          help='Translation method to use (both are free and offline)')
@click.option('--skip-existing/--overwrite-existing', default=True, help='Skip already translated strings')
@click.option('--preserve-comments/--no-preserve-comments', default=True, help='Preserve comments in XML files')
def translate(source, output_dir, languages, api, skip_existing, preserve_comments):
    """Translate Android string resources to multiple languages."""
    try:
        source_path = Path(source)
        if not source_path.exists():
            click.echo(f"Error: Source file '{source}' does not exist", err=True)
            sys.exit(1)

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Parse language codes
        target_languages = get_language_codes(languages)
        
        click.echo(f"Starting translation of {source} to {len(target_languages)} languages")
        
        # Parse source strings
        parser = StringResourceParser(preserve_comments=preserve_comments)
        string_resources = parser.parse(source_path)
        
        click.echo(f"Parsed {len(string_resources.strings)} strings from source file")
        
        # Setup translation client
        if api == 'free':
            translator = FreeTranslateClient()
        else:  # dictionary
            translator = DictionaryTranslator()
        
        # Writer for saving translated files
        writer = StringResourceWriter()
        
        # Process each target language
        stats = {}
        for lang in target_languages:
            click.echo(f"Translating to {lang}...")
            
            # Determine the output file path
            if lang == 'en':
                out_file = output_path / "values" / "strings.xml"
            else:
                out_file = output_path / f"values-{lang}" / "strings.xml"
            
            # Create parent directory if it doesn't exist
            out_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Check for existing translations if skip_existing is enabled
            existing_strings = {}
            if skip_existing and out_file.exists():
                try:
                    existing_resource = parser.parse(out_file)
                    existing_strings = {s.name: s for s in existing_resource.strings}
                    click.echo(f"Found {len(existing_strings)} existing translations in {out_file}")
                except Exception as e:
                    logger.warning(f"Failed to parse existing translations from {out_file}: {e}")
            
            # Translate strings
            translated_resource = string_resources.create_copy_for_translation(lang)
            
            # Collect strings that need translation
            to_translate = []
            for string in translated_resource.strings:
                if not string.translatable or (skip_existing and string.name in existing_strings):
                    if string.name in existing_strings:
                        string.value = existing_strings[string.name].value
                    continue
                to_translate.append(string)
            
            # Perform translation if there are strings to translate
            if to_translate:
                result = translator.translate_batch([s.value for s in to_translate], lang)
                
                # Update string values with translations
                for string, translation in zip(to_translate, result):
                    string.value = translation
            
            # Write the translated strings to the output file
            writer.write(translated_resource, out_file)
            
            # Record statistics
            stats[lang] = {
                'total': len(translated_resource.strings),
                'translated': len(to_translate),
                'skipped': len(existing_strings) if skip_existing else 0
            }
            
            click.echo(f"✓ Successfully translated to {lang} and saved to {out_file}")
        
        # Print summary
        print_summary(stats)
        
    except Exception as e:
        logger.error(f"Translation failed: {e}", exc_info=True)
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
def list_languages():
    """List all supported language codes."""
    click.echo("Supported language codes:")
    
    global_langs = sorted([
        "en", "fr", "es", "de", "it", "pt", "zh", "zh-CN", "zh-TW", 
        "ja", "ko", "ru", "nl", "pt-BR"
    ])
    
    indian_langs = sorted([
        "hi", "bn", "mr", "ta", "te", "kn", "ml", "gu", "pa", "or", "as"
    ])
    
    click.echo("Global languages:")
    for code in global_langs:
        click.echo(f"  {code}")
        
    click.echo("\nIndian languages:")
    for code in indian_langs:
        click.echo(f"  {code}")

def post_process_translations(translations):
    """
    Post-process translated strings to clean up formatting issues.
    For example, ensure proper spacing around punctuation.
    """
    processed = []
    for text in translations:
        # Add a space after punctuation if missing
        text = text.replace(". ", ".").replace(".", ". ")
        text = text.replace(", ", ",").replace(",", ", ")
        text = text.replace("! ", "!").replace("!", "! ")
        text = text.replace("? ", "?").replace("?", "? ")
        # Remove extra spaces
        text = " ".join(text.split())
        processed.append(text)
    return processed

if __name__ == '__main__':
    cli()
