import requests
import json
from lxml import etree # 解析库
from fake_useragent import UserAgent
import time, re, datetime
import pandas as pd

ua = UserAgent()

class CustomException(Exception):

    def __init__(self, status, msg):
        self.status = status
        self.msg = msg

class Info_58:
    '''
    出租房：https://wh.58.com/chuzu/
    买房：https://wh.58.com/xinfang/
    '''

    def __init__(self):
        self.session = requests.Session()
        self.session.headers = {
            "user-agent": ua.random
        }
        self.__init__all_city()
        self.highest = 0
        self.lowest = float('inf')
        self.unit_h = None 
        self.unit_l = None
        self.area_h = None
        self.area_l = None


    def __init__all_city(self):
        '''获取所有城市的名字及缩写的对应关系'''

        api = "https://www.58.com/changecity.html"
        headers = self.session.headers.copy()

        response = self.session.get(api, headers=headers)
        
        html = response.text
        res = re.findall("cityList = (.*?)</script>", html, re.S)[0]
        res = re.sub("\s", "", res)
        dic = json.loads(res)
        for k, v in dic.items():
            for k1, v1 in v.items():
                dic[k][k1] = v1.split("|")[0]
        city_dict = {}

        def traverse_dict(dic: dict):
            for k, v in dic.items():
                if k == "海外" or k == "其他":
                    continue
                if isinstance(v, dict):
                    traverse_dict(v)
                city_dict[k] = v

        traverse_dict(dic)

        other_city = re.findall("independentCityList = (.*?)var", html, re.S)[0]
        res = re.sub("\s", "", other_city)
        other_city_dic = json.loads(res)

        for k, v in other_city_dic.items():
            other_city_dic[k] = v.split("|")[0]

        city_dict.update(other_city_dic)
        self.all_city_dict = city_dict


    def info_zufang(self, city:str = "武汉"):
        '''爬取租房信息的爬虫方法'''
        assert self.all_city_dict is not None, "获取所有城市信息失败"
        print("---all_city_dict---")
        format_city = self.all_city_dict.pop(city, None)
        print("format_city:", format_city)
        assert format_city is not None, "{}该城市不在爬取城市之内".format(city)

        '''构造该城市租房页面url，获取所需数据'''
        self.city = city 
        start_url = "https://{}.58.com/chuzu/j2/".format(format_city)

        # 收集每一页中的价格信息
        self.__spiders(start_url)


    def info_xinfang(self, city:str = "武汉"):
        '''爬取买房信息的爬虫方法'''
        assert self.all_city_dict is not None, "获取所有城市信息失败"
        print("---all_city_dict---")
        format_city = self.all_city_dict.pop(city, None)
        print("format_city:", format_city)
        assert format_city is not None, "{}该城市不在爬取城市之内".format(city)
        
        '''构造该城市买房页面url，获取所需数据'''
        self.city = city 
        start_url = "https://{}.58.com/xinfang/loupan/all/".format(format_city)

        # 收集每一页中的价格信息
        self.__spiders2(start_url)
        



    def __get_html_source(self, url, params=None):
        '''通过get方式获取到网页的源码'''
        time.sleep(2)
        headers = self.session.headers.copy()
        try:
            if not params:
                params = {}
            response = self.session.get(url=url, headers=headers, params=params)
            return response
        except Exception as e:
            with open("./url_log_error.txt", "a", encoding="utf-8") as f:
                f.write(str(datetime.datetime.now()) + "\n")
                f.write(str(e) + "\n")
                f.write("error_url>>:{}".format(url) + "\n")


    def __get_price(self, response):

        html = response.text

        # 开始从页面中提取出想要的数据
        xml = etree.HTML(html)
        xpath_list = xml.xpath("//div[@class='money']/b[@class='strongbox']")
        for price_info_list in xpath_list:
            house_price = re.sub("\s", "", price_info_list.xpath(
                "string(.)"))
            house_price = int(house_price)
            # print(house_price)
            if house_price > self.highest:
                self.highest = house_price 
            if house_price and house_price < self.lowest:
                self.lowest = house_price


    def __get_xinfang_info(self, url, params):
        response = self.__get_html_source(url, params)
        html = response.text

        # 开始从页面中提取出想要的数据
        xml = etree.HTML(html)
        # 
        xpath_list = xml.xpath("//p[@class='price']/span|//p[@class='favor-tag around-price']/span")[0]
        
        house_price = re.sub("\s", "", xpath_list.xpath("string(.)"))
        # house_price = int(house_price)
        unit = re.sub("<.*>", "", etree.tostring(xpath_list, encoding='UTF-8').decode()).strip()
        xpath_list = xml.xpath("//span[@class='building-area']")[0]
        area = re.sub("\s", "", xpath_list.xpath("string(.)")).split('：')[1]
        return house_price, unit, area
        
        



    def __response_to_xml(self, response):
        try:
            xml = etree.HTML(response.text)
            # print(response.text)
            return xml
        except AttributeError:
            raise CustomException(10000, "response对象转换为xml失败,错误的链接地址为>>:{}".format(response))


    def __is_exist_next_page(self, response):
        '''判断是否存在下一页,存在拿到下一页的链接，不存在返回False'''
        xml = self.__response_to_xml(response)
        try:
            next_page_url = xml.xpath("//a[@class='next']/@href")[0]
            # print(next_page_url)
            return next_page_url
        except IndexError:
            return False

    def __spiders(self, url):
        '''租房信息爬取'''
        page_num = 1
        params = None 
        while True:
            print("正在爬取{}--第{}页数据...".format(self.city, page_num))
            time.sleep(2)
            # url = format_url.format(page_num)
            response = self.__get_html_source(url, params)
            self.__get_price(response)       

            # 判断是否还有下一页
            url = self.__is_exist_next_page(response)
            print(url)
            if not url:
                print("{}爬取完毕".format(self.city))
                return
            page_num += 1

    def __spiders2(self, url):
        '''买房信息爬取'''
        params = None
        time.sleep(1)

        url_h = url + "h2_s1/"
        url_l = url + "h2_s2/"
        
        self.highest, self.unit_h, self.area_h = self.__get_xinfang_info(url_h, params)
        self.lowest, self.unit_l, self.area_l = self.__get_xinfang_info(url_l, params)

            
    
        
# //*[@id="tab-customer"]
if __name__ == '__main__':
    city20 = ["重庆","上海","北京","成都","天津","广州","深圳","武汉",
              "南阳","临沂","石家庄","哈尔滨","苏州","保定","郑州","西安",
              "赣州","邯郸","温州","潍坊"]
    # city20 = ["重庆"]
    city_58 = Info_58()
    zufang_list = []
    xinfang_list = []
    for city in city20:
        # city_58.highest = 0
        # city_58.lowest = float('inf')
        # city_58.info_zufang(city)
        # zufang_list.append([city, city_58.highest, city_58.lowest])
        city_58.info_xinfang(city)
        xinfang_list.append([city,city_58.highest+'('+city_58.unit_h+')',city_58.area_h,
                             city_58.lowest+'('+city_58.unit_l+')', city_58.area_l])

    columns_z = ["城市", "最高价", "最低价"]
    columns_x = ["城市", "最高价(单位)", "面积(最高)","最低价(单位)","面积(最低)"]
    dt = pd.DataFrame(xinfang_list, columns=columns_x)
    dt.to_csv("buy_csv.csv", mode='a', index=0)
