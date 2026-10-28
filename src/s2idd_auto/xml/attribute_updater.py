#!/usr/bin/env python3
"""
Script to convert savepv.json to attributes.xml
Converts JSON format to areaDetector attributes XML format
"""

import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
import argparse
import os


def load_json_data(json_file_path):
    """Load JSON data from file"""
    try:
        with open(json_file_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File {json_file_path} not found")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {json_file_path}: {e}")
        return None


def create_xml_structure():
    """Create the base XML structure"""
    # Create root element
    root = ET.Element("Attributes")

    # Add namespace attributes
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    root.set(
        "xsi:schemaLocation", "http://epics.aps.anl.gov/areaDetector/attributes ../attributes.xsd"
    )

    return root


def add_attribute_element(root, key, data):
    """Add an Attribute element to the XML"""
    attr = ET.SubElement(root, "Attribute")

    # Set all the attributes
    attr.set("name", data.get("name", key))
    attr.set("type", data.get("type", "EPICS_PV"))
    attr.set("source", data.get("source", key))
    attr.set("dbrtype", data.get("dbrtype", "DBR_NATIVE"))
    attr.set("description", data.get("description", key))


def convert_json_to_xml(json_data, output_file_path):
    """Convert JSON data to XML and save to file"""
    # Create XML structure
    root = create_xml_structure()

    # Add comment
    comment = ET.Comment(" Attributes ")
    root.insert(0, comment)

    # Process each JSON entry
    for key, data in json_data.items():
        add_attribute_element(root, key, data)

    # Create pretty XML
    rough_string = ET.tostring(root, "unicode")
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="    ")

    # Remove the first line (XML declaration from minidom)
    lines = pretty_xml.split("\n")
    if lines[0].startswith("<?xml"):
        lines = lines[1:]

    # Write to file
    with open(output_file_path, "w") as f:
        f.write('<?xml version="1.0" standalone="no" ?>\n')
        f.write("\n".join(lines))

    print(f"Successfully converted {len(json_data)} attributes to {output_file_path}")


def main():
    """Main function with command line arguments"""
    parser = argparse.ArgumentParser(description="Convert savepv.json to attributes.xml")
    parser.add_argument(
        "input", nargs="?", default="savepv.json", help="Input JSON file (default: savepv.json)"
    )
    parser.add_argument(
        "-o",
        "--output",
        default="attributes_from_json.xml",
        help="Output XML file (default: attributes_from_json.xml)",
    )
    parser.add_argument(
        "--overwrite", action="store_true", help="Overwrite output file if it exists"
    )

    args = parser.parse_args()

    # Check if input file exists
    if not os.path.exists(args.input):
        print(f"Error: Input file '{args.input}' not found")
        return

    # Check if output file exists and handle overwrite
    if os.path.exists(args.output) and not args.overwrite:
        response = input(f"Output file '{args.output}' already exists. Overwrite? (y/N): ")
        if response.lower() != "y":
            print("Operation cancelled.")
            return

    print(f"Converting {args.input} to {args.output}...")

    # Load JSON data
    json_data = load_json_data(args.input)
    if json_data is None:
        return

    # Convert to XML
    convert_json_to_xml(json_data, args.output)

    print("Conversion completed!")


if __name__ == "__main__":
    main()
