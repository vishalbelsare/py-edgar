# -*- coding: UTF-8 -*-
import os
from typing import Any, Dict, List, Tuple

import requests
from lxml import html
from rapidfuzz import fuzz, process
from tqdm import tqdm


class Edgar:

    def __init__(self, companies_page_path: str | None=None):

        # The required SEC EDGAR request header
        SEC_HEADERS = {
            "user-agent": "Edgar oit@sec.gov",
            "accept-encoding": "gzip, deflate",
            "host": "www.sec.gov",
            "referer": "https://www.sec.gov/",
            "cache-control": "no-cache",
            #'connection': 'close'
            #'connection': 'keep-alive'
        }
        # Set new default requests header

        # Add patch from:
        # https://github.com/NetSPI/NetblockTool/issues/3#issuecomment-897138800
        # Here we use the while loop as a poor-mans patch for rate limiting.
        # When that occurs, the first item returns a non-html doc...
        rate_limited = 0
        while not rate_limited:

            all_companies_content: str
            if companies_page_path is not None and os.path.isfile(companies_page_path):
                all_companies_content = open(
                    companies_page_path, encoding="latin-1"
                ).read()
            else:
                edgar_url = "https://www.sec.gov/Archives/edgar/cik-lookup-data.txt"
                all_companies_page = requests.get(edgar_url, headers=SEC_HEADERS)
                all_companies_content = all_companies_page.content.decode("latin1")
            all_companies_array = all_companies_content.split("\n")

            # Check for rate limiting garbage...
            item_arr = all_companies_array[0].split(":")
            if (
                item_arr[0]
                != '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http'
            ):
                rate_limited = 1

            del all_companies_array[-1]
            all_companies_array_rev: list[tuple[str, str]] = []
            for i, item in enumerate(all_companies_array):
                if item == "":
                    continue
                _name, _cik = Edgar.split_raw_string_to_cik_name(item)
                all_companies_array[i] = (_name, _cik)
                all_companies_array_rev.append((_cik, _name))
            self.all_companies_dict: dict[str, str] = dict(all_companies_array)
            self.all_companies_dict_rev = dict(all_companies_array_rev)

    def get_cik_by_company_name(self, name: str) -> str:
        return self.all_companies_dict[name]

    def match_company_by_company_name(
        self, name, top=5, progress=True
    ) -> List[Dict[str, Any]]:
        result = []
        for company, cik in (
            tqdm(self.all_companies_dict.items())
            if progress
            else self.all_companies_dict.items()
        ):
            result.append(
                {
                    "company_name": company,
                    "cik": cik,
                    "score": fuzz.ratio(name.upper(), company),
                }
            )
        return sorted(result, key=lambda row: row["score"], reverse=True)[:top]

    def get_company_name_by_cik(self, cik: str) -> str:
        return self.all_companies_dict_rev[cik]

    def find_company_name(self, words: str) -> List[str]:
        possible_companies = []
        words = words.lower()
        for company in self.all_companies_dict:
            if all(word in company.lower() for word in words.split(" ")):
                possible_companies.append(company)
        return possible_companies

    def find_company_name_cik(self, words: str) -> List[tuple[str, str]]:
        """
        Find possible company names and their corresponding CIKs based on input words.

        This function searches through a dictionary of companies, returning a list of tuples
        containing the names of companies and their Central Index Keys (CIKs) that match all
        the provided words. The search is case-insensitive and considers partial matches.

        Args:
            words (str): A string containing one or more words to search for in company names.
                         Words should be separated by spaces.

        Returns:
            List[tuple[str, str]]: A list of tuples, where each tuple contains:
                - company (str): The name of the company.
                - cik (str): The Central Index Key (CIK) associated with the company.

            If no matches are found, an empty list is returned.

        Example:
            >>> find_company_name_cik("apple inc")
            [("Apple Inc", "0000320193")]

        Note:
            The search checks if all individual words in the input string are present in the
            company names, ignoring case.
        """
        possible_companies = []
        words = words.lower()
        for company, cik in self.all_companies_dict.items():
            if all(word in company.lower() for word in words.split(" ")):
                possible_companies.append((company, cik))
        return possible_companies

    @classmethod
    def split_raw_string_to_cik_name(cls, item):
        item_arr = item.split(":")[:-1]
        return ":".join(item_arr[:-1]), item_arr[-1]


def test():
    com = Company("Oracle Corp", "0001341439")
    tree = com.get_all_filings(filingType="10-K")
    return Company.get_documents(tree)
