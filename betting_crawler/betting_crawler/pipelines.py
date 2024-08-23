# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from scrapy.pipelines.files import FilesPipeline
import zipfile
import os

class BettingCrawlerPipeline:
    def __init__(self, hist_data_dir) -> None:
        self.hist_data_dir = hist_data_dir

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            hist_data_dir=crawler.settings.get("FILES_STORE")
        )

    def process_item(self, item, spider):
        zip_file_path = os.path.join(self.hist_data_dir, item['files'][0].get('path'))
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(self.hist_data_dir)
        
        os.remove(zip_file_path)
    
        return item
    
class HistoricalDataPipeline(FilesPipeline):
    def file_path(self, request, response=None, info=None, *, item=None):
        date = request.url.split("/")[-2]
        filename = f"data{date}.zip"
        return filename
