import codecs
import csv
import smtplib
import sys
import time
import re
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


class FacebookBot:
    def __init__(self, emailpassword):
        config = ConfigParser()
        config.read('config.ini')

        #try:
        #    self.send_email('milmanao@gmail.com', password='111', to='milmanao@gmail.com',
        #                subject='FBGroupScraper Notification', message_text='test')
        #except:
        #    pass

        if not config:
            print('Config file not available!')
            sys.exit()

        try:
            self.login_username = config.get('SETTINGS','Username')
            self.group_url = config.get('SETTINGS','GroupURL')
            self.search_text = config.get('SETTINGS','SearchText')
            self.price_low = config.get('SETTINGS','PriceLow')
            self.price_high = config.get('SETTINGS','PriceHigh')
            profile_folder = config.get('SETTINGS','FirefoxProfileFolder')
            self.scrolls = int(config.get('SETTINGS','NoOfScrolls'))
            self.sender_mail = config.get('SETTINGS','SenderMail')
            self.destination_mail = config.get('SETTINGS','DestinationMail')
        except (KeyError, TypeError):
            print('Config file not configured properly!')
            sys.exit()                        

        self.sender_mail_password = emailpassword
        self.driver = start_webdriver(driver_name='Firefox', profile_path=profile_folder)

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

        for x in range(self.scrolls):
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
            text = post.find_element_by_xpath('.//div[contains(@class,"userContent")]').get_attribute('textContent')
            try:
                #link = post.xpath('.//a[@class="_5pcq"]/@href')[0]
                link = post.find_element_by_xpath('.//a[contains(@href,"/permalink")]').get_attribute('href')
                #link =  post.find_element_by_css_selector('div._1dwg._1w_m > div._5x46 > div > div > div._5va4 > div > div > div._6a._5u5j._6b > div > span > span > a').get_attribute('href')
            except IndexError:
                continue

            self.posts_data.append([text, link])

    def filter_posts(self):
        self.filtered_posts = []

        for x, post in enumerate(self.posts_data):
            regex = re.search(r'\s(\d\d\d\d)\s',post[0], flags=re.I)
            if regex:
                price = regex.group(1) 
                if price <= self.price_high and price >= self.price_low:
                    self.filtered_posts.append(post)

        #for post in self.filtered_posts:
        #    post[1] = 'http://www.facebook.com' + post[1]

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
        date_time = now.strftime('%Y-%m-%d-%H-%M-%S')
        message_text = u'Message: {}\nLink: {}\n\n'

        with codecs.open(date_time + '.csv', mode='wb') as f:
            output_writer = csv.writer(f)

            for item in self.filtered_posts:
                output_writer.writerow(str(item[1]))
                message_text += item[0]+'\t'+ item[1]

        try:
            self.send_email(sender=self.sender_mail, password=self.sender_mail_password, to=self.destination_mail,
                        subject='FBGroupScraper Notification', message_text=message_text)
        except:
            pass

    def execute(self):
        self.scrape_posts()
        self.driver.quit()
        self.filter_posts()
        self.save_data()


x = int(input('Enter the time of interval between each runs of this script (in minutes): '))
emailpassword = getpass('Enter your Email account\'s password: ')

while True:
    bot = FacebookBot(emailpassword)
    bot.execute()
    time.sleep(x*60)
