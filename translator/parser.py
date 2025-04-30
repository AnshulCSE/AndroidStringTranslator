"""
XML Parser for Android string resources.

This module handles parsing of Android string resource XML files.
"""

import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional, Dict, Any
import re

logger = logging.getLogger(__name__)


class StringResource:
    """Represents a single string resource from an Android strings.xml file."""
    
    def __init__(self, name: str, value: str, translatable: bool = True, formatted: bool = True):
        self.name = name
        self.value = value
        self.translatable = translatable
        self.formatted = formatted
        self.attributes: Dict[str, str] = {}
    
    def __repr__(self):
        return f"StringResource(name='{self.name}', value='{self.value}', translatable={self.translatable})"


class XMLComment:
    """Represents an XML comment in the resource file."""
    
    def __init__(self, text: str):
        self.text = text


class StringResourceFile:
    """Represents the entire string resource file with all strings and metadata."""
    
    def __init__(self, language_code: str = "en"):
        self.language_code = language_code
        self.strings: List[StringResource] = []
        self.comments: List[XMLComment] = []
        self.elements: List[Any] = []  # Contains both StringResource and XMLComment objects in order
    
    def add_string(self, string: StringResource) -> None:
        """Add a string resource to the file."""
        self.strings.append(string)
        self.elements.append(string)
    
    def add_comment(self, comment: XMLComment) -> None:
        """Add a comment to the file."""
        self.comments.append(comment)
        self.elements.append(comment)
    
    def create_copy_for_translation(self, language_code: str) -> 'StringResourceFile':
        """Create a copy of this resource file for the given language code."""
        new_file = StringResourceFile(language_code)
        
        # Copy all elements in order
        for element in self.elements:
            if isinstance(element, StringResource):
                new_string = StringResource(
                    element.name, 
                    element.value,
                    element.translatable,
                    element.formatted
                )
                new_string.attributes = element.attributes.copy()
                new_file.add_string(new_string)
            elif isinstance(element, XMLComment):
                new_file.add_comment(XMLComment(element.text))
        
        return new_file


class StringResourceParser:
    """Parser for Android string resource XML files."""
    
    def __init__(self, preserve_comments: bool = True):
        self.preserve_comments = preserve_comments
    
    def parse(self, file_path: Path) -> StringResourceFile:
        """
        Parse an Android string resource XML file and return a StringResourceFile object.
        
        Args:
            file_path: Path to the XML file to parse
            
        Returns:
            StringResourceFile object containing parsed resources
        """
        logger.info(f"Parsing string resources from {file_path}")
        
        # Determine language code from file path (values-XX directory format)
        language_code = "en"  # Default
        path_str = str(file_path)
        match = re.search(r'values-([a-zA-Z_-]+)', path_str)
        if match:
            language_code = match.group(1)
        
        resource_file = StringResourceFile(language_code)
        
        try:
            # If we want to preserve comments, we need to use a custom parser
            if self.preserve_comments:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract comments first
                comment_positions = []
                for match in re.finditer(r'<!--(.*?)-->', content, re.DOTALL):
                    comment_positions.append((match.start(), match.end(), match.group(1).strip()))
                
                # Parse the XML
                tree = ET.parse(file_path)
                root = tree.getroot()
                
                # Process strings
                for string_elem in root.findall('.//string'):
                    self._parse_string_element(string_elem, resource_file)
                
                # Add comments in their positions
                # This is a simplification; in a real implementation, you'd need to track positions more carefully
                for _, _, comment_text in comment_positions:
                    resource_file.add_comment(XMLComment(comment_text))
                
            else:
                # Simple parsing without comments
                tree = ET.parse(file_path)
                root = tree.getroot()
                
                for string_elem in root.findall('.//string'):
                    self._parse_string_element(string_elem, resource_file)
            
            logger.info(f"Successfully parsed {len(resource_file.strings)} strings")
            return resource_file
            
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            raise
    
    def _parse_string_element(self, string_elem: ET.Element, resource_file: StringResourceFile) -> None:
        """Parse a single string element from the XML."""
        name = string_elem.get('name')
        if name is None:
            logger.warning("Found string element without name attribute, skipping")
            return
        
        # Get value, handling both text and inner XML elements
        if len(string_elem) == 0:
            value = string_elem.text or ""
        else:
            value = ET.tostring(string_elem, encoding='unicode', method='xml')
            # Remove the outer <string> tags
            value = re.sub(r'^<string[^>]*>(.*)</string>$', r'\1', value, flags=re.DOTALL)
        
        # Check translatable attribute
        translatable_attr = string_elem.get('translatable', 'true')
        translatable = translatable_attr.lower() == 'true'
        
        # Check formatted attribute
        formatted_attr = string_elem.get('formatted', 'true')
        formatted = formatted_attr.lower() == 'true'
        
        # Create string resource
        string_resource = StringResource(name, value, translatable, formatted)
        
        # Copy all attributes
        for attr_name, attr_value in string_elem.attrib.items():
            string_resource.attributes[attr_name] = attr_value
        
        resource_file.add_string(string_resource)
