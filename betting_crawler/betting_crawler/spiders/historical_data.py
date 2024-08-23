from itemloaders import ItemLoader
import scrapy

import scrapy
from scrapy.http import Response

from typing import Any

# from betting_crawler.betting_crawler.items import HistoricalDataItem
# from itemadapter import ItemAdapter

class HistoricalDataSpider(scrapy.Spider):
    name = "historical_data"
    allowed_domains = ["www.football-data.co.uk"]
    start_urls = ["https://www.football-data.co.uk/downloadm.php"]

    def parse(self, response: Response, **kwargs: Any) -> Any:
        url = response.xpath("//a[contains(@href, 'mmz4281/2425/data.zip')]").attrib["href"]
        url = response.urljoin(url)
        # item = HistoricalDataItem(file_urls=[url])
        # ItemAdapter(item).asdict()

        yield {
            "file_urls": [url]
        }
