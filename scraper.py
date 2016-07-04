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

from configparser import ConfigParser
from lxml import html
from lxml  import etree
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from wdstart import start_webdriver
from sendEmail import send_email


class FacebookBot:
    def __init__(self):
        config = ConfigParser()
        #config.read('config.ini')
        config.read_file(open('config.ini', mode='r', encoding='utf8'))

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
            self.search_text = config.get('SETTINGS','SearchText')
            self.price_low = config.get('SETTINGS','PriceLow')
            self.price_high = config.get('SETTINGS','PriceHigh')
            ff_profile_folder = config.get('SETTINGS','FirefoxProfileFolder')
            chrome_profile_folder = config.get('SETTINGS','ChromeProfileFolder')
            self.scrolls_init = int(config.get('SETTINGS','NoOfInitialScrolls'))
            self.scrolls_next = int(config.get('SETTINGS','NoOfScrollsInRecurring'))
            self.is_first_scroll = True
            self.sender_mail = config.get('SETTINGS','SenderMail')
            self.destination_mail = config.get('SETTINGS','DestinationMail')
        except (KeyError, TypeError):
            print('Config file not configured properly!')
            sys.exit()                        

        self.driver = start_webdriver(driver_name='Firefox', profile_path=ff_profile_folder)
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

    def scrape_posts(self):
        self.driver.get(self.group_url)
        body = self.driver.find_element_by_tag_name('body')

        if self.is_first_scroll:
            for x in range(self.scrolls_init):
                body.send_keys(Keys.END)
                time.sleep(2)
            self.is_first_scroll = False
        else:
            for x in range(self.scrolls_next):
                body.send_keys(Keys.END)
                time.sleep(2)
        see_mores = self.driver.find_elements_by_xpath('//a[@class="see_more_link"]')
        for see_more in see_mores:
            self.driver.execute_script('return arguments[0].scrollIntoView();', see_more)
            self.driver.execute_script('window.scrollBy(0, -150);')
            see_more.click()

        #page = self.driver.page_source
        #tree = html.fromstring(page.encode('utf-8'))

        #posts = tree.xpath('.//div[@class="userContentWrapper _5pcr"]')
        posts = self.driver.find_elements_by_css_selector('div.userContentWrapper._5pcr')
        self.posts_data = []

        for post in posts:
            #text = '\n'.join(post.xpath('.//div[@class="_5pbx userContent"]/div[1]/div[1]/p/text()'))
            try:
                text = post.find_element_by_xpath('.//div[contains(@class,"userContent")]').get_attribute('textContent')
                #link = post.xpath('.//a[@class="_5pcq"]/@href')[0]
                link = post.find_element_by_xpath('.//a[contains(@href,"/permalink")]').get_attribute('href')
                #link =  post.find_element_by_css_selector('div._1dwg._1w_m > div._5x46 > div > div > div._5va4 > div > div > div._6a._5u5j._6b > div > span > span > a').get_attribute('href')
                self.posts_data.append([text, link])

            except:
                try:
                    text = post.get_attribute('textContent')
                    link = post.find_element_by_xpath('.//a[contains(@href,"/permalink")]').get_attribute('href')
                    #link =  post.find_element_by_css_selector('div._1dwg._1w_m > div._5x46 > div > div > div._5va4 > div > div > div._6a._5u5j._6b > div > span > span > a').get_attribute('href')
                    self.posts_data.append([text, link])

                except:
                    continue


    def filter_posts(self):
        self.filtered_posts = []

        for x, post in enumerate(self.posts_data):
            regex = re.search(r'\s(\d\d\d\d)\s',post[0], flags=re.I)
            if regex:
                price = regex.group(1) 
                if price <= self.price_high and price >= self.price_low:
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
        links = []
        message_text = u'<table style="width:100%"> <tr> <th>'+text1+'</th> <th>'+text2+'</th> </tr>'
        if os.path.isfile('links.csv'):
            with open('links.csv', 'rt') as f:
                reader = csv.reader(f)
                for row in reader:
                    links.append(str(row))
        new_results = False
        with open('links.csv', mode='a', encoding='utf-8', newline='\n') as f:
            output_writer = csv.writer(f)            
            for item in self.filtered_posts:
                if str([item[1]]) not in links:
                    new_results = True
                    output_writer.writerow([item[1]])
                    message_text += '<tr> <td>'+ item[0]+'</td> <td>'+ item[1] + ' </td> </tr>'
        message_text += '</table>'
        if new_results:
            try:
                send_email(sender=self.sender_mail, to=self.destination_mail,
                        subject='FBGroupScraper Notification', message_text=message_text)
            except:
                pass

    def execute(self):
        self.scrape_posts()
        self.driver.quit()
        self.filter_posts()
        self.save_data()

sys.modules['win32file'] = None
x = int(input('Enter the time of interval between each runs of this script (in minutes): '))

while True:
    bot = FacebookBot()
    bot.execute()
    time.sleep(x*60)
