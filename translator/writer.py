"""
XML Writer for Android string resources.

This module handles writing translated string resources to XML files.
"""

import logging
import xml.dom.minidom as minidom
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Optional, List

from translator.parser import StringResourceFile, StringResource, XMLComment

logger = logging.getLogger(__name__)


class StringResourceWriter:
    """Writer for Android string resource XML files."""
    
    def __init__(self):
        """Initialize the writer."""
        pass
    
    def write(self, resource_file: StringResourceFile, output_path: Path) -> None:
        """
        Write the string resources to an XML file.
        
        Args:
            resource_file: StringResourceFile object containing the resources to write
            output_path: Path where the XML file should be written
        """
        logger.info(f"Writing {len(resource_file.strings)} strings to {output_path}")
        
        # Create parent directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create the XML structure
        root = ET.Element('resources')
        
        # Add all elements in order
        for element in resource_file.elements:
            if isinstance(element, StringResource):
                string_elem = ET.SubElement(root, 'string')
                string_elem.set('name', element.name)
                
                # Add other attributes (except 'name' which we already handled)
                for attr_name, attr_value in element.attributes.items():
                    if attr_name != 'name':
                        string_elem.set(attr_name, attr_value)
                
                # Clean up the value, especially for Indian languages
                cleaned_value = self._cleanup_text_for_xml(element.value, resource_file.language_code)
                
                # Handle special case for strings with XML content
                if '<' in cleaned_value and '>' in cleaned_value:
                    # Check if it looks like XML content
                    if self._is_xml_content(cleaned_value):
                        # Use CDATA section for XML content
                        string_elem.text = cleaned_value
                    else:
                        string_elem.text = cleaned_value
                else:
                    string_elem.text = cleaned_value
            
            elif isinstance(element, XMLComment):
                # Comments will be added in the final pretty-printed XML
                pass
        
        # Generate pretty-printed XML with correct indentation
        xml_str = ET.tostring(root, encoding='unicode')
        dom = minidom.parseString(xml_str)
        pretty_xml = dom.toprettyxml(indent='    ')
        
        # Remove the XML declaration as it's not needed for Android resources
        pretty_xml = '\n'.join(pretty_xml.split('\n')[1:])
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(pretty_xml)
        
        logger.info(f"Successfully wrote {len(resource_file.strings)} strings to {output_path}")
        
    def _cleanup_text_for_xml(self, text: str, language_code: str) -> str:
        """Clean up text for XML output, with special handling for Indian languages."""
        import re
        
        # List of Indian language codes
        indian_langs = ['hi', 'bn', 'mr', 'ta', 'te', 'kn', 'ml', 'gu', 'pa', 'or', 'as']
        
        # Apply extra cleaning for Indian languages
        if language_code in indian_langs:
            # Special handling for XML/HTML content
            if '<' in text and '>' in text:
                # Preserve XML/HTML tags and entities by temporarily replacing them
                # First, save HTML/XML tags
                tags = []
                
                def replace_tags(match):
                    tags.append(match.group(0))
                    return f"__TAG_{len(tags)-1}__"
                
                # Replace HTML/XML tags with placeholders
                processed_text = re.sub(r'<[^>]+>', replace_tags, text)
                
                # Fix spacing between words (not within tags)
                processed_text = re.sub(r'(?<=\S) (?=\S)', '', processed_text)
                
                # Restore tags
                for i, tag in enumerate(tags):
                    processed_text = processed_text.replace(f"__TAG_{i}__", tag)
                
                return processed_text
            else:
                # For regular text without HTML/XML, clean up spacing
                # Remove unnecessary spaces between characters
                text = re.sub(r'(?<=\S) (?=\S)', '', text)
                # Normalize spacing around format tags
                text = re.sub(r'__FORMAT_(\d+)__', ' __FORMAT_\\1__ ', text).strip()
                # Clean up double spaces
                text = re.sub(r' +', ' ', text)
        
        return text
    
    def _is_xml_content(self, value: str) -> bool:
        """
        Check if a string value contains XML content.
        
        This is a simple heuristic and may not catch all cases.
        """
        # Simple check for balanced tags
        try:
            # Try parsing as XML
            ET.fromstring(f"<root>{value}</root>")
            return True
        except:
            return False
