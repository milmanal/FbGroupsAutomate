import codecs
import csv
import smtplib
import sys
import time
import re
import os.path
from getpass import getpass
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from random import randint

from configparser import ConfigParser
from lxml import html
from lxml  import etree
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from wdstart import start_webdriver
from sendEmail import send_email

is_first_scroll = True
cycleNo = 0

class FacebookBot:
    def __init__(self):
        config = ConfigParser()
        #config.read('config.ini')
        config.read_file(open('config.ini', mode='r', encoding='windows-1255'))

        #try:
        #    self.send_email('milmanao@gmail.com', password='111', to='milmanao@gmail.com',
        #                subject='FBGroupScraper Notification', message_text='test')
        #except:
        #    pass

        if not config:
            print('Config file not available!')
            sys.exit()

        try:
            self.group_url = config.get('SETTINGS','GroupURL')
            self.yad2_url = config.get('SETTINGS','Yad2Url')
            self.yad2_pages_to_scroll = int(config.get('SETTINGS','Yad2Pages'))
            self.send_yad2_first_time = True
            if config.has_option('SETTINGS','Yad2IsSendMailFirstRun'):
               Yad2IsSendMailFirstRun = config.get('SETTINGS','Yad2IsSendMailFirstRun')
               if Yad2IsSendMailFirstRun == 'No' or Yad2IsSendMailFirstRun == 'False':
                   self.send_yad2_first_time = False
            self.driver_name = config.get('SETTINGS','Driver')
            self.search_text = config.get('SETTINGS','ContainsText')
            self.textsNotToContain = config.get('SETTINGS','DoesntContainsText')
            self.price_low = config.get('SETTINGS','PriceLow')
            self.price_high = config.get('SETTINGS','PriceHigh')
            ff_profile_folder = config.get('SETTINGS','FirefoxProfileFolder')
            chrome_profile_folder = config.get('SETTINGS','ChromeProfileFolder')
            self.scrolls_init = int(config.get('SETTINGS','NoOfInitialScrolls'))
            self.scrolls_next = int(config.get('SETTINGS','NoOfScrollsInRecurring'))
            self.is_first_scroll = True
            self.sender_mail = config.get('SETTINGS','SenderMail')
            self.destination_mail = config.get('SETTINGS','DestinationMail')
            self.links = []
            if os.path.isfile('links.csv'):
                with open('links.csv', 'rt') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        self.links.append(str(row))
        except (KeyError, TypeError):
            print('Config file not configured properly!')
            sys.exit()                        

        self.driver = start_webdriver(self.driver_name, profile_path=ff_profile_folder)
        #self.driver = start_webdriver(driver_name='chrome', profile_path=chrome_profile_folder)

    def facebook_login(self):
        self.driver.get('http://www.facebook.com')
        WebDriverWait(self.driver, 30).until(
            EC.title_is('Facebook - Log In or Sign Up'))

        email = self.driver.find_element_by_name('email')
        pas = self.driver.find_element_by_name('pass')
        email.send_keys(self.login_username)
        pas.send_keys(self.login_password)
        email.submit()

    def scrap_yad2_posts(self):
        self.posts_data = []
        with open('links.csv', mode='a', encoding='utf-8', newline='\n') as f:
            output_writer = csv.writer(f)
        times = 1
        if  self.yad2_pages_to_scroll:
            times = self.yad2_pages_to_scroll
        if  self.yad2_url:
            for i in range(0,times):
                self.driver.get(self.yad2_url)
                #nextUrl = self.driver.find_element_by_xpath('//a[@class="next"]').get_attribute('href')
                nextUrl = self.yad2_url + '&page={0}'.format(i+2)
                body = self.driver.find_element_by_tag_name('body')

                #page = self.driver.page_source
                #tree = html.fromstring(page.encode('utf-8'))

                #posts = tree.xpath('.//div[@class="userContentWrapper _5pcr"]')
                posts = self.driver.find_elements_by_xpath('//tr[contains(@class,"showPopupUnder")]')

                for post in posts:
                    #text = '\n'.join(post.xpath('.//div[@class="_5pbx userContent"]/div[1]/div[1]/p/text()'))
                    try:
                        adRows = post.find_elements_by_xpath('./td[contains(@onclick,"show_ad")]')
                        maxIndex = len(adRows)-1
                        adRow = adRows[randint(0,maxIndex)]
                        adRowtext = adRow.get_attribute('onclick')
                        regex = re.search(r'NadlanID\',\'([^\']+)\'',adRowtext, flags=re.I)
                        adId = ''
                        if regex:
                            adId = regex.group(1)
                        if self.links_contain_ad(adId):
                            continue
                        sleep = randint(0,30)
                        time.sleep(sleep)
                        adRow.click()
                        iframeXpath = '//iframe[contains(@src,"'+adId+'")]'
                        iframe = self.driver.find_element_by_xpath(iframeXpath)
                        link = 'http://yad2.co.il' + iframe.get_attribute('src')
                        self.driver.switch_to_frame(iframe)
                        text = self.driver.find_element_by_xpath('//table[@class="innerDetailsDataGrid"]').get_attribute('textContent')
                        text = self.prettifyText(text)
                        #link = post.xpath('.//a[@class="_5pcq"]/@href')[0]
                        #link = 'http://yad2.co.il' + post.find_element_by_xpath('.//iframe').get_attribute('src')
                        self.driver.switch_to_default_content()
                        time.sleep(30-sleep)
                        adRow.click()
                        #link =  post.find_element_by_css_selector('div._1dwg._1w_m > div._5x46 > div > div > div._5va4 > div > div > div._6a._5u5j._6b > div > span > span > a').get_attribute('href')
                        if self.send_yad2_first_time is True:
                            self.posts_data.append([text, link])
                        self.scraped_links.append([link])
                        
                    except Exception as e:
                         print (e)

                self.yad2_url = nextUrl;
        self.filter_posts(False)

    def links_contain_ad(self,text):
        for link in self.links:
            if text in link:
                return True
        return False 
                      
    def prettifyText(self,text):

        text = re.sub(r'\n+', r'\n', text.strip())
        text = re.sub(r'\s+', r' ', text)

        return text
        

    def scrape_fb_posts(self):
        for group_url in self.group_url.split(","):
            self.driver.get(group_url)
            body = self.driver.find_element_by_tag_name('body')

            if is_first_scroll:
                for x in range(self.scrolls_init):
                    body.send_keys(Keys.END)
                    time.sleep(2)
            else:
                for x in range(self.scrolls_next):
                    body.send_keys(Keys.END)
                    time.sleep(2)
            see_mores = self.driver.find_elements_by_xpath('//a[@class="see_more_link"]')
            for see_more in see_mores:
                try:
                    if self.driver_name == 'chrome':
                        see_more.send_keys(Keys.RETURN)
                    else:
                        self.driver.execute_script(see_more, 'return arguments[0].scrollIntoView();', see_more)
                        self.driver.execute_script('window.scrollBy(0, -150);')
                        see_more.click()
                except:
                    continue
            #page = self.driver.page_source
            #tree = html.fromstring(page.encode('utf-8'))

            #posts = tree.xpath('.//div[@class="userContentWrapper _5pcr"]')
            posts = self.driver.find_elements_by_css_selector('div.userContentWrapper._5pcr')

            for post in posts:
                #text = '\n'.join(post.xpath('.//div[@class="_5pbx userContent"]/div[1]/div[1]/p/text()'))
                try:
                    text = post.find_element_by_xpath('.//div[contains(@class,"userContent")]').get_attribute('textContent')                    
                    #link = post.xpath('.//a[@class="_5pcq"]/@href')[0]
                    link = post.find_element_by_xpath('.//a[contains(@href,"/permalink")]').get_attribute('href')
                    #link =  post.find_element_by_css_selector('div._1dwg._1w_m > div._5x46 > div > div > div._5va4 > div > div > div._6a._5u5j._6b > div > span > span > a').get_attribute('href')
                    self.posts_data.append([text, link])
                    self.scraped_links.append([link])

                except:
                    try:
                        text = post.get_attribute('textContent')
                        link = post.find_element_by_xpath('.//a[contains(@href,"/permalink")]').get_attribute('href')
                        #link =  post.find_element_by_css_selector('div._1dwg._1w_m > div._5x46 > div > div > div._5va4 > div > div > div._6a._5u5j._6b > div > span > span > a').get_attribute('href')
                        self.posts_data.append([text, link])
                        self.scraped_links.append([link])

                    except:
                        continue
        self.filter_posts(True)


    def filter_posts(self, isFilterPrice):
        for x, post in enumerate(self.posts_data):
            priceRegexGood = True
            if isFilterPrice is True:
                regex = re.search(r'\D(\d(,)?\d\d\d)\D',post[0], flags=re.I)
                if regex:
                    price = regex.group(1).replace(',','')
                    if price > self.price_high or price < self.price_low:
                        priceRegexGood = False
                else:
                    priceRegexGood = False
            if priceRegexGood:
                qualifiersGood = True
                for qualifier in self.search_text.split(","):
                    if qualifier.strip() not in post[0]:
                        qualifiersGood = False
                        break
                if qualifiersGood:
                    textsNotToContainNotFound = True
                    for textNotToContain in self.textsNotToContain.split(","):
                        if textNotToContain.strip() in post[0]:
                            textsNotToContainNotFound = False
                            break
                    if priceRegexGood and qualifiersGood and textsNotToContainNotFound:
                        self.filtered_posts.append(post)
            

    def send_email(self, sender, password, to, subject, message_text):
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = to
        msg['Subject'] = subject
        body = message_text
        msg.attach(MIMEText(body.encode('utf-8'), 'plain', 'utf-8'))
        server = smtplib.SMTP('smtpout.asia.secureserver.net')
        #server.starttls()
        server.login('michael@shimeba.com', '')
        text = msg.as_string()
        server.sendmail(sender, to, text)
        server.quit()

    def save_data(self):
        now = datetime.now()
        #date_time = now.strftime('%Y-%m-%d-%H-%M-%S')
        message_text = u'Message: {}\nLink: {}\n\n'
        text1 = u'מודעה'
        text2 = u'לינק'
        #new_links = []
        message_text = u'<table style="width:100%"> <tr> <th>'+text1+'</th> <th>'+text2+'</th> </tr>'

        new_results = False

        
        
        for item in self.filtered_posts:
            if str([item[1]]) not in self.links and [str([item[1]])] not in self.links:
                    new_results = True
                    #new_links.append(item[1])
                    message_text += '<tr> <td>'+ item[0]+'</td> <td>'+ item[1] + ' </td> </tr>'
        message_text += '</table>'
        if new_results:
            try:
                send_email(sender=self.sender_mail, to=self.destination_mail,
                        subject='FBGroupScraper Notification', message_text=message_text)
                with open('links.csv', mode='a', encoding='utf-8', newline='\n') as f:
                    output_writer = csv.writer(f)
                    for item in self.scraped_links:
                        output_writer.writerow(item)
                         
            except:
                pass

    def execute(self):
        self.scraped_links = []
        self.posts_data = []
        self.filtered_posts = []
        self.scrape_fb_posts()
        self.scrap_yad2_posts()
        self.driver.quit()
        self.save_data()

sys.modules['win32file'] = None
x = int(input('Enter the time of interval between each runs of this script (in minutes): '))

while True:
    bot = FacebookBot()
    cycleNo = cycleNo+1
    bot.execute()
    is_first_scroll = False
    time.sleep(x*60)
