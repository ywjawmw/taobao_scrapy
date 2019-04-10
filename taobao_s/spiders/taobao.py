# -*- coding: utf-8 -*-
import json
import scrapy
from pathlib import Path
from urllib import parse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from taobao_s.items import TaobaoSItem

class TaobaoSpider(scrapy.Spider):
    name = 'taobao'
    allowed_domains = ['s.taobao.com', 'rate.tmall.com']
    start_urls = ['http://s.taobao.com/search?q=']
    base_url = 'https://s.taobao.com/search?q=%s&sort=sale-desc&s=%s'
    detail_urls = []
    data = []
    headers ={
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.11 (KHTML, like Gecko) Chrome/20.0.1132.11 TaoBrowser/2.0 Safari/536.11"
    }
    # scrapy请求的开始时start_request
    def start_requests(self):
        # taobao_findUrl = 'https://s.taobao.com/search?q=%E5%B8%BD%E5%AD%90&imgfile=&commend=all&ssid=s5-e&search_type=item&sourceId=tb.index&spm=a21bo.50862.201856-taobao-item.1&ie=utf8&initiative_id=tbindexz_20170817&s=300'
        if not Path('taobaoCookies.json').exists():
            __class__.loginTaobao()  # 先执行login，保存cookies之后便可以免登录操作
        # 毕竟每次执行都要登录还是挺麻烦的，我们要充分利用cookies的作用
        # 从文件中获取保存的cookies
        with open('taobaoCookies.json', 'r', encoding='utf-8') as f:
            listcookies = json.loads(f.read())  # 获取cookies
        # 把获取的cookies处理成dict类型
        cookies_dict = dict()
        for cookie in listcookies:
            # 在保存成dict时，我们其实只要cookies中的name和value，而domain等其他都可以不要
            cookies_dict[cookie['name']] = cookie['value']
        key_words = self.settings['KEY_WORDS']
        key_words = parse.quote(key_words).replace(' ', '+')
        print(key_words)
        page_num = self.settings['PAGE_NUM']
        one_page_num = self.settings['ONE_PAGE_COUNT']
        for i in range(page_num):
            url = self.base_url % (key_words, i*one_page_num)
            yield scrapy.Request(url, cookies=cookies_dict, callback=self.parse, headers=__class__.headers)

    # 使用selenium登录知乎并获取登录后的cookies，后续需要登录的操作都可以利用cookies
    @staticmethod
    def loginTaobao():
        url = 'https://login.taobao.com/member/login.jhtml'
        options = webdriver.ChromeOptions()
        # 不加载图片,加快访问速度
        # options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})
        # 此步骤很重要，设置为开发者模式，防止被各大网站识别出来使用了Selenium
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        # options.add_argument('--headless')
        browser = webdriver.Chrome(executable_path="G:\chromedriver_win32\chromedriver.exe", options=options)
        wait = WebDriverWait(browser, 10)  # 超时时长为10s
        # 打开网页
        browser.get(url)
        # 自适应等待，点击密码登录选项
        browser.implicitly_wait(30)  # 智能等待，直到网页加载完毕，最长等待时间为30s
        browser.find_element_by_xpath('//*[@class="forget-pwd J_Quick2Static"]').click()
        browser.find_element_by_xpath('//*[@class="weibo-login"]').click()
        browser.find_element_by_name('username').send_keys('zhan_jinzhou@sina.com')
        browser.find_element_by_name('password').send_keys('qwer@123')
        browser.find_element_by_xpath('//*[@class="btn_tip"]/a/span').click()
        # try:
        #     WebDriverWait(self.browser, 5, 0.5).until(
        #         EC.presence_of_element_located((By.NAME, 'verifycode')))
        #     print('！！！！出现验证码！！！！')
        #     img_url = self.browser.find_element_by_xpath('//*[@class="code"]/img').get_attribute('node-type')
        #     print(img_url)
        #     code = input('请输入验证码：')
        #     self.browser.find_element_by_name('verifycode').send_keys(code)
        #     self.browser.find_element_by_xpath('//*[@class="btn_tip"]/a/span').click()
        # except Exception as e:
        #     print('get button failed: ', e)

        # 直到获取到淘宝会员昵称才能确定是登录成功
        taobao_name = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,
                                                                      '.site-nav-bd > ul.site-nav-bd-l > li#J_SiteNavLogin > div.site-nav-menu-hd > div.site-nav-user > a.site-nav-login-info-nick ')))
        # 输出淘宝昵称
        print(taobao_name.text)

        # 通过上述的方式实现登录后，其实我们的cookies在浏览器中已经有了，我们要做的就是获取
        cookies = browser.get_cookies()  # Selenium为我们提供了get_cookies来获取登录cookies
        browser.close()  # 获取cookies便可以关闭浏览器
        # 然后的关键就是保存cookies，之后请求从文件中读取cookies就可以省去每次都要登录一次的
        # 当然可以把cookies返回回去，但是之后的每次请求都要先执行一次login没有发挥cookies的作用
        jsonCookies = json.dumps(cookies)  # 通过json将cookies写入文件
        with open('taobaoCookies.json', 'w') as f:
            f.write(jsonCookies)
        print(cookies)

    def url_decode(self, temp):
        while '\\' in temp:
            index = temp.find('\\')
            st = temp[index:index + 7]
            temp = temp.replace(st, '')

        index = temp.find('id')
        temp = temp[:index + 2] + '=' + temp[index + 2:]
        index = temp.find('ns')
        temp = temp[:index] + '&' + 'ns=' + temp[index + 2:]
        index = temp.find('abbucket')
        temp = 'https:' + temp[:index] + '&' + 'abbucket=' + temp[index + 8:]
        return temp

    def parse(self, response):
        p = 'g_page_config = ({.*?});'
        g_page_config = response.selector.re(p)[0]
        g_page_config = json.loads(g_page_config)
        auctions = g_page_config['mods']['itemlist']['data']['auctions']
        url1 = 'https://rate.tmall.com/list_detail_rate.htm?itemId=%s&sellerId=%s&order=3&currentPage=%s'
        # 从文件中获取保存的cookies
        with open('taobaoCookies.json', 'r', encoding='utf-8') as f:
            listcookies = json.loads(f.read())  # 获取cookies
        # 把获取的cookies处理成dict类型
        cookies_dict = dict()
        for cookie in listcookies:
            # 在保存成dict时，我们其实只要cookies中的name和value，而domain等其他都可以不要
            cookies_dict[cookie['name']] = cookie['value']
        for auction in auctions:
            item = TaobaoSItem()
            item['price'] = auction['view_price']
            item['sales'] = auction['view_sales']
            item['title'] = auction['raw_title']
            item['nick'] = auction['nick']
            item['loc'] = auction['item_loc']
            item['detail_url'] = auction['detail_url']
            item['nid'] = auction['nid']
            item['sellerid'] = auction['user_id']

            # yield item
            #天猫爬取方式
            if 'tmall' in item['detail_url']:
                for i in range(2):
                    print(item['sellerid'])
                    url = url1 % (item['nid'], item['sellerid'], str(i+1))
                    print(url)
                    request = scrapy.Request(url, cookies=cookies_dict, callback=self.parseNext, headers=__class__.headers)
                    yield request

    def parseNext(self, response):
        print(response.text)
        # p = 'jsonp128({.*?})'
        # page_info = response.selector.re(p)[0]
        # page_info = json.loads(page_info)
        # print(page_info)



