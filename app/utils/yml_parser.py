import asyncio
import re
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup


class YmlParser:
    def __init__(self, yml_path: str):
        self.yml_path = yml_path

    def _normalize(self, text: str) -> str:
        if not text:
            return ''
        return re.sub(r'[^a-zа-я0-9]', '', text.lower())

    async def get_catalog_from_yml(self) -> list:
        return await asyncio.to_thread(self._parse_yml)

    def _parse_yml(self) -> list:
        try:
            root = ET.parse(self.yml_path).getroot()
        except ET.ParseError as e:
            print(f"Ошибка в структуре XML: {e}")
            return []
        except FileNotFoundError:
            print(f"Файл {self.yml_path} не найден.")
            return []

        categories = {cat.get("id"): cat.text for cat in root.findall(".//category")}

        catalog_data = []
        for offer in root.findall(".//offer"):
            name = offer.findtext("name") or offer.findtext("model")
            if not name:
                continue

            desc_raw = offer.findtext("description") or ""
            clean_desc = BeautifulSoup(desc_raw, "html.parser").get_text(strip=True, separator=" ")

            item = {
                "offer_id": offer.get("id"),
                "available": offer.get("available") == "true",
                "name": name,
                "price": offer.findtext("price"),
                "url": offer.findtext("url"),
                "category": categories.get(offer.findtext("categoryId"), ""),
                "vendor": offer.findtext("vendor"),
                "vendor_code": offer.findtext("vendorCode"),
                "description": clean_desc,
                "picture": offer.findtext("picture"),
                "params": {
                    param.get("name", "").lower(): (param.text or "").lower()
                    for param in offer.findall("param")
                    if param.get("name")
                },
            }
            catalog_data.append(item)

        return catalog_data
