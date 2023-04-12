"""
Crawler implementation
"""
import json
import random
import re
import requests
import shutil
from bs4 import BeautifulSoup
from pathlib import Path
from time import sleep
from typing import Pattern, Union
from core_utils.article.article import Article
from core_utils.article.io import to_raw
from core_utils.config_dto import ConfigDTO
from core_utils.constants import (ASSETS_PATH,
                                  CRAWLER_CONFIG_PATH,
                                  NUM_ARTICLES_UPPER_LIMIT,
                                  TIMEOUT_LOWER_LIMIT,
                                  TIMEOUT_UPPER_LIMIT)


class IncorrectSeedURLError(Exception):
    """
    Raised when seed URL does not match standard pattern
    """


class NumbersOfArticlesOutOfRangeError(Exception):
    """
    Raised when number of articles is out of range from 1 to 150
    """


class IncorrectNumberOfArticlesError(Exception):
    """
    Raised when inappropriate value (not integer) for total number of articles is used
    """


class IncorrectHeadersError(Exception):
    """
    Raised when inappropriate value (not dictionary) for headers is used
    """


class IncorrectEncodingError(Exception):
    """
    Raised when inappropriate value (not string) for encoding is used
    """


class IncorrectTimeoutError(Exception):
    """
    Raised when inappropriate value (not positive integer less than 60) for timeout  is used
    """


class IncorrectVerifyError(Exception):
    """
    Raised when inappropriate value (not boolean) for verify certificate is used
    """


class Config:
    """
    Unpacks and validates configurations
    """

    def __init__(self, path_to_config: Path) -> None:
        """
        Initializes an instance of the Config class
        """
        self.path_to_config = path_to_config
        self._validate_config_content()
        config_dto = self._extract_config_content()
        self._seed_urls = config_dto.seed_urls
        self._num_articles = config_dto.total_articles
        self._headers = config_dto.headers
        self._encoding = config_dto.encoding
        self._timeout = config_dto.timeout
        self._should_verify = config_dto.should_verify_certificate

    def _extract_config_content(self) -> ConfigDTO:
        """
        Returns config values
        """
        with open(self.path_to_config, encoding='utf-8') as f:
            content = json.load(f)
        return ConfigDTO(**content)

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters
        are not corrupt
        """
        config_dto = self._extract_config_content()
        if not (isinstance(config_dto.seed_urls, list) and len(config_dto.seed_urls) > 0):
            raise IncorrectSeedURLError
        for url in config_dto.seed_urls:
            if not (isinstance(url, str) and re.match(r'https?://.*', url)):
                raise IncorrectSeedURLError
        if not 1 < config_dto.total_aricles < NUM_ARTICLES_UPPER_LIMIT:
            raise NumbersOfArticlesOutOfRangeError
        if not isinstance(config_dto.total_articles, int):
            raise IncorrectNumberOfArticlesError
        if not isinstance(config_dto.headers, dict):
            raise IncorrectHeadersError
        if not isinstance(config_dto.encoding, str):
            raise IncorrectEncodingError
        if not (isinstance(config_dto.timeout, int) and TIMEOUT_LOWER_LIMIT < config_dto.timeout < TIMEOUT_UPPER_LIMIT):
            raise IncorrectTimeoutError
        if not isinstance(config_dto.should_verify_certificate, bool):
            raise IncorrectVerifyError

    def get_seed_urls(self) -> list[str]:
        """
        Retrieve seed urls
        """
        return self._seed_urls

    def get_num_articles(self) -> int:
        """
        Retrieve total number of articles to scrape
        """
        return self._num_articles

    def get_headers(self) -> dict[str, str]:
        """
        Retrieve headers to use during requesting
        """
        return self._headers

    def get_encoding(self) -> str:
        """
        Retrieve encoding to use during parsing
        """
        return self._encoding

    def get_timeout(self) -> int:
        """
        Retrieve number of seconds to wait for response
        """
        return self._timeout

    def get_verify_certificate(self) -> bool:
        """
        Retrieve whether to verify certificate
        """
        return self._should_verify

    def get_headless_mode(self) -> bool:
        """
        Retrieve whether to use headless mode
        """
        pass


def make_request(url: str, config: Config) -> requests.models.Response:
    """
    Delivers a response from a request
    with given configuration
    """
    sleep(random.randrange(2, 4))
    headers = config.get_headers()
    timeout = config.get_timeout()
    verify = config.get_verify_certificate()
    response = requests.get(url, headers=headers, timeout=timeout, verify=verify)
    response.encoding = config.get_encoding()
    return response


class Crawler:
    """
    Crawler implementation
    """

    url_pattern: Union[Pattern, str]

    def __init__(self, config: Config) -> None:
        """
        Initializes an instance of the Crawler class
        """
        self.urls = []
        self._config = config
        self._seed_urls = config.get_seed_urls()

    def _extract_url(self, article_bs: BeautifulSoup) -> str:
        """
        Finds and retrieves URL from HTML
        """
        return article_bs.get('href')

    def find_articles(self) -> None:
        """
        Finds articles
        """
        while len(self.urls) < self._config.get_num_articles():
            for seed_url in self._seed_urls:
                response = make_request(seed_url, self._config)
                if response.status_code == 200:
                    main_bs = BeautifulSoup(response.text, 'lxml')
                    articles = main_bs.find_all('a', {'class': 'news-for-copy'})
                    for article_bs in articles:
                        self.urls.append(self._extract_url(article_bs))

    def get_search_urls(self) -> list:
        """
        Returns seed_urls param
        """
        return self._seed_urls


class HTMLParser:
    """
    ArticleParser implementation
    """

    def __init__(self, full_url: str, article_id: int, config: Config) -> None:
        """
        Initializes an instance of the HTMLParser class
        """
        self._full_url = full_url
        self._article_id = article_id
        self._config = config
        self.article = Article(self._full_url, self._article_id)

    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:
        """
        Finds text of article
        """
        main_bs = article_soup.find('div', {'class': "page-content io-article-body"})
        for paragraph in main_bs.find_all('p')[:-1]:
            self.article.text += paragraph.text + '/n'


    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Finds meta information of article
        """
        pass

    def unify_date_format(self, date_str: str) -> datetime.datetime:
        """
        Unifies date format
        """
        pass

    def parse(self) -> Union[Article, bool, list]:
        """
        Parses each article
        """
        response = make_request(self._full_url, self._config)
        if response.status_code == 200:
            article_bs = BeautifulSoup(response.text, 'lxml')
            self._fill_article_with_text(article_bs)
            return self.article
        return False


def prepare_environment(base_path: Union[Path, str]) -> None:
    """
    Creates ASSETS_PATH folder if no created and removes existing folder
    """
    if base_path.exists():
        shutil.rmtree(base_path)
    base_path.mkdir(parents=True)


def main() -> None:
    """
    Entrypoint for scrapper module
    """
    config = Config(path_to_config=CRAWLER_CONFIG_PATH)
    prepare_environment(ASSETS_PATH)
    crawler = Crawler(config=config)
    crawler.find_articles()
    for el in crawler.urls:
        parser = HTMLParser(full_url=el, article_id=crawler.urls.index(el) + 1, config=config)
        text = parser.parse()
        if isinstance(text, Article):
            to_raw(text)


if __name__ == "__main__":
    main()
