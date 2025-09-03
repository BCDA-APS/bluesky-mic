#!/usr/bin/env python3
"""
Script to update the meta group in 2idd_tmm_layout.xml
by adding dataset elements based on attributes_from_json.xml
and organizing them into subgroups based on savepv.json group values
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
import argparse
import os
import json

def load_attributes_xml(attributes_file_path):
    """Load attributes from the attributes XML file"""
    try:
        tree = ET.parse(attributes_file_path)
        root = tree.getroot()
        
        attributes = []
        for attr in root.findall('.//Attribute'):
            attr_data = {
                'name': attr.get('name'),
                'source': attr.get('source'),
                'type': attr.get('type'),
                'dbrtype': attr.get('dbrtype'),
                'description': attr.get('description')
            }
            attributes.append(attr_data)
        
        print(f"Loaded {len(attributes)} attributes from {attributes_file_path}")
        return attributes
        
    except FileNotFoundError:
        print(f"Error: Attributes file {attributes_file_path} not found")
        return None
    except ET.ParseError as e:
        print(f"Error: Invalid XML in {attributes_file_path}: {e}")
        return None

def load_savepv_json(json_file_path):
    """Load the savepv.json file to get group and when information"""
    try:
        with open(json_file_path, 'r') as f:
            json_data = json.load(f)
        
        # Create a lookup dictionary by name
        name_lookup = {}
        for key, data in json_data.items():
            name = data.get('name', key)
            name_lookup[name] = {
                'group': data.get('group', 'default'),
                'when': data.get('when', ''),
                'source': data.get('source', key)
            }
        
        print(f"Loaded {len(json_data)} entries from {json_file_path}")
        return name_lookup
        
    except FileNotFoundError:
        print(f"Error: JSON file {json_file_path} not found")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {json_file_path}: {e}")
        return None

def load_layout_xml(layout_file_path):
    """Load the layout XML file"""
    try:
        tree = ET.parse(layout_file_path)
        return tree, tree.getroot()
    except FileNotFoundError:
        print(f"Error: Layout file {layout_file_path} not found")
        return None, None
    except ET.ParseError as e:
        print(f"Error: Invalid XML in {layout_file_path}: {e}")
        return None, None

def find_meta_group(root):
    """Find the meta group in the layout"""
    # Look for meta group in the instrument section
    instrument = root.find('.//group[@name="instrument"]')
    if instrument is not None:
        meta_group = instrument.find('.//group[@name="meta"]')
        if meta_group is not None:
            return meta_group
    
    print("Warning: meta group not found in layout")
    return None

def clear_meta_group(meta_group):
    """Clear existing content from meta group (except comments)"""
    # Remove all group and dataset elements but keep comments
    elements_to_remove = []
    for element in meta_group:
        if element.tag in ['group', 'dataset']:
            elements_to_remove.append(element)
    
    for element in elements_to_remove:
        meta_group.remove(element)
    
    print(f"Cleared {len(elements_to_remove)} existing elements from meta group")

def create_or_find_subgroup(meta_group, group_name):
    """Create a new subgroup or find existing one"""
    # Look for existing subgroup
    for element in meta_group:
        if element.tag == 'group' and element.get('name') == group_name:
            return element
    
    # Create new subgroup
    subgroup = ET.SubElement(meta_group, "group")
    subgroup.set("name", group_name)
    return subgroup

def add_dataset_to_group(group, attr_data, when=""):
    """Add a dataset element to the specified group"""
    dataset = ET.SubElement(group, "dataset")
    dataset.set("name", attr_data['name'])
    dataset.set("source", "ndattribute")
    dataset.set("ndattribute", attr_data['name'])
    
    # Only add when attribute if it's not empty
    if when:
        dataset.set("when", when)

def update_meta_group(meta_group, attributes, json_lookup):
    """Update the meta group with organized subgroups based on JSON data"""
    if meta_group is None:
        print("Error: Cannot update meta group - group not found")
        return False
    
    # Clear existing content
    clear_meta_group(meta_group)
    
    # Group attributes by their group value
    grouped_attributes = {}
    for attr_data in attributes:
        name = attr_data['name']
        
        # Look up group and when information from JSON
        if name in json_lookup:
            group_name = json_lookup[name]['group']
            when_value = json_lookup[name]['when']
        else:
            # Fallback if not found in JSON
            group_name = 'default'
            when_value = ''
        
        if group_name not in grouped_attributes:
            grouped_attributes[group_name] = []
        
        grouped_attributes[group_name].append((attr_data, when_value))
    
    # Create subgroups and add datasets
    total_datasets = 0
    for group_name, attr_list in grouped_attributes.items():
        print(f"Creating subgroup '{group_name}' with {len(attr_list)} attributes")
        
        # Create or find subgroup
        subgroup = create_or_find_subgroup(meta_group, group_name)
        
        # Add datasets to subgroup
        for attr_data, when_value in attr_list:
            add_dataset_to_group(subgroup, attr_data, when_value)
            total_datasets += 1
    
    print(f"Added {total_datasets} dataset elements organized into {len(grouped_attributes)} subgroups")
    return True

def save_layout_xml(tree, output_file_path):
    """Save the updated layout XML with proper formatting"""
    try:
        # Get the XML as string
        rough_string = ET.tostring(tree.getroot(), 'unicode')
        
        # Parse and pretty print
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="    ")
        
        # Remove the first line (XML declaration from minidom)
        lines = pretty_xml.split('\n')
        if lines[0].startswith('<?xml'):
            lines = lines[1:]
        
        # Write to file
        with open(output_file_path, 'w') as f:
            f.write('<?xml version="1.0" standalone="no" ?>\n')
            f.write('\n'.join(lines))
        
        print(f"Successfully saved updated layout to {output_file_path}")
        return True
        
    except Exception as e:
        print(f"Error saving layout file: {e}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Update meta group in layout XML with attributes organized by groups')
    parser.add_argument('--attributes', default='attributes_from_json.xml',
                       help='Input attributes XML file (default: attributes_from_json.xml)')
    parser.add_argument('--json', default='savepv.json',
                       help='Input savepv.json file (default: savepv.json)')
    parser.add_argument('--layout', default='2idd_tmm_layout.xml',
                       help='Input layout XML file (default: 2idd_tmm_layout.xml)')
    parser.add_argument('--output', default='2idd_tmm_layout_updated.xml',
                       help='Output layout XML file (default: 2idd_tmm_layout_updated.xml)')
    parser.add_argument('--overwrite', action='store_true',
                       help='Overwrite output file if it exists')
    
    args = parser.parse_args()
    
    # Check if input files exist
    if not os.path.exists(args.attributes):
        print(f"Error: Attributes file '{args.attributes}' not found")
        return
    
    if not os.path.exists(args.json):
        print(f"Error: JSON file '{args.json}' not found")
        return
    
    if not os.path.exists(args.layout):
        print(f"Error: Layout file '{args.layout}' not found")
        return
    
    # Check if output file exists and handle overwrite
    if os.path.exists(args.output) and not args.overwrite:
        response = input(f"Output file '{args.output}' already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Operation cancelled.")
            return
    
    print(f"Updating meta group in {args.layout}")
    print(f"Using attributes from: {args.attributes}")
    print(f"Using group/when info from: {args.json}")
    print(f"Output: {args.output}")
    
    # Load attributes
    attributes = load_attributes_xml(args.attributes)
    if attributes is None:
        return
    
    # Load JSON data
    json_lookup = load_savepv_json(args.json)
    if json_lookup is None:
        return
    
    # Load layout
    tree, root = load_layout_xml(args.layout)
    if tree is None:
        return
    
    # Find meta group
    meta_group = find_meta_group(root)
    if meta_group is None:
        print("Error: Could not find meta group in layout")
        return
    
    # Update meta group with organized subgroups
    if update_meta_group(meta_group, attributes, json_lookup):
        # Save updated layout
        save_layout_xml(tree, args.output)
        print("Layout update completed successfully!")
    else:
        print("Failed to update layout")

if __name__ == "__main__":
    main()
