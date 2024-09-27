# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from scrapy.pipelines.files import FilesPipeline
import zipfile
import json
import os
from dotenv import load_dotenv

load_dotenv(override=True)

CONFIG_FILE = os.environ['CONFIG_FILE']

class BettingCrawlerPipeline:
    def __init__(self, hist_data_dir) -> None:
        self.hist_data_dir = hist_data_dir

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            hist_data_dir=crawler.settings.get("FILES_STORE")
        )

    def process_item(self, item, spider):
        if not os.path.exists(self.hist_data_dir):
            os.makedirs(self.hist_data_dir)
            
        zip_file_path = os.path.join(self.hist_data_dir, item['files'][0].get('path'))
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(self.hist_data_dir)
        
        os.remove(zip_file_path)
    
        return item
    
class HistoricalDataPipeline(FilesPipeline):
    def file_path(self, request, response=None, info=None, *, item=None):
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        # date = request.url.split("/")[-2]
        filename = f"data{config['season']}.zip"
        return filename
