from  utils.download import Download
from bs4 import BeautifulSoup
from extractor.article_extractor import ArticleExtractor
import re
import datetime
from utils.redis_bloom import bloom_url
def get_listpage(url):
    d = Download()
    html = d.download('GET',url=url)
    soup =  BeautifulSoup(html,'lxml')
    url_list = []
    for tbody in soup.find_all('tbody',id=re.compile('normalthread_.*?')):
        url = tbody.find('th').find_all('a')[1]['href']
        url_list.append(url)
    return url_list


def get_detial_parse(urls):
    item = {}
    for url in urls:
        if bloom_url(url):
            d = Download()
            html = d.download('GET',url = url)
            soup = BeautifulSoup(html,'lxml')
            item['content'] = soup.find('div',attrs = {'class':'t_fsz'})
            publish = soup.find('em',attrs={'id':re.compile('author.*?')}).find('span')['title']
            item['publish'] = datetime.datetime.strptime(publish,'%Y-%m-%d %H:%M:%S')
            item['title'] = soup.find('span',attrs={'id':'thread_subject'}).text.split('_')[0]
            item['author'] = soup.find('div',attrs={'class':'authi'}).find('a').text
            print( item['publish'],item['author'])
        else:
            print('信息已经抓取过')


url ='http://www.fly166.com/forum-39-1.html'
urls = get_listpage(url)
get_detial_parse(urls)