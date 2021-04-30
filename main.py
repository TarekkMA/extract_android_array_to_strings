import os
import re
from enum import Enum
from typing import Dict, List

import stringcase
import lxml.etree as ET
from pathlib import Path
import argparse
from operator import attrgetter


class Mode(Enum):
    extract_english = "extract_english"
    extract_translations = "extract_translations"
    fill_translations_with_en = "fill_translations_with_en"  # simulate crowdin
    move_arrays = "move_arrays"

    def __str__(self):
        return self.value

    @staticmethod
    def from_string(s):
        try:
            return Mode[s]
        except KeyError:
            raise ValueError()


def get_args():
    parser = argparse.ArgumentParser(description='XML Array Extraction Tool')
    parser.add_argument("mode", type=Mode, choices=list(Mode))
    parser.add_argument('--output', dest='output', type=str, help='output directory', default="./out")
    parser.add_argument('-i, --input', dest='input', type=str, help='input directory', required=True)
    return parser.parse_args()


TABSIZE = 4
TAB = " " * TABSIZE

MODE, PROJECT_RES_PATH, OUT_RES_PATH = attrgetter("mode", "input", "output")(get_args())


def lang_prefix(lang: str) -> str:
    return ("-" + lang) if lang else ""


def get_xml(file: str, lang=None):
    path = f"{PROJECT_RES_PATH}/values{lang_prefix(lang)}/{file}"
    return ET.parse(path).getroot()


def build_name_dict() -> Dict[str, List[str]]:
    name_map = {}
    arrays_root = get_xml("11-arrays.xml")
    string_arrays = arrays_root.findall("string-array")
    for string_array in string_arrays:
        array_name = string_array.attrib["name"]
        name_map[array_name] = []
        for i, item in enumerate(string_array.findall("item")):
            item_name = stringcase.snakecase(item.text)
            full_name = f"{array_name}_{item_name}"
            name_map[array_name].append(full_name)
    return name_map


def write_xml(root: ET.Element, path: str):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        xmlstr = ET.tostring(ET.ElementTree(root), xml_declaration=True, encoding="UTF-8").decode("UTF-8")
        # fix comments
        xmlstr = re.sub(r'-->([^\n])', r"-->\n\1", xmlstr)
        f.write(xmlstr)


def remove_arrays(name_dict: Dict[str, List[str]], root: ET.Element) -> ET.Element:
    for arr_name in name_dict:
        results = root.cssselect(f"string-array[name={arr_name}]")
        for a in results:
            root.remove(a)
    return root


def extract_array(
        name_dict: Dict[str, List[str]],
        lang: str = None,
        remove_arrs=False,
):
    arrays_root = get_xml("11-arrays.xml", lang)

    string_arrays = arrays_root.findall("string-array")

    last_element = arrays_root[-1]
    last_element.tail = "\n\n" + TAB

    for string_array in string_arrays:
        array_name = string_array.attrib["name"]
        items = string_array.findall("item")
        for i, item in enumerate(items):
            item_full_name = name_dict[array_name][i]

            new_string_element = ET.Element("string")
            new_string_element.attrib["name"] = item_full_name
            new_string_element.text = item.text
            new_string_element.tail = "\n" + TAB
            arrays_root.append(new_string_element)

        # extra line between items
        new_string_element.tail = "\n\n" + TAB

    # we don't want tab in the last item in the file
    new_string_element.tail = "\n\n"

    if remove_arrs:
        arrays_root = remove_arrays(name_dict, arrays_root)

    write_xml(arrays_root, f"{OUT_RES_PATH}/values{lang_prefix(lang)}/11-arrays.xml")


def copy_arrs(name_dict: Dict[str, List[str]], source: ET.Element, destination: ET.Element, ref_str_res=False):
    destination[-1].tail = "\n" + TAB
    for arr_name in name_dict:
        arr = source.cssselect(f"string-array[name={arr_name}]")[0]
        for i, item in enumerate(arr.findall("item")):
            if ref_str_res:
                item_full_name = name_dict[arr_name][i]
                item.text = f"@string/{item_full_name}"
        arr.tail = "\n" + TAB
        destination.append(arr)
    arr.tail = "\n"


def copy_arr_str_items(name_dict: Dict[str, List[str]], source: ET.Element, destination: ET.Element):
    print(ET.tostring(source).decode("utf-8"))
    for a in source:
        print(a.nsmap, a.tag, a.attrib.get("name"), a.text)
    destination[-1].tail = "\n" + TAB
    for arr_name in name_dict:
        for str_name in name_dict[arr_name]:
            string = source.cssselect(f"string[name={str_name}]")[0]
            destination.append(string)


def move_to_constants(name_dict: Dict[str, List[str]]):
    arrays_root = get_xml("11-arrays.xml")
    constants_root = get_xml("constants.xml")

    copy_arrs(name_dict, arrays_root, constants_root, ref_str_res=True)

    arrays_root = remove_arrays(name_dict, arrays_root)

    write_xml(arrays_root, f"{OUT_RES_PATH}/values/11-arrays.xml")
    write_xml(constants_root, f"{OUT_RES_PATH}/values/constants.xml")


def get_langs():
    langs = [
        f[len("values-"):]
        for f in os.listdir(PROJECT_RES_PATH)
        if f.startswith("values-") and f not in ("values-v21", "values-sw600dp", "values-land")
    ]
    return langs


def run(mode: Mode):
    name_dict = build_name_dict()
    if mode == Mode.extract_english:
        extract_array(name_dict)
    elif mode == Mode.extract_translations:
        for l in get_langs():
            extract_array(name_dict, lang=l, remove_arrs=True)
    elif mode == Mode.move_arrays:
        move_to_constants(name_dict)
    elif mode == Mode.fill_translations_with_en:
        print("E")
        enarr = get_xml("11-arrays.xml")
        for l in get_langs():
            larr = get_xml("11-arrays.xml", lang=l)
            copy_arr_str_items(name_dict, enarr, larr)
            write_xml(larr, f"{OUT_RES_PATH}/values{lang_prefix(l)}/11-arrays.xml")
    else:
        raise Exception(f"Unknown mode '{mode}'")
    print(f"{MODE} DONE")


def main():
    run(MODE)


if __name__ == "__main__":
    main()
