# -*- coding: utf-8 -*-
'''
Created on 2017-11-27 16:41
---------
@summary: 正文提取
---------
@author: Boris
'''
import sys,os
sys.path.append('../')
from init import add_path
add_path()
import re
import  lxml.html
import utils.tools as tools
from utils.log import log
from extractor.config import *
from extractor.region import Region
from urllib.parse import urljoin
from utils.download import Download
from lxml import etree
import chardet
class ArticleExtractor():
    def __init__(self, url, html = None, language='zh'):
        self._html = html
        self._url = url
        self._content_start_pos = ''
        self._content_end_pos = ''
        self._content_center_pos = ''
        self._paragraphs = ''
        if not html:
            self._html = tools.get_html(url)
        self._text = self.__del_html_tag(self._html)

        self.stripper = re.compile(r'\s+')
        self.anchor_ratio_limit = 0.3
        self.impurity_threshold = 30

        self.doc = lxml.html.fromstring(self._text)
        self.region = Region(self.doc)


    def __replace_str(self, source_str, regex, replace_str = ''):
        '''
        @summary: 替换字符串
        ---------
        @param source_str: 原字符串
        @param regex: 正则
        @param replace_str: 用什么来替换 默认为''
        ---------
        @result: 返回替换后的字符串
        '''
        str_info = re.compile(regex)
        return str_info.sub(replace_str, source_str)

    def __del_html_tag(self, html):
        '''
        @summary:
        ---------
        @param html:
        @param save_useful_tag:保留有用的标签，如img和p标签
        ---------
        @result:
        '''
        html = self.__replace_str(html, u'(?i)<script(.|\n)*?</script>')
        html = self.__replace_str(html, u'(?i)<style(.|\n)*?</style>')
        html = self.__replace_str(html, u'(?i)<\/?(span|section|font|em)[^<>]*?>')
        html = self.__replace_str(html, u'(?i)<div[^<>]+?(display:.?none|comment|measure).*?>([\s\S]*?)<\/div>')
        html = self.__replace_str(html, u'<!--(.|\n)*?-->')
        html = self.__replace_str(html, u'(?!&[a-z]+=)&[a-z]+;?', ' ')


        html = self.__replace_str(html, '[\f\r\t\v]') # 将空格和换行符外的其他空白符去掉
        html = html.strip()
        return html

    def __del_unnecessary_character(self, content):
        '''
        @summary: 去掉多余的换行和空格
        ---------
        @param content:
        ---------
        @result:
        '''
        content = content.strip()
        content = content[content.find('>') + 1 : ] if content.startswith('</') else content # 去掉开头的结束符
        content = self.__replace_str(content, ' {2,}', '') # 去掉超过一个的空格
        return self.__replace_str(content, '(?! )\s+', '\n') # 非空格的空白符转换为回车

    def get_title(self):
        title = ''

        # 处理特殊的网站不规则的标题
        for domain, regex in SPECIAL_TITLE.items():
            if domain in self._url:
                title = tools.get_info(self._html, regex, fetch_one = True)
                break

        if not title:
            regex = '(?i)<title.*?>(.*?)</title>'
            title = tools.get_info(self._html, regex, fetch_one = True)
            title = title[:title.find('_')] if '_' in title else title
            title = title[:title.find('-')] if '-' in title else title
            title = title[:title.find('|')] if '|' in title else title

            if not title:
                regexs = ['<h1.*?>(.*?)</h1>', '<h2.*?>(.*?)</h2>', '<h3.*?>(.*?)</h3>', '<h4.*?>(.*?)</h4>']
                title = tools.get_info(self._html, regexs, fetch_one = True)


        title = tools.del_html_tag(title)
        return title

    def get_content1(self):
        '''
        方法一
        @summary:
        基于文本密度查找正文
            1、将html去标签，将空格和换行符外的其他空白符去掉
            2、统计连续n段文字的长度，此处用于形容一定区域的文本密度
            3、将文本最密集处当成正文的开始和结束位置
            4、在正文开始处向上查找、找到文本密度小于等于正文文本密度阈值值，算为正文起始位置。该算法文本密度阈值值为文本密度值的最小值
            5、在正文开始处向下查找、找到文本密度小于等于正文文本密度阈值值，算为正文结束位置。该算法文本密度阈值值为文本密度值的最小值

        去除首页等干扰项：
            1、正文一般都包含p标签。此处统计p标签内的文字数占总正文文字数的比例。超过一定阈值，则算为正文
        待解决：
            翻页 如：http://mini.eastday.com/a/171205202028050-3.html
        ---------
        ---------
        @result:
        '''
        if USEFUL_TAG:
            html = self.__replace_str(self._text, r'(?!{useful_tag})<(.|\n)+?>'.format(useful_tag = '|'.join(USEFUL_TAG)))
        else:
            html = self.__replace_str(self._text, '<(.|\n)*?>')
        paragraphs = html.split('\n')
        # for i, paragraph in enumerate(paragraphs):
        #     print(i, paragraph)

        # 统计连续n段的文本密度
        paragraph_lengths = [len(self.__del_html_tag(paragraph)) for paragraph in paragraphs]
        # paragraph_lengths = [len(paragraph.strip()) for paragraph in paragraphs]
        paragraph_block_lengths = [sum(paragraph_lengths[i : i + MAX_PARAGRAPH_DISTANCE]) for i in range(len(paragraph_lengths))]  # 连续n段段落长度的总和（段落块），如段落长度为[0,1,2,3,4] 则连续三段段落长度为[3,6,9,3,4]

        self._content_center_pos = content_start_pos = content_end_pos = paragraph_block_lengths.index(max(paragraph_block_lengths)) #文章的开始和结束位置默认在段落块文字最密集处
        min_paragraph_block_length = MIN_PARAGRAPH_LENGHT * MAX_PARAGRAPH_DISTANCE
        # 段落块长度大于最小段落块长度且数组没有越界，则看成在正文内。开始下标继续向上查找
        while content_start_pos > 0 and paragraph_block_lengths[content_start_pos] > min_paragraph_block_length:
            content_start_pos -= 1

        # 段落块长度大于最小段落块长度且数组没有越界，则看成在正文内。结束下标继续向下查找
        while content_end_pos < len(paragraph_block_lengths) and paragraph_block_lengths[content_end_pos] > min_paragraph_block_length:
            content_end_pos += 1

        # 处理多余的换行和空白符
        content = paragraphs[content_start_pos : content_end_pos]
        content = '\n'.join(content)
        content = self.__del_unnecessary_character(content)

        # 此处统计p标签内的文字数占总正文文字数的比例。超过一定阈值，则算为正文
        paragraphs_text_len = len(self.__del_html_tag(''.join(tools.get_info(content, '<p.*?>(.*?)</p>'))))
        content_text_len = len(self.__del_html_tag(content))
        if content_text_len and content_text_len > MIN_COUNTENT_WORDS and ((paragraphs_text_len / content_text_len) > MIN_PARAGRAPH_AND_CONTENT_PROPORTION):
            self._content_start_pos = content_start_pos
            self._content_end_pos = content_end_pos
            self._paragraphs = paragraphs
            # print(content_start_pos, content_end_pos, self._content_center_pos)
            return content
        else:
            return ''

    def get_author(self):
        # 不去掉标签匹配
        author = tools.get_info(self._text, AUTHOR_REGEXS_TEXT, fetch_one = True)

        if not author: # 没有匹配到，去掉标签后进一步匹配，有的作者和名字中间有标签
            author = tools.get_info(self.__replace_str(self._text, '<(.|\n)*?>', ' '), AUTHOR_REGEXS_TEXT, fetch_one = True)

        if not author: # 仍没匹配到，则在html的author中匹配
            author = tools.get_info(self._html, AUTHOR_REGEX_TAG, fetch_one = True)

        return author

    def get_release_time_old(self):

        if self._content_start_pos and self._content_end_pos:
            content = self.__replace_str('\n'.join(self._paragraphs[self._content_start_pos  - RELEASE_TIME_OFFSET: self._content_end_pos + RELEASE_TIME_OFFSET]), '<(.|\n)*?>', '<>')
        else:
            content = self.__replace_str(self._text, '<(.|\n)*?>', '<>')

        release_time = tools.get_info(content, DAY_TIME_REGEXS, fetch_one = True)
        if not release_time:
            release_time = tools.get_info(self.__replace_str(self._text, '<(.|\n)*?>', '<>'), DAY_TIME_REGEXS, fetch_one = True)

        release_time = tools.format_date(release_time)

        return release_time

    def get_release_time(self):
        def get_release_time_in_paragraph(paragraph_pos):
            if self._paragraphs:
                while paragraph_pos >= 0:
                    content = self.__replace_str(self._paragraphs[paragraph_pos], '<(.|\n)*?>', '<>')
                    release_time = tools.get_info(content, DAY_TIME_REGEXS, fetch_one = True)
                    if release_time:
                        return tools.format_date(release_time)

                    paragraph_pos -= 1

            return None

        release_time = get_release_time_in_paragraph(self._content_start_pos)
        if not release_time:
            release_time = get_release_time_in_paragraph(self._content_center_pos)

        return release_time


    def extract_content(self, region):
        items = region.xpath('.//text()|.//img|./table')
        tag_hist = {}
        for item in items:
            if  hasattr(item,'tag'):
                continue
            t = item.getparent().tag
            if t not in tag_hist:
                tag_hist[t] = 0
            tag_hist[t] += len(item.strip())
        winner_tag = None
        if len(tag_hist) > 0:
            winner_tag = max((c,k) for k,c in tag_hist.items())[1]
        contents = []
        for item in items:
            if not hasattr(item,'tag'):
                txt = item.strip()
                parent_tag = item.getparent().tag
                if  parent_tag != winner_tag \
                    and len(self.stripper.sub("",txt)) < self.impurity_threshold \
                    and parent_tag != 'li':
                    continue
                if txt == "":
                    continue
                contents.append({"type":"text","data":txt})
            elif item.tag == 'table':
                if winner_tag == 'td':
                    continue
                if item != region:
                    for el in item.xpath(".//a"):
                        el.drop_tag()
                    table_s = lxml.html.tostring(item)
                    contents.append({"type":"html","data":table_s})
                else:
                    for sub_item in item.xpath("//td/text()"):
                        contents.append({"type":"text","data":sub_item})
            elif item.tag == 'img':
                for img_prop in ('original', 'file', 'data-original', 'src-info', 'data-src', 'src'):
                    src =  item.get(img_prop)
                    if src != None:
                        break
                if self._url != "":
                    if not src.startswith("/") and not src.startswith("http") and not src.startswith("./"):
                        src = "/" + src
                    src = urljoin(self._url, src, False)
                contents.append({"type":"image","data":{"src": src}})
            else:
                pass
        return contents



    def extract(self):
        '''
        方法二 去标签结果
        :return:纯文字
        '''
        region = self.region.locate()
        if region == None:
            return []
        rm_tag_set = set([])
        for p_el in region.xpath(".//p|.//li"):
            child_links = p_el.xpath(".//a/text()")
            count_p = len(" ".join(p_el.xpath(".//text()")))
            count_a = len(" ".join(child_links))
            if float(count_a) / (count_p + 1.0) > self.anchor_ratio_limit:
                p_el.drop_tree()
        for el in region.xpath(".//a"):
            rm_tag_set.add(el)
        for el in region.xpath(".//strong|//b"):
            rm_tag_set.add(el)
        for el in rm_tag_set:
            el.drop_tag()
        content = self.extract_content(region)
        return content


    def get_content2(self):
        '''
        方法二 完美
        :return: 带标签的content
        '''
        region = self.region.locate()
        tag_content = etree.tostring(region,encoding='utf-8').decode()
        return tag_content

if __name__ == '__main__':
    urls = [
        # 'http://news.cctv.com/2017/11/30/ARTIvCEUIYEZx9HTsTypXySQ171130.shtml',
        # 'http://www.sohu.com/a/208214795_115178',
        # 'http://mini.eastday.com/a/171201210623679.html',
        # 'http://e.gmw.cn/2017-12/04/content_26998661.htm',
        # 'http://www.sohu.com/a/208241102_570245',
        'http://news.163.com/17/1201/21/D4JN5JRE0001875P.html',  # 乱码问题
        # 'http://mini.eastday.com/a/171204173416401.html',
        # 'http://www.sohu.com/a/208241102_570245',
        # 'http://www.sohu.com/'
        # 'http://www.southcn.com/'
        # 'http://kb.southcn.com/default.htm'
        # 'http://www.sohu.com/a/207186412_104421',
        # 'http://kb.southcn.com/content/2017-12/05/content_179364393.htm',
        # 'http://yn.people.com.cn/n2/2017/1129/c372315-30976586.html', #乱码
        # 'http://www.sohu.com/a/207186412_104421',
        # 'http://www.sohu.com/a/208209445_603687',
        # 'http://mini.eastday.com/a/171204173416401.html',
        # 'http://yn.people.com.cn/n2/2017/1129/c372315-30976586.html',
        # 'http://news.eastday.com/eastday/13news/auto/news/society/20171206/u7ai7256226.html',
        # 'http://cnews.chinadaily.com.cn/2017-12/06/content_35230092.htm',
        # 'http://e.gmw.cn/2017-12/04/content_26998661.htm',
        # 'http://www.sohu.com/a/208241102_570245',
        # 'http://cnews.chinadaily.com.cn/2017-12/06/content_35230092.htm',
        # 'http://news.eastday.com/eastday/13news/auto/news/society/20171206/u7ai7256226.html',
        # 'http://cj.sina.com.cn/article/detail/6185269244/510492',
        # 'http://0575gwy.com/index.php/Index/show/id/2130',
        # 'http://hdmedicine.com.cn/News_info.aspx?News_Id=787&CateId=24',
        # 'http://www.qz001.gov.cn/info/view/86ec076d71a44869ab71e00e5707f89e',
        # 'http://payh.gov.cn/Art/Art_2/Art_2_795.aspx',
        # 'http://qiushi.nbgxedu.com/show.aspx?id=d479b45a-1747-4f60-83f3-f1e2dc85a0d2',
        # 'http://31ly.com/show/10117/product-13846.html'
        # 'http://www.jawin.com.cn/news/show-247708.html'
        # 'http://pjsl.cn/Item/5845.aspx'
        # 'http://news.sina.com.cn/sf/news/flfg/2017-12-04/doc-ifypikwt7105025.shtml'
        # 'http://cq.people.com.cn/n2/2018/0327/c365403-31387318.html'
        # 'http://www.zjgrrb.com/zjzgol/system/2018/03/28/030796013.shtml',
        # 'http://tech.ifeng.com/a/20180116/44847498_0.shtml'
        # 'http://tech.ifeng.com/a/20171228/44825006_0.shtml'
        # 'http://news.ifeng.com/a/20180514/58297302_0.shtml'
        # 'https://baijiahao.baidu.com/s?id=1601748269934604720'
        # 'http://big5.cntv.cn/gate/big5/news.cctv.com/special/sx/index.shtml'
        # 'http://finance.youth.cn/finance_cyxfgsxw/201806/t20180611_11641628.htm'

    ]
    for url in urls:
        d = Download()
        html=d.download('GET',url)
        article_extractor = ArticleExtractor(url, html)
        content = article_extractor.get_content1()
        content1 = article_extractor.get_content2()
        # title = article_extractor.get_title()
        # release_time = article_extractor.get_release_time()
        # author = article_extractor.get_author()
        print('---------------------------')
        print(url)
        # print('title : ', title)
        # print('release_time: ', release_time)
        # print('author', author)
        print('content : ',content)
        print('---------------------------')
        print('content : ',content1)
        # print('---------------------------')
