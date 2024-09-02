import scrapy
from scrapy.http import Response

class UpcomingGamesSpider(scrapy.Spider):
    name = "upcoming_games"
    allowed_domains = ["www.flashscore.com"]
    start_urls = [
        "https://www.flashscore.com/football/football/england/premier-league/", 
        "https://www.flashscore.com/football/football/france/ligue-1/",
        "https://www.flashscore.com/football/football/germany/bundesliga/",
        "https://www.flashscore.com/football/football/portugal/liga-portugal/",
        "https://www.flashscore.com/football/football/turkey/super-lig/"
    ]

    def parse(self, response: Response):
        # partial_urls = response.css('aside.container__myMenu a::attr(href)').getall()
        # filtered_partial_urls = list(filter(lambda x: x in self.leagues, partial_urls))

        # full_urls = response.urljoin(filtered_partial_urls)

        # yield from response.follow_all(full_urls, self.parse_urls)

        def extract_games_info(query):

            return response.css(query).get(default="").strip()

        yield {
            "Date",
            "HomeTeam",
            "AwayTeam"
        }


    def parse_urls(self, response: Response):
        def extract_games_info(query):

            return response.css(query).get(default="").strip()

        yield {
            "Date",
            "HomeTeam",
            "AwayTeam"
        }
        
