#!/usr/bin/env python
#coding:utf-8

import requests
# from .color import printText
from bs4 import UnicodeDammit
from utils.tools import  *
import chardet

class Download(object):
    '''
    :class: use requests.request method,return response or None
    :author: doupeng
    '''
    def __init__(self):

        self._proxies = ''
        self.FAIL_ENCODING = 'ISO-8859-1'
    def download(self,method,url,proxyEnable=False,params=None,data=None,json=None,headers=None,cookies=None,files=None,auth=None,timeout=10,allowRedirects=True,verify=None,stream=None,cert=None):
        '''
        :param method: <class str|'GET','POST','PUT','DELETE','HEAD','OPTIONS'>
        :param url: <class str>
        :param proxyEnable: default=False <class bool|use proxy or not>
        :param params: (optional) Dictionary or bytes to be sent in the query string for the :class:`Request`
        :param data: (optional) Dictionary, bytes, or file-like object to send in the body of the :class:`Request`
        :param json: (optional) json data to send in the body of the :class:`Request`
        :param headers: (optional) Dictionary of HTTP Headers to send with the :class:`Request`
        :param cookies: (optional) Dict or CookieJar object to send with the :class:`Request`
        :param files: (optional) Dictionary of ``'name': file-like-objects`` (or ``{'name': file-tuple}``)
                      for multipart encoding upload.``file-tuple`` can be a 2-tuple ``('filename', fileobj)``,
                      3-tuple ``('filename', fileobj, 'content_type')``or a 4-tuple ``('filename', fileobj,
                      'content_type', custom_headers)``, where ``'content-type'`` is a string defining the
                      content type of the given file and ``custom_headers`` a dict-like object containing
                      additional headers to add for the file
        :param auth: (optional) Auth tuple to enable Basic/Digest/Custom HTTP Auth
        :param timeout: (optional) How long to wait for the server to send data
                        before giving up, as a float, or a :ref:`(connect timeout, read
                        timeout) <timeouts>` tuple <float or tuple>
        :param allow_redirects: (optional) Boolean. Set to True if POST/PUT/DELETE redirect following is allowed <class bool>
        :param proxies: (optional) Dictionary mapping protocol to the URL of the proxy
        :param verify: (optional) whether the SSL cert will be verified. A CA_BUNDLE path can also be provided. Defaults to ``True``
        :param stream: (optional) if ``False``, the response content will be immediately downloaded
        :param cert: (optional) if String, path to ssl client cert file (.pem). If Tuple, ('cert', 'key') pair
        :return: <class Response> if failed <None>
        '''
        response = None
        #----not use proxy--------------
        if proxyEnable == False:
            try:
                response = requests.request(method,url,params=params,data=data,json=json,headers=headers,cookies=cookies,files=files,auth=auth,timeout=timeout,allow_redirects=allowRedirects,verify=verify,stream=stream,cert=cert)
            except Exception as e:
                return ''


        #----use proxy------------------
        elif proxyEnable:
            self._proxies=''
            try:
                response = requests.request(method,url,params=params,data=data,json=json,headers=headers,cookies=cookies,files=files,auth=auth,timeout=timeout,allow_redirects=allowRedirects,proxies=self._proxies,verify=verify,stream=stream,cert=cert)

            except:
                return ''
        # code = chardet.detect(response.content)['encoding']
        # if 'G' in code  or 'g' in code:
        #     code = 'gbk'
        # elif 'U' in code  or 'u' in code:
        #     code = 'utf-8'
        html = self._get_html_from_response(response)
        return html

    def _get_html_from_response(self,response):
        if response.encoding != self.FAIL_ENCODING:
            # return response as a unicode string
            html = response.text
        else:
            # don't attempt decode, return response in bytes
            html = response.content
            html = self.get_unicode_html(html)
            if not is_have_chinese(html):
                response.encoding = 'gb2312'
                html = response.text
        return html or ''

    def get_unicode_html(self,html):
        if isinstance(html, str):
            return html

        if not html:
            return html
        converted = UnicodeDammit(html, is_html=True)
        if not converted.unicode_markup:
            raise Exception( 'Failed to detect encoding of article HTML, tried: %s' %', '.join(converted.tried_encodings))

        html = converted.unicode_markup
        return html



if __name__ == '__main__':
    print(Download())
