import sys
import os
import stringcase
import lxml.etree as ET
from pathlib import Path


PROJECT_RES_PATH = sys.argv[1]
OUT_RES_PATH = PROJECT_RES_PATH  # "./out"


name_map = {}


def fix_arrays(constants_root: ET.Element, lang: str):

    should_build_name_map = lang is None

    prefix = "-" + lang if lang else ""

    arrays_file_root = ET.parse(
        f"{PROJECT_RES_PATH}/values{prefix}/11-arrays.xml"
    ).getroot()
    string_arrays = arrays_file_root.findall("string-array")

    list(arrays_file_root.iter())[-1].tail = "\n\n" + " " * 4
    list(constants_root.iter())[-1].tail = "\n\n" + " " * 4

    for string_array in string_arrays:
        new_string_array = ET.Element("string-array")
        new_string_array.tail = "\n" + " " * 4
        array_name = string_array.attrib["name"]

        new_string_array.attrib["name"] = array_name

        if should_build_name_map:
            name_map[array_name] = []

        for i, item in enumerate(string_array.findall("item")):

            full_name: str

            if should_build_name_map:
                item_name = stringcase.snakecase(item.text)
                full_name = f"{array_name}_{item_name}"
                name_map[array_name].append(full_name)
            else:
                full_name = name_map[array_name][i]

            new_array_item = ET.Element("item")
            new_array_item.text = f"@string/{full_name}"
            new_array_item.tail = "\n" + " " * 4
            new_string_array.append(new_array_item)

            new_string_element = ET.Element("string")
            new_string_element.attrib["name"] = full_name
            new_string_element.text = item.text
            new_string_element.tail = "\n" + " " * 4

            arrays_file_root.append(new_string_element)

        new_string_element.tail = "\n\n" + " " * 4

        if should_build_name_map:
            constants_root.append(new_string_array)
        string_array.getparent().remove(string_array)

    new_string_element.tail = "\n\n"

    write_xml(arrays_file_root, f"{OUT_RES_PATH}/values{prefix}/11-arrays.xml")


def write_xml(root: ET.Element, path: str):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        ET.ElementTree(root).write(f, xml_declaration=True, encoding="UTF-8")


LANGUAGES = [
    f[len("values-") :]
    for f in os.listdir(PROJECT_RES_PATH)
    if f.startswith("values-")
    and f not in ("values-v21", "values-sw600dp", "values-land")
]

constants_root = ET.parse(f"{PROJECT_RES_PATH}/values/constants.xml").getroot()

LANGUAGES = [None] + LANGUAGES

for lang in LANGUAGES:
    fix_arrays(constants_root, lang)

write_xml(constants_root, f"{OUT_RES_PATH}/values/constants.xml")

print("DONE")