# -*- coding:utf-8 -*-
import time
import sys, codecs

import os, os.path
import urllib.error
import urllib.request
from datetime import datetime as dt
import time
import datetime
import re
import lxml.html
#import logging
import requests
import logging.config
import traceback
from time import sleep
from yaget.integrations.chrome_driver import CommonChromeDriver
from yaget.models import YaBuyersItemList, YaBuyersItemDetail, WowmaCatTagOyaList, WowmaTagChildList
from yaget.integrations.wowma_access import WowmaAccess
import selenium
import csv
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.keys import Keys

# logging
#logging.basicConfig(filename='/app/yaget/management/commands/log/yashop_amamws.log', level=logging.DEBUG)
logging.config.fileConfig(fname="/app/yaget/management/commands/ya_buyers_list_logging.config", disable_existing_loggers=False)

logger = logging.getLogger(__name__)

#logger.setLevel(20)

# 共通変数
mydwsrc_dir = "/app/yaget/yabuyers/dwsrc"
mydwimg_dir = "/app/yaget/yabuyers/dwimg/"
myupdcsv_dir = "/app/yaget/yabuyers/updcsv/"

UPLOAD_DIR = '/app/yaget/wowma_buyers/dwcsv/'
DONE_CSV_DIR = '/app/yaget/wowma_buyers/donecsv/'
USER_DATA_DIR = '/app/yaget/wowma_buyers/userdata/'

def failure(e):
    exc_type, exc_obj, tb = sys.exc_info()
    lineno = tb.tb_lineno
    return str(lineno) + ":" + str(type(e))


# sys.stdout = codecs.getwriter('utf_8')(sys.stdout)

class BuyersInfo(object):
    def __init__(self, logger):
        self.logger = logger
        help = 'get from ya buyers list.'
        self.logger.info('buyers_info in. init')
        self.common_chrome_driver = None
        self.upd_csv = []
        self.wowma_access = WowmaAccess(self.logger)
        self.bubrandinfo_obj = BuyersBrandInfo(self.logger)

    # 指定されたURLをリクエスト
    def _get_page_no_tor(self, url):
        retry_cnt = 3
        for i in range(1, retry_cnt + 1):
            try:
                self.common_chrome_driver.driver.get(url)
                # driver.get('https://www.amazon.co.jp/dp/B073QT4NMH/')
            except Exception as e:
                self.logger.info(traceback.format_exc())
                self.logger.info('webdriver error occurred start retry..')
                self.common_chrome_driver.restart_chrome_no_tor(USER_DATA_DIR)
                sleep(3)
            else:
                break

    # バイヤーズにログインしておく
    # ※　common_chrome_driver　の初期化はここでやってるので、バッチ呼び出しの場合は必ずこれを呼ぶこと
    def login_buyers(self):
        try:
            self.logger.info('login_buyers start.')

            self.common_chrome_driver = CommonChromeDriver(self.logger)
            self.common_chrome_driver.init_chrome_with_no_tor(USER_DATA_DIR)


            # バイヤーズのtopページ
            start_url = 'https://buyerz.shop/'
            self._get_page_no_tor(start_url)

            # ログインボタンを押す
            sleep(1)
            self.common_chrome_driver.driver.execute_script("ssl_login('login')")
            sleep(3)

            # ログインページにログイン情報入力
            user_email = 'doublenuts8@gmail.com'
            user_pw = 'NagoY888'
            #self.common_chrome_driver.driver.find_element_by_id("id").send_keys(user_email)
            self.common_chrome_driver.driver.execute_script('document.getElementsByName("id")[0].value="%s";' % user_email)
            self.common_chrome_driver.driver.execute_script('document.getElementsByName("passwd")[0].value="%s";' % user_pw)
            self.common_chrome_driver.driver.execute_script("login_check()")
            sleep(5)

            # ページ遷移したかどうか
            tdatetime = dt.now()
            tstr = tdatetime.strftime('%Y%m%d_%H%M%S')
            tfilename = tstr + '_y_src_login.txt'
            tfpath = mydwsrc_dir + '/detail/' + tfilename
            # f = open(tfpath, mode='w')
            f = codecs.open(tfpath, 'w', 'utf-8')

            f.write(self.common_chrome_driver.driver.page_source)
            # f.write(src_1)
            f.close()

            self.logger.info('login_buyers end.')

        except Exception as e:
            self.logger.info(traceback.format_exc())
            raise Exception("バイヤーズのログインに失敗しました。")

        return True

    # バイヤースの商品詳細ページに遷移して、カートに一つ入れる。要ログイン済みであること
    """
    shop_info_list:
        "shop_name": shop_info.shop_name,
        "from_name": shop_info.from_name,
        "from_name_kana": shop_info.from_name_kana,
        "from_postcode": shop_info.from_postcode,
        "from_state": shop_info.from_state,
        "from_address_1": shop_info.from_address_1,
        "from_address_2": shop_info.from_address_2,
        "from_phone": shop_info.from_phone,
        "mail": shop_info.mail,    

    order_receiver_list
        "sender_name": wow_order.sender_name,
        "sender_kana": wow_order.sender_kana,
        "sender_zipcode": wow_order.sender_zipcode,
        "sender_address": wow_order.sender_address,
        "sender_phone_number_1": wow_order.sender_phone_number_1,
        "sender_phone_number_2": wow_order.sender_phone_number_2,

    payment_method
        (0, 'ポイント支払い'), (1, 'au pay'), (2, 'クレジットカード'), (3, 'ゆうちょ振り込み')
    """
    def get_buyers_detail_page(self, detail_url, shop_info_list, order_receiver_list, payment_method):
        try:
            self.logger.info('get_buyers_detail_page start.')

            #self.common_chrome_driver = CommonChromeDriver(self.logger)
            #self.common_chrome_driver.init_chrome_with_no_tor(USER_DATA_DIR)

            # バイヤーズの詳細ページをロード
            self._get_page_no_tor(detail_url)

            # カートに入れるを押す
            sleep(3)
            self.common_chrome_driver.driver.execute_script("send('','')")
            self.logger.info(' カートに入れる ok')

            # バスケットに入ったら購入を続けるボタンを押下
            sleep(3)
            self.common_chrome_driver.driver.execute_script("sslorder()")
            self.logger.info(' 購入ボタンを押す ok')

            # 確認ページ
            # 以下は aupay の選択。もしポイント払いを増やすなら　payment_method　をチェックすること
            sleep(5)
            #self.logger.info(' 購入ページ[{}]'.format(str(self.common_chrome_driver.driver.page_source)))
            payment_total = str(self.common_chrome_driver.driver.find_element_by_xpath(
                "//p[@class='basketTotalPrice']").text).replace(',','').replace('円','')
            self.logger.info(' 購入価格[{}]'.format(payment_total))
            # 確認ページで順次入力していく

            self.common_chrome_driver.driver.find_element_by_id("sender_name").clear()

            self.logger.info(' sender[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("sender_name").get_attribute('value'))
            )

            self.common_chrome_driver.driver.find_element_by_id("sender_name").send_keys(shop_info_list['from_name'])

            self.logger.info(' sender[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("sender_name").get_attribute('value'))
            )

            self.common_chrome_driver.driver.find_element_by_id("sender_kana").clear()
            self.common_chrome_driver.driver.find_element_by_id("sender_kana").send_keys(shop_info_list['from_name_kana'])

            self.logger.info(' sender_kana[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("sender_kana").get_attribute('value'))
            )

            self.common_chrome_driver.driver.find_element_by_id("sender_tel1_1").clear()
            self.common_chrome_driver.driver.find_element_by_id("sender_tel1_1").send_keys(
                shop_info_list['from_phone'].split('-')[0])

            self.logger.info(' sender_tel1_1[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("sender_tel1_1").get_attribute('value'))
            )

            sleep(1)

            self.common_chrome_driver.driver.find_element_by_id("sender_tel1_2").clear()
            self.common_chrome_driver.driver.find_element_by_id("sender_tel1_2").send_keys(
                shop_info_list['from_phone'].split('-')[1])

            self.logger.info(' sender_tel1_2[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("sender_tel1_2").get_attribute('value'))
            )

            self.common_chrome_driver.driver.find_element_by_id("sender_tel1_3").clear()
            self.common_chrome_driver.driver.find_element_by_id("sender_tel1_3").send_keys(
                shop_info_list['from_phone'].split('-')[2])

            self.logger.info(' sender_tel1_3[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("sender_tel1_3").get_attribute('value'))
            )

            self.common_chrome_driver.driver.find_element_by_id("sender_email").clear()
            self.common_chrome_driver.driver.find_element_by_id("sender_email").send_keys(shop_info_list['mail'])

            self.logger.info(' sender_email[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("sender_email").get_attribute('value'))
            )

            sleep(1)
            self.common_chrome_driver.driver.find_element_by_id("sender_post").clear()
            self.common_chrome_driver.driver.find_element_by_id("sender_post").send_keys(
                shop_info_list['from_postcode'].replace('-',''))

            self.logger.info(' sender_post[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("sender_post").get_attribute('value'))
            )

            #self.common_chrome_driver.driver.find_element_by_id("sender_area").clear()
            #self.common_chrome_driver.driver.find_element_by_id("sender_area").send_keys(shop_info_list['from_state'])
            sender_area = self.common_chrome_driver.driver.find_element_by_id("sender_area")
            select_sender_area = Select(sender_area)
            select_sender_area.select_by_visible_text(shop_info_list['from_state'])

            self.logger.info(' sender_area[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("sender_area").get_attribute('value'))
            )

            self.common_chrome_driver.driver.find_element_by_id("sender_addr").clear()
            self.common_chrome_driver.driver.find_element_by_id("sender_addr").send_keys(shop_info_list['from_address_1'])

            self.logger.info(' sender_addr[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("sender_addr").get_attribute('value'))
            )

            self.common_chrome_driver.driver.find_element_by_id("sender_addr2").clear()
            self.common_chrome_driver.driver.find_element_by_id("sender_addr2").send_keys(shop_info_list['from_address_2'])

            self.logger.info(' sender_addr2[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("sender_addr2").get_attribute('value'))
            )

            sleep(1)
            self.common_chrome_driver.driver.find_element_by_id("receiver_user_type_N").click()
            sleep(1)
            self.common_chrome_driver.driver.find_element_by_id("receiver_name").clear()
            self.common_chrome_driver.driver.find_element_by_id("receiver_name").send_keys(order_receiver_list['sender_name'])
            self.common_chrome_driver.driver.find_element_by_id("receiver_kana").clear()
            self.common_chrome_driver.driver.find_element_by_id("receiver_kana").send_keys(order_receiver_list['sender_kana'])

            self.logger.info(' receiver_name[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("receiver_name").get_attribute('value'))
            )
            self.logger.info(' receiver_kana[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("receiver_kana").get_attribute('value'))
            )


            self.common_chrome_driver.driver.find_element_by_id("receiver_tel_1").clear()
            self.common_chrome_driver.driver.find_element_by_id("receiver_tel_1").send_keys(
                order_receiver_list['sender_phone_number_1'].split('-')[0])

            self.logger.info(' receiver_tel_1[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("receiver_tel_1").get_attribute('value'))
            )

            sleep(1)
            self.common_chrome_driver.driver.find_element_by_id("receiver_tel_2").clear()
            self.common_chrome_driver.driver.find_element_by_id("receiver_tel_2").send_keys(
                order_receiver_list['sender_phone_number_1'].split('-')[1])

            self.logger.info(' receiver_tel_2[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("receiver_tel_2").get_attribute('value'))
            )

            self.common_chrome_driver.driver.find_element_by_id("receiver_tel_3").clear()
            self.common_chrome_driver.driver.find_element_by_id("receiver_tel_3").send_keys(
                order_receiver_list['sender_phone_number_1'].split('-')[2])

            self.logger.info(' receiver_tel_3[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("receiver_tel_3").get_attribute('value'))
            )

            self.common_chrome_driver.driver.find_element_by_id("receiver_post").clear()
            self.common_chrome_driver.driver.find_element_by_id("receiver_post").send_keys(
                order_receiver_list['sender_zipcode'].replace('-',''))

            self.logger.info(' receiver_post[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("receiver_post").get_attribute('value'))
            )


            #self.common_chrome_driver.driver.find_element_by_id("receiver_area").clear()
            #self.common_chrome_driver.driver.find_element_by_id("receiver_area").send_keys(
            #    order_receiver_list['sender_address'].split(' ')[0])
            receiver_area = self.common_chrome_driver.driver.find_element_by_id("receiver_area")
            select_receiver_area = Select(receiver_area)

            # 東京都だったら、23区かそうじゃないかを選ばないといけない
            tmp_rec_area = order_receiver_list['sender_address'].split(' ')[0]
            tmp_rec_sub_area = order_receiver_list['sender_address'].split(' ')[1] # 区を抽出したい

            if tmp_rec_area == '東京都':
                tokyo_area = ['足立区','墨田区','荒川区','世田谷区','板橋区','台東区','江戸川区','千代田区','大田区',
                              '中央区','葛飾区','豊島区','北区','中野区','江東区','練馬区','品川区','文京区','渋谷区',
                              '港区','新宿区','目黒区','杉並区']
                for tmp_area in tokyo_area:
                    if tmp_area in tmp_rec_sub_area:
                        tmp_rec_area = '東京(23区内)'
                if tmp_rec_area == '東京都': # 23区内じゃなければ23区外に
                    tmp_rec_area = '東京(23区外)'

            #select_receiver_area.select_by_visible_text(order_receiver_list['sender_address'].split(' ')[0])
            select_receiver_area.select_by_visible_text(tmp_rec_area)

            self.logger.info(' receiver_area[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("receiver_area").get_attribute('value'))
            )

            my_tmp_list = order_receiver_list['sender_address'].split(' ')
            for i, my_tmp in enumerate(my_tmp_list):
                self.logger.info(' tmp[{}][{}]'.format(i,my_tmp))

            my_receiver_addr = ''
            my_receiver_addr_2 = '　'

            # split(' ')[1] が空文字の場合は、[2]以降を持ってくる
            tmp_flg = 0
            for i, my_tmp in enumerate(my_tmp_list):
                if len(my_tmp_list) > 2:
                    if i == 1 and my_tmp == '':
                        tmp_flg = 1
                    if tmp_flg == 0 and i == 1:
                        my_receiver_addr = my_tmp
                    if tmp_flg == 0 and i > 1:
                        my_receiver_addr_2 += my_tmp + ' '
                    if tmp_flg == 1 and i == 2:
                        my_receiver_addr = my_tmp
                    if tmp_flg == 1 and i > 2:
                        my_receiver_addr_2 += my_tmp + ' '
                else:
                    if i == 1:
                        my_receiver_addr = my_tmp
                    my_receiver_addr_2 = '　'

            self.common_chrome_driver.driver.find_element_by_id("receiver_addr").clear()
            self.common_chrome_driver.driver.find_element_by_id("receiver_addr").send_keys(my_receiver_addr)
            #order_receiver_list['sender_address'].split(' ')[1])

            self.logger.info(' receiver_addr[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("receiver_addr").get_attribute('value'))
            )

            self.common_chrome_driver.driver.find_element_by_id("receiver_addr2").clear()
            self.common_chrome_driver.driver.find_element_by_id("receiver_addr2").send_keys(my_receiver_addr_2)

            """
            if len(order_receiver_list['sender_address'].split(' ')) > 2:
                self.common_chrome_driver.driver.find_element_by_id("receiver_addr2").clear()
                self.common_chrome_driver.driver.find_element_by_id("receiver_addr2").send_keys(
                    order_receiver_list['sender_address'].split(' ')[2])
            else:
                self.common_chrome_driver.driver.find_element_by_id("receiver_addr2").clear()
                self.common_chrome_driver.driver.find_element_by_id("receiver_addr2").send_keys('-')
            """

            sleep(1)
            self.logger.info(' receiver_addr2[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_id("receiver_addr2").get_attribute('value'))
            )

            # raise Exception
            # ページ遷移したかどうか
            """
            tdatetime = dt.now()
            tstr = tdatetime.strftime('%Y%m%d_%H%M%S')
            tfilename = tstr + '_y_src_detail_1.txt'
            tfpath = mydwsrc_dir + '/detail/' + tfilename
            # f = open(tfpath, mode='w')
            f = codecs.open(tfpath, 'w', 'utf-8')

            f.write(self.common_chrome_driver.driver.page_source)
            # f.write(src_1)
            f.close()
            """
            self.common_chrome_driver.driver.execute_script("send();") # 次ページへ
            #self.common_chrome_driver.driver.find_element_by_name("next_step_button").click()

            sleep(7)

            # 確認ページに来たはず
            # ページ遷移したかどうか
            """
            tdatetime = dt.now()
            tstr = tdatetime.strftime('%Y%m%d_%H%M%S')
            tfilename = tstr + '_y_src_detail_kakunin.txt'
            tfpath = mydwsrc_dir + '/detail/' + tfilename
            # f = open(tfpath, mode='w')
            f = codecs.open(tfpath, 'w', 'utf-8')

            f.write(self.common_chrome_driver.driver.page_source)
            # f.write(src_1)
            f.close()
            """

            #self.logger.info(' 確認ページ[{}]'.format(str(self.common_chrome_driver.driver.page_source)))
            self.logger.info(' 確認ページに遷移した')

            # 確認ページにて
            """
            self.logger.info('kakunin_total:[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_class_name('totalPriceItems-price').value))
            """

            # self.common_chrome_driver.driver.find_element_by_class_name('basketTotalMesseage').text))

            sleep(1)
            self.common_chrome_driver.driver.find_element_by_name("paymethod").click()
            sleep(1)

            self.common_chrome_driver.driver.execute_script("send();") # 次ページへ
            sleep(5)

            # 最終確認画面
            self.logger.info('kakunin_total_最終:[{}]'.format(
                self.common_chrome_driver.driver.find_element_by_class_name('basketTotalTax').text))

            # nextStep(); を押せば注文確定。
            self.common_chrome_driver.driver.execute_script("nextStep();")
            # バイヤーズの発注番号と購入価格を取得して返却する class名とかは要確認！
            return self.common_chrome_driver.driver.find_element_by_class_name('large_font_size').text, payment_total

        except Exception as e:
            self.logger.info(traceback.format_exc())
            raise Exception("バイヤーズの商品詳細ページアクセスに失敗しました。url:[{}]".format(detail_url))

        # うまくいけばここには来ないが
        return False

    # 出品手数料を考慮して利益の出る価格を算出する。
    def get_benefit_price(self, normal_price, commission):
        benefit_price = 500
        if normal_price < 500:
            benefit_price = 300
        elif 500 <= normal_price < 1000:
            benefit_price = 400
        elif 1000 <= normal_price < 2000:
            benefit_price = 500
        elif 2000 <= normal_price < 3000:
            benefit_price = 500
        elif 3000 <= normal_price < 4000:
            benefit_price = 550
        elif 4000 <= normal_price < 5000:
            benefit_price = 600
        else:
            benefit_price = 800

        return int(round(((int(normal_price) * commission) + benefit_price), -2)) + 80

    # ###################################################################
    # ★★★　各バッチなどからも基本的にこいつを呼び出して登録しよう。★★★
    # 詳細ページにアクセスして、DBに登録がなければ新規登録、あれば最新の情報に更新する。
    # こいつはDBを最新化するだけ。wowma、qoo10の更新はしない
    # ss_url: リンク元リストページURL
    # gsrc: リストーページ中の商品サムネイル画像URL
    def get_wowma_buyers_detail(self, d_url, gid, gcd, ss_url, gsrc, my_ct):
        self.logger.debug('get_wowma_buyers_detail in.')

        # ページ取得
        self._get_page_no_tor(d_url)

        """
        # 詳細ページのソースを保存したければここをON
        tdatetime = dt.now()
        tstr = tdatetime.strftime('%Y%m%d_%H%M%S')
        tfilename = tstr + '_y_src_' + str(pcount) + '.txt'
        tfpath = mydwsrc_dir + '/detail/' + tfilename
        # f = open(tfpath, mode='w')
        f = codecs.open(tfpath, 'w', 'utf-8')

        f.write(self.common_chrome_driver.driver.page_source)
        # f.write(src_1)
        f.close()
        """
        #self.common_chrome_driver.driver.close() # closeはフォーカスがあたってるブラウザを閉じるらしい

        # 画像リンクを別ウィンドウ呼び出しで格納する
        #dom.xpath("//div[@id='viewButton']")[0].find('a').attrib['href'].click() # 拡大画像のポップアップリンク
        #self.common_chrome_driver.driver.find_element_by_xpath("//div[@id='viewButton']/a").click()
        #self.logger.debug(' popup_href[' + str(dom.xpath("//div[@id='viewButton']")[0].find('a').attrib['href']) + ']') # 拡大画像のポップアップリンク
        self.logger.debug(' popup_href[' + str(self.common_chrome_driver.driver.find_element_by_xpath("//div[@id='viewButton']/a").get_attribute('href')) + ']')
        self.logger.debug(' popup_href_resub[' + re.sub('javascript:', "", str(self.common_chrome_driver.driver.find_element_by_xpath("//div[@id='viewButton']/a").get_attribute('href'))) + ']')
        tmpscriptln = re.sub('javascript:', "", str(self.common_chrome_driver.driver.find_element_by_xpath("//div[@id='viewButton']/a").get_attribute('href')))
        # tmpgalt = re.sub('◆新品◆', "", tmpgalt)

        self.logger.debug(' popup_text[' + str(self.common_chrome_driver.driver.find_element_by_xpath("//div[@id='viewButton']/a")) + ']')
        self.common_chrome_driver.driver.execute_script(tmpscriptln)

        sleep(3)

        retry_cnt = 3
        for i in range(1, retry_cnt + 1):
            handles = self.common_chrome_driver.driver.window_handles
            if len(handles) == 2:
                break
            else:
                sleep(3)

        self.logger.debug('window handles:len[' + str(len(handles)) + ']')
        #self.common_chrome_driver.driver.switch_to_window(handles[1]) # switch_to_window は古い。switch_to.window が正しい
        self.common_chrome_driver.driver.switch_to.window(handles[1])
        self.logger.debug('source ---' + self.common_chrome_driver.driver.page_source + '---')

        tmpimglist = []
        cnt = 0

        # 画像のurlは20まで登録できるようにする
        # 変数名は動的に
        # 0初期化
        tmp_g_img_src = [""] * 20

        tmp_cnt = 0
        for i in self.common_chrome_driver.driver.find_elements_by_xpath("//div[@id='M_mainImage']/div/img"):
            #self.logger.debug('tmpimgs:len[' + str(len(tmpimgs)) + ']')
            tmpgsrc = i.get_attribute('src')
            self.logger.debug('tmpgsrc[' + str(i) + ']:src[' + str(tmpgsrc) + ']')
            self.logger.info('gid:[' + str(gid) + '] tmpgsrc[' + str(i) + ']:src[' + str(tmpgsrc) + ']')
            tmpimglist.append(tmpgsrc)

            tmp_g_img_src[tmp_cnt] = str(tmpgsrc).rsplit("?", 1)[0]
            #tmp_g_img_src[tmp_cnt] = str(tmpgsrc)
            tmp_cnt += 1

            # 画像保存してみる
            myresponce = requests.get(tmpgsrc)
            if cnt == 0:
                tmpimgfname = str(gid)
            else:
                tmpimgfname = str(gid) + '_' + str(cnt)
            with open(mydwimg_dir + "{}.jpg".format(tmpimgfname), "wb") as myf:
                myf.write(myresponce.content)

            cnt += 1
            if tmp_cnt == 19:
                break

        # 親のウィンドウに戻る
        self.common_chrome_driver.driver.close()
        #self.common_chrome_driver.driver.switch_to_window(handles[0])
        self.common_chrome_driver.driver.switch_to.window(handles[0])

        # 商品詳細の各要素を取得する

        #tmpgid = re.sub('https://buyerz.shop/shopdetail/', "", self.common_chrome_driver.driver.find_element_by_xpath("/html/head/link[@rel='canonical']/@href").text)
        #tmpgid = re.sub('/', "", tmpgid)
        tmpgid = gid

        # 商品名
        tmpgname = self.common_chrome_driver.driver.find_element_by_xpath(
            "//div[@id='itemInfo']/h2").text

        try:
            tmpgname = self.common_chrome_driver.driver.find_element_by_xpath(
                "//div[@id='itemInfo']/h2").text
        except:
            self.logger.info('get_wowma_buyers_detail no page. gid:[{}]'.format(tmpgid))
            return False

        # 商品詳細
        try:
            tmpgdetail = self.common_chrome_driver.driver.find_element_by_xpath(
                "//div[@id='itemInfo']/div[1]/div").text
        except:
            """
            この場合、商品詳細が取れないことがある
            https://buyerz.shop/shopdetail/000000024392/ct1075/page1/order/

            //div[@id='itemInfo']/div[1]/div
            が通常だが、親の
            //div[@id='itemInfo']/div[1]
            にtextが入ってることが。これはこれで処理するか。
            """
            try:
                tmpgdetail = self.common_chrome_driver.driver.find_element_by_xpath(
                    "//div[@id='itemInfo']/div[1]").text
            except:
                # ここまで来て取れなければ、ページが終了していると判断する。
                self.logger.info('get_wowma_buyers_detail maybe no page. 1 gid:[{}]]'.format(tmpgid))
                return False



        # 商品詳細の原文から、変換不能文字だけ変えてしまう
        # 変換する文字。shift-jis変換でコケた文字はここに登録
        # for exchange_words in self.bubrandinfo_obj._MY_EXCHANGE_WORDS:
        for exchange_words in BuyersBrandInfo._MY_EXCHANGE_WORDS:
            tmpgdetail = re.sub(exchange_words[0], exchange_words[1], tmpgdetail)

        # =================================
        # 不要文字削除
        ng_flg = 0
        tmpyct_flg = 0
        # 商品名より削除
        tmpgname_obj = None
        tmpgdetail_obj = None

        tmpgname_obj = self.bubrandinfo_obj.chk_goods_title(tmpgname)
        #tmpgname_obj = BuyersBrandInfo.chk_goods_title(tmpgname)

        # wowmaの商品名はひとまずこれにする。
        tmp_wow_gname = self.bubrandinfo_obj.cut_str(tmpgname_obj[0], 100)
        #tmp_wow_gname = BuyersBrandInfo.cut_str(tmpgname_obj[0], 100)

        # 商品名のmaxは100文字とする
        # qoo10の商品名もひとまずこれにする。
        tmp_qoo_gname = self.bubrandinfo_obj.cut_str(tmpgname_obj[0], 100)
        #tmp_qoo_gname = BuyersBrandInfo.cut_str(tmpgname_obj[0], 100)

        if tmpgname_obj[1] == 1:
            ng_flg = 1

        # 不要文字削除
        # 商品説明より削除
        tmp_wow_worn_key = ""  # もし注意文言があればここに格納する
        tmp_qoo_worn_key = ""  # もし注意文言があればここに格納する
        tmpgdetail_obj = self.bubrandinfo_obj.chk_goods_detail(tmpgdetail)
        #tmpgdetail_obj = BuyersBrandInfo.chk_goods_detail(tmpgdetail)

        # wowma は < >をエスケープ
        tmp_wow_gdetail = tmpgdetail_obj[0]
        tmp_wow_gdetail = re.sub('<', '&lt;', tmp_wow_gdetail)
        tmp_wow_gdetail = re.sub('>', '&gt;', tmp_wow_gdetail)

        # qoo10はそのまま
        tmp_qoo_gdetail = tmpgdetail_obj[0]
        if tmpgdetail_obj[1] == 1:
            ng_flg = 1

        if tmpgdetail_obj[1] == 5:
            ng_flg = 1

        if tmpgdetail_obj[1] == 6:
            tmpyct_flg = 6  # NGワードが商品詳細に含まれる、要確認
            if tmpgdetail_obj[2]:
                tmp_wow_worn_key = tmpgdetail_obj[2]
                tmp_qoo_worn_key = tmpgdetail_obj[2]

        # ===============================
        # 通常価格
        tmpgspprice = int(re.sub("\\D", "",
                             self.common_chrome_driver.driver.find_element_by_xpath(
                                 "//li[@id='M_usualValue']/span").text))

        # wowmaの価格を算出
        # wowmaは10%が手数料なので上乗せして、それに利益率を加える。
        tmp_wow_price = self.get_benefit_price(tmpgspprice, 1.15)

        # qoo10の価格を算出
        # qoo10も10%が手数料なので上乗せして、それに利益率を加える。
        # メガ割用に、1.2に
        tmp_qoo_price = self.get_benefit_price(tmpgspprice, 1.3)

        # ===============================
        # 在庫数の抽出
        if len(self.common_chrome_driver.driver.find_elements_by_xpath(
                "//span[@class='M_item-stock-smallstock']")) == 0:
            # 在庫が取れないときは在庫切れか
            self.logger.debug('get_wowma_buyers_detail cant get [M_item-stock-smallstock].')
            tmpgretail = "0"
        else:
            tmpgretail = str(re.sub("\\D", "",
                                self.common_chrome_driver.driver.find_element_by_xpath(
                                    "//span[@class='M_item-stock-smallstock']").text))
        # wowmaは、チェック前は未出品にする
        tmp_wow_upd_status = 0  # 未掲載
        tmp_wow_on_flg = 0  # 確認待

        # qooは、チェック前は未出品にする
        tmp_qoo_upd_status = 1  # 取引待機= 1、取引可能= 2、取引廃止= 3）
        tmp_qoo_on_flg = 0  # 確認待

        # もし商品名や商品詳細のチェックでNGになっていたらブラックリスト入にする。
        if ng_flg == 1:
            tmp_wow_on_flg = 2  # NG
            tmp_qoo_on_flg = 2  # NG

        # 2021/1/19 テストのため、ブラックリストのチェックはいったん外して 0 （未出品にする）
        #tmp_wow_on_flg = 0
        #tmp_qoo_on_flg = 0

        tmpgcode = self.common_chrome_driver.driver.find_element_by_xpath(
            "//div[@id='detailInfo']/ul/li[4]").text

        # ===================================================
        # カテゴリコード　チェック
        # カテゴリコードはとりあえず一つ。パンくずの末尾をとってみる
        # URL指定した際の、バイヤーズのカテゴリコードは my_ct で渡されている。
        tmpyct, tmpyct_flg, tmpyct_qoo, tmpyct_qoo_flg = self.get_wow_qoo_ctcd(
            my_ct, tmpgname, tmp_wow_gdetail, tmp_qoo_gdetail)

        """
        2021/10/10
        これまでは、パンくずに記載のあるカテゴリから引いてみたが
        URL指定の際に、既に指定されるカテゴリコードをリストと紐付けて一意で取ってみる形に。
        # wowmaのカテゴリチェック
        tmpyct_obj = self.chk_wow_ct(my_ct, tmpgname, tmp_wow_gdetail)
        tmpyct = tmpyct_obj[0]
        tmpyct_flg = tmpyct_obj[1]
        """


        """
        tmpyct_obj = self.chk_wow_ct(my_ct, tmpgname, tmp_wow_gdetail)
        if tmpyct_obj:
            if tmpyct_obj[1] == 1:
                # サブカテゴリならそのまま採用
                tmpyct = tmpyct_obj[0]
                tmpyct_flg = 1
            elif tmpyct_obj[1] == 2:
                # 大カテゴリなら次を探索
                tmpyct = tmpyct_obj[0]
                tmpyct_flg = 2
            else:
                # その他カテゴリなら次を探索
                tmpyct = tmpyct_obj[0]
                tmpyct_flg = 3

            self.logger.debug('===> tmpct_obj[0]:[{}]'.format(tmpyct_obj[0]))
            self.logger.debug('===> tmpct_obj[1]:[{}]'.format(tmpyct_obj[1]))

        else:
            tmpyct = ""
            tmpyct_flg = 3

        # qoo10のカテゴリチェック
        tmpyct_qoo_obj = self.chk_qoo_ct(my_ct, tmpgname, tmp_qoo_gdetail)
        tmpyct_qoo = tmpyct_qoo_obj[0]
        tmpyct_qoo_flg = tmpyct_qoo_obj[1]
        """

        """
        tmpyct_qoo_obj = self.chk_qoo_ct(my_ct, tmpgname, tmp_qoo_gdetail)
        if tmpyct_qoo_obj:
            if tmpyct_qoo_obj[1] == 1:
                # サブカテゴリなら採用
                tmpyct_qoo = tmpyct_qoo_obj[0]
                tmpyct_qoo_flg = 1
            elif tmpyct_qoo_obj[1] == 2:
                # 大カテゴリなら次を探索
                tmpyct_qoo = tmpyct_qoo_obj[0]
                tmpyct_qoo_flg = 2
            else:
                # その他カテゴリなら次を探索
                tmpyct_qoo = tmpyct_qoo_obj[0]
                tmpyct_qoo_flg = 3

            self.logger.debug('===> tmpyct_qoo_obj[0]:[{}]'.format(tmpyct_qoo_obj[0]))
            self.logger.debug('===> tmpyct_qoo_obj[1]:[{}]'.format(tmpyct_qoo_obj[1]))

        else:
            tmpyct_qoo = ""
            tmpyct_qoo_flg = 3
        """


        """
        for ii in self.common_chrome_driver.driver.find_elements_by_xpath("//p[@class='pankuzu']/a"):
            # カテゴリ一致するかリスト引いて、マッチしたらそいつをセットしてループは抜ける
            tmpct = ii.get_attribute('href')  # 文字はちゃんと整形して

            self.logger.debug('===> tmpct 1:[{}]'.format(tmpct))

            # index は無視
            if re.search('index', tmpct):
                self.logger.debug('===> tmpct:index hit. continue')
                continue

            tmpct = re.sub('https://buyerz.shop/shopbrand/', "", tmpct)
            tmpct = re.sub('/', "", tmpct)

            self.logger.debug('===> tmpct:[{}]'.format(tmpct))

            # wowmaのカテゴリチェック
            tmpyct_obj = self.buinfo_obj.chk_wow_ct(tmpct, tmpgname)
            if tmpyct_obj:
                if tmpyct_obj[1] == 1:
                    # サブカテゴリなら採用
                    tmpyct = tmpyct_obj[0]
                    tmpyct_flg = 1
                    break
                elif tmpyct_obj[1] == 2:
                    # 大カテゴリなら次を探索
                    tmpyct = tmpyct_obj[0]
                    tmpyct_flg = 2
                else:
                    # その他カテゴリなら次を探索
                    tmpyct = tmpyct_obj[0]
                    tmpyct_flg = 3

                self.logger.debug('===> tmpct_obj[0]:[{}]'.format(tmpyct_obj[0]))
                self.logger.debug('===> tmpct_obj[1]:[{}]'.format(tmpyct_obj[1]))

            else:
                tmpyct = ""
                tmpyct_flg = 3

            # qoo10のカテゴリチェック
            tmpyct_qoo_obj = self.buinfo_obj.chk_qoo_ct(tmpct, tmpgname)
            if tmpyct_qoo_obj:
                if tmpyct_qoo_obj[1] == 1:
                    # サブカテゴリなら採用
                    tmpyct_qoo = tmpyct_qoo_obj[0]
                    tmpyct_qoo_flg = 1
                    break
                elif tmpyct_qoo_obj[1] == 2:
                    # 大カテゴリなら次を探索
                    tmpyct_qoo = tmpyct_qoo_obj[0]
                    tmpyct_qoo_flg = 2
                else:
                    # その他カテゴリなら次を探索
                    tmpyct_qoo = tmpyct_qoo_obj[0]
                    tmpyct_qoo_flg = 3

                self.logger.info('===> tmpyct_qoo_obj[0]:[{}]'.format(tmpyct_qoo_obj[0]))
                self.logger.info('===> tmpyct_qoo_obj[1]:[{}]'.format(tmpyct_qoo_obj[1]))

            else:
                tmpyct_qoo = ""
                tmpyct_qoo_flg = 3
        """

        """
        if tmpyct_flg == 0 or tmpyct_flg == 3:
            tmpyct_key_obj = self.chk_ct_by_keyword_for_wowma(tmpgdetail, tmpgname)
            if tmpyct_key_obj:
                tmpyct = str(tmpyct_key_obj)
                tmpyct_flg = 2

        if tmpyct_qoo_flg == 0 or tmpyct_qoo_flg == 3:
            tmpyct_key_qoo_obj = self.chk_ct_by_keyword_for_qoo(tmpgdetail, tmpgname)
            if tmpyct_key_qoo_obj:
                tmpyct_qoo = str(tmpyct_key_qoo_obj)
                tmpyct_qoo_flg = 2


        # ここでtmpyctが取れてない（""のまま）だったらNGか。
        if tmpyct == "":
            self.logger.info('get_wowma_buyers_detail cant match tmpyct.')
            # self.logger.info('----- > _get_wowma_buyers_detail_for_ecauto cant match tmpyct.')
            # return False
        if tmpyct_qoo == "":
            self.logger.info('get_wowma_buyers_detail cant match tmpyct_qoo.')
        # 2021/1/19 仮に、tmpyct にはwowmaのカテゴリコードを割り当てておく
        #tmpyct = "500501"
        #tmpyct_qoo = "500501"
        """

        # ==========================
        # 配送IDの設定をする
        # 本来は、カテゴリコード設定の際に判定しなければいけないが仮に固定で以下。送料無料
        #tmpdeliveryid = 100003
        #tmp_qoo_deliveryid = 100003
        # バイヤーズの配送コードから、wowmaとqoo10の配送区分（無料かどうか）、配送コードを取得
        # 配送コードは 2(送料無料) か3（個別送料）
        tmp_postage_obj = self.bubrandinfo_obj.get_delivery_info(tmpgname_obj[0])
        tmp_postage_segment = tmp_postage_obj[0]

        tmpdeliveryid = tmp_postage_obj[1]
        tmp_qoo_deliveryid = tmp_postage_obj[2]


        # ==========================
        # 個別送料の判定をする。
        # カテゴリコードをチェックなりして、判断。基本は送料込み。
        # 2021/1/19 今はデフォで送料込み
        #tmp_postage_segment = 2
        tmp_postage = 0

        # qoo10関係  ====================================================================================================
        # 個別送料の判定をする。
        # とりあえず仮
        tmp_qoo_shipping_no = 0  # qoo送料コード 0:送料無料
        tmp_qoo_postage = 0
        tmp_qoo_item_qty = "1"  # 商品数量
        tmp_qoo_adult_yn = "N"  #アダルトフラグ

        # 代表画像
        tmp_qoo_standard_img = tmp_g_img_src[0]

        # 検索キーワード　商品詳細から取れたらいいが今は仮。
        tmp_qoo_keyword = ""

        # アフターサービス情報　今は仮
        tmp_qoo_contact_info = ""

        #self.logger.debug('gid:[' + str(tmpgid) + ']')
        self.logger.debug('d-gid:[' + str(gid) + ']')
        self.logger.debug('d-gname:[' + str(tmpgname) + ']')
        self.logger.debug('d-gdetail:[' + str(tmpgdetail) + ']')
        self.logger.debug('d-gspprice:[' + str(tmpgspprice) + ']')
        self.logger.debug('d-gretail:[' + str(tmpgretail) + ']')
        self.logger.debug('d-gcode:[' + str(tmpgcode) + ']')
        self.logger.debug('d-tmpct:[' + str(my_ct) + ']')

        # qoo10 のqoo販売者コードを設定
        # 販売者コードは、ショップ名とかで付け替えるようにしたいが。
        # [Q][先頭ショップ番号1桁][ショップ名略称3文字 ボアソルテはBOA、YUKIショップは YUK]
        tmp_qoo_seller_code = ''
        tmp_qoo_seller_code_pre = 'Q2YUK'
        tmp_qoo_seller_code_num = 10000001
        tmp_obj_matched = YaBuyersItemDetail.objects.filter(gid=tmpgid).first()
        #tmp_obj_matched = YaBuyersItemDetail.objects.get(gid=tmpgid)
        if tmp_obj_matched:
            self.logger.debug('chk qoo_seller_code matched')
            # 登録済みの商品だったら
            tmp_qoo_seller_code = tmp_obj_matched.qoo_seller_code
            if tmp_qoo_seller_code:
                # 設定済みならそのまま使う。
                pass
            else:
                # 未設定なら登録済みのコードから探して+1して採番
                tmp_obj_before = YaBuyersItemDetail.objects.order_by("-qoo_seller_code").first()
                if tmp_obj_before:
                    if tmp_obj_before.qoo_seller_code:
                        # すでに入力済みなら
                        tmp_qoo_seller_code_before = int(str(tmp_obj_before.qoo_seller_code)[5:])
                        tmp_qoo_seller_code = tmp_qoo_seller_code_pre + str(tmp_qoo_seller_code_before + 1)
                    else:
                        # ひっかかるはずだが、ないってことは初番から入れていく
                        tmp_qoo_seller_code = tmp_qoo_seller_code_pre + str(tmp_qoo_seller_code_num)
                else:
                    # ひっかかるはずだが、ないってことは初番から入れていく
                    tmp_qoo_seller_code = tmp_qoo_seller_code_pre + str(tmp_qoo_seller_code_num)
        else:
            self.logger.info('chk qoo_seller_code un_matched')
            # 未登録ならqoo販売者コードを新規に採番する
            tmp_obj_before = YaBuyersItemDetail.objects.order_by("-qoo_seller_code").first()
            if tmp_obj_before:
                if tmp_obj_before.qoo_seller_code:
                    # すでに入力済みなら
                    tmp_qoo_seller_code_before = int(str(tmp_obj_before.qoo_seller_code)[5:])
                    tmp_qoo_seller_code = tmp_qoo_seller_code_pre + str(tmp_qoo_seller_code_before + 1)
                else:
                    # ひっかかるはずだが、ないってことは初番から入れていく
                    tmp_qoo_seller_code = tmp_qoo_seller_code_pre + str(tmp_qoo_seller_code_num)
            else:
                # ひっかかるはずだが、ないってことは初番から入れていく
                tmp_qoo_seller_code = tmp_qoo_seller_code_pre + str(tmp_qoo_seller_code_num)

        # 検索キーワードをそれぞれ設定
        tmp_qoo_keyword = self.set_qoo_keyword(my_ct, tmpgname, int(tmpyct_qoo))
        tmp_wow_keyword = self.set_wow_keyword(my_ct, tmpgname, tmpyct)

        # wowma は検索タグIDを設定。
        tmp_wow_tagid = self.get_wow_tagid_list(my_ct, tmpgname, tmpyct)

        #tmp_qoo_seller_code = None
        # DBに保存
        self.logger.info('start save YaBuyersItemDetail')
        new_obj = YaBuyersItemDetail.objects.filter(gid=tmpgid).first()
        if not new_obj:
            # いったん、問答無用で上書きアップデートする
            self.logger.info('start save YaBuyersItemDetail add.')
            obj, created = YaBuyersItemDetail.objects.update_or_create(
                gid=tmpgid,
                gcode=gcd,
                glink=d_url,
                ss_url=ss_url,
                gsrc=gsrc,
                gname=tmpgname,
                gdetail=tmpgdetail,
                gnormalprice=tmpgspprice,
                stock=int(tmpgretail) if tmpgretail != '' else 0,
                wow_gname=tmp_wow_gname,
                wow_gdetail=tmp_wow_gdetail,
                wow_worn_key=tmp_wow_worn_key,
                wow_price=tmp_wow_price,
                wow_fixed_price=0,
                wow_postage_segment=tmp_postage_segment,  # wowmaの# 送料設定区分 1:送料別/2:送料込み/3:個別送料
                wow_postage=tmp_postage,  # wowmaの個別送料
                wow_ctid=tmpyct,  # wowmaのカテゴリID
                wow_delivery_method_id=tmpdeliveryid,  # wowmaの配送方法ID
                wow_on_flg=tmp_wow_on_flg,
                wow_upd_status=tmp_wow_upd_status,
                wow_keyword=tmp_wow_keyword,
                wow_tagid=tmp_wow_tagid,
                qoo_gname=tmp_qoo_gname,
                qoo_gdetail=tmp_qoo_gdetail,
                qoo_keyword=tmp_qoo_keyword,
                qoo_contact_info=tmp_qoo_contact_info,
                qoo_worn_key=tmp_qoo_worn_key,
                qoo_price=tmp_qoo_price,
                qoo_fixed_price=0,
                qoo_postage_segment=tmp_postage_segment,  # qoo10の# 送料設定区分 1:送料別/2:送料込み/3:個別送料
                qoo_shipping_no=tmp_qoo_shipping_no,  # qooの# qoo送料コード 0:送料無料
                qoo_postage=tmp_qoo_postage,  # qooの個別送料
                qoo_ctid=int(tmpyct_qoo) if tmpyct_qoo != '' else 0,  # qooのカテゴリID
                qoo_delivery_method_id=tmp_qoo_deliveryid,  # qooの配送方法ID
                qoo_item_qty=int(tmp_qoo_item_qty) if tmp_qoo_item_qty != '' else 0,  #商品数量
                qoo_on_flg=tmp_qoo_on_flg,
                qoo_adult_yn=tmp_qoo_adult_yn,
                qoo_upd_status=tmp_qoo_upd_status,
                qoo_seller_code=tmp_qoo_seller_code,
                qoo_standard_img=tmp_qoo_standard_img,
                g_img_src_1=tmp_g_img_src[0],
                g_img_src_2=tmp_g_img_src[1],
                g_img_src_3=tmp_g_img_src[2],
                g_img_src_4=tmp_g_img_src[3],
                g_img_src_5=tmp_g_img_src[4],
                g_img_src_6=tmp_g_img_src[5],
                g_img_src_7=tmp_g_img_src[6],
                g_img_src_8=tmp_g_img_src[7],
                g_img_src_9=tmp_g_img_src[8],
                g_img_src_10=tmp_g_img_src[9],
                g_img_src_11=tmp_g_img_src[10],
                g_img_src_12=tmp_g_img_src[11],
                g_img_src_13=tmp_g_img_src[12],
                g_img_src_14=tmp_g_img_src[13],
                g_img_src_15=tmp_g_img_src[14],
                g_img_src_16=tmp_g_img_src[15],
                g_img_src_17=tmp_g_img_src[16],
                g_img_src_18=tmp_g_img_src[17],
                g_img_src_19=tmp_g_img_src[18],
                g_img_src_20=tmp_g_img_src[19],
            )
            obj.save()
        else:
            self.logger.info('start save YaBuyersItemDetail start update.')
            new_obj.gcode = gcd
            new_obj.glink = d_url
            new_obj.ss_url = ss_url
            new_obj.gsrc = gsrc
            new_obj.gname = tmpgname
            new_obj.gdetail = tmpgdetail
            new_obj.gnormalprice = int(tmpgspprice) if tmpgspprice != '' else 0
            new_obj.stock = int(tmpgretail) if tmpgretail != '' else 0
            new_obj.wow_gname = tmp_wow_gname
            new_obj.wow_gdetail = tmp_wow_gdetail
            new_obj.wow_worn_key = tmp_wow_worn_key
            new_obj.wow_price = tmp_wow_price
            new_obj.wow_fixed_price = 0
            new_obj.wow_postage_segment = tmp_postage_segment  # wowmaの# 送料設定区分 1:送料別/2:送料込み/3:個別送料
            new_obj.wow_postage = tmp_postage  # wowmaの個別送料
            new_obj.wow_ctid = tmpyct  # wowmaのカテゴリID
            new_obj.wow_delivery_method_id = tmpdeliveryid  # wowmaの配送方法ID
            new_obj.wow_on_flg = tmp_wow_on_flg
            new_obj.wow_upd_status = tmp_wow_upd_status
            new_obj.wow_keyword = tmp_wow_keyword
            new_obj.wow_tagid = tmp_wow_tagid
            new_obj.qoo_gname = tmp_qoo_gname
            new_obj.qoo_gdetail = tmp_qoo_gdetail
            new_obj.qoo_keyword = tmp_qoo_keyword
            new_obj.qoo_contact_info = tmp_qoo_contact_info
            new_obj.qoo_worn_key = tmp_qoo_worn_key
            new_obj.qoo_price = tmp_qoo_price
            new_obj.qoo_fixed_price = 0
            new_obj.qoo_shipping_no = tmp_qoo_shipping_no  # qooの# qoo送料コード 0:送料無料
            new_obj.qoo_postage = tmp_qoo_postage  # qooの個別送料
            new_obj.qoo_ctid = int(tmpyct_qoo) if tmpyct_qoo != '' else 0  # qooのカテゴリID
            new_obj.qoo_delivery_method_id = tmp_qoo_deliveryid  # qooの配送方法ID
            new_obj.qoo_item_qty = int(tmp_qoo_item_qty) if tmp_qoo_item_qty != '' else 0  # 商品数量
            new_obj.qoo_on_flg = tmp_qoo_on_flg
            new_obj.qoo_adult_yn = tmp_qoo_adult_yn
            new_obj.qoo_upd_status = tmp_qoo_upd_status
            new_obj.qoo_seller_code = tmp_qoo_seller_code
            new_obj.qoo_standard_img = tmp_qoo_standard_img
            new_obj.g_img_src_1 = tmp_g_img_src[0]
            new_obj.g_img_src_2 = tmp_g_img_src[1]
            new_obj.g_img_src_3 = tmp_g_img_src[2]
            new_obj.g_img_src_4 = tmp_g_img_src[3]
            new_obj.g_img_src_5 = tmp_g_img_src[4]
            new_obj.g_img_src_6 = tmp_g_img_src[5]
            new_obj.g_img_src_7 = tmp_g_img_src[6]
            new_obj.g_img_src_8 = tmp_g_img_src[7]
            new_obj.g_img_src_9 = tmp_g_img_src[8]
            new_obj.g_img_src_10 = tmp_g_img_src[9]
            new_obj.g_img_src_11 = tmp_g_img_src[10]
            new_obj.g_img_src_12 = tmp_g_img_src[11]
            new_obj.g_img_src_13 = tmp_g_img_src[12]
            new_obj.g_img_src_14 = tmp_g_img_src[13]
            new_obj.g_img_src_15 = tmp_g_img_src[14]
            new_obj.g_img_src_16 = tmp_g_img_src[15]
            new_obj.g_img_src_17 = tmp_g_img_src[16]
            new_obj.g_img_src_18 = tmp_g_img_src[17]
            new_obj.g_img_src_19 = tmp_g_img_src[18]
            new_obj.g_img_src_20 = tmp_g_img_src[19]

            new_obj.save()
        """
        # csvに登録
        tmp_csv_row_dict = {
            'gid': str(gid),
            'gname': str(tmpgname),
            'gdetail': str(tmpgdetail),
            'gspprice': str(tmpgspprice),
            'gretail': str(tmpgretail),
            'gcode': str(tmpgcode),
            'tmpct': str(tmpct),
        }
        self.upd_csv.append(tmp_csv_row_dict)
        """

        """
        tdatetime = dt.now()
        tstr = tdatetime.strftime('%Y%m%d_%H%M%S')
        tfilename = tstr + '_y_src_' + str(pcount) + '.txt'
        tfpath = mydwsrc_dir + '/detail/' + tfilename
        # f = open(tfpath, mode='w')
        f = codecs.open(tfpath, 'w', 'utf-8')

        f.write(self.common_chrome_driver.driver.page_source)
        # f.write(src_1)
        f.close()
        """

        # 要素の検証が終わるまで 10 秒待つ
        """
        element = WebDriverWait(self.common_chrome_driver.driver, 10).until(
            EC.presence_of_element_located((By.ID, 'M_imageWrap'))
        )
        self.logger.debug('get_wowma_buyers_detail popup_text[' + element.text + ']')
        """

        #f_read = codecs.open(tfpath, 'r', 'utf-8')
        #s = f_read.read()
        #dom = lxml.html.fromstring(s)

        #dom.xpath("//div[@id='viewButton']")[0].find('a').attrib['href'].click() # 拡大画像のポップアップリンク
        #dom.xpath("//div[@id='viewButton']")[0].find('a').click() # 拡大画像のポップアップリンク
        """
        dom.xpath("//div[@id='viewButton']")[0].find('a').click() # 拡大画像のポップアップリンク
        # 要素の検証が終わるまで 10 秒待つ
        element = WebDriverWait(self.common_chrome_driver.driver, 10).until(
            EC.presence_of_element_located((By.ID, 'M_imageWrap'))
        )
        self.logger.debug('get_wowma_buyers_detail popup_text[' + element.text + ']')
        """

        """
        # 以下要注意・・・まだできてない
        tmpdivs = dom.xpath("//div[@id='detail']") # これ以降調査のこと

        self.logger.debug('start break item detail.')

        for i, j in enumerate(tmpdivs):
            tmp_td_obj = list(j)
            # print(i)
            self.logger.debug('list. i[' + str(i) + ']')
            for ii, jj in enumerate(tmp_td_obj):
                tmpglink = jj.find_class('imgWrap')[0].find('a').attrib['href']
                tmpgsrc = jj.find_class('imgWrap')[0].find('a/img').attrib['src']
                tmpgid = jj.find_class('detail')[0].find_class('else')[0].find('li')[1].text # gコード
                tmpgname = jj.find_class('detail')[0].find_class('name')[0].find('a').text # 商品名
                #tmpgother = re.sub("\\D", "", str(tmpglink).rsplit("/", 1)[1])  # gコード

                self.logger.debug('glink:[' + str(tmpglink) + ']')
                self.logger.debug('gsrc:[' + str(tmpgsrc) + ']')
                self.logger.debug('gid:[' + str(tmpgid) + ']')
                self.logger.debug('gname:[' + str(tmpgname) + ']')
                if ii == 2:
                    break

                # 不要文字削除
                #tmpgalt = re.sub('◆新品◆', "", tmpgalt)

                # ひとまず、リストの一件毎で詳細まで処理してみよう
                # ユニークにするのに、gidの形式がこれでいいかどうか確認すること
        """

        """
                if not YaBuyersItemList.objects.filter(gid=tmpgid).exists():
                    obj, created = YaBuyersItemList.objects.update_or_create(
                        listurl=ss_url,
                        gid=tmpgid,
                        glink=tmpglink,
                        gname=tmpgname,
                        g_img_src=tmpgsrc,
                    )
                    obj.save()
                    # detailはここで取得してみる
                    if self.get_wowma_buyers_detail(tmpglink) = False:
                        # 途中でコケたら止めておこう
                        return False
        """

        self.logger.debug('get_wowma_buyers_detail out.')
        return True

    # https://qiita.com/tomson784/items/88a3fd2398a41932762a 参照
    # 指定された商品詳細のURLに対して在庫チェックする
    # 渡される ss_url は　https://buyerz.shop/shopbrand/ct113/　の形式
    # 登録の手順としては、
    # 1.  バイヤーズから商品情報取得 この時点ではまだ未掲載。フラグを立てる。まだ出品NG　のフラグを
    # 2.  画面から、掲載可否を判断して商品詳細などを編集する。OKなら出品OKのフラグをたてる。NGならブラックリストいり
    # 3.  wow_on_flg、qoo_on_flg　を在庫切れなら 3 で更新する。価格も更新
    # 4.  この処理の後で、wowmaとqoo10は後でまとめて更新をかける。
    def chk_wowma_buyers_stock(self, ss_url, gid, gcode):
        # self.stdout.write('ss_url:' + ss_url)
        # self.stdout.write(self.style.SUCCESS('my_s_url:' + s_url))
        self.logger.info('_chk_wowma_buyers_stock in ssurl:[' + str(ss_url) + ']')

        tmp_wow_on_flg = 0
        tmp_qoo_on_flg = 0

        if not self.common_chrome_driver:
            self.common_chrome_driver = CommonChromeDriver(self.logger)
            self.common_chrome_driver.init_chrome_with_no_tor(USER_DATA_DIR)

        retry_cnt = 3
        for i in range(1, retry_cnt + 1):
            try:
                # ss_url = 'https://buyerz.shop/shop/shopbrand.html?page=1&search=&sort=&money1=&money2=&prize1=&company1=&content1=&originalcode1=&category=&subcategory='
                self.common_chrome_driver.driver.get(ss_url)
                # driver.get('https://www.amazon.co.jp/dp/B073QT4NMH/')
            except Exception as e:
                self.logger.info(traceback.format_exc())
                self.logger.info('_chk_wowma_buyers_stock webdriver error occurred start retry..')
                self.common_chrome_driver.restart_chrome_no_tor(USER_DATA_DIR)
                # self.restart_chrome()
                sleep(3)
            else:
                break

        s = self.common_chrome_driver.driver.page_source
        dom = lxml.html.fromstring(s)

        # 在庫チェックではいまのところ、画像の再取得は行わない。以下はコメントアウト

        tmpimglist = []
        cnt = 0

        # 商品詳細の各要素を取得する

        # tmpgid = re.sub('https://buyerz.shop/shopdetail/', "", self.common_chrome_driver.driver.find_element_by_xpath("/html/head/link[@rel='canonical']/@href").text)
        # tmpgid = re.sub('/', "", tmpgid)
        tmpgid = gid

        # 在庫チェックの際は、商品名と商品詳細は更新する。
        # wowma用に編集したものはそのままにしておく
        # 商品名
        # ※このタイミングで取得できないときはページが消えている。在庫切れとして処理しないと。
        try:
            tmpgname = self.common_chrome_driver.driver.find_element_by_xpath(
                "//div[@id='itemInfo']/h2").text
        except selenium.common.exceptions.NoSuchElementException as no_such_elem:
            self.logger.info('_chk_wowma_buyers_stock no page. insert stock=0]')
            tmp_myobj = YaBuyersItemDetail.objects.filter(gid=tmpgid).first()
            if tmp_myobj:
                # DBを更新
                # 価格はそのまま、在庫は0
                tmp_myobj.stock = 0
                tmp_myobj.wow_on_flg = 3
                tmp_myobj.qoo_on_flg = 3
                tmp_myobj.save()

                # かつ、ここでwowmaとqoo10は更新しないと。
                return True
            else:
                return False

        # 商品詳細
        try:
            tmpgdetail = self.common_chrome_driver.driver.find_element_by_xpath(
                "//div[@id='itemInfo']/div[1]/div").text
        except:
            """
            この場合、商品詳細が取れないことがある
            https://buyerz.shop/shopdetail/000000024392/ct1075/page1/order/

            //div[@id='itemInfo']/div[1]/div
            が通常だが、親の
            //div[@id='itemInfo']/div[1]
            にtextが入ってることが。これはこれで処理するか。
            """
            try:
                tmpgdetail = self.common_chrome_driver.driver.find_element_by_xpath(
                    "//div[@id='itemInfo']/div[1]").text
            except:
                # ここまで来て取れなければ、ページが終了していると判断する。
                self.logger.info('_chk_wowma_buyers_stock maybe no page. insert stock=0 gid:[{}]]'.format(tmpgid))
                tmp_myobj = YaBuyersItemDetail.objects.filter(gid=tmpgid).first()
                if tmp_myobj:
                    # DBを更新
                    # 価格はそのまま、在庫は0
                    tmp_myobj.stock = 0
                    tmp_myobj.wow_on_flg = 3
                    tmp_myobj.qoo_on_flg = 3
                    tmp_myobj.save()

                    # かつ、ここでwowmaとqoo10は更新しないと。
                    return True
                else:
                    return False

        # ===============================
        # 通常価格
        tmpgspprice = int(re.sub("\\D", "",
                                 self.common_chrome_driver.driver.find_element_by_xpath(
                                     "//li[@id='M_usualValue']/span").text))

        # wowmaの価格を算出
        # wowmaは10%が手数料なので上乗せして、それに利益率を加える。
        tmp_wow_price = self.get_benefit_price(tmpgspprice, 1.15)

        # qoo10の価格を算出
        # qoo10も10%が手数料なので上乗せして、それに利益率を加える。
        tmp_qoo_price = self.get_benefit_price(tmpgspprice, 1.3)
        self.logger.info('_chk_wowma_buyers_stock tmp_wow_price[' + str(tmp_wow_price) + ']')

        # ===============================
        # 在庫数の抽出
        if len(self.common_chrome_driver.driver.find_elements_by_xpath(
                "//span[@class='M_item-stock-smallstock']")) == 0:
            # 在庫が取れないときは在庫切れか
            self.logger.debug('_chk_wowma_buyers_stock cant get [M_item-stock-smallstock].')
            tmpgretail = "0"
        else:
            tmpgretail = re.sub("\\D", "",
                                self.common_chrome_driver.driver.find_element_by_xpath(
                                    "//span[@class='M_item-stock-smallstock']").text)
            if tmpgretail == '':
                tmpgretail = "0"
            else:
                # 在庫あり
                tmp_wow_on_flg = 1
                tmp_qoo_on_flg = 1

        if tmpgretail == "0":
            tmp_wow_on_flg = 3
            tmp_qoo_on_flg = 3

        # DBに保存
        myobj = YaBuyersItemDetail.objects.filter(gid=tmpgid).first()
        if myobj:
            self.logger.info('start save YaBuyersItemDetail add.')

            # 既存DBのフラグによってどうステータスを更新するか
            # 出品はまだNG。（画面から編集してない）が、DBの在庫などは更新していい
            # 元のwow_on_flgが、0か2だったら在庫更新はせずそのまま
            if myobj.wow_on_flg == 0 or myobj.wow_on_flg == 2:
                tmp_wow_on_flg = myobj.wow_on_flg
            if myobj.qoo_on_flg == 0 or myobj.qoo_on_flg == 2:
                tmp_qoo_on_flg = myobj.qoo_on_flg

            # DBを更新
            myobj.gnormalprice = int(tmpgspprice)
            myobj.stock = int(tmpgretail)
            myobj.wow_price = tmp_wow_price
            myobj.qoo_price = tmp_qoo_price
            myobj.wow_on_flg = tmp_wow_on_flg
            myobj.qoo_on_flg = tmp_qoo_on_flg
            myobj.save()
        else:
            # ここで指定された商品は必ずDBにあるはずだが、なかった？　何もしない
            self.logger.debug('_chk_wowma_buyers_stock 指定の商品がDBに登録なし？ gid[{}]'.format(tmpgid))

        self.logger.debug('end of _chk_wowma_buyers_stock')

        return True

    # バイヤーズのカテゴリコードが取れていない場合、商品詳細ページのURLから取得する
    # ヒットしなければ空文字のまま
    def get_buyers_ctcd_from_url(self, glink):
        tmp_item = glink.split('/')
        for item in tmp_item:
            if item.startswith('ct'):
                return item
        return ''

    # バイヤーズのカテゴリコードからwowmaとqoo10のカテゴリコードを取得する
    # リターンは wowma_ctid, wowma_flg, qoo_ctid, qoo_flg の4つにしよう
    def get_wow_qoo_ctcd(self, my_ct, tmpgname, tmp_wow_gdetail, tmp_qoo_gdetail):

        # wowmaのカテゴリチェック
        tmpyct_obj = self.chk_wow_ct(my_ct, tmpgname, tmp_wow_gdetail)
        wowma_catid = tmpyct_obj[0]
        wowma_flg = tmpyct_obj[1]

        # qoo10のカテゴリチェック
        tmpyct_qoo_obj = self.chk_qoo_ct(my_ct, tmpgname, tmp_qoo_gdetail)
        qoo_catid = tmpyct_qoo_obj[0]
        qoo_flg = tmpyct_qoo_obj[1]

        if wowma_flg == 0 or wowma_flg == 3:
            tmpyct_key_obj = self.chk_ct_by_keyword_for_wowma(tmp_wow_gdetail, tmpgname)
            if tmpyct_key_obj:
                wowma_catid = str(tmpyct_key_obj)
                wowma_flg = 2

        if qoo_flg == 0 or qoo_flg == 3:
            tmpyct_key_qoo_obj = self.chk_ct_by_keyword_for_qoo(tmp_qoo_gdetail, tmpgname)
            if tmpyct_key_qoo_obj:
                qoo_catid = str(tmpyct_key_qoo_obj)
                qoo_flg = 2

        if wowma_catid == 0:
            self.logger.info('get_wow_qoo_ctcd cant match wowma_catid.')
        if qoo_catid == 0:
            self.logger.info('get_wow_qoo_ctcd cant match qoo_catid.')

        return wowma_catid, wowma_flg, qoo_catid, qoo_flg

    # カテゴリコードをチェックしてマッチしたらwowmaのカテゴリコードと優先順（1,2,3)を返す
    # 優先順は、1が最優先。一つ決まればOK、決まらなければ続けてチェックする
    def chk_wow_ct(self, ctcode, gname, gdetail):

        try:
            # 5桁の大カテゴリより、10桁のサブカテゴリのマッチを優先する
            try:
                result_y_ct = str(__class__._MY_CT_CODES_SMALL[ctcode]["wowma_catid"])
            except KeyError:

                # 10桁サブカテゴリにマッチしなかった。
                # 続いて、いろんなアイテムが紛れ込んでしまっているカテゴリをチェックしておく。
                # ct119 「ファッション > レディース」とか。
                if ctcode in __class__._MY_CT_CODES_SMALL_WARN:
                    for mykey, myvalue in __class__._MY_CT_CODES_KEYWORD.items():
                        #
                        if re.search(mykey, gname):
                            # レディースかメンズは、wowmaではひとまず判定しない
                            if int(myvalue["wowma_catid"]) > 0:
                                return int(myvalue["wowma_catid"]), 1

                            """
                            if myvalue['sex'] == '1':  # sex に 1が設定されてるカテゴリキーワードだけ
                                if re.search('レディース', gname):
                                    return myvalue["female"], 1  # マッチしたとして 1を返却
                                elif re.search('メンズ', gname):
                                    return myvalue["male"], 1
                                else:
                                    return myvalue["wowma_catid"], 1
                            else:
                                return myvalue["wowma_catid"], 1
                            """

                    for mykey, myvalue in __class__._MY_CT_CODES_KEYWORD.items():
                        if re.search(mykey, gdetail):
                            # レディースかメンズは、wowmaではひとまず判定しない
                            if int(myvalue["wowma_catid"]) > 0:
                                return int(myvalue["wowma_catid"]), 1

                    # ここに来ると設定ミス？
                    self.logger.debug('buyers_info cant match chk_ct.　warning code')
                    return 0, 3

                try:
                    # 5桁の大カテゴリにマッチするか
                    result_y_ct = str(__class__._MY_CT_CODES_BIG[ctcode]["wowma_catid"])
                except KeyError:
                    try:
                        # その他、そのままでは登録できないが既出の500円均一などのカテゴリにマッチするか
                        result_y_ct = str(__class__._MY_CT_CODES_OTHER[ctcode]["wowma_catid"])
                    except KeyError:
                        # だめならFalse (0と3を返すようにした)
                        return 0, 3
                    # 大カテゴリにマッチしたらいちおう3を返す
                    return result_y_ct, 3
                # 大カテゴリにマッチしたらいちおう２を返す
                return result_y_ct, 2

            # サブカテゴリにマッチしたら正解
            return result_y_ct, 1

        except Exception as e:
            self.logger.debug(traceback.format_exc())
            return 0, 3

    # カテゴリコードをチェックしてマッチしたらqoo10のカテゴリコードと優先順（1,2,3)を返す
    # 優先順は、1が最優先。一つ決まればOK、決まらなければ続けてチェックする
    def chk_qoo_ct(self, ctcode, gname, gdetail):

        try:
            # 5桁の大カテゴリより、10桁のサブカテゴリのマッチを優先する
            try:
                result_y_ct = str(__class__._MY_CT_CODES_SMALL[ctcode]["qoo_catid"])
            except KeyError:
                # 10桁サブカテゴリにマッチしなかった。
                # 続いて、いろんなアイテムが紛れ込んでしまっているカテゴリをチェックしておく。
                # ct119 「ファッション > レディース」とか。
                if ctcode in __class__._MY_CT_CODES_SMALL_WARN:
                    for mykey, myvalue in __class__._MY_CT_CODES_KEYWORD.items():
                        #
                        if re.search(mykey, gname):
                            # レディースかメンズは、qooではひとまず判定しない
                            if int(myvalue["qoo_catid"]) > 0:
                                self.logger.info('chk_qoo_ct:1: catid決定したはず[{}]'.format(myvalue["qoo_catid"]))
                                return myvalue["qoo_catid"], 1

                            """
                            if myvalue['sex'] == '1':  # sex に 1が設定されてるカテゴリキーワードだけ
                                if re.search('レディース', gname):
                                    return myvalue["female"], 1  # マッチしたとして 1を返却
                                elif re.search('メンズ', gname):
                                    return myvalue["male"], 1
                                else:
                                    return myvalue["wowma_catid"], 1
                            else:
                                return myvalue["wowma_catid"], 1
                            """

                    # 商品名で見つからなかったら商品説明も見る
                    for mykey, myvalue in __class__._MY_CT_CODES_KEYWORD.items():
                        if re.search(mykey, gdetail):
                            # レディースかメンズは、qooではひとまず判定しない
                            if int(myvalue["qoo_catid"]) > 0:
                                self.logger.info('chk_qoo_ct:2: catid決定したはず[{}]'.format(myvalue["qoo_catid"]))
                                return myvalue["qoo_catid"], 1

                    # ここに来ると設定ミス？ _MY_CT_CODES_SMALL_WARN　で指定されてるけど見つけられなかったらFalse
                    self.logger.info('buyers_info cant match 500 qoo_chk_ct.code[{}]'.format(ctcode))
                    return 0, 3

                try:
                    # 5桁の大カテゴリにマッチするか
                    result_y_ct = str(__class__._MY_CT_CODES_BIG[ctcode]["qoo_catid"])
                except KeyError:
                    try:
                        # その他、そのままでは登録できないが既出の500円均一などのカテゴリにマッチするか
                        result_y_ct = str(__class__._MY_CT_CODES_OTHER[ctcode]["qoo_catid"])
                    except KeyError:
                        # だめならFalse
                        return 0, 3
                    # 大カテゴリにマッチしたらいちおう3を返す
                    return result_y_ct, 3
                # 大カテゴリにマッチしたらいちおう２を返す
                return result_y_ct, 2

            # サブカテゴリにマッチしたら正解
            self.logger.info('chk_qoo_ct:10: smallカテに一致。[{}]'.format(result_y_ct))
            return result_y_ct, 1

        except Exception as e:
            self.logger.info(traceback.format_exc())
            return 0, 3

    # カテゴリコードをチェックしてマッチしたらヤフオクのカテゴリコードと優先順（1,2,3)を返す
    # 優先順は、1が最優先。一つ決まればOK、決まらなければ続けてチェックする
    def chk_ct(self, ctcode, gname):

        try:
            # まず、いろんなアイテムが紛れ込んでしまっているカテゴリをチェックしておく。
            if ctcode in __class__._MY_CT_CODES_SMALL_WARN:
                for mykey, myvalue in __class__._MY_CT_CODES_KEYWORD.items():
                    #
                    if re.search(mykey, gname):
                        # レディースかメンズも判定する
                        if myvalue['sex'] == '1':  # sex に 1が設定されてるカテゴリキーワードだけ
                            if re.search('レディース', gname):
                                return myvalue["female"], 1  # マッチしたとして 1を返却
                            elif re.search('メンズ', gname):
                                return myvalue["male"], 1
                            else:
                                return myvalue["y_ct"], 1
                        else:
                            return myvalue["y_ct"], 1

                # ここに来ると設定ミス？
                self.logger.debug('buyers_info cant match chk_ct.　warning code')
                return False

            # 5桁の大カテゴリより、10桁のサブカテゴリのマッチを優先する
            try:
                result_y_ct = str(__class__._MY_CT_CODES_SMALL[ctcode]["y_ct"])
            except KeyError:
                try:
                    # 5桁の大カテゴリにマッチするか
                    result_y_ct = str(__class__._MY_CT_CODES_BIG[ctcode]["y_ct"])
                except KeyError:
                    try:
                        # その他、そのままでは登録できないが既出の500円均一などのカテゴリにマッチするか
                        result_y_ct = str(__class__._MY_CT_CODES_OTHER[ctcode]["y_ct"])
                    except KeyError:
                        # だめならNone
                        return None
                    # 大カテゴリにマッチしたらいちおう3を返す
                    return result_y_ct, 3
                # 大カテゴリにマッチしたらいちおう２を返す
                return result_y_ct, 2

            # サブカテゴリにマッチしたら正解
            return result_y_ct, 1

        except Exception as e:
            self.logger.debug(traceback.format_exc())
            return False

    # qoo10用の検索ワードをセットして返す。商品名のキーワードに含まれないキーワードリストを
    # 30文字 x 10個までセットして半角スペース区切りに。
    # qoo10に登録するときは注意のこと
    def set_qoo_keyword(self, ctcode, gname, qoo_ctid):

        ret_str = ''
        if ctcode == '':
            # wow_ctid から検索しないと。キーワードマッチの場合であろう
            for mykey, myvalue in __class__._MY_CT_CODES_KEYWORD.items():
                if re.search(mykey, gname):
                    # レディースかメンズは、wowmaではひとまず判定しない
                    if myvalue["s_keyword"]:
                        ret_str = self.get_keyword_set(myvalue["s_keyword"], gname, 3)
                        self.logger.debug('set_qoo_keyword found keyword 1')
                        return ret_str
            # 抜けてしまうと失敗。空文字返す
            return ret_str
        else:
            try:
                # _MY_CT_CODES_SMALL には、s_keyword をセットすること
                moto_keyword = str(__class__._MY_CT_CODES_SMALL[ctcode]["s_keyword"])
                self.logger.info('moto_key:[{}]'.format(moto_keyword))
                ret_str = self.get_keyword_set(moto_keyword, gname, 10)
                self.logger.info('ret_str:[{}]'.format(ret_str))
                # 5桁の大カテゴリより、10桁のサブカテゴリのマッチを優先する
                """
                try:
                    # _MY_CT_CODES_SMALL には、s_keyword をセットすること
                    moto_keyword = str(__class__._MY_CT_CODES_SMALL[ctcode]["s_keyword"])
                    ret_str = self.get_keyword_set(moto_keyword, gname, 10)
                except KeyError:
    
                    # 10桁サブカテゴリにマッチしなかった。
                    # 続いて、いろんなアイテムが紛れ込んでしまっているカテゴリをチェックしておく。
                    # ct119 「ファッション > レディース」とか。
                    if ctcode in __class__._MY_CT_CODES_SMALL_WARN:
                        for mykey, myvalue in __class__._MY_CT_CODES_KEYWORD.items():
                            #
                            if re.search(mykey, gname):
                                # レディースかメンズは、wowmaではひとまず判定しない
                                if int(myvalue["wowma_catid"]) > 0:
                                    return myvalue["wowma_catid"], 1
    
                        # ここに来ると設定ミス？
                        self.logger.debug('buyers_info cant match chk_ct.　warning code')
                        return False
    
                    try:
                        # 5桁の大カテゴリにマッチするか
                        result_y_ct = str(__class__._MY_CT_CODES_BIG[ctcode]["wowma_catid"])
                    except KeyError:
                        try:
                            # その他、そのままでは登録できないが既出の500円均一などのカテゴリにマッチするか
                            result_y_ct = str(__class__._MY_CT_CODES_OTHER[ctcode]["wowma_catid"])
                        except KeyError:
                            # だめならNone
                            return ''
                        # 大カテゴリにマッチしたらいちおう3を返す
                        return result_y_ct, 3
                    # 大カテゴリにマッチしたらいちおう２を返す
                    return result_y_ct, 2
    
                # サブカテゴリにマッチしたら、商品名と比較して含まれてないキーワードをセットする
                return result_y_ct, 1
                """
                #ret_str = ''

            except Exception as e:
                self.logger.debug(traceback.format_exc())
                return ret_str  # 空文字を一応返す

        return ret_str
    # wowma用の検索ワードをセットして返す。商品名のキーワードに含まれないキーワードリストを
    # 20文字 x 3個までセットして半角スペース区切りに。
    # wowmaに登録するときは注意のこと
    def set_wow_keyword(self, ctcode, gname, wow_ctid):

        ret_str = ''
        if ctcode == '':
            # wow_ctid から検索しないと。キーワードマッチの場合であろう
            for mykey, myvalue in __class__._MY_CT_CODES_KEYWORD.items():
                if re.search(mykey, gname):
                    # レディースかメンズは、wowmaではひとまず判定しない
                    if myvalue["s_keyword"]:
                        ret_str = self.get_keyword_set(myvalue["s_keyword"], gname, 3)
                        self.logger.debug('set_wow_keyword found keyword 1')
                        return ret_str
            # 抜けてしまうと失敗。空文字返す
            return ret_str
        else:
            try:
                # _MY_CT_CODES_SMALL には、s_keyword をセットすること
                moto_keyword = str(__class__._MY_CT_CODES_SMALL[ctcode]["s_keyword"])
                ret_str = self.get_keyword_set(moto_keyword, gname, 3)
                # 5桁の大カテゴリより、10桁のサブカテゴリのマッチを優先する
                """
                try:
                    # _MY_CT_CODES_SMALL には、s_keyword をセットすること
                    moto_keyword = str(__class__._MY_CT_CODES_SMALL[ctcode]["s_keyword"])
                    ret_str = self.get_keyword_set(moto_keyword, gname, 3)
                except KeyError:
    
                    # 10桁サブカテゴリにマッチしなかった。
                    # 続いて、いろんなアイテムが紛れ込んでしまっているカテゴリをチェックしておく。
                    # ct119 「ファッション > レディース」とか。
                    if ctcode in __class__._MY_CT_CODES_SMALL_WARN:
                        for mykey, myvalue in __class__._MY_CT_CODES_KEYWORD.items():
                            #
                            if re.search(mykey, gname):
                                # レディースかメンズは、wowmaではひとまず判定しない
                                if int(myvalue["wowma_catid"]) > 0:
                                    return myvalue["wowma_catid"], 1
    
                        # ここに来ると設定ミス？
                        self.logger.debug('buyers_info cant match chk_ct.　warning code')
                        return False
    
                    try:
                        # 5桁の大カテゴリにマッチするか
                        result_y_ct = str(__class__._MY_CT_CODES_BIG[ctcode]["wowma_catid"])
                    except KeyError:
                        try:
                            # その他、そのままでは登録できないが既出の500円均一などのカテゴリにマッチするか
                            result_y_ct = str(__class__._MY_CT_CODES_OTHER[ctcode]["wowma_catid"])
                        except KeyError:
                            # だめならNone
                            return ''
                        # 大カテゴリにマッチしたらいちおう3を返す
                        return result_y_ct, 3
                    # 大カテゴリにマッチしたらいちおう２を返す
                    return result_y_ct, 2
    
                # サブカテゴリにマッチしたら、商品名と比較して含まれてないキーワードをセットする
                return result_y_ct, 1
                """
                #ret_str = ''

            except KeyError:
                #self.logger.debug(traceback.format_exc())
                #return ret_str  # 空文字を一応返す
                # 10桁サブカテゴリにマッチしなかった。
                # 続いて、いろんなアイテムが紛れ込んでしまっているカテゴリをチェックしておく。
                # ct119 「ファッション > レディース」とか。
                if ctcode in __class__._MY_CT_CODES_SMALL_WARN:
                    for mykey, myvalue in __class__._MY_CT_CODES_KEYWORD.items():
                        #
                        if re.search(mykey, gname):
                            # レディースかメンズは、wowmaではひとまず判定しない
                            if myvalue["s_keyword"]:
                                ret_str = self.get_keyword_set(myvalue["s_keyword"], gname, 3)
                                return ret_str

                    # ここに来ると設定ミス？
                    self.logger.debug('buyers_info cant match chk_ct.　warning code')
                    return False

        return ret_str

    # wowma用のタグIDをセットして返す。商品名のキーワードにマッチする検索タグを
    # 64個までセットして半角スペース区切りに。
    # wowmaに登録するときは注意のこと
    # タグとカテゴリとのマッピングはこちら wow_cat
    # https://docs.google.com/spreadsheets/d/1XLHXkiE-_p11nYUFy2TFOsQonWJb7OR7jF4wk0JQRsY/edit#gid=2027093015
    def get_wow_tagid_list(self, ctcode, gname, wowma_catid):
        self.logger.info('get_wow_tagid_list:in ctcode:[{}]'.format(ctcode))

        ret_str = ''
        new_list = []
        try:

            if ctcode == '':
                wow_ctcd = wowma_catid
            else:
                try:
                    wow_ctcd = __class__._MY_CT_CODES_SMALL[ctcode]["wowma_catid"]
                except:
                    # _MY_CT_CODES_SMALL に登録してない、キーワードマッチさせるカテゴリは
                    # ここで KeyErrorが起きる。その場合は空文字を返却して終了
                    self.logger.info(
                        'get_wow_tagid_list:1_1 ctcdがマッチしないので検索タグは空で。ctcd:[{}]'.format(ctcode))
                    return ret_str

            self.logger.info('get_wow_tagid_list:1 wow_ctcd:[{}]'.format(wow_ctcd))

            # WowmaCatTagOyaList, WowmaTagChildList
            oya = WowmaCatTagOyaList.objects.filter(
                wow_cat_id=wow_ctcd,
            ).first()
            if oya:
                self.logger.info('get_wow_tagid_list:2 登録済み親idと一致 gname:[{}]'.format(gname))
            else:
                self.logger.info('get_wow_tagid_list:3 親idと一致せず。処理終了')
                return

            # 商品名から、紐付けるキーワード（ブラック　とか）を抽出
            tmp_list_keyword = gname.split(" ")

            # 10040000 10270000 10280000 とか。
            tmp_list_moto = oya.tag_grp.split(" ")

            # 紐付いている親タグから、小タグを探す
            list_cnt = 0
            for tag_moto in tmp_list_moto:
                child_list = WowmaTagChildList.objects.filter(
                    oya_id=tag_moto,
                ).all()

                child_find_flg = 0
                for child in child_list:
                    # キーワードと、子タグ名称
                    # まず、キーワードとマッチする子タグは優先して登録
                    if child.child_name in tmp_list_keyword:
                        new_list.append(str(child.child_id))
                        child_find_flg = 1
                        list_cnt += 1
                        if child.rel_flg == 0:  # 一つの商品に複数の子タグを登録できない場合はここで終わり
                            break
                        if list_cnt > 63:
                            break
                if child_find_flg == 0:
                    # まだ見つかってなければ、まるごと登録してしまう
                    for child in child_list:
                        # キーワードと、子タグ名称
                        # まず、キーワードとマッチする子タグは優先して登録
                        if child.rel_flg == 0:  # 一つの商品に複数の子タグを登録できない
                            new_list.append(str(child.child_id))  # 一つだけ登録してbreak
                            list_cnt += 1
                            break
                        else:
                            new_list.append(str(child.child_id))  # 紐付いてるだけ登録してゆく
                            list_cnt += 1
                            if list_cnt > 63:
                                break

                # ここでも最大登録数のチェックはしておく
                if list_cnt > 63:
                    break

            # 全部がっちゃんこして半角スペース区切りにして返却
            ret_str = ' '.join(new_list)

            self.logger.info('get_wow_tagid_list:4 返却するタグ:[{}]'.format(ret_str))
            return ret_str.strip()

        except Exception as e:
            self.logger.info(traceback.format_exc())
            self.logger.debug(traceback.format_exc())
            return

        return

    # wowmaの商品登録・更新時に返却されたロットナンバーをDBにセットする
    def set_wow_lotnum(self, gid, lotnum):
        self.logger.info('set_wow_lotnum:in gid:[{}] lotnum[{}]'.format(gid,lotnum))
        # DBに保存
        ret_obj = YaBuyersItemDetail.objects.filter(gid=gid).first()
        if ret_obj:
            # DBを更新
            ret_obj.wow_lotnum = lotnum
            ret_obj.save()
            self.logger.info('set_wow_lotnum seved. :lotnum:[{}]'.format(ret_obj.wow_lotnum))
        return

    # 指定された個数だけ、キーワードセットを取得する。半角スペース区切り
    def get_keyword_set(self, moto_key, delete_key, ret_num):
        ret_str = ""
        tmp_list_moto = moto_key.split(" ")
        tmp_list_del = delete_key.split(" ")
        new_list = []

        my_cnt = 0
        for moto in tmp_list_moto:
            if moto not in tmp_list_del:
                new_list.append(moto)
                my_cnt += 1
                if my_cnt >= ret_num:
                    break

        ret_str = ' '.join(new_list)
        return ret_str.strip()

    # カテゴリコード一覧を返す
    def get_ct(self):
        return __class__._MY_CT_CODES

    # wowma向けの商品取得対象URL一覧を返す
    def get_url_list_for_wowma(self):
        return __class__._MY_URLS_WOWMA

    # 文字列内でキーワードがマッチしたらカテゴリコードを返す
    def chk_ct_by_keyword_for_wowma(self, mystr, mytitle):

        try:
            # 5桁の大カテゴリより、10桁のサブカテゴリのマッチを優先する
            #result_y_ct = str(__class__._MY_CT_CODES_KEYWORD[ctcode]["y_ct"])
            for mykey, myvalue in __class__._MY_CT_CODES_KEYWORD.items():
                #
                if re.search(mykey, mystr):

                    return int(myvalue["wowma_catid"])

                    """
                    # レディースかメンズも判定する
                    if myvalue['sex'] == '1': # sex に 1が設定されてるカテゴリキーワードだけ
                        if re.search('レディース', mytitle):
                            return myvalue["female"]
                        elif re.search('メンズ', mytitle):
                            return myvalue["male"]
                        else:
                            return myvalue["y_ct"]
                    else:
                        return myvalue["y_ct"]
                    """

        except Exception as e:
            self.logger.debug(traceback.format_exc())
            return False

    # 文字列内でキーワードがマッチしたらカテゴリコードを返す
    def chk_ct_by_keyword_for_qoo(self, mystr, mytitle):

        try:
            # 5桁の大カテゴリより、10桁のサブカテゴリのマッチを優先する
            #result_y_ct = str(__class__._MY_CT_CODES_KEYWORD[ctcode]["y_ct"])
            for mykey, myvalue in __class__._MY_CT_CODES_KEYWORD.items():
                #
                if re.search(mykey, mystr):
                    return myvalue["qoo_catid"]

        except Exception as e:
            self.logger.debug(traceback.format_exc())
            return False

    # 文字列内でキーワードがマッチしたらカテゴリコードを返す
    def chk_ct_by_keyword(self, mystr, mytitle):

        try:
            # 5桁の大カテゴリより、10桁のサブカテゴリのマッチを優先する
            #result_y_ct = str(__class__._MY_CT_CODES_KEYWORD[ctcode]["y_ct"])
            for mykey, myvalue in __class__._MY_CT_CODES_KEYWORD.items():
                #
                if re.search(mykey, mystr):

                    # レディースかメンズも判定する
                    if myvalue['sex'] == '1': # sex に 1が設定されてるカテゴリキーワードだけ
                        if re.search('レディース', mytitle):
                            return myvalue["female"]
                        elif re.search('メンズ', mytitle):
                            return myvalue["male"]
                        else:
                            return myvalue["y_ct"]
                    else:
                        return myvalue["y_ct"]

        except Exception as e:
            self.logger.debug(traceback.format_exc())
            return False

    # wowmaで取得対象にする、バイヤーズのカテゴリコードの一覧を返却する
    # ctflg ：　サブカテゴリのチェックフラグ。"small" が少カテゴリで登録OK、送料無料
    #           "sale" が500円均一など、追加でカテゴリのチェックや商品内容の確認が必要なもの
    #           "pack" がゆうパックなど、送料が別のもの。送料は個別でここに設定するか？
    # shipping : 送料を文字列で。"0" や "500" など

    """
    _MY_URLS_WOWMA = {
        "ct1076": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ピアス > その他
    }
    """

    _MY_URLS_WOWMA = {
        "ct676": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > メンズファッション > ジャケット、上着 > ライダース > Lサイズ
        "ct677": {"ctflg": "small", "shipping": "0"}, #オークション > スポーツ、レジャー > スポーツウエア > 男性用 > パーカー
        "ct678": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > メンズファッション > ジャケット、上着 > ジャンパー、ブルゾン > ジャンパー、ブルゾン一般 > Mサイズ
        "ct679": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > メンズファッション > ジャケット、上着 > ジャンパー、ブルゾン > ジャンパー、ブルゾン一般 > Mサイズ
        "ct680": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > メンズファッション > コート > コート一般 > Mサイズ
        "ct681": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > メンズファッション > シャツ > 半袖 > 半袖シャツ一般 > Mサイズ
        "ct682": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > メンズファッション > シャツ > 長袖 > 長袖シャツ一般 > Mサイズ
        "ct685": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > メンズファッション > カーディガン
        "ct803": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > メンズファッション > シャツ > その他の袖丈
        "ct804": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > メンズファッション > トレーナー > Mサイズ
        "ct805": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > メンズファッション > パンツ、スラックス > Mサイズ
        "ct806": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > メンズファッション > インナーウエア > ボクサーブリーフ > Mサイズ
        "ct807": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > メンズファッション > 水着 > Mサイズ
        "ct120": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > コート > コート一般 > Mサイズ
        "ct689": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ジャケット、上着 > ライダース
        "ct690": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ジャケット、上着 > その他
        "ct691": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ジャケット、上着 > ジャンパー、ブルゾン > ジャンパー、ブルゾン一般 > Mサイズ
        "ct692": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ジャケット、上着 > ジャケット、ブレザー > Mサイズ
        "ct693": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ジャケット、上着 > パーカ > パーカ一般 > Mサイズ
        "ct694": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > コート > コート一般 > Mサイズ
        "ct695": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ジャケット、上着 > ジャンパー、ブルゾン > スカジャン
        "ct696": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ジャケット、上着 > ジャンパー、ブルゾン > ジージャン > Mサイズ
        "ct1022": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ジャケット、上着 > パーカ > パーカ一般 > Mサイズ
        "ct163": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > カットソー > 長袖 > Mサイズ
        "ct1108": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > カットソー > 長袖 > Mサイズ
        "ct698": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > カットソー > 長袖 > Mサイズ
        "ct699": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > Vネック > その他
        "ct700": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > その他
        "ct1102": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Lサイズ > その他
        "ct704": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Lサイズ > その他
        "ct701": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > 丸首 > イラスト、キャラクター
        "ct702": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > Tシャツ > その他の袖丈
        "ct1107": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > その他
        "ct703": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > その他
        "ct1111": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > Vネック > 柄もの
        "ct1112": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > 丸首 > 文字、ロゴ
        "ct705": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ
        "ct706": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ
        "ct707": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ
        "ct708": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ
        "ct1045": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ
        "ct1044": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ
        "ct709": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ
        "ct710": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ
        "ct711": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ
        "ct715": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ
        "ct712": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > その他
        "ct713": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > その他
        "ct714": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > シャツ、ブラウス > 半袖 > Mサイズ
        "ct716": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > シャツ、ブラウス > 袖なし、ノースリーブ > ノースリーブシャツ一般
        "ct717": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > キャミソール
        "ct719": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > チュニック > 袖なし、ノースリーブ > Mサイズ
        "ct1110": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > チューブトップ、ベアトップ
        "ct162": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > カーディガン > Mサイズ
        "ct720": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > カーディガン > Mサイズ
        "ct721": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > カーディガン > Mサイズ
        "ct722": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ニット、セーター > 長袖 > Mサイズ
        "ct723": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ニット、セーター > 長袖 > Mサイズ
        "ct724": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ニット、セーター > 長袖 > Mサイズ
        "ct725": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ニット、セーター > 長袖 > Mサイズ
        "ct726": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > カーディガン > Mサイズ
        "ct727": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > カーディガン > Mサイズ
        "ct122": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > パンツ、スラックス > Mサイズ
        "ct728": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > パンツ、スラックス > Mサイズ
        "ct1008": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > レギンス、トレンカ
        "ct1009": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ワークパンツ、ペインターパンツ > Mサイズ
        "ct1010": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ワークパンツ、ペインターパンツ > Mサイズ
        "ct1047": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > パンツ、スラックス > Mサイズ
        "ct738": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > スカート > ロングスカート > その他
        "ct739": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > スカート > ロングスカート > その他
        "ct740": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > スカート > ロングスカート > その他
        "ct741": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > スカート > ミニスカート > その他
        "ct742": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > スカート > ミニスカート > タイトスカート > Mサイズ
        "ct743": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > スカート > ひざ丈スカート > その他
        "ct744": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > スカート > ひざ丈スカート > プリーツスカート > Mサイズ
        "ct745": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > スカート > ひざ丈スカート > フレアースカート、ギャザースカート > Mサイズ
        "ct746": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > スカート > ひざ丈スカート > タイトスカート > Mサイズ
        "ct747": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > スカート > ひざ丈スカート > その他
        "ct748": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > スカート > ロングスカート > その他
        "ct754": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > スカート > ロングスカート > フレアースカート、ギャザースカート > Mサイズ
        "ct156": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ワンピース > ミニスカート > Mサイズ
        "ct749": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ワンピース > ロングスカート > Mサイズ
        "ct750": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ワンピース > ロングスカート > Mサイズ
        "ct751": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ワンピース > ロングスカート > Mサイズ
        "ct752": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > ワンピース > ミニスカート > Mサイズ
        "ct753": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > フォーマル > ワンピース
        "ct755": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > フォーマル > ワンピース
        "ct756": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > フォーマル > ワンピース
        "ct757": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > フォーマル > ワンピース
        "ct758": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > フォーマル > ワンピース
        "ct759": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > フォーマル > ワンピース
        "ct760": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > フォーマル > ワンピース
        "ct761": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > フォーマル > ワンピース
        "ct762": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > フォーマル > ワンピース
        "ct1453": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > フォーマル > ワンピース
        "ct765": {"ctflg": "small", "shipping": "0"}, #オークション > スポーツ、レジャー > スポーツウエア > 女性用 > 上下セット > ジャージ > その他
        "ct763": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > インナーウエア > その他
        "ct767": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > インナーウエア > ブラジャー > その他
        "ct1109": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > インナーウエア > その他
        "ct768": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > インナーウエア > ブラジャー > その他
        "ct769": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > インナーウエア > ブラジャー > その他
        "ct770": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > インナーウエア > ショーツ > Mサイズ > スタンダード
        "ct771": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > インナーウエア > スリップ > Mサイズ
        "ct772": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > インナーウエア > ブラジャー > その他
        "ct773": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > インナーウエア > 補正下着 > その他
        "ct774": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > インナーウエア > ストッキング > Mサイズ
        "ct779": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > 水着 > その他
        "ct780": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > 水着 > セパレート > Mサイズ > 三角ビキニ
        "ct781": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > 水着 > その他
        "ct782": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > 水着 > その他
        "ct1038": {"ctflg": "small", "shipping": "0"}, #オークション > スポーツ、レジャー > スポーツ別 > サーフィン > ウエア > ラッシュガード > 女性用 > Mサイズ
        "ct775": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > キッズ、ベビーファッション > 子ども服（男女兼用） > トップス > 長袖Tシャツ > 140（135～144cm）
        "ct776": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > キッズ、ベビーファッション > 子ども服（男女兼用） > ボトムス > パンツ、ズボン一般 > 140（135～144cm）
        "ct1031": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > キッズ、ベビーファッション > 子ども服（女の子用） > その他
        "ct777": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > キッズ、ベビーファッション > 子ども服（男女兼用） > コート > コート一般 > 130（125～134cm）
        "ct778": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > キッズ、ベビーファッション > 子ども服（男女兼用） > セット、まとめ売り
        "ct1016": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > キッズ、ベビーファッション > 子ども用ファッション小物 > その他
        "ct1032": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > キッズ、ベビーファッション > 子ども用ファッション小物 > その他
        "ct784": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > キッズ、ベビーファッション > 子ども服（男の子用） > その他
        "ct785": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > キッズ、ベビーファッション > ベビー服 > ボトムス > ロンパース > 80（75～84cm）
        "ct786": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > キッズ、ベビーファッション > ベビー服 > トップス > Tシャツ > 長袖 > 男女兼用 > 90（85～94cm）
        "ct787": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > キッズ、ベビーファッション > ベビー服 > ボトムス > その他
        "ct788": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > キッズ、ベビーファッション > ベビー服 > コート、ジャンパー > コート > 男女兼用 > 90（85～94cm）
        "ct789": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > キッズ、ベビーファッション > ベビー用ファッション小物 > スタイ、よだれかけ
        "ct790": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > キッズ、ベビーファッション > ベビー服 > 水着 > 女の子用 > 90（85～94cm）
        "ct791": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > キッズ、ベビーファッション > ベビー用ファッション小物 > その他
        "ct792": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > マタニティウエア > その他
        "ct795": {"ctflg": "small", "shipping": "0"}, #オークション > コミック、アニメグッズ > コスプレ衣装 > その他
        "ct1028": {"ctflg": "small", "shipping": "0"}, #オークション > コミック、アニメグッズ > コスプレ衣装 > 男性用
        "ct1029": {"ctflg": "small", "shipping": "0"}, #オークション > コミック、アニメグッズ > コスプレ衣装 > その他
        "ct1030": {"ctflg": "small", "shipping": "0"}, #オークション > コミック、アニメグッズ > コスプレ衣装 > その他
        "ct796": {"ctflg": "small", "shipping": "0"}, #オークション > コミック、アニメグッズ > コスプレ衣装 > コミック、アニメ、ゲームキャラクター > コスプレ衣装
        "ct797": {"ctflg": "small", "shipping": "0"}, #オークション > コミック、アニメグッズ > コスプレ衣装 > コミック、アニメ、ゲームキャラクター > 衣装一式
        "ct798": {"ctflg": "small", "shipping": "0"}, #オークション > コミック、アニメグッズ > コスプレ衣装 > コミック、アニメ、ゲームキャラクター > 衣装一式
        "ct799": {"ctflg": "small", "shipping": "0"}, #オークション > コミック、アニメグッズ > コスプレ衣装 > コミック、アニメ、ゲームキャラクター > アクセサリー、小物
        "ct1000": {"ctflg": "small", "shipping": "0"}, #オークション > コミック、アニメグッズ > コスプレ衣装 > コミック、アニメ、ゲームキャラクター > インナー
        "ct800": {"ctflg": "small", "shipping": "0"}, #オークション > コミック、アニメグッズ > コスプレ衣装 > その他
        "ct801": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 帽子 > 男性用 > その他
        "ct826": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 帽子 > 男性用 > その他
        "ct828": {"ctflg": "small", "shipping": "0"}, #オークション > スポーツ、レジャー > スポーツ別 > ゴルフ > ウエア（男性用） > キャップ > その他
        "ct829": {"ctflg": "small", "shipping": "0"}, #オークション > スポーツ、レジャー > スポーツ別 > ゴルフ > ウエア（男性用） > ニット帽
        "ct1026": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 帽子 > 男性用 > その他
        "ct830": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 帽子 > 女性用 > ワッチキャップ、ニットキャップ
        "ct831": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 帽子 > 女性用 > ワッチキャップ、ニットキャップ
        "ct832": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 帽子 > 女性用 > ワッチキャップ、ニットキャップ
        "ct833": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 帽子 > 女性用 > テンガロンハット、ウエスタンハット
        "ct834": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 帽子 > 女性用 > 麦わら帽子
        "ct1024": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 帽子 > 女性用 > キャスケット
        "ct1025": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 帽子 > 女性用 > ベレー帽
        "ct1154": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > キッズ、ベビーファッション > 子ども用ファッション小物 > 帽子
        "ct1050": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ウイッグ > その他
        "ct1051": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ウイッグ > ショート
        "ct1052": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ウイッグ > ロング
        "ct1053": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ウイッグ > その他
        "ct1054": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ウイッグ > その他
        "ct1017": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > その他
        "ct1018": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ヘアゴム、シュシュ
        "ct1019": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > その他
        "ct1020": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ヘアバンド、カチューシャ
        "ct1021": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ヘアバンド、カチューシャ
        "ct1011": {"ctflg": "small", "shipping": "0"}, #オークション > ビューティー、ヘルスケア > めがね、コンタクト > その他
        "ct1012": {"ctflg": "small", "shipping": "0"}, #オークション > スポーツ、レジャー > スポーツサングラス > その他
        "ct1013": {"ctflg": "small", "shipping": "0"}, #オークション > ビューティー、ヘルスケア > めがね、コンタクト > その他
        "ct1014": {"ctflg": "small", "shipping": "0"}, #オークション > ビューティー、ヘルスケア > めがね、コンタクト > 老眼鏡
        "ct1015": {"ctflg": "small", "shipping": "0"}, #オークション > おもちゃ、ゲーム > 手品、パーティグッズ > パーティグッズ > その他
        "ct1055": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > メンズアクセサリー > その他
        "ct1056": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > イヤリング > その他
        "ct1061": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > メンズアクセサリー > その他
        "ct1062": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > イヤリング > その他
        "ct1057": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > メンズアクセサリー > ピアス > その他
        "ct1064": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ピアス > その他
        "ct1074": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ピアス > その他
        "ct1075": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ピアス > その他
        "ct1076": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ピアス > その他
        "ct1077": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ピアス > その他
        "ct1078": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ピアス > その他
        "ct1079": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ピアス > その他
        "ct1058": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > メンズアクセサリー > ネックレス > その他
        "ct1065": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > メンズアクセサリー > ネックレス > その他
        "ct1080": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > メンズアクセサリー > ネックレス > その他
        "ct1081": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > メンズアクセサリー > ネックレス > その他
        "ct1066": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ネックレス、ペンダント > その他
        "ct1082": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ネックレス、ペンダント > その他
        "ct1083": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > チョーカー > その他
        "ct1084": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ネックレス、ペンダント > その他
        "ct1085": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ネックレス、ペンダント > その他
        "ct1086": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ネックレス、ペンダント > ダイヤモンド > その他
        "ct1087": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ネックレス、ペンダント > その他
        "ct1059": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > メンズアクセサリー > ブレスレット、バングル > その他
        "ct1068": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > メンズアクセサリー > ブレスレット、バングル > その他
        "ct1088": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > メンズアクセサリー > ブレスレット、バングル > その他
        "ct1089": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > メンズアクセサリー > ブレスレット、バングル > バングル > その他
        "ct1090": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > メンズアクセサリー > ブレスレット、バングル > その他
        "ct1069": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > メンズアクセサリー > ブレスレット、バングル > その他
        "ct1091": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > メンズアクセサリー > ブレスレット、バングル > その他
        "ct1092": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ブレスレット、バングル > バングル > その他
        "ct1093": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > アンクレット > その他
        "ct1094": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > アンクレット > その他
        "ct1060": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > メンズアクセサリー > 指輪 > その他
        "ct1070": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > メンズアクセサリー > 指輪 > その他
        "ct1071": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > 指輪 > その他
        "ct1095": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > 指輪 > ゴールド > その他
        "ct1096": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > 指輪 > その他
        "ct1097": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > 指輪 > その他
        "ct1158": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディースアクセサリー > ブローチ > その他
        "ct794": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > マフラー > 女性用 > マフラー一般
        "ct819": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > ストール > ストール一般
        "ct821": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > マフラー > 男性用
        "ct822": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > ストール > ストール一般
        "ct820": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > マフラー > 女性用 > マフラー一般
        "ct823": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > マフラー > 女性用 > マフラー一般
        "ct824": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > ストール > ストール一般
        "ct810": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースバッグ > ハンドバッグ > その他
        "ct848": {"ctflg": "small", "shipping": "0"}, #オークション > スポーツ、レジャー > キャンプ、アウトドア用品 > バックパック、かばん > リュックサック > バックパック
        "ct849": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > 男女兼用バッグ > リュックサック、デイパック
        "ct850": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > 男女兼用バッグ > ショルダーバッグ
        "ct851": {"ctflg": "small", "shipping": "0"}, #オークション > スポーツ、レジャー > 自転車、サイクリング > バッグ > メッセンジャーバッグ
        "ct852": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > メンズバッグ > ボディバッグ
        "ct853": {"ctflg": "small", "shipping": "0"}, #オークション > 事務、店舗用品 > バッグ、スーツケース > スーツケース、トランク > スーツケース、トランク一般
        "ct854": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースバッグ > クラッチバッグ、パーティバッグ
        "ct855": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースバッグ > ハンドバッグ > その他
        "ct856": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > 男女兼用バッグ > トートバッグ
        "ct858": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースバッグ > ポーチ
        "ct1005": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースバッグ > ショルダーバッグ > その他
        "ct1006": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースバッグ > ショルダーバッグ > その他
        "ct1007": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースバッグ > ショルダーバッグ > その他
        "ct1462": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > 男女兼用バッグ > ボストンバッグ
        "ct1463": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > 男女兼用バッグ > エコバッグ
        "ct838": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > メンズ腕時計 > デジタル > その他
        "ct839": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > レディース腕時計 > デジタル > その他
        "ct840": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > ユニセックス腕時計 > デジタル > その他
        "ct841": {"ctflg": "small", "shipping": "0"}, #オークション > アクセサリー、時計 > ユニセックス腕時計 > デジタル > その他
        "ct808": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 財布 > 男性用 > その他
        "ct842": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 財布 > 男性用 > その他
        "ct843": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 財布 > 男性用 > 長財布（小銭入れあり）
        "ct844": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 財布 > 男性用 > 二つ折り財布（小銭入れあり）
        "ct836": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 財布 > 女性用 > その他
        "ct845": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 財布 > 女性用 > 長財布（小銭入れあり）
        "ct846": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 財布 > 女性用 > 二つ折り財布（小銭入れあり）
        "ct837": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 財布 > 男性用 > その他
        "ct847": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 財布 > 女性用 > その他
        "ct811": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > メンズシューズ > その他
        "ct859": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > メンズシューズ > その他
        "ct860": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースシューズ > その他
        "ct861": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > キッズ、ベビーファッション > ベビーシューズ > スニーカー > 14cm～
        "ct1104": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースシューズ > その他
        "ct793": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > スカーフ、ポケットチーフ > 女性用
        "ct1027": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 手袋 > 女性用 > その他
        "ct1033": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > ベルト > 男性用 > その他
        "ct809": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > キーケース
        "ct1023": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > 名刺入れ、カードケース > 男性用
        "ct908": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > 家具、インテリア > 鏡台、ドレッサー
        "ct909": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > 家具、インテリア > カーテン、ブラインド > カーテン > その他
        "ct910": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > 家具、インテリア > カーテン、ブラインド > カーテン > その他
        "ct911": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > キッチン、食器 > 収納、キッチン雑貨 > その他
        "ct912": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > キッチン、食器 > 収納、キッチン雑貨 > その他
        "ct913": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > キッチン、食器 > テーブルリネン > テーブルクロス
        "ct914": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > キッチン、食器 > 食器 > 洋食器 > プレート、皿 > その他
        "ct915": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > キッチン、食器 > 収納、キッチン雑貨 > その他
        "ct1098": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > キッチン、食器 > 調理器具 > その他
        "ct1106": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > 家庭用品 > バス > その他
        "ct1037": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > 家庭用品 > スリッパ
        "ct916": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > 家庭用品 > タオル > その他
        "ct917": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > 家庭用品 > タオル > バスタオル
        "ct919": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > ファッション小物 > エプロン
        "ct920": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > キッチン、食器 > 収納、キッチン雑貨 > その他
        "ct1105": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > キッチン、食器 > 収納、キッチン雑貨 > その他
        "ct63": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > キッチン、食器 > 収納、キッチン雑貨 > その他
        "ct54": {"ctflg": "small", "shipping": "0"}, #オークション > コンピュータ > 周辺機器 > その他
        "ct56": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 家庭用電化製品 > その他
        "ct922": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 冷暖房、空調 > 加湿器、除湿器 > 加湿器 > その他
        "ct923": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 冷暖房、空調 > 扇風機
        "ct1977": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > オーディオ機器 > ヘッドフォン、イヤフォン > イヤフォン > その他
        "ct981": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > オーディオ機器 > ヘッドフォン、イヤフォン > イヤフォン > その他
        "ct513": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct926": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone X用
        "ct927": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone XS用
        "ct928": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone XS用
        "ct929": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone XS用
        "ct930": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール
        "ct1330": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct1331": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > ハードケース
        "ct1332": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他
        "ct1333": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他
        "ct1334": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct1335": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール
        "ct1336": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct1337": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > ハードケース
        "ct1338": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他
        "ct1339": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他
        "ct1340": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct1341": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール
        "ct1342": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct1343": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > ハードケース
        "ct1344": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他
        "ct1345": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他
        "ct1346": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct1347": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール
        "ct924": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct931": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone XR用
        "ct932": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone XR用
        "ct933": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone XR用
        "ct934": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct935": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール
        "ct925": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct936": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone XS Max用
        "ct937": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone XS Max用
        "ct938": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone XS Max用
        "ct939": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct940": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール
        "ct68": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct941": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 7 Plus/8 Plus用
        "ct942": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 7 Plus/8 Plus用
        "ct943": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 7 Plus/8 Plus用
        "ct944": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct945": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール
        "ct65": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct946": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 7/8用
        "ct947": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 7/8用
        "ct948": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 7/8用
        "ct949": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct950": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール
        "ct75": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct951": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 6 Plus/6s Plus用
        "ct952": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 6 Plus/6s Plus用
        "ct953": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 6 Plus/6s Plus用
        "ct954": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct955": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール
        "ct72": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct956": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 6 Plus/6s Plus用
        "ct957": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 6 Plus/6s Plus用
        "ct958": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 6 Plus/6s Plus用
        "ct959": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct960": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール
        "ct69": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct961": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 5用
        "ct962": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 5用
        "ct963": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 5用
        "ct964": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct965": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール
        "ct76": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct966": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > ハードケース
        "ct967": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他
        "ct968": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他
        "ct969": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct970": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール
        "ct516": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct971": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > ハードケース
        "ct972": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他
        "ct973": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他
        "ct974": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct975": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール
        "ct78": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー
        "ct976": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct977": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct978": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct979": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct980": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct32": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他
        "ct10": {"ctflg": "small", "shipping": "0"}, #オークション > 事務、店舗用品 > 文房具 > その他
        "ct57": {"ctflg": "small", "shipping": "0"}, #オークション > 事務、店舗用品 > 文房具 > その他
        "ct17": {"ctflg": "small", "shipping": "0"}, #オークション > ビューティー、ヘルスケア > 健康用品、健康器具 > その他
        "ct982": {"ctflg": "small", "shipping": "0"}, #オークション > ビューティー、ヘルスケア > 健康用品、健康器具 > その他
        "ct95": {"ctflg": "small", "shipping": "0"}, #オークション > 食品、飲料 > ダイエット食品 > その他
        "ct1103": {"ctflg": "small", "shipping": "0"}, #オークション > 家電、AV、カメラ > 美容、健康 > 美容機器 > ネイルケア
        "ct13": {"ctflg": "small", "shipping": "0"}, #オークション > スポーツ、レジャー > キャンプ、アウトドア用品 > その他
        "ct1046": {"ctflg": "small", "shipping": "0"}, #オークション > スポーツ、レジャー > アウトドアウエア > 服飾小物 > その他
        "ct73": {"ctflg": "small", "shipping": "0"}, #医療・介護・医薬品＞介護・福祉＞その他生活グッズ＞サポーター
        "ct983": {"ctflg": "small", "shipping": "0"}, #オークション > スポーツ、レジャー > キャンプ、アウトドア用品 > 雨具、レインウエア > その他
        "ct984": {"ctflg": "small", "shipping": "0"}, #ダイエット・健康＞抗菌・除菌グッズ＞マスク＞その他マスク
        "ct987": {"ctflg": "small", "shipping": "0"}, #オークション > スポーツ、レジャー > キャンプ、アウトドア用品 > その他
        "ct999": {"ctflg": "small", "shipping": "0"}, #オークション > おもちゃ、ゲーム > 水遊び > ビーチボール
        "ct12": {"ctflg": "small", "shipping": "0"}, #オークション > 自動車、オートバイ > オートバイ > オートバイ関連グッズ > その他
        "ct64": {"ctflg": "small", "shipping": "0"}, #オークション > 自動車、オートバイ > アクセサリー > エンブレム > その他
        "ct66": {"ctflg": "small", "shipping": "0"}, #オークション > 自動車、オートバイ > カーナビ > 液晶保護フィルム、カバー > その他
        "ct991": {"ctflg": "small", "shipping": "0"}, #オークション > 自動車、オートバイ > オートバイ > オートバイ関連グッズ > その他
        "ct992": {"ctflg": "small", "shipping": "0"}, #オークション > 自動車、オートバイ > オートバイ > オートバイ関連グッズ > その他
        "ct67": {"ctflg": "small", "shipping": "0"}, #オークション > 自動車、オートバイ > オートバイ > オートバイ関連グッズ > その他
        "ct1116": {"ctflg": "small", "shipping": "0"}, #オークション > ファッション > レディースファッション > マタニティウエア
        "ct993": {"ctflg": "small", "shipping": "0"}, #オークション > おもちゃ、ゲーム > 手品、パーティグッズ > パーティグッズ > その他
        "ct995": {"ctflg": "small", "shipping": "0"}, #オークション > おもちゃ、ゲーム > こま > 一般
        "ct83": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > ペット用品 > 犬 > 服
        "ct988": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > ペット用品 > 犬 > 服 > 中型犬用>その他
        "ct989": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > ペット用品 > 犬 > 服 > 中型犬用>その他
        "ct87": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > ペット用品 > 犬 > 手入れ用品
        "ct990": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > ペット用品 > 犬 > その他
        "ct91": {"ctflg": "small", "shipping": "0"}, #オークション > 住まい、インテリア > ペット用品 > 犬 > その他
        "ct996": {"ctflg": "small", "shipping": "0"}, #オークション > おもちゃ、ゲーム > 知育玩具 > その他
        "ct994": {"ctflg": "small", "shipping": "0"}, #オークション > おもちゃ、ゲーム > 食玩、おまけ　> その他
        "ct109": {"ctname": "オークション > ファッション > メンズファッション", "y_ct": "23176", "wowma_catid": "", "qoo_catid": ""},
        "ct119": {"ctname": "オークション > ファッション > レディースファッション", "y_ct": "23288", "wowma_catid": "", "qoo_catid": ""},
        "ct164": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス", "y_ct": "42184", "wowma_catid": "",
                  "qoo_catid": ""},
        "ct161": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス", "y_ct": "42184", "wowma_catid": "",
                  "qoo_catid": ""},
        "ct133": {"ctname": "オークション > ファッション > レディースファッション > スカート", "y_ct": "42183", "wowma_catid": "",
                  "qoo_catid": ""},
        "ct169": {"ctname": "オークション > ファッション > レディースファッション＞その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
        "ct764": {"ctname": "オークション > ファッション > レディースファッション > その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
        "ct766": {"ctname": "オークション > ファッション > レディースファッション > その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
        "ct998": {"ctname": "オークション > ファッション > レディースファッション > その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
        "ct1039": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > その他", "y_ct": "2084005208", "wowma_catid": "",
                   "qoo_catid": ""},
        "ct1042": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > その他", "y_ct": "2084005208", "wowma_catid": "",
                   "qoo_catid": ""},
        "ct1040": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > その他", "y_ct": "2084005208", "wowma_catid": "",
                   "qoo_catid": ""},
        "ct1041": {"ctname": "オークション > ファッション > レディースファッション > スカート", "y_ct": "42183", "wowma_catid": "",
                   "qoo_catid": ""},
        "ct825": {"ctname": "オークション > ファッション > ファッション小物 > その他", "y_ct": "44164", "wowma_catid": "", "qoo_catid": ""},
        "ct857": {"ctname": "オークション > スポーツ、レジャー > スポーツ別 > その他", "y_ct": "25462", "wowma_catid": "", "qoo_catid": ""},
        "ct802": {"ctname": "オークション > アクセサリー、時計 > ブランド腕時計", "y_ct": "23260", "wowma_catid": "", "qoo_catid": ""},
        "ct1100": {"ctname": "オークション > ファッション > ファッション小物 > その他", "y_ct": "44164", "wowma_catid": "", "qoo_catid": ""},
        "ct813": {"ctname": "オークション > ファッション > ファッション小物 > その他", "y_ct": "44164", "wowma_catid": "", "qoo_catid": ""},
        "ct818": {"ctname": "オークション > ファッション > ファッション小物 > その他", "y_ct": "44164", "wowma_catid": "", "qoo_catid": ""},
        "ct60": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > その他", "y_ct": "42172", "wowma_catid": "", "qoo_catid": ""},
        "ct1099": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > その他", "y_ct": "24462", "wowma_catid": "", "qoo_catid": ""},
        "ct62": {"ctname": "オークション > 住まい、インテリア > キッチン、食器", "y_ct": "42168", "wowma_catid": "", "qoo_catid": ""},
        "ct921": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > その他", "y_ct": "24462", "wowma_catid": "", "qoo_catid": ""},
        "ct9": {"ctname": "オークション > 家電、AV、カメラ", "y_ct": "23632", "wowma_catid": "", "qoo_catid": ""},
        "ct55": {"ctname": "オークション > 家電、AV、カメラ > オーディオ機器 > その他", "y_ct": "23828", "wowma_catid": "", "qoo_catid": ""},
        "ct58": {"ctname": "オークション > 事務、店舗用品 > オフィス用品一般", "y_ct": "42176", "wowma_catid": "", "qoo_catid": ""},
        "ct59": {"ctname": "オークション > 事務、店舗用品 > その他", "y_ct": "22996", "wowma_catid": "", "qoo_catid": ""},
        "ct98": {"ctname": "オークション > ビューティー、ヘルスケア > コスメ、スキンケア > その他", "y_ct": "44379", "wowma_catid": "",
                 "qoo_catid": ""},
        "ct101": {"ctname": "オークション > ビューティー、ヘルスケア > コスメ、スキンケア > その他", "y_ct": "44379", "wowma_catid": "",
                  "qoo_catid": ""},
        "ct71": {"ctname": "オークション > スポーツ、レジャー > 自転車、サイクリング > アクセサリー > その他", "y_ct": "26242", "wowma_catid": "",
                 "qoo_catid": ""},
        "ct74": {"ctname": "オークション > スポーツ、レジャー > 自転車、サイクリング > アクセサリー > その他", "y_ct": "26242", "wowma_catid": "",
                 "qoo_catid": ""},
        "ct1114": {"ctname": "オークション > ベビー用品", "y_ct": "24202", "wowma_catid": "", "qoo_catid": ""},
        "ct1115": {"ctname": "オークション > ベビー用品＞ベビー服、マタニティウエア", "y_ct": "24210", "wowma_catid": "", "qoo_catid": ""},
        "ct83": {"ctname": "オークション > ファッション > レディースファッション > その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
        "ct996": {"ctname": "オークション > コンピュータ > ソフトウエア > パッケージ版 > Windows > 教育、教養 > その他", "y_ct": "23580",
                  "wowma_catid": "", "qoo_catid": ""},
        "ct172": {"ctname": "オークション > おもちゃ、ゲーム > パズル > その他", "y_ct": "27711", "wowma_catid": "", "qoo_catid": ""},
        "ct15": {"ctname": "オークション > 住まい、インテリア > ペット用品", "y_ct": "24534", "wowma_catid": "", "qoo_catid": ""},
        "ct170": {"ctname": "オークション > おもちゃ、ゲーム", "y_ct": "25464", "wowma_catid": "", "qoo_catid": ""},
        "ct171": {"ctname": "オークション > おもちゃ、ゲーム　＞　その他", "y_ct": "26082", "wowma_catid": "", "qoo_catid": ""},
        "ct18": {"ctname": "オークション > 自動車、オートバイ > 工具", "y_ct": "24650", "wowma_catid": "", "qoo_catid": ""},
        "ct19": {"ctname": "オークション > ファッション > レディースファッション > その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
    }

    # 以下はキーワードマッチを取得する一時的なリスト。本番用は↑を使う
    """
    _MY_URLS_WOWMA = {
        "ct109": {"ctname": "オークション > ファッション > メンズファッション", "y_ct": "23176", "wowma_catid": "", "qoo_catid": ""},
        "ct119": {"ctname": "オークション > ファッション > レディースファッション", "y_ct": "23288", "wowma_catid": "", "qoo_catid": ""},
        "ct164": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス", "y_ct": "42184", "wowma_catid": "",
                  "qoo_catid": ""},
        "ct161": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス", "y_ct": "42184", "wowma_catid": "",
                  "qoo_catid": ""},
        "ct133": {"ctname": "オークション > ファッション > レディースファッション > スカート", "y_ct": "42183", "wowma_catid": "",
                  "qoo_catid": ""},
        "ct169": {"ctname": "オークション > ファッション > レディースファッション＞その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
        "ct764": {"ctname": "オークション > ファッション > レディースファッション > その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
        "ct766": {"ctname": "オークション > ファッション > レディースファッション > その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
        "ct998": {"ctname": "オークション > ファッション > レディースファッション > その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
        "ct1039": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > その他", "y_ct": "2084005208", "wowma_catid": "",
                   "qoo_catid": ""},
        "ct1042": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > その他", "y_ct": "2084005208", "wowma_catid": "",
                   "qoo_catid": ""},
        "ct1040": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > その他", "y_ct": "2084005208", "wowma_catid": "",
                   "qoo_catid": ""},
        "ct1041": {"ctname": "オークション > ファッション > レディースファッション > スカート", "y_ct": "42183", "wowma_catid": "",
                   "qoo_catid": ""},
        "ct825": {"ctname": "オークション > ファッション > ファッション小物 > その他", "y_ct": "44164", "wowma_catid": "", "qoo_catid": ""},
        "ct857": {"ctname": "オークション > スポーツ、レジャー > スポーツ別 > その他", "y_ct": "25462", "wowma_catid": "", "qoo_catid": ""},
        "ct802": {"ctname": "オークション > アクセサリー、時計 > ブランド腕時計", "y_ct": "23260", "wowma_catid": "", "qoo_catid": ""},
        "ct1100": {"ctname": "オークション > ファッション > ファッション小物 > その他", "y_ct": "44164", "wowma_catid": "", "qoo_catid": ""},
        "ct813": {"ctname": "オークション > ファッション > ファッション小物 > その他", "y_ct": "44164", "wowma_catid": "", "qoo_catid": ""},
        "ct818": {"ctname": "オークション > ファッション > ファッション小物 > その他", "y_ct": "44164", "wowma_catid": "", "qoo_catid": ""},
        "ct60": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > その他", "y_ct": "42172", "wowma_catid": "", "qoo_catid": ""},
        "ct1099": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > その他", "y_ct": "24462", "wowma_catid": "", "qoo_catid": ""},
        "ct62": {"ctname": "オークション > 住まい、インテリア > キッチン、食器", "y_ct": "42168", "wowma_catid": "", "qoo_catid": ""},
        "ct921": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > その他", "y_ct": "24462", "wowma_catid": "", "qoo_catid": ""},
        "ct9": {"ctname": "オークション > 家電、AV、カメラ", "y_ct": "23632", "wowma_catid": "", "qoo_catid": ""},
        "ct55": {"ctname": "オークション > 家電、AV、カメラ > オーディオ機器 > その他", "y_ct": "23828", "wowma_catid": "", "qoo_catid": ""},
        "ct58": {"ctname": "オークション > 事務、店舗用品 > オフィス用品一般", "y_ct": "42176", "wowma_catid": "", "qoo_catid": ""},
        "ct59": {"ctname": "オークション > 事務、店舗用品 > その他", "y_ct": "22996", "wowma_catid": "", "qoo_catid": ""},
        "ct98": {"ctname": "オークション > ビューティー、ヘルスケア > コスメ、スキンケア > その他", "y_ct": "44379", "wowma_catid": "",
                 "qoo_catid": ""},
        "ct101": {"ctname": "オークション > ビューティー、ヘルスケア > コスメ、スキンケア > その他", "y_ct": "44379", "wowma_catid": "",
                  "qoo_catid": ""},
        "ct71": {"ctname": "オークション > スポーツ、レジャー > 自転車、サイクリング > アクセサリー > その他", "y_ct": "26242", "wowma_catid": "",
                 "qoo_catid": ""},
        "ct74": {"ctname": "オークション > スポーツ、レジャー > 自転車、サイクリング > アクセサリー > その他", "y_ct": "26242", "wowma_catid": "",
                 "qoo_catid": ""},
        "ct1114": {"ctname": "オークション > ベビー用品", "y_ct": "24202", "wowma_catid": "", "qoo_catid": ""},
        "ct1115": {"ctname": "オークション > ベビー用品＞ベビー服、マタニティウエア", "y_ct": "24210", "wowma_catid": "", "qoo_catid": ""},
        "ct83": {"ctname": "オークション > ファッション > レディースファッション > その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
        "ct996": {"ctname": "オークション > コンピュータ > ソフトウエア > パッケージ版 > Windows > 教育、教養 > その他", "y_ct": "23580",
                  "wowma_catid": "", "qoo_catid": ""},
        "ct172": {"ctname": "オークション > おもちゃ、ゲーム > パズル > その他", "y_ct": "27711", "wowma_catid": "", "qoo_catid": ""},
        "ct15": {"ctname": "オークション > 住まい、インテリア > ペット用品", "y_ct": "24534", "wowma_catid": "", "qoo_catid": ""},
        "ct170": {"ctname": "オークション > おもちゃ、ゲーム", "y_ct": "25464", "wowma_catid": "", "qoo_catid": ""},
        "ct171": {"ctname": "オークション > おもちゃ、ゲーム　＞　その他", "y_ct": "26082", "wowma_catid": "", "qoo_catid": ""},
        "ct18": {"ctname": "オークション > 自動車、オートバイ > 工具", "y_ct": "24650", "wowma_catid": "", "qoo_catid": ""},
        "ct19": {"ctname": "オークション > ファッション > レディースファッション > その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
    }
    """







    # 10桁のサブカテゴリをこちらに。優先
    # ここで指定したカテゴリは、_MY_CT_CODES_KEYWORD　のキーワードにヒットさせて判定する
    _MY_CT_CODES_SMALL_WARN = {
        "ct113": {"ctname": "my_key", "y_ct": "", "sex":"0", "male":"", "female":"","wowma_catid": "","wowma_catname": "","qoo_catid": "","qoo_catname": ""},
        "ct117": {"ctname": "my_key", "y_ct": "", "sex":"0", "male":"", "female":"","wowma_catid": "","wowma_catname": "","qoo_catid": "","qoo_catname": ""},
        "ct109": {"ctname": "オークション > ファッション > メンズファッション", "y_ct": "23176", "wowma_catid": "", "qoo_catid": ""},
        "ct119": {"ctname": "オークション > ファッション > レディースファッション", "y_ct": "23288", "wowma_catid": "", "qoo_catid": ""},
        "ct164": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス", "y_ct": "42184", "wowma_catid": "",
                  "qoo_catid": ""},
        "ct161": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス", "y_ct": "42184", "wowma_catid": "",
                  "qoo_catid": ""},
        "ct133": {"ctname": "オークション > ファッション > レディースファッション > スカート", "y_ct": "42183", "wowma_catid": "",
                  "qoo_catid": ""},
        "ct764": {"ctname": "オークション > ファッション > レディースファッション > その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
        "ct766": {"ctname": "オークション > ファッション > レディースファッション > その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
        "ct1039": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > その他", "y_ct": "2084005208", "wowma_catid": "",
                   "qoo_catid": ""},
        "ct1042": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > その他", "y_ct": "2084005208", "wowma_catid": "",
                   "qoo_catid": ""},
        "ct1040": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > その他", "y_ct": "2084005208", "wowma_catid": "",
                   "qoo_catid": ""},
        "ct1041": {"ctname": "オークション > ファッション > レディースファッション > スカート", "y_ct": "42183", "wowma_catid": "",
                   "qoo_catid": ""},
        "ct825": {"ctname": "オークション > ファッション > ファッション小物 > その他", "y_ct": "44164", "wowma_catid": "", "qoo_catid": ""},
        "ct857": {"ctname": "オークション > スポーツ、レジャー > スポーツ別 > その他", "y_ct": "25462", "wowma_catid": "", "qoo_catid": ""},
        "ct802": {"ctname": "オークション > アクセサリー、時計 > ブランド腕時計", "y_ct": "23260", "wowma_catid": "", "qoo_catid": ""},
        "ct1100": {"ctname": "オークション > ファッション > ファッション小物 > その他", "y_ct": "44164", "wowma_catid": "", "qoo_catid": ""},
        "ct813": {"ctname": "オークション > ファッション > ファッション小物 > その他", "y_ct": "44164", "wowma_catid": "", "qoo_catid": ""},
        "ct818": {"ctname": "オークション > ファッション > ファッション小物 > その他", "y_ct": "44164", "wowma_catid": "", "qoo_catid": ""},
        "ct60": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > その他", "y_ct": "42172", "wowma_catid": "", "qoo_catid": ""},
        "ct62": {"ctname": "オークション > 住まい、インテリア > キッチン、食器", "y_ct": "42168", "wowma_catid": "", "qoo_catid": ""},
        "ct921": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > その他", "y_ct": "24462", "wowma_catid": "", "qoo_catid": ""},
        "ct9": {"ctname": "オークション > 家電、AV、カメラ", "y_ct": "23632", "wowma_catid": "", "qoo_catid": ""},
        "ct55": {"ctname": "オークション > 家電、AV、カメラ > オーディオ機器 > その他", "y_ct": "23828", "wowma_catid": "", "qoo_catid": ""},
        "ct58": {"ctname": "オークション > 事務、店舗用品 > オフィス用品一般", "y_ct": "42176", "wowma_catid": "", "qoo_catid": ""},
        "ct59": {"ctname": "オークション > 事務、店舗用品 > その他", "y_ct": "22996", "wowma_catid": "", "qoo_catid": ""},
        "ct98": {"ctname": "オークション > ビューティー、ヘルスケア > コスメ、スキンケア > その他", "y_ct": "44379", "wowma_catid": "",
                 "qoo_catid": ""},
        "ct101": {"ctname": "オークション > ビューティー、ヘルスケア > コスメ、スキンケア > その他", "y_ct": "44379", "wowma_catid": "",
                  "qoo_catid": ""},
        "ct1115": {"ctname": "オークション > ベビー用品＞ベビー服、マタニティウエア", "y_ct": "24210", "wowma_catid": "", "qoo_catid": ""},
        "ct83": {"ctname": "オークション > ファッション > レディースファッション > その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
        "ct996": {"ctname": "オークション > コンピュータ > ソフトウエア > パッケージ版 > Windows > 教育、教養 > その他", "y_ct": "23580",
                  "wowma_catid": "", "qoo_catid": ""},
        "ct172": {"ctname": "オークション > おもちゃ、ゲーム > パズル > その他", "y_ct": "27711", "wowma_catid": "", "qoo_catid": ""},
        "ct15": {"ctname": "オークション > 住まい、インテリア > ペット用品", "y_ct": "24534", "wowma_catid": "", "qoo_catid": ""},
        "ct171": {"ctname": "オークション > おもちゃ、ゲーム　＞　その他", "y_ct": "26082", "wowma_catid": "", "qoo_catid": ""},
        "ct19": {"ctname": "オークション > ファッション > レディースファッション > その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
    }

    """
    _MY_CT_CODES_SMALL_WARN = {
        "ct113": {"ctname": "オークション > ファッション > メンズファッション > コート > コート一般 > Mサイズ", "y_ct": "2084057466", "sex":"0", "male":"", "female":"","wowma_catid": "","wowma_catname": "","qoo_catid": "","qoo_catname": ""},
        "ct117": {"ctname": "オークション > ファッション > メンズファッション > シャツ > その他の袖丈", "y_ct": "2084054038", "sex":"0", "male":"", "female":"","wowma_catid": "","wowma_catname": "","qoo_catid": "","qoo_catname": ""},
    }
    """

    # 10桁のサブカテゴリをこちらに。優先
    # バイヤーズカテゴリのシート、　https://docs.google.com/spreadsheets/d/1XLHXkiE-_p11nYUFy2TFOsQonWJb7OR7jF4wk0JQRsY/edit#gid=492800307
    # ↓ 2021/10/10 qoo10のカテゴリ含めた最新は以下[qoo_リスト抽出用]
    # https://docs.google.com/spreadsheets/d/1XLHXkiE-_p11nYUFy2TFOsQonWJb7OR7jF4wk0JQRsY/edit#gid=1688672388
    # 「cat_wowma_1_edit」シート　R列　を参考に
    _MY_CT_CODES_SMALL = {
        "ct676": {"ctname": "オークション > ファッション > メンズファッション > ジャケット、上着 > ライダース > Lサイズ", "y_ct": "2084243906","sex": "0","male": "","female": "","wowma_catid": "500501","wowma_catname": "メンズファッション＞ジャケット・アウター＞その他ジャケット・アウター","qoo_catid": "300002284","qoo_catname": "メンズファッション_アウター_ダウンジャケット","s_keyword": "メンズ 冬 防寒 ビジネス カジュアル 防水 ゴルフ レディース バイク キッズ オムニヒート 中綿 マウンテンパーカー オフィス 秋冬 スーツ 入学式 ボア コンパクト np71830 150 赤 大きい 5l フード付き 作業着 裏起毛 ゆったり かわいい 黒 オシャレ プロテクター コミネ オール シーズン パーカー j140 デトロイト 古着 プルオーバー j131 ダック 大きいサイズブランド 6l ロング レザー 4l 7l 大きいサイズ5l"},
        "ct677": {"ctname": "オークション > スポーツ、レジャー > スポーツウエア > 男性用 > パーカー", "y_ct": "2084303393","sex": "0","male": "","female": "","wowma_catid": "404909","wowma_catname": "スポーツ・アウトドア＞水泳＞男性用スイムウェア・競泳水着","qoo_catid": "300002279","qoo_catname": "メンズファッション_アウター_パーカー・トレーナー","s_keyword": "メンズ 冬 防寒 ビジネス カジュアル 防水 ゴルフ レディース バイク キッズ オムニヒート 中綿 マウンテンパーカー オフィス 秋冬 スーツ 入学式 ボア コンパクト np71830 150 赤 大きい 5l フード付き 作業着 裏起毛 ゆったり かわいい 黒 オシャレ プロテクター コミネ オール シーズン パーカー j140 デトロイト 古着 プルオーバー j131 ダック 大きいサイズブランド 6l ロング レザー 4l 7l 大きいサイズ5l"},
        "ct678": {"ctname": "オークション > ファッション > メンズファッション > ジャケット、上着 > ジャンパー、ブルゾン > ジャンパー、ブルゾン一般 > Mサイズ", "y_ct": "2084050108","sex": "0","male": "","female": "","wowma_catid": "500501","wowma_catname": "メンズファッション＞ジャケット・アウター＞その他ジャケット・アウター","qoo_catid": "300002284","qoo_catname": "メンズファッション_アウター_ダウンジャケット","s_keyword": "メンズ 冬 防寒 ビジネス カジュアル 防水 ゴルフ レディース バイク キッズ オムニヒート 中綿 マウンテンパーカー オフィス 秋冬 スーツ 入学式 ボア コンパクト np71830 150 赤 大きい 5l フード付き 作業着 裏起毛 ゆったり かわいい 黒 オシャレ プロテクター コミネ オール シーズン パーカー j140 デトロイト 古着 プルオーバー j131 ダック 大きいサイズブランド 6l ロング レザー 4l 7l 大きいサイズ5l"},
        "ct679": {"ctname": "オークション > ファッション > メンズファッション > ジャケット、上着 > ジャンパー、ブルゾン > ジャンパー、ブルゾン一般 > Mサイズ", "y_ct": "2084050108","sex": "0","male": "","female": "","wowma_catid": "500501","wowma_catname": "メンズファッション＞ジャケット・アウター＞その他ジャケット・アウター","qoo_catid": "300002284","qoo_catname": "メンズファッション_アウター_ダウンジャケット","s_keyword": "メンズ 冬 防寒 ビジネス カジュアル 防水 ゴルフ レディース バイク キッズ オムニヒート 中綿 マウンテンパーカー オフィス 秋冬 スーツ 入学式 ボア コンパクト np71830 150 赤 大きい 5l フード付き 作業着 裏起毛 ゆったり かわいい 黒 オシャレ プロテクター コミネ オール シーズン パーカー j140 デトロイト 古着 プルオーバー j131 ダック 大きいサイズブランド 6l ロング レザー 4l 7l 大きいサイズ5l"},
        "ct680": {"ctname": "オークション > ファッション > メンズファッション > コート > コート一般 > Mサイズ", "y_ct": "2084057466","sex": "0","male": "","female": "","wowma_catid": "500524","wowma_catname": "メンズファッション＞ジャケット・アウター＞トレンチコート","qoo_catid": "300000059","qoo_catname": "メンズファッション_アウター_Aライン・ピーコート","s_keyword": "メンズ 冬 防寒 ビジネス カジュアル 防水 ゴルフ レディース バイク キッズ オムニヒート 中綿 マウンテンパーカー オフィス 秋冬 スーツ 入学式 ボア コンパクト np71830 150 赤 大きい 5l フード付き 作業着 裏起毛 ゆったり かわいい 黒 オシャレ プロテクター コミネ オール シーズン パーカー j140 デトロイト 古着 プルオーバー j131 ダック 大きいサイズブランド 6l ロング レザー 4l 7l 大きいサイズ5l"},
        "ct681": {"ctname": "オークション > ファッション > メンズファッション > シャツ > 半袖 > 半袖シャツ一般 > Mサイズ", "y_ct": "2084064183","sex": "0","male": "","female": "","wowma_catid": "320403","wowma_catname": "インナー・ルームウェア＞メンズインナー＞シャツ・肌着","qoo_catid": "300000055","qoo_catname": "メンズファッション_トップス_長袖シャツ","s_keyword": "メンズ 長袖 カジュアル ビジネス レディース ワンピース 下着 秋冬 冬 白 厚手 ストライプ 柄 ブランド 無地 ノーアイロン ビジネスカジュアル セット スリム 紺色 黒 チェック 形状記憶 襟付き オフィス コーデュロイ vネック 3l ヒートテック 4l ランニング ノースリーブ ロング きれいめ ミニ キッズ 赤 青 アイロン 暖かい アイロン不要 アニメ インナー 犬 イタリアンカラー 衣装 インク 裏起毛 ウィメンズ"},
        "ct682": {"ctname": "オークション > ファッション > メンズファッション > シャツ > 長袖 > 長袖シャツ一般 > Mサイズ", "y_ct": "2084064178","sex": "0","male": "","female": "","wowma_catid": "320403","wowma_catname": "インナー・ルームウェア＞メンズインナー＞シャツ・肌着","qoo_catid": "300000055","qoo_catname": "メンズファッション_トップス_長袖シャツ","s_keyword": "メンズ 長袖 カジュアル ビジネス レディース ワンピース 下着 秋冬 冬 白 厚手 ストライプ 柄 ブランド 無地 ノーアイロン ビジネスカジュアル セット スリム 紺色 黒 チェック 形状記憶 襟付き オフィス コーデュロイ vネック 3l ヒートテック 4l ランニング ノースリーブ ロング きれいめ ミニ キッズ 赤 青 アイロン 暖かい アイロン不要 アニメ インナー 犬 イタリアンカラー 衣装 インク 裏起毛 ウィメンズ"},
        "ct685": {"ctname": "オークション > ファッション > メンズファッション > カーディガン", "y_ct": "2084007052","sex": "0","male": "","female": "","wowma_catid": "501103","wowma_catname": "メンズファッション＞学生服＞スクールニット・カーディガン","qoo_catid": "300002278","qoo_catname": "メンズファッション_アウター_カーディガン","s_keyword": "メンズ 冬 ビジネス ニット フリース 厚手 ロング レディース オフィス ゆったり 黒 短め 大きめ 赤 ポケット カシミア ウール 和風 学生 女子 男子 ベージュ 白 キッズ ナース ダイナソー セット ベビー 4l ブラウン 洗える 大きい ブランド カシミヤ vネック 丸首 ニットジャケット メンズコート 長袖 ニットセーター 羽織コート ロングコート アウター カットソー カジュアル ボーター柄 ニット細見 スーツ ラムウール"},
        "ct803": {"ctname": "オークション > ファッション > メンズファッション > シャツ > その他の袖丈", "y_ct": "2084054038","sex": "0","male": "","female": "","wowma_catid": "320403","wowma_catname": "インナー・ルームウェア＞メンズインナー＞シャツ・肌着","qoo_catid": "300000055","qoo_catname": "メンズファッション_トップス_長袖シャツ","s_keyword": "メンズ 長袖 カジュアル ビジネス レディース ワンピース 下着 秋冬 冬 白 厚手 ストライプ 柄 ブランド 無地 ノーアイロン ビジネスカジュアル セット スリム 紺色 黒 チェック 形状記憶 襟付き オフィス コーデュロイ vネック 3l ヒートテック 4l ランニング ノースリーブ ロング きれいめ ミニ キッズ 赤 青 アイロン 暖かい アイロン不要 アニメ インナー 犬 イタリアンカラー 衣装 インク 裏起毛 ウィメンズ"},
        "ct804": {"ctname": "オークション > ファッション > メンズファッション > トレーナー > Mサイズ", "y_ct": "2084057461","sex": "0","male": "","female": "","wowma_catid": "500712","wowma_catname": "メンズファッション＞トップス＞トレーナー・スウェット","qoo_catid": "300002279","qoo_catname": "メンズファッション_アウター_パーカー・トレーナー","s_keyword": "メンズ 裏起毛 ブランド おしゃれ 冬 長袖 オーバーサイズ レディース ゆったり チャンピオン 韓国 キッズ ジュニア 白 上下 160 グレー 5l 4l 3l オシャレ 6l 厚手 無地 大きい 黒 ザ ベビー ベージュ パーカー 2xl 緑 茶 男の子 女の子 150 140 130 ユッタリ ロング かわいい 赤 青 アニメ イラスト 犬 犬柄 インナー"},
        "ct805": {"ctname": "オークション > ファッション > メンズファッション > パンツ、スラックス > Mサイズ", "y_ct": "2084224619","sex": "0","male": "","female": "","wowma_catid": "500808","wowma_catname": "メンズファッション＞パンツ・ボトムス＞スラックス","qoo_catid": "300002302","qoo_catname": "メンズファッション_ビジネス・フォーマル_パンツ・スラックス","s_keyword": "メンズ 冬 ハンガー ハンガーラック すそ上げ済み パンツ レディース レディース 裏起毛 カジュアル 裾上げ済 ストレッチ 冬用 アジャスター ツータック ビジネス スリム 挟む クリップ 木製 洗濯 スタンド 極太 キャスター キャスター付き ハンガーラック30本 20本 山善 10本 2段 日本製 大きい ノータック 秋冬 ワイド 裾上げ 白 秋冬物 大きいサイズ秋冬 裾上げ済み ストライプ ワンタック ウール 黒 暖かい ネイビー アジャスター付き アイロン 赤"},
        "ct806": {"ctname": "オークション > ファッション > メンズファッション > インナーウエア > ボクサーブリーフ > Mサイズ", "y_ct": "2084053072","sex": "0","male": "","female": "","wowma_catid": "500801","wowma_catname": "メンズファッション＞パンツ・ボトムス＞その他パンツ・ボトムス","qoo_catid": "300000066","qoo_catname": "メンズファッション_インナー・靴下_ボクサーパンツ","s_keyword": "メンズ 冬 メンズ防寒 レディース ー タンクトップ レディース レディースよネック府 レディース暖かい レディース上下 サッカー キッズ 裏起毛 長袖 ジュニア the north freon pocket専用 電熱 上下セット 13箇所発熱 電熱パンツ"},
        "ct807": {"ctname": "オークション > ファッション > メンズファッション > 水着 > Mサイズ", "y_ct": "2084051835","sex": "0","male": "","female": "","wowma_catid": "501201","wowma_catname": "メンズファッション＞水着＞その他水着","qoo_catid": "300002298","qoo_catname": "メンズファッション_その他メンズファッション_水着","s_keyword": "レディース メンズ フィットネス 体型カバー レディース 競泳 セパレート 男性 ビキニ ワンピース タンキニ セット ラッシュガード 上下 練習用 インナー アリーナ スピード 50代 40代 50代大きい 60代 3l 体型カバーsale エレッセ スピードセパレート arena 半袖 フィラ セパレートミズノ ショート ボックス fina認証 ジム 上 男性用 穴あき アンダーショーツ アンダー 赤ちゃん インナーショーツ いんなーパンツ tバック インナーパンツ 上着 上だけ うえだけ 上に羽織る"},
        "ct120": {"ctname": "オークション > ファッション > レディースファッション > コート > コート一般 > Mサイズ", "y_ct": "2084057471","sex": "0","male": "","female": "","wowma_catid": "320708","wowma_catname": "インナー・ルームウェア＞レディースインナー＞ペチコート","qoo_catid": "300002186","qoo_catname": "レディースファッション_アウター_ダウンジャケット・コート","s_keyword": "レディース メンズ 冬 ハンガー 掛け レディース冬 ビジネス おしゃれ かわいい ロング カシミヤ 黒 綺麗 防寒 カジュアル チェスター ベージュ ブランド ショート スリム 木製 ハンガーラック 壁掛け 玄関 山崎実業 壁 軽い ダウン aライン スタンド フック 傷つけない 突っ張り レディース冬 レディース冬物 レディース冬軽い レディース冬ロング レディース冬ブランド ダッフル レディース冬モコモコ ビジネスカジュアル トレンチ ハーフ ウール"},
        "ct689": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > ライダース", "y_ct": "2084243900","sex": "0","male": "","female": "","wowma_catid": "510330","wowma_catname": "レディースファッション＞アウター＞ライダースジャケット","qoo_catid": "300002186","qoo_catname": "レディースファッション_アウター_ダウンジャケット・コート","s_keyword": "冬 防寒 ビジネス カジュアル 防水 ゴルフ レディース バイク キッズ オムニヒート 中綿 マウンテンパーカー オフィス 秋冬 スーツ 入学式 ボア コンパクト np71830 150 赤 大きい 5l フード付き 作業着 裏起毛 ゆったり かわいい 黒 オシャレ プロテクター コミネ オール シーズン パーカー j140 デトロイト 古着 プルオーバー j131 ダック 大きいサイズブランド 6l ロング レザー 4l 7l 大きいサイズ5l"},
        "ct690": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > その他", "y_ct": "2084005208","sex": "0","male": "","female": "","wowma_catid": "510301","wowma_catname": "レディースファッション＞アウター＞その他アウター","qoo_catid": "300002186","qoo_catname": "レディースファッション_アウター_ダウンジャケット・コート","s_keyword": "冬 防寒 ビジネス カジュアル 防水 ゴルフ レディース バイク キッズ オムニヒート 中綿 マウンテンパーカー オフィス 秋冬 スーツ 入学式 ボア コンパクト np71830 150 赤 大きい 5l フード付き 作業着 裏起毛 ゆったり かわいい 黒 オシャレ プロテクター コミネ オール シーズン パーカー j140 デトロイト 古着 プルオーバー j131 ダック 大きいサイズブランド 6l ロング レザー 4l 7l 大きいサイズ5l"},
        "ct691": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > ジャンパー、ブルゾン > ジャンパー、ブルゾン一般 > Mサイズ", "y_ct": "2084057481","sex": "0","male": "","female": "","wowma_catid": "510324","wowma_catname": "レディースファッション＞アウター＞ブルゾン","qoo_catid": "300002186","qoo_catname": "レディースファッション_アウター_ダウンジャケット・コート","s_keyword": "冬 防寒 ビジネス カジュアル 防水 ゴルフ レディース バイク キッズ オムニヒート 中綿 マウンテンパーカー オフィス 秋冬 スーツ 入学式 ボア コンパクト np71830 150 赤 大きい 5l フード付き 作業着 裏起毛 ゆったり かわいい 黒 オシャレ プロテクター コミネ オール シーズン パーカー j140 デトロイト 古着 プルオーバー j131 ダック 大きいサイズブランド 6l ロング レザー 4l 7l 大きいサイズ5l"},
        "ct692": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > ジャケット、ブレザー > Mサイズ", "y_ct": "2084057476","sex": "0","male": "","female": "","wowma_catid": "510301","wowma_catname": "レディースファッション＞アウター＞その他アウター","qoo_catid": "300002186","qoo_catname": "レディースファッション_アウター_ダウンジャケット・コート","s_keyword": "冬 防寒 ビジネス カジュアル 防水 ゴルフ レディース バイク キッズ オムニヒート 中綿 マウンテンパーカー オフィス 秋冬 スーツ 入学式 ボア コンパクト np71830 150 赤 大きい 5l フード付き 作業着 裏起毛 ゆったり かわいい 黒 オシャレ プロテクター コミネ オール シーズン パーカー j140 デトロイト 古着 プルオーバー j131 ダック 大きいサイズブランド 6l ロング レザー 4l 7l 大きいサイズ5l"},
        "ct693": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > パーカ > パーカ一般 > Mサイズ", "y_ct": "2084050490","sex": "0","male": "","female": "","wowma_catid": "510309","wowma_catname": "レディースファッション＞アウター＞スタンドカラージャケット・コート","qoo_catid": "300002186","qoo_catname": "レディースファッション_アウター_ダウンジャケット・コート","s_keyword": "冬 防寒 ビジネス カジュアル 防水 ゴルフ レディース バイク キッズ オムニヒート 中綿 マウンテンパーカー オフィス 秋冬 スーツ 入学式 ボア コンパクト np71830 150 赤 大きい 5l フード付き 作業着 裏起毛 ゆったり かわいい 黒 オシャレ プロテクター コミネ オール シーズン パーカー j140 デトロイト 古着 プルオーバー j131 ダック 大きいサイズブランド 6l ロング レザー 4l 7l 大きいサイズ5l"},
        "ct694": {"ctname": "オークション > ファッション > レディースファッション > コート > コート一般 > Mサイズ", "y_ct": "2084057471","sex": "0","male": "","female": "","wowma_catid": "320708","wowma_catname": "インナー・ルームウェア＞レディースインナー＞ペチコート","qoo_catid": "300002186","qoo_catname": "レディースファッション_アウター_ダウンジャケット・コート","s_keyword": "冬 ハンガー 掛け レディース冬 ビジネス おしゃれ かわいい ロング カシミヤ 黒 綺麗 防寒 カジュアル チェスター ベージュ ブランド ショート スリム 木製 ハンガーラック 壁掛け 玄関 山崎実業 壁 軽い ダウン aライン スタンド フック 傷つけない 突っ張り レディース冬 レディース冬物 レディース冬軽い レディース冬ロング レディース冬ブランド ダッフル レディース冬モコモコ ビジネスカジュアル トレンチ ハーフ ウール"},
        "ct695": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > ジャンパー、ブルゾン > スカジャン", "y_ct": "2084052541","sex": "0","male": "","female": "","wowma_catid": "510307","wowma_catname": "レディースファッション＞アウター＞スカジャン","qoo_catid": "300002186","qoo_catname": "レディースファッション_アウター_ダウンジャケット・コート","s_keyword": "冬 防寒 ビジネス カジュアル 防水 ゴルフ レディース バイク キッズ オムニヒート 中綿 マウンテンパーカー オフィス 秋冬 スーツ 入学式 ボア コンパクト np71830 150 赤 大きい 5l フード付き 作業着 裏起毛 ゆったり かわいい 黒 オシャレ プロテクター コミネ オール シーズン パーカー j140 デトロイト 古着 プルオーバー j131 ダック 大きいサイズブランド 6l ロング レザー 4l 7l 大きいサイズ5l"},
        "ct696": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > ジャンパー、ブルゾン > ジージャン > Mサイズ", "y_ct": "2084054383","sex": "0","male": "","female": "","wowma_catid": "510317","wowma_catname": "レディースファッション＞アウター＞デニムジャケット","qoo_catid": "300000041","qoo_catname": "レディースファッション_アウター_ジャンパー・ブルゾン","s_keyword": "冬 防寒 ビジネス カジュアル 防水 ゴルフ レディース バイク キッズ オムニヒート 中綿 マウンテンパーカー オフィス 秋冬 スーツ 入学式 ボア コンパクト np71830 150 赤 大きい 5l フード付き 作業着 裏起毛 ゆったり かわいい 黒 オシャレ プロテクター コミネ オール シーズン パーカー j140 デトロイト 古着 プルオーバー j131 ダック 大きいサイズブランド 6l ロング レザー 4l 7l 大きいサイズ5l"},
        "ct1022": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > パーカ > パーカ一般 > Mサイズ", "y_ct": "2084050490","sex": "0","male": "","female": "","wowma_catid": "510301","wowma_catname": "レディースファッション＞アウター＞その他アウター","qoo_catid": "300002186","qoo_catname": "レディースファッション_アウター_ダウンジャケット・コート","s_keyword": "冬 防寒 ビジネス カジュアル 防水 ゴルフ レディース バイク キッズ オムニヒート 中綿 マウンテンパーカー オフィス 秋冬 スーツ 入学式 ボア コンパクト np71830 150 赤 大きい 5l フード付き 作業着 裏起毛 ゆったり かわいい 黒 オシャレ プロテクター コミネ オール シーズン パーカー j140 デトロイト 古着 プルオーバー j131 ダック 大きいサイズブランド 6l ロング レザー 4l 7l 大きいサイズ5l"},
        "ct163": {"ctname": "オークション > ファッション > レディースファッション > カットソー > 長袖 > Mサイズ", "y_ct": "2084050495","sex": "0","male": "","female": "","wowma_catid": "510804","wowma_catname": "レディースファッション＞トップス＞カットソー","qoo_catid": "300002252","qoo_catname": "レディースファッション_トップス_Tシャツ・カットソー","s_keyword": "長袖 vネック ハイネック ワッフル 厚手 ボーダー おしゃれ 秋冬 大きい レディース タートルネック 冬 きれいめ 白 ゆったり 秋 ショート スーツ オフィス 綿 秋冬もの 4l 3l 7分袖 モノトーン キッズ ロングスリーブ ベビー コットン 赤 アシンメトリー アーノルド パーマー あったか 青 インナー 裏起毛 ウール 裏起毛冬レディース 柄 襟付き 柄レディース 映画 女の子 オーバーサイズ オフショル オレンジ 重ね着"},
        "ct1108": {"ctname": "オークション > ファッション > レディースファッション > カットソー > 長袖 > Mサイズ", "y_ct": "2084050495","sex": "0","male": "","female": "","wowma_catid": "510804","wowma_catname": "レディースファッション＞トップス＞カットソー","qoo_catid": "300002252","qoo_catname": "レディースファッション_トップス_Tシャツ・カットソー","s_keyword": "長袖 vネック ハイネック ワッフル 厚手 ボーダー おしゃれ 秋冬 大きい レディース タートルネック 冬 きれいめ 白 ゆったり 秋 ショート スーツ オフィス 綿 秋冬もの 4l 3l 7分袖 モノトーン キッズ ロングスリーブ ベビー コットン 赤 アシンメトリー アーノルド パーマー あったか 青 インナー 裏起毛 ウール 裏起毛冬レディース 柄 襟付き 柄レディース 映画 女の子 オーバーサイズ オフショル オレンジ 重ね着"},
        "ct698": {"ctname": "オークション > ファッション > レディースファッション > カットソー > 長袖 > Mサイズ", "y_ct": "2084050495","sex": "0","male": "","female": "","wowma_catid": "510804","wowma_catname": "レディースファッション＞トップス＞カットソー","qoo_catid": "300002252","qoo_catname": "レディースファッション_トップス_Tシャツ・カットソー","s_keyword": "長袖 vネック ハイネック ワッフル 厚手 ボーダー おしゃれ 秋冬 大きい レディース タートルネック 冬 きれいめ 白 ゆったり 秋 ショート スーツ オフィス 綿 秋冬もの 4l 3l 7分袖 モノトーン キッズ ロングスリーブ ベビー コットン 赤 アシンメトリー アーノルド パーマー あったか 青 インナー 裏起毛 ウール 裏起毛冬レディース 柄 襟付き 柄レディース 映画 女の子 オーバーサイズ オフショル オレンジ 重ね着"},
        "ct699": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > Vネック > その他", "y_ct": "2084051324","sex": "0","male": "","female": "","wowma_catid": "510801","wowma_catname": "レディースファッション＞トップス＞Tシャツ","qoo_catid": "300002767","qoo_catname": "レディースファッション_ワンピース・ドレス_Tシャツワンピ","s_keyword": "tシャツ 半袖 長袖 レディース おもしろ おおきいサイズ vネック スポーツ 速乾 厚手 無地 セット 白 黒 冬 ゆったり 七分袖 7分袖 グリマー びーふぃー バスケ キッズ 大人 赤 サンタ 安い トナカイ 面白い 文字 猫 青ラベル ジャパンフィット 赤ラベル 3p ビーフィー ロング ランニング へいんす アニメ 青 犬 インナー イラスト 印刷 印刷シート インク インコ 犬柄"},
        "ct700": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > その他", "y_ct": "2084051326","sex": "0","male": "","female": "","wowma_catid": "510801","wowma_catname": "レディースファッション＞トップス＞Tシャツ","qoo_catid": "300002767","qoo_catname": "レディースファッション_ワンピース・ドレス_Tシャツワンピ","s_keyword": "tシャツ 半袖 長袖 レディース おもしろ おおきいサイズ vネック スポーツ 速乾 厚手 無地 セット 白 黒 冬 ゆったり 七分袖 7分袖 グリマー びーふぃー バスケ キッズ 大人 赤 サンタ 安い トナカイ 面白い 文字 猫 青ラベル ジャパンフィット 赤ラベル 3p ビーフィー ロング ランニング へいんす アニメ 青 犬 インナー イラスト 印刷 印刷シート インク インコ 犬柄"},
        "ct1102": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Lサイズ > その他", "y_ct": "2084051342","sex": "0","male": "","female": "","wowma_catid": "510801","wowma_catname": "レディースファッション＞トップス＞Tシャツ","qoo_catid": "300002767","qoo_catname": "レディースファッション_ワンピース・ドレス_Tシャツワンピ","s_keyword": "tシャツ 半袖 長袖 レディース おもしろ おおきいサイズ vネック スポーツ 速乾 厚手 無地 セット 白 黒 冬 ゆったり 七分袖 7分袖 グリマー びーふぃー バスケ キッズ 大人 赤 サンタ 安い トナカイ 面白い 文字 猫 青ラベル ジャパンフィット 赤ラベル 3p ビーフィー ロング ランニング へいんす アニメ 青 犬 インナー イラスト 印刷 印刷シート インク インコ 犬柄"},
        "ct704": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Lサイズ > その他", "y_ct": "2084051342","sex": "0","male": "","female": "","wowma_catid": "510801","wowma_catname": "レディースファッション＞トップス＞Tシャツ","qoo_catid": "300002767","qoo_catname": "レディースファッション_ワンピース・ドレス_Tシャツワンピ","s_keyword": "tシャツ 半袖 長袖 レディース おもしろ おおきいサイズ vネック スポーツ 速乾 厚手 無地 セット 白 黒 冬 ゆったり 七分袖 7分袖 グリマー びーふぃー バスケ キッズ 大人 赤 サンタ 安い トナカイ 面白い 文字 猫 青ラベル ジャパンフィット 赤ラベル 3p ビーフィー ロング ランニング へいんす アニメ 青 犬 インナー イラスト 印刷 印刷シート インク インコ 犬柄"},
        "ct701": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > 丸首 > イラスト、キャラクター", "y_ct": "2084051314","sex": "0","male": "","female": "","wowma_catid": "510801","wowma_catname": "レディースファッション＞トップス＞Tシャツ","qoo_catid": "300002767","qoo_catname": "レディースファッション_ワンピース・ドレス_Tシャツワンピ","s_keyword": "tシャツ 半袖 長袖 レディース おもしろ おおきいサイズ vネック スポーツ 速乾 厚手 無地 セット 白 黒 冬 ゆったり 七分袖 7分袖 グリマー びーふぃー バスケ キッズ 大人 赤 サンタ 安い トナカイ 面白い 文字 猫 青ラベル ジャパンフィット 赤ラベル 3p ビーフィー ロング ランニング へいんす アニメ 青 犬 インナー イラスト 印刷 印刷シート インク インコ 犬柄"},
        "ct702": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > その他の袖丈", "y_ct": "2084054032","sex": "0","male": "","female": "","wowma_catid": "510801","wowma_catname": "レディースファッション＞トップス＞Tシャツ","qoo_catid": "300002767","qoo_catname": "レディースファッション_ワンピース・ドレス_Tシャツワンピ","s_keyword": "tシャツ 半袖 長袖 レディース おもしろ おおきいサイズ vネック スポーツ 速乾 厚手 無地 セット 白 黒 冬 ゆったり 七分袖 7分袖 グリマー びーふぃー バスケ キッズ 大人 赤 サンタ 安い トナカイ 面白い 文字 猫 青ラベル ジャパンフィット 赤ラベル 3p ビーフィー ロング ランニング へいんす アニメ 青 犬 インナー イラスト 印刷 印刷シート インク インコ 犬柄"},
        "ct1107": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > その他", "y_ct": "2084051326","sex": "0","male": "","female": "","wowma_catid": "510801","wowma_catname": "レディースファッション＞トップス＞Tシャツ","qoo_catid": "300002767","qoo_catname": "レディースファッション_ワンピース・ドレス_Tシャツワンピ","s_keyword": "tシャツ 半袖 長袖 レディース おもしろ おおきいサイズ vネック スポーツ 速乾 厚手 無地 セット 白 黒 冬 ゆったり 七分袖 7分袖 グリマー びーふぃー バスケ キッズ 大人 赤 サンタ 安い トナカイ 面白い 文字 猫 青ラベル ジャパンフィット 赤ラベル 3p ビーフィー ロング ランニング へいんす アニメ 青 犬 インナー イラスト 印刷 印刷シート インク インコ 犬柄"},
        "ct703": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > その他", "y_ct": "2084051326","sex": "0","male": "","female": "","wowma_catid": "510801","wowma_catname": "レディースファッション＞トップス＞Tシャツ","qoo_catid": "300002767","qoo_catname": "レディースファッション_ワンピース・ドレス_Tシャツワンピ","s_keyword": "tシャツ 半袖 長袖 レディース おもしろ おおきいサイズ vネック スポーツ 速乾 厚手 無地 セット 白 黒 冬 ゆったり 七分袖 7分袖 グリマー びーふぃー バスケ キッズ 大人 赤 サンタ 安い トナカイ 面白い 文字 猫 青ラベル ジャパンフィット 赤ラベル 3p ビーフィー ロング ランニング へいんす アニメ 青 犬 インナー イラスト 印刷 印刷シート インク インコ 犬柄"},
        "ct1111": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > Vネック > 柄もの", "y_ct": "2084051321","sex": "0","male": "","female": "","wowma_catid": "510801","wowma_catname": "レディースファッション＞トップス＞Tシャツ","qoo_catid": "300002767","qoo_catname": "レディースファッション_ワンピース・ドレス_Tシャツワンピ","s_keyword": "tシャツ 半袖 長袖 レディース おもしろ おおきいサイズ vネック スポーツ 速乾 厚手 無地 セット 白 黒 冬 ゆったり 七分袖 7分袖 グリマー びーふぃー バスケ キッズ 大人 赤 サンタ 安い トナカイ 面白い 文字 猫 青ラベル ジャパンフィット 赤ラベル 3p ビーフィー ロング ランニング へいんす アニメ 青 犬 インナー イラスト 印刷 印刷シート インク インコ 犬柄"},
        "ct1112": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > 丸首 > 文字、ロゴ", "y_ct": "2084051317","sex": "0","male": "","female": "","wowma_catid": "510801","wowma_catname": "レディースファッション＞トップス＞Tシャツ","qoo_catid": "300002767","qoo_catname": "レディースファッション_ワンピース・ドレス_Tシャツワンピ","s_keyword": "tシャツ 半袖 長袖 レディース おもしろ おおきいサイズ vネック スポーツ 速乾 厚手 無地 セット 白 黒 冬 ゆったり 七分袖 7分袖 グリマー びーふぃー バスケ キッズ 大人 赤 サンタ 安い トナカイ 面白い 文字 猫 青ラベル ジャパンフィット 赤ラベル 3p ビーフィー ロング ランニング へいんす アニメ 青 犬 インナー イラスト 印刷 印刷シート インク インコ 犬柄"},
        "ct705": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486","sex": "0","male": "","female": "","wowma_catid": "510815","wowma_catname": "レディースファッション＞トップス＞ブラウス","qoo_catid": "300000013","qoo_catname": "レディースファッション_トップス_シャツ・ブラウス","s_keyword": "レディース 長袖 オフィス おしゃれ 白 シャツ 量産型 事務服 フォーマル かわいい 黒 ハイネック 冬 七分袖 形状記憶 オフィス大きめ 無地 オフィス大きい 柄 おしゃれ黒 シースルー おしゃれ冬 おしゃれ前あき 丸襟 リボン スタンドカラー ボタンなし 韓国 襟付き ピンク ロリータ ノーアイロン ストレッチ リボン付き 4l キッズ 150 子供 フリル 赤 青 厚手 秋冬 あったか 暖かい インナー インデックス イエナ 裏起毛"},
        "ct706": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486","sex": "0","male": "","female": "","wowma_catid": "510815","wowma_catname": "レディースファッション＞トップス＞ブラウス","qoo_catid": "300000013","qoo_catname": "レディースファッション_トップス_シャツ・ブラウス","s_keyword": "レディース 長袖 オフィス おしゃれ 白 シャツ 事務服 フォーマル かわいい 黒 ハイネック 冬 七分袖 形状記憶 オフィス大きめ 無地 オフィス大きい 柄 おしゃれ黒 シースルー おしゃれ冬 おしゃれ前あき 丸襟 リボン スタンドカラー ボタンなし 韓国 襟付き ピンク ロリータ ノーアイロン ストレッチ リボン付き 4l キッズ 150 子供 フリル 赤 青 厚手 秋冬 あったか 暖かい インナー インデックス イエナ 裏起毛"},
        "ct707": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486","sex": "0","male": "","female": "","wowma_catid": "510815","wowma_catname": "レディースファッション＞トップス＞ブラウス","qoo_catid": "300000013","qoo_catname": "レディースファッション_トップス_シャツ・ブラウス","s_keyword": "レディース 長袖 オフィス おしゃれ 白 シャツ 事務服 フォーマル かわいい 黒 ハイネック 冬 七分袖 形状記憶 オフィス大きめ 無地 オフィス大きい 柄 おしゃれ黒 シースルー おしゃれ冬 おしゃれ前あき 丸襟 リボン スタンドカラー ボタンなし 韓国 襟付き ピンク ロリータ ノーアイロン ストレッチ リボン付き 4l キッズ 150 子供 フリル 赤 青 厚手 秋冬 あったか 暖かい インナー インデックス イエナ 裏起毛"},
        "ct708": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486","sex": "0","male": "","female": "","wowma_catid": "510815","wowma_catname": "レディースファッション＞トップス＞ブラウス","qoo_catid": "300000013","qoo_catname": "レディースファッション_トップス_シャツ・ブラウス","s_keyword": "レディース 長袖 オフィス おしゃれ 白 シャツ 事務服 フォーマル かわいい 黒 ハイネック 冬 七分袖 形状記憶 オフィス大きめ 無地 オフィス大きい 柄 おしゃれ黒 シースルー おしゃれ冬 おしゃれ前あき 丸襟 リボン スタンドカラー ボタンなし 韓国 襟付き ピンク ロリータ ノーアイロン ストレッチ リボン付き 4l キッズ 150 子供 フリル 赤 青 厚手 秋冬 あったか 暖かい インナー インデックス イエナ 裏起毛"},
        "ct1045": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486","sex": "0","male": "","female": "","wowma_catid": "510815","wowma_catname": "レディースファッション＞トップス＞ブラウス","qoo_catid": "300000013","qoo_catname": "レディースファッション_トップス_シャツ・ブラウス","s_keyword": "レディース 長袖 オフィス おしゃれ 白 シャツ 事務服 フォーマル かわいい 黒 ハイネック 冬 七分袖 形状記憶 オフィス大きめ 無地 オフィス大きい 柄 おしゃれ黒 シースルー おしゃれ冬 おしゃれ前あき 丸襟 リボン スタンドカラー ボタンなし 韓国 襟付き ピンク ロリータ ノーアイロン ストレッチ リボン付き 4l キッズ 150 子供 フリル 赤 青 厚手 秋冬 あったか 暖かい インナー インデックス イエナ 裏起毛"},
        "ct1044": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486","sex": "0","male": "","female": "","wowma_catid": "510815","wowma_catname": "レディースファッション＞トップス＞ブラウス","qoo_catid": "300000013","qoo_catname": "レディースファッション_トップス_シャツ・ブラウス","s_keyword": "レディース 長袖 オフィス おしゃれ 白 シャツ 事務服 フォーマル かわいい 黒 ハイネック 冬 七分袖 形状記憶 オフィス大きめ 無地 オフィス大きい 柄 おしゃれ黒 シースルー おしゃれ冬 おしゃれ前あき 丸襟 リボン スタンドカラー ボタンなし 韓国 襟付き ピンク ロリータ ノーアイロン ストレッチ リボン付き 4l キッズ 150 子供 フリル 赤 青 厚手 秋冬 あったか 暖かい インナー インデックス イエナ 裏起毛"},
        "ct709": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486","sex": "0","male": "","female": "","wowma_catid": "510815","wowma_catname": "レディースファッション＞トップス＞ブラウス","qoo_catid": "300000013","qoo_catname": "レディースファッション_トップス_シャツ・ブラウス","s_keyword": "レディース 長袖 オフィス おしゃれ 白 シャツ 事務服 フォーマル かわいい 黒 ハイネック 冬 七分袖 形状記憶 オフィス大きめ 無地 オフィス大きい 柄 おしゃれ黒 シースルー おしゃれ冬 おしゃれ前あき 丸襟 リボン スタンドカラー ボタンなし 韓国 襟付き ピンク ロリータ ノーアイロン ストレッチ リボン付き 4l キッズ 150 子供 フリル 赤 青 厚手 秋冬 あったか 暖かい インナー インデックス イエナ 裏起毛"},
        "ct710": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486","sex": "0","male": "","female": "","wowma_catid": "510815","wowma_catname": "レディースファッション＞トップス＞ブラウス","qoo_catid": "300000013","qoo_catname": "レディースファッション_トップス_シャツ・ブラウス","s_keyword": "レディース 長袖 オフィス おしゃれ 白 シャツ 事務服 フォーマル かわいい 黒 ハイネック 冬 七分袖 形状記憶 オフィス大きめ 無地 オフィス大きい 柄 おしゃれ黒 シースルー おしゃれ冬 おしゃれ前あき 丸襟 リボン スタンドカラー ボタンなし 韓国 襟付き ピンク ロリータ ノーアイロン ストレッチ リボン付き 4l キッズ 150 子供 フリル 赤 青 厚手 秋冬 あったか 暖かい インナー インデックス イエナ 裏起毛"},
        "ct711": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486","sex": "0","male": "","female": "","wowma_catid": "510815","wowma_catname": "レディースファッション＞トップス＞ブラウス","qoo_catid": "300000013","qoo_catname": "レディースファッション_トップス_シャツ・ブラウス","s_keyword": "レディース 長袖 オフィス おしゃれ 白 シャツ 事務服 フォーマル かわいい 黒 ハイネック 冬 七分袖 形状記憶 オフィス大きめ 無地 オフィス大きい 柄 おしゃれ黒 シースルー おしゃれ冬 おしゃれ前あき 丸襟 リボン スタンドカラー ボタンなし 韓国 襟付き ピンク ロリータ ノーアイロン ストレッチ リボン付き 4l キッズ 150 子供 フリル 赤 青 厚手 秋冬 あったか 暖かい インナー インデックス イエナ 裏起毛"},
        "ct715": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486","sex": "0","male": "","female": "","wowma_catid": "510815","wowma_catname": "レディースファッション＞トップス＞ブラウス","qoo_catid": "300000013","qoo_catname": "レディースファッション_トップス_シャツ・ブラウス","s_keyword": "レディース 長袖 オフィス おしゃれ 白 シャツ 事務服 フォーマル かわいい 黒 ハイネック 冬 七分袖 形状記憶 オフィス大きめ 無地 オフィス大きい 柄 おしゃれ黒 シースルー おしゃれ冬 おしゃれ前あき 丸襟 リボン スタンドカラー ボタンなし 韓国 襟付き ピンク ロリータ ノーアイロン ストレッチ リボン付き 4l キッズ 150 子供 フリル 赤 青 厚手 秋冬 あったか 暖かい インナー インデックス イエナ 裏起毛"},
        "ct712": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > その他", "y_ct": "2084051326","sex": "0","male": "","female": "","wowma_catid": "510801","wowma_catname": "レディースファッション＞トップス＞Tシャツ","qoo_catid": "300002767","qoo_catname": "レディースファッション_ワンピース・ドレス_Tシャツワンピ","s_keyword": "tシャツ 半袖 長袖 レディース おもしろ おおきいサイズ vネック スポーツ 速乾 厚手 無地 セット 白 黒 冬 ゆったり 七分袖 7分袖 グリマー びーふぃー バスケ キッズ 大人 赤 サンタ 安い トナカイ 面白い 文字 猫 青ラベル ジャパンフィット 赤ラベル 3p ビーフィー ロング ランニング へいんす アニメ 青 犬 インナー イラスト 印刷 印刷シート インク インコ 犬柄"},
        "ct713": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > その他", "y_ct": "2084051326","sex": "0","male": "","female": "","wowma_catid": "510801","wowma_catname": "レディースファッション＞トップス＞Tシャツ","qoo_catid": "300002767","qoo_catname": "レディースファッション_ワンピース・ドレス_Tシャツワンピ","s_keyword": "tシャツ 半袖 長袖 レディース おもしろ おおきいサイズ vネック スポーツ 速乾 厚手 無地 セット 白 黒 冬 ゆったり 七分袖 7分袖 グリマー びーふぃー バスケ キッズ 大人 赤 サンタ 安い トナカイ 面白い 文字 猫 青ラベル ジャパンフィット 赤ラベル 3p ビーフィー ロング ランニング へいんす アニメ 青 犬 インナー イラスト 印刷 印刷シート インク インコ 犬柄"},
        "ct714": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 半袖 > Mサイズ", "y_ct": "2084064237","sex": "0","male": "","female": "","wowma_catid": "510815","wowma_catname": "レディースファッション＞トップス＞ブラウス","qoo_catid": "300000013","qoo_catname": "レディースファッション_トップス_シャツ・ブラウス","s_keyword": "レディース 長袖 オフィス おしゃれ 白 シャツ 事務服 フォーマル かわいい 黒 ハイネック 冬 七分袖 形状記憶 オフィス大きめ 無地 オフィス大きい 柄 おしゃれ黒 シースルー おしゃれ冬 おしゃれ前あき 丸襟 リボン スタンドカラー ボタンなし 韓国 襟付き ピンク ロリータ ノーアイロン ストレッチ リボン付き 4l キッズ 150 子供 フリル 赤 青 厚手 秋冬 あったか 暖かい インナー インデックス イエナ 裏起毛"},
        "ct716": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 袖なし、ノースリーブ > ノースリーブシャツ一般", "y_ct": "2084027443","sex": "0","male": "","female": "","wowma_catid": "510812","wowma_catname": "レディースファッション＞トップス＞ノースリーブ","qoo_catid": "300000013","qoo_catname": "レディースファッション_トップス_シャツ・ブラウス","s_keyword": "レディース 長袖 オフィス おしゃれ 白 シャツ 事務服 フォーマル かわいい 黒 ハイネック 冬 七分袖 形状記憶 オフィス大きめ 無地 オフィス大きい 柄 おしゃれ黒 シースルー おしゃれ冬 おしゃれ前あき 丸襟 リボン スタンドカラー ボタンなし 韓国 襟付き ピンク ロリータ ノーアイロン ストレッチ リボン付き 4l キッズ 150 子供 フリル 赤 青 厚手 秋冬 あったか 暖かい インナー インデックス イエナ 裏起毛"},
        "ct717": {"ctname": "オークション > ファッション > レディースファッション > キャミソール", "y_ct": "2084064258","sex": "0","male": "","female": "","wowma_catid": "510806","wowma_catname": "レディースファッション＞トップス＞キャミソール","qoo_catid": "300000012","qoo_catname": "レディースファッション_トップス_キャミソール・タンクトップ","s_keyword": "レディース 綿100 レース セット ロング 可愛い シルク カップ付き 激安 赤 大きい 白 上下 中学生 綿 4l 5l 冬 黒 ピンク 見せる インナー ワンピース 秋冬 ミニ サテン ロングレディース タイト 授乳 産後 ベルメゾン 2枚セット あったか 犬印 セットアップ 透け 長め シルク100 シルクサテン 暖かい 汗取り 穴あき 温かい あったかい いちご 裏起毛 薄手 ウイング"},
        "ct719": {"ctname": "オークション > ファッション > レディースファッション > チュニック > 袖なし、ノースリーブ > Mサイズ", "y_ct": "2084231772","sex": "0","male": "","female": "","wowma_catid": "510810","wowma_catname": "レディースファッション＞トップス＞チュニック","qoo_catid": "300002253","qoo_catname": "レディースファッション_トップス_チュニック","s_keyword": "レディース 冬 オシャレ 裏起毛 ニット 大きい 暖かい 3l 冬フリース 冬小さいサイズ 秋冬 きれいめ 60代 50代 ミセス ピンク ハイネック ブランド チェック エプロン おしゃれ 保育士 長袖 エプロン割烹着 レディース冬物 ワンピース ワンピース秋冬 ミニ オフショルダー 40代 黒 冬用 大きいサイズニット ブラウス ブラウス長袖 ブラウス秋冬 白 赤 あったか 秋 インナー ルームウェア ウエスト ウール 裏ボア 冬裏起毛 柄 防水 襟付き エプロン長袖"},
        "ct1110": {"ctname": "オークション > ファッション > レディースファッション > チューブトップ、ベアトップ", "y_ct": "2084243344","sex": "0","male": "","female": "","wowma_catid": "510816","wowma_catname": "レディースファッション＞トップス＞ベアトップ・チューブトップ","qoo_catid": "320001136","qoo_catname": "下着・レッグウェア_キャミソール・ペチコート_ベアトップ・チューブトップ","s_keyword": "レース スパンコール セット ブラジャー フリル ショーツ オレンジ 透明ストラップ ダンス 子供 ひも外せる 120 140 110 肌色 子ども カップなし ラメ フラダンス おすすめ 5l 赤 穴あき 水着 盛れる ワンピース 暖かい 青 温かい あったかい あったか インナー 衣装 裏起毛 薄手 エナメル 柄 演奏会 エクササイズ おおきいサイズ 落ちない 大きい おしゃれ"},
        "ct162": {"ctname": "オークション > ファッション > レディースファッション > カーディガン > Mサイズ", "y_ct": "2084064209","sex": "0","male": "","female": "","wowma_catid": "510805","wowma_catname": "レディースファッション＞トップス＞カーディガン","qoo_catid": "300003071","qoo_catname": "レディースファッション_トップス_カーディガン","s_keyword": "冬 ビジネス ニット フリース 厚手 ロング レディース オフィス ゆったり 黒 短め 大きめ 赤 ポケット カシミア ウール 和風 学生 女子 男子 ベージュ 白 キッズ ナース ダイナソー セット ベビー 4l ブラウン 洗える 大きい ブランド カシミヤ vネック 丸首 ニットジャケット メンズコート 長袖 ニットセーター 羽織コート ロングコート アウター カットソー カジュアル ボーター柄 ニット細見 スーツ ラムウール"},
        "ct720": {"ctname": "オークション > ファッション > レディースファッション > カーディガン > Mサイズ", "y_ct": "2084064209","sex": "0","male": "","female": "","wowma_catid": "510805","wowma_catname": "レディースファッション＞トップス＞カーディガン","qoo_catid": "300003071","qoo_catname": "レディースファッション_トップス_カーディガン","s_keyword": "冬 ビジネス ニット フリース 厚手 ロング レディース オフィス ゆったり 黒 短め 大きめ 赤 ポケット カシミア ウール 和風 学生 女子 男子 ベージュ 白 キッズ ナース ダイナソー セット ベビー 4l ブラウン 洗える 大きい ブランド カシミヤ vネック 丸首 ニットジャケット メンズコート 長袖 ニットセーター 羽織コート ロングコート アウター カットソー カジュアル ボーター柄 ニット細見 スーツ ラムウール"},
        "ct721": {"ctname": "オークション > ファッション > レディースファッション > カーディガン > Mサイズ", "y_ct": "2084064209","sex": "0","male": "","female": "","wowma_catid": "510805","wowma_catname": "レディースファッション＞トップス＞カーディガン","qoo_catid": "300003071","qoo_catname": "レディースファッション_トップス_カーディガン","s_keyword": "冬 ビジネス ニット フリース 厚手 ロング レディース オフィス ゆったり 黒 短め 大きめ 赤 ポケット カシミア ウール 和風 学生 女子 男子 ベージュ 白 キッズ ナース ダイナソー セット ベビー 4l ブラウン 洗える 大きい ブランド カシミヤ vネック 丸首 ニットジャケット メンズコート 長袖 ニットセーター 羽織コート ロングコート アウター カットソー カジュアル ボーター柄 ニット細見 スーツ ラムウール"},
        "ct722": {"ctname": "オークション > ファッション > レディースファッション > ニット、セーター > 長袖 > Mサイズ", "y_ct": "2084064247","sex": "0","male": "","female": "","wowma_catid": "510811","wowma_catname": "レディースファッション＞トップス＞ニット・セーター","qoo_catid": "300000025","qoo_catname": "レディースファッション_トップス_ニット","s_keyword": "冬 ビジネス vネック ゴルフ タートルネック ニット 人気のゴルフ  レディース ゆったり 秋冬 かわいい ダサい キッズ 子供 ペアルック ベビー 親子 ダサイ 大きい カシミヤニット 長い ウール ボーイズ 学生 厚手 冬服 ボーダー ブランド 白 ハイネック v カシミヤ おしゃれ 洗える 5l 4l 5xl 柄 ジップ s メンズコットン ホワイト l 赤 編み物 本"},
        "ct723": {"ctname": "オークション > ファッション > レディースファッション > ニット、セーター > 長袖 > Mサイズ", "y_ct": "2084064247","sex": "0","male": "","female": "","wowma_catid": "510811","wowma_catname": "レディースファッション＞トップス＞ニット・セーター","qoo_catid": "300000025","qoo_catname": "レディースファッション_トップス_ニット","s_keyword": "冬 ビジネス vネック ゴルフ タートルネック ニット 人気のゴルフ  レディース ゆったり 秋冬 かわいい ダサい キッズ 子供 ペアルック ベビー 親子 ダサイ 大きい カシミヤニット 長い ウール ボーイズ 学生 厚手 冬服 ボーダー ブランド 白 ハイネック v カシミヤ おしゃれ 洗える 5l 4l 5xl 柄 ジップ s メンズコットン ホワイト l 赤 編み物 本"},
        "ct724": {"ctname": "オークション > ファッション > レディースファッション > ニット、セーター > 長袖 > Mサイズ", "y_ct": "2084064247","sex": "0","male": "","female": "","wowma_catid": "510811","wowma_catname": "レディースファッション＞トップス＞ニット・セーター","qoo_catid": "300000025","qoo_catname": "レディースファッション_トップス_ニット","s_keyword": "冬 ビジネス vネック ゴルフ タートルネック ニット 人気のゴルフ  レディース ゆったり 秋冬 かわいい ダサい キッズ 子供 ペアルック ベビー 親子 ダサイ 大きい カシミヤニット 長い ウール ボーイズ 学生 厚手 冬服 ボーダー ブランド 白 ハイネック v カシミヤ おしゃれ 洗える 5l 4l 5xl 柄 ジップ s メンズコットン ホワイト l 赤 編み物 本"},
        "ct725": {"ctname": "オークション > ファッション > レディースファッション > ニット、セーター > 長袖 > Mサイズ", "y_ct": "2084064247","sex": "0","male": "","female": "","wowma_catid": "510811","wowma_catname": "レディースファッション＞トップス＞ニット・セーター","qoo_catid": "300000025","qoo_catname": "レディースファッション_トップス_ニット","s_keyword": "冬 ビジネス vネック ゴルフ タートルネック ニット 人気のゴルフ  レディース ゆったり 秋冬 かわいい ダサい キッズ 子供 ペアルック ベビー 親子 ダサイ 大きい カシミヤニット 長い ウール ボーイズ 学生 厚手 冬服 ボーダー ブランド 白 ハイネック v カシミヤ おしゃれ 洗える 5l 4l 5xl 柄 ジップ s メンズコットン ホワイト l 赤 編み物 本"},
        "ct726": {"ctname": "オークション > ファッション > レディースファッション > カーディガン > Mサイズ", "y_ct": "2084064209","sex": "0","male": "","female": "","wowma_catid": "510805","wowma_catname": "レディースファッション＞トップス＞カーディガン","qoo_catid": "300003071","qoo_catname": "レディースファッション_トップス_カーディガン","s_keyword": "冬 ビジネス ニット フリース 厚手 ロング レディース オフィス ゆったり 黒 短め 大きめ 赤 ポケット カシミア ウール 和風 学生 女子 男子 ベージュ 白 キッズ ナース ダイナソー セット ベビー 4l ブラウン 洗える 大きい ブランド カシミヤ vネック 丸首 ニットジャケット メンズコート 長袖 ニットセーター 羽織コート ロングコート アウター カットソー カジュアル ボーター柄 ニット細見 スーツ ラムウール"},
        "ct727": {"ctname": "オークション > ファッション > レディースファッション > カーディガン > Mサイズ", "y_ct": "2084064209","sex": "0","male": "","female": "","wowma_catid": "510805","wowma_catname": "レディースファッション＞トップス＞カーディガン","qoo_catid": "300003071","qoo_catname": "レディースファッション_トップス_カーディガン","s_keyword": "冬 ビジネス ニット フリース 厚手 ロング レディース オフィス ゆったり 黒 短め 大きめ 赤 ポケット カシミア ウール 和風 学生 女子 男子 ベージュ 白 キッズ ナース ダイナソー セット ベビー 4l ブラウン 洗える 大きい ブランド カシミヤ vネック 丸首 ニットジャケット メンズコート 長袖 ニットセーター 羽織コート ロングコート アウター カットソー カジュアル ボーター柄 ニット細見 スーツ ラムウール"},
        "ct122": {"ctname": "オークション > ファッション > レディースファッション > パンツ、スラックス > Mサイズ", "y_ct": "2084224590","sex": "0","male": "","female": "","wowma_catid": "511001","wowma_catname": "レディースファッション＞パンツ＞その他パンツ","qoo_catid": "300002763","qoo_catname": "レディースファッション_パンツ_その他","s_keyword": "冬 ハンガー ハンガーラック すそ上げ済み パンツ レディース レディース 裏起毛 カジュアル 裾上げ済 ストレッチ 冬用 アジャスター ツータック ビジネス スリム 挟む クリップ 木製 洗濯 スタンド 極太 キャスター キャスター付き ハンガーラック30本 20本 山善 10本 2段 日本製 大きい ノータック 秋冬 ワイド 裾上げ 白 秋冬物 大きいサイズ秋冬 裾上げ済み ストライプ ワンタック ウール 黒 暖かい ネイビー アジャスター付き アイロン 赤"},
        "ct728": {"ctname": "オークション > ファッション > レディースファッション > パンツ、スラックス > Mサイズ", "y_ct": "2084224590","sex": "0","male": "","female": "","wowma_catid": "511001","wowma_catname": "レディースファッション＞パンツ＞その他パンツ","qoo_catid": "300002763","qoo_catname": "レディースファッション_パンツ_その他","s_keyword": "冬 ハンガー ハンガーラック すそ上げ済み パンツ レディース レディース 裏起毛 カジュアル 裾上げ済 ストレッチ 冬用 アジャスター ツータック ビジネス スリム 挟む クリップ 木製 洗濯 スタンド 極太 キャスター キャスター付き ハンガーラック30本 20本 山善 10本 2段 日本製 大きい ノータック 秋冬 ワイド 裾上げ 白 秋冬物 大きいサイズ秋冬 裾上げ済み ストライプ ワンタック ウール 黒 暖かい ネイビー アジャスター付き アイロン 赤"},
        "ct1008": {"ctname": "オークション > ファッション > レディースファッション > レギンス、トレンカ", "y_ct": "2084007161","sex": "0","male": "","female": "","wowma_catid": "511011","wowma_catname": "レディースファッション＞パンツ＞スパッツ・レギンス","qoo_catid": "300000047","qoo_catname": "レディースファッション_パンツ_レギンス","s_keyword": "レディース 冬 タイツ 裏起毛 スポーツ マタニティ munny パンツ 7分丈 綿 柄 オシャレ 5分丈 ヨガ 防寒 ランニング 7部丈 靴下屋 ベージュ レディースユニクロ 肌色 レザー おおきいサイズ 300デニール 皮 ゆったり デニム 2l 裏起毛ひざ下 寒 ７分 大きい スポーツ5分丈 裏起毛s チェック ジュニア コールドギア キッズ 2.0 トレーニング/men ヒートギア べるみす 着圧 あったか 暖かい 穴あき 厚手 赤ちゃん"},
        "ct1009": {"ctname": "オークション > ファッション > レディースファッション > ワークパンツ、ペインターパンツ > Mサイズ", "y_ct": "2084224605","sex": "0","male": "","female": "","wowma_catid": "511001","wowma_catname": "レディースファッション＞パンツ＞その他パンツ","qoo_catid": "300002763","qoo_catname": "レディースファッション_パンツ_その他","s_keyword": "レディース レッドキャップ 裏起毛 冬 ストレッチ ゆったり 冬用 カーゴ 874 大きい 青 チノパン デニム 作業用 グレー 防風 作業 ハイウエスト ネイビー pt20 pt50 白 防水 アヴィレックス 赤 アメカジ 厚手 アウトドア カーゴパンツ ズボン 作業服 ゆったりポケット 綿 裏ボア 頑丈 ポケット多い 洗えるベルト付き オレンジ おしゃれ オリーブ カーキ カジュアル レッドきゃっぷ 黒 紺 作業着 スリム"},
        "ct1010": {"ctname": "オークション > ファッション > レディースファッション > ワークパンツ、ペインターパンツ > Mサイズ", "y_ct": "2084224605","sex": "0","male": "","female": "","wowma_catid": "511001","wowma_catname": "レディースファッション＞パンツ＞その他パンツ","qoo_catid": "300002763","qoo_catname": "レディースファッション_パンツ_その他","s_keyword": "レディース レッドキャップ 裏起毛 冬 ストレッチ ゆったり 冬用 カーゴ 874 大きい 青 チノパン デニム 作業用 グレー 防風 作業 ハイウエスト ネイビー pt20 pt50 白 防水 アヴィレックス 赤 アメカジ 厚手 アウトドア カーゴパンツ ズボン 作業服 ゆったりポケット 綿 裏ボア 頑丈 ポケット多い 洗えるベルト付き オレンジ おしゃれ オリーブ カーキ カジュアル レッドきゃっぷ 黒 紺 作業着 スリム"},
        "ct1047": {"ctname": "オークション > ファッション > レディースファッション > パンツ、スラックス > Mサイズ", "y_ct": "2084224590","sex": "0","male": "","female": "","wowma_catid": "511001","wowma_catname": "レディースファッション＞パンツ＞その他パンツ","qoo_catid": "300002763","qoo_catname": "レディースファッション_パンツ_その他","s_keyword": "冬 ハンガー ハンガーラック すそ上げ済み パンツ レディース レディース 裏起毛 カジュアル 裾上げ済 ストレッチ 冬用 アジャスター ツータック ビジネス スリム 挟む クリップ 木製 洗濯 スタンド 極太 キャスター キャスター付き ハンガーラック30本 20本 山善 10本 2段 日本製 大きい ノータック 秋冬 ワイド 裾上げ 白 秋冬物 大きいサイズ秋冬 裾上げ済み ストライプ ワンタック ウール 黒 暖かい ネイビー アジャスター付き アイロン 赤"},
        "ct738": {"ctname": "オークション > ファッション > レディースファッション > スカート > ロングスカート > その他", "y_ct": "2084007175","sex": "0","male": "","female": "","wowma_catid": "510601","wowma_catname": "レディースファッション＞スカート＞その他スカート","qoo_catid": "300002764","qoo_catname": "レディースファッション_スカート_ロングスカート","s_keyword": "レディース 秋冬 ハンガー 冬 膝丈 黒 ロング ミニ きれいめ チェック 膝上 タイト ウエストゴム 省スペース 跡がつかない プラスチック 木製 連結 ゴールド 白 ピンク 日本製 マタニティ ゴルフ ゴム 小さめ 木 78cm 90 120 150 赤 ファー 裏起毛 マーメイド シャーリング フラワー スリット プリーツ シアー ブラック 花柄 チュール パンツ オレンジ ドット ツイード ひざ丈"},
        "ct739": {"ctname": "オークション > ファッション > レディースファッション > スカート > ロングスカート > その他", "y_ct": "2084007175","sex": "0","male": "","female": "","wowma_catid": "510601","wowma_catname": "レディースファッション＞スカート＞その他スカート","qoo_catid": "300002764","qoo_catname": "レディースファッション_スカート_ロングスカート","s_keyword": "レディース 秋冬 ハンガー 冬 膝丈 黒 ロング ミニ きれいめ チェック 膝上 タイト ウエストゴム 省スペース 跡がつかない プラスチック 木製 連結 ゴールド 白 ピンク 日本製 マタニティ ゴルフ ゴム 小さめ 木 78cm 90 120 150 赤 ファー 裏起毛 マーメイド シャーリング フラワー スリット プリーツ シアー ブラック 花柄 チュール パンツ オレンジ ドット ツイード ひざ丈"},
        "ct740": {"ctname": "オークション > ファッション > レディースファッション > スカート > ロングスカート > その他", "y_ct": "2084007175","sex": "0","male": "","female": "","wowma_catid": "510601","wowma_catname": "レディースファッション＞スカート＞その他スカート","qoo_catid": "300002764","qoo_catname": "レディースファッション_スカート_ロングスカート","s_keyword": "レディース 秋冬 ハンガー 冬 膝丈 黒 ロング ミニ きれいめ チェック 膝上 タイト ウエストゴム 省スペース 跡がつかない プラスチック 木製 連結 ゴールド 白 ピンク 日本製 マタニティ ゴルフ ゴム 小さめ 木 78cm 90 120 150 赤 ファー 裏起毛 マーメイド シャーリング フラワー スリット プリーツ シアー ブラック 花柄 チュール パンツ オレンジ ドット ツイード ひざ丈"},
        "ct741": {"ctname": "オークション > ファッション > レディースファッション > スカート > ミニスカート > その他", "y_ct": "2084007171","sex": "0","male": "","female": "","wowma_catid": "510601","wowma_catname": "レディースファッション＞スカート＞その他スカート","qoo_catid": "300000040","qoo_catname": "レディースファッション_スカート_ミニスカート","s_keyword": "レディース 秋冬 ハンガー 冬 膝丈 黒 ロング ミニ きれいめ チェック 膝上 タイト ウエストゴム 省スペース 跡がつかない プラスチック 木製 連結 ゴールド 白 ピンク 日本製 マタニティ ゴルフ ゴム 小さめ 木 78cm 90 120 150 赤 ファー 裏起毛 マーメイド シャーリング フラワー スリット プリーツ シアー ブラック 花柄 チュール パンツ オレンジ ドット ツイード ひざ丈"},
        "ct742": {"ctname": "オークション > ファッション > レディースファッション > スカート > ミニスカート > タイトスカート > Mサイズ", "y_ct": "2084222253","sex": "0","male": "","female": "","wowma_catid": "510605","wowma_catname": "レディースファッション＞スカート＞タイトスカート","qoo_catid": "300002247","qoo_catname": "レディースファッション_スーツ_スカートスーツ","s_keyword": "レディース 秋冬 ハンガー 冬 膝丈 黒 ロング ミニ きれいめ チェック 膝上 タイト ウエストゴム 省スペース 跡がつかない プラスチック 木製 連結 ゴールド 白 ピンク 日本製 マタニティ ゴルフ ゴム 小さめ 木 78cm 90 120 150 赤 ファー 裏起毛 マーメイド シャーリング フラワー スリット プリーツ シアー ブラック 花柄 チュール パンツ オレンジ ドット ツイード ひざ丈"},
        "ct743": {"ctname": "オークション > ファッション > レディースファッション > スカート > ひざ丈スカート > その他", "y_ct": "2084054014","sex": "0","male": "","female": "","wowma_catid": "510601","wowma_catname": "レディースファッション＞スカート＞その他スカート","qoo_catid": "300002860","qoo_catname": "レディースファッション_スカート_その他","s_keyword": "レディース 秋冬 ハンガー 冬 膝丈 黒 ロング ミニ きれいめ チェック 膝上 タイト ウエストゴム 省スペース 跡がつかない プラスチック 木製 連結 ゴールド 白 ピンク 日本製 マタニティ ゴルフ ゴム 小さめ 木 78cm 90 120 150 赤 ファー 裏起毛 マーメイド シャーリング フラワー スリット プリーツ シアー ブラック 花柄 チュール パンツ オレンジ ドット ツイード ひざ丈"},
        "ct744": {"ctname": "オークション > ファッション > レディースファッション > スカート > ひざ丈スカート > プリーツスカート > Mサイズ", "y_ct": "2084222283","sex": "0","male": "","female": "","wowma_catid": "510612","wowma_catname": "レディースファッション＞スカート＞プリーツスカート","qoo_catid": "300002859","qoo_catname": "レディースファッション_スカート_ミディアムスカート","s_keyword": "レディース 秋冬 ハンガー 冬 膝丈 黒 ロング ミニ きれいめ チェック 膝上 タイト ウエストゴム 省スペース 跡がつかない プラスチック 木製 連結 ゴールド 白 ピンク 日本製 マタニティ ゴルフ ゴム 小さめ 木 78cm 90 120 150 赤 ファー 裏起毛 マーメイド シャーリング フラワー スリット プリーツ シアー ブラック 花柄 チュール パンツ オレンジ ドット ツイード ひざ丈"},
        "ct745": {"ctname": "オークション > ファッション > レディースファッション > スカート > ひざ丈スカート > フレアースカート、ギャザースカート > Mサイズ", "y_ct": "2084222278","sex": "0","male": "","female": "","wowma_catid": "510603","wowma_catname": "レディースファッション＞スカート＞ギャザースカート","qoo_catid": "300002860","qoo_catname": "レディースファッション_スカート_その他","s_keyword": "レディース 秋冬 ハンガー 冬 膝丈 黒 ロング ミニ きれいめ チェック 膝上 タイト ウエストゴム 省スペース 跡がつかない プラスチック 木製 連結 ゴールド 白 ピンク 日本製 マタニティ ゴルフ ゴム 小さめ 木 78cm 90 120 150 赤 ファー 裏起毛 マーメイド シャーリング フラワー スリット プリーツ シアー ブラック 花柄 チュール パンツ オレンジ ドット ツイード ひざ丈"},
        "ct746": {"ctname": "オークション > ファッション > レディースファッション > スカート > ひざ丈スカート > タイトスカート > Mサイズ", "y_ct": "2084222273","sex": "0","male": "","female": "","wowma_catid": "510605","wowma_catname": "レディースファッション＞スカート＞タイトスカート","qoo_catid": "300002247","qoo_catname": "レディースファッション_スーツ_スカートスーツ","s_keyword": "レディース 秋冬 ハンガー 冬 膝丈 黒 ロング ミニ きれいめ チェック 膝上 タイト ウエストゴム 省スペース 跡がつかない プラスチック 木製 連結 ゴールド 白 ピンク 日本製 マタニティ ゴルフ ゴム 小さめ 木 78cm 90 120 150 赤 ファー 裏起毛 マーメイド シャーリング フラワー スリット プリーツ シアー ブラック 花柄 チュール パンツ オレンジ ドット ツイード ひざ丈"},
        "ct747": {"ctname": "オークション > ファッション > レディースファッション > スカート > ひざ丈スカート > その他", "y_ct": "2084054014","sex": "0","male": "","female": "","wowma_catid": "510601","wowma_catname": "レディースファッション＞スカート＞その他スカート","qoo_catid": "300002860","qoo_catname": "レディースファッション_スカート_その他","s_keyword": "レディース 秋冬 ハンガー 冬 膝丈 黒 ロング ミニ きれいめ チェック 膝上 タイト ウエストゴム 省スペース 跡がつかない プラスチック 木製 連結 ゴールド 白 ピンク 日本製 マタニティ ゴルフ ゴム 小さめ 木 78cm 90 120 150 赤 ファー 裏起毛 マーメイド シャーリング フラワー スリット プリーツ シアー ブラック 花柄 チュール パンツ オレンジ ドット ツイード ひざ丈"},
        "ct748": {"ctname": "オークション > ファッション > レディースファッション > スカート > ロングスカート > その他", "y_ct": "2084007175","sex": "0","male": "","female": "","wowma_catid": "510601","wowma_catname": "レディースファッション＞スカート＞その他スカート","qoo_catid": "300002764","qoo_catname": "レディースファッション_スカート_ロングスカート","s_keyword": "レディース 秋冬 ハンガー 冬 膝丈 黒 ロング ミニ きれいめ チェック 膝上 タイト ウエストゴム 省スペース 跡がつかない プラスチック 木製 連結 ゴールド 白 ピンク 日本製 マタニティ ゴルフ ゴム 小さめ 木 78cm 90 120 150 赤 ファー 裏起毛 マーメイド シャーリング フラワー スリット プリーツ シアー ブラック 花柄 チュール パンツ オレンジ ドット ツイード ひざ丈"},
        "ct754": {"ctname": "オークション > ファッション > レディースファッション > スカート > ロングスカート > フレアースカート、ギャザースカート > Mサイズ", "y_ct": "2084222298","sex": "0","male": "","female": "","wowma_catid": "510603","wowma_catname": "レディースファッション＞スカート＞ギャザースカート","qoo_catid": "300002860","qoo_catname": "レディースファッション_スカート_その他","s_keyword": "レディース 秋冬 ハンガー 冬 膝丈 黒 ロング ミニ きれいめ チェック 膝上 タイト ウエストゴム 省スペース 跡がつかない プラスチック 木製 連結 ゴールド 白 ピンク 日本製 マタニティ ゴルフ ゴム 小さめ 木 78cm 90 120 150 赤 ファー 裏起毛 マーメイド シャーリング フラワー スリット プリーツ シアー ブラック 花柄 チュール パンツ オレンジ ドット ツイード ひざ丈"},
        "ct156": {"ctname": "オークション > ファッション > レディースファッション > ワンピース > ミニスカート > Mサイズ", "y_ct": "2084224575","sex": "0","male": "","female": "","wowma_catid": "511104","wowma_catname": "レディースファッション＞ワンピース＞ショート・ミニ丈","qoo_catid": "300000040","qoo_catname": "レディースファッション_スカート_ミニスカート","s_keyword": "秋冬 レディース フィギュア ロング ミニ フォーマル 韓国 ゆったり 大きい ニット pop ゾロ ナミ カイドウ ルフィ ヤマト シャンクス ハンコック きれいめ体型カバー 膝丈 きれいめにっと 黒 全巻セット 新品 激安 box カラー版 パジャマ 長袖 セール レース フレアチュール ドット 赤 ノースリーブ マタニティ"},
        "ct749": {"ctname": "オークション > ファッション > レディースファッション > ワンピース > ロングスカート > Mサイズ", "y_ct": "2084224585","sex": "0","male": "","female": "","wowma_catid": "511105","wowma_catname": "レディースファッション＞ワンピース＞ロング・マキシ丈","qoo_catid": "300002764","qoo_catname": "レディースファッション_スカート_ロングスカート","s_keyword": "秋冬 レディース フィギュア ロング ミニ フォーマル 韓国 ゆったり 大きい ニット pop ゾロ ナミ カイドウ ルフィ ヤマト シャンクス ハンコック きれいめ体型カバー 膝丈 きれいめにっと 黒 全巻セット 新品 激安 box カラー版 パジャマ 長袖 セール レース フレアチュール ドット 赤 ノースリーブ マタニティ"},
        "ct750": {"ctname": "オークション > ファッション > レディースファッション > ワンピース > ロングスカート > Mサイズ", "y_ct": "2084224585","sex": "0","male": "","female": "","wowma_catid": "511105","wowma_catname": "レディースファッション＞ワンピース＞ロング・マキシ丈","qoo_catid": "300002764","qoo_catname": "レディースファッション_スカート_ロングスカート","s_keyword": "秋冬 レディース フィギュア ロング ミニ フォーマル 韓国 ゆったり 大きい ニット pop ゾロ ナミ カイドウ ルフィ ヤマト シャンクス ハンコック きれいめ体型カバー 膝丈 きれいめにっと 黒 全巻セット 新品 激安 box カラー版 パジャマ 長袖 セール レース フレアチュール ドット 赤 ノースリーブ マタニティ"},
        "ct751": {"ctname": "オークション > ファッション > レディースファッション > ワンピース > ロングスカート > Mサイズ", "y_ct": "2084224585","sex": "0","male": "","female": "","wowma_catid": "511105","wowma_catname": "レディースファッション＞ワンピース＞ロング・マキシ丈","qoo_catid": "300002764","qoo_catname": "レディースファッション_スカート_ロングスカート","s_keyword": "秋冬 レディース フィギュア ロング ミニ フォーマル 韓国 ゆったり 大きい ニット pop ゾロ ナミ カイドウ ルフィ ヤマト シャンクス ハンコック きれいめ体型カバー 膝丈 きれいめにっと 黒 全巻セット 新品 激安 box カラー版 パジャマ 長袖 セール レース フレアチュール ドット 赤 ノースリーブ マタニティ"},
        "ct752": {"ctname": "オークション > ファッション > レディースファッション > ワンピース > ミニスカート > Mサイズ", "y_ct": "2084224575","sex": "0","male": "","female": "","wowma_catid": "511104","wowma_catname": "レディースファッション＞ワンピース＞ショート・ミニ丈","qoo_catid": "300000040","qoo_catname": "レディースファッション_スカート_ミニスカート","s_keyword": "秋冬 レディース フィギュア ロング ミニ フォーマル 韓国 ゆったり 大きい ニット pop ゾロ ナミ カイドウ ルフィ ヤマト シャンクス ハンコック きれいめ体型カバー 膝丈 きれいめにっと 黒 全巻セット 新品 激安 box カラー版 パジャマ 長袖 セール レース フレアチュール ドット 赤 ノースリーブ マタニティ"},
        "ct753": {"ctname": "オークション > ファッション > レディースファッション > フォーマル > ワンピース", "y_ct": "2084037008","sex": "0","male": "","female": "","wowma_catid": "511101","wowma_catname": "レディースファッション＞ワンピース＞その他ワンピース","qoo_catid": "300002248","qoo_catname": "レディースファッション_スーツ_ワンピーススーツ","s_keyword": "シューズ 女の子 キッズ 23cm 22cm 黒 白 20cm 21cm 19cm 22.5cm バッグ レディース 岩佐 結婚式 大きめ サブバッグ ワンピース 冬 150 120 七五三 ママ 140 スーツ 卒業式 入学式 パンツ 喪服 ドレス 50代 20代 30代 40 ボレロ 男の子 22.5 ブラウン 18 23 24 22 19 23.5 25 日本製 数珠"},
        "ct755": {"ctname": "オークション > ファッション > レディースファッション > フォーマル > ワンピース", "y_ct": "2084037008","sex": "0","male": "","female": "","wowma_catid": "511101","wowma_catname": "レディースファッション＞ワンピース＞その他ワンピース","qoo_catid": "300002248","qoo_catname": "レディースファッション_スーツ_ワンピーススーツ","s_keyword": "シューズ 女の子 キッズ 23cm 22cm 黒 白 20cm 21cm 19cm 22.5cm バッグ レディース 岩佐 結婚式 大きめ サブバッグ ワンピース 冬 150 120 七五三 ママ 140 スーツ 卒業式 入学式 パンツ 喪服 ドレス 50代 20代 30代 40 ボレロ 男の子 22.5 ブラウン 18 23 24 22 19 23.5 25 日本製 数珠"},
        "ct756": {"ctname": "オークション > ファッション > レディースファッション > フォーマル > ワンピース", "y_ct": "2084037008","sex": "0","male": "","female": "","wowma_catid": "511101","wowma_catname": "レディースファッション＞ワンピース＞その他ワンピース","qoo_catid": "300002248","qoo_catname": "レディースファッション_スーツ_ワンピーススーツ","s_keyword": "シューズ 女の子 キッズ 23cm 22cm 黒 白 20cm 21cm 19cm 22.5cm バッグ レディース 岩佐 結婚式 大きめ サブバッグ ワンピース 冬 150 120 七五三 ママ 140 スーツ 卒業式 入学式 パンツ 喪服 ドレス 50代 20代 30代 40 ボレロ 男の子 22.5 ブラウン 18 23 24 22 19 23.5 25 日本製 数珠"},
        "ct757": {"ctname": "オークション > ファッション > レディースファッション > フォーマル > ワンピース", "y_ct": "2084037008","sex": "0","male": "","female": "","wowma_catid": "511101","wowma_catname": "レディースファッション＞ワンピース＞その他ワンピース","qoo_catid": "300002248","qoo_catname": "レディースファッション_スーツ_ワンピーススーツ","s_keyword": "シューズ 女の子 キッズ 23cm 22cm 黒 白 20cm 21cm 19cm 22.5cm バッグ レディース 岩佐 結婚式 大きめ サブバッグ ワンピース 冬 150 120 七五三 ママ 140 スーツ 卒業式 入学式 パンツ 喪服 ドレス 50代 20代 30代 40 ボレロ 男の子 22.5 ブラウン 18 23 24 22 19 23.5 25 日本製 数珠"},
        "ct758": {"ctname": "オークション > ファッション > レディースファッション > フォーマル > ワンピース", "y_ct": "2084037008","sex": "0","male": "","female": "","wowma_catid": "511101","wowma_catname": "レディースファッション＞ワンピース＞その他ワンピース","qoo_catid": "300002248","qoo_catname": "レディースファッション_スーツ_ワンピーススーツ","s_keyword": "シューズ 女の子 キッズ 23cm 22cm 黒 白 20cm 21cm 19cm 22.5cm バッグ レディース 岩佐 結婚式 大きめ サブバッグ ワンピース 冬 150 120 七五三 ママ 140 スーツ 卒業式 入学式 パンツ 喪服 ドレス 50代 20代 30代 40 ボレロ 男の子 22.5 ブラウン 18 23 24 22 19 23.5 25 日本製 数珠"},
        "ct759": {"ctname": "オークション > ファッション > レディースファッション > フォーマル > ワンピース", "y_ct": "2084037008","sex": "0","male": "","female": "","wowma_catid": "511101","wowma_catname": "レディースファッション＞ワンピース＞その他ワンピース","qoo_catid": "300002248","qoo_catname": "レディースファッション_スーツ_ワンピーススーツ","s_keyword": "シューズ 女の子 キッズ 23cm 22cm 黒 白 20cm 21cm 19cm 22.5cm バッグ レディース 岩佐 結婚式 大きめ サブバッグ ワンピース 冬 150 120 七五三 ママ 140 スーツ 卒業式 入学式 パンツ 喪服 ドレス 50代 20代 30代 40 ボレロ 男の子 22.5 ブラウン 18 23 24 22 19 23.5 25 日本製 数珠"},
        "ct760": {"ctname": "オークション > ファッション > レディースファッション > フォーマル > ワンピース", "y_ct": "2084037008","sex": "0","male": "","female": "","wowma_catid": "511101","wowma_catname": "レディースファッション＞ワンピース＞その他ワンピース","qoo_catid": "300002248","qoo_catname": "レディースファッション_スーツ_ワンピーススーツ","s_keyword": "シューズ 女の子 キッズ 23cm 22cm 黒 白 20cm 21cm 19cm 22.5cm バッグ レディース 岩佐 結婚式 大きめ サブバッグ ワンピース 冬 150 120 七五三 ママ 140 スーツ 卒業式 入学式 パンツ 喪服 ドレス 50代 20代 30代 40 ボレロ 男の子 22.5 ブラウン 18 23 24 22 19 23.5 25 日本製 数珠"},
        "ct761": {"ctname": "オークション > ファッション > レディースファッション > フォーマル > ワンピース", "y_ct": "2084037008","sex": "0","male": "","female": "","wowma_catid": "511101","wowma_catname": "レディースファッション＞ワンピース＞その他ワンピース","qoo_catid": "300002248","qoo_catname": "レディースファッション_スーツ_ワンピーススーツ","s_keyword": "シューズ 女の子 キッズ 23cm 22cm 黒 白 20cm 21cm 19cm 22.5cm バッグ レディース 岩佐 結婚式 大きめ サブバッグ ワンピース 冬 150 120 七五三 ママ 140 スーツ 卒業式 入学式 パンツ 喪服 ドレス 50代 20代 30代 40 ボレロ 男の子 22.5 ブラウン 18 23 24 22 19 23.5 25 日本製 数珠"},
        "ct762": {"ctname": "オークション > ファッション > レディースファッション > フォーマル > ワンピース", "y_ct": "2084037008","sex": "0","male": "","female": "","wowma_catid": "511101","wowma_catname": "レディースファッション＞ワンピース＞その他ワンピース","qoo_catid": "300002248","qoo_catname": "レディースファッション_スーツ_ワンピーススーツ","s_keyword": "シューズ 女の子 キッズ 23cm 22cm 黒 白 20cm 21cm 19cm 22.5cm バッグ レディース 岩佐 結婚式 大きめ サブバッグ ワンピース 冬 150 120 七五三 ママ 140 スーツ 卒業式 入学式 パンツ 喪服 ドレス 50代 20代 30代 40 ボレロ 男の子 22.5 ブラウン 18 23 24 22 19 23.5 25 日本製 数珠"},
        "ct1453": {"ctname": "オークション > ファッション > レディースファッション > フォーマル > ワンピース", "y_ct": "2084037008","sex": "0","male": "","female": "","wowma_catid": "511101","wowma_catname": "レディースファッション＞ワンピース＞その他ワンピース","qoo_catid": "300002248","qoo_catname": "レディースファッション_スーツ_ワンピーススーツ","s_keyword": "シューズ 女の子 キッズ 23cm 22cm 黒 白 20cm 21cm 19cm 22.5cm バッグ レディース 岩佐 結婚式 大きめ サブバッグ ワンピース 冬 150 120 七五三 ママ 140 スーツ 卒業式 入学式 パンツ 喪服 ドレス 50代 20代 30代 40 ボレロ 男の子 22.5 ブラウン 18 23 24 22 19 23.5 25 日本製 数珠"},
        "ct765": {"ctname": "オークション > スポーツ、レジャー > スポーツウエア > 女性用 > 上下セット > ジャージ > その他", "y_ct": "2084203510","sex": "0","male": "","female": "","wowma_catid": "402302","wowma_catname": "スポーツ・アウトドア＞スポーツウェア＞ジャージ","qoo_catid": "300000211","qoo_catname": "スポーツ_スポーツウェア_レディーススポーツウェア","s_keyword": "レディース用 長袖 冬 レディース用パンツ  上下 ー下 メンズ上下 防寒 ー上下 子ども メンズ上下 レデース 冬上下 冬ゴルフ 冬ジャケット パンツ 半袖 レデース上下 tシャツ 長袖tシャツ 冬用 上下セット冬物 レディース セール アウター ウィ上 上着 大きい 女の子 あったか キッズ 130 セット 120 150 140 男子 子供 白 下着 ショートパンツ スパッツ スカート スウェット"},
        "ct763": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > その他", "y_ct": "2084053158","sex": "0","male": "","female": "","wowma_catid": "32070201","wowma_catname": "インナー・ルームウェア＞レディースインナー＞ショーツ＞Tバック・タンガ","qoo_catid": "300002872","qoo_catname": "スポーツ_スポーツウェア_レディーススポーツインナー","s_keyword": "レディース 上下セット 福袋 tバック ノンワイヤー かわいい 赤 セット 収納 ガーターベルト パンツ 可愛い 黒 ショーツ 綿 収納ボックス 吊り下げ 引き出し 仕切り チェスト ハンガー 旅行 プラスチック 穴あき 白 メンズシャツ メンズボクサーパンツ 過激人気 メンズトランクス メンズ長袖 暖か メンズ冬 長袖 セクシーtバック 安い セクシーノーワイヤー パール 上下 e70 2022 脇高 ロング トランクス 冬 ビキニ パンツ綿 暖かい"},
        "ct767": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > ブラジャー > その他", "y_ct": "2084053090","sex": "0","male": "","female": "","wowma_catid": "32070603","wowma_catname": "インナー・ルームウェア＞レディースインナー＞ブラ＞その他ブラ","qoo_catid": "300000029","qoo_catname": "下着・レッグウェア_ブラジャー_ブラジャー","s_keyword": "ショーツセット ノンワイヤー わき肉 背中 すっきり セット 福袋 小さく見せる 重力に負けない リボンブラ サルート 脇肉すっきり フルカップ iカップ gカップ b95 5枚セット 綿 レース 3枚セット 大きい すっきりトリンプ ゼロフィール 3l セール ゼロフィール2.0 4l ll ベーシック 天使のブラ プレミアム 恋するブラ 天使のブラセット 脇高 コットン f75 ショーツ e75 s1 364 フラワー tバック 可愛い 洗濯ネット 赤 アジャスター アンダーアツギ"},
        "ct1109": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > その他", "y_ct": "2084053158","sex": "0","male": "","female": "","wowma_catid": "320701","wowma_catname": "インナー・ルームウェア＞レディースインナー＞その他レディースインナー","qoo_catid": "300002267","qoo_catname": "下着・レッグウェア_靴下・レッグウェア_その他","s_keyword": "レディース 上下セット 福袋 tバック ノンワイヤー かわいい 赤 セット 収納 ガーターベルト パンツ 可愛い 黒 ショーツ 綿 収納ボックス 吊り下げ 引き出し 仕切り チェスト ハンガー 旅行 プラスチック 穴あき 白 メンズシャツ メンズボクサーパンツ 過激人気 メンズトランクス メンズ長袖 暖か メンズ冬 長袖 セクシーtバック 安い セクシーノーワイヤー パール 上下 e70 2022 脇高 ロング トランクス 冬 ビキニ パンツ綿 暖かい"},
        "ct768": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > ブラジャー > その他", "y_ct": "2084053090","sex": "0","male": "","female": "","wowma_catid": "32070603","wowma_catname": "インナー・ルームウェア＞レディースインナー＞ブラ＞その他ブラ","qoo_catid": "300000029","qoo_catname": "下着・レッグウェア_ブラジャー_ブラジャー","s_keyword": "ショーツセット ノンワイヤー わき肉 背中 すっきり セット 福袋 小さく見せる 重力に負けない リボンブラ サルート 脇肉すっきり フルカップ iカップ gカップ b95 5枚セット 綿 レース 3枚セット 大きい すっきりトリンプ ゼロフィール 3l セール ゼロフィール2.0 4l ll ベーシック 天使のブラ プレミアム 恋するブラ 天使のブラセット 脇高 コットン f75 ショーツ e75 s1 364 フラワー tバック 可愛い 洗濯ネット 赤 アジャスター アンダーアツギ"},
        "ct769": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > ブラジャー > その他", "y_ct": "2084053090","sex": "0","male": "","female": "","wowma_catid": "32070603","wowma_catname": "インナー・ルームウェア＞レディースインナー＞ブラ＞その他ブラ","qoo_catid": "300000029","qoo_catname": "下着・レッグウェア_ブラジャー_ブラジャー","s_keyword": "ショーツセット ノンワイヤー わき肉 背中 すっきり セット 福袋 小さく見せる 重力に負けない リボンブラ サルート 脇肉すっきり フルカップ iカップ gカップ b95 5枚セット 綿 レース 3枚セット 大きい すっきりトリンプ ゼロフィール 3l セール ゼロフィール2.0 4l ll ベーシック 天使のブラ プレミアム 恋するブラ 天使のブラセット 脇高 コットン f75 ショーツ e75 s1 364 フラワー tバック 可愛い 洗濯ネット 赤 アジャスター アンダーアツギ"},
        "ct770": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > ショーツ > Mサイズ > スタンダード", "y_ct": "2084211818","sex": "0","male": "","female": "","wowma_catid": "32070202","wowma_catname": "インナー・ルームウェア＞レディースインナー＞ショーツ＞その他ショーツ","qoo_catid": "300000030","qoo_catname": "下着・レッグウェア_ショーツ_ショーツ","s_keyword": "ブラジャー セット ノンワイヤー 福袋 深め レディース 綿 ll tバック 浅め ローライズ トラタニ シルク 綿100 ボクサー 3l 日本製 赤 ナプキン タイプ ソフィ xl ロタイプs ブラックフライデー 定期便 ブラ 10枚 盛れるブラジャー スポーツブラ かわいい コットン l サニタリー ボーイレングス レース 364 腹巻き 深ばき 4l サテン 可愛い 黒 5l ブラック 一分丈"},
        "ct771": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > スリップ > Mサイズ", "y_ct": "2084053118","sex": "0","male": "","female": "","wowma_catid": "320713","wowma_catname": "インナー・ルームウェア＞レディースインナー＞スリップ","qoo_catid": "300002833","qoo_catname": "下着・レッグウェア_キャミソール・ペチコート_キャミソール・スリップ","s_keyword": "レディース オンマフラー オン slip-on リード ノット ペンケース ランジェリー マット 大きい ロング レース シルク カップ付き 黒 セット 50.8 60.5 38mm 35mm ショート バイク アメリカン 51mm パスケース ブックカバー 財布 キーケース ボールペン リール 小銭入れ カバー オンシューズ オンサイレンサー 大型犬 小型犬 中型犬 革 シーザーミラン 150 メンドータ 犬 大型犬アウトレット cd マスク パーカー tシャツ ウイスキー"},
        "ct772": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > ブラジャー > その他", "y_ct": "2084053090","sex": "0","male": "","female": "","wowma_catid": "32070603","wowma_catname": "インナー・ルームウェア＞レディースインナー＞ブラ＞その他ブラ","qoo_catid": "300000029","qoo_catname": "下着・レッグウェア_ブラジャー_ブラジャー","s_keyword": "ショーツセット ノンワイヤー わき肉 背中 すっきり セット 福袋 小さく見せる 重力に負けない リボンブラ サルート 脇肉すっきり フルカップ iカップ gカップ b95 5枚セット 綿 レース 3枚セット 大きい すっきりトリンプ ゼロフィール 3l セール ゼロフィール2.0 4l ll ベーシック 天使のブラ プレミアム 恋するブラ 天使のブラセット 脇高 コットン f75 ショーツ e75 s1 364 フラワー tバック 可愛い 洗濯ネット 赤 アジャスター アンダーアツギ"},
        "ct773": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > 補正下着 > その他", "y_ct": "2084053156","sex": "0","male": "","female": "","wowma_catid": "32071101","wowma_catname": "インナー・ルームウェア＞レディースインナー＞補正下着＞その他補正下着","qoo_catid": "300000031","qoo_catname": "下着・レッグウェア_補正下着_補正下着・ガードル","s_keyword": "レディース ブラジャー お腹 ハイウエスト ボディスーツ ボディースーツ コルセット 矯正下着 キャミソール お腹引き締め ヒップアップ 姿勢矯正 ダイエット ガードル 上下セット 背中 わき肉 すっきり d75 セット マルコ ノンワイヤー 脇高 ブラジャー6xl 男性 お腹ぽっこり お腹人気 トイレ ウエストマイナス パッド 苦しくない ヒップ ベージュ ハード ボディシェイパー シームレス ボディスーツ胸開き ボディスーツセクシー 穴あき ニッパー ボディスーツトイレホール レディース穴あき セパレート レディース夏用 薄手 コルセットファスナー 矯正下着又空き"},
        "ct774": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > ストッキング > Mサイズ", "y_ct": "2084053100","sex": "0","male": "","female": "","wowma_catid": "34060307","wowma_catname": "キッズベビー・マタニティ＞マタニティ・ママ＞マタニティインナー＞ストッキング・タイツ・スパッツ","qoo_catid": "300000049","qoo_catname": "下着・レッグウェア_靴下・レッグウェア_ストッキング・タイツ","s_keyword": "暖かい 膝下 黒 ベージュ 着圧 肌色 ひざ下 風タイツ 裏起毛 大きい ll 透け感 靴下 1200デニール 温かい 伝線しにくい 暖 厚手 冬 ゆったり 80デニール 柄 3l 5l オープンクロッチ ガーター ガーターベルト 付き 白 ｌ 赤 ベビードール 網 光沢 福助 ロゼワイン 30デニール 満足 コーラルベージュ 極上 スルー 風裏起毛タイツ 韓国 おおきいサイズ 穴あき 股開き"},
        "ct779": {"ctname": "オークション > ファッション > レディースファッション > 水着 > その他", "y_ct": "2084051839","sex": "0","male": "","female": "","wowma_catid": "511301","wowma_catname": "レディースファッション＞水着＞その他水着","qoo_catid": "300002269","qoo_catname": "レディースファッション_水着・ラッシュガード_ビキニ","s_keyword": "レディース フィットネス 体型カバー レディース 競泳 セパレート 男性 ビキニ ワンピース タンキニ セット ラッシュガード 上下 練習用 インナー アリーナ スピード 50代 40代 50代大きい 60代 3l 体型カバーsale エレッセ スピードセパレート arena 半袖 フィラ セパレートミズノ ショート ボックス fina認証 ジム 上 男性用 穴あき アンダーショーツ アンダー 赤ちゃん インナーショーツ いんなーパンツ tバック インナーパンツ 上着 上だけ うえだけ 上に羽織る"},
        "ct780": {"ctname": "オークション > ファッション > レディースファッション > 水着 > セパレート > Mサイズ > 三角ビキニ", "y_ct": "2084211851","sex": "0","male": "","female": "","wowma_catid": "511303","wowma_catname": "レディースファッション＞水着＞ビキニ","qoo_catid": "300002269","qoo_catname": "レディースファッション_水着・ラッシュガード_ビキニ","s_keyword": "レディース フィットネス 体型カバー レディース 競泳 セパレート 男性 ビキニ ワンピース タンキニ セット ラッシュガード 上下 練習用 インナー アリーナ スピード 50代 40代 50代大きい 60代 3l 体型カバーsale エレッセ スピードセパレート arena 半袖 フィラ セパレートミズノ ショート ボックス fina認証 ジム 上 男性用 穴あき アンダーショーツ アンダー 赤ちゃん インナーショーツ いんなーパンツ tバック インナーパンツ 上着 上だけ うえだけ 上に羽織る"},
        "ct781": {"ctname": "オークション > ファッション > レディースファッション > 水着 > その他", "y_ct": "2084051839","sex": "0","male": "","female": "","wowma_catid": "511301","wowma_catname": "レディースファッション＞水着＞その他水着","qoo_catid": "300002269","qoo_catname": "レディースファッション_水着・ラッシュガード_ビキニ","s_keyword": "レディース フィットネス 体型カバー レディース 競泳 セパレート 男性 ビキニ ワンピース タンキニ セット ラッシュガード 上下 練習用 インナー アリーナ スピード 50代 40代 50代大きい 60代 3l 体型カバーsale エレッセ スピードセパレート arena 半袖 フィラ セパレートミズノ ショート ボックス fina認証 ジム 上 男性用 穴あき アンダーショーツ アンダー 赤ちゃん インナーショーツ いんなーパンツ tバック インナーパンツ 上着 上だけ うえだけ 上に羽織る"},
        "ct782": {"ctname": "オークション > ファッション > レディースファッション > 水着 > その他", "y_ct": "2084051839","sex": "0","male": "","female": "","wowma_catid": "511301","wowma_catname": "レディースファッション＞水着＞その他水着","qoo_catid": "300002269","qoo_catname": "レディースファッション_水着・ラッシュガード_ビキニ","s_keyword": "レディース フィットネス 体型カバー レディース 競泳 セパレート 男性 ビキニ ワンピース タンキニ セット ラッシュガード 上下 練習用 インナー アリーナ スピード 50代 40代 50代大きい 60代 3l 体型カバーsale エレッセ スピードセパレート arena 半袖 フィラ セパレートミズノ ショート ボックス fina認証 ジム 上 男性用 穴あき アンダーショーツ アンダー 赤ちゃん インナーショーツ いんなーパンツ tバック インナーパンツ 上着 上だけ うえだけ 上に羽織る"},
        "ct1038": {"ctname": "オークション > スポーツ、レジャー > スポーツ別 > サーフィン > ウエア > ラッシュガード > 女性用 > Mサイズ", "y_ct": "2084304030","sex": "0","male": "","female": "","wowma_catid": "40370705","wowma_catname": "スポーツ・アウトドア＞マリンスポーツ＞マリンウェア＞ラッシュガード","qoo_catid": "300003037","qoo_catname": "レディースファッション_水着・ラッシュガード_ラッシュガード","s_keyword": "ブーツ 冬 5mm マジック ハンガー グローブ レディース インナー 耳栓 ポンチョ バケツ ワックス ヘッドキャップ ライフ 1mm 2mm 3mm 1.5mm インナーパンツ 裏起毛 保温 インナーソックス インナーネック インナーショーツ 音が聞こえる 聞こえる docs 子供 キッズ タオル マイクロファイバー fcs 綿 防寒 ピンク コットン 大 四角 折りたたみ 蓋付き 30l l tools 38l 黒 秋冬 ワックスケース ワックスリムーバー リムーバー"},
        "ct775": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > 子ども服（男女兼用） > トップス > 長袖Tシャツ > 140（135～144cm）", "y_ct": "2084053319","sex": "0","male": "","female": "","wowma_catid": "34010810","wowma_catname": "キッズベビー・マタニティ＞キッズ＞子供服（トップス）＞ブラウス・シャツ","qoo_catid": "300002440","qoo_catname": "キッズ_男女兼用・その他の子供服_トップス","s_keyword": "男の子 女の子 冬 120 秋冬 収納 女の子90 アウター 140 ニットワンピ 160 ブルゾン 手袋 リュック 福袋 男の子秋冬 70 スウェット 男の子80 恐竜 冬ワンピース 冬150 130 110 100 ウィッグ バンダイ 95 90 150 秋冬80 秋冬セットアップ セット 収納ケース クラフト 本 ワンピース 韓国 子ども アクセサリーセット アクセサリー アイシャドウ アクセサリーボックス 編み物 遊び おもちゃ アンガーマネジメント"},
        "ct776": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > 子ども服（男女兼用） > ボトムス > パンツ、ズボン一般 > 140（135～144cm）", "y_ct": "2084053356","sex": "0","male": "","female": "","wowma_catid": "34011001","wowma_catname": "キッズベビー・マタニティ＞キッズ＞子供服（ボトムス）＞その他子供服（ボトムス）","qoo_catid": "300002441","qoo_catname": "キッズ_男女兼用・その他の子供服_ボトムス","s_keyword": "男の子 女の子 冬 120 秋冬 収納 女の子90 アウター 140 ニットワンピ 160 ブルゾン 手袋 リュック 福袋 男の子秋冬 70 スウェット 男の子80 恐竜 冬ワンピース 冬150 130 110 100 ウィッグ バンダイ 95 90 150 秋冬80 秋冬セットアップ セット 収納ケース クラフト 本 ワンピース 韓国 子ども アクセサリーセット アクセサリー アイシャドウ アクセサリーボックス 編み物 遊び おもちゃ アンガーマネジメント"},
        "ct1031": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > 子ども服（女の子用） > その他", "y_ct": "2084051664","sex": "0","male": "","female": "","wowma_catid": "34020802","wowma_catname": "キッズベビー・マタニティ＞ジュニア＞子供服（トップス）＞その他子供服（トップス）","qoo_catid": "320001059","qoo_catname": "キッズ_女の子ファッション_その他","s_keyword": "男の子 女の子 冬 120 秋冬 収納 女の子90 アウター 140 ニットワンピ 160 ブルゾン 手袋 リュック 福袋 男の子秋冬 70 スウェット 男の子80 恐竜 冬ワンピース 冬150 130 110 100 ウィッグ バンダイ 95 90 150 秋冬80 秋冬セットアップ セット 収納ケース クラフト 本 ワンピース 韓国 子ども アクセサリーセット アクセサリー アイシャドウ アクセサリーボックス 編み物 遊び おもちゃ アンガーマネジメント"},
        "ct777": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > 子ども服（男女兼用） > コート > コート一般 > 130（125～134cm）", "y_ct": "2084053283","sex": "0","male": "","female": "","wowma_catid": "34020502","wowma_catname": "キッズベビー・マタニティ＞ジュニア＞子供服（アウター）＞その他子供服（アウター）","qoo_catid": "300002442","qoo_catname": "キッズ_男女兼用・その他の子供服_アウター","s_keyword": "男の子 女の子 冬 120 秋冬 収納 女の子90 アウター 140 ニットワンピ 160 ブルゾン 手袋 リュック 福袋 男の子秋冬 70 スウェット 男の子80 恐竜 冬ワンピース 冬150 130 110 100 ウィッグ バンダイ 95 90 150 秋冬80 秋冬セットアップ セット 収納ケース クラフト 本 ワンピース 韓国 子ども アクセサリーセット アクセサリー アイシャドウ アクセサリーボックス 編み物 遊び おもちゃ アンガーマネジメント"},
        "ct778": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > 子ども服（男女兼用） > セット、まとめ売り", "y_ct": "2084313344","sex": "0","male": "","female": "","wowma_catid": "340101","wowma_catname": "キッズベビー・マタニティ＞キッズ＞その他キッズ","qoo_catid": "320001063","qoo_catname": "キッズ_男女兼用・その他の子供服_その他","s_keyword": "男の子 女の子 冬 120 秋冬 収納 女の子90 アウター 140 ニットワンピ 160 ブルゾン 手袋 リュック 福袋 男の子秋冬 70 スウェット 男の子80 恐竜 冬ワンピース 冬150 130 110 100 ウィッグ バンダイ 95 90 150 秋冬80 秋冬セットアップ セット 収納ケース クラフト 本 ワンピース 韓国 子ども アクセサリーセット アクセサリー アイシャドウ アクセサリーボックス 編み物 遊び おもちゃ アンガーマネジメント"},
        "ct1016": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > 子ども用ファッション小物 > その他", "y_ct": "2084006431","sex": "0","male": "","female": "","wowma_catid": "341001","wowma_catname": "キッズベビー・マタニティ＞子供用ファッション小物・雑貨＞その他子供用ファッション小物・雑貨","qoo_catid": "320001063","qoo_catname": "キッズ_男女兼用・その他の子供服_その他","s_keyword": "レディース ファッション アラフォー 秋冬 アウター アート アニメ アクセサリー 安全ピン アネモネ イラスト 本 イン ジャパン 色 イラストレーション 描き方 イラスト集 ウィッグ 売上枚数予測 腕時計 上着 エッセイ 柄 映画 絵 英語 英和 おもちゃ 女の子 男 大人 面白い 男の子 おしゃれ パーカー 韓国 カジュアル プルオーバー アルファベット ラウンドネック 絵画 革靴 環境 カレンダー 2022 プリント スタンドネック"},
        "ct1032": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > 子ども用ファッション小物 > その他", "y_ct": "2084006431","sex": "0","male": "","female": "","wowma_catid": "341001","wowma_catname": "キッズベビー・マタニティ＞子供用ファッション小物・雑貨＞その他子供用ファッション小物・雑貨","qoo_catid": "320001063","qoo_catname": "キッズ_男女兼用・その他の子供服_その他","s_keyword": "レディース ファッション アラフォー 秋冬 アウター アート アニメ アクセサリー 安全ピン アネモネ イラスト 本 イン ジャパン 色 イラストレーション 描き方 イラスト集 ウィッグ 売上枚数予測 腕時計 上着 エッセイ 柄 映画 絵 英語 英和 おもちゃ 女の子 男 大人 面白い 男の子 おしゃれ パーカー 韓国 カジュアル プルオーバー アルファベット ラウンドネック 絵画 革靴 環境 カレンダー 2022 プリント スタンドネック"},
        "ct784": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > 子ども服（男の子用） > その他", "y_ct": "2084051663","sex": "0","male": "","female": "","wowma_catid": "340101","wowma_catname": "キッズベビー・マタニティ＞キッズ＞その他キッズ","qoo_catid": "320001063","qoo_catname": "キッズ_男女兼用・その他の子供服_その他","s_keyword": "男の子 女の子 冬 120 秋冬 収納 女の子90 アウター 140 ニットワンピ 160 ブルゾン 手袋 リュック 福袋 男の子秋冬 70 スウェット 男の子80 恐竜 冬ワンピース 冬150 130 110 100 ウィッグ バンダイ 95 90 150 秋冬80 秋冬セットアップ セット 収納ケース クラフト 本 ワンピース 韓国 子ども アクセサリーセット アクセサリー アイシャドウ アクセサリーボックス 編み物 遊び おもちゃ アンガーマネジメント"},
        "ct785": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > ベビー服 > ボトムス > ロンパース > 80（75～84cm）", "y_ct": "2084052490","sex": "0","male": "","female": "","wowma_catid": "34051309","wowma_catname": "キッズベビー・マタニティ＞ベビー＞下着・肌着・パジャマ＞ロンパース","qoo_catid": "320001578","qoo_catname": "ベビー・マタニティ_ベビー服_ロンパース","s_keyword": "女の子 男の子 80 秋冬 70 next サンタ 60 90 冬 ロンパース セットアップ アウター トップス セパレート トレーナー ブランド 秋冬 カバーオール 長袖 日本製 春 コスチューム ワンピース 上下 セット 上着 キャラクター レギンスブラウン ツーウェイオール フォーマル コート 中綿 足付き 肌着 サンタクロース 50 新生児 帽子 アニメ 赤色 足付きロンパース アウター90 足つき 一歳 一升餅 犬"},
        "ct786": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > ベビー服 > トップス > Tシャツ > 長袖 > 男女兼用 > 90（85～94cm）", "y_ct": "2084053373","sex": "0","male": "","female": "","wowma_catid": "34050901","wowma_catname": "キッズベビー・マタニティ＞ベビー＞ベビー服＞Tシャツ","qoo_catid": "300000392","qoo_catname": "ベビー・マタニティ_ベビー服_トップス","s_keyword": "女の子 男の子 80 秋冬 70 next サンタ 60 90 冬 ロンパース セットアップ アウター トップス セパレート トレーナー ブランド 秋冬 カバーオール 長袖 日本製 春 コスチューム ワンピース 上下 セット 上着 キャラクター レギンスブラウン ツーウェイオール フォーマル コート 中綿 足付き 肌着 サンタクロース 50 新生児 帽子 アニメ 赤色 足付きロンパース アウター90 足つき 一歳 一升餅 犬"},
        "ct787": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > ベビー服 > ボトムス > その他", "y_ct": "2084042011","sex": "0","male": "","female": "","wowma_catid": "34011001","wowma_catname": "キッズベビー・マタニティ＞キッズ＞子供服（ボトムス）＞その他子供服（ボトムス）","qoo_catid": "300000394","qoo_catname": "ベビー・マタニティ_ベビー服_ボトムス","s_keyword": "女の子 男の子 80 秋冬 70 next サンタ 60 90 冬 ロンパース セットアップ アウター トップス セパレート トレーナー ブランド 秋冬 カバーオール 長袖 日本製 春 コスチューム ワンピース 上下 セット 上着 キャラクター レギンスブラウン ツーウェイオール フォーマル コート 中綿 足付き 肌着 サンタクロース 50 新生児 帽子 アニメ 赤色 足付きロンパース アウター90 足つき 一歳 一升餅 犬"},
        "ct788": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > ベビー服 > コート、ジャンパー > コート > 男女兼用 > 90（85～94cm）", "y_ct": "2084053362","sex": "0","male": "","female": "","wowma_catid": "34010501","wowma_catname": "キッズベビー・マタニティ＞キッズ＞子供服（アウター）＞その他ブルゾン・ジャンパー","qoo_catid": "300000393","qoo_catname": "ベビー・マタニティ_ベビー服_アウター","s_keyword": "女の子 男の子 80 秋冬 70 next サンタ 60 90 冬 ロンパース セットアップ アウター トップス セパレート トレーナー ブランド 秋冬 カバーオール 長袖 日本製 春 コスチューム ワンピース 上下 セット 上着 キャラクター レギンスブラウン ツーウェイオール フォーマル コート 中綿 足付き 肌着 サンタクロース 50 新生児 帽子 アニメ 赤色 足付きロンパース アウター90 足つき 一歳 一升餅 犬"},
        "ct789": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > ベビー用ファッション小物 > スタイ、よだれかけ", "y_ct": "2084007257","sex": "0","male": "","female": "","wowma_catid": "34050303","wowma_catname": "キッズベビー・マタニティ＞ベビー＞スタイ・お食事エプロン＞スタイ","qoo_catid": "320000480","qoo_catname": "ベビー・マタニティ_授乳・食事_スタイ","s_keyword": "レディース ファッション アラフォー 秋冬 アウター アート アニメ アクセサリー 安全ピン アネモネ イラスト 本 イン ジャパン 色 イラストレーション 描き方 イラスト集 ウィッグ 売上枚数予測 腕時計 上着 エッセイ 柄 映画 絵 英語 英和 おもちゃ 女の子 男 大人 面白い 男の子 おしゃれ パーカー 韓国 カジュアル プルオーバー アルファベット ラウンドネック 絵画 革靴 環境 カレンダー 2022 プリント スタンドネック"},
        "ct790": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > ベビー服 > 水着 > 女の子用 > 90（85～94cm）", "y_ct": "2084051882","sex": "0","male": "","female": "","wowma_catid": "34051008","wowma_catname": "キッズベビー・マタニティ＞ベビー＞ベビー用品・小物＞水着","qoo_catid": "300000398","qoo_catname": "ベビー・マタニティ_ベビー服_水着","s_keyword": "女の子 男の子 80 秋冬 70 next サンタ 60 90 冬 ロンパース セットアップ アウター トップス セパレート トレーナー ブランド 秋冬 カバーオール 長袖 日本製 春 コスチューム ワンピース 上下 セット 上着 キャラクター レギンスブラウン ツーウェイオール フォーマル コート 中綿 足付き 肌着 サンタクロース 50 新生児 帽子 アニメ 赤色 足付きロンパース アウター90 足つき 一歳 一升餅 犬"},
        "ct791": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > ベビー用ファッション小物 > その他", "y_ct": "2084007258","sex": "0","male": "","female": "","wowma_catid": "34051003","wowma_catname": "キッズベビー・マタニティ＞ベビー＞ベビー用品・小物＞その他ベビー用品・小物","qoo_catid": "300000450","qoo_catname": "キッズ_雑貨・小物_その他","s_keyword": "レディース ファッション アラフォー 秋冬 アウター アート アニメ アクセサリー 安全ピン アネモネ イラスト 本 イン ジャパン 色 イラストレーション 描き方 イラスト集 ウィッグ 売上枚数予測 腕時計 上着 エッセイ 柄 映画 絵 英語 英和 おもちゃ 女の子 男 大人 面白い 男の子 おしゃれ パーカー 韓国 カジュアル プルオーバー アルファベット ラウンドネック 絵画 革靴 環境 カレンダー 2022 プリント スタンドネック"},
        "ct792": {"ctname": "オークション > ファッション > レディースファッション > マタニティウエア > その他", "y_ct": "2084006313","sex": "0","male": "","female": "","wowma_catid": "34060402","wowma_catname": "キッズベビー・マタニティ＞マタニティ・ママ＞マタニティウエア＞その他マタニティウエア","qoo_catid": "300000379","qoo_catname": "ベビー・マタニティ_マタニティ_マタニティウェア","s_keyword": "オートバイ グッズ 便利グッズ オートバイ防寒グッズ"},
        "ct795": {"ctname": "オークション > コミック、アニメグッズ > コスプレ衣装 > その他", "y_ct": "2084208673","sex": "0","male": "","female": "","wowma_catid": "3409","wowma_catname": "キッズベビー・マタニティ＞子供用コスチューム","qoo_catid": "300000701","qoo_catname": "ホビー・コスプレ_パーティー・イベント用品_コスプレ・変装・仮装","s_keyword": "女性 アニメ サンタ 可愛い ナース スカート ol キッズ 子供 子ども 子供用 赤 456 マスク 連体服 こども サキュバス アニメキャラ レディース ボーカロイド vocaloid 初音ミク cosplay衣装 コスチューム 仮装 変装 文化祭 イベント 人気のトナカイ ランキング ウエディングドレス セーラー服 ウィッグ付き ウマ娘 アイドル アリス マーガトロイド アイカツ アズールレーン アイドルマスター あんスタ 陰陽師 グラスワンダー 全セット うみねこのなく頃に 右代宮 絵羽"},
        "ct1028": {"ctname": "オークション > コミック、アニメグッズ > コスプレ衣装 > 男性用", "y_ct": "2084241340","sex": "0","male": "","female": "","wowma_catid": "5004","wowma_catname": "メンズファッション＞コスチューム","qoo_catid": "300000701","qoo_catname": "ホビー・コスプレ_パーティー・イベント用品_コスプレ・変装・仮装","s_keyword": "女性 アニメ サンタ 可愛い ナース スカート ol キッズ 子供 子ども 子供用 赤 456 マスク 連体服 こども サキュバス アニメキャラ レディース ボーカロイド vocaloid 初音ミク cosplay衣装 コスチューム 仮装 変装 文化祭 イベント 人気のトナカイ ランキング ウエディングドレス セーラー服 ウィッグ付き ウマ娘 アイドル アリス マーガトロイド アイカツ アズールレーン アイドルマスター あんスタ 陰陽師 グラスワンダー 全セット うみねこのなく頃に 右代宮 絵羽"},
        "ct1029": {"ctname": "オークション > コミック、アニメグッズ > コスプレ衣装 > その他", "y_ct": "2084208673","sex": "0","male": "","female": "","wowma_catid": "3409","wowma_catname": "キッズベビー・マタニティ＞子供用コスチューム","qoo_catid": "300000701","qoo_catname": "ホビー・コスプレ_パーティー・イベント用品_コスプレ・変装・仮装","s_keyword": "女性 アニメ サンタ 可愛い ナース スカート ol キッズ 子供 子ども 子供用 赤 456 マスク 連体服 こども サキュバス アニメキャラ レディース ボーカロイド vocaloid 初音ミク cosplay衣装 コスチューム 仮装 変装 文化祭 イベント 人気のトナカイ ランキング ウエディングドレス セーラー服 ウィッグ付き ウマ娘 アイドル アリス マーガトロイド アイカツ アズールレーン アイドルマスター あんスタ 陰陽師 グラスワンダー 全セット うみねこのなく頃に 右代宮 絵羽"},
        "ct1030": {"ctname": "オークション > コミック、アニメグッズ > コスプレ衣装 > その他", "y_ct": "2084208673","sex": "0","male": "","female": "","wowma_catid": "3409","wowma_catname": "キッズベビー・マタニティ＞子供用コスチューム","qoo_catid": "300000701","qoo_catname": "ホビー・コスプレ_パーティー・イベント用品_コスプレ・変装・仮装","s_keyword": "女性 アニメ サンタ 可愛い ナース スカート ol キッズ 子供 子ども 子供用 赤 456 マスク 連体服 こども サキュバス アニメキャラ レディース ボーカロイド vocaloid 初音ミク cosplay衣装 コスチューム 仮装 変装 文化祭 イベント 人気のトナカイ ランキング ウエディングドレス セーラー服 ウィッグ付き ウマ娘 アイドル アリス マーガトロイド アイカツ アズールレーン アイドルマスター あんスタ 陰陽師 グラスワンダー 全セット うみねこのなく頃に 右代宮 絵羽"},
        "ct796": {"ctname": "オークション > コミック、アニメグッズ > コスプレ衣装 > コミック、アニメ、ゲームキャラクター > コスプレ衣装", "y_ct": "2084311485","sex": "0","male": "","female": "","wowma_catid": "3409","wowma_catname": "キッズベビー・マタニティ＞子供用コスチューム","qoo_catid": "300000701","qoo_catname": "ホビー・コスプレ_パーティー・イベント用品_コスプレ・変装・仮装","s_keyword": "女性 アニメ サンタ 可愛い ナース スカート ol キッズ 子供 子ども 子供用 赤 456 マスク 連体服 こども サキュバス アニメキャラ レディース ボーカロイド vocaloid 初音ミク cosplay衣装 コスチューム 仮装 変装 文化祭 イベント 人気のトナカイ ランキング ウエディングドレス セーラー服 ウィッグ付き ウマ娘 アイドル アリス マーガトロイド アイカツ アズールレーン アイドルマスター あんスタ 陰陽師 グラスワンダー 全セット うみねこのなく頃に 右代宮 絵羽"},
        "ct797": {"ctname": "オークション > コミック、アニメグッズ > コスプレ衣装 > コミック、アニメ、ゲームキャラクター > 衣装一式", "y_ct": "2084311486","sex": "0","male": "","female": "","wowma_catid": "290805","wowma_catname": "おもちゃ・趣味＞コレクション＞キャラクターグッズ","qoo_catid": "300000700","qoo_catname": "ホビー・コスプレ_パーティー・イベント用品_コスチューム一式","s_keyword": "女性 アニメ サンタ 可愛い ナース スカート ol キッズ 子供 子ども 子供用 赤 456 マスク 連体服 こども サキュバス アニメキャラ レディース ボーカロイド vocaloid 初音ミク cosplay衣装 コスチューム 仮装 変装 文化祭 イベント 人気のトナカイ ランキング ウエディングドレス セーラー服 ウィッグ付き ウマ娘 アイドル アリス マーガトロイド アイカツ アズールレーン アイドルマスター あんスタ 陰陽師 グラスワンダー 全セット うみねこのなく頃に 右代宮 絵羽"},
        "ct798": {"ctname": "オークション > コミック、アニメグッズ > コスプレ衣装 > コミック、アニメ、ゲームキャラクター > 衣装一式", "y_ct": "2084311486","sex": "0","male": "","female": "","wowma_catid": "290805","wowma_catname": "おもちゃ・趣味＞コレクション＞キャラクターグッズ","qoo_catid": "300000700","qoo_catname": "ホビー・コスプレ_パーティー・イベント用品_コスチューム一式","s_keyword": "女性 アニメ サンタ 可愛い ナース スカート ol キッズ 子供 子ども 子供用 赤 456 マスク 連体服 こども サキュバス アニメキャラ レディース ボーカロイド vocaloid 初音ミク cosplay衣装 コスチューム 仮装 変装 文化祭 イベント 人気のトナカイ ランキング ウエディングドレス セーラー服 ウィッグ付き ウマ娘 アイドル アリス マーガトロイド アイカツ アズールレーン アイドルマスター あんスタ 陰陽師 グラスワンダー 全セット うみねこのなく頃に 右代宮 絵羽"},
        "ct799": {"ctname": "オークション > コミック、アニメグッズ > コスプレ衣装 > コミック、アニメ、ゲームキャラクター > アクセサリー、小物", "y_ct": "2084311489","sex": "0","male": "","female": "","wowma_catid": "290805","wowma_catname": "おもちゃ・趣味＞コレクション＞キャラクターグッズ","qoo_catid": "300000701","qoo_catname": "ホビー・コスプレ_パーティー・イベント用品_コスプレ・変装・仮装","s_keyword": "女性 アニメ サンタ 可愛い ナース スカート ol キッズ 子供 子ども 子供用 赤 456 マスク 連体服 こども サキュバス アニメキャラ レディース ボーカロイド vocaloid 初音ミク cosplay衣装 コスチューム 仮装 変装 文化祭 イベント 人気のトナカイ ランキング ウエディングドレス セーラー服 ウィッグ付き ウマ娘 アイドル アリス マーガトロイド アイカツ アズールレーン アイドルマスター あんスタ 陰陽師 グラスワンダー 全セット うみねこのなく頃に 右代宮 絵羽"},
        "ct1000": {"ctname": "オークション > コミック、アニメグッズ > コスプレ衣装 > コミック、アニメ、ゲームキャラクター > インナー", "y_ct": "2084311488","sex": "0","male": "","female": "","wowma_catid": "290805","wowma_catname": "おもちゃ・趣味＞コレクション＞キャラクターグッズ","qoo_catid": "300000702","qoo_catname": "ホビー・コスプレ_パーティー・イベント用品_その他","s_keyword": "女性 アニメ サンタ 可愛い ナース スカート ol キッズ 子供 子ども 子供用 赤 456 マスク 連体服 こども サキュバス アニメキャラ レディース ボーカロイド vocaloid 初音ミク cosplay衣装 コスチューム 仮装 変装 文化祭 イベント 人気のトナカイ ランキング ウエディングドレス セーラー服 ウィッグ付き ウマ娘 アイドル アリス マーガトロイド アイカツ アズールレーン アイドルマスター あんスタ 陰陽師 グラスワンダー 全セット うみねこのなく頃に 右代宮 絵羽"},
        "ct800": {"ctname": "オークション > コミック、アニメグッズ > コスプレ衣装 > その他", "y_ct": "2084208673","sex": "0","male": "","female": "","wowma_catid": "290805","wowma_catname": "おもちゃ・趣味＞コレクション＞キャラクターグッズ","qoo_catid": "300000702","qoo_catname": "ホビー・コスプレ_パーティー・イベント用品_その他","s_keyword": "女性 アニメ サンタ 可愛い ナース スカート ol キッズ 子供 子ども 子供用 赤 456 マスク 連体服 こども サキュバス アニメキャラ レディース ボーカロイド vocaloid 初音ミク cosplay衣装 コスチューム 仮装 変装 文化祭 イベント 人気のトナカイ ランキング ウエディングドレス セーラー服 ウィッグ付き ウマ娘 アイドル アリス マーガトロイド アイカツ アズールレーン アイドルマスター あんスタ 陰陽師 グラスワンダー 全セット うみねこのなく頃に 右代宮 絵羽"},
        "ct801": {"ctname": "オークション > ファッション > ファッション小物 > 帽子 > 男性用 > その他", "y_ct": "2084006684","sex": "0","male": "","female": "","wowma_catid": "450701","wowma_catname": "バッグ・財布・ファッション小物＞帽子＞その他帽子","qoo_catid": "300002177","qoo_catname": "バッグ・雑貨_帽子_その他","s_keyword": "メンズ 冬 レディース 収納 かけ 掛け おしゃれ ハンチング ニット キャップ つばつき 耳当て 大きい 年配 フェルト ブランド 秋冬 キャスケット 65cm 冬用 深め アウトドア メッシュ ゴルフ 吊り下げ 収納ボックス ハンガー 壁掛け ラック 壁 大容量 スタンド 耳あて 耳 ファー オシャレ つば広 赤 ウール ドア 壁傷つけない フック かけるやつ かける 傷つけない ミニ キッズ 女の子 男の子"},
        "ct826": {"ctname": "オークション > ファッション > ファッション小物 > 帽子 > 男性用 > その他", "y_ct": "2084006684","sex": "0","male": "","female": "","wowma_catid": "450701","wowma_catname": "バッグ・財布・ファッション小物＞帽子＞その他帽子","qoo_catid": "300002177","qoo_catname": "バッグ・雑貨_帽子_その他","s_keyword": "メンズ 冬 レディース 収納 かけ 掛け おしゃれ ハンチング ニット キャップ つばつき 耳当て 大きい 年配 フェルト ブランド 秋冬 キャスケット 65cm 冬用 深め アウトドア メッシュ ゴルフ 吊り下げ 収納ボックス ハンガー 壁掛け ラック 壁 大容量 スタンド 耳あて 耳 ファー オシャレ つば広 赤 ウール ドア 壁傷つけない フック かけるやつ かける 傷つけない ミニ キッズ 女の子 男の子"},
        "ct828": {"ctname": "オークション > スポーツ、レジャー > スポーツ別 > ゴルフ > ウエア（男性用） > キャップ > その他", "y_ct": "2084208718","sex": "0","male": "","female": "","wowma_catid": "40191403","wowma_catname": "スポーツ・アウトドア＞ゴルフ＞メンズゴルフウェア＞ゴルフキャップ","qoo_catid": "300002172","qoo_catname": "バッグ・雑貨_帽子_キャップ","s_keyword": "メンズ 冬 レディース 収納 かけ 掛け おしゃれ ハンチング ニット キャップ つばつき 耳当て 大きい 年配 フェルト ブランド 秋冬 キャスケット 65cm 冬用 深め アウトドア メッシュ ゴルフ 吊り下げ 収納ボックス ハンガー 壁掛け ラック 壁 大容量 スタンド 耳あて 耳 ファー オシャレ つば広 赤 ウール ドア 壁傷つけない フック かけるやつ かける 傷つけない ミニ キッズ 女の子 男の子"},
        "ct829": {"ctname": "オークション > スポーツ、レジャー > スポーツ別 > ゴルフ > ウエア（男性用） > ニット帽", "y_ct": "2084262354","sex": "0","male": "","female": "","wowma_catid": "40191403","wowma_catname": "スポーツ・アウトドア＞ゴルフ＞メンズゴルフウェア＞ゴルフキャップ","qoo_catid": "300002173","qoo_catname": "バッグ・雑貨_帽子_ニット帽","s_keyword": "メンズ 冬 レディース 収納 かけ 掛け おしゃれ ハンチング ニット キャップ つばつき 耳当て 大きい 年配 フェルト ブランド 秋冬 キャスケット 65cm 冬用 深め アウトドア メッシュ ゴルフ 吊り下げ 収納ボックス ハンガー 壁掛け ラック 壁 大容量 スタンド 耳あて 耳 ファー オシャレ つば広 赤 ウール ドア 壁傷つけない フック かけるやつ かける 傷つけない ミニ キッズ 女の子 男の子"},
        "ct1026": {"ctname": "オークション > ファッション > ファッション小物 > 帽子 > 男性用 > その他", "y_ct": "2084006684","sex": "0","male": "","female": "","wowma_catid": "450701","wowma_catname": "バッグ・財布・ファッション小物＞帽子＞その他帽子","qoo_catid": "300002177","qoo_catname": "バッグ・雑貨_帽子_その他","s_keyword": "メンズ 冬 レディース 収納 かけ 掛け おしゃれ ハンチング ニット キャップ つばつき 耳当て 大きい 年配 フェルト ブランド 秋冬 キャスケット 65cm 冬用 深め アウトドア メッシュ ゴルフ 吊り下げ 収納ボックス ハンガー 壁掛け ラック 壁 大容量 スタンド 耳あて 耳 ファー オシャレ つば広 赤 ウール ドア 壁傷つけない フック かけるやつ かける 傷つけない ミニ キッズ 女の子 男の子"},
        "ct830": {"ctname": "オークション > ファッション > ファッション小物 > 帽子 > 女性用 > ワッチキャップ、ニットキャップ", "y_ct": "2084006693","sex": "0","male": "","female": "","wowma_catid": "450711","wowma_catname": "バッグ・財布・ファッション小物＞帽子＞ニット帽","qoo_catid": "300002172","qoo_catname": "バッグ・雑貨_帽子_キャップ","s_keyword": "メンズ 冬 レディース 収納 かけ 掛け おしゃれ ハンチング ニット キャップ つばつき 耳当て 大きい 年配 フェルト ブランド 秋冬 キャスケット 65cm 冬用 深め アウトドア メッシュ ゴルフ 吊り下げ 収納ボックス ハンガー 壁掛け ラック 壁 大容量 スタンド 耳あて 耳 ファー オシャレ つば広 赤 ウール ドア 壁傷つけない フック かけるやつ かける 傷つけない ミニ キッズ 女の子 男の子"},
        "ct831": {"ctname": "オークション > ファッション > ファッション小物 > 帽子 > 女性用 > ワッチキャップ、ニットキャップ", "y_ct": "2084006693","sex": "0","male": "","female": "","wowma_catid": "450711","wowma_catname": "バッグ・財布・ファッション小物＞帽子＞ニット帽","qoo_catid": "300002172","qoo_catname": "バッグ・雑貨_帽子_キャップ","s_keyword": "冬 レディース 収納 かけ 掛け おしゃれ ハンチング ニット キャップ つばつき 耳当て 大きい 年配 フェルト ブランド 秋冬 キャスケット 65cm 冬用 深め アウトドア メッシュ ゴルフ 吊り下げ 収納ボックス ハンガー 壁掛け ラック 壁 大容量 スタンド 耳あて 耳 ファー オシャレ つば広 赤 ウール ドア 壁傷つけない フック かけるやつ かける 傷つけない ミニ キッズ 女の子 男の子"},
        "ct832": {"ctname": "オークション > ファッション > ファッション小物 > 帽子 > 女性用 > ワッチキャップ、ニットキャップ", "y_ct": "2084006693","sex": "0","male": "","female": "","wowma_catid": "450711","wowma_catname": "バッグ・財布・ファッション小物＞帽子＞ニット帽","qoo_catid": "300002172","qoo_catname": "バッグ・雑貨_帽子_キャップ","s_keyword": "冬 レディース 収納 かけ 掛け おしゃれ ハンチング ニット キャップ つばつき 耳当て 大きい 年配 フェルト ブランド 秋冬 キャスケット 65cm 冬用 深め アウトドア メッシュ ゴルフ 吊り下げ 収納ボックス ハンガー 壁掛け ラック 壁 大容量 スタンド 耳あて 耳 ファー オシャレ つば広 赤 ウール ドア 壁傷つけない フック かけるやつ かける 傷つけない ミニ キッズ 女の子 男の子"},
        "ct833": {"ctname": "オークション > ファッション > ファッション小物 > 帽子 > 女性用 > テンガロンハット、ウエスタンハット", "y_ct": "2084006692","sex": "0","male": "","female": "","wowma_catid": "450701","wowma_catname": "バッグ・財布・ファッション小物＞帽子＞その他帽子","qoo_catid": "300002174","qoo_catname": "バッグ・雑貨_帽子_ハット","s_keyword": "冬 レディース 収納 かけ 掛け おしゃれ ハンチング ニット キャップ つばつき 耳当て 大きい 年配 フェルト ブランド 秋冬 キャスケット 65cm 冬用 深め アウトドア メッシュ ゴルフ 吊り下げ 収納ボックス ハンガー 壁掛け ラック 壁 大容量 スタンド 耳あて 耳 ファー オシャレ つば広 赤 ウール ドア 壁傷つけない フック かけるやつ かける 傷つけない ミニ キッズ 女の子 男の子"},
        "ct834": {"ctname": "オークション > ファッション > ファッション小物 > 帽子 > 女性用 > 麦わら帽子", "y_ct": "2084006695","sex": "0","male": "","female": "","wowma_catid": "450701","wowma_catname": "バッグ・財布・ファッション小物＞帽子＞その他帽子","qoo_catid": "300002177","qoo_catname": "バッグ・雑貨_帽子_その他","s_keyword": "冬 レディース 収納 かけ 掛け おしゃれ ハンチング ニット キャップ つばつき 耳当て 大きい 年配 フェルト ブランド 秋冬 キャスケット 65cm 冬用 深め アウトドア メッシュ ゴルフ 吊り下げ 収納ボックス ハンガー 壁掛け ラック 壁 大容量 スタンド 耳あて 耳 ファー オシャレ つば広 赤 ウール ドア 壁傷つけない フック かけるやつ かける 傷つけない ミニ キッズ 女の子 男の子"},
        "ct1024": {"ctname": "オークション > ファッション > ファッション小物 > 帽子 > 女性用 > キャスケット", "y_ct": "2084243504","sex": "0","male": "","female": "","wowma_catid": "450701","wowma_catname": "バッグ・財布・ファッション小物＞帽子＞その他帽子","qoo_catid": "300002175","qoo_catname": "バッグ・雑貨_帽子_ハンチング・キャスケット","s_keyword": "冬 レディース 収納 かけ 掛け おしゃれ ハンチング ニット キャップ つばつき 耳当て 大きい 年配 フェルト ブランド 秋冬 キャスケット 65cm 冬用 深め アウトドア メッシュ ゴルフ 吊り下げ 収納ボックス ハンガー 壁掛け ラック 壁 大容量 スタンド 耳あて 耳 ファー オシャレ つば広 赤 ウール ドア 壁傷つけない フック かけるやつ かける 傷つけない ミニ キッズ 女の子 男の子"},
        "ct1025": {"ctname": "オークション > ファッション > ファッション小物 > 帽子 > 女性用 > ベレー帽", "y_ct": "2084006694","sex": "0","male": "","female": "","wowma_catid": "450713","wowma_catname": "バッグ・財布・ファッション小物＞帽子＞ベレー帽","qoo_catid": "300003091","qoo_catname": "バッグ・雑貨_帽子_ベレー帽","s_keyword": "冬 レディース 収納 かけ 掛け おしゃれ ハンチング ニット キャップ つばつき 耳当て 大きい 年配 フェルト ブランド 秋冬 キャスケット 65cm 冬用 深め アウトドア メッシュ ゴルフ 吊り下げ 収納ボックス ハンガー 壁掛け ラック 壁 大容量 スタンド 耳あて 耳 ファー オシャレ つば広 赤 ウール ドア 壁傷つけない フック かけるやつ かける 傷つけない ミニ キッズ 女の子 男の子"},
        "ct1154": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > 子ども用ファッション小物 > 帽子", "y_ct": "2084006429","sex": "0","male": "","female": "","wowma_catid": "34011101","wowma_catname": "キッズベビー・マタニティ＞キッズ＞帽子（キッズ）＞その他帽子（キッズ）","qoo_catid": "320001587","qoo_catname": "ベビー・マタニティ_ベビー服_ベビー帽子","s_keyword": "レディース ファッション アラフォー 秋冬 アウター アート アニメ アクセサリー 安全ピン アネモネ イラスト 本 イン ジャパン 色 イラストレーション 描き方 イラスト集 ウィッグ 売上枚数予測 腕時計 上着 エッセイ 柄 映画 絵 英語 英和 おもちゃ 女の子 男 大人 面白い 男の子 おしゃれ パーカー 韓国 カジュアル プルオーバー アルファベット ラウンドネック 絵画 革靴 環境 カレンダー 2022 プリント スタンドネック"},
        "ct1050": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ウイッグ > その他", "y_ct": "2084062532","sex": "0","male": "","female": "","wowma_catid": "301602","wowma_catname": "アクセサリー・ジュエリー＞ヘアアクセサリー＞その他ヘアアクセサリー","qoo_catid": "300002181","qoo_catname": "バッグ・雑貨_ウィッグ・つけ毛_フルウィッグ","s_keyword": "大人 子供 女の子 結婚式 リボン お呼ばれ パール セット キッズ ピン こども 子ども サンタ 光る クリップ おしゃれ バレッタ キラキラ ギフト バナナクリップ 発表会 花 可愛い カチューシャ プレゼント 小学生 3才 赤 シルバー ゴールド 和装 大きい 黒 ベロア 白 青 ワイヤー パールゴム 幼児 赤ちゃん アクリル アップ アレンジ アンティーク 編み込み 入れ物 ウェディング 宇宙 うさぎ"},
        "ct1051": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ウイッグ > ショート", "y_ct": "2084062531","sex": "0","male": "","female": "","wowma_catid": "470902","wowma_catname": "ビューティ・コスメ＞ヘアケア・スタイリング＞ウィッグ・かつら","qoo_catid": "300003088","qoo_catname": "バッグ・雑貨_ウィッグ・つけ毛_ハーフウィッグ","s_keyword": "大人 子供 女の子 結婚式 リボン お呼ばれ パール セット キッズ ピン こども 子ども サンタ 光る クリップ おしゃれ バレッタ キラキラ ギフト バナナクリップ 発表会 花 可愛い カチューシャ プレゼント 小学生 3才 赤 シルバー ゴールド 和装 大きい 黒 ベロア 白 青 ワイヤー パールゴム 幼児 赤ちゃん アクリル アップ アレンジ アンティーク 編み込み 入れ物 ウェディング 宇宙 うさぎ"},
        "ct1052": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ウイッグ > ロング", "y_ct": "2084062528","sex": "0","male": "","female": "","wowma_catid": "470902","wowma_catname": "ビューティ・コスメ＞ヘアケア・スタイリング＞ウィッグ・かつら","qoo_catid": "300002181","qoo_catname": "バッグ・雑貨_ウィッグ・つけ毛_フルウィッグ","s_keyword": "大人 子供 女の子 結婚式 リボン お呼ばれ パール セット キッズ ピン こども 子ども サンタ 光る クリップ おしゃれ バレッタ キラキラ ギフト バナナクリップ 発表会 花 可愛い カチューシャ プレゼント 小学生 3才 赤 シルバー ゴールド 和装 大きい 黒 ベロア 白 青 ワイヤー パールゴム 幼児 赤ちゃん アクリル アップ アレンジ アンティーク 編み込み 入れ物 ウェディング 宇宙 うさぎ"},
        "ct1053": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ウイッグ > その他", "y_ct": "2084062532","sex": "0","male": "","female": "","wowma_catid": "301602","wowma_catname": "アクセサリー・ジュエリー＞ヘアアクセサリー＞その他ヘアアクセサリー","qoo_catid": "300003088","qoo_catname": "バッグ・雑貨_ウィッグ・つけ毛_ハーフウィッグ","s_keyword": "大人 子供 女の子 結婚式 リボン お呼ばれ パール セット キッズ ピン こども 子ども サンタ 光る クリップ おしゃれ バレッタ キラキラ ギフト バナナクリップ 発表会 花 可愛い カチューシャ プレゼント 小学生 3才 赤 シルバー ゴールド 和装 大きい 黒 ベロア 白 青 ワイヤー パールゴム 幼児 赤ちゃん アクリル アップ アレンジ アンティーク 編み込み 入れ物 ウェディング 宇宙 うさぎ"},
        "ct1054": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ウイッグ > その他", "y_ct": "2084062532","sex": "0","male": "","female": "","wowma_catid": "301602","wowma_catname": "アクセサリー・ジュエリー＞ヘアアクセサリー＞その他ヘアアクセサリー","qoo_catid": "300003088","qoo_catname": "バッグ・雑貨_ウィッグ・つけ毛_ハーフウィッグ","s_keyword": "大人 子供 女の子 結婚式 リボン お呼ばれ パール セット キッズ ピン こども 子ども サンタ 光る クリップ おしゃれ バレッタ キラキラ ギフト バナナクリップ 発表会 花 可愛い カチューシャ プレゼント 小学生 3才 赤 シルバー ゴールド 和装 大きい 黒 ベロア 白 青 ワイヤー パールゴム 幼児 赤ちゃん アクリル アップ アレンジ アンティーク 編み込み 入れ物 ウェディング 宇宙 うさぎ"},
        "ct1017": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > その他", "y_ct": "2084005387","sex": "0","male": "","female": "","wowma_catid": "301602","wowma_catname": "アクセサリー・ジュエリー＞ヘアアクセサリー＞その他ヘアアクセサリー","qoo_catid": "300000127","qoo_catname": "バッグ・雑貨_ヘアアクセサリー_その他","s_keyword": "大人 子供 女の子 結婚式 リボン お呼ばれ パール セット キッズ ピン こども 子ども サンタ 光る クリップ おしゃれ バレッタ キラキラ ギフト バナナクリップ 発表会 花 可愛い カチューシャ プレゼント 小学生 3才 赤 シルバー ゴールド 和装 大きい 黒 ベロア 白 青 ワイヤー パールゴム 幼児 赤ちゃん アクリル アップ アレンジ アンティーク 編み込み 入れ物 ウェディング 宇宙 うさぎ"},
        "ct1018": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ヘアゴム、シュシュ", "y_ct": "2084019052","sex": "0","male": "","female": "","wowma_catid": "301606","wowma_catname": "アクセサリー・ジュエリー＞ヘアアクセサリー＞シュシュ","qoo_catid": "300002180","qoo_catname": "バッグ・雑貨_ヘアアクセサリー_ヘアゴム・シュシュ","s_keyword": "大人 子供 女の子 結婚式 リボン お呼ばれ パール セット キッズ ピン こども 子ども サンタ 光る クリップ おしゃれ バレッタ キラキラ ギフト バナナクリップ 発表会 花 可愛い カチューシャ プレゼント 小学生 3才 赤 シルバー ゴールド 和装 大きい 黒 ベロア 白 青 ワイヤー パールゴム 幼児 赤ちゃん アクリル アップ アレンジ アンティーク 編み込み 入れ物 ウェディング 宇宙 うさぎ"},
        "ct1019": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > その他", "y_ct": "2084005387","sex": "0","male": "","female": "","wowma_catid": "301602","wowma_catname": "アクセサリー・ジュエリー＞ヘアアクセサリー＞その他ヘアアクセサリー","qoo_catid": "300000127","qoo_catname": "バッグ・雑貨_ヘアアクセサリー_その他","s_keyword": "大人 子供 女の子 結婚式 リボン お呼ばれ パール セット キッズ ピン こども 子ども サンタ 光る クリップ おしゃれ バレッタ キラキラ ギフト バナナクリップ 発表会 花 可愛い カチューシャ プレゼント 小学生 3才 赤 シルバー ゴールド 和装 大きい 黒 ベロア 白 青 ワイヤー パールゴム 幼児 赤ちゃん アクリル アップ アレンジ アンティーク 編み込み 入れ物 ウェディング 宇宙 うさぎ"},
        "ct1020": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ヘアバンド、カチューシャ", "y_ct": "2084019051","sex": "0","male": "","female": "","wowma_catid": "301611","wowma_catname": "アクセサリー・ジュエリー＞ヘアアクセサリー＞ヘアバンド","qoo_catid": "300000126","qoo_catname": "バッグ・雑貨_ヘアアクセサリー_カチューシャ・ヘアバンド","s_keyword": "大人 子供 女の子 結婚式 リボン お呼ばれ パール セット キッズ ピン こども 子ども サンタ 光る クリップ おしゃれ バレッタ キラキラ ギフト バナナクリップ 発表会 花 可愛い カチューシャ プレゼント 小学生 3才 赤 シルバー ゴールド 和装 大きい 黒 ベロア 白 青 ワイヤー パールゴム 幼児 赤ちゃん アクリル アップ アレンジ アンティーク 編み込み 入れ物 ウェディング 宇宙 うさぎ"},
        "ct1021": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ヘアバンド、カチューシャ", "y_ct": "2084019051","sex": "0","male": "","female": "","wowma_catid": "301603","wowma_catname": "アクセサリー・ジュエリー＞ヘアアクセサリー＞カチューシャ","qoo_catid": "300000126","qoo_catname": "バッグ・雑貨_ヘアアクセサリー_カチューシャ・ヘアバンド","s_keyword": "大人 子供 女の子 結婚式 リボン お呼ばれ パール セット キッズ ピン こども 子ども サンタ 光る クリップ おしゃれ バレッタ キラキラ ギフト バナナクリップ 発表会 花 可愛い カチューシャ プレゼント 小学生 3才 赤 シルバー ゴールド 和装 大きい 黒 ベロア 白 青 ワイヤー パールゴム 幼児 赤ちゃん アクリル アップ アレンジ アンティーク 編み込み 入れ物 ウェディング 宇宙 うさぎ"},
        "ct1011": {"ctname": "ファッション雑貨 > メガネ", "y_ct": "2084042537", "sex": "0", "male": "", "female": "",
                   "wowma_catid": "450602", "wowma_catname": "バッグ・財布・ファッション小物>メガネ>その他メガネ", "qoo_catid": "300000128",
                   "qoo_catname": "バッグ・雑貨_眼鏡・サングラス_サングラス",
                   "s_keyword": "メンズ 運転用 レディース 偏光 メガネの上から おしゃれ ポリス メガネの上 野球 ゴルフ 偏光レンズ ケース ロードバイク ランニング 昼夜兼用 夜間 日本製 調光 大きめ ブランド スポーツ 黒 uvカット スワンズ クリップオン 運転 釣り クラブマスター 木村拓哉 ティアドロップ クリップ式 跳ね上げ式 007 メンズキムタク 透明 0816 tf0875 キムタク ブルーレンズ 赤 青レンズ 青 赤レンズ アウトドア 朝倉未来 イヤホン いかつい 色つき"},
        "ct1012": {"ctname": "オークション > スポーツ、レジャー > スポーツサングラス > その他", "y_ct": "2084214056","sex": "0","male": "","female": "","wowma_catid": "450202","wowma_catname": "バッグ・財布・ファッション小物＞サングラス＞スポーツサングラス","qoo_catid": "300000209","qoo_catname": "スポーツ_スポーツシューズ・雑貨_スポーツグラス・ゴーグル","s_keyword": "メンズ 運転用 レディース 偏光 メガネの上から おしゃれ ポリス メガネの上 野球 ゴルフ 偏光レンズ ケース ロードバイク ランニング 昼夜兼用 夜間 日本製 調光 大きめ ブランド スポーツ 黒 uvカット スワンズ クリップオン 運転 釣り クラブマスター 木村拓哉 ティアドロップ クリップ式 跳ね上げ式 007 メンズキムタク 透明 0816 tf0875 キムタク ブルーレンズ 赤 青レンズ 青 赤レンズ アウトドア 朝倉未来 イヤホン いかつい 色つき"},
        "ct1013": {"ctname": "オークション > ビューティー、ヘルスケア > めがね、コンタクト > その他", "y_ct": "2084042537","sex": "0","male": "","female": "","wowma_catid": "3801","wowma_catname": "コンタクトレンズ・カラコン＞その他コンタクトレンズ・カラコン","qoo_catid": "300000128","qoo_catname": "バッグ・雑貨_眼鏡・サングラス_サングラス","s_keyword": "メンズ 運転用 レディース 偏光 メガネの上から おしゃれ ポリス メガネの上 野球 ゴルフ 偏光レンズ ケース ロードバイク ランニング 昼夜兼用 夜間 日本製 調光 大きめ ブランド スポーツ 黒 uvカット スワンズ クリップオン 運転 釣り クラブマスター 木村拓哉 ティアドロップ クリップ式 跳ね上げ式 007 メンズキムタク 透明 0816 tf0875 キムタク ブルーレンズ 赤 青レンズ 青 赤レンズ アウトドア 朝倉未来 イヤホン いかつい 色つき"},
        "ct1014": {"ctname": "オークション > ビューティー、ヘルスケア > めがね、コンタクト > 老眼鏡", "y_ct": "2084042533","sex": "0","male": "","female": "","wowma_catid": "450609","wowma_catname": "バッグ・財布・ファッション小物＞メガネ＞老眼鏡","qoo_catid": "300003090","qoo_catname": "バッグ・雑貨_眼鏡・サングラス_老眼鏡","s_keyword": "メンズ 運転用 レディース 偏光 メガネの上から おしゃれ ポリス メガネの上 野球 ゴルフ 偏光レンズ ケース ロードバイク ランニング 昼夜兼用 夜間 日本製 調光 大きめ ブランド スポーツ 黒 uvカット スワンズ クリップオン 運転 釣り クラブマスター 木村拓哉 ティアドロップ クリップ式 跳ね上げ式 007 メンズキムタク 透明 0816 tf0875 キムタク ブルーレンズ 赤 青レンズ 青 赤レンズ アウトドア 朝倉未来 イヤホン いかつい 色つき"},
        "ct1015": {"ctname": "オークション > おもちゃ、ゲーム > 手品、パーティグッズ > パーティグッズ > その他", "y_ct": "2084059858","sex": "0","male": "","female": "","wowma_catid": "29120506","wowma_catname": "おもちゃ・趣味＞トレーディングカード＞トレーディングカードゲーム＞マジック：ザ・ギャザリング","qoo_catid": "300000702","qoo_catname": "ホビー・コスプレ_パーティー・イベント用品_その他","s_keyword": "おもしろ 誕生日 メガネ マスク びっくり ひげ 被り物 耳 ヒゲ tシャツ おもちゃ 王冠 冠 かわいい たすき クラッカー くす玉 ケーキ 子ども サングラス スプレー 扇子 かつら 大人の 風船 三角帽子 優勝 リボン ルーレット ワイン ジャケット ビリビリ 帽子 ピュー 2022 500円"},
        "ct1055": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > その他", "y_ct": "2084062070","sex": "0","male": "","female": "","wowma_catid": "450321","wowma_catname": "バッグ・財布・ファッション小物＞バッグ＞バッグ小物・アクセサリー","qoo_catid": "300000103","qoo_catname": "腕時計・アクセサリー_ファッション腕時計_その他","s_keyword": "ネックレス 人気 ブレスレット リング ピアス イヤリング ケース セット 福袋 皮 人気シルバー リング韓国風 指輪 ブランド ギフト バングル プレゼント メンズ アクセサリー 腕 おしゃれ 革 可愛い 金 金属アレルギー対応 クロス 黒 収納 シルバー 誕生石 12月 チョーカー とみーふぃるふぃがー 猫 羽 紐 蛇ネックレス 本 耳 安い レザー ロング かわいい ゴールド  ボックス パーツ プラチナ"},
        "ct1056": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > イヤリング > その他", "y_ct": "2084005416","sex": "0","male": "","female": "","wowma_catid": "3004","wowma_catname": "アクセサリー・ジュエリー＞イヤリング","qoo_catid": "320001455","qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_イヤリング","s_keyword": "レディース 人気 パーツ コンバーター 収納 片耳 シリコンカバー 穴なし 黒 シンプル フェイクピアス シルバー ゴールド 赤 安い 大人 揺れる ブランド 大ぶり 冬 パール 雪 サージカルステンレス アレルギー対応 クリップ式 平皿 フープ クリップ ネジバネ式 縦型 樹脂 ピンクゴールド 横型 金属アレルギー アネモネ 収納ケース 壁掛け 大容量 おしゃれ 木製 ミニ 子供 かわいい マグネット 片耳せっと ネジ式 5mm 大"},
        "ct1061": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > その他", "y_ct": "2084062070","sex": "0","male": "","female": "","wowma_catid": "450321","wowma_catname": "バッグ・財布・ファッション小物＞バッグ＞バッグ小物・アクセサリー","qoo_catid": "300000103","qoo_catname": "腕時計・アクセサリー_ファッション腕時計_その他","s_keyword": "ネックレス 人気 ブレスレット リング ピアス イヤリング ケース セット 福袋 皮 人気シルバー リング韓国風 指輪 ブランド ギフト バングル プレゼント メンズ アクセサリー 腕 おしゃれ 革 可愛い 金 金属アレルギー対応 クロス 黒 収納 シルバー 誕生石 12月 チョーカー とみーふぃるふぃがー 猫 羽 紐 蛇ネックレス 本 耳 安い レザー ロング かわいい ゴールド  ボックス パーツ プラチナ"},
        "ct1062": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > イヤリング > その他", "y_ct": "2084005416","sex": "0","male": "","female": "","wowma_catid": "3004","wowma_catname": "アクセサリー・ジュエリー＞イヤリング","qoo_catid": "320001455","qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_イヤリング","s_keyword": "レディース 人気 パーツ コンバーター 収納 片耳 シリコンカバー 穴なし 黒 シンプル フェイクピアス シルバー ゴールド 赤 安い 大人 揺れる ブランド 大ぶり 冬 パール 雪 サージカルステンレス アレルギー対応 クリップ式 平皿 フープ クリップ ネジバネ式 縦型 樹脂 ピンクゴールド 横型 金属アレルギー アネモネ 収納ケース 壁掛け 大容量 おしゃれ 木製 ミニ 子供 かわいい マグネット 片耳せっと ネジ式 5mm 大"},
        "ct1057": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > ピアス > その他", "y_ct": "2084062576","sex": "0","male": "","female": "","wowma_catid": "3012","wowma_catname": "アクセサリー・ジュエリー＞ピアス","qoo_catid": "320001456","qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_ピアス","s_keyword": "メンズ レディース 18金 人気 金属アレルギー対応 キャッチ リング ケース プラチナ 片耳 ブランド フープ 黒 シンプル セット 両耳 ゆれる 大人 人気18金 ピンクゴールド つけっぱなし 揺れる パール 小さめ チェーン 安い 落ちない シリコン 16g キャッチャー シルバー 14g ゴールド 細い 8mm 収納 持ち運び 大容量 プレゼント用 携帯用 ミニ プレゼント ダイヤ プラチナ950 小さい ダイヤモンド アレルギー対応 赤 あれるぎー対応 アレルギー"},
        "ct1064": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ピアス > その他", "y_ct": "2084005423","sex": "0","male": "","female": "","wowma_catid": "3012","wowma_catname": "アクセサリー・ジュエリー＞ピアス","qoo_catid": "320001456","qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_ピアス","s_keyword": "レディース 18金 人気 金属アレルギー対応 キャッチ リング ケース プラチナ 片耳 ブランド フープ 黒 シンプル セット 両耳 ゆれる 大人 人気18金 ピンクゴールド つけっぱなし 揺れる パール 小さめ チェーン 安い 落ちない シリコン 16g キャッチャー シルバー 14g ゴールド 細い 8mm 収納 持ち運び 大容量 プレゼント用 携帯用 ミニ プレゼント ダイヤ プラチナ950 小さい ダイヤモンド アレルギー対応 赤 あれるぎー対応 アレルギー"},
        "ct1074": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ピアス > その他", "y_ct": "2084005423","sex": "0","male": "","female": "","wowma_catid": "3012","wowma_catname": "アクセサリー・ジュエリー＞ピアス","qoo_catid": "320001456","qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_ピアス","s_keyword": "レディース 18金 人気 金属アレルギー対応 キャッチ リング ケース プラチナ 片耳 ブランド フープ 黒 シンプル セット 両耳 ゆれる 大人 人気18金 ピンクゴールド つけっぱなし 揺れる パール 小さめ チェーン 安い 落ちない シリコン 16g キャッチャー シルバー 14g ゴールド 細い 8mm 収納 持ち運び 大容量 プレゼント用 携帯用 ミニ プレゼント ダイヤ プラチナ950 小さい ダイヤモンド アレルギー対応 赤 あれるぎー対応 アレルギー"},
        "ct1075": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ピアス > その他", "y_ct": "2084005423","sex": "0","male": "","female": "","wowma_catid": "3012","wowma_catname": "アクセサリー・ジュエリー＞ピアス","qoo_catid": "320001456","qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_ピアス","s_keyword": "レディース 18金 人気 金属アレルギー対応 キャッチ リング ケース プラチナ 片耳 ブランド フープ 黒 シンプル セット 両耳 ゆれる 大人 人気18金 ピンクゴールド つけっぱなし 揺れる パール 小さめ チェーン 安い 落ちない シリコン 16g キャッチャー シルバー 14g ゴールド 細い 8mm 収納 持ち運び 大容量 プレゼント用 携帯用 ミニ プレゼント ダイヤ プラチナ950 小さい ダイヤモンド アレルギー対応 赤 あれるぎー対応 アレルギー"},
        "ct1076": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ピアス > その他", "y_ct": "2084005423","sex": "0","male": "","female": "","wowma_catid": "3012","wowma_catname": "アクセサリー・ジュエリー＞ピアス","qoo_catid": "320001456","qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_ピアス","s_keyword": "レディース 18金 人気 金属アレルギー対応 キャッチ リング ケース プラチナ 片耳 ブランド フープ 黒 シンプル セット 両耳 ゆれる 大人 人気18金 ピンクゴールド つけっぱなし 揺れる パール 小さめ チェーン 安い 落ちない シリコン 16g キャッチャー シルバー 14g ゴールド 細い 8mm 収納 持ち運び 大容量 プレゼント用 携帯用 ミニ プレゼント ダイヤ プラチナ950 小さい ダイヤモンド アレルギー対応 赤 あれるぎー対応 アレルギー"},
        "ct1077": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ピアス > その他", "y_ct": "2084005423","sex": "0","male": "","female": "","wowma_catid": "3012","wowma_catname": "アクセサリー・ジュエリー＞ピアス","qoo_catid": "320001456","qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_ピアス","s_keyword": "レディース 18金 人気 金属アレルギー対応 キャッチ リング ケース プラチナ 片耳 ブランド フープ 黒 シンプル セット 両耳 ゆれる 大人 人気18金 ピンクゴールド つけっぱなし 揺れる パール 小さめ チェーン 安い 落ちない シリコン 16g キャッチャー シルバー 14g ゴールド 細い 8mm 収納 持ち運び 大容量 プレゼント用 携帯用 ミニ プレゼント ダイヤ プラチナ950 小さい ダイヤモンド アレルギー対応 赤 あれるぎー対応 アレルギー"},
        "ct1078": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ピアス > その他", "y_ct": "2084005423","sex": "0","male": "","female": "","wowma_catid": "3012","wowma_catname": "アクセサリー・ジュエリー＞ピアス","qoo_catid": "320001456","qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_ピアス","s_keyword": "レディース 18金 人気 金属アレルギー対応 キャッチ リング ケース プラチナ 片耳 ブランド フープ 黒 シンプル セット 両耳 ゆれる 大人 人気18金 ピンクゴールド つけっぱなし 揺れる パール 小さめ チェーン 安い 落ちない シリコン 16g キャッチャー シルバー 14g ゴールド 細い 8mm 収納 持ち運び 大容量 プレゼント用 携帯用 ミニ プレゼント ダイヤ プラチナ950 小さい ダイヤモンド アレルギー対応 赤 あれるぎー対応 アレルギー"},
        "ct1079": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ピアス > その他", "y_ct": "2084005423","sex": "0","male": "","female": "","wowma_catid": "3012","wowma_catname": "アクセサリー・ジュエリー＞ピアス","qoo_catid": "320001456","qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_ピアス","s_keyword": "レディース 18金 人気 金属アレルギー対応 キャッチ リング ケース プラチナ 片耳 ブランド フープ 黒 シンプル セット 両耳 ゆれる 大人 人気18金 ピンクゴールド つけっぱなし 揺れる パール 小さめ チェーン 安い 落ちない シリコン 16g キャッチャー シルバー 14g ゴールド 細い 8mm 収納 持ち運び 大容量 プレゼント用 携帯用 ミニ プレゼント ダイヤ プラチナ950 小さい ダイヤモンド アレルギー対応 赤 あれるぎー対応 アレルギー"},
        "ct1058": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > ネックレス > その他", "y_ct": "2084006915","sex": "0","male": "","female": "","wowma_catid": "3009","wowma_catname": "アクセサリー・ジュエリー＞ネックレス","qoo_catid": "300000106","qoo_catname": "メンズバッグ・シューズ・小物_メンズ小物_ネックレス","s_keyword": "レディース メンズ 人気 チェーン ゴールド ブランド 安い ピンクゴールド メンズ人気 メンズ人気ブランド シルバー メンズブランド 革紐 メンズチェーン ごろーず 正規品 オープンハート tiffany スマイル ダイヤ 人気ブランド 4 金属アレルギー対応 ロング シンプル ハート スワン ペア ピアス セット かっこいい 磁気 スポーツ 人気ブランドプラチナ 人気ブランド チェーンのみ ステンレス 指輪 女性 鍵 金 オーブ ピンク ブルー パール アジャスター 赤 アニメ"},
        "ct1065": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > ネックレス > その他", "y_ct": "2084006915","sex": "0","male": "","female": "","wowma_catid": "3009","wowma_catname": "アクセサリー・ジュエリー＞ネックレス","qoo_catid": "300000106","qoo_catname": "メンズバッグ・シューズ・小物_メンズ小物_ネックレス","s_keyword": "レディース メンズ 人気 チェーン ゴールド ブランド 安い ピンクゴールド メンズ人気 メンズ人気ブランド シルバー メンズブランド 革紐 メンズチェーン ごろーず 正規品 オープンハート tiffany スマイル ダイヤ 人気ブランド 4 金属アレルギー対応 ロング シンプル ハート スワン ペア ピアス セット かっこいい 磁気 スポーツ 人気ブランドプラチナ 人気ブランド チェーンのみ ステンレス 指輪 女性 鍵 金 オーブ ピンク ブルー パール アジャスター 赤 アニメ"},
        "ct1080": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > ネックレス > その他", "y_ct": "2084006915","sex": "0","male": "","female": "","wowma_catid": "3009","wowma_catname": "アクセサリー・ジュエリー＞ネックレス","qoo_catid": "300000106","qoo_catname": "メンズバッグ・シューズ・小物_メンズ小物_ネックレス","s_keyword": "レディース メンズ 人気 チェーン ゴールド ブランド 安い ピンクゴールド メンズ人気 メンズ人気ブランド シルバー メンズブランド 革紐 メンズチェーン ごろーず 正規品 オープンハート tiffany スマイル ダイヤ 人気ブランド 4 金属アレルギー対応 ロング シンプル ハート スワン ペア ピアス セット かっこいい 磁気 スポーツ 人気ブランドプラチナ 人気ブランド チェーンのみ ステンレス 指輪 女性 鍵 金 オーブ ピンク ブルー パール アジャスター 赤 アニメ"},
        "ct1081": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > ネックレス > その他", "y_ct": "2084006915","sex": "0","male": "","female": "","wowma_catid": "3009","wowma_catname": "アクセサリー・ジュエリー＞ネックレス","qoo_catid": "300000106","qoo_catname": "メンズバッグ・シューズ・小物_メンズ小物_ネックレス","s_keyword": "レディース メンズ 人気 チェーン ゴールド ブランド 安い ピンクゴールド メンズ人気 メンズ人気ブランド シルバー メンズブランド 革紐 メンズチェーン ごろーず 正規品 オープンハート tiffany スマイル ダイヤ 人気ブランド 4 金属アレルギー対応 ロング シンプル ハート スワン ペア ピアス セット かっこいい 磁気 スポーツ 人気ブランドプラチナ 人気ブランド チェーンのみ ステンレス 指輪 女性 鍵 金 オーブ ピンク ブルー パール アジャスター 赤 アニメ"},
        "ct1066": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ネックレス、ペンダント > その他", "y_ct": "2084005400","sex": "0","male": "","female": "","wowma_catid": "3009","wowma_catname": "アクセサリー・ジュエリー＞ネックレス","qoo_catid": "300002342","qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_ネックレス","s_keyword": "レディース 人気 チェーン ゴールド ブランド 安い ピンクゴールド メンズ人気 メンズ人気ブランド シルバー メンズブランド 革紐 メンズチェーン ごろーず 正規品 オープンハート tiffany スマイル ダイヤ 人気ブランド 4 金属アレルギー対応 ロング シンプル ハート スワン ペア ピアス セット かっこいい 磁気 スポーツ 人気ブランドプラチナ 人気ブランド チェーンのみ ステンレス 指輪 女性 鍵 金 オーブ ピンク ブルー パール アジャスター 赤 アニメ"},
        "ct1082": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ネックレス、ペンダント > その他", "y_ct": "2084005400","sex": "0","male": "","female": "","wowma_catid": "3009","wowma_catname": "アクセサリー・ジュエリー＞ネックレス","qoo_catid": "300002342","qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_ネックレス","s_keyword": "レディース 人気 チェーン ゴールド ブランド 安い ピンクゴールド メンズ人気 メンズ人気ブランド シルバー メンズブランド 革紐 メンズチェーン ごろーず 正規品 オープンハート tiffany スマイル ダイヤ 人気ブランド 4 金属アレルギー対応 ロング シンプル ハート スワン ペア ピアス セット かっこいい 磁気 スポーツ 人気ブランドプラチナ 人気ブランド チェーンのみ ステンレス 指輪 女性 鍵 金 オーブ ピンク ブルー パール アジャスター 赤 アニメ"},
        "ct1083": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > チョーカー > その他", "y_ct": "2084005394","sex": "0","male": "","female": "","wowma_catid": "3008","wowma_catname": "アクセサリー・ジュエリー＞チョーカー","qoo_catid": "300002342","qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_ネックレス","s_keyword": "レディース 黒 首輪 赤 レザー レース ネックレス シルバー ゴールド リボン 白 ピンク シンプル 太め ゴシック 鈴 人気 十字架 革紐 クロス リード付き sm 太い コスプレ キッズ 赤色 チェーン 紐 トライアングル ハートモチーフ おしゃれ 革 迷子札 業務用 小型犬 大型犬 正月 ネックレスチェーン ラインストーン 地雷系 青 アンティーク 足 安全靴 脚 アンクレット イニシャル"},
        "ct1084": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ネックレス、ペンダント > その他", "y_ct": "2084005400","sex": "0","male": "","female": "","wowma_catid": "3009","wowma_catname": "アクセサリー・ジュエリー＞ネックレス","qoo_catid": "300002342","qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_ネックレス","s_keyword": "レディース 人気 チェーン ゴールド ブランド 安い ピンクゴールド メンズ人気 メンズ人気ブランド シルバー メンズブランド 革紐 メンズチェーン ごろーず 正規品 オープンハート tiffany スマイル ダイヤ 人気ブランド 4 金属アレルギー対応 ロング シンプル ハート スワン ペア ピアス セット かっこいい 磁気 スポーツ 人気ブランドプラチナ 人気ブランド チェーンのみ ステンレス 指輪 女性 鍵 金 オーブ ピンク ブルー パール アジャスター 赤 アニメ"},
        "ct1085": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ネックレス、ペンダント > その他", "y_ct": "2084005400","sex": "0","male": "","female": "","wowma_catid": "3009","wowma_catname": "アクセサリー・ジュエリー＞ネックレス","qoo_catid": "300002342","qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_ネックレス","s_keyword": "レディース 人気 チェーン ゴールド ブランド 安い ピンクゴールド メンズ人気 メンズ人気ブランド シルバー メンズブランド 革紐 メンズチェーン ごろーず 正規品 オープンハート tiffany スマイル ダイヤ 人気ブランド 4 金属アレルギー対応 ロング シンプル ハート スワン ペア ピアス セット かっこいい 磁気 スポーツ 人気ブランドプラチナ 人気ブランド チェーンのみ ステンレス 指輪 女性 鍵 金 オーブ ピンク ブルー パール アジャスター 赤 アニメ"},
        "ct1086": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ネックレス、ペンダント > ダイヤモンド > その他", "y_ct": "2084209780","sex": "0","male": "","female": "","wowma_catid": "3009","wowma_catname": "アクセサリー・ジュエリー＞ネックレス","qoo_catid": "320001121","qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_指輪","s_keyword": "レディース 人気 チェーン ゴールド ブランド 安い ピンクゴールド メンズ人気 メンズ人気ブランド シルバー メンズブランド 革紐 メンズチェーン ごろーず 正規品 オープンハート tiffany スマイル ダイヤ 人気ブランド 4 金属アレルギー対応 ロング シンプル ハート スワン ペア ピアス セット かっこいい 磁気 スポーツ 人気ブランドプラチナ 人気ブランド チェーンのみ ステンレス 指輪 女性 鍵 金 オーブ ピンク ブルー パール アジャスター 赤 アニメ"},
        "ct1087": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ネックレス、ペンダント > その他", "y_ct": "2084005400","sex": "0","male": "","female": "","wowma_catid": "3009","wowma_catname": "アクセサリー・ジュエリー＞ネックレス","qoo_catid": "300002342","qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_ネックレス","s_keyword": "レディース 人気 チェーン ゴールド ブランド 安い ピンクゴールド メンズ人気 メンズ人気ブランド シルバー メンズブランド 革紐 メンズチェーン ごろーず 正規品 オープンハート tiffany スマイル ダイヤ 人気ブランド 4 金属アレルギー対応 ロング シンプル ハート スワン ペア ピアス セット かっこいい 磁気 スポーツ 人気ブランドプラチナ 人気ブランド チェーンのみ ステンレス 指輪 女性 鍵 金 オーブ ピンク ブルー パール アジャスター 赤 アニメ"},
        "ct1059": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > ブレスレット、バングル > その他", "y_ct": "2084052636","sex": "0","male": "","female": "","wowma_catid": "3014","wowma_catname": "アクセサリー・ジュエリー＞ブレスレット","qoo_catid": "300000107","qoo_catname": "メンズバッグ・シューズ・小物_メンズ小物_ブレスレット・バングル","s_keyword": "静電気除去 メンズ 静電気防止 人気 レディース レディース ペア 18金 最強 シリコン おしゃれ 強力 日本製 ブランド シルバー コラントッテ レザー 革 女性 人気女性用 安い ピンクゴールド 静電気 ゴールド ハードウェア 正規品 エルサ ペレッティ ミニ オープン ハート カップル つけっぱなし 金属アレルギー対応 刻印 誕生石 ペアルック ピンク グリーン ブルー 喜平 バングル レディース高額 9月 レディース50g 赤 青 アジャスター"},
        "ct1068": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > ブレスレット、バングル > その他", "y_ct": "2084052636","sex": "0","male": "","female": "","wowma_catid": "3014","wowma_catname": "アクセサリー・ジュエリー＞ブレスレット","qoo_catid": "300000107","qoo_catname": "メンズバッグ・シューズ・小物_メンズ小物_ブレスレット・バングル","s_keyword": "静電気除去 メンズ 静電気防止 人気 レディース レディース ペア 18金 最強 シリコン おしゃれ 強力 日本製 ブランド シルバー コラントッテ レザー 革 女性 人気女性用 安い ピンクゴールド 静電気 ゴールド ハードウェア 正規品 エルサ ペレッティ ミニ オープン ハート カップル つけっぱなし 金属アレルギー対応 刻印 誕生石 ペアルック ピンク グリーン ブルー 喜平 バングル レディース高額 9月 レディース50g 赤 青 アジャスター"},
        "ct1088": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > ブレスレット、バングル > その他", "y_ct": "2084052636","sex": "0","male": "","female": "","wowma_catid": "3014","wowma_catname": "アクセサリー・ジュエリー＞ブレスレット","qoo_catid": "300000107","qoo_catname": "メンズバッグ・シューズ・小物_メンズ小物_ブレスレット・バングル","s_keyword": "静電気除去 メンズ 静電気防止 人気 レディース レディース ペア 18金 最強 シリコン おしゃれ 強力 日本製 ブランド シルバー コラントッテ レザー 革 女性 人気女性用 安い ピンクゴールド 静電気 ゴールド ハードウェア 正規品 エルサ ペレッティ ミニ オープン ハート カップル つけっぱなし 金属アレルギー対応 刻印 誕生石 ペアルック ピンク グリーン ブルー 喜平 バングル レディース高額 9月 レディース50g 赤 青 アジャスター"},
        "ct1089": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > ブレスレット、バングル > バングル > その他", "y_ct": "2084062608","sex": "0","male": "","female": "","wowma_catid": "3014","wowma_catname": "アクセサリー・ジュエリー＞ブレスレット","qoo_catid": "300000107","qoo_catname": "メンズバッグ・シューズ・小物_メンズ小物_ブレスレット・バングル","s_keyword": "静電気除去 メンズ 静電気防止 人気 レディース レディース ペア 18金 最強 シリコン おしゃれ 強力 日本製 ブランド シルバー コラントッテ レザー 革 女性 人気女性用 安い ピンクゴールド 静電気 ゴールド ハードウェア 正規品 エルサ ペレッティ ミニ オープン ハート カップル つけっぱなし 金属アレルギー対応 刻印 誕生石 ペアルック ピンク グリーン ブルー 喜平 バングル レディース高額 9月 レディース50g 赤 青 アジャスター"},
        "ct1090": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > ブレスレット、バングル > その他", "y_ct": "2084052636","sex": "0","male": "","female": "","wowma_catid": "3014","wowma_catname": "アクセサリー・ジュエリー＞ブレスレット","qoo_catid": "300000107","qoo_catname": "メンズバッグ・シューズ・小物_メンズ小物_ブレスレット・バングル","s_keyword": "静電気除去 メンズ 静電気防止 人気 レディース レディース ペア 18金 最強 シリコン おしゃれ 強力 日本製 ブランド シルバー コラントッテ レザー 革 女性 人気女性用 安い ピンクゴールド 静電気 ゴールド ハードウェア 正規品 エルサ ペレッティ ミニ オープン ハート カップル つけっぱなし 金属アレルギー対応 刻印 誕生石 ペアルック ピンク グリーン ブルー 喜平 バングル レディース高額 9月 レディース50g 赤 青 アジャスター"},
        "ct1069": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > ブレスレット、バングル > その他", "y_ct": "2084052636","sex": "0","male": "","female": "","wowma_catid": "3014","wowma_catname": "アクセサリー・ジュエリー＞ブレスレット","qoo_catid": "300000107","qoo_catname": "メンズバッグ・シューズ・小物_メンズ小物_ブレスレット・バングル","s_keyword": "静電気除去 メンズ 静電気防止 人気 レディース レディース ペア 18金 最強 シリコン おしゃれ 強力 日本製 ブランド シルバー コラントッテ レザー 革 女性 人気女性用 安い ピンクゴールド 静電気 ゴールド ハードウェア 正規品 エルサ ペレッティ ミニ オープン ハート カップル つけっぱなし 金属アレルギー対応 刻印 誕生石 ペアルック ピンク グリーン ブルー 喜平 バングル レディース高額 9月 レディース50g 赤 青 アジャスター"},
        "ct1091": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > ブレスレット、バングル > その他", "y_ct": "2084052636","sex": "0","male": "","female": "","wowma_catid": "3014","wowma_catname": "アクセサリー・ジュエリー＞ブレスレット","qoo_catid": "300000107","qoo_catname": "メンズバッグ・シューズ・小物_メンズ小物_ブレスレット・バングル","s_keyword": "静電気除去 メンズ 静電気防止 人気 レディース レディース ペア 18金 最強 シリコン おしゃれ 強力 日本製 ブランド シルバー コラントッテ レザー 革 女性 人気女性用 安い ピンクゴールド 静電気 ゴールド ハードウェア 正規品 エルサ ペレッティ ミニ オープン ハート カップル つけっぱなし 金属アレルギー対応 刻印 誕生石 ペアルック ピンク グリーン ブルー 喜平 バングル レディース高額 9月 レディース50g 赤 青 アジャスター"},
        "ct1092": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ブレスレット、バングル > バングル > その他", "y_ct": "2084019059","sex": "0","male": "","female": "","wowma_catid": "3014","wowma_catname": "アクセサリー・ジュエリー＞ブレスレット","qoo_catid": "300000107","qoo_catname": "メンズバッグ・シューズ・小物_メンズ小物_ブレスレット・バングル","s_keyword": "静電気除去 静電気防止 人気 レディース レディース ペア 18金 最強 シリコン おしゃれ 強力 日本製 ブランド シルバー コラントッテ レザー 革 女性 人気女性用 安い ピンクゴールド 静電気 ゴールド ハードウェア 正規品 エルサ ペレッティ ミニ オープン ハート カップル つけっぱなし 金属アレルギー対応 刻印 誕生石 ペアルック ピンク グリーン ブルー 喜平 バングル レディース高額 9月 レディース50g 赤 青 アジャスター"},
        "ct1093": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > アンクレット > その他", "y_ct": "2084062566","sex": "0","male": "","female": "","wowma_catid": "3003","wowma_catname": "アクセサリー・ジュエリー＞アンクレット","qoo_catid": "320001451","qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_アンクレット","s_keyword": "レディース ペア つけっぱなし 人気 ピンクゴールド 18k プラチナ ステンレス 18金 ミサンガ チェーン 磁気 ブランド シルバー ゴールド スポーツ オニキス 金属アレルギー対応 誕生石 カップル レザー 刻印 ツケッパナシ ゴム ハート 可愛い 金 まるあずき 足首 23 グリーン つけっぱなし人気 健康 25 アレルギー対応 赤 麻 アメジスト アクアマリン アレルギー 赤い糸 アジアン イニシャル 石 犬 馬 海 うさぎ 延長"},
        "ct1094": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > アンクレット > その他", "y_ct": "2084062566","sex": "0","male": "","female": "","wowma_catid": "3003","wowma_catname": "アクセサリー・ジュエリー＞アンクレット","qoo_catid": "320001451","qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_アンクレット","s_keyword": "レディース ペア つけっぱなし 人気 ピンクゴールド 18k プラチナ ステンレス 18金 ミサンガ チェーン 磁気 ブランド シルバー ゴールド スポーツ オニキス 金属アレルギー対応 誕生石 カップル レザー 刻印 ツケッパナシ ゴム ハート 可愛い 金 まるあずき 足首 23 グリーン つけっぱなし人気 健康 25 アレルギー対応 赤 麻 アメジスト アクアマリン アレルギー 赤い糸 アジアン イニシャル 石 犬 馬 海 うさぎ 延長"},
        "ct1060": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > 指輪 > その他", "y_ct": "2084049294","sex": "0","male": "","female": "","wowma_catid": "3020","wowma_catname": "アクセサリー・ジュエリー＞指輪・リング","qoo_catid": "300000108","qoo_catname": "メンズバッグ・シューズ・小物_メンズ小物_指輪","s_keyword": "レディース メンズ ケース サイズ 計測 ペアリング 物語 おしゃれ さいず 人気 安い オシャレ ピンクゴールド ゴールド 18金 フリーサイズ プラチナ シルバー ブランド セット 黒 ステンレス シンプル プロポーズ 持ち運び 携帯用 2個用 小さい ミニ 木製 プレゼント 日本製 棒 可愛い 日本規格 海外規格 us カップル チタン 刻印 サイズ調整 調節 測る やつ シリコン サイズ調整可能 サイズフリー サイズなおし 文庫 本"},
        "ct1070": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > 指輪 > その他", "y_ct": "2084049294","sex": "0","male": "","female": "","wowma_catid": "3020","wowma_catname": "アクセサリー・ジュエリー＞指輪・リング","qoo_catid": "300000108","qoo_catname": "メンズバッグ・シューズ・小物_メンズ小物_指輪","s_keyword": "レディース メンズ ケース サイズ 計測 ペアリング 物語 おしゃれ さいず 人気 安い オシャレ ピンクゴールド ゴールド 18金 フリーサイズ プラチナ シルバー ブランド セット 黒 ステンレス シンプル プロポーズ 持ち運び 携帯用 2個用 小さい ミニ 木製 プレゼント 日本製 棒 可愛い 日本規格 海外規格 us カップル チタン 刻印 サイズ調整 調節 測る やつ シリコン サイズ調整可能 サイズフリー サイズなおし 文庫 本"},
        "ct1071": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > 指輪 > その他", "y_ct": "2084005435","sex": "0","male": "","female": "","wowma_catid": "3020","wowma_catname": "アクセサリー・ジュエリー＞指輪・リング","qoo_catid": "320001121","qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_指輪","s_keyword": "レディース ケース サイズ 計測 ペアリング 物語 おしゃれ さいず 人気 安い オシャレ ピンクゴールド ゴールド 18金 フリーサイズ プラチナ シルバー ブランド セット 黒 ステンレス シンプル プロポーズ 持ち運び 携帯用 2個用 小さい ミニ 木製 プレゼント 日本製 棒 可愛い 日本規格 海外規格 us カップル チタン 刻印 サイズ調整 調節 測る やつ シリコン サイズ調整可能 サイズフリー サイズなおし 文庫 本"},
        "ct1095": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > 指輪 > ゴールド > その他", "y_ct": "2084052678","sex": "0","male": "","female": "","wowma_catid": "3020","wowma_catname": "アクセサリー・ジュエリー＞指輪・リング","qoo_catid": "320001121","qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_指輪","s_keyword": "レディース ケース サイズ 計測 ペアリング 物語 おしゃれ さいず 人気 安い オシャレ ピンクゴールド ゴールド 18金 フリーサイズ プラチナ シルバー ブランド セット 黒 ステンレス シンプル プロポーズ 持ち運び 携帯用 2個用 小さい ミニ 木製 プレゼント 日本製 棒 可愛い 日本規格 海外規格 us カップル チタン 刻印 サイズ調整 調節 測る やつ シリコン サイズ調整可能 サイズフリー サイズなおし 文庫 本"},
        "ct1096": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > 指輪 > その他", "y_ct": "2084005435","sex": "0","male": "","female": "","wowma_catid": "3020","wowma_catname": "アクセサリー・ジュエリー＞指輪・リング","qoo_catid": "320001121","qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_指輪","s_keyword": "レディース ケース サイズ 計測 ペアリング 物語 おしゃれ さいず 人気 安い オシャレ ピンクゴールド ゴールド 18金 フリーサイズ プラチナ シルバー ブランド セット 黒 ステンレス シンプル プロポーズ 持ち運び 携帯用 2個用 小さい ミニ 木製 プレゼント 日本製 棒 可愛い 日本規格 海外規格 us カップル チタン 刻印 サイズ調整 調節 測る やつ シリコン サイズ調整可能 サイズフリー サイズなおし 文庫 本"},
        "ct1097": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > 指輪 > その他", "y_ct": "2084005435","sex": "0","male": "","female": "","wowma_catid": "3020","wowma_catname": "アクセサリー・ジュエリー＞指輪・リング","qoo_catid": "320001121","qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_指輪","s_keyword": "レディース ケース サイズ 計測 ペアリング 物語 おしゃれ さいず 人気 安い オシャレ ピンクゴールド ゴールド 18金 フリーサイズ プラチナ シルバー ブランド セット 黒 ステンレス シンプル プロポーズ 持ち運び 携帯用 2個用 小さい ミニ 木製 プレゼント 日本製 棒 可愛い 日本規格 海外規格 us カップル チタン 刻印 サイズ調整 調節 測る やつ シリコン サイズ調整可能 サイズフリー サイズなおし 文庫 本"},
        "ct1158": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ブローチ > その他", "y_ct": "2084005380","sex": "0","male": "","female": "","wowma_catid": "301501","wowma_catname": "アクセサリー・ジュエリー＞ブローチ・コサージュ＞その他ブローチ・コサージュ","qoo_catid": "320001458","qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_ブローチ","s_keyword": "ピン パール おしゃれ 雪の結晶 猫 25mm 15mm 金具 20mm 30mm 日本製 回転式 パーツ 台座 アナグラム クリスマスリース セット フェルト クリスマスモチーフ ポインセチア 大きめ サークル フォーマル パール本物 リボン イニシャル アコヤ 花 華やか オシャレ ゴールド お洒落 おしゃれ大きめ 85歳 スーツ 結婚式 ミリタリー チェーン シルバー 猫モチーフ 回転 アンティーク 赤 青"},
        "ct794": {"ctname": "オークション > ファッション > ファッション小物 > マフラー > 女性用 > マフラー一般", "y_ct": "2084006464","sex": "0","male": "","female": "","wowma_catid": "450420","wowma_catname": "バッグ・財布・ファッション小物＞ファッション小物＞マフラー","qoo_catid": "300000763","qoo_catname": "バッグ・雑貨_ストール・マフラー_マフラー","s_keyword": "レディース カシミヤ ふわふわ ブランド 白 大判 チェック カシュミー 人気 カシミヤ100 ピンク 赤 ロング リバーシブル フワフワ スヌード かわいい 茶色 ふわふわ毛糸 高校生 ランキング 女子大 ホワイト 2021 ギフト プレゼント ラッピング 並行輸入 ウール 中古 大きめ 白黒 可愛い もこもこ 青 アイボリー 厚手 あったかい アウトドア アクネ 犬 インナーサイレンサー 今治 イギリス 犬用 犬柄"},
        "ct819": {"ctname": "オークション > ファッション > ファッション小物 > ストール > ストール一般", "y_ct": "2084006466","sex": "0","male": "","female": "","wowma_catid": "450410","wowma_catname": "バッグ・財布・ファッション小物＞ファッション小物＞ストール・ショール","qoo_catid": "300000764","qoo_catname": "バッグ・雑貨_ストール・マフラー_ストール","s_keyword": "レディース 大判 クリップ 厚手 カシミヤ マフラー 冬 ブランド 薄手 チェック かわいい 黒 シルク 赤 公式 ドレスゴードン ニット ピンク 革 パール ブローチ パーツ マグネット 猫 リボン 授乳ケープ ポンチョ ボタン 無地 白 人気 花柄 カシミヤタッチ カシミヤ100 レディースloo レディースカシミヤ レオパード 還暦 洗える 青 暖かい アイボリー アジアン アウトドア イギリス インド 今治 イタリア製 家"},
        "ct821": {"ctname": "オークション > ファッション > ファッション小物 > マフラー > 男性用", "y_ct": "2084006472","sex": "0","male": "","female": "","wowma_catid": "450420","wowma_catname": "バッグ・財布・ファッション小物＞ファッション小物＞マフラー","qoo_catid": "300000764","qoo_catname": "バッグ・雑貨_ストール・マフラー_ストール","s_keyword": "レディース カシミヤ メンズ ふわふわ ブランド 白 大判 チェック カシュミー 人気 カシミヤ100 ピンク 赤 ロング リバーシブル フワフワ スヌード かわいい 茶色 ふわふわ毛糸 高校生 ランキング 女子大 ホワイト 2021 ギフト プレゼント ラッピング 並行輸入 ウール 中古 大きめ 白黒 可愛い もこもこ 青 アイボリー 厚手 あったかい アウトドア アクネ 犬 インナーサイレンサー 今治 イギリス 犬用 犬柄"},
        "ct822": {"ctname": "オークション > ファッション > ファッション小物 > ストール > ストール一般", "y_ct": "2084006466","sex": "0","male": "","female": "","wowma_catid": "450410","wowma_catname": "バッグ・財布・ファッション小物＞ファッション小物＞ストール・ショール","qoo_catid": "300000764","qoo_catname": "バッグ・雑貨_ストール・マフラー_ストール","s_keyword": "レディース 大判 メンズ クリップ 厚手 カシミヤ マフラー 冬 ブランド 薄手 チェック かわいい 黒 シルク 赤 公式 ドレスゴードン ニット ピンク 革 パール ブローチ パーツ マグネット 猫 リボン 授乳ケープ ポンチョ ボタン 無地 白 人気 花柄 カシミヤタッチ カシミヤ100 レディースloo レディースカシミヤ レオパード 還暦 洗える 青 暖かい アイボリー アジアン アウトドア イギリス インド 今治 イタリア製 家"},
        "ct820": {"ctname": "オークション > ファッション > ファッション小物 > マフラー > 女性用 > マフラー一般", "y_ct": "2084006464","sex": "0","male": "","female": "","wowma_catid": "450420","wowma_catname": "バッグ・財布・ファッション小物＞ファッション小物＞マフラー","qoo_catid": "300000763","qoo_catname": "バッグ・雑貨_ストール・マフラー_マフラー","s_keyword": "レディース カシミヤ ふわふわ ブランド 白 大判 チェック カシュミー 人気 カシミヤ100 ピンク 赤 ロング リバーシブル フワフワ スヌード かわいい 茶色 ふわふわ毛糸 高校生 ランキング 女子大 ホワイト 2021 ギフト プレゼント ラッピング 並行輸入 ウール 中古 大きめ 白黒 可愛い もこもこ 青 アイボリー 厚手 あったかい アウトドア アクネ 犬 インナーサイレンサー 今治 イギリス 犬用 犬柄"},
        "ct823": {"ctname": "オークション > ファッション > ファッション小物 > マフラー > 女性用 > マフラー一般", "y_ct": "2084006464","sex": "0","male": "","female": "","wowma_catid": "450420","wowma_catname": "バッグ・財布・ファッション小物＞ファッション小物＞マフラー","qoo_catid": "300000763","qoo_catname": "バッグ・雑貨_ストール・マフラー_マフラー","s_keyword": "レディース カシミヤ ふわふわ ブランド 白 大判 チェック カシュミー 人気 カシミヤ100 ピンク 赤 ロング リバーシブル フワフワ スヌード かわいい 茶色 ふわふわ毛糸 高校生 ランキング 女子大 ホワイト 2021 ギフト プレゼント ラッピング 並行輸入 ウール 中古 大きめ 白黒 可愛い もこもこ 青 アイボリー 厚手 あったかい アウトドア アクネ 犬 インナーサイレンサー 今治 イギリス 犬用 犬柄"},
        "ct824": {"ctname": "オークション > ファッション > ファッション小物 > ストール > ストール一般", "y_ct": "2084006466","sex": "0","male": "","female": "","wowma_catid": "450410","wowma_catname": "バッグ・財布・ファッション小物＞ファッション小物＞ストール・ショール","qoo_catid": "300000764","qoo_catname": "バッグ・雑貨_ストール・マフラー_ストール","s_keyword": "レディース 大判 クリップ 厚手 カシミヤ マフラー 冬 ブランド 薄手 チェック かわいい 黒 シルク 赤 公式 ドレスゴードン ニット ピンク 革 パール ブローチ パーツ マグネット 猫 リボン 授乳ケープ ポンチョ ボタン 無地 白 人気 花柄 カシミヤタッチ カシミヤ100 レディースloo レディースカシミヤ レオパード 還暦 洗える 青 暖かい アイボリー アジアン アウトドア イギリス インド 今治 イタリア製 家"},
        "ct810": {"ctname": "オークション > ファッション > レディースバッグ > ハンドバッグ > その他", "y_ct": "2084051024","sex": "0","male": "","female": "","wowma_catid": "450312","wowma_catname": "バッグ・財布・ファッション小物＞バッグ＞ハンドバッグ","qoo_catid": "300000113","qoo_catname": "バッグ・雑貨_バッグ_ハンドバッグ","s_keyword": "レディース 小さめ 人気 本革 ブランド 大きめ 黒 ショルダーバッグ 革 ビジネス おしゃれ ck 防水 財布 軽量 普段使い フォーマル カジュアル 布 トートバッグ 手提げバッグ ブガッティ型バッグ ショルダースト 人気ブランド ベストセラー トート ピンク 白 f83607 ベージュ デニム グレー ミニ アウトレット 1927 1052271 赤 アウトドア アンティーク アニマル柄 青 うさぎ エナメル 柄 エピ a4 女の子"},
        "ct848": {"ctname": "オークション > スポーツ、レジャー > キャンプ、アウトドア用品 > バックパック、かばん > リュックサック > バックパック", "y_ct": "2084057274","sex": "0","male": "","female": "","wowma_catid": "450313","wowma_catname": "バッグ・財布・ファッション小物＞バッグ＞バックパック・リュック","qoo_catid": "300000119","qoo_catname": "メンズバッグ・シューズ・小物_メンズバッグ_リュック・デイパック","s_keyword": "メンズ 大容量 40l レディース 防水 キャンプ ビジネス サイバトロン おしゃれ 小型 本革 30l 80l 60l 50l 軽量 ミリタリー 登山 サッカー 小さめ 通勤 ブランド 人気 旅行用 防水カバー バイク 20l 10 100l 革 ネイビー キッズ トレラン 30 シャトル 3pタクティカル 37l molle アウトドア u.sタイプ リュックデイパック 3day 軍用 molle対応 タクティカル ウォータープルーフ アウトドアデイパック ３day バックル 65"},
        "ct849": {"ctname": "オークション > ファッション > 男女兼用バッグ > リュックサック、デイパック", "y_ct": "2084233233","sex": "0","male": "","female": "","wowma_catid": "450313","wowma_catname": "バッグ・財布・ファッション小物＞バッグ＞バックパック・リュック","qoo_catid": "300002169","qoo_catname": "バッグ・雑貨_バッグ_リュック・デイパック","s_keyword": "メンズ レディース 大容量 女の子 ザ防水 おしゃれ ビジネス 小さめ アウトドア 革 ブランド 大人 本革 軽量 通勤 キッズ 30l 20l 小学生 ベージュ ホットショット 高校生 50l 80l 40l かわいい 幼児 幼稚園 黒 60l 登山 学生 登山用 黄色 オレンジ ピンク ２３ｌ 通学 防水カバー 反射 usb 韓国 赤 アニメ 犬 犬柄 インナーバッグ イザック"},
        "ct850": {"ctname": "オークション > ファッション > 男女兼用バッグ > ショルダーバッグ", "y_ct": "2084233231","sex": "0","male": "","female": "","wowma_catid": "450307","wowma_catname": "バッグ・財布・ファッション小物＞バッグ＞ショルダーバッグ","qoo_catid": "320001471","qoo_catname": "メンズバッグ・シューズ・小物_メンズバッグ_ショルダーバッグ","s_keyword": "レディース メンズ 人気 斜めがけ ブランド 小さめ 大容量 カジュアル a4 革 メンズ斜めかけ 防水 メンズ小さめ 人気ブランド 斜めがけバッグ メッセンジャーバッグ 肩掛けバッグ 通勤 ボディバッグ おしゃれカバン オシャレ 本革 人気ベルトが幅太く タンカー スモーキー レザー フリースタイル 軽量 大きめ ナイロン アウトレット 黒 激安 ピンク キッズ パープルレーベル 4l ミニ f23216 白 ブランドアウトドア 赤 アウトドアブランド"},
        "ct851": {"ctname": "オークション > スポーツ、レジャー > 自転車、サイクリング > バッグ > メッセンジャーバッグ", "y_ct": "2084227171","sex": "0","male": "","female": "","wowma_catid": "450319","wowma_catname": "バッグ・財布・ファッション小物＞バッグ＞メッセンジャーバッグ","qoo_catid": "300002376","qoo_catname": "メンズバッグ・シューズ・小物_メンズバッグ_メッセンジャー・ボディバッグ","s_keyword": "レディース ショルダー 小さめ 人気 ブランド 大きめ a4 トート 斜めがけ メンズ 大容量 リュック ボディ ビジネス イン トート用 縦型 タテ型 リヒトラブ 横 軽量 ハンガー テーブル テーブルフック 10kg ハンガーホルダー かばんかけ クローゼット かわいい クリッパ カラビナ 革 レザー 帆布 カジュアル ナイロン 収納 吊り下げ ラック 収納袋 仕切り 収納ケース 山崎実業 カゴ レディース チャーム チェーン ファー リボン イニシャル ぬいぐるみ"},
        "ct852": {"ctname": "オークション > ファッション > メンズバッグ > ボディバッグ", "y_ct": "2084008349","sex": "0","male": "","female": "","wowma_catid": "450318","wowma_catname": "バッグ・財布・ファッション小物＞バッグ＞ボディバッグ","qoo_catid": "300002376","qoo_catname": "メンズバッグ・シューズ・小物_メンズバッグ_メッセンジャー・ボディバッグ","s_keyword": "メンズ レディース 防水 大容量 革 人気ブランド 小さめ おしゃれ 斜めがけ 人気 ブランド 可愛い ナイロン 軽量 a4 防犯 バイク ショルダーバ usb 本革 ミリタリー 撥水 ビジネス アウトドア 大きめ オリオン スウィープ キッズ 日本製 小型 マチ10センチ 革製品 長財布 ウエストバッグ ボディーバッグ キャラクター mp1101 tbpi ホワイト ワンショルダーバッグ a4サイズ 大容量可愛い アウトドアブランド 赤 イタリアンレザー インナー 入れたまま操作"},
        "ct853": {"ctname": "オークション > 事務、店舗用品 > バッグ、スーツケース > スーツケース、トランク > スーツケース、トランク一般", "y_ct": "2084062327","sex": "0","male": "","female": "","wowma_catid": "450309","wowma_catname": "バッグ・財布・ファッション小物＞バッグ＞スーツケース・キャリーバッグ","qoo_catid": "300000120","qoo_catname": "メンズバッグ・シューズ・小物_メンズバッグ_その他","s_keyword": "機内持ち込み sサイズ mサイズ 大型 軽量 3泊4日用 カバー ベルト フロントオープン 超軽量 拡張 おしゃれ かわいい 人気 可愛い 白 安い 黒 ホワイト 静音 100l以上 120l以上 90l以上 ソフト フレーム 布 ストッパー付き 3泊4日用日本製 3泊4日用グリーン 防水 伸縮 s 透明 カバーmサイズ xl tsaロック キャラクター 十字 ワンタッチ tsa 鍵付き ゴム m 5122 モカ l ss"},
        "ct854": {"ctname": "オークション > ファッション > レディースバッグ > クラッチバッグ、パーティバッグ", "y_ct": "2084008347","sex": "0","male": "","female": "","wowma_catid": "450305","wowma_catname": "バッグ・財布・ファッション小物＞バッグ＞クラッチバッグ","qoo_catid": "300002167","qoo_catname": "バッグ・雑貨_バッグ_クラッチバッグ","s_keyword": "メンズ レディース 本革 結婚式 ブランド 小さめ 大きめ ゴールド 黒 カジュアル ファー レザー 小さい 大きい a4 日本製 結婚式ランキング ２way あお 赤 シルバー ブラック アニアリ アウトドア 青 アニマル 厚め アニメ イタリア イタリアンレザー イントレチャート ウルティマ 薄型 柄 エピ柄 エルゴポック エナメル オシャレ おしゃれ 折り畳み オレンジ 折りたたみ 革 冠婚葬祭 肩掛け かわいい カーボン 紙 キャバ"},
        "ct855": {"ctname": "オークション > ファッション > レディースバッグ > ハンドバッグ > その他", "y_ct": "2084051024","sex": "0","male": "","female": "","wowma_catid": "450312","wowma_catname": "バッグ・財布・ファッション小物＞バッグ＞ハンドバッグ","qoo_catid": "300000113","qoo_catname": "バッグ・雑貨_バッグ_ハンドバッグ","s_keyword": "レディース 小さめ 人気 本革 ブランド 大きめ 黒 ショルダーバッグ 革 ビジネス おしゃれ ck 防水 財布 軽量 普段使い フォーマル カジュアル 布 トートバッグ 手提げバッグ ブガッティ型バッグ ショルダースト 人気ブランド ベストセラー トート ピンク 白 f83607 ベージュ デニム グレー ミニ アウトレット 1927 1052271 赤 アウトドア アンティーク アニマル柄 青 うさぎ エナメル 柄 エピ a4 女の子"},
        "ct856": {"ctname": "オークション > ファッション > 男女兼用バッグ > トートバッグ", "y_ct": "2084233232","sex": "0","male": "","female": "","wowma_catid": "450310","wowma_catname": "バッグ・財布・ファッション小物＞バッグ＞トートバッグ","qoo_catid": "300000116","qoo_catname": "バッグ・雑貨_バッグ_トートバッグ","s_keyword": "レディース メンズ 大容量 キャンバス 小さめ a4 人気 軽量 ブランド 革 本革 カジュアル 大学生 マザーズバック ファスナー付き アウトドア 帆布 韓国 ラージ スモール ミニ ミディアム ジップ エクストララージ ロングハンドル ファスナー 黒 無地 大きめ くま ピンク キャンバスレザー ビッグポニー アウトレット デニム 布 ファー ナイロン 仕切り かわいい ロンシャン l 赤 アウトドアブランド アニメ 洗える アニマル"},
        "ct858": {"ctname": "オークション > ファッション > レディースバッグ > ポーチ", "y_ct": "2084007482","sex": "0","male": "","female": "","wowma_catid": "450303","wowma_catname": "バッグ・財布・ファッション小物＞バッグ＞ウエストポーチ","qoo_catid": "300002863","qoo_catname": "バッグ・雑貨_財布・ポーチ_ポーチ","s_keyword": "レディース かわいい 小物入れ ブランド ライト 可愛い ガジェット 小さめ 人気 ショルダー 大きめ 小さい 化粧品入れ 革 腰 韓国 ナプキン入れ 安い 女の子 小物入れ多能機能性 防水 大きい 薄型 ベルト おしゃれ シンプル 透明 ノベルティ kate 人感センサー 屋外 センサー付き led ソーラー センサー オーデリック 高校生 ミニ ピンク コンパクト 小型 ソフト ハード セミハード キャラクター アウトドア 赤 アニメ"},
        "ct1005": {"ctname": "オークション > ファッション > レディースバッグ > ショルダーバッグ > その他", "y_ct": "2084051009","sex": "0","male": "","female": "","wowma_catid": "450307","wowma_catname": "バッグ・財布・ファッション小物＞バッグ＞ショルダーバッグ","qoo_catid": "300000115","qoo_catname": "バッグ・雑貨_バッグ_ショルダーバッグ","s_keyword": "レディース 人気 斜めがけ ブランド 小さめ 大容量 カジュアル a4 革 メンズ斜めかけ 防水 メンズ小さめ 人気ブランド 斜めがけバッグ メッセンジャーバッグ 肩掛けバッグ 通勤 ボディバッグ おしゃれカバン オシャレ 本革 人気ベルトが幅太く タンカー スモーキー レザー フリースタイル 軽量 大きめ ナイロン アウトレット 黒 激安 ピンク キッズ パープルレーベル 4l ミニ f23216 白 ブランドアウトドア 赤 アウトドアブランド"},
        "ct1006": {"ctname": "オークション > ファッション > レディースバッグ > ショルダーバッグ > その他", "y_ct": "2084051009","sex": "0","male": "","female": "","wowma_catid": "450307","wowma_catname": "バッグ・財布・ファッション小物＞バッグ＞ショルダーバッグ","qoo_catid": "300000115","qoo_catname": "バッグ・雑貨_バッグ_ショルダーバッグ","s_keyword": "レディース 人気 斜めがけ ブランド 小さめ 大容量 カジュアル a4 革 メンズ斜めかけ 防水 メンズ小さめ 人気ブランド 斜めがけバッグ メッセンジャーバッグ 肩掛けバッグ 通勤 ボディバッグ おしゃれカバン オシャレ 本革 人気ベルトが幅太く タンカー スモーキー レザー フリースタイル 軽量 大きめ ナイロン アウトレット 黒 激安 ピンク キッズ パープルレーベル 4l ミニ f23216 白 ブランドアウトドア 赤 アウトドアブランド"},
        "ct1007": {"ctname": "オークション > ファッション > レディースバッグ > ショルダーバッグ > その他", "y_ct": "2084051009","sex": "0","male": "","female": "","wowma_catid": "450307","wowma_catname": "バッグ・財布・ファッション小物＞バッグ＞ショルダーバッグ","qoo_catid": "300000115","qoo_catname": "バッグ・雑貨_バッグ_ショルダーバッグ","s_keyword": "レディース 人気 斜めがけ ブランド 小さめ 大容量 カジュアル a4 革 メンズ斜めかけ 防水 メンズ小さめ 人気ブランド 斜めがけバッグ メッセンジャーバッグ 肩掛けバッグ 通勤 ボディバッグ おしゃれカバン オシャレ 本革 人気ベルトが幅太く タンカー スモーキー レザー フリースタイル 軽量 大きめ ナイロン アウトレット 黒 激安 ピンク キッズ パープルレーベル 4l ミニ f23216 白 ブランドアウトドア 赤 アウトドアブランド"},
        "ct1462": {"ctname": "オークション > ファッション > 男女兼用バッグ > ボストンバッグ", "y_ct": "2084233234","sex": "0","male": "","female": "","wowma_catid": "450317","wowma_catname": "バッグ・財布・ファッション小物＞バッグ＞ボストンバッグ","qoo_catid": "300002170","qoo_catname": "バッグ・雑貨_バッグ_ボストンバッグ","s_keyword": "レディース メンズ 大容量 修学旅行 革 女の子 ゴルフ 2泊3日 おしゃれ 小さめ 1泊 ブランド 旅行 軽量 レザー 本革 スポーツ 100l 防水 80l 大容量65l 男の子 小学生 3泊 人気 le coq large ラージ ミディアム 7185 medium weekender エルサイズ エクストララージ ビジネス 大きめ 革製 ネイビー 50l 子供用 パープル 50 白 95l 71l 60リットル 45l 40l バッグ"},
        "ct1463": {"ctname": "オークション > ファッション > 男女兼用バッグ > エコバッグ", "y_ct": "2084233235","sex": "0","male": "","female": "","wowma_catid": "450304","wowma_catname": "バッグ・財布・ファッション小物＞バッグ＞エコバッグ","qoo_catid": "300002171","qoo_catname": "バッグ・雑貨_バッグ_エコバッグ","s_keyword": "折りたたみ 人気 大容量 コンパクト 保冷 キャラクター 可愛い 小さめ メンズ ブランド マチ付き レジカゴ 丈夫 ファスナー 軽量 おしゃれ オシャレ レディース 大きめ お洒落 キャンバス しゅぱっと m l s シュパット リュック ドロップ 2021 付録 紫 ハワイ 正規品 ミニ 赤 ベージュ ピンク ブルー 折り畳み コンビニサイズ 北欧 かわいい 猫 レジカゴ対応 かご リュック型 リュックサック リュックにもなる アニメ"},
        "ct838": {"ctname": "オークション > アクセサリー、時計 > メンズ腕時計 > デジタル > その他", "y_ct": "2084223447","sex": "0","male": "","female": "","wowma_catid": "5821","wowma_catname": "腕時計＞腕時計メンズ","qoo_catid": "300002357","qoo_catname": "腕時計・アクセサリー_ファッション腕時計_メンズ腕時計","s_keyword": "ソーラー電波時計 安い 自動巻き 人気ブランド ブランド ソーラー電波 人気 安いおしゃれ 安い電波 安いデジタル アナログ 安い順 安いソーラー 自動巻き四角 自動巻きスケルトン 自動巻き自動巻き革バンド 自動巻きデイトナ 自動巻き国産 人気ブランド大きめ 人気ブランド激安 ソーラー電波デジタル 防水 ダイバー 5 自動巻 ダイバー 人気おしゃれ シチズンソーラー シチズンダイバー シチズンダイバーズ クロノグラフ 3d立体文字盤 デジタル オリエント 精度が高い 個性的な設計 長持ち可能 安価格 メンズ 腕時計 インビクタ インディペンデント 薄型 ウブロ"},
        "ct839": {"ctname": "オークション > アクセサリー、時計 > レディース腕時計 > デジタル > その他", "y_ct": "2084223405","sex": "0","male": "","female": "","wowma_catid": "5822","wowma_catname": "腕時計＞腕時計レディース","qoo_catid": "300000103","qoo_catname": "腕時計・アクセサリー_ファッション腕時計_その他","s_keyword": "ソーラー電波 ソーラー ブランド ブレスレット 安い エンジェルハート ソーラー電波防水 ソーラー電波時計 ソーラー電波 充電 日付 ブランドブランド ブレスレット付き 安いもの レディース 腕時計 おしゃれ 細め 電波ソーラー 人気 スクエア アンジェーヌ アナログ 赤 青 アルバ アウトドア アラビア数字 防水 イギリス 薄型 海 宇宙 ウェーブセプター エコドライブ エクシード オリエント 大きめ オリビアバートン クラシック 大人 オシャレ シーマスター お買い得 カシオ"},
        "ct840": {"ctname": "オークション > アクセサリー、時計 > ユニセックス腕時計 > デジタル > その他", "y_ct": "2084223426","sex": "0","male": "","female": "","wowma_catid": "5824","wowma_catname": "腕時計＞腕時計男女兼用（ユニセックス）","qoo_catid": "300002358","qoo_catname": "腕時計・アクセサリー_ファッション腕時計_男女兼用","s_keyword": "メンズ 電波ソーラー 安い 防水 デジタル ソーラー レディース 人気 チタン アナログ キッズ 男の子 女の子 キッズ電波 子供 小学生 かわいい ベルト 20mm 18mm 22mm ベルト調整 工具 ピン 革 12mm 16mm スタンド 木製 2本 アクリル 黒 大理石 スタンドオシャレ ディスプレイ 自動巻 1本 シンプル おしゃれ 赤 アニメ アウトドア 青"},
        "ct841": {"ctname": "オークション > アクセサリー、時計 > ユニセックス腕時計 > デジタル > その他", "y_ct": "2084223426","sex": "0","male": "","female": "","wowma_catid": "5824","wowma_catname": "腕時計＞腕時計男女兼用（ユニセックス）","qoo_catid": "300002358","qoo_catname": "腕時計・アクセサリー_ファッション腕時計_男女兼用","s_keyword": "メンズ 電波ソーラー 安い 防水 デジタル ソーラー レディース 人気 チタン アナログ キッズ 男の子 女の子 キッズ電波 子供 小学生 かわいい ベルト 20mm 18mm 22mm ベルト調整 工具 ピン 革 12mm 16mm スタンド 木製 2本 アクリル 黒 大理石 スタンドオシャレ ディスプレイ 自動巻 1本 シンプル おしゃれ 赤 アニメ アウトドア 青"},
        "ct808": {"ctname": "オークション > ファッション > ファッション小物 > 財布 > 男性用 > その他", "y_ct": "2084292136","sex": "0","male": "","female": "","wowma_catid": "450802","wowma_catname": "バッグ・財布・ファッション小物＞財布＞その他財布","qoo_catid": "300002166","qoo_catname": "バッグ・雑貨_財布・ポーチ_その他","s_keyword": "メンズ 二つ折り レディース 長 人気ブランド こども 男の子 薄い 大容量 本革 ファスナー 小銭入れ無し ブランド 人気 がま口 安い かわいい 人気ブランド 人気ブランド金運 人気ブランド グリーン 緑 アウトレット  ラウンドファスナー ラビット 迷彩 札入れ 花柄 子供 ひもつき キャラクター ストラップ アウトドア アニメ 赤 青 アウトドアブランド アニメコラボ 犬 イタリア 印伝 犬柄 いるびぞんて うす型 薄型 うさぎ"},
        "ct842": {"ctname": "オークション > ファッション > ファッション小物 > 財布 > 男性用 > その他", "y_ct": "2084292136","sex": "0","male": "","female": "","wowma_catid": "450802","wowma_catname": "バッグ・財布・ファッション小物＞財布＞その他財布","qoo_catid": "300002166","qoo_catname": "バッグ・雑貨_財布・ポーチ_その他","s_keyword": "メンズ 二つ折り レディース 長 人気ブランド こども 男の子 薄い 大容量 本革 ファスナー 小銭入れ無し ブランド 人気 がま口 安い かわいい 人気ブランド 人気ブランド金運 人気ブランド グリーン 緑 アウトレット  ラウンドファスナー ラビット 迷彩 札入れ 花柄 子供 ひもつき キャラクター ストラップ アウトドア アニメ 赤 青 アウトドアブランド アニメコラボ 犬 イタリア 印伝 犬柄 いるびぞんて うす型 薄型 うさぎ"},
        "ct843": {"ctname": "オークション > ファッション > ファッション小物 > 財布 > 男性用 > 長財布（小銭入れあり）", "y_ct": "2084292126","sex": "0","male": "","female": "","wowma_catid": "450807","wowma_catname": "バッグ・財布・ファッション小物＞財布＞長財布","qoo_catid": "300000112","qoo_catname": "バッグ・雑貨_財布・ポーチ_長財布","s_keyword": "メンズ 二つ折り レディース 長 人気ブランド こども 男の子 薄い 大容量 本革 ファスナー 小銭入れ無し ブランド 人気 がま口 安い かわいい 人気ブランド 人気ブランド金運 人気ブランド グリーン 緑 アウトレット  ラウンドファスナー ラビット 迷彩 札入れ 花柄 子供 ひもつき キャラクター ストラップ アウトドア アニメ 赤 青 アウトドアブランド アニメコラボ 犬 イタリア 印伝 犬柄 いるびぞんて うす型 薄型 うさぎ"},
        "ct844": {"ctname": "オークション > ファッション > ファッション小物 > 財布 > 男性用 > 二つ折り財布（小銭入れあり）", "y_ct": "2084292128","sex": "0","male": "","female": "","wowma_catid": "450805","wowma_catname": "バッグ・財布・ファッション小物＞財布＞折りたたみ財布","qoo_catid": "300002164","qoo_catname": "バッグ・雑貨_財布・ポーチ_二つ折り財布","s_keyword": "メンズ 二つ折り レディース 長 人気ブランド こども 男の子 薄い 大容量 本革 ファスナー 小銭入れ無し ブランド 人気 がま口 安い かわいい 人気ブランド 人気ブランド金運 人気ブランド グリーン 緑 アウトレット  ラウンドファスナー ラビット 迷彩 札入れ 花柄 子供 ひもつき キャラクター ストラップ アウトドア アニメ 赤 青 アウトドアブランド アニメコラボ 犬 イタリア 印伝 犬柄 いるびぞんて うす型 薄型 うさぎ"},
        "ct836": {"ctname": "オークション > ファッション > ファッション小物 > 財布 > 女性用 > その他", "y_ct": "2084292137","sex": "0","male": "","female": "","wowma_catid": "450802","wowma_catname": "バッグ・財布・ファッション小物＞財布＞その他財布","qoo_catid": "300002166","qoo_catname": "バッグ・雑貨_財布・ポーチ_その他","s_keyword": "メンズ 二つ折り レディース 長 人気ブランド こども 男の子 薄い 大容量 本革 ファスナー 小銭入れ無し ブランド 人気 がま口 安い かわいい 人気ブランド 人気ブランド金運 人気ブランド グリーン 緑 アウトレット  ラウンドファスナー ラビット 迷彩 札入れ 花柄 子供 ひもつき キャラクター ストラップ アウトドア アニメ 赤 青 アウトドアブランド アニメコラボ 犬 イタリア 印伝 犬柄 いるびぞんて うす型 薄型 うさぎ"},
        "ct845": {"ctname": "オークション > ファッション > ファッション小物 > 財布 > 女性用 > 長財布（小銭入れあり）", "y_ct": "2084292116","sex": "0","male": "","female": "","wowma_catid": "450807","wowma_catname": "バッグ・財布・ファッション小物＞財布＞長財布","qoo_catid": "300000112","qoo_catname": "バッグ・雑貨_財布・ポーチ_長財布","s_keyword": "二つ折り レディース 長 人気ブランド こども 男の子 薄い 大容量 本革 ファスナー 小銭入れ無し ブランド 人気 がま口 安い かわいい 人気ブランド 人気ブランド金運 人気ブランド グリーン 緑 アウトレット  ラウンドファスナー ラビット 迷彩 札入れ 花柄 子供 ひもつき キャラクター ストラップ アウトドア アニメ 赤 青 アウトドアブランド アニメコラボ 犬 イタリア 印伝 犬柄 いるびぞんて うす型 薄型 うさぎ"},
        "ct846": {"ctname": "オークション > ファッション > ファッション小物 > 財布 > 女性用 > 二つ折り財布（小銭入れあり）", "y_ct": "2084292118","sex": "0","male": "","female": "","wowma_catid": "450805","wowma_catname": "バッグ・財布・ファッション小物＞財布＞折りたたみ財布","qoo_catid": "300002164","qoo_catname": "バッグ・雑貨_財布・ポーチ_二つ折り財布","s_keyword": "二つ折り レディース 長 人気ブランド こども 男の子 薄い 大容量 本革 ファスナー 小銭入れ無し ブランド 人気 がま口 安い かわいい 人気ブランド 人気ブランド金運 人気ブランド グリーン 緑 アウトレット  ラウンドファスナー ラビット 迷彩 札入れ 花柄 子供 ひもつき キャラクター ストラップ アウトドア アニメ 赤 青 アウトドアブランド アニメコラボ 犬 イタリア 印伝 犬柄 いるびぞんて うす型 薄型 うさぎ"},
        "ct837": {"ctname": "オークション > ファッション > ファッション小物 > 財布 > 男性用 > その他", "y_ct": "2084292136","sex": "0","male": "","female": "","wowma_catid": "450802","wowma_catname": "バッグ・財布・ファッション小物＞財布＞その他財布","qoo_catid": "300002166","qoo_catname": "バッグ・雑貨_財布・ポーチ_その他","s_keyword": "メンズ 二つ折り レディース 長 人気ブランド こども 男の子 薄い 大容量 本革 ファスナー 小銭入れ無し ブランド 人気 がま口 安い かわいい 人気ブランド 人気ブランド金運 人気ブランド グリーン 緑 アウトレット  ラウンドファスナー ラビット 迷彩 札入れ 花柄 子供 ひもつき キャラクター ストラップ アウトドア アニメ 赤 青 アウトドアブランド アニメコラボ 犬 イタリア 印伝 犬柄 いるびぞんて うす型 薄型 うさぎ"},
        "ct847": {"ctname": "オークション > ファッション > ファッション小物 > 財布 > 女性用 > その他", "y_ct": "2084292137","sex": "0","male": "","female": "","wowma_catid": "450802","wowma_catname": "バッグ・財布・ファッション小物＞財布＞その他財布","qoo_catid": "300002166","qoo_catname": "バッグ・雑貨_財布・ポーチ_その他","s_keyword": "メンズ 二つ折り レディース 長 人気ブランド こども 男の子 薄い 大容量 本革 ファスナー 小銭入れ無し ブランド 人気 がま口 安い かわいい 人気ブランド 人気ブランド金運 人気ブランド グリーン 緑 アウトレット  ラウンドファスナー ラビット 迷彩 札入れ 花柄 子供 ひもつき キャラクター ストラップ アウトドア アニメ 赤 青 アウトドアブランド アニメコラボ 犬 イタリア 印伝 犬柄 いるびぞんて うす型 薄型 うさぎ"},
        "ct811": {"ctname": "オークション > ファッション > メンズシューズ > その他", "y_ct": "2084005486","sex": "0","male": "","female": "","wowma_catid": "501301","wowma_catname": "メンズファッション＞靴・シューズ＞その他靴・シューズ","qoo_catid": "300000081","qoo_catname": "メンズバッグ・シューズ・小物_メンズシューズ_その他","s_keyword": "カジュアル スニーカー 革 ビジネス スリッポン トレッキング 4e 冬 底高い 防水 幅広 人気 野球用 スニーカー白 スニーカー防水 防水防滑 ハイカット 白 ランニング 996 ウォーキング 本革 ビジネスカジュアル 小さいサイズ ヒール ロングノーズ ビジネス冬用 ビジネスブランド レザー ローカット 4e防水 スウェード 厚底 赤 雨 雪 アウトドア 暖かい イタリア 裏起毛 ウイングチップ エナメル エコー  おしゃれ"},
        "ct859": {"ctname": "オークション > ファッション > メンズシューズ > その他", "y_ct": "2084005486","sex": "0","male": "","female": "","wowma_catid": "501301","wowma_catname": "メンズファッション＞靴・シューズ＞その他靴・シューズ","qoo_catid": "300000081","qoo_catname": "メンズバッグ・シューズ・小物_メンズシューズ_その他","s_keyword": "カジュアル スニーカー 革 ビジネス スリッポン トレッキング 4e 冬 底高い 防水 幅広 人気 野球用 スニーカー白 スニーカー防水 防水防滑 ハイカット 白 ランニング 996 ウォーキング 本革 ビジネスカジュアル 小さいサイズ ヒール ロングノーズ ビジネス冬用 ビジネスブランド レザー ローカット 4e防水 スウェード 厚底 赤 雨 雪 アウトドア 暖かい イタリア 裏起毛 ウイングチップ エナメル エコー  おしゃれ"},
        "ct860": {"ctname": "オークション > ファッション > レディースシューズ > その他", "y_ct": "2084005499","sex": "0","male": "","female": "","wowma_catid": "511401","wowma_catname": "レディースファッション＞靴・シューズ＞その他靴・シューズ","qoo_catid": "300000203","qoo_catname": "スポーツ_スポーツシューズ・雑貨_レディーススポーツシューズ","s_keyword": "スニーカー 歩きやすい ローヒール スリッポン モカシン ブーツ 黒 冬 滑らない 通勤 幅広 スニーカー スニーカー 人気 歩きやすい4e 歩きやすいスニーカー 牛革 歩きやすい3e ゆりこ ローヒール牛革 ローヒールパンプス ファー 厚底 27cm 冬用 冬物 革 白 4e 厚底スニーカー 暖かい 赤 あったかい 秋冬 アウトドア アンクルブーツ かわいい ウォーキング ウェッジソール 上履き エナメル エアー エコー おしゃれ 大きめ オフィス お洒落 かかとなし"},
        "ct861": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > ベビーシューズ > スニーカー > 14cm～", "y_ct": "2084053796","sex": "0","male": "","female": "","wowma_catid": "34050701","wowma_catname": "キッズベビー・マタニティ＞ベビー＞ベビーシューズ＞その他ベビーシューズ","qoo_catid": "300000399","qoo_catname": "ベビー・マタニティ_ベビー服_ベビー靴・靴下","s_keyword": "13 12 14cm 12.5 女の子 男の子 インソール 313 996 15cm ベージュ 373 13.5 14センチ 冬 13cm 13.5cm 12cm 12.5cm 赤 w vans 14 スクスク  あったかい あったか いないいないばあ 一体型 一歳 イフミーライト 22-7701 うさぎ 上履き エアエアフォース オニツカタイガー 音が鳴る 音 かわいい おしゃれ 軽い 革 黄色 キャラクター"},
        "ct1104": {"ctname": "オークション > ファッション > レディースシューズ > その他", "y_ct": "2084005499","sex": "0","male": "","female": "","wowma_catid": "511401","wowma_catname": "レディースファッション＞靴・シューズ＞その他靴・シューズ","qoo_catid": "300000203","qoo_catname": "スポーツ_スポーツシューズ・雑貨_レディーススポーツシューズ","s_keyword": "スニーカー 歩きやすい ローヒール スリッポン モカシン ブーツ 黒 冬 滑らない 通勤 幅広 スニーカー スニーカー 人気 歩きやすい4e 歩きやすいスニーカー 牛革 歩きやすい3e ゆりこ ローヒール牛革 ローヒールパンプス ファー 厚底 27cm 冬用 冬物 革 白 4e 厚底スニーカー 暖かい 赤 あったかい 秋冬 アウトドア アンクルブーツ かわいい ウォーキング ウェッジソール 上履き エナメル エアー エコー おしゃれ 大きめ オフィス お洒落 かかとなし"},
        "ct793": {"ctname": "オークション > ファッション > ファッション小物 > スカーフ、ポケットチーフ > 女性用", "y_ct": "2084006442","sex": "0","male": "","female": "","wowma_catid": "450432","wowma_catname": "バッグ・財布・ファッション小物＞ファッション小物＞ポケットチーフ","qoo_catid": "300000123","qoo_catname": "バッグ・雑貨_スカーフ・ハンカチ_スカーフ","s_keyword": "レディース リング 大判 シルク コントローラー 赤 小さめ ブランド 冬 バッグ 黒 カシミヤ クリップ 革 レザー シルバー リングブランド 薄手 白 ロング 正方形 90 無地 冬用 黄色 綿 日本製 長方形 カレ90 ツイリー 中古 本 新品 140 ps4 ps5 コントローラーpc コントローラー本 バキ外伝 blu-ray 4k ポスター フィギュア 冨樫倫太郎 tシャツ dvd パーカー"},
        "ct1027": {"ctname": "オークション > ファッション > ファッション小物 > 手袋 > 女性用 > その他", "y_ct": "2084214886","sex": "0","male": "","female": "","wowma_catid": "450423","wowma_catname": "バッグ・財布・ファッション小物＞ファッション小物＞手袋","qoo_catid": "300002382","qoo_catname": "バッグ・雑貨_ストール・マフラー_その他","s_keyword": "防寒 レディース 暖かい スマホ対応 キッズ レディース 自転車 スマホ 防水 バイク スポーツ 指出し 薄手 大きい 革 冬 ブランド 指なし かわいい 運転 手首長め 冬用 男の子 女の子 サッカー 小さめ レザー 大きめ ハリスツイード カシミヤ 使い捨て アウトドア 赤 あったかい 赤ちゃん 穴あき インナー 犬 イラスト 家用 医療用 裏起毛 ウール うさぎ 絵本 絵描き用 園芸 液タブ エヴォログ"},
        "ct1033": {"ctname": "オークション > ファッション > ファッション小物 > ベルト > 男性用 > その他", "y_ct": "2084214922","sex": "0","male": "","female": "","wowma_catid": "450502","wowma_catname": "バッグ・財布・ファッション小物＞ベルト＞その他ベルト","qoo_catid": "300002383","qoo_catname": "バッグ・雑貨_ベルト_その他","s_keyword": "メンズ サンダー レディース カジュアル ビジネス おおきいサイズ ポーチ ブランド 穴なし おしゃれ 本革 オートロック 電動 替え 卓上 リョービ エアー アタッチメント 10mm 太め 細い ゴム 革 太 長い 白 リーバイス 編み込み ブラウン 日本製 おおきめ リバーシブル 150cm 130 160 スーツ ワイン メッシュ 作業用 小型 スマホ 防水 横型 人気 ブランドリバーシブル 3.5cm幅 交換用 バックルなし 110"},
        "ct809": {"ctname": "オークション > ファッション > ファッション小物 > キーケース", "y_ct": "2084012476","sex": "0","male": "","female": "","wowma_catid": "450406","wowma_catname": "バッグ・財布・ファッション小物＞ファッション小物＞キーケース","qoo_catid": "300000765","qoo_catname": "バッグ・雑貨_財布・ポーチ_キーケース","s_keyword": "メンズ レディース ブランド 人気 車 スマートキー スマートキー対応 革 小銭入れ付き  可愛い 名入れ 6連 グリーン 正規品 グレー 4連 安い ブランド6連 ピンク ブランドcoach 緑 カード 人気ブランド 1000円 カード入れ プルートミッキー 人気かわいい 花柄 箱あり 箱 アウトレット 赤 コイン ブランド かわいい  リレーアタック ダブル キャラクター 黒 ブラックフライデー 黄色 ブラウン アニメ アウトドア アウトドアブランド 青"},
        "ct1023": {"ctname": "オークション > ファッション > ファッション小物 > 名刺入れ、カードケース > 男性用", "y_ct": "2084246781","sex": "0","male": "","female": "","wowma_catid": "450421","wowma_catname": "バッグ・財布・ファッション小物＞ファッション小物＞名刺入れ","qoo_catid": "300002375","qoo_catname": "バッグ・雑貨_財布・ポーチ_名刺入れ・カードケース","s_keyword": "メンズ レディース ブランド 人気 革 本革 安い おしゃれ 人気ブランド 名入れ 女性 ペタルプリント ピンク 人気薄型 人気安い  ギフト 薄い スリム 黒 革製 コードバン お洒落 アルミ 赤 アルミケース アニメ アーノルドパーマー 青 アタッシュケース アウトドア 印伝 印伝屋 犬 イタリアンレザー イタリア いんでんや 薄型 うす型 うさぎ 馬革 牛 レザー エッティンガー"},
        "ct908": {"ctname": "オークション > 住まい、インテリア > 家具、インテリア > 鏡台、ドレッサー", "y_ct": "2084005506","sex": "0","male": "","female": "","wowma_catid": "29061102","wowma_catname": "おもちゃ・趣味＞アート・美術品・骨董品＞骨董品・アンティーク＞インテリア雑貨","qoo_catid": "300002932","qoo_catname": "家具・インテリア_ミラー・ドレッサー_鏡","s_keyword": "おもちゃ 女の子 テーブル コンパクト 姫系 白 化粧台 木製 卓上 プリンセス アナ アリエル 木 完成品 コンセント付き ロータイプ 安い ロー おしゃれ 鏡なし 黒 トロピカルージュ トロピカル 購入特典 トロピカルハート ハート お菓子 特典 鏡台 コスメボックス キャスター付き かわいい 子供 持ち運び ライト付き ピンク 収納 ミニ 三面鏡 ライト シンプル 女優 大容量 アナと雪の女王 アンティーク アイリスプラザ アイリス アイアン"},
        "ct909": {"ctname": "オークション > 住まい、インテリア > 家具、インテリア > カーテン、ブラインド > カーテン > その他", "y_ct": "2084238440","sex": "0","male": "","female": "","wowma_catid": "310601","wowma_catname": "インテリア・寝具＞カーテン・ブラインド＞その他カーテン・ブラインド","qoo_catid": "300000466","qoo_catname": "家具・インテリア_カーテン・ソファカバー・クッション_カーテン","s_keyword": "遮光 4枚セット 200cm丈 遮光1級 110cm丈 135cm丈 210cm丈 190cm丈 220cm丈 白 レール つっぱり式 ダブル シングル ランナー 曲がる 天井付け フック 2m つっぱり棒 150幅 200cm 安い おしゃれ 185cm リング 90mm 金属 クリップ アジャスター 75mm 70mm 50mm ステンレス レース 透けない レースセット 100cm丈 2枚 レース付き 130幅 自動 自動開閉 自動開閉装置 アレクサ タイマー 自動車 自動化 ソーラー 自動車用 幅150"},
        "ct910": {"ctname": "オークション > 住まい、インテリア > 家具、インテリア > カーテン、ブラインド > カーテン > その他", "y_ct": "2084238440","sex": "0","male": "","female": "","wowma_catid": "310601","wowma_catname": "インテリア・寝具＞カーテン・ブラインド＞その他カーテン・ブラインド","qoo_catid": "320000511","qoo_catname": "家具・インテリア_カーテン・ソファカバー・クッション_ブラインド","s_keyword": "遮光 4枚セット 200cm丈 遮光1級 110cm丈 135cm丈 210cm丈 190cm丈 220cm丈 白 レール つっぱり式 ダブル シングル ランナー 曲がる 天井付け フック 2m つっぱり棒 150幅 200cm 安い おしゃれ 185cm リング 90mm 金属 クリップ アジャスター 75mm 70mm 50mm ステンレス レース 透けない レースセット 100cm丈 2枚 レース付き 130幅 自動 自動開閉 自動開閉装置 アレクサ タイマー 自動車 自動化 ソーラー 自動車用 幅150"},
        "ct911": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > 収納、キッチン雑貨 > その他", "y_ct": "2084018482","sex": "0","male": "","female": "","wowma_catid": "35060809","wowma_catname": "キッチン・食器・調理＞キッチン用品・キッチン雑貨＞キッチン小物＞整理ボックス","qoo_catid": "300000504","qoo_catname": "キッチン用品_キッチン雑貨_その他","s_keyword": "おしゃれ レトロ 北欧 人気 カントリー アメリカン 木製 プレゼント 韓国 かわいい 赤 アンティーク アンティーク風 キッチン 椅子 イス いす ハイチェア 折りたたみ 板 インテリア キャスター ウェットシート ウォールステッカー ウォールシェルフ 浮かせる収納 ウェットティッシュ ウエットシート 受け皿 上 収納 ウォールラック ラック 延長コード 延長 防水 エプロン 絵本 映画 台 おもちゃ エイド おもしろ 可愛い キャラクター クリップ クリーナー クロス クイックル 靴"},
        "ct912": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > 収納、キッチン雑貨 > その他", "y_ct": "2084018482","sex": "0","male": "","female": "","wowma_catid": "350602","wowma_catname": "キッチン・食器・調理＞キッチン用品・キッチン雑貨＞その他キッチン用品・キッチン雑貨","qoo_catid": "300000504","qoo_catname": "キッチン用品_キッチン雑貨_その他","s_keyword": "おしゃれ レトロ 北欧 人気 カントリー アメリカン 木製 プレゼント 韓国 かわいい 赤 アンティーク アンティーク風 キッチン 椅子 イス いす ハイチェア 折りたたみ 板 インテリア キャスター ウェットシート ウォールステッカー ウォールシェルフ 浮かせる収納 ウェットティッシュ ウエットシート 受け皿 上 収納 ウォールラック ラック 延長コード 延長 防水 エプロン 絵本 映画 台 おもちゃ エイド おもしろ 可愛い キャラクター クリップ クリーナー クロス クイックル 靴"},
        "ct913": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > テーブルリネン > テーブルクロス", "y_ct": "2084046784","sex": "0","male": "","female": "","wowma_catid": "310809","wowma_catname": "インテリア・寝具＞クッション・ファブリック＞テーブルクロス","qoo_catid": "320000805","qoo_catname": "キッチン用品_キッチン雑貨_テーブルクロス","s_keyword": "円形 透明 おしゃれ 机 大きめ"},
        "ct914": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > 食器 > 洋食器 > プレート、皿 > その他", "y_ct": "2084005701","sex": "0","male": "","female": "","wowma_catid": "35120303","wowma_catname": "キッチン・食器・調理＞子供向け食器＞キッズ用食器＞プレート","qoo_catid": "300000504","qoo_catname": "キッチン用品_キッチン雑貨_その他","s_keyword": "棚 棚シート スリム 完成品 ロータイプ ひとり暮らし用 幅90 レンジ台付き ミニ 幅120 用洗剤 詰め替え エコベール 業務用 緑の魔女 ジョイ マジカ ボトル 洗剤 洗い乾燥機 セット 水切り 大容量 手に優しい 詰め替えボトル 食洗機 速乾 ディスペンサー 洗剤つめかえ大容量 つめかえ 手にやさしい 業務 無添加 キュキュットつめかえ マーチソンヒューム 工事不要 タンク式 np-tsp1 5人用 np-tsk1 コンパクト 滑り止め 35cm 45cm 40cm レース 防虫 日本製 かわいい 30cm"},
        "ct915": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > 収納、キッチン雑貨 > その他", "y_ct": "2084018482","sex": "0","male": "","female": "","wowma_catid": "350602","wowma_catname": "キッチン・食器・調理＞キッチン用品・キッチン雑貨＞その他キッチン用品・キッチン雑貨","qoo_catid": "300000504","qoo_catname": "キッチン用品_キッチン雑貨_その他","s_keyword": "おしゃれ レトロ 北欧 人気 カントリー アメリカン 木製 プレゼント 韓国 かわいい 赤 アンティーク アンティーク風 キッチン 椅子 イス いす ハイチェア 折りたたみ 板 インテリア キャスター ウェットシート ウォールステッカー ウォールシェルフ 浮かせる収納 ウェットティッシュ ウエットシート 受け皿 上 収納 ウォールラック ラック 延長コード 延長 防水 エプロン 絵本 映画 台 おもちゃ エイド おもしろ 可愛い キャラクター クリップ クリーナー クロス クイックル 靴"},
        "ct1098": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > 調理器具 > その他", "y_ct": "2084005977","sex": "0","male": "","female": "","wowma_catid": "352013","wowma_catname": "キッチン・食器・調理＞調理道具・下ごしらえ用品＞アウトドア用調理器具","qoo_catid": "320000784","qoo_catname": "キッチン用品_調理用品_調理器具","s_keyword": "キャンプ用品 セット キャンプ 便利 せっと 一人暮らし 収納 おままごと バーナー １人用 ガスコンロ コンパクト タイムセール 鍋 離乳食 アウトドア シリコン ih 包丁 入れ ケース 折りたたみ テフロン 便利グッズ 便利フライパン 便利家電 せっと一人暮らし おしゃれ ステンレス ガス 日本製 収納ケース 引き出し 収納ボックス マグネット フック 立てる 壁掛け 木製 なべセット フライパン プラスチック 人気のキャンプ用品 ランキング 子供用"},
        "ct1106": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > バス > その他", "y_ct": "2084024452","sex": "0","male": "","female": "","wowma_catid": "341110","wowma_catname": "キッズベビー・マタニティ＞子供用日用品＞子供用バスタオル","qoo_catid": "300000500","qoo_catname": "日用品雑貨_バス用品_その他","s_keyword": "タオル 今治 タオル研究所 タオルハンガー 大判 セット マイクロファイバー 安い 日本製 マット 珪藻土 速乾 タオル地 すのこ 大きめ 浴室内 おしゃれ マジックリン 詰め替え エアジェット 業務用 本体 デオクリア ソルト クナイプ クナイプ ギフト 発汗 プレゼント エプソムソルト 女性 人気 kneipp ケットボール 7号 5号 公式球 6号 屋外 ケース ケットボールシューズ ボム おもちゃ lush 子供 ボムメーカー ボムセット ボムラボ タブクレンジング"},
        "ct1037": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > スリッパ", "y_ct": "2084047779","sex": "0","male": "","female": "","wowma_catid": "350602","wowma_catname": "キッチン・食器・調理＞キッチン用品・キッチン雑貨＞その他キッチン用品・キッチン雑貨","qoo_catid": "320001616","qoo_catname": "シューズ_サンダル_スリッパ","s_keyword": "冬用 室内 メンズ あったかい ラック 来客用 冬 レディース 洗える かわいい 子供 キャラクター セット 安い 29cm 大きい 28cm 静音 28 キッズ 電熱 壁掛け スリム 木製 山崎実業 おしゃれ tower マグネット タワー 4足セット 2足セット 高級 使い捨て 5足セット 外 30cm 日本製 外履き 27 パンジー 電気 暖かい あたたかい 厚底 あったか 麻 あらえる アニマル 犬"},
        "ct916": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > タオル > その他", "y_ct": "2084006327","sex": "0","male": "","female": "","wowma_catid": "341111","wowma_catname": "キッズベビー・マタニティ＞子供用日用品＞子供用フェイスタオル","qoo_catid": "300000500","qoo_catname": "日用品雑貨_バス用品_その他","s_keyword": "ハンガー マグネット 物干し 吸盤 キッチン ステンレス アイアン 粘着 洗面所 トイレ ケット シングル ダブル セミダブル 厚手 今治 研究所 バス ボリュームリッチ 2枚 003 001 3枚 大判 毎日シンプル ライトグレー 006 フェイス 10枚 5枚 白 薄手 掛け タカラスタンダード アイアンバー ハンカチ レディース メンズ ブランド ギフト 男の子 セット かけ 強力 キャップ 子供 スイミング 大人 すみっこぐらし 女の子"},
        "ct917": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > タオル > バスタオル", "y_ct": "2084006328","sex": "0","male": "","female": "","wowma_catid": "341110","wowma_catname": "キッズベビー・マタニティ＞子供用日用品＞子供用バスタオル","qoo_catid": "300003271","qoo_catname": "日用品雑貨_バス用品_バスタオル","s_keyword": "ハンガー マグネット 物干し 吸盤 キッチン ステンレス アイアン 粘着 洗面所 トイレ ケット シングル ダブル セミダブル 厚手 今治 研究所 バス ボリュームリッチ 2枚 003 001 3枚 大判 毎日シンプル ライトグレー 006 フェイス 10枚 5枚 白 薄手 掛け タカラスタンダード アイアンバー ハンカチ レディース メンズ ブランド ギフト 男の子 セット かけ 強力 キャップ 子供 スイミング 大人 すみっこぐらし 女の子"},
        "ct919": {"ctname": "オークション > ファッション > ファッション小物 > エプロン", "y_ct": "2084018499","sex": "0","male": "","female": "","wowma_catid": "341002","wowma_catname": "キッズベビー・マタニティ＞子供用ファッション小物・雑貨＞エプロン","qoo_catid": "300003264","qoo_catname": "日用品雑貨_生活雑貨_エプロン","s_keyword": "レディース 子供 保育士 おしゃれ かわいい 大人 黒 バッグ デニム かぶるだけ 可愛い サンタ 花柄 フリル h型 お尻隠れる キャンプ 防水 料理 撥水 男の子 女の子 三角巾 セット 食事 150 130 キャラクター 長袖 無地 割烹着 新作 人気 オシャレ 北欧 キッズ お洒落 ピンク ロング お尻が隠れる 腰巻き ショート ポケット多い 仕事用 小さめ ウエストポーチ ショルダー"},
        "ct920": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > 収納、キッチン雑貨 > その他", "y_ct": "2084018482","sex": "0","male": "","female": "","wowma_catid": "350602","wowma_catname": "キッチン・食器・調理＞キッチン用品・キッチン雑貨＞その他キッチン用品・キッチン雑貨","qoo_catid": "300000504","qoo_catname": "キッチン用品_キッチン雑貨_その他","s_keyword": "おしゃれ レトロ 北欧 人気 カントリー アメリカン 木製 プレゼント 韓国 かわいい 赤 アンティーク アンティーク風 キッチン 椅子 イス いす ハイチェア 折りたたみ 板 インテリア キャスター ウェットシート ウォールステッカー ウォールシェルフ 浮かせる収納 ウェットティッシュ ウエットシート 受け皿 上 収納 ウォールラック ラック 延長コード 延長 防水 エプロン 絵本 映画 台 おもちゃ エイド おもしろ 可愛い キャラクター クリップ クリーナー クロス クイックル 靴"},
        "ct1105": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > 収納、キッチン雑貨 > その他", "y_ct": "2084018482","sex": "0","male": "","female": "","wowma_catid": "350602","wowma_catname": "キッチン・食器・調理＞キッチン用品・キッチン雑貨＞その他キッチン用品・キッチン雑貨","qoo_catid": "300000504","qoo_catname": "キッチン用品_キッチン雑貨_その他","s_keyword": "おしゃれ レトロ 北欧 人気 カントリー アメリカン 木製 プレゼント 韓国 かわいい 赤 アンティーク アンティーク風 キッチン 椅子 イス いす ハイチェア 折りたたみ 板 インテリア キャスター ウェットシート ウォールステッカー ウォールシェルフ 浮かせる収納 ウェットティッシュ ウエットシート 受け皿 上 収納 ウォールラック ラック 延長コード 延長 防水 エプロン 絵本 映画 台 おもちゃ エイド おもしろ 可愛い キャラクター クリップ クリーナー クロス クイックル 靴"},
        "ct63": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > 収納、キッチン雑貨 > その他", "y_ct": "2084018482","sex": "0","male": "","female": "","wowma_catid": "350602","wowma_catname": "キッチン・食器・調理＞キッチン用品・キッチン雑貨＞その他キッチン用品・キッチン雑貨","qoo_catid": "300000504","qoo_catname": "キッチン用品_キッチン雑貨_その他","s_keyword": "おしゃれ レトロ 北欧 人気 カントリー アメリカン 木製 プレゼント 韓国 かわいい 赤 アンティーク アンティーク風 キッチン 椅子 イス いす ハイチェア 折りたたみ 板 インテリア キャスター ウェットシート ウォールステッカー ウォールシェルフ 浮かせる収納 ウェットティッシュ ウエットシート 受け皿 上 収納 ウォールラック ラック 延長コード 延長 防水 エプロン 絵本 映画 台 おもちゃ エイド おもしろ 可愛い キャラクター クリップ クリーナー クロス クイックル 靴"},
        "ct54": {"ctname": "オークション > コンピュータ > 周辺機器 > その他", "y_ct": "2084048551","sex": "0","male": "","female": "","wowma_catid": "460502","wowma_catname": "パソコン・PC周辺機器＞キーボード・マウス・入力機器＞キーボード","qoo_catid": "320000144","qoo_catname": "楽器_ギター・ベース周辺機器_その他","s_keyword": "デスクトップ サイエンス デスクセット マウス モニター ブルートゥース スピーカー"},
        "ct56": {"ctname": "オークション > 家電、AV、カメラ > 家庭用電化製品 > その他", "y_ct": "2084061709","sex": "0","male": "","female": "","wowma_catid": "530508","wowma_catname": "家電＞キッチン家電＞オーブン","qoo_catid": "320000075","qoo_catname": "楽器_ギター_その他","s_keyword": "bluetooth マーシャル ねこみみ 有線 スタンド マイク付き ワイヤレス ノイズキャンセリング"},
        "ct922": {"ctname": "オークション > 家電、AV、カメラ > 冷暖房、空調 > 加湿器、除湿器 > 加湿器 > その他", "y_ct": "2084239049","sex": "0","male": "","female": "","wowma_catid": "532103","wowma_catname": "家電＞空気清浄機＞空気清浄機本体","qoo_catid": "320002060","qoo_catname": "季節家電_加湿器・除湿器_加湿器","s_keyword": "大容量 ハイブリッド 日本製 加熱式 上から注水 スチーム式 アロマ 業務用 タワー 卓上 人気 ランキング コードレス usb 小型 アロマ対応 充電式 かわいい 上部給水 人気ランキング大きい 6畳 スチーム 超音波 uhk-500 ハイブリッド式 空気清浄機 ダイキン 8畳 2019 象印 除菌 山善 上から給水 ダイニチ モダンデコ 除菌液 除菌タイム 除菌機能 除菌機能付き 銀 液体 アロマウォーター 除菌水 フィルター プラズマクラスター hv-p75 カートリッジ hv-p55 アロマオイル 用 ホワイトムスク"},
        "ct923": {"ctname": "オークション > 家電、AV、カメラ > 冷暖房、空調 > 扇風機", "y_ct": "2084008361","sex": "0","male": "","female": "","wowma_catid": "532103","wowma_catname": "家電＞空気清浄機＞空気清浄機本体","qoo_catid": "320002066","qoo_catname": "季節家電_扇風機・サーキュレーター_扇風機","s_keyword": "小型 クリップ カバー 壁掛け 卓上 usb dcモーター 業務用 リビング コンセント 静音 首振り 100v 山善 充電式 大型 タイマー 自動首振り リモコン カバー収納 ほこり 50cm 全体 おしゃれ 使い捨て 不織布 レトロ リモコン付き ミニ 金具 40 メカ式 ac コンセント式 強力 usb給電 マグネット サーキュレーター 日本製 dcモータータワー型 床置き dc 高さ リビング安い 微風 リビング扇 キャンプ アウトドア 暖かい アイリス"},
        "ct1977": {"ctname": "オークション > 家電、AV、カメラ > オーディオ機器 > ヘッドフォン、イヤフォン > イヤフォン > AirPodsケース", "y_ct": "2084219572","sex": "0","male": "","female": "","wowma_catid": "44060201","wowma_catname": "テレビ・オーディオ・カメラ＞ヘッドホン・イヤホン＞イヤホン＞その他イヤホン","qoo_catid": "320002462","qoo_catname": "イヤホン・ヘッドホン_イヤホン_イヤホン","s_keyword": "bluetooth マーシャル ねこみみ 有線 スタンド マイク付き ワイヤレス ノイズキャンセリング キッズ 白 ピンク ホワイト ブラウン ノイズキャンセル メジャー4 ケース こども用 ブルートゥース 水色 猫耳 黒 パッド solo3 スタジオ3 修理 イヤーパッド 無線 両用 ハイレゾ 軽量 密閉型 複数 木製 usb マグネット ２台 レイザー スイッチ対応 子供 テレビ用 ゲーミング mdr wh-1000xm3 dtm アンプ アンカー 赤 アップル 青"},
        "ct981": {"ctname": "オークション > 家電、AV、カメラ > オーディオ機器 > ヘッドフォン、イヤフォン > イヤフォン > その他", "y_ct": "2084219572","sex": "0","male": "","female": "","wowma_catid": "44060201","wowma_catname": "テレビ・オーディオ・カメラ＞ヘッドホン・イヤホン＞イヤホン＞その他イヤホン","qoo_catid": "320002280","qoo_catname": "スマートフォン・タブレットPC_スマートフォン用アクセサリー_イヤホンジャック","s_keyword": "bluetooth マーシャル ねこみみ 有線 スタンド マイク付き ワイヤレス ノイズキャンセリング キッズ 白 ピンク ホワイト ブラウン ノイズキャンセル メジャー4 ケース こども用 ブルートゥース 水色 猫耳 黒 パッド solo3 スタジオ3 修理 イヤーパッド 無線 両用 ハイレゾ 軽量 密閉型 複数 木製 usb マグネット ２台 レイザー スイッチ対応 子供 テレビ用 ゲーミング mdr wh-1000xm3 dtm アンプ アンカー 赤 アップル 青"},
        "ct513": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002216","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_iPhoneX","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct926": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone X用", "y_ct": "2084315958","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002216","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_iPhoneX","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct927": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone XS用", "y_ct": "2084316070","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002215","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_iPhone Xs","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct928": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone XS用", "y_ct": "2084316070","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002215","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_iPhone Xs","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct929": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone XS用", "y_ct": "2084316070","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002215","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_iPhone Xs","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct930": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール", "y_ct": "2084299106","sex": "0","male": "","female": "","wowma_catid": "410518","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞液晶保護フィルム","qoo_catid": "320002213","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_iPhone 11","s_keyword": "ブルーライトカット さらさら ブルーライト アンチグレア 覗き見防止 全面 指紋防止 マット 有機el ガラス 有機elモデル ホリ macbook air m1 光沢 キーボード ミヤビックス 反射防止 iphone se iphone13 iphone12 フリーサイズ iphone8 カメラ サラサラ スマホふぃるむ se2 第一世代 全面保護 第二世代 pro max mini iphone13プロ iphone12ミニ 柔らかい a4 大きい 剥がせる ノングレア 覗き見 防水 透明 非光沢 割れない プラス サンリオ"},
        "ct1330": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002213","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_iPhone 11","s_keyword": "落下防止 リング ストラップ チェーン イヤホンジャック ケース 可愛い 韓国 ポーチ 落下防止ミラー カード入れ 鏡 パッチ トラップホルダー 紛失 落下 盗難防止 ２枚 キラキラ 車 プーさんの クレヨンしんちゃん すとらっぷ トムとジェリー 話題の ハンドストラップ ハーネスベルト ふわふわ 入れ 磁石 便利 anker bts bt21 usbポート"},
        "ct1331": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > ハードケース", "y_ct": "2084306949","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002232","qoo_catname": "スマホケース・保護フィルム_その他スマホケース_多機種対応ケース","s_keyword": "落下防止 リング ストラップ チェーン イヤホンジャック ケース 可愛い 韓国 ポーチ 落下防止ミラー カード入れ 鏡 パッチ トラップホルダー 紛失 落下 盗難防止 ２枚 キラキラ 車 プーさんの クレヨンしんちゃん すとらっぷ トムとジェリー 話題の ハンドストラップ ハーネスベルト ふわふわ 入れ 磁石 便利 anker bts bt21 usbポート"},
        "ct1332": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他", "y_ct": "2084306951","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002213","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_iPhone 11","s_keyword": "落下防止 リング ストラップ チェーン イヤホンジャック ケース 可愛い 韓国 ポーチ 落下防止ミラー カード入れ 鏡 パッチ トラップホルダー 紛失 落下 盗難防止 ２枚 キラキラ 車 プーさんの クレヨンしんちゃん すとらっぷ トムとジェリー 話題の ハンドストラップ ハーネスベルト ふわふわ 入れ 磁石 便利 anker bts bt21 usbポート"},
        "ct1333": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他", "y_ct": "2084306951","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002213","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_iPhone 11","s_keyword": "落下防止 リング ストラップ チェーン イヤホンジャック ケース 可愛い 韓国 ポーチ 落下防止ミラー カード入れ 鏡 パッチ トラップホルダー 紛失 落下 盗難防止 ２枚 キラキラ 車 プーさんの クレヨンしんちゃん すとらっぷ トムとジェリー 話題の ハンドストラップ ハーネスベルト ふわふわ 入れ 磁石 便利 anker bts bt21 usbポート"},
        "ct1334": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002232","qoo_catname": "スマホケース・保護フィルム_その他スマホケース_多機種対応ケース","s_keyword": "落下防止 リング ストラップ チェーン イヤホンジャック ケース 可愛い 韓国 ポーチ 落下防止ミラー カード入れ 鏡 パッチ トラップホルダー 紛失 落下 盗難防止 ２枚 キラキラ 車 プーさんの クレヨンしんちゃん すとらっぷ トムとジェリー 話題の ハンドストラップ ハーネスベルト ふわふわ 入れ 磁石 便利 anker bts bt21 usbポート"},
        "ct1335": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール", "y_ct": "2084299106","sex": "0","male": "","female": "","wowma_catid": "410518","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞液晶保護フィルム","qoo_catid": "320002233","qoo_catname": "スマホケース・保護フィルム_保護フィルム_iPhone 保護フィルム","s_keyword": "ブルーライトカット さらさら ブルーライト アンチグレア 覗き見防止 全面 指紋防止 マット 有機el ガラス 有機elモデル ホリ macbook air m1 光沢 キーボード ミヤビックス 反射防止 iphone se iphone13 iphone12 フリーサイズ iphone8 カメラ サラサラ スマホふぃるむ se2 第一世代 全面保護 第二世代 pro max mini iphone13プロ iphone12ミニ 柔らかい a4 大きい 剥がせる ノングレア 覗き見 防水 透明 非光沢 割れない プラス サンリオ"},
        "ct1336": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002212","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_iPhone 11 Pro","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct1337": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > ハードケース", "y_ct": "2084306949","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002232","qoo_catname": "スマホケース・保護フィルム_その他スマホケース_多機種対応ケース","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct1338": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他", "y_ct": "2084306951","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002212","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_iPhone 11 Pro","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct1339": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他", "y_ct": "2084306951","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002232","qoo_catname": "スマホケース・保護フィルム_その他スマホケース_多機種対応ケース","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct1340": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002232","qoo_catname": "スマホケース・保護フィルム_その他スマホケース_多機種対応ケース","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct1341": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール", "y_ct": "2084299106","sex": "0","male": "","female": "","wowma_catid": "410518","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞液晶保護フィルム","qoo_catid": "320002212","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_iPhone 11 Pro","s_keyword": "ブルーライトカット さらさら ブルーライト アンチグレア 覗き見防止 全面 指紋防止 マット 有機el ガラス 有機elモデル ホリ macbook air m1 光沢 キーボード ミヤビックス 反射防止 iphone se iphone13 iphone12 フリーサイズ iphone8 カメラ サラサラ スマホふぃるむ se2 第一世代 全面保護 第二世代 pro max mini iphone13プロ iphone12ミニ 柔らかい a4 大きい 剥がせる ノングレア 覗き見 防水 透明 非光沢 割れない プラス サンリオ"},
        "ct1342": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002211","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_iPhone 11 Pro Max","s_keyword": "落下防止 リング ストラップ チェーン イヤホンジャック ケース 可愛い 韓国 ポーチ 落下防止ミラー カード入れ 鏡 パッチ トラップホルダー 紛失 落下 盗難防止 ２枚 キラキラ 車 プーさんの クレヨンしんちゃん すとらっぷ トムとジェリー 話題の ハンドストラップ ハーネスベルト ふわふわ 入れ 磁石 便利 anker bts bt21 usbポート"},
        "ct1343": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > ハードケース", "y_ct": "2084306949","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002243","qoo_catname": "スマホケース・保護フィルム_保護フィルム_多機種対応保護フィルム","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct1344": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他", "y_ct": "2084306951","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002211","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_iPhone 11 Pro Max","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct1345": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他", "y_ct": "2084306951","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002232","qoo_catname": "スマホケース・保護フィルム_その他スマホケース_多機種対応ケース","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct1346": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002232","qoo_catname": "スマホケース・保護フィルム_その他スマホケース_多機種対応ケース","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct1347": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール", "y_ct": "2084299106","sex": "0","male": "","female": "","wowma_catid": "410518","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞液晶保護フィルム","qoo_catid": "320002243","qoo_catname": "スマホケース・保護フィルム_保護フィルム_多機種対応保護フィルム","s_keyword": "ブルーライトカット さらさら ブルーライト アンチグレア 覗き見防止 全面 指紋防止 マット 有機el ガラス 有機elモデル ホリ macbook air m1 光沢 キーボード ミヤビックス 反射防止 iphone se iphone13 iphone12 フリーサイズ iphone8 カメラ サラサラ スマホふぃるむ se2 第一世代 全面保護 第二世代 pro max mini iphone13プロ iphone12ミニ 柔らかい a4 大きい 剥がせる ノングレア 覗き見 防水 透明 非光沢 割れない プラス サンリオ"},
        "ct924": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002217","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_iPhone XR","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct931": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone XR用", "y_ct": "2084316072","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002217","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_iPhone XR","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct932": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone XR用", "y_ct": "2084316072","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002217","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_iPhone XR","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct933": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone XR用", "y_ct": "2084316072","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002217","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_iPhone XR","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct934": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002217","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_iPhone XR","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct935": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール", "y_ct": "2084299106","sex": "0","male": "","female": "","wowma_catid": "410518","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞液晶保護フィルム","qoo_catid": "320002243","qoo_catname": "スマホケース・保護フィルム_保護フィルム_多機種対応保護フィルム","s_keyword": "ブルーライトカット さらさら ブルーライト アンチグレア 覗き見防止 全面 指紋防止 マット 有機el ガラス 有機elモデル ホリ macbook air m1 光沢 キーボード ミヤビックス 反射防止 iphone se iphone13 iphone12 フリーサイズ iphone8 カメラ サラサラ スマホふぃるむ se2 第一世代 全面保護 第二世代 pro max mini iphone13プロ iphone12ミニ 柔らかい a4 大きい 剥がせる ノングレア 覗き見 防水 透明 非光沢 割れない プラス サンリオ"},
        "ct925": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002214","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_iPhone Xs Max","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct936": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone XS Max用", "y_ct": "2084316071","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002214","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_iPhone Xs Max","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct937": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone XS Max用", "y_ct": "2084316071","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002214","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_iPhone Xs Max","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct938": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone XS Max用", "y_ct": "2084316071","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002214","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_iPhone Xs Max","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct939": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002232","qoo_catname": "スマホケース・保護フィルム_その他スマホケース_多機種対応ケース","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct940": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール", "y_ct": "2084299106","sex": "0","male": "","female": "","wowma_catid": "410518","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞液晶保護フィルム","qoo_catid": "320002243","qoo_catname": "スマホケース・保護フィルム_保護フィルム_多機種対応保護フィルム","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct68": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002219","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_その他 iPhone ケース","s_keyword": "ブルーライトカット さらさら ブルーライト アンチグレア 覗き見防止 全面 指紋防止 マット 有機el ガラス 有機elモデル ホリ macbook air m1 光沢 キーボード ミヤビックス 反射防止 iphone se iphone13 iphone12 フリーサイズ iphone8 カメラ サラサラ スマホふぃるむ se2 第一世代 全面保護 第二世代 pro max mini iphone13プロ iphone12ミニ 柔らかい a4 大きい 剥がせる ノングレア 覗き見 防水 透明 非光沢 割れない プラス サンリオ"},
        "ct941": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 7 Plus/8 Plus用", "y_ct": "2084315957","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002219","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_その他 iPhone ケース","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct942": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 7 Plus/8 Plus用", "y_ct": "2084315957","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002219","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_その他 iPhone ケース","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct943": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 7 Plus/8 Plus用", "y_ct": "2084315957","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002219","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_その他 iPhone ケース","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct944": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002219","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_その他 iPhone ケース","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct945": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール", "y_ct": "2084299106","sex": "0","male": "","female": "","wowma_catid": "410518","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞液晶保護フィルム","qoo_catid": "320002243","qoo_catname": "スマホケース・保護フィルム_保護フィルム_多機種対応保護フィルム","s_keyword": "ブルーライトカット さらさら ブルーライト アンチグレア 覗き見防止 全面 指紋防止 マット 有機el ガラス 有機elモデル ホリ macbook air m1 光沢 キーボード ミヤビックス 反射防止 iphone se iphone13 iphone12 フリーサイズ iphone8 カメラ サラサラ スマホふぃるむ se2 第一世代 全面保護 第二世代 pro max mini iphone13プロ iphone12ミニ 柔らかい a4 大きい 剥がせる ノングレア 覗き見 防水 透明 非光沢 割れない プラス サンリオ"},
        "ct65": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002243","qoo_catname": "スマホケース・保護フィルム_保護フィルム_多機種対応保護フィルム","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct946": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 7/8用", "y_ct": "2084315956","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002219","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_その他 iPhone ケース","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct947": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 7/8用", "y_ct": "2084315956","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002219","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_その他 iPhone ケース","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct948": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 7/8用", "y_ct": "2084315956","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002219","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_その他 iPhone ケース","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct949": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002219","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_その他 iPhone ケース","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct950": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール", "y_ct": "2084299106","sex": "0","male": "","female": "","wowma_catid": "410518","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞液晶保護フィルム","qoo_catid": "320002243","qoo_catname": "スマホケース・保護フィルム_保護フィルム_多機種対応保護フィルム","s_keyword": "ブルーライトカット さらさら ブルーライト アンチグレア 覗き見防止 全面 指紋防止 マット 有機el ガラス 有機elモデル ホリ macbook air m1 光沢 キーボード ミヤビックス 反射防止 iphone se iphone13 iphone12 フリーサイズ iphone8 カメラ サラサラ スマホふぃるむ se2 第一世代 全面保護 第二世代 pro max mini iphone13プロ iphone12ミニ 柔らかい a4 大きい 剥がせる ノングレア 覗き見 防水 透明 非光沢 割れない プラス サンリオ"},
        "ct75": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002219","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_その他 iPhone ケース","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct951": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 6 Plus/6s Plus用", "y_ct": "2084314669","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002219","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_その他 iPhone ケース","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct952": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 6 Plus/6s Plus用", "y_ct": "2084314669","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002219","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_その他 iPhone ケース","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct953": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 6 Plus/6s Plus用", "y_ct": "2084314669","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002219","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_その他 iPhone ケース","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct954": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002219","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_その他 iPhone ケース","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct955": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール", "y_ct": "2084299106","sex": "0","male": "","female": "","wowma_catid": "410518","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞液晶保護フィルム","qoo_catid": "320002243","qoo_catname": "スマホケース・保護フィルム_保護フィルム_多機種対応保護フィルム","s_keyword": "ブルーライトカット さらさら ブルーライト アンチグレア 覗き見防止 全面 指紋防止 マット 有機el ガラス 有機elモデル ホリ macbook air m1 光沢 キーボード ミヤビックス 反射防止 iphone se iphone13 iphone12 フリーサイズ iphone8 カメラ サラサラ スマホふぃるむ se2 第一世代 全面保護 第二世代 pro max mini iphone13プロ iphone12ミニ 柔らかい a4 大きい 剥がせる ノングレア 覗き見 防水 透明 非光沢 割れない プラス サンリオ"},
        "ct72": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002219","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_その他 iPhone ケース","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct956": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 6 Plus/6s Plus用", "y_ct": "2084314669","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002219","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_その他 iPhone ケース","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct957": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 6 Plus/6s Plus用", "y_ct": "2084314669","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002219","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_その他 iPhone ケース","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct958": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 6 Plus/6s Plus用", "y_ct": "2084314669","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002219","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_その他 iPhone ケース","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct959": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002219","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_その他 iPhone ケース","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct960": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール", "y_ct": "2084299106","sex": "0","male": "","female": "","wowma_catid": "410518","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞液晶保護フィルム","qoo_catid": "320002243","qoo_catname": "スマホケース・保護フィルム_保護フィルム_多機種対応保護フィルム","s_keyword": "ブルーライトカット さらさら ブルーライト アンチグレア 覗き見防止 全面 指紋防止 マット 有機el ガラス 有機elモデル ホリ macbook air m1 光沢 キーボード ミヤビックス 反射防止 iphone se iphone13 iphone12 フリーサイズ iphone8 カメラ サラサラ スマホふぃるむ se2 第一世代 全面保護 第二世代 pro max mini iphone13プロ iphone12ミニ 柔らかい a4 大きい 剥がせる ノングレア 覗き見 防水 透明 非光沢 割れない プラス サンリオ"},
        "ct69": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002219","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_その他 iPhone ケース","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct961": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 5用", "y_ct": "2084308386","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002219","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_その他 iPhone ケース","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct962": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 5用", "y_ct": "2084308386","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002219","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_その他 iPhone ケース","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct963": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 5用", "y_ct": "2084308386","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002219","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_その他 iPhone ケース","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct964": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002219","qoo_catname": "スマホケース・保護フィルム_iPhoneケース_その他 iPhone ケース","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct965": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール", "y_ct": "2084299106","sex": "0","male": "","female": "","wowma_catid": "410518","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞液晶保護フィルム","qoo_catid": "320002243","qoo_catname": "スマホケース・保護フィルム_保護フィルム_多機種対応保護フィルム","s_keyword": "ブルーライトカット さらさら ブルーライト アンチグレア 覗き見防止 全面 指紋防止 マット 有機el ガラス 有機elモデル ホリ macbook air m1 光沢 キーボード ミヤビックス 反射防止 iphone se iphone13 iphone12 フリーサイズ iphone8 カメラ サラサラ スマホふぃるむ se2 第一世代 全面保護 第二世代 pro max mini iphone13プロ iphone12ミニ 柔らかい a4 大きい 剥がせる ノングレア 覗き見 防水 透明 非光沢 割れない プラス サンリオ"},
        "ct76": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002232","qoo_catname": "スマホケース・保護フィルム_その他スマホケース_多機種対応ケース","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct966": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > ハードケース", "y_ct": "2084306949","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002232","qoo_catname": "スマホケース・保護フィルム_その他スマホケース_多機種対応ケース","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct967": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他", "y_ct": "2084306951","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002232","qoo_catname": "スマホケース・保護フィルム_その他スマホケース_多機種対応ケース","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct968": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他", "y_ct": "2084306951","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002232","qoo_catname": "スマホケース・保護フィルム_その他スマホケース_多機種対応ケース","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct969": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002283","qoo_catname": "スマートフォン・タブレットPC_スマートフォン用アクセサリー_その他スマートフォン用アクセサリー","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct970": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール", "y_ct": "2084299106","sex": "0","male": "","female": "","wowma_catid": "410518","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞液晶保護フィルム","qoo_catid": "320002243","qoo_catname": "スマホケース・保護フィルム_保護フィルム_多機種対応保護フィルム","s_keyword": "ブルーライトカット さらさら ブルーライト アンチグレア 覗き見防止 全面 指紋防止 マット 有機el ガラス 有機elモデル ホリ macbook air m1 光沢 キーボード ミヤビックス 反射防止 iphone se iphone13 iphone12 フリーサイズ iphone8 カメラ サラサラ スマホふぃるむ se2 第一世代 全面保護 第二世代 pro max mini iphone13プロ iphone12ミニ 柔らかい a4 大きい 剥がせる ノングレア 覗き見 防水 透明 非光沢 割れない プラス サンリオ"},
        "ct516": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002220","qoo_catname": "スマホケース・保護フィルム_その他スマホケース_GALAXY ケース","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct971": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > ハードケース", "y_ct": "2084306949","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002232","qoo_catname": "スマホケース・保護フィルム_その他スマホケース_多機種対応ケース","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct972": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他", "y_ct": "2084306951","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002232","qoo_catname": "スマホケース・保護フィルム_その他スマホケース_多機種対応ケース","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct973": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他", "y_ct": "2084306951","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002232","qoo_catname": "スマホケース・保護フィルム_その他スマホケース_多機種対応ケース","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct974": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002283","qoo_catname": "スマートフォン・タブレットPC_スマートフォン用アクセサリー_その他スマートフォン用アクセサリー","s_keyword": "iphone12 mini 手帳型 韓国 max iphone12ミニ 透明 かわいい iphone se se2 ifリング付き iphone13 pro iphone13ミニ iphone13プロ iphonese2 耐衝撃 キャラクター シリコン iphone8 iphone8プラス おしゃれ クリア xr カード収納 第二世代 トムとジェリー セーラームーン sense3 iphone7 iphone7プラス x xs iphone11 8 ペア アンドロイド アニメ あんどろいど 全機種対応 あくおす sense4 あいほん11 sense6 アイフェイス アローズ sense5g 犬"},
        "ct975": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール", "y_ct": "2084299106","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002243","qoo_catname": "スマホケース・保護フィルム_保護フィルム_多機種対応保護フィルム","s_keyword": "ブルーライトカット さらさら ブルーライト アンチグレア 覗き見防止 全面 指紋防止 マット 有機el ガラス 有機elモデル ホリ macbook air m1 光沢 キーボード ミヤビックス 反射防止 iphone se iphone13 iphone12 フリーサイズ iphone8 カメラ サラサラ スマホふぃるむ se2 第一世代 全面保護 第二世代 pro max mini iphone13プロ iphone12ミニ 柔らかい a4 大きい 剥がせる ノングレア 覗き見 防水 透明 非光沢 割れない プラス サンリオ"},
        "ct78": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー", "y_ct": "2084005062","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002283","qoo_catname": "スマートフォン・タブレットPC_スマートフォン用アクセサリー_その他スマートフォン用アクセサリー","s_keyword": "落下防止 リング ストラップ チェーン イヤホンジャック ケース 可愛い 韓国 ポーチ 落下防止ミラー カード入れ 鏡 パッチ トラップホルダー 紛失 落下 盗難防止 ２枚 キラキラ 車 プーさんの クレヨンしんちゃん すとらっぷ トムとジェリー 話題の ハンドストラップ ハーネスベルト ふわふわ 入れ 磁石 便利 anker bts bt21 usbポート"},
        "ct976": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002283","qoo_catname": "スマートフォン・タブレットPC_スマートフォン用アクセサリー_その他スマートフォン用アクセサリー","s_keyword": "落下防止 リング ストラップ チェーン イヤホンジャック ケース 可愛い 韓国 ポーチ 落下防止ミラー カード入れ 鏡 パッチ トラップホルダー 紛失 落下 盗難防止 ２枚 キラキラ 車 プーさんの クレヨンしんちゃん すとらっぷ トムとジェリー 話題の ハンドストラップ ハーネスベルト ふわふわ 入れ 磁石 便利 anker bts bt21 usbポート"},
        "ct977": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002283","qoo_catname": "スマートフォン・タブレットPC_スマートフォン用アクセサリー_その他スマートフォン用アクセサリー","s_keyword": "落下防止 リング ストラップ チェーン イヤホンジャック ケース 可愛い 韓国 ポーチ 落下防止ミラー カード入れ 鏡 パッチ トラップホルダー 紛失 落下 盗難防止 ２枚 キラキラ 車 プーさんの クレヨンしんちゃん すとらっぷ トムとジェリー 話題の ハンドストラップ ハーネスベルト ふわふわ 入れ 磁石 便利 anker bts bt21 usbポート"},
        "ct978": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002283","qoo_catname": "スマートフォン・タブレットPC_スマートフォン用アクセサリー_その他スマートフォン用アクセサリー","s_keyword": "落下防止 リング ストラップ チェーン イヤホンジャック ケース 可愛い 韓国 ポーチ 落下防止ミラー カード入れ 鏡 パッチ トラップホルダー 紛失 落下 盗難防止 ２枚 キラキラ 車 プーさんの クレヨンしんちゃん すとらっぷ トムとジェリー 話題の ハンドストラップ ハーネスベルト ふわふわ 入れ 磁石 便利 anker bts bt21 usbポート"},
        "ct979": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002283","qoo_catname": "スマートフォン・タブレットPC_スマートフォン用アクセサリー_その他スマートフォン用アクセサリー","s_keyword": "落下防止 リング ストラップ チェーン イヤホンジャック ケース 可愛い 韓国 ポーチ 落下防止ミラー カード入れ 鏡 パッチ トラップホルダー 紛失 落下 盗難防止 ２枚 キラキラ 車 プーさんの クレヨンしんちゃん すとらっぷ トムとジェリー 話題の ハンドストラップ ハーネスベルト ふわふわ 入れ 磁石 便利 anker bts bt21 usbポート"},
        "ct980": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002283","qoo_catname": "スマートフォン・タブレットPC_スマートフォン用アクセサリー_その他スマートフォン用アクセサリー","s_keyword": "落下防止 リング ストラップ チェーン イヤホンジャック ケース 可愛い 韓国 ポーチ 落下防止ミラー カード入れ 鏡 パッチ トラップホルダー 紛失 落下 盗難防止 ２枚 キラキラ 車 プーさんの クレヨンしんちゃん すとらっぷ トムとジェリー 話題の ハンドストラップ ハーネスベルト ふわふわ 入れ 磁石 便利 anker bts bt21 usbポート"},
        "ct32": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062","sex": "0","male": "","female": "","wowma_catid": "410509","wowma_catname": "スマホ・タブレット・モバイル通信＞スマホアクセサリー＞スマホケース","qoo_catid": "320002283","qoo_catname": "スマートフォン・タブレットPC_スマートフォン用アクセサリー_その他スマートフォン用アクセサリー","s_keyword": "落下防止 リング ストラップ チェーン イヤホンジャック ケース 可愛い 韓国 ポーチ 落下防止ミラー カード入れ 鏡 パッチ トラップホルダー 紛失 落下 盗難防止 ２枚 キラキラ 車 プーさんの クレヨンしんちゃん すとらっぷ トムとジェリー 話題の ハンドストラップ ハーネスベルト ふわふわ 入れ 磁石 便利 anker bts bt21 usbポート"},
        "ct10": {"ctname": "オークション > 事務、店舗用品 > 文房具 > その他", "y_ct": "2084042489","sex": "0","male": "","female": "","wowma_catid": "54090201","wowma_catname": "日用品・文房具・手芸用品＞手芸・クラフト・生地＞その他手芸用品＞その他","qoo_catid": "300000532","qoo_catname": "文具_文房具_その他","s_keyword": "セット 女の子 便利 小学生 最新 収納 大人 男の子 高学年 おしゃれ オシャレ 可愛い 500円 小学生おしゃれ大きい 小学生1000円 プレゼントユニコーン タピオカ プレゼント交換 商品 ペンケース ペン 商品ペン 最新アマゾン ノート 本 筆箱 人気 ベストセラー 人気学校で使える ベストセラー中学生 ベストセラー大人 便利グッズ ファイル プリンセス すみっこぐらし かわいい ユニコーン 最新小学生 最新セット 持ち運び バッグ 引き出し 卓上 ポーチ 自立 仕切り おもしろい アニメ"},
        "ct57": {"ctname": "オークション > 事務、店舗用品 > 文房具 > その他", "y_ct": "2084042489","sex": "0","male": "","female": "","wowma_catid": "54090201","wowma_catname": "日用品・文房具・手芸用品＞手芸・クラフト・生地＞その他手芸用品＞その他","qoo_catid": "300000532","qoo_catname": "文具_文房具_その他","s_keyword": "セット 女の子 便利 小学生 最新 収納 大人 男の子 高学年 おしゃれ オシャレ 可愛い 500円 小学生おしゃれ大きい 小学生1000円 プレゼントユニコーン タピオカ プレゼント交換 商品 ペンケース ペン 商品ペン 最新アマゾン ノート 本 筆箱 人気 ベストセラー 人気学校で使える ベストセラー中学生 ベストセラー大人 便利グッズ ファイル プリンセス すみっこぐらし かわいい ユニコーン 最新小学生 最新セット 持ち運び バッグ 引き出し 卓上 ポーチ 自立 仕切り おもしろい アニメ"},
        "ct17": {"ctname": "ヘルス/ビューティー", "y_ct": "2084042545","sex": "0","male": "","female": "","wowma_catid": "471101","wowma_catname": "ビューティ・コスメ＞ボディケア＞その他ボディケア","qoo_catid": "320001859","qoo_catname": "ダイエット・矯正_シェイプアップ・ダイエットグッズ_エクササイズグッズ","s_keyword": "マッサージ 腰 首 背中 ツボ 肩甲骨 ふくらはぎ 太もも おしゃれ 女性 メンズ お腹 脚やせ 男性 効果大 人気 脚やせ 男性 女性 プレゼント 下腹 "},
        "ct982": {"ctname": "ヘルス/ビューティー > 健康グッズ", "y_ct": "2084042545","sex": "0","male": "","female": "","wowma_catid": "471101","wowma_catname": "ビューティ・コスメ＞ボディケア＞その他ボディケア","qoo_catid": "320001859","qoo_catname": "ダイエット・矯正_シェイプアップ・ダイエットグッズ_エクササイズグッズ","s_keyword": "マッサージ 腰 首 背中 ツボ 肩甲骨 ふくらはぎ 太もも おしゃれ 女性 メンズ お腹 脚やせ 男性 効果大 人気 脚やせ 男性 女性 プレゼント 下腹 "},
        "ct95": {"ctname": "ヘルス/ビューティー > ダイエットグッズ", "y_ct": "2084006890","sex": "0","male": "","female": "","wowma_catid": "471101","wowma_catname": "ビューティ・コスメ＞ボディケア＞その他ボディケア","qoo_catid": "320001859","qoo_catname": "ダイエット・矯正_シェイプアップ・ダイエットグッズ_エクササイズグッズ","s_keyword": "マッサージ 腰 首 背中 ツボ 肩甲骨 ふくらはぎ 太もも おしゃれ 女性 メンズ お腹 脚やせ 男性 効果大 人気 脚やせ 男性 女性 プレゼント 下腹 "},
        "ct1103": {"ctname": "オークション > 家電、AV、カメラ > 美容、健康 > 美容機器 > ネイルケア", "y_ct": "2084055371","sex": "0","male": "","female": "","wowma_catid": "470708","wowma_catname": "ビューティ・コスメ＞ネイル＞ネイルケアグッズ","qoo_catid": "320002118","qoo_catname": "美容・健康家電_ネイルケア家電_電動ネイルケア","s_keyword": "顔 スチーマー ジェル 用ジェル 目元 スチーム 法令線 小顔 脱毛 訳あり ブランド カート キャビテーション ピコレーザー シミ 肝斑 青色レーザー 赤色レーザー 美容レーザー ほくろ除去 110v 毛穴 コンセントタイプ 入浴 脱毛器 レディース ipl光脱毛器 60万回照射 5段階 光美容器 永久脱毛 無痛脱毛 全身ムダ毛処理 美肌機能付き 母の日のプレゼント 本 光 やーまん メンズ 目 リフトアップ ems リファビューテック ストレートアイロン レア髪 美容 ヘアケア iroil2103 rwc21"},
        "ct13": {"ctname": "オークション > スポーツ、レジャー > キャンプ、アウトドア用品 > その他", "y_ct": "2084005102","sex": "0","male": "","female": "","wowma_catid": "40110501","wowma_catname": "スポーツ・アウトドア＞アウトドア＞アウトドア用品＞その他アウトドア用品","qoo_catid": "300000240","qoo_catname": "アウトドア_キャンプ用品_その他","s_keyword": "調理器具 キャンプ用品 人気 テント テーブル 便利 キャンプ ローテーブル キャンプ用品コンロ タープ 人気シングルバーナー 便利グッズ バーナー プレゼント 椅子 アルコールストーブ アウトドア用 温度計 カップ かご かまど キャリー 車 クッカー 靴 ケトル コーヒーミル コンロ 小物 コップ コット コンパクトバーナー ふるさと納税 kh-100bk snow peak アウトドア 128p002 set-111 051p001 缶クーラー350 tw-355 011p027 食器 収納袋 収納"},
        "ct1046": {"ctname": "オークション > スポーツ、レジャー > アウトドアウエア > 服飾小物 > その他", "y_ct": "2084057246","sex": "0","male": "","female": "","wowma_catid": "40110501","wowma_catname": "スポーツ・アウトドア＞アウトドア＞アウトドア用品＞その他アウトドア用品","qoo_catid": "300000239","qoo_catname": "アウトドア_登山用品_その他","s_keyword": "メンズ 冬 レディース冬 レディース 上下 レディース ブランド メンズ 洗剤 キッズ アウトドア 防寒対策 5つヒーター pse認証済 ブレスサーモ  ユニセックス"},
        "ct73": {"ctname": "医療・介護・医薬品＞介護・福祉＞その他生活グッズ＞サポーター", "y_ct": "2084063134","sex": "0","male": "","female": "","wowma_catid": "52010202","wowma_catname": "医療・介護・医薬品＞介護・福祉＞その他生活グッズ＞サポーター","qoo_catid": "320001860","qoo_catname": "ダイエット・矯正_矯正・マッサージ_姿勢矯正","s_keyword": "腰痛 妊婦 大きいサイズ 矯正 高齢者 メンズ"},
        "ct983": {"ctname": "オークション > スポーツ、レジャー > キャンプ、アウトドア用品 > 雨具、レインウエア > その他", "y_ct": "2084208701","sex": "0","male": "","female": "","wowma_catid": "401101","wowma_catname": "スポーツ・アウトドア＞アウトドア＞その他アウトドア","qoo_catid": "300000240","qoo_catname": "アウトドア_キャンプ用品_その他","s_keyword": "メンズ 上下 自転車 ズボン ポンチョ 人気のカッパ ランキング カッパ レディース 作業 作業マリン 登山 バイク リュック 防寒 リュック対応 撥水加工 レッグカバー バイザー 下 上 防水 キッズ 透明 軽量 使い捨て 150 ポンチョリュック 車椅子 子供 ランキング女子 カッパズボン カッパ子供 カッパ5l 小学生 上下セット s 小さめ おしゃれ リュックサック 160 スポーツ 帽子 足元カバー アウトドア 頭 足 足首 足カバー"},
        "ct984": {"ctname": "ダイエット・健康＞抗菌・除菌グッズ＞マスク＞その他マスク", "y_ct": "2084063121","sex": "0","male": "","female": "","wowma_catid": "42080499","wowma_catname": "ダイエット・健康＞抗菌・除菌グッズ＞マスク＞その他マスク","qoo_catid": "300000521","qoo_catname": "日用品雑貨_衛生用品_マスク","s_keyword": "不織布 日本製 立体 マスクケース 大きめ 携帯用 使い捨て 洗える ブラック 耳が痛くならない"},
        "ct987": {"ctname": "オークション > スポーツ、レジャー > キャンプ、アウトドア用品 > その他", "y_ct": "2084005102","sex": "0","male": "","female": "","wowma_catid": "401101","wowma_catname": "スポーツ・アウトドア＞アウトドア＞その他アウトドア","qoo_catid": "300000240","qoo_catname": "アウトドア_キャンプ用品_その他","s_keyword": "調理器具 キャンプ用品 人気 テント テーブル 便利 キャンプ ローテーブル キャンプ用品コンロ タープ 人気シングルバーナー 便利グッズ バーナー プレゼント 椅子 アルコールストーブ アウトドア用 温度計 カップ かご かまど キャリー 車 クッカー 靴 ケトル コーヒーミル コンロ 小物 コップ コット コンパクトバーナー ふるさと納税 kh-100bk snow peak アウトドア 128p002 set-111 051p001 缶クーラー350 tw-355 011p027 食器 収納袋 収納"},
        "ct999": {"ctname": "オークション > おもちゃ、ゲーム > 水遊び > ビーチボール", "y_ct": "2084042424","sex": "0","male": "","female": "","wowma_catid": "401101","wowma_catname": "スポーツ・アウトドア＞アウトドア＞その他アウトドア","qoo_catid": "320000272","qoo_catname": "スポーツ_水泳・水着・マリンスポーツ_その他","s_keyword": "巨大 30cm 50cm バレー 40cm 透明 日本語 サッカー 日本語表記 5点セット ビック ひらがな 公式球 バレーボール バレー公式ボール ウエア 東京 冬用 スイカ アメリカ アニメ イガラシ インテックス 犬 宇宙 大きい おもちゃ おしゃれ 大きめ かわいい 韓国 キャラクター キラキラ キティ 恐竜 黄色 空気入れ 黒 アダプター クリア 公認球 子供 公式 小型 子ども サイコロ 白 小"},
        "ct12": {"ctname": "オークション > 自動車、オートバイ > オートバイ > オートバイ関連グッズ > その他", "y_ct": "2084019984","sex": "0","male": "","female": "","wowma_catid": "336718","wowma_catname": "カー用品・バイク用品＞バイクパーツ＞その他バイクパーツ","qoo_catid": "300000253","qoo_catname": "カー用品_バイク用品_その他","s_keyword": "オートバイ 便利グッズ オートバイ防寒グッズ"},
        "ct64": {"ctname": "オークション > 自動車、オートバイ > アクセサリー > エンブレム > その他", "y_ct": "2084203148","sex": "0","male": "","female": "","wowma_catid": "336401","wowma_catname": "カー用品・バイク用品＞カー用品＞カーアクセサリー","qoo_catid": "320000294","qoo_catname": "カー用品_バイク用品_アクセサリー","s_keyword": "ステッカー 剥がし 車 シール バイク ブラック 赤 黒 クラシック モンキー ハンドル ウイング 82mm カーボン xdrive m 筆記体 led マットブラック フロント カタカナ ハイヴォクシー 猫 キャラクター ムーミン 剥がしキット エーモン 糸 ドリル 剥がしスプレー カスタム アルファベット 車金属 うさぎ マツダ カニ ボディ pc windows xeon intel dvd amd パソコン 人気の車 トヨタランキング"},
        "ct66": {"ctname": "オークション > 自動車、オートバイ > カーナビ > 液晶保護フィルム、カバー > その他", "y_ct": "2084286642","sex": "0","male": "","female": "","wowma_catid": "336403","wowma_catname": "カー用品・バイク用品＞カー用品＞カーナビ・カーオーディオ","qoo_catid": "320000294","qoo_catname": "カー用品_バイク用品_アクセサリー","s_keyword": "ブルーライトカット さらさら ブルーライト アンチグレア 覗き見防止 全面 指紋防止 マット 有機el ガラス 有機elモデル ホリ macbook air m1 光沢 キーボード ミヤビックス 反射防止 iphone se iphone13 iphone12 フリーサイズ iphone8 カメラ サラサラ スマホふぃるむ se2 第一世代 全面保護 第二世代 pro max mini iphone13プロ iphone12ミニ 柔らかい a4 大きい 剥がせる ノングレア 覗き見 防水 透明 非光沢 割れない プラス サンリオ"},
        "ct991": {"ctname": "オークション > 自動車、オートバイ > オートバイ > オートバイ関連グッズ > その他", "y_ct": "2084019984","sex": "0","male": "","female": "","wowma_catid": "336718","wowma_catname": "カー用品・バイク用品＞バイクパーツ＞その他バイクパーツ","qoo_catid": "300000253","qoo_catname": "カー用品_バイク用品_その他","s_keyword": "オートバイ 便利グッズ オートバイ防寒グッズ"},
        "ct992": {"ctname": "オークション > 自動車、オートバイ > オートバイ > オートバイ関連グッズ > その他", "y_ct": "2084019984","sex": "0","male": "","female": "","wowma_catid": "336718","wowma_catname": "カー用品・バイク用品＞バイクパーツ＞その他バイクパーツ","qoo_catid": "300000253","qoo_catname": "カー用品_バイク用品_その他","s_keyword": "オートバイ 便利グッズ オートバイ防寒グッズ"},
        "ct67": {"ctname": "オークション > 自動車、オートバイ > オートバイ > オートバイ関連グッズ > その他", "y_ct": "2084019984","sex": "0","male": "","female": "","wowma_catid": "336718","wowma_catname": "カー用品・バイク用品＞バイクパーツ＞その他バイクパーツ","qoo_catid": "300000253","qoo_catname": "カー用品_バイク用品_その他","s_keyword": "オートバイ 便利グッズ オートバイ防寒グッズ"},
        "ct1116": {"ctname": "オークション > ファッション > レディースファッション > マタニティウエア", "y_ct": "2084006309","sex": "0","male": "","female": "","wowma_catid": "34060401","wowma_catname": "キッズベビー・マタニティ＞マタニティ・ママ＞マタニティウエア＞Tシャツ","qoo_catid": "300000379","qoo_catname": "ベビー・マタニティ_マタニティ_マタニティウェア","s_keyword": "レギンス パジャマ ショーツ レギンス ズボン タイツ ブラ 長袖 冬パジャマ 裏起毛 大きいサイズ 前開き ワンピース 夏パジャマ ローライズショーツ セットショーツ 綿100 ハイウエストショーツ シームレスショーツ "},
        "ct993": {"ctname": "オークション > おもちゃ、ゲーム > 手品、パーティグッズ > パーティグッズ > その他", "y_ct": "2084059858", "sex": "0",
                  "male": "", "female": "", "wowma_catid": "291501", "wowma_catname": "おもちゃ・趣味>パーティーグッズ>その他パーティーグッズ",
                  "qoo_catid": "300000702", "qoo_catname": "ホビー・コスプレ_パーティー・イベント用品_その他",
                  "s_keyword": "おもしろ 誕生日 メガネ マスク びっくり ひげ 被り物 耳 ヒゲ tシャツ おもちゃ 王冠 冠 かわいい たすき クラッカー くす玉 ケーキ 子ども サングラス スプレー 扇子 かつら 大人の 風船 三角帽子 優勝 リボン ルーレット ワイン ジャケット ビリビリ 帽子 ピュー 2022 500円"},
        "ct83": {"ctname": "オークション > 住まい、インテリア > ペット用品 > 犬 > 服", "y_ct": "2084045164","sex": "0","male": "","female": "","wowma_catid": "491105","wowma_catname": "ペット・ペットグッズ＞犬用品・ドッグフード＞ドッグウェア・アクセサリー","qoo_catid": "320000755","qoo_catname": "ペット_ペット用品_その他","s_keyword": "犬 猫 犬服 おもちゃ ピルクラッシャー 収納 ハーネス 水飲み おやつ うんち袋 リード 首輪 食器 トイレ 爪とぎ ケージ ボール ハウス 猫タワー ブラシ ロンパース 犬服bts 犬服冬服 コスチューム 犬服エル dsサイズ 玩具 笛 ぬいぐるみ 収納ラック 収納ボックス ワゴン 収納棚 収納ケース 服 水飲み器 アイリス うさぎ ウサギ うんち うどん ウエットシート エサ皿 餌台 餌入れ 餌 餌皿 大型犬 お散歩バッグ おむつ"},
        "ct988": {"ctname": "オークション > 住まい、インテリア > ペット用品 > 犬 > 服 > 中型犬用>その他", "y_ct": "2084062626","sex": "0","male": "","female": "","wowma_catid": "491105","wowma_catname": "ペット・ペットグッズ＞犬用品・ドッグフード＞ドッグウェア・アクセサリー","qoo_catid": "320000755","qoo_catname": "ペット_ペット用品_その他","s_keyword": "犬 猫 犬服 おもちゃ ピルクラッシャー 収納 ハーネス 水飲み おやつ うんち袋 リード 首輪 食器 トイレ 爪とぎ ケージ ボール ハウス 猫タワー ブラシ ロンパース 犬服bts 犬服冬服 コスチューム 犬服エル dsサイズ 玩具 笛 ぬいぐるみ 収納ラック 収納ボックス ワゴン 収納棚 収納ケース 服 水飲み器 アイリス うさぎ ウサギ うんち うどん ウエットシート エサ皿 餌台 餌入れ 餌 餌皿 大型犬 お散歩バッグ おむつ"},
        "ct989": {"ctname": "オークション > 住まい、インテリア > ペット用品 > 犬 > 服 > 中型犬用>その他", "y_ct": "2084062626","sex": "0","male": "","female": "","wowma_catid": "491105","wowma_catname": "ペット・ペットグッズ＞犬用品・ドッグフード＞ドッグウェア・アクセサリー","qoo_catid": "320000755","qoo_catname": "ペット_ペット用品_その他","s_keyword": "犬 猫 犬服 おもちゃ ピルクラッシャー 収納 ハーネス 水飲み おやつ うんち袋 リード 首輪 食器 トイレ 爪とぎ ケージ ボール ハウス 猫タワー ブラシ ロンパース 犬服bts 犬服冬服 コスチューム 犬服エル dsサイズ 玩具 笛 ぬいぐるみ 収納ラック 収納ボックス ワゴン 収納棚 収納ケース 服 水飲み器 アイリス うさぎ ウサギ うんち うどん ウエットシート エサ皿 餌台 餌入れ 餌 餌皿 大型犬 お散歩バッグ おむつ"},
        "ct87": {"ctname": "オークション > 住まい、インテリア > ペット用品 > 犬 > 手入れ用品", "y_ct": "2084008198","sex": "0","male": "","female": "","wowma_catid": "491110","wowma_catname": "ペット・ペットグッズ＞犬用品・ドッグフード＞その他犬用品・ドッグフード","qoo_catid": "320000755","qoo_catname": "ペット_ペット用品_その他","s_keyword": "犬 猫 犬服 おもちゃ ピルクラッシャー 収納 ハーネス 水飲み おやつ うんち袋 リード 首輪 食器 トイレ 爪とぎ ケージ ボール ハウス 猫タワー ブラシ ロンパース 犬服bts 犬服冬服 コスチューム 犬服エル dsサイズ 玩具 笛 ぬいぐるみ 収納ラック 収納ボックス ワゴン 収納棚 収納ケース 服 水飲み器 アイリス うさぎ ウサギ うんち うどん ウエットシート エサ皿 餌台 餌入れ 餌 餌皿 大型犬 お散歩バッグ おむつ"},
        "ct990": {"ctname": "オークション > 住まい、インテリア > ペット用品 > 犬 > その他", "y_ct": "2084008200","sex": "0","male": "","female": "","wowma_catid": "491110","wowma_catname": "ペット・ペットグッズ＞犬用品・ドッグフード＞その他犬用品・ドッグフード","qoo_catid": "320000755","qoo_catname": "ペット_ペット用品_その他","s_keyword": "犬 猫 犬服 おもちゃ ピルクラッシャー 収納 ハーネス 水飲み おやつ うんち袋 リード 首輪 食器 トイレ 爪とぎ ケージ ボール ハウス 猫タワー ブラシ ロンパース 犬服bts 犬服冬服 コスチューム 犬服エル dsサイズ 玩具 笛 ぬいぐるみ 収納ラック 収納ボックス ワゴン 収納棚 収納ケース 服 水飲み器 アイリス うさぎ ウサギ うんち うどん ウエットシート エサ皿 餌台 餌入れ 餌 餌皿 大型犬 お散歩バッグ おむつ"},
        "ct91": {"ctname": "オークション > 住まい、インテリア > ペット用品 > 犬 > その他", "y_ct": "2084008200","sex": "0","male": "","female": "","wowma_catid": "491110","wowma_catname": "ペット・ペットグッズ＞犬用品・ドッグフード＞その他犬用品・ドッグフード","qoo_catid": "320000755","qoo_catname": "ペット_ペット用品_その他","s_keyword": "犬 猫 犬服 おもちゃ ピルクラッシャー 収納 ハーネス 水飲み おやつ うんち袋 リード 首輪 食器 トイレ 爪とぎ ケージ ボール ハウス 猫タワー ブラシ ロンパース 犬服bts 犬服冬服 コスチューム 犬服エル dsサイズ 玩具 笛 ぬいぐるみ 収納ラック 収納ボックス ワゴン 収納棚 収納ケース 服 水飲み器 アイリス うさぎ ウサギ うんち うどん ウエットシート エサ皿 餌台 餌入れ 餌 餌皿 大型犬 お散歩バッグ おむつ"},
        "ct996": {"ctname": "おもちゃ・ホビー > 教育系", "y_ct": "2084045581","sex": "0","male": "","female": "","wowma_catid": "293005","wowma_catname": "おもちゃ・趣味>知育玩具・教育玩具>その他知育玩具・教育玩具","qoo_catid": "300000462","qoo_catname": "おもちゃ・知育_知育教材_その他","s_keyword": "1歳 2歳 4歳 5歳 3歳 0歳 小学生 犬 きのおもちゃ 赤ちゃん モンテッソーリ 1歳半 女の子 木 木製 男の子 2歳児 パズル 4歳以上 ブロック 人気 4歳児 大工 6歳 パソコン 知育パッド 5歳以上 5歳児 ひらがな 公文 英語 0歳児 指先 つかまり 小学生高学年 低学年 プログラミング 中学年 形 ６歳 よくばり にんじん おやつ コング ニーナオットソン ノーズワーク おもちゃ ニーナ 大型犬 あいうえお"},
        "ct994": {"ctname": "おもちゃ・ホビー > キーホルダー", "y_ct": "2084312319","sex": "0","male": "","female": "","wowma_catid": "450407","wowma_catname": "バッグ・財布・ファッション小物>ファッション小物>キーホルダー・キーリング","qoo_catid": "320000605","qoo_catname": "ホビー・コスプレ_コレクション_食玩・おまけ","s_keyword": "メンズ レディース 人気 静電気除去 gps 金具 プッシュポップ 革 カッコイイ ブランド 車 おしゃれ バイク かわいい キラキラ キャラクター 安い 人気ブランド イニシャル くま 小さい スマートキー 人気せいでんき チタン"},
        "ct169": {"ctname": "ファッション > レディース > セットアップ、オーバーオール", "y_ct": "2084057486", "sex": "0", "male": "",
                  "female": "", "wowma_catid": "510405", "wowma_catname": "レディースファッション>オールインワン・サロペット>セットアップ",
                  "qoo_catid": "300003063", "qoo_catname": "レディースファッション_オールインワン・セットアップ_セットアップ",
                  "s_keyword": "メンズ 大きいサイズ ディッキーズ  作業着 デニム 5l ゆったり 夏 lee レディース キッズ 金具 サロペット 白 スカート 黒 スキニー カジュアル フェイミー ストレッチ 6l 5xl 柄 作業 3xl 160 140 150 120 100 130 男の子 90 40mm 45mm 33mm 50mm 子供 ブラック 30 50cm carhartt サンドベージュ ヒッコリー 大きい サロペットレディース 赤 アウトドア 赤ちゃん アイボリー "},
        "ct998": {"ctname": "ファッション > レディース > セットアップ、オーバーオール＞オールインワン", "y_ct": "2084057486", "sex": "0", "male": "",
                  "female": "", "wowma_catid": "510402", "wowma_catname": "レディースファッション>オールインワン・サロペット>オールインワン",
                  "qoo_catid": "320001443", "qoo_catname": "レディースファッション_オールインワン・セットアップ_オールインワン",
                  "s_keyword": "メンズ 大きいサイズ ディッキーズ  作業着 デニム 5l ゆったり 夏 lee レディース キッズ 金具 サロペット 白 スカート 黒 スキニー カジュアル フェイミー ストレッチ 6l 5xl 柄 作業 3xl 160 140 150 120 100 130 男の子 90 40mm 45mm 33mm 50mm 子供 ブラック 30 50cm carhartt サンドベージュ ヒッコリー 大きい サロペットレディース 赤 アウトドア 赤ちゃん アイボリー "},
        "ct133": {"ctname": "ファッション > レディース > スカート", "y_ct": "2084057486", "sex": "0", "male": "", "female": "",
                  "wowma_catid": "510601", "wowma_catname": "レディースファッション>スカート>その他スカート", "qoo_catid": "300002860",
                  "qoo_catname": "レディースファッション_スカート_その他",
                  "s_keyword": "ハンガー レディース 春 ロング 膝丈 ギンガムチェック ゴルフ 省スペース 跡がつかない 連結 日本製 白 木製 ピンク プラスチック 夏 きれいめ 春夏 大きいサイズ チャンピオン デニム きれいめゴム フレア 40代 短め タイト 黒 ゴム aライン 膝丈夏 スポーツ ライクパンツ ミニ レース チェック ドット シアー セール マーメイド パンツ ハイウエスト レザー 赤 キッズ レッド 長め インナーパンツ 長め丈 インナー バレエ 大人"},
        "ct1099": {"ctname": "インテリア/生活雑貨 > インテリア > その他", "y_ct": "2084057486", "sex": "0", "male": "", "female": "",
                   "wowma_catid": "310401", "wowma_catname": "インテリア・寝具>インテリア小物・置物>その他インテリア小物・置物",
                   "qoo_catid": "300000468", "qoo_catname": "家具・インテリア_インテリア・装飾_インテリア雑貨",
                   "s_keyword": "マタニティー アジャスターバンド マタニティ アジャスター 抱き枕 衣装 お宮参り お受験 オールインワン キャミ 着圧 サロンペット シートベルト ショーパン シューズ シャツ 写真 ショートパンツ ショーツ 大きいサイズ 仕事 服 マタニティーフォト フォーマルスーツ ワンピース 夏 春 フォーマル 可愛い ドレス 結婚式 マキシ丈 ブラジャー ブラジャーセット ブライダルインナー ボトム デニム ボトムス ボディークリーム ボディブリファー ボード パンツ パジャマ パーティードレス ペイントシール ペイント ペン ベルト バッグ 車 マグネット"},
        "ct1114": {"ctname": "ベビー/マタニティー用品", "y_ct": "2084057486", "sex": "0", "male": "", "female": "",
                   "wowma_catid": "340502", "wowma_catname": "キッズベビー・マタニティ>ベビー>その他ベビー", "qoo_catid": "320000478",
                   "qoo_catname": "ベビー・マタニティ_衛生用品・ヘルスケア_その他",
                   "s_keyword": "パーツ 子供 女の子 ライト バー ミラー スマホ バイクシートバッグ 防水 マウント キャットアイ ロゴ入り ブラック 2本 自転車用アクセサリ 自転車 アクセサリ おりたたみ自転車"},
        "ct71": {"ctname": "スポーツ/アウトドア > 自転車アクセサリ", "y_ct": "2084057486", "sex": "0", "male": "", "female": "",
                 "wowma_catid": "40510601", "wowma_catname": "スポーツ・アウトドア>自転車>自転車アクセサリ>その他自転車アクセサリ",
                 "qoo_catid": "300000251", "qoo_catname": "自転車_自転車用品_その他",
                 "s_keyword": "おりたたみテーブル ロール 軽量 椅子 大きい 180 パラソル ロー 大型 調理器具 キャンプ用品 焚き火台 タイムセール テーブル タープテント テント ランタン キャンプ用品イス らんたん テーブルセット セール コット アウトドアポンプ 遊び 一式 ウォータータンク 日清食品 カップヌードル リフィル 72g 8個 詰め替え用 エコパック アウトドア オイルランタン 斧 蚊取り線香 カトラリー キッズ キャンプ鍋 キャリー クーラーボックス クッカーセット クッカー ケース ケトル コンロ コーヒーミル bromesy コーヒー"},
        "ct74": {"ctname": "スポーツ/アウトドア > その他", "y_ct": "2084057486", "sex": "0", "male": "", "female": "",
                 "wowma_catid": "401101", "wowma_catname": "スポーツ・アウトドア>アウトドア>その他アウトドア", "qoo_catid": "300000239",
                 "qoo_catname": "アウトドア_登山用品_その他",
                 "s_keyword": "おりたたみテーブル ロール 軽量 椅子 大きい 180 パラソル ロー 大型 調理器具 キャンプ用品 焚き火台 タイムセール テーブル タープテント テント ランタン キャンプ用品イス らんたん テーブルセット セール コット アウトドアポンプ 遊び 一式 ウォータータンク 日清食品 カップヌードル リフィル 72g 8個 詰め替え用 エコパック アウトドア オイルランタン 斧 蚊取り線香 カトラリー キッズ キャンプ鍋 キャリー クーラーボックス クッカーセット クッカー ケース ケトル コンロ コーヒーミル bromesy コーヒー"},
        "ct170": {"ctname": "おもちゃ・ホビー", "y_ct": "2084057486", "sex": "0", "male": "", "female": "",
                  "wowma_catid": "290101", "wowma_catname": "おもちゃ・趣味>おもちゃ>その他おもちゃ", "qoo_catid": "300000459",
                  "qoo_catname": "おもちゃ・知育_スポーツ玩具_その他",
                  "s_keyword": "猫 犬 玩具 女の子 収納 男の子 箱 自動 電動 人気 ボール ねずみ オモチャ 噛む ぬいぐるみ ロープ 丈夫 動く 2歳 3歳 1歳 0歳 大人 玩具箱 女性 ピストン 大容量 男性用 小学生 4歳 5歳 6歳 赤ちゃん 収納ボックス バスケット キャスター 引き出し 本棚付き 蓋付き マット 7歳 車 おしゃれ 座れる 箱イカロス ふた付き キャスター付き コンテナ 1歳児 子犬 あま噛み 小型犬"},
        "ct18": {"ctname": "DIY・工具", "y_ct": "2084057486", "sex": "0", "male": "", "female": "",
                 "wowma_catid": "592612", "wowma_catname": "花・ガーデン・DIY工具>DIY工具>その他DIY工具", "qoo_catid": "300000481",
                 "qoo_catname": "ガーデニング・DIY・工具_DIY工具_その他",
                 "s_keyword": "diy工具 diy工具セット 初心者 diy工具入れ diy工具50の極意 diy工具電動 diy工具器具備品 ドリル 本 diy工具収納 diy 工具セット 電動 おもちゃ ドリルガイド セット ダボ継ぎ用ジグ 垂直穴あけ ガイドプレート 家具 木材 ブルー クレッグ 正規輸入品 diyや棚の作成に 斜め穴あけガイド 6サイズ ドリル刃 ほぞ穴あけ 四角の穴あけ用 角穴ドリル 高硬度 木工 ドリルビット 角のみ 電動工具 工具 インパクト 超基本diy木工 トグルクランプ 下方押え型 ゴムヘッド 簡単操作 補助 締付 圧締 金属 固定工具 10個セット nanmara クランプ 固定 保持 2個セット"},
    }
    """
    _MY_CT_CODES_SMALL = {
        "ct676": {"ctname": "オークション > ファッション > メンズファッション > ジャケット、上着 > ライダース > Lサイズ", "y_ct": "2084243906","sex": "0","male": "","female": "","wowma_catid": "500501","wowma_catname": "メンズファッション＞ジャケット・アウター＞その他ジャケット・アウター","qoo_catid": "300002284","qoo_catname": "メンズファッション_アウター_ダウンジャケット"},
        "ct677": {"ctname": "オークション > スポーツ、レジャー > スポーツウエア > 男性用 > パーカー", "y_ct": "2084303393","sex": "0","male": "","female": "","wowma_catid": "500501","wowma_catname": "メンズファッション＞ジャケット・アウター＞その他ジャケット・アウター","qoo_catid": "300002279","qoo_catname": "メンズファッション_アウター_パーカー・トレーナー"},
        "ct678": {"ctname": "オークション > ファッション > メンズファッション > ジャケット、上着 > ジャンパー、ブルゾン > ジャンパー、ブルゾン一般 > Mサイズ", "y_ct": "2084050108","sex": "0","male": "","female": "","wowma_catid": "500501","wowma_catname": "メンズファッション＞ジャケット・アウター＞その他ジャケット・アウター","qoo_catid": "300002284","qoo_catname": "メンズファッション_アウター_ダウンジャケット"},
        "ct679": {"ctname": "オークション > ファッション > メンズファッション > ジャケット、上着 > ジャンパー、ブルゾン > ジャンパー、ブルゾン一般 > Mサイズ", "y_ct": "2084050108","sex": "0","male": "","female": "","wowma_catid": "500501","wowma_catname": "メンズファッション＞ジャケット・アウター＞その他ジャケット・アウター","qoo_catid": "300002284","qoo_catname": "メンズファッション_アウター_ダウンジャケット"},
        "ct680": {"ctname": "オークション > ファッション > メンズファッション > コート > コート一般 > Mサイズ", "y_ct": "2084057466","sex": "0","male": "","female": "","wowma_catid": "500524","wowma_catname": "メンズファッション＞ジャケット・アウター＞トレンチコート","qoo_catid": "300000059","qoo_catname": "メンズファッション_アウター_Aライン・ピーコート"},
        "ct681": {"ctname": "オークション > ファッション > メンズファッション > シャツ > 半袖 > 半袖シャツ一般 > Mサイズ", "y_ct": "2084064183","sex": "0","male": "","female": "","wowma_catid": "320403","wowma_catname": "インナー・ルームウェア＞メンズインナー＞シャツ・肌着","qoo_catid": "300000055","qoo_catname": "メンズファッション_トップス_長袖シャツ"},
        "ct682": {"ctname": "オークション > ファッション > メンズファッション > シャツ > 長袖 > 長袖シャツ一般 > Mサイズ", "y_ct": "2084064178","sex": "0","male": "","female": "","wowma_catid": "320403","wowma_catname": "インナー・ルームウェア＞メンズインナー＞シャツ・肌着","qoo_catid": "300000055","qoo_catname": "メンズファッション_トップス_長袖シャツ"},
        "ct685": {"ctname": "オークション > ファッション > メンズファッション > カーディガン", "y_ct": "2084007052","sex": "0","male": "","female": "","wowma_catid": "501103","wowma_catname": "メンズファッション＞学生服＞スクールニット・カーディガン","qoo_catid": "300002278","qoo_catname": "メンズファッション_アウター_カーディガン"},
        "ct803": {"ctname": "オークション > ファッション > メンズファッション > シャツ > その他の袖丈", "y_ct": "2084054038","sex": "0","male": "","female": "","wowma_catid": "320403","wowma_catname": "インナー・ルームウェア＞メンズインナー＞シャツ・肌着","qoo_catid": "300000055","qoo_catname": "メンズファッション_トップス_長袖シャツ"},
        "ct804": {"ctname": "オークション > ファッション > メンズファッション > トレーナー > Mサイズ", "y_ct": "2084057461","sex": "0","male": "","female": "","wowma_catid": "500712","wowma_catname": "メンズファッション＞トップス＞トレーナー・スウェット","qoo_catid": "300002279","qoo_catname": "メンズファッション_アウター_パーカー・トレーナー"},
        "ct805": {"ctname": "オークション > ファッション > メンズファッション > パンツ、スラックス > Mサイズ", "y_ct": "2084224619","sex": "0","male": "","female": "","wowma_catid": "500808","wowma_catname": "メンズファッション＞パンツ・ボトムス＞スラックス","qoo_catid": "300002302","qoo_catname": "メンズファッション_ビジネス・フォーマル_パンツ・スラックス"},
        "ct806": {"ctname": "オークション > ファッション > メンズファッション > インナーウエア > ボクサーブリーフ > Mサイズ", "y_ct": "2084053072","sex": "0","male": "","female": "","wowma_catid": "500801","wowma_catname": "メンズファッション＞パンツ・ボトムス＞その他パンツ・ボトムス","qoo_catid": "300000066","qoo_catname": "メンズファッション_インナー・靴下_ボクサーパンツ"},
        "ct807": {"ctname": "オークション > ファッション > メンズファッション > 水着 > Mサイズ", "y_ct": "2084051835","sex": "0","male": "","female": "","wowma_catid": "501201","wowma_catname": "メンズファッション＞水着＞その他水着","qoo_catid": "300002298","qoo_catname": "メンズファッション_その他メンズファッション_水着"},
        "ct120": {"ctname": "オークション > ファッション > レディースファッション > コート > コート一般 > Mサイズ", "y_ct": "2084057471","sex": "0","male": "","female": "","wowma_catid": "320708","wowma_catname": "インナー・ルームウェア＞レディースインナー＞ペチコート","qoo_catid": "300002186","qoo_catname": "レディースファッション_アウター_ダウンジャケット・コート"},
        "ct689": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > ライダース", "y_ct": "2084243900","sex": "0","male": "","female": "","wowma_catid": "510330","wowma_catname": "レディースファッション＞アウター＞ライダースジャケット","qoo_catid": "300002186","qoo_catname": "レディースファッション_アウター_ダウンジャケット・コート"},
        "ct690": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > その他", "y_ct": "2084005208","sex": "0","male": "","female": "","wowma_catid": "510301","wowma_catname": "レディースファッション＞アウター＞その他アウター","qoo_catid": "300002186","qoo_catname": "レディースファッション_アウター_ダウンジャケット・コート"},
        "ct691": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > ジャンパー、ブルゾン > ジャンパー、ブルゾン一般 > Mサイズ", "y_ct": "2084057481","sex": "0","male": "","female": "","wowma_catid": "510324","wowma_catname": "レディースファッション＞アウター＞ブルゾン","qoo_catid": "300002186","qoo_catname": "レディースファッション_アウター_ダウンジャケット・コート"},
        "ct692": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > ジャケット、ブレザー > Mサイズ", "y_ct": "2084057476","sex": "0","male": "","female": "","wowma_catid": "510301","wowma_catname": "レディースファッション＞アウター＞その他アウター","qoo_catid": "300002186","qoo_catname": "レディースファッション_アウター_ダウンジャケット・コート"},
        "ct693": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > パーカ > パーカ一般 > Mサイズ", "y_ct": "2084050490","sex": "0","male": "","female": "","wowma_catid": "510309","wowma_catname": "レディースファッション＞アウター＞スタンドカラージャケット・コート","qoo_catid": "300002186","qoo_catname": "レディースファッション_アウター_ダウンジャケット・コート"},
        "ct694": {"ctname": "オークション > ファッション > レディースファッション > コート > コート一般 > Mサイズ", "y_ct": "2084057471","sex": "0","male": "","female": "","wowma_catid": "320708","wowma_catname": "インナー・ルームウェア＞レディースインナー＞ペチコート","qoo_catid": "300002186","qoo_catname": "レディースファッション_アウター_ダウンジャケット・コート"},
        "ct695": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > ジャンパー、ブルゾン > スカジャン", "y_ct": "2084052541","sex": "0","male": "","female": "","wowma_catid": "510307","wowma_catname": "レディースファッション＞アウター＞スカジャン","qoo_catid": "300002186","qoo_catname": "レディースファッション_アウター_ダウンジャケット・コート"},
        "ct696": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > ジャンパー、ブルゾン > ジージャン > Mサイズ", "y_ct": "2084054383","sex": "0","male": "","female": "","wowma_catid": "510317","wowma_catname": "レディースファッション＞アウター＞デニムジャケット","qoo_catid": "300000041","qoo_catname": "レディースファッション_アウター_ジャンパー・ブルゾン"},
        "ct1022": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > パーカ > パーカ一般 > Mサイズ", "y_ct": "2084050490","sex": "0","male": "","female": "","wowma_catid": "510301","wowma_catname": "レディースファッション＞アウター＞その他アウター","qoo_catid": "300002186","qoo_catname": "レディースファッション_アウター_ダウンジャケット・コート"},
        "ct163": {"ctname": "オークション > ファッション > レディースファッション > カットソー > 長袖 > Mサイズ", "y_ct": "2084050495","sex": "0","male": "","female": "","wowma_catid": "510804","wowma_catname": "レディースファッション＞トップス＞カットソー","qoo_catid": "300002252","qoo_catname": "レディースファッション_トップス_Tシャツ・カットソー"},
        "ct1108": {"ctname": "オークション > ファッション > レディースファッション > カットソー > 長袖 > Mサイズ", "y_ct": "2084050495","sex": "0","male": "","female": "","wowma_catid": "510804","wowma_catname": "レディースファッション＞トップス＞カットソー","qoo_catid": "300002252","qoo_catname": "レディースファッション_トップス_Tシャツ・カットソー"},
        "ct698": {"ctname": "オークション > ファッション > レディースファッション > カットソー > 長袖 > Mサイズ", "y_ct": "2084050495","sex": "0","male": "","female": "","wowma_catid": "510804","wowma_catname": "レディースファッション＞トップス＞カットソー","qoo_catid": "300002252","qoo_catname": "レディースファッション_トップス_Tシャツ・カットソー"},
        "ct699": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > Vネック > その他", "y_ct": "2084051324","sex": "0","male": "","female": "","wowma_catid": "510801","wowma_catname": "レディースファッション＞トップス＞Tシャツ","qoo_catid": "300002767","qoo_catname": "レディースファッション_ワンピース・ドレス_Tシャツワンピ"},
        "ct700": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > その他", "y_ct": "2084051326","sex": "0","male": "","female": "","wowma_catid": "510801","wowma_catname": "レディースファッション＞トップス＞Tシャツ","qoo_catid": "300002767","qoo_catname": "レディースファッション_ワンピース・ドレス_Tシャツワンピ"},
        "ct1102": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Lサイズ > その他", "y_ct": "2084051342","sex": "0","male": "","female": "","wowma_catid": "510801","wowma_catname": "レディースファッション＞トップス＞Tシャツ","qoo_catid": "300002767","qoo_catname": "レディースファッション_ワンピース・ドレス_Tシャツワンピ"},
        "ct704": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Lサイズ > その他", "y_ct": "2084051342","sex": "0","male": "","female": "","wowma_catid": "510801","wowma_catname": "レディースファッション＞トップス＞Tシャツ","qoo_catid": "300002767","qoo_catname": "レディースファッション_ワンピース・ドレス_Tシャツワンピ"},
        "ct701": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > 丸首 > イラスト、キャラクター", "y_ct": "2084051314","sex": "0","male": "","female": "","wowma_catid": "510801","wowma_catname": "レディースファッション＞トップス＞Tシャツ","qoo_catid": "300002767","qoo_catname": "レディースファッション_ワンピース・ドレス_Tシャツワンピ"},
        "ct702": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > その他の袖丈", "y_ct": "2084054032","sex": "0","male": "","female": "","wowma_catid": "510801","wowma_catname": "レディースファッション＞トップス＞Tシャツ","qoo_catid": "300002767","qoo_catname": "レディースファッション_ワンピース・ドレス_Tシャツワンピ"},
        "ct1107": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > その他", "y_ct": "2084051326","sex": "0","male": "","female": "","wowma_catid": "510801","wowma_catname": "レディースファッション＞トップス＞Tシャツ","qoo_catid": "300002767","qoo_catname": "レディースファッション_ワンピース・ドレス_Tシャツワンピ"},
        "ct703": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > その他", "y_ct": "2084051326","sex": "0","male": "","female": "","wowma_catid": "510801","wowma_catname": "レディースファッション＞トップス＞Tシャツ","qoo_catid": "300002767","qoo_catname": "レディースファッション_ワンピース・ドレス_Tシャツワンピ"},
        "ct1111": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > Vネック > 柄もの", "y_ct": "2084051321","sex": "0","male": "","female": "","wowma_catid": "510801","wowma_catname": "レディースファッション＞トップス＞Tシャツ","qoo_catid": "300002767","qoo_catname": "レディースファッション_ワンピース・ドレス_Tシャツワンピ"},
        "ct1112": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > 丸首 > 文字、ロゴ", "y_ct": "2084051317","sex": "0","male": "","female": "","wowma_catid": "510801","wowma_catname": "レディースファッション＞トップス＞Tシャツ","qoo_catid": "300002767","qoo_catname": "レディースファッション_ワンピース・ドレス_Tシャツワンピ"},
        "ct705": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486","sex": "0","male": "","female": "","wowma_catid": "510815","wowma_catname": "レディースファッション＞トップス＞ブラウス","qoo_catid": "300000013","qoo_catname": "レディースファッション_トップス_シャツ・ブラウス"},
        "ct706": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486","sex": "0","male": "","female": "","wowma_catid": "510815","wowma_catname": "レディースファッション＞トップス＞ブラウス","qoo_catid": "300000013","qoo_catname": "レディースファッション_トップス_シャツ・ブラウス"},
        "ct707": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486","sex": "0","male": "","female": "","wowma_catid": "510815","wowma_catname": "レディースファッション＞トップス＞ブラウス","qoo_catid": "300000013","qoo_catname": "レディースファッション_トップス_シャツ・ブラウス"},
        "ct708": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486","sex": "0","male": "","female": "","wowma_catid": "510815","wowma_catname": "レディースファッション＞トップス＞ブラウス","qoo_catid": "300000013","qoo_catname": "レディースファッション_トップス_シャツ・ブラウス"},
        "ct1045": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486","sex": "0","male": "","female": "","wowma_catid": "510815","wowma_catname": "レディースファッション＞トップス＞ブラウス","qoo_catid": "300000013","qoo_catname": "レディースファッション_トップス_シャツ・ブラウス"},
        "ct1044": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486","sex": "0","male": "","female": "","wowma_catid": "510815","wowma_catname": "レディースファッション＞トップス＞ブラウス","qoo_catid": "300000013","qoo_catname": "レディースファッション_トップス_シャツ・ブラウス"},
        "ct709": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486","sex": "0","male": "","female": "","wowma_catid": "510815","wowma_catname": "レディースファッション＞トップス＞ブラウス","qoo_catid": "300000013","qoo_catname": "レディースファッション_トップス_シャツ・ブラウス"},
        "ct710": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486","sex": "0","male": "","female": "","wowma_catid": "510815","wowma_catname": "レディースファッション＞トップス＞ブラウス","qoo_catid": "300000013","qoo_catname": "レディースファッション_トップス_シャツ・ブラウス"},
        "ct711": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486","sex": "0","male": "","female": "","wowma_catid": "510815","wowma_catname": "レディースファッション＞トップス＞ブラウス","qoo_catid": "300000013","qoo_catname": "レディースファッション_トップス_シャツ・ブラウス"},
        "ct715": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486","sex": "0","male": "","female": "","wowma_catid": "510815","wowma_catname": "レディースファッション＞トップス＞ブラウス","qoo_catid": "300000013","qoo_catname": "レディースファッション_トップス_シャツ・ブラウス"},
        "ct712": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > その他", "y_ct": "2084051326","sex": "0","male": "","female": "","wowma_catid": "510801","wowma_catname": "レディースファッション＞トップス＞Tシャツ","qoo_catid": "300002767","qoo_catname": "レディースファッション_ワンピース・ドレス_Tシャツワンピ"},
        "ct713": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > その他", "y_ct": "2084051326","sex": "0","male": "","female": "","wowma_catid": "510801","wowma_catname": "レディースファッション＞トップス＞Tシャツ","qoo_catid": "300002767","qoo_catname": "レディースファッション_ワンピース・ドレス_Tシャツワンピ"},
        "ct714": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 半袖 > Mサイズ", "y_ct": "2084064237","sex": "0","male": "","female": "","wowma_catid": "510815","wowma_catname": "レディースファッション＞トップス＞ブラウス","qoo_catid": "300000013","qoo_catname": "レディースファッション_トップス_シャツ・ブラウス"},
        "ct716": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 袖なし、ノースリーブ > ノースリーブシャツ一般", "y_ct": "2084027443","sex": "0","male": "","female": "","wowma_catid": "510812","wowma_catname": "レディースファッション＞トップス＞ノースリーブ","qoo_catid": "300000013","qoo_catname": "レディースファッション_トップス_シャツ・ブラウス"},
        "ct717": {"ctname": "オークション > ファッション > レディースファッション > キャミソール", "y_ct": "2084064258","sex": "0","male": "","female": "","wowma_catid": "510806","wowma_catname": "レディースファッション＞トップス＞キャミソール","qoo_catid": "300000012","qoo_catname": "レディースファッション_トップス_キャミソール・タンクトップ"},
        "ct719": {"ctname": "オークション > ファッション > レディースファッション > チュニック > 袖なし、ノースリーブ > Mサイズ", "y_ct": "2084231772","sex": "0","male": "","female": "","wowma_catid": "510810","wowma_catname": "レディースファッション＞トップス＞チュニック","qoo_catid": "300002253","qoo_catname": "レディースファッション_トップス_チュニック"},
        "ct1110": {"ctname": "オークション > ファッション > レディースファッション > チューブトップ、ベアトップ", "y_ct": "2084243344","sex": "0","male": "","female": "","wowma_catid": "510816","wowma_catname": "レディースファッション＞トップス＞ベアトップ・チューブトップ","qoo_catid": "320001136","qoo_catname": "下着・レッグウェア_キャミソール・ペチコート_ベアトップ・チューブトップ"},
        "ct162": {"ctname": "オークション > ファッション > レディースファッション > カーディガン > Mサイズ", "y_ct": "2084064209","sex": "0","male": "","female": "","wowma_catid": "510805","wowma_catname": "レディースファッション＞トップス＞カーディガン","qoo_catid": "300003071","qoo_catname": "レディースファッション_トップス_カーディガン"},
        "ct720": {"ctname": "オークション > ファッション > レディースファッション > カーディガン > Mサイズ", "y_ct": "2084064209","sex": "0","male": "","female": "","wowma_catid": "510805","wowma_catname": "レディースファッション＞トップス＞カーディガン","qoo_catid": "300003071","qoo_catname": "レディースファッション_トップス_カーディガン"},
        "ct721": {"ctname": "オークション > ファッション > レディースファッション > カーディガン > Mサイズ", "y_ct": "2084064209","sex": "0","male": "","female": "","wowma_catid": "510805","wowma_catname": "レディースファッション＞トップス＞カーディガン","qoo_catid": "300003071","qoo_catname": "レディースファッション_トップス_カーディガン"},
        "ct722": {"ctname": "オークション > ファッション > レディースファッション > ニット、セーター > 長袖 > Mサイズ", "y_ct": "2084064247","sex": "0","male": "","female": "","wowma_catid": "510811","wowma_catname": "レディースファッション＞トップス＞ニット・セーター","qoo_catid": "300000025","qoo_catname": "レディースファッション_トップス_ニット"},
        "ct723": {"ctname": "オークション > ファッション > レディースファッション > ニット、セーター > 長袖 > Mサイズ", "y_ct": "2084064247","sex": "0","male": "","female": "","wowma_catid": "510811","wowma_catname": "レディースファッション＞トップス＞ニット・セーター","qoo_catid": "300000025","qoo_catname": "レディースファッション_トップス_ニット"},
        "ct724": {"ctname": "オークション > ファッション > レディースファッション > ニット、セーター > 長袖 > Mサイズ", "y_ct": "2084064247","sex": "0","male": "","female": "","wowma_catid": "510811","wowma_catname": "レディースファッション＞トップス＞ニット・セーター","qoo_catid": "300000025","qoo_catname": "レディースファッション_トップス_ニット"},
        "ct725": {"ctname": "オークション > ファッション > レディースファッション > ニット、セーター > 長袖 > Mサイズ", "y_ct": "2084064247","sex": "0","male": "","female": "","wowma_catid": "510811","wowma_catname": "レディースファッション＞トップス＞ニット・セーター","qoo_catid": "300000025","qoo_catname": "レディースファッション_トップス_ニット"},
        "ct726": {"ctname": "オークション > ファッション > レディースファッション > カーディガン > Mサイズ", "y_ct": "2084064209","sex": "0","male": "","female": "","wowma_catid": "510805","wowma_catname": "レディースファッション＞トップス＞カーディガン","qoo_catid": "300003071","qoo_catname": "レディースファッション_トップス_カーディガン"},
        "ct727": {"ctname": "オークション > ファッション > レディースファッション > カーディガン > Mサイズ", "y_ct": "2084064209","sex": "0","male": "","female": "","wowma_catid": "510805","wowma_catname": "レディースファッション＞トップス＞カーディガン","qoo_catid": "300003071","qoo_catname": "レディースファッション_トップス_カーディガン"},
        "ct122": {"ctname": "オークション > ファッション > レディースファッション > パンツ、スラックス > Mサイズ", "y_ct": "2084224590","sex": "0","male": "","female": "","wowma_catid": "511001","wowma_catname": "レディースファッション＞パンツ＞その他パンツ","qoo_catid": "300002763","qoo_catname": "レディースファッション_パンツ_その他"},
        "ct728": {"ctname": "オークション > ファッション > レディースファッション > パンツ、スラックス > Mサイズ", "y_ct": "2084224590","sex": "0","male": "","female": "","wowma_catid": "511001","wowma_catname": "レディースファッション＞パンツ＞その他パンツ","qoo_catid": "300002763","qoo_catname": "レディースファッション_パンツ_その他"},
        "ct1008": {"ctname": "オークション > ファッション > レディースファッション > レギンス、トレンカ", "y_ct": "2084007161","sex": "0","male": "","female": "","wowma_catid": "511011","wowma_catname": "レディースファッション＞パンツ＞スパッツ・レギンス","qoo_catid": "300000047","qoo_catname": "レディースファッション_パンツ_レギンス"},
        "ct1009": {"ctname": "オークション > ファッション > レディースファッション > ワークパンツ、ペインターパンツ > Mサイズ", "y_ct": "2084224605","sex": "0","male": "","female": "","wowma_catid": "511001","wowma_catname": "レディースファッション＞パンツ＞その他パンツ","qoo_catid": "300002763","qoo_catname": "レディースファッション_パンツ_その他"},
        "ct1010": {"ctname": "オークション > ファッション > レディースファッション > ワークパンツ、ペインターパンツ > Mサイズ", "y_ct": "2084224605","sex": "0","male": "","female": "","wowma_catid": "511001","wowma_catname": "レディースファッション＞パンツ＞その他パンツ","qoo_catid": "300002763","qoo_catname": "レディースファッション_パンツ_その他"},
        "ct1047": {"ctname": "オークション > ファッション > レディースファッション > パンツ、スラックス > Mサイズ", "y_ct": "2084224590","sex": "0","male": "","female": "","wowma_catid": "511001","wowma_catname": "レディースファッション＞パンツ＞その他パンツ","qoo_catid": "300002763","qoo_catname": "レディースファッション_パンツ_その他"},
        "ct738": {"ctname": "オークション > ファッション > レディースファッション > スカート > ロングスカート > その他", "y_ct": "2084007175","sex": "0","male": "","female": "","wowma_catid": "510601","wowma_catname": "レディースファッション＞スカート＞その他スカート","qoo_catid": "300002764","qoo_catname": "レディースファッション_スカート_ロングスカート"},
        "ct739": {"ctname": "オークション > ファッション > レディースファッション > スカート > ロングスカート > その他", "y_ct": "2084007175","sex": "0","male": "","female": "","wowma_catid": "510601","wowma_catname": "レディースファッション＞スカート＞その他スカート","qoo_catid": "300002764","qoo_catname": "レディースファッション_スカート_ロングスカート"},
        "ct740": {"ctname": "オークション > ファッション > レディースファッション > スカート > ロングスカート > その他", "y_ct": "2084007175","sex": "0","male": "","female": "","wowma_catid": "510601","wowma_catname": "レディースファッション＞スカート＞その他スカート","qoo_catid": "300002764","qoo_catname": "レディースファッション_スカート_ロングスカート"},
        "ct741": {"ctname": "オークション > ファッション > レディースファッション > スカート > ミニスカート > その他", "y_ct": "2084007171","sex": "0","male": "","female": "","wowma_catid": "510601","wowma_catname": "レディースファッション＞スカート＞その他スカート","qoo_catid": "300000040","qoo_catname": "レディースファッション_スカート_ミニスカート"},
        "ct742": {"ctname": "オークション > ファッション > レディースファッション > スカート > ミニスカート > タイトスカート > Mサイズ", "y_ct": "2084222253","sex": "0","male": "","female": "","wowma_catid": "510605","wowma_catname": "レディースファッション＞スカート＞タイトスカート","qoo_catid": "300002247","qoo_catname": "レディースファッション_スーツ_スカートスーツ"},
        "ct743": {"ctname": "オークション > ファッション > レディースファッション > スカート > ひざ丈スカート > その他", "y_ct": "2084054014","sex": "0","male": "","female": "","wowma_catid": "510601","wowma_catname": "レディースファッション＞スカート＞その他スカート","qoo_catid": "300002860","qoo_catname": "レディースファッション_スカート_その他"},
        "ct744": {"ctname": "オークション > ファッション > レディースファッション > スカート > ひざ丈スカート > プリーツスカート > Mサイズ", "y_ct": "2084222283","sex": "0","male": "","female": "","wowma_catid": "510612","wowma_catname": "レディースファッション＞スカート＞プリーツスカート","qoo_catid": "300002859","qoo_catname": "レディースファッション_スカート_ミディアムスカート"},
        "ct745": {"ctname": "オークション > ファッション > レディースファッション > スカート > ひざ丈スカート > フレアースカート、ギャザースカート > Mサイズ", "y_ct": "2084222278","sex": "0","male": "","female": "","wowma_catid": "510603","wowma_catname": "レディースファッション＞スカート＞ギャザースカート","qoo_catid": "300002860","qoo_catname": "レディースファッション_スカート_その他"},
        "ct746": {"ctname": "オークション > ファッション > レディースファッション > スカート > ひざ丈スカート > タイトスカート > Mサイズ", "y_ct": "2084222273","sex": "0","male": "","female": "","wowma_catid": "510605","wowma_catname": "レディースファッション＞スカート＞タイトスカート","qoo_catid": "300002247","qoo_catname": "レディースファッション_スーツ_スカートスーツ"},
        "ct747": {"ctname": "オークション > ファッション > レディースファッション > スカート > ひざ丈スカート > その他", "y_ct": "2084054014","sex": "0","male": "","female": "","wowma_catid": "510601","wowma_catname": "レディースファッション＞スカート＞その他スカート","qoo_catid": "300002860","qoo_catname": "レディースファッション_スカート_その他"},
        "ct748": {"ctname": "オークション > ファッション > レディースファッション > スカート > ロングスカート > その他", "y_ct": "2084007175","sex": "0","male": "","female": "","wowma_catid": "510601","wowma_catname": "レディースファッション＞スカート＞その他スカート","qoo_catid": "300002764","qoo_catname": "レディースファッション_スカート_ロングスカート"},
        "ct754": {"ctname": "オークション > ファッション > レディースファッション > スカート > ロングスカート > フレアースカート、ギャザースカート > Mサイズ", "y_ct": "2084222298","sex": "0","male": "","female": "","wowma_catid": "510603","wowma_catname": "レディースファッション＞スカート＞ギャザースカート","qoo_catid": "300002860","qoo_catname": "レディースファッション_スカート_その他"},
        "ct156": {"ctname": "オークション > ファッション > レディースファッション > ワンピース > ミニスカート > Mサイズ", "y_ct": "2084224575","sex": "0","male": "","female": "","wowma_catid": "511104","wowma_catname": "レディースファッション＞ワンピース＞ショート・ミニ丈","qoo_catid": "300000040","qoo_catname": "レディースファッション_スカート_ミニスカート"},
        "ct749": {"ctname": "オークション > ファッション > レディースファッション > ワンピース > ロングスカート > Mサイズ", "y_ct": "2084224585","sex": "0","male": "","female": "","wowma_catid": "511105","wowma_catname": "レディースファッション＞ワンピース＞ロング・マキシ丈","qoo_catid": "300002764","qoo_catname": "レディースファッション_スカート_ロングスカート"},
        "ct750": {"ctname": "オークション > ファッション > レディースファッション > ワンピース > ロングスカート > Mサイズ", "y_ct": "2084224585","sex": "0","male": "","female": "","wowma_catid": "511105","wowma_catname": "レディースファッション＞ワンピース＞ロング・マキシ丈","qoo_catid": "300002764","qoo_catname": "レディースファッション_スカート_ロングスカート"},
        "ct751": {"ctname": "オークション > ファッション > レディースファッション > ワンピース > ロングスカート > Mサイズ", "y_ct": "2084224585","sex": "0","male": "","female": "","wowma_catid": "511105","wowma_catname": "レディースファッション＞ワンピース＞ロング・マキシ丈","qoo_catid": "300002764","qoo_catname": "レディースファッション_スカート_ロングスカート"},
        "ct752": {"ctname": "オークション > ファッション > レディースファッション > ワンピース > ミニスカート > Mサイズ", "y_ct": "2084224575","sex": "0","male": "","female": "","wowma_catid": "511104","wowma_catname": "レディースファッション＞ワンピース＞ショート・ミニ丈","qoo_catid": "300000040","qoo_catname": "レディースファッション_スカート_ミニスカート"},
        "ct753": {"ctname": "オークション > ファッション > レディースファッション > フォーマル > ワンピース", "y_ct": "2084037008","sex": "0","male": "","female": "","wowma_catid": "511101","wowma_catname": "レディースファッション＞ワンピース＞その他ワンピース","qoo_catid": "300002248","qoo_catname": "レディースファッション_スーツ_ワンピーススーツ"},
        "ct755": {"ctname": "オークション > ファッション > レディースファッション > フォーマル > ワンピース", "y_ct": "2084037008","sex": "0","male": "","female": "","wowma_catid": "511101","wowma_catname": "レディースファッション＞ワンピース＞その他ワンピース","qoo_catid": "300002248","qoo_catname": "レディースファッション_スーツ_ワンピーススーツ"},
        "ct756": {"ctname": "オークション > ファッション > レディースファッション > フォーマル > ワンピース", "y_ct": "2084037008","sex": "0","male": "","female": "","wowma_catid": "511101","wowma_catname": "レディースファッション＞ワンピース＞その他ワンピース","qoo_catid": "300002248","qoo_catname": "レディースファッション_スーツ_ワンピーススーツ"},
        "ct757": {"ctname": "オークション > ファッション > レディースファッション > フォーマル > ワンピース", "y_ct": "2084037008","sex": "0","male": "","female": "","wowma_catid": "511101","wowma_catname": "レディースファッション＞ワンピース＞その他ワンピース","qoo_catid": "300002248","qoo_catname": "レディースファッション_スーツ_ワンピーススーツ"},
        "ct758": {"ctname": "オークション > ファッション > レディースファッション > フォーマル > ワンピース", "y_ct": "2084037008","sex": "0","male": "","female": "","wowma_catid": "511101","wowma_catname": "レディースファッション＞ワンピース＞その他ワンピース","qoo_catid": "300002248","qoo_catname": "レディースファッション_スーツ_ワンピーススーツ"},
        "ct759": {"ctname": "オークション > ファッション > レディースファッション > フォーマル > ワンピース", "y_ct": "2084037008","sex": "0","male": "","female": "","wowma_catid": "511101","wowma_catname": "レディースファッション＞ワンピース＞その他ワンピース","qoo_catid": "300002248","qoo_catname": "レディースファッション_スーツ_ワンピーススーツ"},
        "ct760": {"ctname": "オークション > ファッション > レディースファッション > フォーマル > ワンピース", "y_ct": "2084037008","sex": "0","male": "","female": "","wowma_catid": "511101","wowma_catname": "レディースファッション＞ワンピース＞その他ワンピース","qoo_catid": "300002248","qoo_catname": "レディースファッション_スーツ_ワンピーススーツ"},
        "ct761": {"ctname": "オークション > ファッション > レディースファッション > フォーマル > ワンピース", "y_ct": "2084037008","sex": "0","male": "","female": "","wowma_catid": "511101","wowma_catname": "レディースファッション＞ワンピース＞その他ワンピース","qoo_catid": "300002248","qoo_catname": "レディースファッション_スーツ_ワンピーススーツ"},
        "ct762": {"ctname": "オークション > ファッション > レディースファッション > フォーマル > ワンピース", "y_ct": "2084037008","sex": "0","male": "","female": "","wowma_catid": "511101","wowma_catname": "レディースファッション＞ワンピース＞その他ワンピース","qoo_catid": "300002248","qoo_catname": "レディースファッション_スーツ_ワンピーススーツ"},
        "ct1453": {"ctname": "オークション > ファッション > レディースファッション > フォーマル > ワンピース", "y_ct": "2084037008","sex": "0","male": "","female": "","wowma_catid": "511101","wowma_catname": "レディースファッション＞ワンピース＞その他ワンピース","qoo_catid": "300002248","qoo_catname": "レディースファッション_スーツ_ワンピーススーツ"},
        "ct765": {"ctname": "オークション > スポーツ、レジャー > スポーツウエア > 女性用 > 上下セット > ジャージ > その他", "y_ct": "2084203510","sex": "0","male": "","female": "","wowma_catid": "402302","wowma_catname": "スポーツ・アウトドア＞スポーツウェア＞ジャージ","qoo_catid": "300000211","qoo_catname": "スポーツ_スポーツウェア_レディーススポーツウェア"},
        "ct763": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > その他", "y_ct": "2084053158","sex": "0","male": "","female": "","wowma_catid": "32070201","wowma_catname": "インナー・ルームウェア＞レディースインナー＞ショーツ＞Tバック・タンガ","qoo_catid": "300002872","qoo_catname": "スポーツ_スポーツウェア_レディーススポーツインナー"},
        "ct767": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > ブラジャー > その他", "y_ct": "2084053090","sex": "0","male": "","female": "","wowma_catid": "32070603","wowma_catname": "インナー・ルームウェア＞レディースインナー＞ブラ＞その他ブラ","qoo_catid": "300000029","qoo_catname": "下着・レッグウェア_ブラジャー_ブラジャー"},
        "ct1109": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > その他", "y_ct": "2084053158","sex": "0","male": "","female": "","wowma_catid": "320701","wowma_catname": "インナー・ルームウェア＞レディースインナー＞その他レディースインナー","qoo_catid": "300002267","qoo_catname": "下着・レッグウェア_靴下・レッグウェア_その他"},
        "ct768": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > ブラジャー > その他", "y_ct": "2084053090","sex": "0","male": "","female": "","wowma_catid": "32070603","wowma_catname": "インナー・ルームウェア＞レディースインナー＞ブラ＞その他ブラ","qoo_catid": "300000029","qoo_catname": "下着・レッグウェア_ブラジャー_ブラジャー"},
        "ct769": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > ブラジャー > その他", "y_ct": "2084053090","sex": "0","male": "","female": "","wowma_catid": "32070603","wowma_catname": "インナー・ルームウェア＞レディースインナー＞ブラ＞その他ブラ","qoo_catid": "300000029","qoo_catname": "下着・レッグウェア_ブラジャー_ブラジャー"},
        "ct770": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > ショーツ > Mサイズ > スタンダード", "y_ct": "2084211818","sex": "0","male": "","female": "","wowma_catid": "32070202","wowma_catname": "インナー・ルームウェア＞レディースインナー＞ショーツ＞その他ショーツ","qoo_catid": "300000030","qoo_catname": "下着・レッグウェア_ショーツ_ショーツ"},
        "ct771": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > スリップ > Mサイズ", "y_ct": "2084053118","sex": "0","male": "","female": "","wowma_catid": "320713","wowma_catname": "インナー・ルームウェア＞レディースインナー＞スリップ","qoo_catid": "300002833","qoo_catname": "下着・レッグウェア_キャミソール・ペチコート_キャミソール・スリップ"},
        "ct772": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > ブラジャー > その他", "y_ct": "2084053090","sex": "0","male": "","female": "","wowma_catid": "32070603","wowma_catname": "インナー・ルームウェア＞レディースインナー＞ブラ＞その他ブラ","qoo_catid": "300000029","qoo_catname": "下着・レッグウェア_ブラジャー_ブラジャー"},
        "ct773": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > 補正下着 > その他", "y_ct": "2084053156","sex": "0","male": "","female": "","wowma_catid": "32071101","wowma_catname": "インナー・ルームウェア＞レディースインナー＞補正下着＞その他補正下着","qoo_catid": "300000031","qoo_catname": "下着・レッグウェア_補正下着_補正下着・ガードル"},
        "ct774": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > ストッキング > Mサイズ", "y_ct": "2084053100","sex": "0","male": "","female": "","wowma_catid": "34060307","wowma_catname": "キッズベビー・マタニティ＞マタニティ・ママ＞マタニティインナー＞ストッキング・タイツ・スパッツ","qoo_catid": "300000049","qoo_catname": "下着・レッグウェア_靴下・レッグウェア_ストッキング・タイツ"},
        "ct779": {"ctname": "オークション > ファッション > レディースファッション > 水着 > その他", "y_ct": "2084051839","sex": "0","male": "","female": "","wowma_catid": "511301","wowma_catname": "レディースファッション＞水着＞その他水着","qoo_catid": "300002269","qoo_catname": "レディースファッション_水着・ラッシュガード_ビキニ"},
        "ct780": {"ctname": "オークション > ファッション > レディースファッション > 水着 > セパレート > Mサイズ > 三角ビキニ", "y_ct": "2084211851","sex": "0","male": "","female": "","wowma_catid": "511303","wowma_catname": "レディースファッション＞水着＞ビキニ","qoo_catid": "300002269","qoo_catname": "レディースファッション_水着・ラッシュガード_ビキニ"},
        "ct781": {"ctname": "オークション > ファッション > レディースファッション > 水着 > その他", "y_ct": "2084051839","sex": "0","male": "","female": "","wowma_catid": "511301","wowma_catname": "レディースファッション＞水着＞その他水着","qoo_catid": "300002269","qoo_catname": "レディースファッション_水着・ラッシュガード_ビキニ"},
        "ct782": {"ctname": "オークション > ファッション > レディースファッション > 水着 > その他", "y_ct": "2084051839","sex": "0","male": "","female": "","wowma_catid": "511301","wowma_catname": "レディースファッション＞水着＞その他水着","qoo_catid": "300002269","qoo_catname": "レディースファッション_水着・ラッシュガード_ビキニ"},
        "ct1038": {"ctname": "オークション > スポーツ、レジャー > スポーツ別 > サーフィン > ウエア > ラッシュガード > 女性用 > Mサイズ", "y_ct": "2084304030","sex": "0","male": "","female": "","wowma_catid": "40370705","wowma_catname": "スポーツ・アウトドア＞マリンスポーツ＞マリンウェア＞ラッシュガード","qoo_catid": "300003037","qoo_catname": "レディースファッション_水着・ラッシュガード_ラッシュガード"},
        "ct775": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > 子ども服（男女兼用） > トップス > 長袖Tシャツ > 140（135～144cm）", "y_ct": "2084053319","sex": "0","male": "","female": "","wowma_catid": "34010810","wowma_catname": "キッズベビー・マタニティ＞キッズ＞子供服（トップス）＞ブラウス・シャツ","qoo_catid": "300002440","qoo_catname": "キッズ_男女兼用・その他の子供服_トップス"},
        "ct776": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > 子ども服（男女兼用） > ボトムス > パンツ、ズボン一般 > 140（135～144cm）", "y_ct": "2084053356","sex": "0","male": "","female": "","wowma_catid": "34011001","wowma_catname": "キッズベビー・マタニティ＞キッズ＞子供服（ボトムス）＞その他子供服（ボトムス）","qoo_catid": "300002441","qoo_catname": "キッズ_男女兼用・その他の子供服_ボトムス"},
        "ct1031": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > 子ども服（女の子用） > その他", "y_ct": "2084051664","sex": "0","male": "","female": "","wowma_catid": "34020802","wowma_catname": "キッズベビー・マタニティ＞ジュニア＞子供服（トップス）＞その他子供服（トップス）","qoo_catid": "320001059","qoo_catname": "キッズ_女の子ファッション_その他"},
        "ct777": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > 子ども服（男女兼用） > コート > コート一般 > 130（125～134cm）", "y_ct": "2084053283","sex": "0","male": "","female": "","wowma_catid": "34020502","wowma_catname": "キッズベビー・マタニティ＞ジュニア＞子供服（アウター）＞その他子供服（アウター）","qoo_catid": "300002442","qoo_catname": "キッズ_男女兼用・その他の子供服_アウター"},
        "ct778": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > 子ども服（男女兼用） > セット、まとめ売り", "y_ct": "2084313344","sex": "0","male": "","female": "","wowma_catid": "340101","wowma_catname": "キッズベビー・マタニティ＞キッズ＞その他キッズ","qoo_catid": "320001063","qoo_catname": "キッズ_男女兼用・その他の子供服_その他"},
        "ct1016": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > 子ども用ファッション小物 > その他", "y_ct": "2084006431","sex": "0","male": "","female": "","wowma_catid": "341001","wowma_catname": "キッズベビー・マタニティ＞子供用ファッション小物・雑貨＞その他子供用ファッション小物・雑貨","qoo_catid": "320001063","qoo_catname": "キッズ_男女兼用・その他の子供服_その他"},
        "ct1032": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > 子ども用ファッション小物 > その他", "y_ct": "2084006431","sex": "0","male": "","female": "","wowma_catid": "341001","wowma_catname": "キッズベビー・マタニティ＞子供用ファッション小物・雑貨＞その他子供用ファッション小物・雑貨","qoo_catid": "320001063","qoo_catname": "キッズ_男女兼用・その他の子供服_その他"},
    }
    """

    """
    _MY_CT_CODES_SMALL = {
        "ct676": {"ctname": "オークション > ファッション > メンズファッション > ジャケット、上着 > ライダース > Lサイズ", "y_ct": "2084243906", "sex": "0", "male": "", "female": ""},
        "ct677": {"ctname": "オークション > スポーツ、レジャー > スポーツウエア > 男性用 > パーカー", "y_ct": "2084303393", "sex": "0", "male": "", "female": ""},
        "ct678": {"ctname": "オークション > ファッション > メンズファッション > ジャケット、上着 > ジャンパー、ブルゾン > ジャンパー、ブルゾン一般 > Mサイズ", "y_ct": "2084050108", "sex": "0", "male": "", "female": ""},
        "ct679": {"ctname": "オークション > ファッション > メンズファッション > ジャケット、上着 > ジャンパー、ブルゾン > ジャンパー、ブルゾン一般 > Mサイズ", "y_ct": "2084050108", "sex": "0", "male": "", "female": ""},
        "ct680": {"ctname": "オークション > ファッション > メンズファッション > コート > コート一般 > Mサイズ", "y_ct": "2084057466", "sex": "0", "male": "", "female": ""},
        "ct681": {"ctname": "オークション > ファッション > メンズファッション > シャツ > 半袖 > 半袖シャツ一般 > Mサイズ", "y_ct": "2084064183", "sex": "0", "male": "", "female": ""},
        "ct682": {"ctname": "オークション > ファッション > メンズファッション > シャツ > 長袖 > 長袖シャツ一般 > Mサイズ ", "y_ct": "2084064178", "sex": "0", "male": "", "female": ""},
        "ct685": {"ctname": "オークション > ファッション > メンズファッション > カーディガン ", "y_ct": "2084007052", "sex": "0", "male": "","female": ""},
        "ct803": {"ctname": "オークション > ファッション > メンズファッション > シャツ > その他の袖丈", "y_ct": "2084054038", "sex": "0", "male": "","female": ""},
        "ct804": {"ctname": "オークション > ファッション > メンズファッション > トレーナー > Mサイズ", "y_ct": "2084057461", "sex": "0", "male": "","female": ""},
        "ct805": {"ctname": "オークション > ファッション > メンズファッション > パンツ、スラックス > Mサイズ", "y_ct": "2084224619", "sex": "0","male": "", "female": ""},
        "ct806": {"ctname": "オークション > ファッション > メンズファッション > インナーウエア > ボクサーブリーフ > Mサイズ", "y_ct": "2084053072", "sex": "0","male": "", "female": ""},
        "ct807": {"ctname": "オークション > ファッション > メンズファッション > 水着 > Mサイズ", "y_ct": "2084051835", "sex": "0", "male": "","female": ""},
        "ct120": {"ctname": "オークション > ファッション > レディースファッション > コート > コート一般 > Mサイズ", "y_ct": "2084057471", "sex": "0","male": "", "female": ""},
        "ct689": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > ライダース", "y_ct": "2084243900", "sex": "0","male": "", "female": ""},
        "ct690": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > その他", "y_ct": "2084005208", "sex": "0","male": "", "female": ""},
        "ct691": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > ジャンパー、ブルゾン > ジャンパー、ブルゾン一般 > Mサイズ","y_ct": "2084057481", "sex": "0", "male": "", "female": ""},
        "ct692": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > ジャケット、ブレザー > Mサイズ", "y_ct": "2084057476","sex": "0", "male": "", "female": ""},
        "ct693": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > パーカ > パーカ一般 > Mサイズ", "y_ct": "2084050490","sex": "0", "male": "", "female": ""},
        "ct694": {"ctname": "オークション > ファッション > レディースファッション > コート > コート一般 > Mサイズ", "y_ct": "2084057471", "sex": "0","male": "", "female": ""},
        "ct695": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > ジャンパー、ブルゾン > スカジャン", "y_ct": "2084052541","sex": "0", "male": "", "female": ""},
        "ct696": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > ジャンパー、ブルゾン > ジージャン > Mサイズ","y_ct": "2084054383", "sex": "0", "male": "", "female": ""},
        "ct1022": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > パーカ > パーカ一般 > Mサイズ", "y_ct": "2084050490","sex": "0", "male": "", "female": ""},
        "ct163": {"ctname": "オークション > ファッション > レディースファッション > カットソー > 長袖 > Mサイズ", "y_ct": "2084050495", "sex": "0","male": "", "female": ""},
        "ct1108": {"ctname": "オークション > ファッション > レディースファッション > カットソー > 長袖 > Mサイズ", "y_ct": "2084050495", "sex": "0","male": "", "female": ""},
        "ct698": {"ctname": "オークション > ファッション > レディースファッション > カットソー > 長袖 > Mサイズ", "y_ct": "2084050495", "sex": "0","male": "", "female": ""},
        "ct699": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > Vネック > その他", "y_ct": "2084051324","sex": "0", "male": "", "female": ""},
        "ct700": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > その他 ", "y_ct": "2084051326", "sex": "0","male": "", "female": ""},
        "ct1102": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Lサイズ > その他", "y_ct": "2084051342", "sex": "0","male": "", "female": ""},
        "ct704": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Lサイズ > その他", "y_ct": "2084051342", "sex": "0","male": "", "female": ""},
        "ct701": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > 丸首 > イラスト、キャラクター", "y_ct": "2084051314","sex": "0", "male": "", "female": ""},
        "ct702": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > その他の袖丈", "y_ct": "2084054032", "sex": "0","male": "", "female": ""},
        "ct1107": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > その他", "y_ct": "2084051326", "sex": "0","male": "", "female": ""},
        "ct703": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > その他", "y_ct": "2084051326", "sex": "0","male": "", "female": ""},
        "ct1111": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > Vネック > 柄もの", "y_ct": "2084051321","sex": "0", "male": "", "female": ""},
        "ct1112": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > 丸首 > 文字、ロゴ", "y_ct": "2084051317","sex": "0", "male": "", "female": ""},
        "ct705": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486", "sex": "0","male": "", "female": ""},
        "ct706": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ ", "y_ct": "2084057486", "sex": "0","male": "", "female": ""},
        "ct707": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486", "sex": "0","male": "", "female": ""},
        "ct708": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486", "sex": "0","male": "", "female": ""},
        "ct1045": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486", "sex": "0","male": "", "female": ""},
        "ct1044": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486", "sex": "0","male": "", "female": ""},
        "ct709": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486", "sex": "0","male": "", "female": ""},
        "ct710": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486", "sex": "0","male": "", "female": ""},
        "ct711": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486", "sex": "0","male": "", "female": ""},
        "ct715": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486", "sex": "0","male": "", "female": ""},
        "ct712": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > その他", "y_ct": "2084051326", "sex": "0","male": "", "female": ""},
        "ct713": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > 半袖 > Mサイズ > その他", "y_ct": "2084051326", "sex": "0","male": "", "female": ""},
        "ct714": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 半袖 > Mサイズ", "y_ct": "2084064237", "sex": "0","male": "", "female": ""},
        "ct716": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 袖なし、ノースリーブ > ノースリーブシャツ一般", "y_ct": "2084027443","sex": "0", "male": "", "female": ""},
        "ct717": {"ctname": "オークション > ファッション > レディースファッション > キャミソール", "y_ct": "2084064258", "sex": "0", "male": "","female": ""},
        "ct719": {"ctname": "オークション > ファッション > レディースファッション > チュニック > 袖なし、ノースリーブ > Mサイズ", "y_ct": "2084231772","sex": "0", "male": "", "female": ""},
        "ct1110": {"ctname": "オークション > ファッション > レディースファッション > チューブトップ、ベアトップ", "y_ct": "2084243344", "sex": "0","male": "", "female": ""},
        "ct162": {"ctname": "オークション > ファッション > レディースファッション > カーディガン > Mサイズ", "y_ct": "2084064209", "sex": "0","male": "", "female": ""},
        "ct720": {"ctname": "オークション > ファッション > レディースファッション > カーディガン > Mサイズ", "y_ct": "2084064209", "sex": "0","male": "", "female": ""},
        "ct721": {"ctname": "オークション > ファッション > レディースファッション > カーディガン > Mサイズ", "y_ct": "2084064209", "sex": "0","male": "", "female": ""},
        "ct722": {"ctname": "オークション > ファッション > レディースファッション > ニット、セーター > 長袖 > Mサイズ", "y_ct": "2084064247", "sex": "0","male": "", "female": ""},
        "ct723": {"ctname": "オークション > ファッション > レディースファッション > ニット、セーター > 長袖 > Mサイズ", "y_ct": "2084064247", "sex": "0","male": "", "female": ""},
        "ct724": {"ctname": "オークション > ファッション > レディースファッション > ニット、セーター > 長袖 > Mサイズ", "y_ct": "2084064247", "sex": "0","male": "", "female": ""},
        "ct725": {"ctname": "オークション > ファッション > レディースファッション > ニット、セーター > 長袖 > Mサイズ", "y_ct": "2084064247", "sex": "0","male": "", "female": ""},
        "ct726": {"ctname": "オークション > ファッション > レディースファッション > カーディガン > Mサイズ", "y_ct": "2084064209", "sex": "0","male": "", "female": ""},
        "ct727": {"ctname": "オークション > ファッション > レディースファッション > カーディガン > Mサイズ", "y_ct": "2084064209", "sex": "0","male": "", "female": ""},
        "ct122": {"ctname": "オークション > ファッション > レディースファッション > パンツ、スラックス > Mサイズ", "y_ct": "2084224590", "sex": "0","male": "", "female": ""},
        "ct728": {"ctname": "オークション > ファッション > レディースファッション > パンツ、スラックス > Mサイズ", "y_ct": "2084224590", "sex": "0","male": "", "female": ""},
        "ct1008": {"ctname": "オークション > ファッション > レディースファッション > レギンス、トレンカ", "y_ct": "2084007161", "sex": "0", "male": "","female": ""},
        "ct1009": {"ctname": "オークション > ファッション > レディースファッション > ワークパンツ、ペインターパンツ > Mサイズ", "y_ct": "2084224605", "sex": "0","male": "", "female": ""},
        "ct1010": {"ctname": "オークション > ファッション > レディースファッション > ワークパンツ、ペインターパンツ > Mサイズ", "y_ct": "2084224605", "sex": "0","male": "", "female": ""},
        "ct1047": {"ctname": "オークション > ファッション > レディースファッション > パンツ、スラックス > Mサイズ", "y_ct": "2084224590", "sex": "0","male": "", "female": ""},
        "ct738": {"ctname": "オークション > ファッション > レディースファッション > スカート > ロングスカート > その他", "y_ct": "2084007175", "sex": "0","male": "", "female": ""},
        "ct739": {"ctname": "オークション > ファッション > レディースファッション > スカート > ロングスカート > その他", "y_ct": "2084007175", "sex": "0","male": "", "female": ""},
        "ct740": {"ctname": "オークション > ファッション > レディースファッション > スカート > ロングスカート > その他", "y_ct": "2084007175", "sex": "0","male": "", "female": ""},
        "ct741": {"ctname": "オークション > ファッション > レディースファッション > スカート > ミニスカート > その他", "y_ct": "2084007171", "sex": "0","male": "", "female": ""},
        "ct742": {"ctname": "オークション > ファッション > レディースファッション > スカート > ミニスカート > タイトスカート > Mサイズ", "y_ct": "2084222253","sex": "0", "male": "", "female": ""},
        "ct743": {"ctname": "オークション > ファッション > レディースファッション > スカート > ひざ丈スカート > その他", "y_ct": "2084054014", "sex": "0","male": "", "female": ""},
        "ct744": {"ctname": "オークション > ファッション > レディースファッション > スカート > ひざ丈スカート > プリーツスカート > Mサイズ", "y_ct": "2084222283","sex": "0", "male": "", "female": ""},
        "ct745": {"ctname": "オークション > ファッション > レディースファッション > スカート > ひざ丈スカート > フレアースカート、ギャザースカート > Mサイズ","y_ct": "2084222278", "sex": "0", "male": "", "female": ""},
        "ct746": {"ctname": "オークション > ファッション > レディースファッション > スカート > ひざ丈スカート > タイトスカート > Mサイズ", "y_ct": "2084222273","sex": "0", "male": "", "female": ""},
        "ct747": {"ctname": "オークション > ファッション > レディースファッション > スカート > ひざ丈スカート > その他", "y_ct": "2084054014", "sex": "0","male": "", "female": ""},
        "ct748": {"ctname": "オークション > ファッション > レディースファッション > スカート > ロングスカート > その他", "y_ct": "2084007175", "sex": "0","male": "", "female": ""},
        "ct754": {"ctname": "オークション > ファッション > レディースファッション > スカート > ロングスカート > フレアースカート、ギャザースカート > Mサイズ","y_ct": "2084222298", "sex": "0", "male": "", "female": ""},
        "ct156": {"ctname": "オークション > ファッション > レディースファッション > ワンピース > ミニスカート > Mサイズ", "y_ct": "2084224575", "sex": "0","male": "", "female": ""},
        "ct749": {"ctname": "オークション > ファッション > レディースファッション > ワンピース > ロングスカート > Mサイズ", "y_ct": "2084224585", "sex": "0","male": "", "female": ""},
        "ct750": {"ctname": "オークション > ファッション > レディースファッション > ワンピース > ロングスカート > Mサイズ", "y_ct": "2084224585", "sex": "0","male": "", "female": ""},
        "ct751": {"ctname": "オークション > ファッション > レディースファッション > ワンピース > ロングスカート > Mサイズ", "y_ct": "2084224585", "sex": "0","male": "", "female": ""},
        "ct752": {"ctname": "オークション > ファッション > レディースファッション > ワンピース > ミニスカート > Mサイズ", "y_ct": "2084224575", "sex": "0","male": "", "female": ""},
        "ct753": {"ctname": "オークション > ファッション > レディースファッション > フォーマル > ワンピース", "y_ct": "2084037008", "sex": "0","male": "", "female": ""},
        "ct755": {"ctname": "オークション > ファッション > レディースファッション > フォーマル > ワンピース", "y_ct": "2084037008", "sex": "0","male": "", "female": ""},
        "ct756": {"ctname": "オークション > ファッション > レディースファッション > フォーマル > ワンピース", "y_ct": "2084037008", "sex": "0","male": "", "female": ""},
        "ct757": {"ctname": "オークション > ファッション > レディースファッション > フォーマル > ワンピース", "y_ct": "2084037008", "sex": "0","male": "", "female": ""},
        "ct758": {"ctname": "オークション > ファッション > レディースファッション > フォーマル > ワンピース", "y_ct": "2084037008", "sex": "0","male": "", "female": ""},
        "ct759": {"ctname": "オークション > ファッション > レディースファッション > フォーマル > ワンピース", "y_ct": "2084037008", "sex": "0","male": "", "female": ""},
        "ct760": {"ctname": "オークション > ファッション > レディースファッション > フォーマル > ワンピース", "y_ct": "2084037008", "sex": "0","male": "", "female": ""},
        "ct761": {"ctname": "オークション > ファッション > レディースファッション > フォーマル > ワンピース", "y_ct": "2084037008", "sex": "0","male": "", "female": ""},
        "ct762": {"ctname": "オークション > ファッション > レディースファッション > フォーマル > ワンピース", "y_ct": "2084037008", "sex": "0","male": "", "female": ""},
        "ct1453": {"ctname": "オークション > ファッション > レディースファッション > フォーマル > ワンピース", "y_ct": "2084037008", "sex": "0","male": "", "female": ""},
        "ct765": {"ctname": "オークション > スポーツ、レジャー > スポーツウエア > 女性用 > 上下セット > ジャージ > その他", "y_ct": "2084203510", "sex": "0","male": "", "female": ""},
        "ct763": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > その他", "y_ct": "2084053158", "sex": "0","male": "", "female": ""},
        "ct767": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > ブラジャー > その他", "y_ct": "2084053090", "sex": "0","male": "", "female": ""},
        "ct1109": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > その他", "y_ct": "2084053158", "sex": "0","male": "", "female": ""},
        "ct768": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > ブラジャー > その他", "y_ct": "2084053090", "sex": "0","male": "", "female": ""},
        "ct769": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > ブラジャー > その他", "y_ct": "2084053090", "sex": "0","male": "", "female": ""},
        "ct770": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > ショーツ > Mサイズ > スタンダード", "y_ct": "2084211818","sex": "0", "male": "", "female": ""},
        "ct771": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > スリップ > Mサイズ", "y_ct": "2084053118", "sex": "0","male": "", "female": ""},
        "ct772": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > ブラジャー > その他", "y_ct": "2084053090", "sex": "0","male": "", "female": ""},
        "ct773": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > 補正下着 > その他", "y_ct": "2084053156", "sex": "0","male": "", "female": ""},
        "ct774": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > ストッキング > Mサイズ", "y_ct": "2084053100", "sex": "0","male": "", "female": ""},
        "ct779": {"ctname": "オークション > ファッション > レディースファッション > 水着 > その他", "y_ct": "2084051839", "sex": "0", "male": "","female": ""},
        "ct780": {"ctname": "オークション > ファッション > レディースファッション > 水着 > セパレート > Mサイズ > 三角ビキニ", "y_ct": "2084211851","sex": "0", "male": "", "female": ""},
        "ct781": {"ctname": "オークション > ファッション > レディースファッション > 水着 > その他", "y_ct": "2084051839", "sex": "0", "male": "","female": ""},
        "ct782": {"ctname": "オークション > ファッション > レディースファッション > 水着 > その他", "y_ct": "2084051839", "sex": "0", "male": "","female": ""},
        "ct1038": {"ctname": "オークション > スポーツ、レジャー > スポーツ別 > サーフィン > ウエア > ラッシュガード > 女性用 > Mサイズ", "y_ct": "2084304030","sex": "0", "male": "", "female": ""},
        "ct775": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > 子ども服（男女兼用） > トップス > 長袖Tシャツ > 140（135～144cm）","y_ct": "2084053319", "sex": "0", "male": "", "female": ""},
        "ct776": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > 子ども服（男女兼用） > ボトムス > パンツ、ズボン一般 > 140（135～144cm）","y_ct": "2084053356", "sex": "0", "male": "", "female": ""},
        "ct1031": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > 子ども服（女の子用） > その他", "y_ct": "2084051664", "sex": "0","male": "", "female": ""},
        "ct777": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > 子ども服（男女兼用） > コート > コート一般 > 130（125～134cm）","y_ct": "2084053283", "sex": "0", "male": "", "female": ""},
        "ct778": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > 子ども服（男女兼用） > セット、まとめ売り", "y_ct": "2084313344","sex": "0", "male": "", "female": ""},
        "ct1016": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > 子ども用ファッション小物 > その他", "y_ct": "2084006431", "sex": "0","male": "", "female": ""},
        "ct1032": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > 子ども用ファッション小物 > その他", "y_ct": "2084006431", "sex": "0","male": "", "female": ""},
        "ct784": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > 子ども服（男の子用） > その他", "y_ct": "2084051663", "sex": "0","male": "", "female": ""},
        "ct785": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > ベビー服 > ボトムス > ロンパース > 80（75～84cm）", "y_ct": "2084052490","sex": "0", "male": "", "female": ""},
        "ct786": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > ベビー服 > トップス > Tシャツ > 長袖 > 男女兼用 > 90（85～94cm）","y_ct": "2084053373", "sex": "0", "male": "", "female": ""},
        "ct787": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > ベビー服 > ボトムス > その他", "y_ct": "2084042011", "sex": "0","male": "", "female": ""},
        "ct788": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > ベビー服 > コート、ジャンパー > コート > 男女兼用 > 90（85～94cm）","y_ct": "2084053362", "sex": "0", "male": "", "female": ""},
        "ct789": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > ベビー用ファッション小物 > スタイ、よだれかけ", "y_ct": "2084007257","sex": "0", "male": "", "female": ""},
        "ct790": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > ベビー服 > 水着 > 女の子用 > 90（85～94cm）", "y_ct": "2084051882","sex": "0", "male": "", "female": ""},
        "ct791": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > ベビー用ファッション小物 > その他", "y_ct": "2084007258", "sex": "0","male": "", "female": ""},
        "ct792": {"ctname": "オークション > ファッション > レディースファッション > マタニティウエア > その他", "y_ct": "2084006313", "sex": "0","male": "", "female": ""},
        "ct795": {"ctname": "オークション > コミック、アニメグッズ > コスプレ衣装 > その他", "y_ct": "2084208673", "sex": "0", "male": "","female": ""},
        "ct1028": {"ctname": "オークション > コミック、アニメグッズ > コスプレ衣装 > 男性用", "y_ct": "2084241340", "sex": "0", "male": "","female": ""},
        "ct1029": {"ctname": "オークション > コミック、アニメグッズ > コスプレ衣装 > その他", "y_ct": "2084208673", "sex": "0", "male": "","female": ""},
        "ct1030": {"ctname": "オークション > コミック、アニメグッズ > コスプレ衣装 > その他", "y_ct": "2084208673", "sex": "0", "male": "","female": ""},
        "ct796": {"ctname": "オークション > コミック、アニメグッズ > コスプレ衣装 > コミック、アニメ、ゲームキャラクター > コスプレ衣装", "y_ct": "2084311485","sex": "0", "male": "", "female": ""},
        "ct797": {"ctname": "オークション > コミック、アニメグッズ > コスプレ衣装 > コミック、アニメ、ゲームキャラクター > 衣装一式", "y_ct": "2084311486","sex": "0", "male": "", "female": ""},
        "ct798": {"ctname": "オークション > コミック、アニメグッズ > コスプレ衣装 > コミック、アニメ、ゲームキャラクター > 衣装一式", "y_ct": "2084311486","sex": "0", "male": "", "female": ""},
        "ct799": {"ctname": "オークション > コミック、アニメグッズ > コスプレ衣装 > コミック、アニメ、ゲームキャラクター > アクセサリー、小物", "y_ct": "2084311489","sex": "0", "male": "", "female": ""},
        "ct1000": {"ctname": "オークション > コミック、アニメグッズ > コスプレ衣装 > コミック、アニメ、ゲームキャラクター > インナー", "y_ct": "2084311488","sex": "0", "male": "", "female": ""},
        "ct800": {"ctname": "オークション > コミック、アニメグッズ > コスプレ衣装 > その他", "y_ct": "2084208673", "sex": "0", "male": "","female": ""},
        "ct801": {"ctname": "オークション > ファッション > ファッション小物 > 帽子 > 男性用 > その他", "y_ct": "2084006684", "sex": "0", "male": "","female": ""},
        "ct826": {"ctname": "オークション > ファッション > ファッション小物 > 帽子 > 男性用 > その他", "y_ct": "2084006684", "sex": "0", "male": "","female": ""},
        "ct828": {"ctname": "オークション > スポーツ、レジャー > スポーツ別 > ゴルフ > ウエア（男性用） > キャップ > その他", "y_ct": "2084208718","sex": "0", "male": "", "female": ""},
        "ct829": {"ctname": "オークション > スポーツ、レジャー > スポーツ別 > ゴルフ > ウエア（男性用） > ニット帽", "y_ct": "2084262354", "sex": "0","male": "", "female": ""},
        "ct1026": {"ctname": "オークション > ファッション > ファッション小物 > 帽子 > 男性用 > その他", "y_ct": "2084006684", "sex": "0","male": "", "female": ""},
        "ct830": {"ctname": "オークション > ファッション > ファッション小物 > 帽子 > 女性用 > ワッチキャップ、ニットキャップ", "y_ct": "2084006693", "sex": "0","male": "", "female": ""},
        "ct831": {"ctname": "オークション > ファッション > ファッション小物 > 帽子 > 女性用 > ワッチキャップ、ニットキャップ", "y_ct": "2084006693", "sex": "0","male": "", "female": ""},
        "ct832": {"ctname": "オークション > ファッション > ファッション小物 > 帽子 > 女性用 > ワッチキャップ、ニットキャップ", "y_ct": "2084006693", "sex": "0","male": "", "female": ""},
        "ct833": {"ctname": "オークション > ファッション > ファッション小物 > 帽子 > 女性用 > テンガロンハット、ウエスタンハット", "y_ct": "2084006692","sex": "0", "male": "", "female": ""},
        "ct834": {"ctname": "オークション > ファッション > ファッション小物 > 帽子 > 女性用 > 麦わら帽子", "y_ct": "2084006695", "sex": "0","male": "", "female": ""},
        "ct1024": {"ctname": "オークション > ファッション > ファッション小物 > 帽子 > 女性用 > キャスケット", "y_ct": "2084243504", "sex": "0","male": "", "female": ""},
        "ct1025": {"ctname": "オークション > ファッション > ファッション小物 > 帽子 > 女性用 > ベレー帽", "y_ct": "2084006694", "sex": "0","male": "", "female": ""},
        "ct1154": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > 子ども用ファッション小物 > 帽子", "y_ct": "2084006429", "sex": "0","male": "", "female": ""},
        "ct1050": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ウイッグ > その他", "y_ct": "2084062532","sex": "0", "male": "", "female": ""},
        "ct1051": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ウイッグ > ショート", "y_ct": "2084062531","sex": "0", "male": "", "female": ""},
        "ct1052": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ウイッグ > ロング", "y_ct": "2084062528","sex": "0", "male": "", "female": ""},
        "ct1053": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ウイッグ > その他", "y_ct": "2084062532","sex": "0", "male": "", "female": ""},
        "ct1054": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ウイッグ > その他", "y_ct": "2084062532","sex": "0", "male": "", "female": ""},
        "ct1017": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > その他", "y_ct": "2084005387", "sex": "0","male": "", "female": ""},
        "ct1018": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ヘアゴム、シュシュ", "y_ct": "2084019052","sex": "0", "male": "", "female": ""},
        "ct1019": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > その他", "y_ct": "2084005387", "sex": "0","male": "", "female": ""},
        "ct1020": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ヘアバンド、カチューシャ", "y_ct": "2084019051","sex": "0", "male": "", "female": ""},
        "ct1021": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ヘアバンド、カチューシャ", "y_ct": "2084019051","sex": "0", "male": "", "female": ""},
        "ct1011": {"ctname": "オークション > ビューティー、ヘルスケア > めがね、コンタクト > その他", "y_ct": "2084042537", "sex": "0", "male": "","female": ""},
        "ct1012": {"ctname": "オークション > スポーツ、レジャー > スポーツサングラス > その他", "y_ct": "2084214056", "sex": "0", "male": "","female": ""},
        "ct1013": {"ctname": "オークション > ビューティー、ヘルスケア > めがね、コンタクト > その他", "y_ct": "2084042537", "sex": "0", "male": "","female": ""},
        "ct1014": {"ctname": "オークション > ビューティー、ヘルスケア > めがね、コンタクト > 老眼鏡", "y_ct": "2084042533", "sex": "0", "male": "","female": ""},
        "ct1015": {"ctname": "オークション > おもちゃ、ゲーム > 手品、パーティグッズ > パーティグッズ > その他", "y_ct": "2084059858", "sex": "0","male": "", "female": ""},
        "ct1055": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > その他", "y_ct": "2084062070", "sex": "0", "male": "","female": ""},
        "ct1056": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > イヤリング > その他", "y_ct": "2084005416", "sex": "0","male": "", "female": ""},
        "ct1061": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > その他", "y_ct": "2084062070", "sex": "0", "male": "","female": ""},
        "ct1062": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > イヤリング > その他", "y_ct": "2084005416", "sex": "0","male": "", "female": ""},
        "ct1057": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > ピアス > その他", "y_ct": "2084062576", "sex": "0", "male": "","female": ""},
        "ct1064": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ピアス > その他", "y_ct": "2084005423", "sex": "0","male": "", "female": ""},
        "ct1074": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ピアス > その他", "y_ct": "2084005423", "sex": "0","male": "", "female": ""},
        "ct1075": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ピアス > その他", "y_ct": "2084005423", "sex": "0","male": "", "female": ""},
        "ct1076": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ピアス > その他", "y_ct": "2084005423", "sex": "0","male": "", "female": ""},
        "ct1077": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ピアス > その他", "y_ct": "2084005423", "sex": "0","male": "", "female": ""},
        "ct1078": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ピアス > その他", "y_ct": "2084005423", "sex": "0","male": "", "female": ""},
        "ct1079": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ピアス > その他", "y_ct": "2084005423", "sex": "0","male": "", "female": ""},
        "ct1058": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > ネックレス > その他", "y_ct": "2084006915", "sex": "0","male": "", "female": ""},
        "ct1065": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > ネックレス > その他", "y_ct": "2084006915", "sex": "0","male": "", "female": ""},
        "ct1080": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > ネックレス > その他", "y_ct": "2084006915", "sex": "0","male": "", "female": ""},
        "ct1081": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > ネックレス > その他", "y_ct": "2084006915", "sex": "0","male": "", "female": ""},
        "ct1066": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ネックレス、ペンダント > その他", "y_ct": "2084005400", "sex": "0","male": "", "female": ""},
        "ct1082": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ネックレス、ペンダント > その他", "y_ct": "2084005400", "sex": "0","male": "", "female": ""},
        "ct1083": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > チョーカー > その他", "y_ct": "2084005394", "sex": "0","male": "", "female": ""},
        "ct1084": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ネックレス、ペンダント > その他", "y_ct": "2084005400", "sex": "0","male": "", "female": ""},
        "ct1085": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ネックレス、ペンダント > その他", "y_ct": "2084005400", "sex": "0","male": "", "female": ""},
        "ct1086": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ネックレス、ペンダント > ダイヤモンド > その他", "y_ct": "2084209780","sex": "0", "male": "", "female": ""},
        "ct1087": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ネックレス、ペンダント > その他", "y_ct": "2084005400", "sex": "0","male": "", "female": ""},
        "ct1059": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > ブレスレット、バングル > その他", "y_ct": "2084052636", "sex": "0","male": "", "female": ""},
        "ct1068": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > ブレスレット、バングル > その他", "y_ct": "2084052636", "sex": "0","male": "", "female": ""},
        "ct1088": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > ブレスレット、バングル > その他", "y_ct": "2084052636", "sex": "0","male": "", "female": ""},
        "ct1089": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > ブレスレット、バングル > バングル > その他", "y_ct": "2084062608","sex": "0", "male": "", "female": ""},
        "ct1090": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > ブレスレット、バングル > その他", "y_ct": "2084052636", "sex": "0","male": "", "female": ""},
        "ct1069": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > ブレスレット、バングル > その他", "y_ct": "2084052636", "sex": "0","male": "", "female": ""},
        "ct1091": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > ブレスレット、バングル > その他", "y_ct": "2084052636", "sex": "0","male": "", "female": ""},
        "ct1092": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ブレスレット、バングル > バングル > その他", "y_ct": "2084019059","sex": "0", "male": "", "female": ""},
        "ct1093": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > アンクレット > その他", "y_ct": "2084062566", "sex": "0","male": "", "female": ""},
        "ct1094": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > アンクレット > その他", "y_ct": "2084062566", "sex": "0","male": "", "female": ""},
        "ct1060": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > 指輪 > その他", "y_ct": "2084049294", "sex": "0", "male": "","female": ""},
        "ct1070": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > 指輪 > その他", "y_ct": "2084049294", "sex": "0", "male": "","female": ""},
        "ct1071": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > 指輪 > その他", "y_ct": "2084005435", "sex": "0","male": "", "female": ""},
        "ct1095": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > 指輪 > ゴールド > その他", "y_ct": "2084052678", "sex": "0","male": "", "female": ""},
        "ct1096": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > 指輪 > その他", "y_ct": "2084005435", "sex": "0","male": "", "female": ""},
        "ct1097": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > 指輪 > その他", "y_ct": "2084005435", "sex": "0","male": "", "female": ""},
        "ct1158": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ブローチ > その他", "y_ct": "2084005380", "sex": "0","male": "", "female": ""},
        "ct794": {"ctname": "オークション > ファッション > ファッション小物 > マフラー > 女性用 > マフラー一般", "y_ct": "2084006464", "sex": "0","male": "", "female": ""},
        "ct819": {"ctname": "オークション > ファッション > ファッション小物 > ストール > ストール一般", "y_ct": "2084006466", "sex": "0", "male": "","female": ""},
        "ct821": {"ctname": "オークション > ファッション > ファッション小物 > マフラー > 男性用", "y_ct": "2084006472", "sex": "0", "male": "","female": ""},
        "ct822": {"ctname": "オークション > ファッション > ファッション小物 > ストール > ストール一般", "y_ct": "2084006466", "sex": "0", "male": "","female": ""},
        "ct820": {"ctname": "オークション > ファッション > ファッション小物 > マフラー > 女性用 > マフラー一般", "y_ct": "2084006464", "sex": "0","male": "", "female": ""},
        "ct823": {"ctname": "オークション > ファッション > ファッション小物 > マフラー > 女性用 > マフラー一般", "y_ct": "2084006464", "sex": "0","male": "", "female": ""},
        "ct824": {"ctname": "オークション > ファッション > ファッション小物 > ストール > ストール一般", "y_ct": "2084006466", "sex": "0", "male": "","female": ""},
        "ct810": {"ctname": "オークション > ファッション > レディースバッグ > ハンドバッグ > その他", "y_ct": "2084051024", "sex": "0", "male": "","female": ""},
        "ct848": {"ctname": "オークション > スポーツ、レジャー > キャンプ、アウトドア用品 > バックパック、かばん > リュックサック > バックパック", "y_ct": "2084057274","sex": "0", "male": "", "female": ""},
        "ct849": {"ctname": "オークション > ファッション > 男女兼用バッグ > リュックサック、デイパック", "y_ct": "2084233233", "sex": "0", "male": "","female": ""},
        "ct850": {"ctname": "オークション > ファッション > 男女兼用バッグ > ショルダーバッグ", "y_ct": "2084233231", "sex": "0", "male": "","female": ""},
        "ct851": {"ctname": "オークション > スポーツ、レジャー > 自転車、サイクリング > バッグ > メッセンジャーバッグ", "y_ct": "2084227171", "sex": "0","male": "", "female": ""},
        "ct852": {"ctname": "オークション > ファッション > メンズバッグ > ボディバッグ", "y_ct": "2084008349", "sex": "0", "male": "","female": ""},
        "ct853": {"ctname": "オークション > 事務、店舗用品 > バッグ、スーツケース > スーツケース、トランク > スーツケース、トランク一般", "y_ct": "2084062327","sex": "0", "male": "", "female": ""},
        "ct854": {"ctname": "オークション > ファッション > レディースバッグ > クラッチバッグ、パーティバッグ", "y_ct": "2084008347", "sex": "0","male": "", "female": ""},
        "ct855": {"ctname": "オークション > ファッション > レディースバッグ > ハンドバッグ > その他", "y_ct": "2084051024", "sex": "0", "male": "","female": ""},
        "ct856": {"ctname": "オークション > ファッション > 男女兼用バッグ > トートバッグ", "y_ct": "2084233232", "sex": "0", "male": "","female": ""},
        "ct858": {"ctname": "オークション > ファッション > レディースバッグ > ポーチ", "y_ct": "2084007482", "sex": "0", "male": "","female": ""},
        "ct1005": {"ctname": "オークション > ファッション > レディースバッグ > ショルダーバッグ > その他", "y_ct": "2084051009", "sex": "0","male": "", "female": ""},
        "ct1006": {"ctname": "オークション > ファッション > レディースバッグ > ショルダーバッグ > その他", "y_ct": "2084051009", "sex": "0","male": "", "female": ""},
        "ct1007": {"ctname": "オークション > ファッション > レディースバッグ > ショルダーバッグ > その他", "y_ct": "2084051009", "sex": "0","male": "", "female": ""},
        "ct1462": {"ctname": "オークション > ファッション > 男女兼用バッグ > ボストンバッグ", "y_ct": "2084233234", "sex": "0", "male": "","female": ""},
        "ct1463": {"ctname": "オークション > ファッション > 男女兼用バッグ > エコバッグ", "y_ct": "2084233235", "sex": "0", "male": "","female": ""},
        "ct838": {"ctname": "オークション > アクセサリー、時計 > メンズ腕時計 > デジタル > その他", "y_ct": "2084223447", "sex": "0", "male": "","female": ""},
        "ct839": {"ctname": "オークション > アクセサリー、時計 > レディース腕時計 > デジタル > その他", "y_ct": "2084223405", "sex": "0", "male": "","female": ""},
        "ct840": {"ctname": "オークション > アクセサリー、時計 > ユニセックス腕時計 > デジタル > その他", "y_ct": "2084223426", "sex": "0", "male": "","female": ""},
        "ct841": {"ctname": "オークション > アクセサリー、時計 > ユニセックス腕時計 > デジタル > その他", "y_ct": "2084223426", "sex": "0", "male": "","female": ""},
        "ct808": {"ctname": "オークション > ファッション > ファッション小物 > 財布 > 男性用 > その他", "y_ct": "2084292136", "sex": "0", "male": "","female": ""},
        "ct842": {"ctname": "オークション > ファッション > ファッション小物 > 財布 > 男性用 > その他", "y_ct": "2084292136", "sex": "0", "male": "","female": ""},
        "ct843": {"ctname": "オークション > ファッション > ファッション小物 > 財布 > 男性用 > 長財布（小銭入れあり）", "y_ct": "2084292126", "sex": "0","male": "", "female": ""},
        "ct844": {"ctname": "オークション > ファッション > ファッション小物 > 財布 > 男性用 > 二つ折り財布（小銭入れあり）", "y_ct": "2084292128", "sex": "0","male": "", "female": ""},
        "ct836": {"ctname": "オークション > ファッション > ファッション小物 > 財布 > 女性用 > その他", "y_ct": "2084292137", "sex": "0", "male": "","female": ""},
        "ct845": {"ctname": "オークション > ファッション > ファッション小物 > 財布 > 女性用 > 長財布（小銭入れあり）", "y_ct": "2084292116", "sex": "0","male": "", "female": ""},
        "ct846": {"ctname": "オークション > ファッション > ファッション小物 > 財布 > 女性用 > 二つ折り財布（小銭入れあり）", "y_ct": "2084292118", "sex": "0","male": "", "female": ""},
        "ct837": {"ctname": "オークション > ファッション > ファッション小物 > 財布 > 男性用 > その他", "y_ct": "2084292136", "sex": "0", "male": "","female": ""},
        "ct847": {"ctname": "オークション > ファッション > ファッション小物 > 財布 > 女性用 > その他", "y_ct": "2084292137", "sex": "0", "male": "","female": ""},
        "ct811": {"ctname": "オークション > ファッション > メンズシューズ > その他", "y_ct": "2084005486", "sex": "0", "male": "","female": ""},
        "ct859": {"ctname": "オークション > ファッション > メンズシューズ > その他", "y_ct": "2084005486", "sex": "0", "male": "","female": ""},
        "ct860": {"ctname": "オークション > ファッション > レディースシューズ > その他", "y_ct": "2084005499", "sex": "0", "male": "","female": ""},
        "ct861": {"ctname": "オークション > ファッション > キッズ、ベビーファッション > ベビーシューズ > スニーカー > 14cm～", "y_ct": "2084053796","sex": "0", "male": "", "female": ""},
        "ct1104": {"ctname": "オークション > ファッション > レディースシューズ > その他", "y_ct": "2084005499", "sex": "0", "male": "","female": ""},
        "ct793": {"ctname": "オークション > ファッション > ファッション小物 > スカーフ、ポケットチーフ > 女性用", "y_ct": "2084006442", "sex": "0","male": "", "female": ""},
        "ct1027": {"ctname": "オークション > ファッション > ファッション小物 > 手袋 > 女性用 > その他", "y_ct": "2084214886", "sex": "0","male": "", "female": ""},
        "ct1033": {"ctname": "オークション > ファッション > ファッション小物 > ベルト > 男性用 > その他", "y_ct": "2084214922", "sex": "0","male": "", "female": ""},
        "ct809": {"ctname": "オークション > ファッション > ファッション小物 > キーケース", "y_ct": "2084012476", "sex": "0", "male": "","female": ""},
        "ct1023": {"ctname": "オークション > ファッション > ファッション小物 > 名刺入れ、カードケース > 男性用", "y_ct": "2084246781", "sex": "0","male": "", "female": ""},
        "ct908": {"ctname": "オークション > 住まい、インテリア > 家具、インテリア > 鏡台、ドレッサー", "y_ct": "2084005506", "sex": "0", "male": "","female": ""},
        "ct909": {"ctname": "オークション > 住まい、インテリア > 家具、インテリア > カーテン、ブラインド > カーテン > その他", "y_ct": "2084238440", "sex": "0","male": "", "female": ""},
        "ct910": {"ctname": "オークション > 住まい、インテリア > 家具、インテリア > カーテン、ブラインド > カーテン > その他", "y_ct": "2084238440", "sex": "0","male": "", "female": ""},
        "ct911": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > 収納、キッチン雑貨 > その他", "y_ct": "2084018482", "sex": "0","male": "", "female": ""},
        "ct912": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > 収納、キッチン雑貨 > その他", "y_ct": "2084018482", "sex": "0","male": "", "female": ""},
        "ct913": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > テーブルリネン > テーブルクロス", "y_ct": "2084046784", "sex": "0","male": "", "female": ""},
        "ct914": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > 食器 > 洋食器 > プレート、皿 > その他", "y_ct": "2084005701", "sex": "0","male": "", "female": ""},
        "ct915": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > 収納、キッチン雑貨 > その他", "y_ct": "2084018482", "sex": "0","male": "", "female": ""},
        "ct1098": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > 調理器具 > その他", "y_ct": "2084005977", "sex": "0", "male": "","female": ""},
        "ct1106": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > バス > その他", "y_ct": "2084024452", "sex": "0", "male": "","female": ""},
        "ct1037": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > スリッパ", "y_ct": "2084047779", "sex": "0", "male": "","female": ""},
        "ct916": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > タオル > その他", "y_ct": "2084006327", "sex": "0", "male": "","female": ""},
        "ct917": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > タオル > バスタオル", "y_ct": "2084006328", "sex": "0", "male": "","female": ""},
        "ct919": {"ctname": "オークション > ファッション > ファッション小物 > エプロン", "y_ct": "2084018499", "sex": "0", "male": "","female": ""},
        "ct920": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > 収納、キッチン雑貨 > その他", "y_ct": "2084018482", "sex": "0","male": "", "female": ""},
        "ct1105": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > 収納、キッチン雑貨 > その他", "y_ct": "2084018482", "sex": "0","male": "", "female": ""},
        "ct63": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > 収納、キッチン雑貨 > その他", "y_ct": "2084018482", "sex": "0","male": "", "female": ""},
        "ct54": {"ctname": "オークション > コンピュータ > 周辺機器 > その他", "y_ct": "2084048551", "sex": "0", "male": "", "female": ""},
        "ct56": {"ctname": "オークション > 家電、AV、カメラ > 家庭用電化製品 > その他", "y_ct": "2084061709", "sex": "0", "male": "","female": ""},
        "ct922": {"ctname": "オークション > 家電、AV、カメラ > 冷暖房、空調 > 加湿器、除湿器 > 加湿器 > その他", "y_ct": "2084239049", "sex": "0","male": "", "female": ""},
        "ct923": {"ctname": "オークション > 家電、AV、カメラ > 冷暖房、空調 > 扇風機", "y_ct": "2084008361", "sex": "0", "male": "","female": ""},
        "ct1977": {"ctname": "オークション > 家電、AV、カメラ > オーディオ機器 > ヘッドフォン、イヤフォン > イヤフォン > その他", "y_ct": "2084219572","sex": "0", "male": "", "female": ""},
        "ct981": {"ctname": "オークション > 家電、AV、カメラ > オーディオ機器 > ヘッドフォン、イヤフォン > イヤフォン > その他", "y_ct": "2084219572","sex": "0", "male": "", "female": ""},
        "ct32": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0","male": "", "female": ""},
        "ct513": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0","male": "", "female": ""},
        "ct926": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone X用", "y_ct": "2084315958","sex": "0", "male": "", "female": ""},
        "ct927": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone XS用","y_ct": "2084316070", "sex": "0", "male": "", "female": ""},
        "ct928": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone XS用","y_ct": "2084316070", "sex": "0", "male": "", "female": ""},
        "ct929": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone XS用","y_ct": "2084316070", "sex": "0", "male": "", "female": ""},
        "ct930": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール", "y_ct": "2084299106", "sex": "0","male": "", "female": ""},
        "ct1330": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0","male": "", "female": ""},
        "ct1331": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > ハードケース", "y_ct": "2084306949","sex": "0", "male": "", "female": ""},
        "ct1332": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他", "y_ct": "2084306951", "sex": "0","male": "", "female": ""},
        "ct1333": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他", "y_ct": "2084306951", "sex": "0","male": "", "female": ""},
        "ct1334": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0","male": "", "female": ""},
        "ct1335": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール", "y_ct": "2084299106","sex": "0", "male": "", "female": ""},
        "ct1336": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0","male": "", "female": ""},
        "ct1337": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > ハードケース", "y_ct": "2084306949","sex": "0", "male": "", "female": ""},
        "ct1338": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他", "y_ct": "2084306951", "sex": "0","male": "", "female": ""},
        "ct1339": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他", "y_ct": "2084306951", "sex": "0","male": "", "female": ""},
        "ct1340": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0","male": "", "female": ""},
        "ct1341": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール", "y_ct": "2084299106","sex": "0", "male": "", "female": ""},
        "ct1342": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0","male": "", "female": ""},
        "ct1343": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > ハードケース", "y_ct": "2084306949","sex": "0", "male": "", "female": ""},
        "ct1344": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他", "y_ct": "2084306951", "sex": "0","male": "", "female": ""},
        "ct1345": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他", "y_ct": "2084306951", "sex": "0","male": "", "female": ""},
        "ct1346": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0","male": "", "female": ""},
        "ct1347": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール", "y_ct": "2084299106","sex": "0", "male": "", "female": ""},
        "ct924": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0","male": "", "female": ""},
        "ct931": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone XR用","y_ct": "2084316072", "sex": "0", "male": "", "female": ""},
        "ct932": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone XR用","y_ct": "2084316072", "sex": "0", "male": "", "female": ""},
        "ct933": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone XR用","y_ct": "2084316072", "sex": "0", "male": "", "female": ""},
        "ct934": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0","male": "", "female": ""},
        "ct935": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール", "y_ct": "2084299106", "sex": "0","male": "", "female": ""},
        "ct925": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0","male": "", "female": ""},
        "ct936": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone XS Max用","y_ct": "2084316071", "sex": "0", "male": "", "female": ""},
        "ct937": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone XS Max用","y_ct": "2084316071", "sex": "0", "male": "", "female": ""},
        "ct938": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone XS Max用","y_ct": "2084316071", "sex": "0", "male": "", "female": ""},
        "ct939": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0","male": "", "female": ""},
        "ct940": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール", "y_ct": "2084299106", "sex": "0","male": "", "female": ""},
        "ct68": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0","male": "", "female": ""},
        "ct941": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 7 Plus/8 Plus用","y_ct": "2084315957", "sex": "0", "male": "", "female": ""},
        "ct942": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 7 Plus/8 Plus用","y_ct": "2084315957", "sex": "0", "male": "", "female": ""},
        "ct943": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 7 Plus/8 Plus用","y_ct": "2084315957", "sex": "0", "male": "", "female": ""},
        "ct944": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0","male": "", "female": ""},
        "ct945": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール", "y_ct": "2084299106", "sex": "0","male": "", "female": ""},
        "ct65": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0","male": "", "female": ""},
        "ct946": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 7/8用","y_ct": "2084315956", "sex": "0", "male": "", "female": ""},
        "ct947": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 7/8用","y_ct": "2084315956", "sex": "0", "male": "", "female": ""},
        "ct948": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 7/8用","y_ct": "2084315956", "sex": "0", "male": "", "female": ""},
        "ct949": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0","male": "", "female": ""},
        "ct950": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール", "y_ct": "2084299106", "sex": "0","male": "", "female": ""},
        "ct75": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0","male": "", "female": ""},
        "ct951": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 6 Plus/6s Plus用","y_ct": "2084314669", "sex": "0", "male": "", "female": ""},
        "ct952": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 6 Plus/6s Plus用","y_ct": "2084314669", "sex": "0", "male": "", "female": ""},
        "ct953": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 6 Plus/6s Plus用","y_ct": "2084314669", "sex": "0", "male": "", "female": ""},
        "ct954": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0","male": "", "female": ""},
        "ct955": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール", "y_ct": "2084299106", "sex": "0","male": "", "female": ""},
        "ct72": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0","male": "", "female": ""},
        "ct956": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 6 Plus/6s Plus用","y_ct": "2084314669", "sex": "0", "male": "", "female": ""},
        "ct957": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 6 Plus/6s Plus用","y_ct": "2084314669", "sex": "0", "male": "", "female": ""},
        "ct958": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 6 Plus/6s Plus用","y_ct": "2084314669", "sex": "0", "male": "", "female": ""},
        "ct959": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0","male": "", "female": ""},
        "ct960": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール", "y_ct": "2084299106", "sex": "0","male": "", "female": ""},
        "ct69": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0","male": "", "female": ""},
        "ct961": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 5用", "y_ct": "2084308386","sex": "0", "male": "", "female": ""},
        "ct962": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 5用", "y_ct": "2084308386","sex": "0", "male": "", "female": ""},
        "ct963": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > iPhone用ケース > iPhone 5用", "y_ct": "2084308386","sex": "0", "male": "", "female": ""},
        "ct964": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0","male": "", "female": ""},
        "ct965": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール", "y_ct": "2084299106", "sex": "0","male": "", "female": ""},
        "ct76": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0","male": "", "female": ""},
        "ct966": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > ハードケース", "y_ct": "2084306949","sex": "0", "male": "", "female": ""},
        "ct967": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他", "y_ct": "2084306951", "sex": "0","male": "", "female": ""},
        "ct968": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他", "y_ct": "2084306951", "sex": "0","male": "", "female": ""},
        "ct969": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0","male": "", "female": ""},
        "ct970": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール", "y_ct": "2084299106", "sex": "0","male": "", "female": ""},
        "ct516": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0","male": "", "female": ""},
        "ct971": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > ハードケース", "y_ct": "2084306949","sex": "0", "male": "", "female": ""},
        "ct972": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他", "y_ct": "2084306951", "sex": "0","male": "", "female": ""},
        "ct973": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他", "y_ct": "2084306951", "sex": "0","male": "", "female": ""},
        "ct974": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0","male": "", "female": ""},
        "ct975": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール", "y_ct": "2084299106", "sex": "0","male": "", "female": ""},
        "ct78": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー", "y_ct": "2084005062", "sex": "0", "male": "","female": ""},
        "ct976": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0","male": "", "female": ""},
        "ct977": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0","male": "", "female": ""},
        "ct978": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0","male": "", "female": ""},
        "ct979": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0","male": "", "female": ""},
        "ct980": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0","male": "", "female": ""},
        "ct10": {"ctname": "オークション > 事務、店舗用品 > 文房具 > その他", "y_ct": "2084042489", "sex": "0", "male": "", "female": ""},"ct57": {"ctname": "オークション > 事務、店舗用品 > 文房具 > その他", "y_ct": "2084042489", "sex": "0", "male": "", "female": ""},
        "ct17": {"ctname": "オークション > ビューティー、ヘルスケア > 健康用品、健康器具 > その他", "y_ct": "2084042545", "sex": "0", "male": "","female": ""},
        "ct982": {"ctname": "オークション > ビューティー、ヘルスケア > 健康用品、健康器具 > その他", "y_ct": "2084042545", "sex": "0", "male": "","female": ""},
        "ct95": {"ctname": "オークション > 食品、飲料 > ダイエット食品 > その他", "y_ct": "2084006890", "sex": "0", "male": "","female": ""},
        "ct1103": {"ctname": "オークション > 家電、AV、カメラ > 美容、健康 > 美容機器 > ネイルケア", "y_ct": "2084055371", "sex": "0", "male": "","female": ""},
        "ct13": {"ctname": "オークション > スポーツ、レジャー > キャンプ、アウトドア用品 > その他", "y_ct": "2084005102", "sex": "0", "male": "","female": ""},
        "ct1046": {"ctname": "オークション > スポーツ、レジャー > アウトドアウエア > 服飾小物 > その他", "y_ct": "2084057246", "sex": "0", "male": "","female": ""},
        "ct73": {"ctname": "医療・介護・医薬品＞介護・福祉＞その他生活グッズ＞サポーター", "y_ct": "2084063134","sex": "0", "male": "", "female": ""},
        "ct983": {"ctname": "オークション > スポーツ、レジャー > キャンプ、アウトドア用品 > 雨具、レインウエア > その他", "y_ct": "2084208701", "sex": "0","male": "", "female": ""},
        "ct984": {"ctname": "オークション > スポーツ、レジャー > スポーツ別 > 野球 > 防具 > マスク", "y_ct": "2084063121", "sex": "0", "male": "","female": ""},
        "ct987": {"ctname": "オークション > スポーツ、レジャー > キャンプ、アウトドア用品 > その他", "y_ct": "2084005102", "sex": "0", "male": "","female": ""},
        "ct999": {"ctname": "オークション > おもちゃ、ゲーム > 水遊び > ビーチボール", "y_ct": "2084042424", "sex": "0", "male": "","female": ""},
        "ct12": {"ctname": "オークション > 自動車、オートバイ > オートバイ > オートバイ関連グッズ > その他", "y_ct": "2084019984", "sex": "0","male": "", "female": ""},
        "ct64": {"ctname": "オークション > 自動車、オートバイ > アクセサリー > エンブレム > その他", "y_ct": "2084203148", "sex": "0", "male": "","female": ""},
        "ct66": {"ctname": "オークション > 自動車、オートバイ > カーナビ > 液晶保護フィルム、カバー > その他", "y_ct": "2084286642", "sex": "0","male": "", "female": ""},
        "ct991": {"ctname": "オークション > 自動車、オートバイ > オートバイ > オートバイ関連グッズ > その他", "y_ct": "2084019984", "sex": "0","male": "", "female": ""},
        "ct992": {"ctname": "オークション > 自動車、オートバイ > オートバイ > オートバイ関連グッズ > その他", "y_ct": "2084019984", "sex": "0","male": "", "female": ""},
        "ct67": {"ctname": "オークション > 自動車、オートバイ > オートバイ > オートバイ関連グッズ > その他", "y_ct": "2084019984", "sex": "0","male": "", "female": ""},
        "ct1116": {"ctname": "オークション > ファッション > レディースファッション > マタニティウエア", "y_ct": "2084006309", "sex": "0", "male": "","female": ""},
        "ct993": {"ctname": "オークション > おもちゃ、ゲーム > 手品、パーティグッズ > パーティグッズ > その他", "y_ct": "2084059858", "sex": "0","male": "", "female": ""},
        "ct995": {"ctname": "オークション > おもちゃ、ゲーム > こま > 一般", "y_ct": "2084041893", "sex": "0", "male": "", "female": ""},
        "ct83": {"ctname": "オークション > 住まい、インテリア > ペット用品 > 犬 > 服", "y_ct": "2084045164", "sex": "0", "male": "","female": ""},
        "ct988": {"ctname": "オークション > 住まい、インテリア > ペット用品 > 犬 > 服 > 中型犬用>その他", "y_ct": "2084062626", "sex": "0","male": "", "female": ""},
        "ct989": {"ctname": "オークション > 住まい、インテリア > ペット用品 > 犬 > 服 > 中型犬用>その他", "y_ct": "2084062626", "sex": "0","male": "", "female": ""},
        "ct87": {"ctname": "オークション > 住まい、インテリア > ペット用品 > 犬 > 手入れ用品", "y_ct": "2084008198", "sex": "0", "male": "","female": ""},
        "ct990": {"ctname": "オークション > 住まい、インテリア > ペット用品 > 犬 > その他", "y_ct": "2084008200", "sex": "0", "male": "","female": ""},
        "ct91": {"ctname": "オークション > 住まい、インテリア > ペット用品 > 犬 > その他", "y_ct": "2084008200", "sex": "0", "male": "","female": ""},
        "ct996": {"ctname": "オークション > おもちゃ、ゲーム > 知育玩具 > その他", "y_ct": "2084045581", "sex": "0", "male": "","female": ""},
        "ct994": {"ctname": "オークション > おもちゃ、ゲーム > 食玩、おまけ　> その他", "y_ct": "2084312319", "sex": "0", "male": "","female": ""},


        """


    # 大カテゴリ。仕方ない場合
    # バイヤーズカテゴリのシート、「リスト抽出用_2」のJ列を参照する
    _MY_CT_CODES_BIG = {
        "ct109": {"ctname": "オークション > ファッション > メンズファッション", "y_ct": "23176", "wowma_catid": "", "qoo_catid": ""},
        "ct119": {"ctname": "オークション > ファッション > レディースファッション", "y_ct": "23288", "wowma_catid": "", "qoo_catid": ""},
        "ct164": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス", "y_ct": "42184", "wowma_catid": "", "qoo_catid": ""},
        "ct161": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス", "y_ct": "42184", "wowma_catid": "", "qoo_catid": ""},
        "ct133": {"ctname": "オークション > ファッション > レディースファッション > スカート", "y_ct": "42183", "wowma_catid": "", "qoo_catid": ""},
        "ct169": {"ctname": "オークション > ファッション > レディースファッション＞その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
        "ct764": {"ctname": "オークション > ファッション > レディースファッション > その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
        "ct766": {"ctname": "オークション > ファッション > レディースファッション > その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
        "ct998": {"ctname": "オークション > ファッション > レディースファッション > その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
        "ct1039": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > その他", "y_ct": "2084005208", "wowma_catid": "", "qoo_catid": ""},
        "ct1042": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > その他", "y_ct": "2084005208", "wowma_catid": "", "qoo_catid": ""},
        "ct1040": {"ctname": "オークション > ファッション > レディースファッション > ジャケット、上着 > その他", "y_ct": "2084005208", "wowma_catid": "", "qoo_catid": ""},
        "ct1041": {"ctname": "オークション > ファッション > レディースファッション > スカート", "y_ct": "42183", "wowma_catid": "", "qoo_catid": ""},
        "ct825": {"ctname": "オークション > ファッション > ファッション小物 > その他", "y_ct": "44164", "wowma_catid": "", "qoo_catid": ""},
        "ct857": {"ctname": "オークション > スポーツ、レジャー > スポーツ別 > その他", "y_ct": "25462", "wowma_catid": "", "qoo_catid": ""},
        "ct802": {"ctname": "オークション > アクセサリー、時計 > ブランド腕時計", "y_ct": "23260", "wowma_catid": "", "qoo_catid": ""},
        "ct1100": {"ctname": "オークション > ファッション > ファッション小物 > その他", "y_ct": "44164", "wowma_catid": "", "qoo_catid": ""},
        "ct813": {"ctname": "オークション > ファッション > ファッション小物 > その他", "y_ct": "44164", "wowma_catid": "", "qoo_catid": ""},
        "ct818": {"ctname": "オークション > ファッション > ファッション小物 > その他", "y_ct": "44164", "wowma_catid": "", "qoo_catid": ""},
        "ct60": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > その他", "y_ct": "42172", "wowma_catid": "", "qoo_catid": ""},
        "ct1099": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > その他", "y_ct": "24462", "wowma_catid": "", "qoo_catid": ""},
        "ct62": {"ctname": "オークション > 住まい、インテリア > キッチン、食器", "y_ct": "42168", "wowma_catid": "", "qoo_catid": ""},
        "ct921": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > その他", "y_ct": "24462", "wowma_catid": "", "qoo_catid": ""},
        "ct9": {"ctname": "オークション > 家電、AV、カメラ", "y_ct": "23632", "wowma_catid": "", "qoo_catid": ""},
        "ct55": {"ctname": "オークション > 家電、AV、カメラ > オーディオ機器 > その他", "y_ct": "23828", "wowma_catid": "", "qoo_catid": ""},
        "ct58": {"ctname": "オークション > 事務、店舗用品 > オフィス用品一般", "y_ct": "42176", "wowma_catid": "", "qoo_catid": ""},
        "ct59": {"ctname": "オークション > 事務、店舗用品 > その他", "y_ct": "22996", "wowma_catid": "", "qoo_catid": ""},
        "ct98": {"ctname": "オークション > ビューティー、ヘルスケア > コスメ、スキンケア > その他", "y_ct": "44379", "wowma_catid": "", "qoo_catid": ""},
        "ct101": {"ctname": "オークション > ビューティー、ヘルスケア > コスメ、スキンケア > その他", "y_ct": "44379", "wowma_catid": "", "qoo_catid": ""},
        "ct71": {"ctname": "オークション > スポーツ、レジャー > 自転車、サイクリング > アクセサリー > その他", "y_ct": "26242", "wowma_catid": "", "qoo_catid": ""},
        "ct74": {"ctname": "オークション > スポーツ、レジャー > 自転車、サイクリング > アクセサリー > その他", "y_ct": "26242", "wowma_catid": "", "qoo_catid": ""},
        "ct1114": {"ctname": "オークション > ベビー用品", "y_ct": "24202", "wowma_catid": "", "qoo_catid": ""},
        "ct1115": {"ctname": "オークション > ベビー用品＞ベビー服、マタニティウエア", "y_ct": "24210", "wowma_catid": "", "qoo_catid": ""},
        "ct83": {"ctname": "オークション > ファッション > レディースファッション > その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
        "ct996": {"ctname": "オークション > コンピュータ > ソフトウエア > パッケージ版 > Windows > 教育、教養 > その他", "y_ct": "23580", "wowma_catid": "", "qoo_catid": ""},
        "ct172": {"ctname": "オークション > おもちゃ、ゲーム > パズル > その他", "y_ct": "27711", "wowma_catid": "", "qoo_catid": ""},
        "ct15": {"ctname": "オークション > 住まい、インテリア > ペット用品", "y_ct": "24534", "wowma_catid": "", "qoo_catid": ""},
        "ct170": {"ctname": "オークション > おもちゃ、ゲーム", "y_ct": "25464", "wowma_catid": "", "qoo_catid": ""},
        "ct171": {"ctname": "オークション > おもちゃ、ゲーム　＞　その他", "y_ct": "26082", "wowma_catid": "", "qoo_catid": ""},
        "ct18": {"ctname": "オークション > 自動車、オートバイ > 工具", "y_ct": "24650", "wowma_catid": "", "qoo_catid": ""},
        "ct19": {"ctname": "オークション > ファッション > レディースファッション > その他", "y_ct": "23316", "wowma_catid": "", "qoo_catid": ""},
    }

    # 500円均一など。そのままでは割当られない場合
    _MY_CT_CODES_OTHER = {
        "ct439": {"ctname": "(NG) 3000円未満", "y_ct": "_NG_2500円未満", "wowma_catid": "_NG_2500円未満", "qoo_catid": "_NG_2500円未満"},
        "ct438": {"ctname": "(NG) 2500円未満", "y_ct": "_NG_2500円未満", "wowma_catid": "_NG_2500円未満", "qoo_catid": "_NG_2500円未満"},
        "ct437": {"ctname": "(NG) 2000円未満", "y_ct": "_NG_2000円未満", "wowma_catid": "_NG_2000円未満", "qoo_catid": "_NG_2000円未満"},
        "ct436": {"ctname": "(NG) 1500円未満", "y_ct": "_NG_1500円未満", "wowma_catid": "_NG_1500円未満", "qoo_catid": "_NG_1500円未満"},
        "ct435": {"ctname": "(NG) 1000円未満", "y_ct": "_NG_1000円未満", "wowma_catid": "_NG_1000円未満", "qoo_catid": "_NG_1000円未満"},
        "ct434": {"ctname": "(NG) 500円未満", "y_ct": "_NG_500円未満", "wowma_catid": "_NG_500円未満", "qoo_catid": "_NG_500円未満"},
        "ct426": {"ctname": "(NG) 20個以上在庫", "y_ct": "_NG_20個以上在庫", "wowma_catid": "_NG_20個以上在庫", "qoo_catid": "_NG_20個以上在庫"},
        "ct338": {"ctname": "(NG) 50個以上在庫", "y_ct": "_NG_50個以上在庫", "wowma_catid": "_NG_50個以上在庫", "qoo_catid": "_NG_50個以上在庫"},
        "ct634": {"ctname": "(NG) バイヤーズボックス", "y_ct": "_NG_バイヤーズボックス", "wowma_catid": "_NG_バイヤーズボックス", "qoo_catid": "_NG_バイヤーズボックス"},
    }

    # バイヤーズカテゴリのシート、　https://docs.google.com/spreadsheets/d/1XLHXkiE-_p11nYUFy2TFOsQonWJb7OR7jF4wk0JQRsY/edit#gid=492800307
    # 「cat_wowma_edit」シート　J列　を参考に
    _MY_CT_CODES_KEYWORD = {
        "プリンセスドレス": {"ctname": "オークション > ファッション > レディースファッション > フォーマル > ウエディングドレス > プリンセスタイプ", "y_ct": "2084064269",
                     "sex": "0", "male": "", "female": "", "wowma_catid": "510911",
                     "wowma_catname": "レディースファッション>ドレス>パーティドレス", "qoo_catid": "300002195",
                     "qoo_catname": "レディースファッション_ワンピース・ドレス_その他",
                     "s_keyword": "子供 大人 100 110 120 90 130 150 ベル 子供と靴 黄色 アリエル アナ インナー エルサ オーロラ姫 型紙 キッズ プリンセス ドレス 靴 コスプレ 子ども シューズ シンデレラ 白 セット ソーイング  メルちゃん  長袖 女の子 ピアノ発表会 フォーマル 子供服 ノースリーブ ベビードレス 子供の 普段着 マーメイド 5点セット 水色 紫 メモ 安い ユニコーン 幼児 眠れる森の美女の で彩るパウダールーム"},
        "便利手帳": {"ctname": "オークション > 本、雑誌 > 住まい、暮らし、育児 > インテリア、家づくり", "y_ct": "2084008946", "sex": "0", "male": "",
                 "female": "", "wowma_catid": "550505", "wowma_catname": "本・コミック・雑誌>ガーデニング>庭園・庭づくり",
                 "qoo_catid": "300000532", "qoo_catname": "文具_文房具_その他",
                 "s_keyword": "手帳 グッズ 便利 便利アイテム お薬手帳 マナーの全てが分かる 便利な手帳 ワインの システム手帳 a5 iphone13 pro ケース 手帳型 軽量 新oct octa カード収納 6穴手帳便利グッズ"},
        "リップブラシ": {"ctname": "オークション > ビューティー、ヘルスケア > コスメ、スキンケア > メイク道具、化粧小物 > ブラシ、チップ、コーム > その他", "y_ct": "2084228684",
                   "sex": "0", "male": "", "female": "", "wowma_catid": "471212",
                   "wowma_catname": "ビューティ・コスメ>メイク道具・ケアグッズ>ブラシ・チップ", "qoo_catid": "320001711",
                   "qoo_catname": "ポイントメイク_リップメイク_リップパレット",
                   "s_keyword": "使い捨て   rmk 携帯用 シリコン 熊野筆 スライド式 日本製 平筆 個包装 筆 キャップ付き 使い捨て先 ミニ ロージー 熊野     押し出し  可愛い 黒 携帯   メイク人気ブラシ 任意化粧品に適用され ブラック 化粧道具 多機能  小 スライド スタンプ スポンジ チップ ちふれ 業務用 蓋なし 人気 熊の筆 幅広 ひ 太め   丸"},
        "鍋敷き": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > 収納、キッチン雑貨 > その他", "y_ct": "2084018482", "sex": "0",
                "male": "", "female": "", "wowma_catid": "350627", "wowma_catname": "キッチン・食器・調理>キッチン用品・キッチン雑貨>鍋敷き",
                "qoo_catid": "320000800", "qoo_catname": "キッチン用品_キッチン雑貨_鍋敷き",
                "s_keyword": "おしゃれ 木製 シリコン 耐熱 コルク マグネット キャンプ 藁 北欧 オシャレ 木 タイル 陶器 布 スキレット 丸 折り畳み 日本製 四角 白 グレー 折りたたみ 便利 洗える 黒 大判 大きい 金属 厚い ストウブ 20cm コルクボード 20 マグネット付 円 岩手 アウトドア アイアン 麻 アルミ 編み込み 赤 編み アンティーク 大きめ い草 いぐさ 石 井草 いちご"},
        "VGAケーブル": {"ctname": "オークション > コンピュータ > 周辺機器 > その他", "y_ct": "2084048551", "sex": "0", "male": "",
                    "female": "", "wowma_catid": "46080402", "wowma_catname": "パソコン・PC周辺機器>パソコン本体>デスクトップパソコン>ディスプレイセット",
                    "qoo_catid": "320002326", "qoo_catname": "パソコン_PCケーブル_RGB・VGAケーブル",
                    "s_keyword": "vgaケーブル 30m 10m 20m オスメス 7m 長い メス 分岐 白 vga ケーブル メスメス 1.5ｍ 細い 短い 柔らかい 薄型 延長 オスオス 拡張 切り替え キーボード 黒 コンパクト 小型コネクタ 小型 高画質 コネクタ  スリム タイプc ネジ無し hdmi vgaの変換ケーブル フラット 二股 変換 usb 細 ホワイト ミニ vgaからhdmi 変換ケーブル 双方向 ケーブルへんかん ゲーム 極細 ディスプレイポート バッファロー 分配器"},
        "ブリーフ": {"ctname": "オークション > ファッション > メンズファッション > インナーウエア > ビキニ、ブリーフ > Mサイズ", "y_ct": "2084053066", "sex": "0",
                 "male": "", "female": "", "wowma_catid": "320408", "wowma_catname": "インナー・ルームウェア>メンズインナー>ブリーフ",
                 "qoo_catid": "320001570", "qoo_catname": "メンズファッション_インナー・靴下_ブリーフ",
                 "s_keyword": "ィング briefing ゴルフ リュック ビジネスバッグ キャディバッグ 財布 トートバッグ ポーチ ケース メンズ a4 本革 レディース ビジネス プラスチック バッグ レザー キャップ ゴルフバッグ ショルダーバッグ neo b4 liner パスケース 下着 ビキニ  bvd 前開き 黒 4l 3l 大きいサイズ ゴルフウェア 帽子 ヘッドカバー カートバッグ  セミビキニ スタンダード 日本製 白 sサイズ アニマル 3way 薄型 グレー 30l 小さめ 軽量"},
        "シャープペンシル": {"ctname": "オークション > 事務、店舗用品 > 文房具 > 筆記用具 > シャープペンシル", "y_ct": "2084040729", "sex": "0", "male": "",
                     "female": "", "wowma_catid": "54090201", "wowma_catname": "日用品・文房具・手芸用品>手芸・クラフト・生地>その他手芸用品>その他",
                     "qoo_catid": "320001574", "qoo_catname": "おもちゃ・知育_子供用文房具_ペン",
                     "s_keyword": "0.5 書きやすい 芯 中学生 高級 0.3 0.7mm 0.9 ドクターぐりっぷ b 2b クルトガ hb ドクターグリップ かわいい 0.7 おしゃれ 書きやすい0.9 可愛い uni 4b 青 赤 h 三菱 高級中学生お祝い 木製 名入れ 高校生 ギフト 白 女性 0.3mm 折れない 替芯 オレンズ カラー  0.9mm 0.9ミリ 0.5新作 ホワイト 復刻 0.5白 黒 30周年 消しゴム アニメ 赤芯 アルファゲル"},
        "VGA延長アダプタ": {"ctname": "オークション > 家電、AV、カメラ > その他", "y_ct": "23972", "sex": "0", "male": "", "female": "",
                      "wowma_catid": "46080402", "wowma_catname": "パソコン・PC周辺機器>パソコン本体>デスクトップパソコン>ディスプレイセット",
                      "qoo_catid": "320002460", "qoo_catname": "テレビ・オーディオ_その他AV機器_その他AV機器用アクセサリー",
                      "s_keyword": "vga延長アダプタ  アナログ rgb 中継コネクタ d-sub15ピン メス/メス メス/オス 1個 vce vgaメス to メス 中継アダプタ vgaケーブル連結 vga延長コネクタ d-sub 15ピン ミニ 3個セット"},
        "HDMI変換アダプター": {"ctname": "オークション > 家電、AV、カメラ > 映像機器 > 映像用ケーブル > HDMIケーブル", "y_ct": "2084239134", "sex": "0",
                        "male": "", "female": "", "wowma_catid": "44020401",
                        "wowma_catname": "テレビ・オーディオ・カメラ>カメラ>カメラ用周辺機器・アクセサリー>ACアダプター", "qoo_catid": "320002324",
                        "qoo_catname": "パソコン_PCケーブル_HDMIケーブル",
                        "s_keyword": "wii mayflash 国産 mg2000 純正 1.5 usb 4k mac os対応 テレビ type-c windows11 2口 充電 win11対応 iphone アンドロイド vga ミニ 車 apple type-cメス galaxy tv ipad android lightning アナログ アップル hdmi 変換アダプタ エクスペリア オス カーナビ 変換アダプター ablewe 1080p 60hz /20cm/保証付き rankie 4k高解像度対応 オーディオ付き ブラック ケーブル サンワ スターテック スマホ セット タイプc l phone hdmi変換ケーブル i-pad アダプター テレビに映す"},
        "ハロウィン コスプレ 男性": {"ctname": "オークション > コミック、アニメグッズ > コスプレ衣装 > 男性用", "y_ct": "2084241340", "sex": "0", "male": "",
                          "female": "", "wowma_catid": "5004", "wowma_catname": "メンズファッション>コスチューム",
                          "qoo_catid": "300000789", "qoo_catname": "ホビー・コスプレ_パーティー・イベント用品_ハロウィン",
                          "s_keyword": "メンズ かっこいい ドラキュラ ジャケット コート 王子様 ハロウィン コスプレ 仮装 ステージ衣装 男性用ジャケット 舞台衣装 中世 貴族服装 クリスマス 新年 コスチューム"},
        "メモリカードホルダー": {"ctname": "オークション > コンピュータ > 周辺機器 > その他", "y_ct": "2084048551", "sex": "0", "male": "",
                       "female": "", "wowma_catid": "461407", "wowma_catname": "パソコン・PC周辺機器>記録メディア>SDカード",
                       "qoo_catid": "320002201", "qoo_catname": "カメラ・光学機器用_メモリーカード_メモリーカードケース",
                       "s_keyword": "薄型 メモリーカードケース TF MicroSD Micro SD MSD カード 10枚 収納可能 TFカードケース MicroSDカードケース MSDカードケース 携帯便利 メモリーカードホルダー 花柄"},
        "枕カバー": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > 寝具 > シーツ、カバー > 枕カバー", "y_ct": "2084245297", "sex": "0",
                 "male": "", "female": "", "wowma_catid": "311617", "wowma_catname": "インテリア・寝具>寝具>枕カバー",
                 "qoo_catid": "300002917", "qoo_catname": "寝具・ベッド・マットレス_枕_枕",
                 "s_keyword": "シルク 50x70 35x50 40 60 タオル地 のびのび 洗える インサートエアピロー 43x63cm 片面 50 70 43 63 2枚セット 35 日本製 封筒 ロング 2枚組 綿 かわいい ファスナー式 今治 フリル キャラクター ファスナー 綿100 西川 タオル 伸びる セット のびのび大きめ 50cm 70cm  猫 2枚 大きい dx 二股 160 人気 43x63cm柄 90 cb  両面 アニメ"},
        "ガーランド": {"ctname": "オークション > 住まい、インテリア > 季節、年中行事 > > > 飾り、オーナメント", "y_ct": "2084283929", "sex": "0",
                  "male": "", "female": "", "wowma_catid": "311908", "wowma_catname": "インテリア・寝具>壁紙・装飾フィルム>その他壁紙・装飾フィルム",
                  "qoo_catid": "320000881", "qoo_catname": "ガーデニング・DIY・工具_住宅設備・ライト_ガーデンオーナメント・置物",
                  "s_keyword": "誕生日 バースデー 結婚式 ハッピーバースデー おしゃれ happy birthday キャンプ フラッグ インテリア 男の子 女の子 シルバー シンプル マリオ 男 ピンク マイクラ ナチュラル 1歳 ペーパーファン 写真 風船 和装 ウェルカム 木製 セット ゴールド 恐竜 花 布 オシャレ タッセル ブルー シック 麻 黒 ライト led トリコロール テント アンティーク 屋外 １０ｍ フィギュア 青 アルファベット 赤ちゃん アウトドア 赤"},
        "ラグマット": {"ctname": "オークション > 住まい、インテリア > 家具、インテリア > カーペット、ラグ、マット > ラグ > ラグ一般", "y_ct": "2084304266",
                  "sex": "0", "male": "", "female": "", "wowma_catid": "310710",
                  "wowma_catname": "インテリア・寝具>カーペット・ラグ>ジョイントマット", "qoo_catid": "300003262",
                  "qoo_catname": "家具・インテリア_カーペット・マット_ラグマット",
                  "s_keyword": "円形 おしゃれ 3畳 2畳 200x300 低反発 北欧 200x250 1.5畳 180 140 200cm 160 120 100 150 90cm グリーン 韓国 洗える オシャレ 柄 小さめ 夏 夏用 厚手 オールシーズン 綿 インド綿 通年 防音 アイボリー グレー ブラック シャギー 極厚 1畳 小さい ピンク 北欧デザイン 白 ビニール ベージュ キルト ふわふわ ホットカーペット ブルー アウトドア 厚め アメリカン"},
        "シリコンふた": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > 収納、キッチン雑貨 > その他", "y_ct": "2084018482", "sex": "0",
                   "male": "", "female": "", "wowma_catid": "350629",
                   "wowma_catname": "キッチン・食器・調理>キッチン用品・キッチン雑貨>シリコンラップ", "qoo_catid": "300000505",
                   "qoo_catname": "キッチン用品_キッチン消耗品_保存容器",
                   "s_keyword": "カバー 耐熱 ぶた マグカップ カバー風呂 鍋 レンジ 日本製 お風呂 シンク シリコン ふた かわいい カップ たいふc 保護シリコン 蓋 フタ カインズ 缶 紙コップ キャラ リッド 選べる5色 タンブラー ほこりよけ 保温 カフェ 可 ラッピング不可 ホワイト 瓶 ふた開け オープナー びんふた開け コップ こぼれない 皿 小 食洗機 収納 ストロー セット 製氷皿 小さい 長方形 ふたつき ねこ カップのふた コップのふた マグカップのふた"},
        "まつげブラシ": {"ctname": "オークション > ビューティー、ヘルスケア > コスメ、スキンケア > メイク道具、化粧小物 > ブラシ、チップ、コーム > メイクブラシセット",
                   "y_ct": "2084228681", "sex": "0", "male": "", "female": "", "wowma_catid": "471212",
                   "wowma_catname": "ビューティ・コスメ>メイク道具・ケアグッズ>ブラシ・チップ", "qoo_catid": "320001725",
                   "qoo_catname": "メイク小物_メイク道具_メイクブラシ",
                   "s_keyword": "コーム 使い捨て シリコン kittro 100本 眉ブラシ スクリューブラシ アイメイク 化粧用品 ブラック さつまつげ ブラシ まつげパーマ y字ブラシ"},
        "テーブルクロス": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > テーブルリネン > テーブルクロス", "y_ct": "2084046784", "sex": "0",
                    "male": "", "female": "", "wowma_catid": "310809", "wowma_catname": "インテリア・寝具>クッション・ファブリック>テーブルクロス",
                    "qoo_catid": "320001076", "qoo_catname": "家具・インテリア_インテリア・装飾_テーブルクロス",
                    "s_keyword": "ビニール 透明 おしゃれ 防水 撥水 白 長方形 正方形 円形 90 180 切り売り 北欧 厚手 ビニールレース テーブル 丸型 150 80 120 75 140 薄い 耐熱 小さい 小さめ オシャレ かわいい 撥水加工 ピンク 240 グリーン 無地 リネン 布 大きめ 大きい 90cm 100x100 110x110 100 120cm 60cm 110 赤 アウトドア 青 麻 アンティーク アイボリー"},
        "アルミバンパー": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0",
                    "male": "", "female": "", "wowma_catid": "410509",
                    "wowma_catname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>スマホケース", "qoo_catid": "320002283",
                    "qoo_catname": "スマートフォン・タブレットPC_スマートフォン用アクセサリー_その他スマートフォン用アクセサリー",
                    "s_keyword": "iphone13 ケース  ガラスケース 背面 グリーン ネジ ケース両面 レッド 赤 iphone12 背面パネル付き 薄 木 iphone se 第３ pga 第2世代 両面ガラス pro xperia max iphone8 13mini 13promax 13 mini 12mini 5 iii 1 ii xperia5ii アルミ 強化ガラス ガラスフィルム 両面磁石 360 全面保護 擦り傷防止 いphone11 あいふぉん13ケース あいふぉん13 えくすぺりあ1iii ケース極薄 背面付き カメラまで保護 覗き見防止 ロック付き 背面保護"},
        "ドアストッパー": {"ctname": "オークション > 住まい、インテリア > 工具、DIY用品 > 建築材料、住宅設備 > 内装 > 建具 > ドア、扉 > その他", "y_ct": "2084304484",
                    "sex": "0", "male": "", "female": "", "wowma_catid": "29061102",
                    "wowma_catname": "おもちゃ・趣味>アート・美術品・骨董品>骨董品・アンティーク>インテリア雑貨", "qoo_catid": "320000891",
                    "qoo_catname": "ガーデニング・DIY・工具_住宅設備・ライト_その他",
                    "s_keyword": "マグネット 玄関 室内 強力 ゴム 猫 引き戸 マグネット式 足 かわいい ロング マグネット付き ブラウン おしゃれ 高さ 段差 防犯 置物 上部 白 可愛い シリコン 替え ゴムキャップ 小さい 大 大きい 13mm ゴムクッション 磁石 強力マグネット ノブロック 猫用 引き戸用 ペット ポルテ 赤ちゃん あかちゃん 足で操作 アイスクリーム 足長 アンティーク アラーム 足踏み 犬 インコ 石 いたずら 上枠 薄型"},
        "ケースオープナー": {"ctname": "オークション > アクセサリー、時計 > 時計用工具 > セット", "y_ct": "2084062479", "sex": "0", "male": "",
                     "female": "", "wowma_catid": "5827", "wowma_catname": "腕時計>腕時計メンテナンス", "qoo_catid": "300002361",
                     "qoo_catname": "腕時計・アクセサリー_腕時計用品_ケア・修理用品",
                     "s_keyword": "パソコン ヘラ 時計 ノートパソコン セット 5個セット pc スマホ 分解 ツール たくさん使える"},
        "サポーター": {"ctname": "オークション > ビューティー、ヘルスケア > 健康用品、健康器具 > サポーター > その他", "y_ct": "2084216486", "sex": "0",
                  "male": "", "female": "", "wowma_catid": "40480802",
                  "wowma_catname": "スポーツ・アウトドア>格闘技>プロテクター>アンクルサポーター", "qoo_catid": "320001138",
                  "qoo_catname": "バッグ・雑貨_小物_リストバンド",
                  "s_keyword": "手首  腱鞘炎 固定 女性 筋トレ 女性用 医療用  薄手 ひざ 膝 スポーツ 用 大きいサイズ 高齢者 変形性膝関節症 バレーボール ランニング 肘 テニス肘  野球 ゴルフ 子供用 バレー レディース ジュニア ふくらはぎ 肉離れ 着圧 就寝用 ランニング用 手首用 足首 腰 腕 テニス 親指 肌色 手根管症候群 捻挫 足首用 腰痛 男性用 protaid 背中 腕用 タトゥー 黒 ふくらはぎ用"},
        "Pro用ケース": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0",
                    "male": "", "female": "", "wowma_catid": "410509",
                    "wowma_catname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>スマホケース", "qoo_catid": "320002207",
                    "qoo_catname": "スマホケース・保護フィルム_iPhoneケース_iPhone 12 Pro Max",
                    "s_keyword": "iphone12 pro用 ケース 手帳型 ケースあーと かわいい pro max用 可愛い ドラえもん おしゃれ ケースおしゃれ 手帳型おしゃれ リング付き iphone 12 max 用  first classケース airpods くすみブルー class pro専用 ケースぶらっく 肩掛け owc mercury 5.25インチ 光学ドライブ用 外付けケース 肩掛け名前 かっこいい プーさん クレヨンしんちゃん キャ ipad リングつき 12/12 simplism ケースとの相性抜群 ゴリラガラス 画面保護強化ガラス 高透明  ケース第三世代に適用 キーチェーン付き 透明 tpuカバー ワイヤ"},
        "カーラー": {"ctname": "オークション > ビューティー、ヘルスケア > コスメ、スキンケア > メイク道具、化粧小物 > ビューラー", "y_ct": "2084007463", "sex": "0",
                 "male": "", "female": "", "wowma_catid": "471208", "wowma_catname": "ビューティ・コスメ>メイク道具・ケアグッズ>ビューラー・カーラー",
                 "qoo_catid": "320001727", "qoo_catname": "メイク小物_メイク道具_ビューラー・カーラー",
                 "s_keyword": "前髪 太め 韓国 40 特大 前髪クリップ 熱 前髪用 アルミ 38 50mm 60 寝ながら 長め クリップ アイロン アイロンコンパクト 32 26 アイロンサロニア コードレス ミニ 3 巻き髪 ロング スポンジ 日本製 マペペ  38ミリ オリーブヤング 50 50ミリ クリップ付き クリップのみ アイプチ 一重 ひとえ 替え 替えゴム 細め まつ毛 アルミ付き アイラッシュ アイ 泡ローラー アイロン太め いちご 一個 いろいろ ウェーブ"},
        "アイプチ": {"ctname": "オークション > ビューティー、ヘルスケア > コスメ、スキンケア > メイク道具、化粧小物 > ビューラー", "y_ct": "2084007463", "sex": "0",
                 "male": "", "female": "", "wowma_catid": "471202",
                 "wowma_catname": "ビューティ・コスメ>メイク道具・ケアグッズ>その他メイク道具・ケアグッズ", "qoo_catid": "320001726",
                 "qoo_catname": "メイク小物_メイク道具_二重まぶたグッズ",
                 "s_keyword": "ビューラー 夜用 マスカラ メンズ テープ 皮膜式 のり アストレアヴィルゴ おりしき 替えゴム ひとえ 奥二重用 一重 ゴム 単 奥2重用 夜用くせ付き 人気 夜用癖付き 湘南 プラムブラウン プラム 木苺ブラウン マスカラリムーバー リムーバー 1重 一重用 プライムブラウン 癖付け ナイト 両面 メッシュ 夜 100均 片面 透明 日本製 奥二重 奥2重 ハード 強力 ノリ のりメンズ かぶれない コージー 安い 折式 オリシキ 奥ぶたえ用カーラー カーラー"},
        "バランスボール": {"ctname": "オークション > スポーツ、レジャー > スポーツ別 > ヨガ、ピラティス > ヨガボール", "y_ct": "2084286287", "sex": "0",
                    "male": "", "female": "", "wowma_catid": "403806",
                    "wowma_catname": "スポーツ・アウトドア>ヨガ・ピラティス>ヨガマット・ヨガラグ", "qoo_catid": "320000279",
                    "qoo_catname": "スポーツ_フィットネス・ヨガ_その他",
                    "s_keyword": "椅子 65cm 55cm 75cm チェア 45cm カバー 空気入れ こども用 椅子代わり 椅子用 椅子の上 椅子型 背もたれ 45 リング付き カバー付き 日本製 アンチバースト 固定リング reebok  白 ホワイト リング 黒 オレンジ ゴールド 500kg 黄色 75 65  キャスター gaiam 子供 チェアー 大人 ベージュ 55 電動 空気入れ付き アタッチメント ノズル 針 東急スポーツ 空気入れつき すみっこ 体幹 人気"},
        "歯ブラシ": {"ctname": "オークション > ビューティー、ヘルスケア > オーラルケア > 歯ブラシ > 一般", "y_ct": "2084063362", "sex": "0", "male": "",
                 "female": "", "wowma_catid": "34051915", "wowma_catname": "キッズベビー・マタニティ>ベビー>衛生・ヘルスケア>乳児用歯ブラシ",
                 "qoo_catid": "300000506", "qoo_catname": "日用品雑貨_デンタルケア_歯ブラシ",
                 "s_keyword": "ホルダー こども ケース 立て やわらかめ セット 子供 犬 システマ 浮かせる マグネット 吸盤 除菌 tower 壁掛け 珪藻土 マーナ ステンレス 2歳 3歳 ciメディカル タフト まとめ買い 6歳 1歳 小学生 ケース付き コップ付き 携帯用 携帯 コップ 子ども かわいい おしゃれ 一人用 可愛い 柔らかめ コンパクト 極細 歯科医院専用 超コンパクト シュミテクト 大人 男の子 幼稚園 キャップ 超小型犬 小型犬 360 指サック"},
        "靴紐": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > 靴用品 > その他", "y_ct": "2084238538", "sex": "0", "male": "",
               "female": "", "wowma_catid": "542003", "wowma_catname": "日用品・文房具・手芸用品>シューズ関連小物>靴紐",
               "qoo_catid": "300002328", "qoo_catname": "シューズ_シューズアクセサリー_その他",
               "s_keyword": "結ばない ゴム 革靴 白 黒 スニーカー 赤 ピンク 子供 金具 シリコン 子供用 ベージュ ハイカット 革靴用 黄色 茶色 75cm 平紐 85cm 60cm 65cm ブラウン 120cm 白黒 110cm 140 丸型 100cm 丸 130cm 140cm 黒白 ビジネス 80cm スニーカー用 90cm おしゃれ グレー 150 赤黒 ブーツ 160 赤白 120 ピンクベージュ グラデーション ピンクラメ ピンクゴールド ピンク紫"},
        "シューレース": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > 靴用品 > その他", "y_ct": "2084238538", "sex": "0", "male": "",
                   "female": "", "wowma_catid": "542003", "wowma_catname": "日用品・文房具・手芸用品>シューズ関連小物>靴紐",
                   "qoo_catid": "300002328", "qoo_catname": "シューズ_シューズアクセサリー_その他",
                   "s_keyword": "nodc 140 120 丸紐 ゴム ストッパー アンカー 160 ヴィンテージ オーバル グリーン ワイド セイル 楕円 kenji 140cm 平紐 コットン 生成り ベージュ 120cm ブーツ ブルー 黒 グレー ピンク 白 9mm 110 ゴム紐 キッズ 丸 革靴 90 幅 ジョーダン コードストッパー 2穴 ジョーダン5 スニーカー ビジネス オレンジ 160cm 160オーバル ワックス ナイキ黒120cm 赤 アクセサリー 青 アグレット"},
        "ドリンクホルダー": {"ctname": "オークション > 自動車、オートバイ > アクセサリー > 車内収納、ホルダー > コンソールボックス", "y_ct": "2084213751", "sex": "0",
                     "male": "", "female": "", "wowma_catid": "33641401",
                     "wowma_catname": "カー用品・バイク用品>カー用品>トラック用品>内装用品", "qoo_catid": "320000304",
                     "qoo_catname": "カー用品_カー用品_アクセサリー",
                     "s_keyword": "車 ベビーカー デスク 自転車 ハイエース バイク スマホ ヤリスクロス 2個置き 保冷 保温 エアコン エアコン吹き出し口 後部座席 ドア掛け 紙パック 丸型エアコン アップリカ 2個 コンビ 携帯ホルダー 折畳み サイベックス ミッキー 深い クランプ 白 大きめ ペットボトル 倒れ防止 デスク用 ヘッドホン 折り畳み ハンドル アルミ 自転車用 カーボン オレンジ 緑 コーヒー  jb64 jb23 星光産業 背もたれ アピオ ja11 増設トレイ タニグチ フロント"},
        "保護ケース": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0",
                  "male": "", "female": "", "wowma_catid": "410509",
                  "wowma_catname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>スマホケース", "qoo_catid": "320002283",
                  "qoo_catname": "スマートフォン・タブレットPC_スマートフォン用アクセサリー_その他スマートフォン用アクセサリー",
                  "s_keyword": "surfacego3  アップルウォッチ ipad ポーチ パソコン 小物 スマホ 30cm 40mm 41mm 38mm 付きバンド 44mm 45mm 42mm クリア レディース キャラクター 有機el かわいい バッグセット どうぶつ マリオ あつ森 第9世代 第7世代 10.2 キーボード 頑丈 9.7 第8世代 磁気吸着 マグネット sog01 geanee adp-503g fate a4 いphone11 全面 max カメラ保護 あいふぉん13ケース スイッチゆうきel あっぷるうぉっち 保護フィルム えあーぽっず ケース 全面保護 大型"},
        "D端子ケーブル": {"ctname": "オークション > 家電、AV、カメラ > 映像機器 > 映像用ケーブル > D端子ケーブル", "y_ct": "2084239135", "sex": "0",
                    "male": "", "female": "", "wowma_catid": "440902",
                    "wowma_catname": "テレビ・オーディオ・カメラ>映像プレイヤー・レコーダー>DVD・Blu-rayレコーダー", "qoo_catid": "320002460",
                    "qoo_catname": "テレビ・オーディオ_その他AV機器_その他AV機器用アクセサリー",
                    "s_keyword": "d端子ケーブル ps2 hdmi 変換 5m wii コンポジット psp ゲームキューブ d端子から 変換ケーブル yf2-０３ スーパーファミコン d端子avケーブル wii専用 ps3/ps2 ps3/ps2用 コロンバスサークル cc-p3dc-bk type-c ケーブル d端子 ps3 type d usb vga d端子a/vケーブル xbox 用 メス接続 コンポーネント オス接続 0.3m 1m 1.8m プレイステーション2 プレステ3 2m 3m"},
        "ペンケース": {"ctname": "オークション > 事務、店舗用品 > 文房具 > ペンケース", "y_ct": "2084048848", "sex": "0", "male": "",
                  "female": "", "wowma_catid": "29061115", "wowma_catname": "おもちゃ・趣味>アート・美術品・骨董品>骨董品・アンティーク>文具",
                  "qoo_catid": "300000525", "qoo_catname": "文具_文房具_筆記具",
                  "s_keyword": "おしゃれ シンプル 中学生 男子 大人 大容量 革   スリム 大人女子 女子高校生 女子 韓国 オシャレ 女子中学生 高校生 女の子 白 黒 透明 かわいい スポーツメーカー  スタンド 女性 大人かわいい 男 メンズ 多機能 立つ キャラクター 筆箱 ツール ポーチ 中小学生 レディース 3本差し 万年筆 1本差し ピンク がま口 ベージュ パール 040 水色 赤 ニキ ハチドリ ゴリラ"},
        "健康ボード": {"ctname": "オークション > ビューティー、ヘルスケア > 健康用品、健康器具 > その他", "y_ct": "2084042545", "sex": "0", "male": "",
                  "female": "", "wowma_catid": "34051903", "wowma_catname": "キッズベビー・マタニティ>ベビー>衛生・ヘルスケア>その他衛生・ヘルスケア",
                  "qoo_catid": "320000478", "qoo_catname": "ベビー・マタニティ_衛生用品・ヘルスケア_その他",
                  "s_keyword": "足のつぼ  足つぼマット ポータブル 足つぼマッサージ シート フットマッサージ マット 足ツボ 足裏 棒 スリッパ"},
        "犬の服": {"ctname": "オークション > 住まい、インテリア > ペット用品 > 犬 > 服 > 小型犬用 > その他", "y_ct": "2084057211", "sex": "0",
                "male": "", "female": "", "wowma_catid": "491105",
                "wowma_catname": "ペット・ペットグッズ>犬用品・ドッグフード>ドッグウェア・アクセサリー", "qoo_catid": "320000755",
                "qoo_catname": "ペット_ペット用品_その他",
                "s_keyword": "春夏 春用 夏 お揃い つなぎ 春夏用 本 足まで 4s 中型犬 春夏メス用 中型犬マザーグース 春夏背中開き 春夏短め 春夏マジックテープ 春夏無地tシャツ 春夏蚊よけ 春用つなぎ 春用 xs 春用中型犬 春用中かた 夏服 コットン 脱げない 大型犬 夏ワンピース 夏サッカー 冷却 lee つなぎ夏用 春夏用ll 編み物 小型犬 安い 型紙 アディドッグ 赤 アロハ アニメ あったかい イタグレ いちご 海 エックスガール 女の子 おしゃれ 男の子 ロンパース 面白い"},
        "ドッグウエア": {"ctname": "オークション > 住まい、インテリア > ペット用品 > 犬 > 服 > 小型犬用 > その他", "y_ct": "2084057211", "sex": "0",
                   "male": "", "female": "", "wowma_catid": "491105",
                   "wowma_catname": "ペット・ペットグッズ>犬用品・ドッグフード>ドッグウェア・アクセサリー", "qoo_catid": "300000534",
                   "qoo_catname": "ペット_犬用品_ドッグウェア",
                   "s_keyword": "小型犬 中型犬 大型犬 夏用 ブランド  春夏 パーカー シンプル ー 小型犬お嬢様 ハーネス付き ダックス タキシード と便利グッズ"},
        "アイフォンケース": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0",
                     "male": "", "female": "", "wowma_catid": "410509",
                     "wowma_catname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>スマホケース", "qoo_catid": "320002219",
                     "qoo_catname": "スマホケース・保護フィルム_iPhoneケース_その他 iPhone ケース",
                     "s_keyword": "12 se 13 11 8 xr 13pro 11pro 手帳型 12pro 12mini 12promax 12ミニ シリコン 可愛い 透明 se2 se3 第2世代 キャラクター  ショルダー 13ミニ 13mini おしゃれ 13promax かわいい 韓国 max 11promax リング付き  オシャレ 8プラス 薄型 チェキ ケース 紐付き リング 13proケース  ブランド レザー 首掛け グレージュ 手帳型肩掛け 白黒 ワンピース クリア アニメ"},
        "ハーネス": {"ctname": "オークション > 住まい、インテリア > ペット用品 > 犬 > 首輪、リード > リード", "y_ct": "2084062614", "sex": "0",
                 "male": "", "female": "", "wowma_catid": "40111011", "wowma_catname": "スポーツ・アウトドア>アウトドア>トレッキング用品>ハーネス",
                 "qoo_catid": "320000684", "qoo_catname": "ペット_猫用品_首輪・ハーネス",
                 "s_keyword": "猫 犬 安全帯 新規格 セット 小型犬 ユリウスk9 犬用小型犬 中型犬 抜けない 日本製 おすすめ ダブルロック かわいい 大きいサイズ 可愛い おしゃれ 名前入り 用 大型 ラディカ トレポンティ セットタジマ 軽量 セット椿モデル セットたじま タイタン 紫 金具 y型リール式 藤井電工 ペット 夏 デニム 人気 ペティオ タジマ 椿モデル ランヤード ミニミニ mini baby2 メッシュ 大型犬 サイズ0 名前ラベル ベイビー2 ネームラベル 犬用小型犬かわいい 犬用小型犬抜けにくい"},
        "ブックマーク": {"ctname": "オークション > 事務、店舗用品 > 文房具 > その他", "y_ct": "2084042489", "sex": "0", "male": "", "female": "",
                   "wowma_catid": "29061115", "wowma_catname": "おもちゃ・趣味>アート・美術品・骨董品>骨董品・アンティーク>文具",
                   "qoo_catid": "320000559", "qoo_catname": "文具_手帳・ダイアリー_その他",
                   "s_keyword": "おしゃれ しおり 金属 マグネット クリップ 革 かわいい セット チェーン 女性 ギフト お洒落 おしゃれ金属 桜 みどり 曜日 パーツ 可愛い 大きい クリップ式 名入れ プレゼント アニメ アート アリス アンティーク アプリ 犬 伊東屋 インデックス イタリア 薄い ウィリアムモリス エッフェル塔 おもしろ 音楽 面白い 落ちない 音符 紙 韓国 皮 かっこいい 神 軽い キャラクター 木 キティ 恐竜 金"},
        "しおり": {"ctname": "オークション > 事務、店舗用品 > 文房具 > その他", "y_ct": "2084042489", "sex": "0", "male": "", "female": "",
                "wowma_catid": "29061115", "wowma_catname": "おもちゃ・趣味>アート・美術品・骨董品>骨董品・アンティーク>文具",
                "qoo_catid": "300000532", "qoo_catname": "文具_文房具_その他",
                "s_keyword": "栞 おしゃれ 18 えくすぺりえんす 金属 本 栞と紙魚子 新装版 木製 猫 紐 栞子 寝そべり メガネ 男性 女性 オシャレ プレゼント 可愛い 全巻 エクスペリエンス 栞エクスペリエンス 17 桜 花 パーツ 和風 星座 クリップ 16 セット 12 グッズ 本革 プラスチック かわいい 詩織 ガメラ フィルム マンガ マグネット 革 アニメ アニメキャラクター アンティーク アート アリス アクリル 犬 イタリアン"},
        "肩サポーター": {"ctname": "オークション > ビューティー、ヘルスケア > 健康用品、健康器具 > サポーター > その他", "y_ct": "2084216486", "sex": "0",
                   "male": "", "female": "", "wowma_catid": "54090216",
                   "wowma_catname": "日用品・文房具・手芸用品>手芸・クラフト・生地>その他手芸用品>肩パット", "qoo_catid": "300003396",
                   "qoo_catname": "ドラッグストア_その他医薬部外品_その他",
                   "s_keyword": "右肩用 女性 五十肩 50肩 日本製 左肩用 左肩用リハビリ 男用 両肩 ダークグレー 両肩用 両肩タイプ 女性用 コンプレッション あたため ショルダーラップ 肩 サポーター 医療用  薄手 chefal  冷え おすすめ 大きいサイズ 大きい 肩こり 担ぐ 簡単 寝るとき 巻き肩 route1 肩用サポーター 柔道整復師が認めた 肩の保護安定 左右兼用 フリーサイズ クッション 腱板断裂 子供 固定 骨折 首 肩らくらく さらさら快適ver 衝撃吸収 スポーツ 筋トレ 白十字 fc 遠赤サポーター肩当 ふつうサイズ"},
        "荒野行動コントローラー": {"ctname": "オークション > コンピュータ > 周辺機器 > 入力装置 > ジョイスティック", "y_ct": "2084039610", "sex": "0",
                        "male": "", "female": "", "wowma_catid": "61011004",
                        "wowma_catname": "音楽・映像>映像DVD・Blu-ray>ミュージックビデオ>アニメ・ゲーム・声優", "qoo_catid": "320001949",
                        "qoo_catname": "テレビゲーム_その他ゲーム_その他ゲーム",
                        "s_keyword": "iphone iphone13 連打き 荒野行動 コントローラー ipad 連射 android ゴム 6本指 予備 連打機 タブレット codモバイル pubg モバイル  軽く反応 タブレット用 ipad用 ゲームコントローラー 感度 mobile cod 50連打 冷却 六本指 bluetooth スオミ商会 用コントローラー fps tps ゲームパット 6.7インチ iphone12 mini zoyubs プロの荒野行動 モバイルコ aiyujiwu 2020最新 最新型 スマホゲーム パッド"},
        "タイヤ エア バルブ キャップ": {"ctname": "オークション > 自動車、オートバイ > 工具 > タイヤチェンジャー", "y_ct": "2084261043", "sex": "0",
                            "male": "", "female": "", "wowma_catid": "33641610",
                            "wowma_catname": "カー用品・バイク用品>カー用品>タイヤ・ホイール>エアバルブキャップ", "qoo_catid": "300000258",
                            "qoo_catname": "カー用品_カー用品_その他",
                            "s_keyword": "タイヤ エアーバルブ キャップ エアバルブキャップ メルセデスベンツ 赤 スバル bmw メッキ レインボー"},
        "インナーパンツ": {"ctname": "オークション > ファッション > レディースファッション > レギンス、トレンカ", "y_ct": "2084007161", "sex": "0", "male": "",
                    "female": "", "wowma_catid": "40530303",
                    "wowma_catname": "スポーツ・アウトドア>陸上・トラック競技>陸上競技用ウェア>インナーパンツ・スパッツ", "qoo_catid": "300002872",
                    "qoo_catname": "スポーツ_スポーツウェア_レディーススポーツインナー",
                    "s_keyword": "レディース メンズ 女の子 パールイズミ サイクル 自転車 サッカー ロードバイク スポーツ 黒 ゴルフ 夏 水着 綿 大きいサイズ ロング 冬 防寒 白 前開き 100 ダンス フリル 130 3dメガ パッド ジュニア キッズ 滑り止め ゲル 夏用 青 赤 アウトドア 一分丈 裏起毛 海 柄 女 カラー グレー 子供 クッション 透け防止 しちぶたけ 七分たけ 高校生 コンプレ 子ども こども"},
        "Vネック ニット": {"ctname": "オークション > ファッション > レディースファッション > ニット、セーター > 長袖 > Mサイズ", "y_ct": "2084064247", "sex": "0",
                     "male": "", "female": "", "wowma_catid": "510811", "wowma_catname": "レディースファッション>トップス>ニット・セーター",
                     "qoo_catid": "300000025", "qoo_catname": "レディースファッション_トップス_ニット",
                     "s_keyword": "vネック ニット レディース 大きいサイズ ピンク カシミヤ 綿 着丈64 長袖 4l メンズ ニットベスト ワンピース 薄手 ゆったり パープル 白 ネイビー ベスト ニットセーター セーター トップス 畦編み 無地 おしゃれ ビジネス 2点セット シャツ きれいめ カジュアル 大人可愛い 韓国ファッション  重ね着風 二重襟付き スクール ニットカーディガン 秋冬 40代 ショット アウター 50代 30代 ニットせーたー vネックのニット 春 半袖  チルデン ケーブル編み オーバーサイズ"},
        "タブレット用 折りたたみ式 スタンド": {"ctname": "オークション > コンピュータ > 周辺機器 > その他", "y_ct": "2084048551", "sex": "0", "male": "",
                               "female": "", "wowma_catid": "410706",
                               "wowma_catname": "スマホ・タブレット・モバイル通信>タブレットPCアクセサリー>タブレットPC用液晶保護フィルム",
                               "qoo_catid": "320002278", "qoo_catname": "スマートフォン・タブレットPC_スマートフォン用アクセサリー_スマートフォン用スタンド",
                               "s_keyword": "vネック ニット レディース 大きいサイズ ピンク カシミヤ 綿 着丈64 長袖 4l メンズ ニットベスト ワンピース 薄手 ゆったり パープル 白 ネイビー ベスト ニットセーター セーター トップス 畦編み 無地 おしゃれ ビジネス 2点セット シャツ きれいめ カジュアル 大人可愛い 韓国ファッション  重ね着風 二重襟付き スクール ニットカーディガン 秋冬 40代 ショット アウター 50代 30代 ニットせーたー vネックのニット 春 半袖  チルデン ケーブル編み オーバーサイズ"},
        "折り畳み式スタンド": {"ctname": "オークション > コンピュータ > 周辺機器 > その他", "y_ct": "2084048551", "sex": "0", "male": "",
                      "female": "", "wowma_catid": "410903",
                      "wowma_catname": "スマホ・タブレット・モバイル通信>バッテリー・充電器>スマホ・タブレット用充電器", "qoo_catid": "320002278",
                      "qoo_catname": "スマートフォン・タブレットPC_スマートフォン用アクセサリー_スマートフォン用スタンド",
                      "s_keyword": "kankan 携帯置き台 kksmart lomicall klearlook ノートパソコン スタンド 折畳み式 pc アルミ合金製 安定性あり ブラック weimall アルミラダー 2本セット 折り畳み式 スタンド付き 軽量 滑りにくい アルミ ラダーレール アルミブリッジ aタイプ 折りたたみ式 読書スタンド ベッド ソファ 床 畳 車内で使える tongyong スマホスタンド 高さ調整 卓上 ホルダー おりたたみ 滑り止め 携帯 スマホ拡大鏡 16インチスクリーン 5倍 携帯に便利 各機種に対応 h&y エイチアンドワイ 床置きスタンド アーム折り畳み式 cyfie バッティングティー 野球 練習スタンド 折り畳み 持ち運び便利 硬式"},
        "スノボ膝プロテクター": {"ctname": "オークション > スポーツ、レジャー > スポーツ別 > スノーボード > ウエア、装備（男性用） > プロテクター", "y_ct": "2084284390",
                       "sex": "0", "male": "", "female": "", "wowma_catid": "405104",
                       "wowma_catname": "スポーツ・アウトドア>自転車>サイクルプロテクター", "qoo_catid": "300000246",
                       "qoo_catname": "アウトドア_ウィンタースポーツ_その他", "s_keyword": "スノボ 膝 プロテクター メンズ 肘"},
        "エアーギター": {"ctname": "オークション > ホビー、カルチャー > 楽器、器材 > ギター > エレキギター > 本体 > その他", "y_ct": "2084019026", "sex": "0",
                   "male": "", "female": "", "wowma_catid": "562403", "wowma_catname": "楽器・音響機器>ギター>エレキギター",
                   "qoo_catid": "320000075", "qoo_catname": "楽器_ギター_その他",
                   "s_keyword": "ギターバルーン エアー ギター 楽器 パーティー おもちゃ ギター アコースティックギター 初心者向け 入門練習用ギター アコギギター 学生・初心者入門セット ギター 入門レベル 入門練習ギター ブラック"},
        "リアキャップ": {"ctname": "オークション > 家電、AV、カメラ > カメラ、光学機器 > レンズ > 一眼カメラ用（マニュアルフォーカス） > その他", "y_ct": "2084261700",
                   "sex": "0", "male": "", "female": "", "wowma_catid": "44020402",
                   "wowma_catname": "テレビ・オーディオ・カメラ>カメラ>カメラ用周辺機器・アクセサリー>その他カメラ用周辺機器・アクセサリー", "qoo_catid": "320002188",
                   "qoo_catname": "カメラ・光学機器用_レンズ用アクセサリー_レンズキャップ",
                   "s_keyword": "マウント対応ボディ レンズリアキャップ セット プラスチック カメラボディ Fマウントカメラレンズ用 防塵 コンパクト 耐久 マウント用 交換用品 "},
        "シューズカバー": {"ctname": "オークション > スポーツ、レジャー > 自転車、サイクリング > ウエア > ウォーマー、カバー", "y_ct": "2084229858", "sex": "0",
                    "male": "", "female": "", "wowma_catid": "402505",
                    "wowma_catname": "スポーツ・アウトドア>スポーツシューズ>シューズケース・バッグ", "qoo_catid": "300000081",
                    "qoo_catname": "メンズバッグ・シューズ・小物_メンズシューズ_その他",
                    "s_keyword": "防水 使い捨て 雨 シリコン ロードバイク レイン 子供 不織布 バイク 自転車 ロング キッズ 滑り止め ビニール 感染対策 靴カバー ブーツカバー 完全防水 くつカバー 防水-20枚 レディース 雨の日 歩きやすい シリコン自転車用 パールイズミ ソックス apt シマノ 防寒 エアロ 当日発送 レインウェア メンズ 台風対策 雨具 子供用 バレエ 厚手 赤ちゃん アウトドア 足首 医療用 医療 上 大きいサイズ 大きい オートバイ おしゃれ 革靴 カメラ"},
        "ドッグウェア": {"ctname": "オークション > 住まい、インテリア > ペット用品 > 犬 > 服 > 小型犬用 > その他", "y_ct": "2084057211", "sex": "0",
                   "male": "", "female": "", "wowma_catid": "491105",
                   "wowma_catname": "ペット・ペットグッズ>犬用品・ドッグフード>ドッグウェア・アクセサリー", "qoo_catid": "300000534",
                   "qoo_catname": "ペット_犬用品_ドッグウェア",
                   "s_keyword": "小型犬 中型犬 大型犬 夏用 ブランド  春夏 パーカー シンプル ー 小型犬お嬢様 ハーネス付き ダックス タキシード と便利グッズ"},
        "反射ステッカー": {"ctname": "オークション > 自動車、オートバイ > アクセサリー > ステッカー、デカール > トラック、ダンプ用", "y_ct": "2084291447", "sex": "0",
                    "male": "", "female": "", "wowma_catid": "6012", "wowma_catname": "車本体・バイク原付本体>バイク・原付本体",
                    "qoo_catid": "300000253", "qoo_catname": "カー用品_バイク用品_その他",
                    "s_keyword": "工房 ドラレコ ドラレコステッカー マグネット 国旗 宅配ボックス 猫 ドライブレコーダー ポスト ねこ  車 バイク 自転車 かわいい ヘルメット 黒 白 ミラー 名前 ランドセル 緑 赤 青 アウトドア キッズいんかー ステッカー反射 isdy 割れない鏡 貼る鏡 シール シート ウォール ステッカー 鏡 反射板 レフ版 ウクライナ国旗 おもしろ 黄色 恐竜 君が代 キャラクター シルバー スカル セキュリティ ステッカーしーと 耐水 反射 日本 肉球"},
        "エア枕": {"ctname": "オークション > スポーツ、レジャー > キャンプ、アウトドア用品 > 寝袋、寝具 > その他", "y_ct": "2084263235", "sex": "0",
                "male": "", "female": "", "wowma_catid": "40110910",
                "wowma_catname": "スポーツ・アウトドア>アウトドア>テント>レジャーシート・ブランケット", "qoo_catid": "320000766",
                "qoo_catname": "アウトドア_キャンプ用品_アウトドア用寝具",
                "s_keyword": "アウトドア 防災 携帯 旅行 コンパクト 安い 低反発 防水 ロゴス 災害 エア インパクト レンチ インソール 椅子 抱き枕 インフレーター 池 インパクトドライバー 一方コック イヤフォン ウォーター エアウォール ウェーブ まくら ウォールuv ウィー ヴ エアウーブン マッハ マットレス ウォーキング ウィルソン エボリューション エレメント エアジョーダン ロー トロピカルツイスト 延長 エルボ エクステンション オプティクス ex アクア プラス ハイドラグライド 乱視用 遠近両用 オナホ オットマン"},
        "空気まくら": {"ctname": "オークション > スポーツ、レジャー > キャンプ、アウトドア用品 > 寝袋、寝具 > その他", "y_ct": "2084263235", "sex": "0",
                  "male": "", "female": "", "wowma_catid": "40110910",
                  "wowma_catname": "スポーツ・アウトドア>アウトドア>テント>レジャーシート・ブランケット", "qoo_catid": "320000766",
                  "qoo_catname": "アウトドア_キャンプ用品_アウトドア用寝具",
                  "s_keyword": "携帯型 エアー枕 飛行機  アウトドア 夜行バス いつも綺麗 じゃなくていい 50歳からの美人の 空気 のまといかた homca 枕 まくら 低反発 中空設計 ピロー 良い通気性 プレゼント カバー洗える おすすめ 抱きまくら だきまくら kingcamp キャンプ枕 エアーピロー 旅行枕 キャンプまくら 空気枕 腰枕 洗える可能 超軽量 コンパクト 収納袋付き ア ぷらずまくらすたー 空気清浄機 たわしまくら 悟空の気持ちダイゴ 悟空の気持ち フィルター くびまくら 車 7000"},
        "USB充電ポート": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > バッテリー、充電器 > USB式充電器", "y_ct": "2084239197",
                     "sex": "0", "male": "", "female": "", "wowma_catid": "410903",
                     "wowma_catname": "スマホ・タブレット・モバイル通信>バッテリー・充電器>スマホ・タブレット用充電器", "qoo_catid": "320002033",
                     "qoo_catname": "生活家電_電池_充電器",
                     "s_keyword": "usb充電ポート 車 リュック 複数 クランプ固定式 マツダ 電源タップ 壁付け アンカー スイッチ anker type-c 多機能 大容量 バックパック 可愛い 発光 盗難防止 usb充電ポート搭載 男女兼用 旅行 登山 中学生 高校生 並行輸入品 usb 充電アダプタ 2ポート あいふおん充電コード アダプタ usbポート きゅうそく充電器 3ポート 4ポート 充電器 12w acアダプター 1m iphone 充電ケーブル 2本付き コンセント スマホ充電器 usb付き タイプc 2つusb-c pd 急速充電ポート ３個usb充電ポート 3つacコンセント yeslau ショルダーバッグ メンズ 斜めがけ ボディバッグ 防水 肩掛けバッグ ipad収納可能 通勤"},
        "キーカバー": {"ctname": "オークション > 自動車、オートバイ > アクセサリー > キーホルダー > その他", "y_ct": "2084210631", "sex": "0", "male": "",
                  "female": "", "wowma_catid": "450407", "wowma_catname": "バッグ・財布・ファッション小物>ファッション小物>キーホルダー・キーリング",
                  "qoo_catid": "300002385", "qoo_catname": "バッグ・雑貨_小物_キーホルダー",
                  "s_keyword": "シリコン キャラクター スズキ 革 ホンダ かわいい ベンツ アルファード 家 可愛い 人気 サンリオ カービィ ワンピース スペーシア 純正 スイフト ワゴンr バイク ソリオ 三菱 車 ヤリス 黒 25mm ネック フリード ヴェゼル オデッセイ ステップワゴン リモコン 動物 レザー amg bクラス tpu カーボン ゴールド glc 2ボタン 30系 30系後期 20系 グリーン 猫 アニメ アルミ アラレちゃん 赤 アニマル"},
        "ランチョンマット": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > テーブルリネン > ランチョンマット", "y_ct": "2084046785", "sex": "0",
                     "male": "", "female": "", "wowma_catid": "340815",
                     "wowma_catname": "キッズベビー・マタニティ>子供用キッチン・お弁当グッズ>子供用ランチョンマット", "qoo_catid": "320000804",
                     "qoo_catname": "キッチン用品_キッチン雑貨_ランチョンマット",
                     "s_keyword": "小学生 40cm 60cm 幼稚園 40 60 おしゃれ 中学生男子 シリコン 布製 25 35 男の子 女の子 50 30 給食 綿 布 キャラクター 無地 20 小さめ ビニール キティ パウパトロール 小学校 すみっこ オシャレ 北欧 洗える 撥水 セット お洒落 丸 6枚 子供 かわいい 大きめ 赤ちゃん 雲 ポケット 4枚 布製45 大判 動物 こぐまちゃん おさるのジョージ サンリオ 恐竜"},
        "ボールペン": {"ctname": "オークション > 事務、店舗用品 > 文房具 > 筆記用具 > ボールペン > ボールペン一般", "y_ct": "2084064350", "sex": "0",
                  "male": "", "female": "", "wowma_catid": "54090201",
                  "wowma_catname": "日用品・文房具・手芸用品>手芸・クラフト・生地>その他手芸用品>その他", "qoo_catid": "320001574",
                  "qoo_catname": "おもちゃ・知育_子供用文房具_ペン",
                  "s_keyword": "高級 女性 名入れ 男性 三色 パーカー 名前入れ 高級感 多機能 ジェットストリーム 3色 0.5 0.38 0.7 替え芯 三菱  uni キャラクター bt21 ソネット ジョッター im ギフト 名入れ無料 アーバン レディース かきやすい 人気 0.3 書きやすい 3色赤青黒 人気キャラクター 4色 パイロット ジュース アクロボール 替芯 ジャニーズwest brfs-10f ドクターグリップ 赤 モンブラン リフィル pix m f スターウォーカー 細字 25872 サラサ"},
        "巾着": {"ctname": "オークション > ファッション > 女性和服、着物 > きんちゃく、バッグ > 巾着", "y_ct": "2084308407", "sex": "0", "male": "",
               "female": "", "wowma_catid": "34010412", "wowma_catname": "キッズベビー・マタニティ>キッズ>バッグ・ランドセル>巾着袋",
               "qoo_catid": "320000797", "qoo_catname": "キッチン用品_キッチン雑貨_ランチバッグ・巾着",
               "s_keyword": "袋 男の子 女の子 大 小 無地 特大 体操服 おしゃれ 防水  バッグ ポーチ 給食袋 コップ セット コップ入れ 体操服入れ 中 シンプル 大きめ キャラクター 大人 スポーツ 小さい 小学生 コップ袋 小さめ 和柄 小物入れ コットン 布 綿 黒 ナイロン レディース メンズ ショルダー レザー 革 カジュアル 斜めがけ 韓国 かわいい 可愛い ブランド ポーチとバッグ 本 50cm 大容量 持ち手"},
        "フィッシングルアー": {"ctname": "オークション > スポーツ、レジャー > フィッシング > ルアー用品 > その他", "y_ct": "2084303062", "sex": "0",
                      "male": "", "female": "", "wowma_catid": "40340701",
                      "wowma_catname": "スポーツ・アウトドア>フィッシング>ルアー・フライ>その他ルアー・フライ", "qoo_catid": "320001600",
                      "qoo_catname": "アウトドア_フィッシング用品_ルアー", "s_keyword": "ベイト タックルボックス"},
        "フィシングルアー": {"ctname": "オークション > スポーツ、レジャー > フィッシング > ルアー用品 > その他", "y_ct": "2084303062", "sex": "0",
                     "male": "", "female": "", "wowma_catid": "40340701",
                     "wowma_catname": "スポーツ・アウトドア>フィッシング>ルアー・フライ>その他ルアー・フライ", "qoo_catid": "320001600",
                     "qoo_catname": "アウトドア_フィッシング用品_ルアー", "s_keyword": "フィッシングルアー タックルボックス"},
        "ラッピング ボックス": {"ctname": "オークション > 事務、店舗用品 > ラッピング、包装 > ギフトボックス", "y_ct": "2084221001", "sex": "0", "male": "",
                       "female": "", "wowma_catid": "54131306", "wowma_catname": "日用品・文房具・手芸用品>日用品・生活雑貨>梱包資材>ダンボール",
                       "qoo_catid": "320000539", "qoo_catname": "文具_文房具_ギフトラッピング用品",
                       "s_keyword": "小 透明 大 おしゃれ クリア 長方形 クッキー 正方形 お菓子 ラッピングボックス アクセサリー 赤 薄型 腕時計 かわいい 缶 窓付きボックス ラッピング 窓付きボックス手提げ 子供 スポンジ ハンカチ 引き出し 服 本 窓付き 窓 マグネット 丸 丸型 無地 リボン付き ベージュ 業務用 ジュエリー バレンタイン 瓶 ポロシャツ ピロー型 100mm 300mm 15cm 1個 10cm 35cm"},
        "保護ガラス": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール", "y_ct": "2084299106", "sex": "0",
                  "male": "", "female": "", "wowma_catid": "410518",
                  "wowma_catname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>液晶保護フィルム", "qoo_catid": "320002243",
                  "qoo_catname": "スマホケース・保護フィルム_保護フィルム_多機種対応保護フィルム",
                  "s_keyword": "13mini  ブルーライトカット 覗き見防止 カメラ アンチグレア ランキング spigen 指紋 日本製 iphone 10s ブルーライト iphone13 pixel 3a iphone12 11 iphone8 se2 se ゴリラ iface フィルム iphone12ミニ max mini elecom pro 10ｈ se3 se第2世代 5s 0.2mm se第３世代 あくおすせんす6 保護シート ガラス あくおすセンス4 保護フィルム いphone11 ipadだい9世代 ふぁーうえい p30 lite はーうぇい スマートウォッチ gt2 スイッチえきしょう エクスペリア 液体"},
        "ヨガ スポーツ ウェア": {"ctname": "オークション > スポーツ、レジャー > スポーツ別 > エクササイズ用品 > ウエア > 女性用 > スパッツ", "y_ct": "2084006880",
                        "sex": "0", "male": "", "female": "", "wowma_catid": "402309",
                        "wowma_catname": "スポーツ・アウトドア>スポーツウェア>ウェア", "qoo_catid": "320001852",
                        "qoo_catname": "ダイエット・矯正_シェイプアップ・ダイエットグッズ_着圧レギンス・スパッツ",
                        "s_keyword": "anatman ヨガ ソックス 5本指 滑り止め 付き yoga ホットヨガ 靴下 ウェア スポーツ ジム スポーツウェア レディース"},
        "レッグパンツ": {"ctname": "オークション > ファッション > レディースファッション > パンツ、スラックス > Mサイズ", "y_ct": "2084224590", "sex": "0",
                   "male": "", "female": "", "wowma_catid": "511001", "wowma_catname": "レディースファッション>パンツ>その他パンツ",
                   "qoo_catid": "300002302", "qoo_catname": "メンズファッション_ビジネス・フォーマル_パンツ・スラックス",
                   "s_keyword": "メンズ スウェットパンツ ワイドレッグパンツ ズボン ジョガーパンツ 作業着 トレーニングウェア 無地 カジュアル おおきい サイズ 春 夏 秋 冬 ワイドレッグパンツ レディース ワイドパンツ ストレッチ パンツ ズボン ボトム スポーツ アウトドア ルームウェア 部屋着 柄 派手 ベルト付き ジーンズ ゆったり 大きいサイズ ハイウエスト ジーンズ ロング丈 レディース カーゴパンツ ジーンズ ミリタリーパンツ ストリート おしゃれ"},
        "レインコート": {"ctname": "オークション > スポーツ、レジャー > キャンプ、アウトドア用品 > 雨具、レインウエア > その他", "y_ct": "2084208701", "sex": "0",
                   "male": "", "female": "", "wowma_catid": "500539", "wowma_catname": "メンズファッション>ジャケット・アウター>レインコート",
                   "qoo_catid": "320001552", "qoo_catname": "日用品雑貨_生活雑貨_レインコート",
                   "s_keyword": "自転車 キッズ レディース メンズ リュック対応 上下 犬 ルックス 通学 ママ 人気 リュック ランドセル対応 男の子 女の子 100 ランドセル wpc kiu おしゃれ ロング 自転車用 上下セット ポンチョ メンズ大きいサイズ メンズ上下 大きい バイク ビジネス 軽量 リュック対応3l 上下別 子供 防水 日本製 白 中型犬 小型犬 大型犬 着せやすい おすすめ 柴犬 呉工業 詰め替え つめかえ用 詰め替え用 ２２０ アウトドア 赤ちゃん 足カバー"},
        "カバーケース": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0",
                   "male": "", "female": "", "wowma_catid": "410509",
                   "wowma_catname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>スマホケース", "qoo_catid": "320002232",
                   "qoo_catname": "スマホケース・保護フィルム_その他スマホケース_多機種対応ケース",
                   "s_keyword": "surface laptop 4  13.5 15インチ 純正 水色 かわいい キャラクター あつ森 go3 ホワイト マニア エクスペディア galaxy se iphone13 pro s22 b5 イルマワン あいぱっとだい8世代 あいぱっとえあー4 えあーぽっつ プロ ふぁーうえい mini iphone 13がんじょう ipad air お絵描き iphone12 おしゃれ パソコン かわいい15インチ キーボード付き 第9世代 山崎産業 ラバーカップ 洋式 al付き トイレ つまり取り al 付き 139880 iphonese3 滑りにくい ぐーぐるぴくせる6"},
        "iPhone X ケース": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0",
                         "male": "", "female": "", "wowma_catid": "410509",
                         "wowma_catname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>スマホケース", "qoo_catid": "320002216",
                         "qoo_catname": "スマホケース・保護フィルム_iPhoneケース_iPhoneX",
                         "s_keyword": "iphone x ケース 手帳型 iface リング クリア シリコン カード かわいい 透明 おしゃれ ブランド 本革 花柄 キャラクター 栃木レザー 猫 first class marvel ハード キラキラ ストラップ リング付き 充電可能 マグネット グリーン リングティンカーベル リング可愛い リング付 黒 赤 黄色 カード収納 背面 ショルダー 高級 ネックストラップ 韓国 サンリオ レディース 可愛い あいふぇいす あいフェイス あいフェース うす型 うさぎ ドラえもん xケース ぶりぶりざえもん"},
        "iPhoneカバー": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0",
                      "male": "", "female": "", "wowma_catid": "410509",
                      "wowma_catname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>スマホケース", "qoo_catid": "320002219",
                      "qoo_catname": "スマホケース・保護フィルム_iPhoneケース_その他 iPhone ケース",
                      "s_keyword": "iphoneカバー se 手帳型 透明 花柄 se2 可愛い キャラクター マグリット 手帳型かわいいキャラ 旧式 mini max リング クリア 韓国 手帳型薄い オススメ lifeproof fre iphoneカバー8 シリコン 皮製品 xr おしゃれ ポケット カード収納 ミッキー ブランド suica x 13 pro xs 7 iphone カバー アニメ アイフェイス 赤 アルミ アウトドア アップル 青 s 犬 イルミナティ イーブイ 薄型 転スラ 薄い"},
        "iphoneケース": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0",
                      "male": "", "female": "", "wowma_catid": "410509",
                      "wowma_catname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>スマホケース", "qoo_catid": "320002219",
                      "qoo_catname": "スマホケース・保護フィルム_iPhoneケース_その他 iPhone ケース",
                      "s_keyword": "13 se 12 11 トムとジェリー 11pro xr 13pro xs 13mini 13promax 韓国 13手帳型 キャラクター max クリア se2 手帳型 se3 カード収納 可愛い iface かわいい 12プロ mini 12ミニ 12promax 透明 肩掛け カップル 12mini 11proマックス シリコン ブランド リング付き ショルダー キラキラ ストラップ xsマックス 8 アルミ アイフェス アルミバンパー アクスタ あんぱんまん アイフェイス透明 アイフェス13 アニメキャラクター あつ森 アップルロゴ"},
        "携帯電話用防水ケース": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0",
                       "male": "", "female": "", "wowma_catid": "410509",
                       "wowma_catname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>スマホケース", "qoo_catid": "320002232",
                       "qoo_catname": "スマホケース・保護フィルム_その他スマホケース_多機種対応ケース",
                       "s_keyword": "iphoneケース se 12 11 トムとジェリー 11pro xr xs 韓国 キャラクター max クリア se2 手帳型 se3 カード収納 可愛い iface かわいい 12プロ mini 12ミニ 12promax 透明 肩掛け 11proマックス シリコン ブランド リング付き ショルダー キラキラ ストラップ xsマックス 8 13 アルミ アイフェス アルミバンパー アクスタ あんぱんまん アイフェイス透明 アイフェス13 アニメキャラクター あつ森 アップルロゴ インナーシート イヤホン イレブンプロ 色が変わる 一体型 イワンコフ"},
        "TPU ケース": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0",
                    "male": "", "female": "", "wowma_catid": "410509",
                    "wowma_catname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>スマホケース", "qoo_catid": "320002232",
                    "qoo_catname": "スマホケース・保護フィルム_その他スマホケース_多機種対応ケース",
                    "s_keyword": "tpu ケース iphone13 iphone se tpuケース あいふぉん13ケース あくおすセンス4 カバー いphone11 iphone12 韓国 かわいい いphonese 第1世代 えあぽっつ3 おしゃれ レンズ保護 シンプルおしゃれ かんたんスマホ2 アイホン8 ipad mini5 ペンホルダー付き xperia 5 iii リング付き 耐衝撃 so-53b sog05 炭素繊維 11 pro 透明 黒 teclast t40 plus tpu蓋なし ストラップ ぐーぐるぴくせる6 ぴくせる6 ケースtpu トムとジェリー airpods チップとデール ケース第三世代に適用 キーチェーン付き tpuカバー ワイヤ"},
        "Lightningケーブル": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > バッテリー、充電器 > USB式充電器", "y_ct": "2084239197",
                          "sex": "0", "male": "", "female": "", "wowma_catid": "410903",
                          "wowma_catname": "スマホ・タブレット・モバイル通信>バッテリー・充電器>スマホ・タブレット用充電器", "qoo_catid": "320002327",
                          "qoo_catname": "パソコン_PCケーブル_ライトニングケーブル",
                          "s_keyword": "usbc anker 2m usb-c 短い apple - type-c usb c to 1m 3m 0.1 0.3 l字 変換 高耐久 typec 1.8m セット mfi認証 黒 5本 純正 タイプc ピンク pd対応 10cm 0.2m 急速充電 早い 2 m 1 1.5m 0.5m pd アンカー 50cm 0.1m 0.2 マグネット ugreen mfi 3本 ロジテック 高耐久ナイロン 1メートル アップル アップル純正"},
        "iPhoneケーブル": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > バッテリー、充電器 > USB式充電器", "y_ct": "2084239197",
                       "sex": "0", "male": "", "female": "", "wowma_catid": "410903",
                       "wowma_catname": "スマホ・タブレット・モバイル通信>バッテリー・充電器>スマホ・タブレット用充電器", "qoo_catid": "320002327",
                       "qoo_catname": "パソコン_PCケーブル_ライトニングケーブル",
                       "s_keyword": "iphoneケーブル 高速充電 純正品 1m 高速充電タイプc 2m 3m 短い 純正 ピンク 50cm アンカー タイプc ゴールド 急速 mfi 2本 純正品短い amazon製 丈夫 apple データ転送 iphone ケーブル アマゾンベーシック アダプター アップル純正 赤 あんかー アクセサリー イヤホン イヤホン接続 薄い 薄型 液晶 電圧 オーディオ おすすめ 音楽 音楽用 おしゃれ 充電 オウルテック 音声 オレンジ オスメス カバー かわいい カール 可愛い カメラ"},
        "メタル プレート": {"ctname": "オークション > アンティーク、コレクション > 広告、ノベルティグッズ > 看板", "y_ct": "27784", "sex": "0", "male": "",
                     "female": "", "wowma_catid": "29061117", "wowma_catname": "おもちゃ・趣味>アート・美術品・骨董品>骨董品・アンティーク>看板",
                     "qoo_catid": "300000475", "qoo_catname": "家具・インテリア_インテリア・装飾_その他",
                     "s_keyword": "磁石 金色 マグネット ジグ ハンドメイド メタルプレート アメリカン アクセサリー アップル 穴あき アンティーク アドニット イヤリング インテリア 薄い 薄型 英語 おしゃれ 大判 大きい 大きめ オシャレ 壁 角形 カーボン 黒 車 クラフト ケース 携帯 小型 刻印 三角 シール 小 白 車載 手芸 シルバー スマホ 強力 スチール プレート 極薄 充電 3cm スマホリング スクエア ストラップ セット"},
        "スマホホルダー": {"ctname": "オークション > 自動車、オートバイ > アクセサリー > 携帯電話・スマートフォン用品 > ホルダー", "y_ct": "2084286659", "sex": "0",
                    "male": "", "female": "", "wowma_catid": "410509",
                    "wowma_catname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>スマホケース", "qoo_catid": "320002278",
                    "qoo_catname": "スマートフォン・タブレットPC_スマートフォン用アクセサリー_スマートフォン用スタンド",
                    "s_keyword": "車 ワイヤレス充電 マグネット エアコン吹き出し口 自動開閉 充電 クリップ ドリンクホルダー 手帳型対応 吸盤  バイク 自転車 デイトナ 原付 ロードバイク カエディア 防水 振動吸収 ミラー アルミ バイク用 シリコン iphone ワンタッチ ステム ミノウラ 7インチ 3 補修部品 3プラス ゴム ワイド クイック 振動吸収ワイド エアコン アンカー 日本製 15w シガーソケット fmトランスミッター 風呂 キッチン 強力 プレート ミラー取付 落ちない iphone12 13mini 手帳 簡単"},
        "スマホスタンド": {"ctname": "オークション > 自動車、オートバイ > アクセサリー > 携帯電話・スマートフォン用品 > ホルダー", "y_ct": "2084286659", "sex": "0",
                    "male": "", "female": "", "wowma_catid": "410509",
                    "wowma_catname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>スマホケース", "qoo_catid": "320002278",
                    "qoo_catname": "スマートフォン・タブレットPC_スマートフォン用アクセサリー_スマートフォン用スタンド",
                    "s_keyword": "卓上 車 三脚 寝ながら アーム かわいい 充電 自転車 可愛い 木製 高さ調整 おしゃれ スタンド ホルダー 高度調整可能 折りたたみ 2台 ワイヤレス充電 マグネット 車用 自動開閉 クリップ式 エアコン吹き出し口 手帳型ケース対応 カップホルダー コンパクト ライト付き くねくね 長い 2m 自撮り 160cm 持ち運び 床置き 首かけ 布団 日本製 自立 安い 白 クリップ アーム式 ベッド ピンク ipad 犬 猫 キャラクター 動物 ワイヤレス"},
        "外反母趾": {"ctname": "オークション > ビューティー、ヘルスケア > その他", "y_ct": "2084005300", "sex": "0", "male": "", "female": "",
                 "wowma_catid": "34051903", "wowma_catname": "キッズベビー・マタニティ>ベビー>衛生・ヘルスケア>その他衛生・ヘルスケア",
                 "qoo_catid": "320001864", "qoo_catname": "ダイエット・矯正_矯正・マッサージ_外反母趾",
                 "s_keyword": "矯正グッズ 矯正グッズ男性 治療 メンズ 医療 矯正グッズランキング 靴下 シリコン ソルボ 小指  サポーター 矯正 矯正サポーター 医療用 靴 足指サポーター 用靴 レディース インソール 対策サンダル 治っ た 親指 夜 左足 矯正器具 サンダル ソックス 寝る間 男性 左 l 子供用 右足 フィットフィット fitfit コンフォートシューズ おしゃれ スニーカー 男性用 5e 5本指 履きやすい 男 対策 グッズ 薄型メッシュシリコン ジェルパッド 男女兼用 日本製"},
        "レインブーツカバー": {"ctname": "オークション > 自動車、オートバイ > オートバイ > バイクウエア、装備 > 雨具 > ブーツ・シューズカバー", "y_ct": "2084235749",
                      "sex": "0", "male": "", "female": "", "wowma_catid": "51140702",
                      "wowma_catname": "レディースファッション>靴・シューズ>レインシューズ>ショートレインブーツ", "qoo_catid": "300000754",
                      "qoo_catname": "シューズ_ブーツ・ブーティー_レインブーツ",
                      "s_keyword": "バイク用 レディース メンズ sc-001 32cm komine wildwing"},
        "レインフィットカバー": {"ctname": "オークション > 自動車、オートバイ > オートバイ > バイクウエア、装備 > 雨具 > ブーツ・シューズカバー", "y_ct": "2084235749",
                       "sex": "0", "male": "", "female": "", "wowma_catid": "51140702",
                       "wowma_catname": "レディースファッション>靴・シューズ>レインシューズ>ショートレインブーツ", "qoo_catid": "300000754",
                       "qoo_catname": "シューズ_ブーツ・ブーティー_レインブーツ",
                       "s_keyword": "レインブーツカバー メンズ sc-001 32cm バイク用 komine wildwing"},
        "レインブーツ": {"ctname": "オークション > スポーツ、レジャー > キャンプ、アウトドア用品 > 雨具、レインウエア > その他", "y_ct": "2084208701", "sex": "0",
                   "male": "", "female": "", "wowma_catid": "51140702",
                   "wowma_catname": "レディースファッション>靴・シューズ>レインシューズ>ショートレインブーツ", "qoo_catid": "300000754",
                   "qoo_catname": "シューズ_ブーツ・ブーティー_レインブーツ",
                   "s_keyword": "レディース ロング レディースおしゃれ 軽量 レディースショート ヒール モズ 防水 防滑 ハンター クロックス  メンズ キッズ 女の子 男の子 hunter ショート 野鳥の会 おしゃれ ビジネス 29cm 30cm 28cm stample ムーンスター 22cm 22センチ ブラウン チョコレート チェルシー ローファー wfs2078rma レディースエナメル 25cm 22 19 21 18 ユニコーン 20 レインボー 21cm 20cm 24cm 17 23cm 23.5 18cm オリジナル ミディアム"},
        "IQOS": {"ctname": "オークション > アンティーク、コレクション > 雑貨 > 喫煙グッズ > その他", "y_ct": "26144", "sex": "0", "male": "",
                 "female": "", "wowma_catid": "540801", "wowma_catname": "日用品・文房具・手芸用品>喫煙具>その他喫煙具",
                 "qoo_catid": "320002473", "qoo_catname": "電子タバコ・加熱式タバコ_電子タバコ・加熱式タバコ_電子タバコ・加熱式タバコ本体",
                 "s_keyword": "iqosイルマワン カバー ケース アクセサリー シリコン 充電 車 けーす iqosイルマ本体 レッド ピンク iqos イルマ ワン 本体 プライム リング キット iqos3 duo ホルダーのみ キャップ ホルダー スティックのみ ドアカバー duoホルダー単品 充電器 iqosイルマケース キャラクター キラキラ ブランド レザー iluma one prime terea for メンソール タバコ case 互換機 日本製 人気 40本 typec 2022 ブレードレス pluscig 小型 multi マルチ"},
        "手帳型ケース": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > レザーケース", "y_ct": "2084306950",
                   "sex": "0", "male": "", "female": "", "wowma_catid": "410509",
                   "wowma_catname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>スマホケース", "qoo_catid": "320002232",
                   "qoo_catname": "スマホケース・保護フィルム_その他スマホケース_多機種対応ケース",
                   "s_keyword": "iphone13  レディース 本革 可愛い おしゃれ 女性 かわいい キャラクター クリア iphone12 人気 背面クリア pro ブランド iphone se 第2世代 第三世代 耐衝撃 第3世代 全機種対応 iphone11 対応 車載ホルダー タブレットホルダー ヘッドレスト取り付け at-88 左利き アニメ aquos 21 インコ iphone11プロ ストラップ iphone7 猫 xr アイフォン12 アート アイフォン13 薄い 手帳型 おもしろ 面白い かるい 革 カーボン かわいい主婦 車 けきたいケース"},
        "TPUケース": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他", "y_ct": "2084306951", "sex": "0",
                   "male": "", "female": "", "wowma_catid": "410509",
                   "wowma_catname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>スマホケース", "qoo_catid": "320002232",
                   "qoo_catname": "スマホケース・保護フィルム_その他スマホケース_多機種対応ケース",
                   "s_keyword": "tpuケース iphone12 iphone13 iphone se 10インチ ipad mini xperia z2 クリア フルカバー p30pro 黒 tpuケースブラック カメラ保護 ストラップ 赤 薄型 はで surphy レザー ブラック メッキ加工 バンクシー 指紋防止 iphone8 xr あいふぉん13ケース tpu カバー いphone11 いphonese 第1世代 ケース 韓国 かわいい えあぽっつ3 おしゃれ あくおすセンス4 レンズ保護 シンプルおしゃれ かんたんスマホ2 アイホン8 5 iii リング付き 耐衝撃 so-53b sog05 炭素繊維"},
        "ソフトケース": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他", "y_ct": "2084306951", "sex": "0",
                   "male": "", "female": "", "wowma_catid": "410509",
                   "wowma_catname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>スマホケース", "qoo_catid": "320002232",
                   "qoo_catname": "スマホケース・保護フィルム_その他スマホケース_多機種対応ケース",
                   "s_keyword": "収納 カービィ 24 かわいい ポケモン図鑑 大容量 スプラトゥーン スイッチ マリオ あつ森 マイクラ 純正 3ds サクラクレパス 16色 小物 キャンプ 工具 a4 カメラ ホリ ライセンス dragon quest ドラクエ 可愛い ふとまき 名入れ 透明 厚手 小物入れ カード アウトドア アコースティック 衣類 アーチェリー アコギ 色鉛筆 一眼レフ 犬 すうぃっち どうぶつの森 ずこうクレヨン ptcgw2-16 円柱 エレキギター エフェクター エアガン 大型 大きい"},
        "スリム ケース": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他", "y_ct": "2084306951",
                    "sex": "0", "male": "", "female": "", "wowma_catid": "410509",
                    "wowma_catname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>スマホケース", "qoo_catid": "320002232",
                    "qoo_catname": "スマホケース・保護フィルム_その他スマホケース_多機種対応ケース",
                    "s_keyword": "pc 収納 スリム 眼鏡ケース 可愛い ケース dtab compact d-42a うす型 おくすり手帳ケース 収納ケース 引き出し 収納ボックス 収納棚 折りたたみ 3段 布 小物 おしゃれ スリムお弁当ケース pcケース バッグ 13インチ かわいい 手巻きタバコ 衣装ケース アストロ 羽毛布団用 ベージュ シングサイズ 収納袋 不織布 薄型 コンパクト 優しく圧縮 131-26 東洋ケース スリッパラック 玄関収納 引っ掛け 壁掛け よこ28 たて77cm 賃貸 コレクションケース fケース たばこケース 手巻きたばこ サンワサプライ 1枚収納 50枚セット クリア fcd-pu50c"},
        "スマホ ケース": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他", "y_ct": "2084306951",
                    "sex": "0", "male": "", "female": "", "wowma_catid": "410509",
                    "wowma_catname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>スマホケース", "qoo_catid": "320002232",
                    "qoo_catname": "スマホケース・保護フィルム_その他スマホケース_多機種対応ケース",
                    "s_keyword": "ストラップ 首掛け ショルダー ベルト 付 穴 可愛い トポロジー iphone8 iphone8手帳型 iphone8プラス かわいい アイフェイス iphone8韓国 高級 ポーチ 型 iphone12 手帳型 透明 max リング iphone13 pro 両面 人気 カード ピクセル 6 6プロ キャラクター 6かわいい 全機種対応 so-02l se2 小物入れ ロック スタンド ショルダー掛け スマホポーチ アクオス センス6 wish センス5g アローズwe アンドロイド xperia アウトドア アローズ アイフォン10 アイフォン"},
        "スマートフォン カバー": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他", "y_ct": "2084306951",
                        "sex": "0", "male": "", "female": "", "wowma_catid": "410509",
                        "wowma_catname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>スマホケース", "qoo_catid": "320002232",
                        "qoo_catname": "スマホケース・保護フィルム_その他スマホケース_多機種対応ケース",
                        "s_keyword": "手帳 型 xperia 5 ⅲ ギャラクシー iphone se sh-01k 日本製 10 iii 折りたたみ アクオス sence4 sence6 はーうぇい スマートフォン 液晶カバー うさぎ ruuu ace so-02l エクスペリア ハード スマホ ケース カバー おもしろ 野菜 クリア スマートフォンカバー 木 se2 f-42a らくらく f-52b ストラップ 首掛け 抱き枕カバー canon selphy square qx10カバー docomoらくらく f-04k ケースgoogle pixel 3a 富士通 arrows m04"},
        "耳栓": {"ctname": "オークション > ビューティー、ヘルスケア > リラクゼーショングッズ > その他", "y_ct": "2084042540", "sex": "0", "male": "",
               "female": "", "wowma_catid": "471114", "wowma_catname": "ビューティ・コスメ>ボディケア>耳掃除", "qoo_catid": "320002472",
               "qoo_catname": "イヤホン・ヘッドホン_その他イヤホン・ヘッドホン_イヤーパッド",
               "s_keyword": "睡眠用 完全遮音 ノイズキャンセリング 安眠 シリコン 最強 日本製 防音 モルデックス 日本製医師推薦の 小さめ 痛くない いびき 睡眠 40db 射撃 聴覚過敏 工場 勉強 イヤホン 仕事 子供 コード quietide 安眠モルデックス シリコン粘土 水泳 紐付き 小さい 防水 ダイバー いびき対策 女性 工事 爆音 3m 声聞こえる メテオ スモール お試し 50 カモ カモプラグ ケース おすすめ あったかい アラーム 洗える アラームは聞こえる あたたかい"},
        "glo": {"ctname": "オークション > アンティーク、コレクション > 雑貨 > 喫煙グッズ > その他", "y_ct": "26144", "sex": "0", "male": "",
                "female": "", "wowma_catid": "540801", "wowma_catname": "日用品・文房具・手芸用品>喫煙具>その他喫煙具",
                "qoo_catid": "320002474", "qoo_catname": "電子タバコ・加熱式タバコ_電子タバコ・加熱式タバコ_アクセサリー",
                "s_keyword": "本体 スターターキット ブラック グロー"},
        "風船": {"ctname": "オークション > おもちゃ、ゲーム > 手品、パーティグッズ > パーティグッズ > その他", "y_ct": "2084059858", "sex": "0", "male": "",
               "female": "", "wowma_catid": "29090402", "wowma_catname": "おもちゃ・趣味>サバイバルゲーム>消耗品>その他消耗品",
               "qoo_catid": "300000702", "qoo_catname": "ホビー・コスプレ_パーティー・イベント用品_その他",
               "s_keyword": "バルーン 誕生日 飾り付け パーティー 結婚式 バースデーバルーン 記念日 セット マカロンバルーン 10インチ アソート風船 ラテックスバルーン パーティー お誕生日会 結婚式 二次会 飾り付け"},
        "つけまつげ": {"ctname": "オークション > ビューティー、ヘルスケア > コスメ、スキンケア > マスカラ、まつげ用品 > その他 > まつげエクステ、つけまつげ",
                  "y_ct": "2084263000", "sex": "0", "male": "", "female": "", "wowma_catid": "471003",
                  "wowma_catname": "ビューティ・コスメ>ベースメイク・メイクアップ>つけまつげ", "qoo_catid": "320001707",
                  "qoo_catname": "ポイントメイク_まつげ_つけまつげ・エクステ",
                  "s_keyword": "のり ナチュラル ドーリーウインク 部分 つけまつ毛 ダイヤモンドラッシュ マグネット dup 付け睫 でぃーあっぷ 資生堂 のりがいらない ディーアップ 強力 黒 短め 人気 ブラウン 一重 奥2重 10秒 ピンク 中央 オコジョ 14 1番 すっぴん 5 部分用 下まつげ 韓国 6ミリ 9 ケース 目尻 磁石 セレブ ドーリー 3d グラマラス ブルー アリュール 日本製 挟む 501 552 ブラック 敏感肌 のり付き リムーバー"},
        "スポーツブラ": {"ctname": "オークション > スポーツ、レジャー > スポーツウエア > 女性用 > インナーウエア > スポーツブラ", "y_ct": "2084246688", "sex": "0",
                   "male": "", "female": "", "wowma_catid": "32070606",
                   "wowma_catname": "インナー・ルームウェア>レディースインナー>ブラ>スポーツブラ", "qoo_catid": "300002902",
                   "qoo_catname": "下着・レッグウェア_ブラジャー_スポーツブラ",
                   "s_keyword": "レディース ジャー 揺れない ジュニア 大きいサイズ yvette セット 中学生 ナップザック ンド 上下セット 白 前開き タンクトップ プーマ 小学生 ショーツセット 学生 ハード ランニング ハイサポート ヨガ 160 可愛い 165 4l 3l 5l 前あき 大きいサイズ5枚組 ホックなし 上下 チャンピオン セットアップ 女子 綿 黒 部活 赤 アジャスター アンダー95 イベット 育乳 インナー 一体型 イグニオ 薄手 運動 後ろホック ウェア"},
        "サポートインナー": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > 補正下着 > その他", "y_ct": "2084053156", "sex": "0",
                     "male": "", "female": "", "wowma_catid": "32071101",
                     "wowma_catname": "インナー・ルームウェア>レディースインナー>補正下着>その他補正下着", "qoo_catid": "300000715",
                     "qoo_catname": "下着・レッグウェア_ルームウェア_インナーウェア・肌着", "s_keyword": "レディース メンズ はく腰 junior rider"},
        "ストレッチインナー": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > 補正下着 > その他", "y_ct": "2084053156",
                      "sex": "0", "male": "", "female": "", "wowma_catid": "32071101",
                      "wowma_catname": "インナー・ルームウェア>レディースインナー>補正下着>その他補正下着", "qoo_catid": "300000031",
                      "qoo_catname": "下着・レッグウェア_補正下着_補正下着・ガードル",
                      "s_keyword": "メンズ シャツ レディース パンツ グローブ ロングパンツ 夏 フィラ キッズ 長袖 黒"},
        "二の腕やせサポーター": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > 補正下着 > その他", "y_ct": "2084053156",
                       "sex": "0", "male": "", "female": "", "wowma_catid": "32071101",
                       "wowma_catname": "インナー・ルームウェア>レディースインナー>補正下着>その他補正下着", "qoo_catid": "300000031",
                       "qoo_catname": "下着・レッグウェア_補正下着_補正下着・ガードル", "s_keyword": "ストレッチインナー メンズ レディース 夏 フィラ キッズ 長袖 黒"},
        "補正下着": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > 補正下着 > その他", "y_ct": "2084053156", "sex": "0",
                 "male": "", "female": "", "wowma_catid": "320411", "wowma_catname": "インナー・ルームウェア>メンズインナー>補正下着",
                 "qoo_catid": "300000031", "qoo_catname": "下着・レッグウェア_補正下着_補正下着・ガードル",
                 "s_keyword": "レディース ブラジャー お腹 ハイウエスト ボディスーツ ボディースーツ コルセット 矯正下着 大きいサイズ キャミソール お腹引き締め ヒップアップ 姿勢矯正 ダイエット ガードル 上下セット 背中 わき肉 すっきり d75 セット マルコ ノンワイヤー 脇高 ブラジャー6xl 男性 メンズ お腹ぽっこり お腹人気 トイレ ウエストマイナス パッド 苦しくない ヒップ ベージュ ハード ボディシェイパー シームレス ボディスーツ胸開き ボディスーツセクシー 穴あき ニッパー ボディスーツメンズ トイレホール レディース穴あき セパレート レディース夏用 薄手 コルセットファスナー 矯正下着又空き"},
        "姿勢改善インナー": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > 補正下着 > その他", "y_ct": "2084053156", "sex": "0",
                     "male": "", "female": "", "wowma_catid": "32071101",
                     "wowma_catname": "インナー・ルームウェア>レディースインナー>補正下着>その他補正下着", "qoo_catid": "300000031",
                     "qoo_catname": "下着・レッグウェア_補正下着_補正下着・ガードル",
                     "s_keyword": "ウエストニッパー コルセット 女性 ブラック 補正下着 お腹　引き締め くびれ 腰サポート腹筋ベルト 背中サポート バストアップ 二重加圧 産後 インナーウェア ルームウェア 調節可能 ブラック 伸縮性 ムレにくい 背筋補正サポートインナー 前ホック付き 猫背サポーター 美姿勢シェイパー 姿勢矯正 猫背矯正 猫背改善 抗菌防臭 吸水速乾 伸縮素材 女性用 肩こり 腰痛 オレンジケア背中シャキッT ブラック 女性用キャミソール"},
        "ウエストウォーマー": {"ctname": "オークション > ビューティー、ヘルスケア > 健康用品、健康器具 > サポーター > 腰用", "y_ct": "2084216485", "sex": "0",
                      "male": "", "female": "", "wowma_catid": "34051903",
                      "wowma_catname": "キッズベビー・マタニティ>ベビー>衛生・ヘルスケア>その他衛生・ヘルスケア", "qoo_catid": "300002906",
                      "qoo_catname": "下着・レッグウェア_補正下着_ウエストニッパー",
                      "s_keyword": "メンズ レディース 電熱 男性用 スポーツ バイク ポケット 着る岩盤浴 une nana cool バードジャカード rs タイチ e-heat スーパーメリノウール exp. ジオライン l.w."},
        "腹巻き": {"ctname": "オークション > ビューティー、ヘルスケア > 健康用品、健康器具 > サポーター > 腰用", "y_ct": "2084216485", "sex": "0",
                "male": "", "female": "", "wowma_catid": "320106", "wowma_catname": "インナー・ルームウェア>その他インナー・ルームウェア>腹巻",
                "qoo_catid": "300002906", "qoo_catname": "下着・レッグウェア_補正下着_ウエストニッパー",
                "s_keyword": "メンズ 大きいサイズ 冷え防止 夏用 厚手 シルク 暖かい 4l  加圧 レディース 薄手 かわいい 温かい ロング ポケット付き 妊婦  パンツ 綿 大きい マタニティ 五分たけ 夏 可愛い セット 3l 5l 6l 大きいサイズ薄手 ポケット あたたかい 就寝 薄い シルク100 子供 日本製 妊婦用 あたたか 妊婦4l キッズ 赤 赤ちゃん アニメ アクリル 犬用 犬柄 犬印 医療用 犬 ウール"},
        "コルセット": {"ctname": "オークション > ビューティー、ヘルスケア > 健康用品、健康器具 > サポーター > 腰用", "y_ct": "2084216485", "sex": "0",
                  "male": "", "female": "", "wowma_catid": "320106", "wowma_catname": "インナー・ルームウェア>その他インナー・ルームウェア>腹巻",
                  "qoo_catid": "300002906", "qoo_catname": "下着・レッグウェア_補正下着_ウエストニッパー",
                  "s_keyword": "ダイエット くびれ 腰痛 男性用 首 女性 肋骨 大きいサイズ 人気 メンズ レディース 紐 男性 編み上げ ベージュ クビレ 二重  医療用 スポーツ 大きい 薄型 メッシュ 中山式 白 ストレートネック 寝る時 就寝用 夏 黒 大きめ xs 薄い 日本製 s 骨折 サポーター 骨盤 男性用大きいサイズ 姿勢 通気性 マックスベルト 加圧 6l 4l 5l 肋骨締め アンダーバスト 女性用 赤"},
        "耳かき": {"ctname": "オークション > ビューティー、ヘルスケア > 救急、衛生用品 > 耳掃除用品", "y_ct": "2084227183", "sex": "0", "male": "",
                "female": "", "wowma_catid": "471114", "wowma_catname": "ビューティ・コスメ>ボディケア>耳掃除", "qoo_catid": "320000537",
                "qoo_catname": "日用品雑貨_衛生用品_身だしなみ用品",
                "s_keyword": "カメラ 日本製 カメラ付き ピンセット bebird iphone 有線 イヤースプーン スコープ 替え モニター付き bluetooth 500万画素 ライト ライト付き 子供 子ども usb 充電 シリコン 竹 竹製 細い 極細 匠の技 ケース 小さい しなる 医療用 チタン 最高級 すすたけ 最高級天然煤竹 3.0  ステンレス 吸引 人気 android スパイラル スプーン 短い 一本 薄い 薄型 長い 赤ちゃん あめ耳 安全 アタッチメント アイフォン"},
        "トレーニング チューブ": {"ctname": "オークション > スポーツ、レジャー > スポーツ別 > エクササイズ用品 > ギア > エキスパンダー、チューブ", "y_ct": "2084006835",
                        "sex": "0", "male": "", "female": "", "wowma_catid": "34060603",
                        "wowma_catname": "キッズベビー・マタニティ>マタニティ・ママ>マタニティビクス・ヨガ>スポーツウエア", "qoo_catid": "320000289",
                        "qoo_catname": "スポーツ_ゴルフ用品_トレーニング用具",
                        "s_keyword": "おすすめ ハード 懸垂 最強 プロマーク ニシ ソフト 本 ハンドル woket 足指 トレーニングチューブ 一本 イオーノ 腕 ウルトラハード 腕立て エクササイズバンド エクストラ 円 肩甲骨 肩 カバー かわいい 空手 替え カラビナ 壁 可愛い 黄色 強度 強力 金属製 競泳 黒 高強度 子供 高負荷 固定 国産 サッカー シェイプアップ ストレッチ ダイエット 運動 尻 白 初心者 シリコン 筋トレ"},
        "いびきストッパー": {"ctname": "オークション > ビューティー、ヘルスケア > 健康用品、健康器具 > その他", "y_ct": "2084042545", "sex": "0", "male": "",
                     "female": "", "wowma_catid": "34051903", "wowma_catname": "キッズベビー・マタニティ>ベビー>衛生・ヘルスケア>その他衛生・ヘルスケア",
                     "qoo_catid": "320001859", "qoo_catname": "ダイエット・矯正_シェイプアップ・ダイエットグッズ_エクササイズグッズ",
                     "s_keyword": "スノアサークル emsパッド"},
        "手首サポーター": {"ctname": "オークション > ビューティー、ヘルスケア > 健康用品、健康器具 > サポーター > 手首用", "y_ct": "2084216482", "sex": "0",
                    "male": "", "female": "", "wowma_catid": "34051903",
                    "wowma_catname": "キッズベビー・マタニティ>ベビー>衛生・ヘルスケア>その他衛生・ヘルスケア", "qoo_catid": "320001859",
                    "qoo_catname": "ダイエット・矯正_シェイプアップ・ダイエットグッズ_エクササイズグッズ",
                    "s_keyword": "女性 腱鞘炎 防水 育児 女性用 ピンク 固定 女性リュウマチ ベージュ メンズ メンズ 左手用 freetoo スポーツ用 医療用 親指の固定 薄手 子供用 手首の固定 手根管症候群 保護 左 右 pykes peak 手首 サポーター 暖かい 暖め 赤 汗 洗える 赤ちゃん アルミ 目立たない 骨折 医療 骨折後 痛み 薄型 薄い 腕立て ウエイト 運動 保温 え けんしょうえん オシャレ 可愛い 隠す 勝野式"},
        "手首 サポーター": {"ctname": "オークション > ビューティー、ヘルスケア > 健康用品、健康器具 > サポーター > 手首用", "y_ct": "2084216482", "sex": "0",
                     "male": "", "female": "", "wowma_catid": "34051903",
                     "wowma_catname": "キッズベビー・マタニティ>ベビー>衛生・ヘルスケア>その他衛生・ヘルスケア", "qoo_catid": "320001859",
                     "qoo_catname": "ダイエット・矯正_シェイプアップ・ダイエットグッズ_エクササイズグッズ",
                     "s_keyword": "腱鞘炎 固定 女性 筋トレ 女性用 医療用  薄手 左手 左 日本製 女性右手 右手 テニス 野球 ゴルフ 子供 スポーツケア用品 2枚セット wrist supporter ベージュ 2枚 白 筋トレキング 治し方 手首の痛み 手根管症候群 tfcc損傷 tfcc 固定しない sサイズ 蒸れない 暖かい 目立たない 骨折 骨折後 加圧 ふつう 小さめ 大きめ 保温  暖め 赤 汗 洗える 赤ちゃん アルミ 育児"},
        "手首　サポーター": {"ctname": "オークション > ビューティー、ヘルスケア > 健康用品、健康器具 > サポーター > 手首用", "y_ct": "2084216482", "sex": "0",
                     "male": "", "female": "", "wowma_catid": "34051903",
                     "wowma_catname": "キッズベビー・マタニティ>ベビー>衛生・ヘルスケア>その他衛生・ヘルスケア", "qoo_catid": "320001859",
                     "qoo_catname": "ダイエット・矯正_シェイプアップ・ダイエットグッズ_エクササイズグッズ",
                     "s_keyword": "腱鞘炎 固定 女性 筋トレ 女性用 医療用  薄手 左手 左 日本製 女性右手 右手 テニス 野球 ゴルフ 子供 スポーツケア用品 2枚セット wrist supporter ベージュ 2枚 白 筋トレキング 治し方 手首の痛み 手根管症候群 tfcc損傷 tfcc 固定しない sサイズ 蒸れない 暖かい 目立たない 骨折 骨折後 加圧 ふつう 小さめ 大きめ 保温  暖め 赤 汗 洗える 赤ちゃん アルミ 育児"},
        "スマホとタブレットのスタンド": {"ctname": "オークション > コンピュータ > 周辺機器 > その他", "y_ct": "2084048551", "sex": "0", "male": "",
                           "female": "", "wowma_catid": "410903",
                           "wowma_catname": "スマホ・タブレット・モバイル通信>バッテリー・充電器>スマホ・タブレット用充電器", "qoo_catid": "320002278",
                           "qoo_catname": "スマートフォン・タブレットPC_スマートフォン用アクセサリー_スマートフォン用スタンド",
                           "s_keyword": "手首 サポーター 腱鞘炎 固定 女性 筋トレ 女性用 医療用  薄手 左手 左 日本製 女性右手 右手 テニス 野球 ゴルフ 子供 スポーツケア用品 2枚セット wrist supporter ベージュ 2枚 白 筋トレキング 治し方 手首の痛み 手根管症候群 tfcc損傷 tfcc 固定しない sサイズ 蒸れない 暖かい 目立たない 骨折 骨折後 加圧 ふつう 小さめ 大きめ 保温  暖め 赤 汗 洗える 赤ちゃん アルミ"},
        "ヨガパンツ": {"ctname": "オークション > スポーツ、レジャー > スポーツウエア > 女性用 > ボトムス > ロング > その他", "y_ct": "2084057034", "sex": "0",
                  "male": "", "female": "", "wowma_catid": "34060603",
                  "wowma_catname": "キッズベビー・マタニティ>マタニティ・ママ>マタニティビクス・ヨガ>スポーツウエア", "qoo_catid": "300000221",
                  "qoo_catname": "スポーツ_フィットネス・ヨガ_フィットネス・ヨガパンツ",
                  "s_keyword": "レディース ゆったり メンズ 人気 レギンス サルエル フレア ショート ハイウエスト 7分丈 大きいサイズ 柄せっと ハーフ 速乾 ライン ストレッチ 柄 グリーン ポケット 花柄 水陸両用 uvカット xl とろみ お腹抑え 暖かい アシュレイ 赤 麻 穴開き 厚手 編み 一体型 薄手 薄い エスニック おしゃれ お尻 大きめ 3l オレンジ おおきいサイズ オシャレ かわいい 可愛い 重ね着風 カラフル キッズ 着圧 黒"},
        "ストレッチパンツ": {"ctname": "オークション > スポーツ、レジャー > スポーツウエア > 女性用 > ボトムス > ロング > その他", "y_ct": "2084057034",
                     "sex": "0", "male": "", "female": "", "wowma_catid": "402309",
                     "wowma_catname": "スポーツ・アウトドア>スポーツウェア>ウェア", "qoo_catid": "300000221",
                     "qoo_catname": "スポーツ_フィットネス・ヨガ_フィットネス・ヨガパンツ",
                     "s_keyword": "メンズ 大きいサイズ   ゴルフ ビジネス デニム スキニー 作業着 白 黒 レディース キッズ 春 ゆったり 仕事 ゴム ジャージ素材 130 160 秋冬  裏起毛 レディース春夏 赤 アウトドア 赤ちゃん アンクル 厚手 薄手 運動 柄 男の子 100 おしゃれ 女の子 看護 介護 カーゴ カーゴメンズ  クライミング 子供 紺 光沢 作業 作業用 下着メンズ  下着 スラックス"},
        "ズボン": {"ctname": "オークション > ファッション > レディースファッション > パンツ、スラックス > Mサイズ", "y_ct": "2084224590", "sex": "1",
                "male": "2084224619", "female": "2084224590", "wowma_catid": "511012",
                "wowma_catname": "レディースファッション>パンツ>スラックス", "qoo_catid": "300000034",
                "qoo_catname": "レディースファッション_パンツ_ロングパンツ",
                "s_keyword": "ハンガー ハンガーラック 省スペース 洗濯 クリップ すべらない 木製 跡がつかない ステンレス 白  メンズ レディース プレッサー 用ハンガー 大きいサイズ 収納 下 ゆったり おしゃれ 春 夏 ストレッチ 黒 夏用 韓国 ゴム デニム ストレート 人気 東芝 ツインバード 縦置き コルビー 横 アイリス ガラス 用ハンガーラック 複数がけ プラスチック 干す ピンク ビジネス 5l 安い 7分 裾上げ スポーツ クローゼット 仕切り 吊り下げ"},
        "バルーン": {"ctname": "オークション > おもちゃ、ゲーム > 手品、パーティグッズ > パーティグッズ > その他", "y_ct": "2084059858", "sex": "0",
                 "male": "", "female": "", "wowma_catid": "290801", "wowma_catname": "おもちゃ・趣味>コレクション>その他コレクション",
                 "qoo_catid": "300000702", "qoo_catname": "ホビー・コスプレ_パーティー・イベント用品_その他",
                 "s_keyword": "誕生日 男の子 数字 女の子 紫 青 ヘリウムガス入り ユニコーン 赤  大きい 小さい 白 60cm 黒 40cm ゴールド ピンク スタンド 160cm ロング 130cm 風船セット スタンドセット 高さ調整 2セット 長い ヘリウムガス 用 安い ゴム アート 風船 割れにくい ポンプ 空気入れ セット メタリック 本 ブーケ 卒業式 ミニ 花束 卒業 発表会 卒園 キャラクター フラワー フラワーギフト 材料 フラワーブーケ"},
        "メイクブラシ": {"ctname": "オークション > ビューティー、ヘルスケア > コスメ、スキンケア > メイク道具、化粧小物 > ブラシ、チップ、コーム > メイクブラシセット",
                   "y_ct": "2084228681", "sex": "0", "male": "", "female": "", "wowma_catid": "471212",
                   "wowma_catname": "ビューティ・コスメ>メイク道具・ケアグッズ>ブラシ・チップ", "qoo_catid": "320001725",
                   "qoo_catname": "メイク小物_メイク道具_メイクブラシ",
                   "s_keyword": "セット 人気 ケース クリーナー スタンド マリリン  収納 熊野筆 かわいい  くまのふで  安い ケース付き 日本製 可愛い ケースつき ピンク 人気熊野 天然毛 蓋付き 持ち運び 小さい コンパクト 自立 腰巻 パール プロ 電動 スプレー 速乾 クリーナーマット  スポンジ mac シリコン ドライ 大理石 アクリル 乾燥 大容量 蓋 単品 フェイスブラシ 11本 マミ様 ふた付き ポーチ 収納ボックス"},
        "化粧道具": {"ctname": "オークション > ビューティー、ヘルスケア > コスメ、スキンケア > メイク道具、化粧小物 > その他", "y_ct": "2084007465", "sex": "0",
                 "male": "", "female": "", "wowma_catid": "471202",
                 "wowma_catname": "ビューティ・コスメ>メイク道具・ケアグッズ>その他メイク道具・ケアグッズ", "qoo_catid": "320001725",
                 "qoo_catname": "メイク小物_メイク道具_メイクブラシ",
                 "s_keyword": "収納 入れ セット 洗剤 収納ボックス 入れケース メンズ 収納棚 おもちゃ 蓋付き ピンク 木製 入れ鏡付き 持ち運び 大人 ブランド 洗浄 カート 子供 一式 オシャレ 大人気 リップ パレット 球体 ケース 子供用 メイク人気ブラシ 使い捨てリップブラシ 任意化粧品に適用され ブラック 黒 多機能 メイクブラシセット 化粧眉ブラシ 使い捨て 多機能化粧ブラシ 化粧 眉ブラシ 立て スポンジパフ 美容卵 パウダーパフ 粉色 ままごとお 日本の美術 シャネルの 子供のお 手作り化粧品 道具"},
        "コンシーラー": {"ctname": "オークション > ビューティー、ヘルスケア > コスメ、スキンケア > コンシーラー", "y_ct": "2084005315", "sex": "0", "male": "",
                   "female": "", "wowma_catid": "471010", "wowma_catname": "ビューティ・コスメ>ベースメイク・メイクアップ>コンシーラー",
                   "qoo_catid": "320001655", "qoo_catname": "ベースメイク_コンシーラー_スティックコンシーラー",
                   "s_keyword": "しみカバー 人気 肝斑 韓国 メンズ スティック  プチプラ オレンジ 明日配送 ざせむ ザセム 1.5  グリーンベージュ 01 1.25 0.5 1.75 dior 0n 1n 1.5n 2n 1w 2w 3n ブライトナー グリーン ピーチベージュ 青髭 ニキビ クマ 色白 黒 日焼け くま シミ ディオール on ブラシ ロージーローザ 平筆 フラット 携帯用 細い 美粧堂 ミニ くま消し 50代 赤み"},
        "ベスト": {"ctname": "オークション > ファッション > メンズファッション > ベスト > Mサイズ", "y_ct": "2084064193", "sex": "0",
                "male": "2084064193", "female": "", "wowma_catid": "500518",
                "wowma_catname": "メンズファッション>ジャケット・アウター>ダウンベスト", "qoo_catid": "300002283",
                "qoo_catname": "メンズファッション_アウター_ベスト",
                "s_keyword": "メンズ レディース セラー  アルバム 女性用 春 コ  本 ランキング カー 春夏 夏用 大きいサイズ スーツ ニット アウトドアブランド 夏 vネック ロング 学生 自己啓発本 脚立 4段 軽量 安全 セラー1位 洋書 セラー商品 セラーコード アルバム2022 アルバム2021 収録曲 中古 アルバム最新 cd マリーゴールド mp3 アルバムハート セラー 媚薬 ローター リモコン セラー福袋 静音 セラー ローション 春綿 麻"},
        "トレーナー": {"ctname": "オークション > ファッション > メンズファッション > トレーナー > Mサイズ", "y_ct": "2084057461", "sex": "1",
                  "male": "2084057461", "female": "2084064261", "wowma_catid": "500712",
                  "wowma_catname": "メンズファッション>トップス>トレーナー・スウェット", "qoo_catid": "300002279",
                  "qoo_catname": "メンズファッション_アウター_パーカー・トレーナー",
                  "s_keyword": "メンズ 大きいサイズ 春 ブランド おしゃれ  パタゴニア チャンピオン レディース ゆったり バタフライナイフ パラグラフ スポーツ 韓国 キッズ リバースウィーブ 古着 4l 裏起毛 グリーン ベビー 丈長め 春夏 春秋 春人気 無地 グレー 薄手 5l 上下 厚手 緑  50代 安い ゆったりパンツ 白 かわいい sランク かっこいい奴 オクタン 子供用 黒 g10 かっこいい ベンチメイド ゆうた エアポッツケース やまと 青 紫"},
        "サルエルパンツ": {"ctname": "オークション > ファッション > メンズファッション > サルエルパンツ", "y_ct": "2084246078", "sex": "1",
                    "male": "2084246078", "female": "2084246107", "wowma_catid": "511007",
                    "wowma_catname": "レディースファッション>パンツ>サルエルパンツ", "qoo_catid": "320001450",
                    "qoo_catname": "レディースファッション_パンツ_サルエルパンツ",
                    "s_keyword": "メンズ レディース 大きいサイズ 夏 春 デニム キッズ 無地 冬 夏用 スウェット 黒 アシンメトリー ヨガ ダンス きれいめ 七分丈 大きいサイズ5l 大きいサイズデニム 黄色 グレー 春夏秋 ゆったり 春夏 ufnisak ストレッチ 男の子 150 100 白 130 キッズ140 アジアン 麻 厚手 赤 青 アラジンパンツ アジア インド綿 衣装 裏起毛 ウエストゴム ウエスト120 上 薄手 エスニック 柄 おおきいサイズ オーバーオール"},
        "ジョガーパンツ": {"ctname": "オークション > ファッション > メンズファッション > パンツ、スラックス > Lサイズ", "y_ct": "2084224620", "sex": "1",
                    "male": "2084224620", "female": "2084224590", "wowma_catid": "500805",
                    "wowma_catname": "メンズファッション>パンツ・ボトムス>ジョガーパンツ", "qoo_catid": "300002763",
                    "qoo_catname": "レディースファッション_パンツ_その他",
                    "s_keyword": "メンズ 夏 デニム トレーニング 大きいサイズ  ゴルフ 迷彩 レディース テックフリース 作業着 スポーツ きれいめ 速乾 スリット コットン 夏用 黒 大きい デニム細め ストレッチ スウェット  s 赤 冬 デニム生地 作業着上下 アウトドア インディゴ 犬印 薄手 裏起毛 ウインドブレーカー ウィンドブレーカー エンボス 柄 エスニック おしゃれ オシャレレディース オリーブ オレンジ 大きめ カーゴ カーキ 韓国 カモフラ カーゴパンツ カジュアル カモフラージュ カモ"},
        "スエットパンツ": {"ctname": "オークション > ファッション > メンズファッション > パンツ、スラックス > Lサイズ", "y_ct": "2084224620", "sex": "1",
                    "male": "2084224620", "female": "2084224590", "wowma_catid": "500807",
                    "wowma_catname": "メンズファッション>パンツ・ボトムス>スウェットパンツ", "qoo_catid": "300002763",
                    "qoo_catname": "レディースファッション_パンツ_その他",
                    "s_keyword": "メンズ 大きいサイズ ブランド 薄手 綿100 裏起毛 チャンピオン 春夏 厚手  レディース レディース ゆったり 綿 キャラクター 大きいサイズ八分丈 大きいサイズ白 キッズ usa 冬 レディース 安い 赤 アウトドア メンズ 薄手レディース 裏毛 大きめ おしゃれ 大きい カーゴ カモフラ かわいい 韓国 男の子 130 140 起毛 160 黒 クラッシック ひちぶたけ 子供 高齢者 サルエル 白 ショーツ ショート シニア ストレート スリム"},
        "マウンテンパーカー": {"ctname": "オークション > ファッション > メンズファッション > ジャケット、上着 > ジャンパー、ブルゾン > ジャンパー、ブルゾン一般 > Mサイズ",
                      "y_ct": "2084050108", "sex": "1", "male": "2084050108", "female": "2084057472",
                      "wowma_catid": "500533", "wowma_catname": "メンズファッション>ジャケット・アウター>マウンテンパーカー",
                      "qoo_catid": "300003075", "qoo_catname": "レディースファッション_トップス_パーカー",
                      "s_keyword": "レディース 春 大きいサイズ クラシカルエルフ  撥水 防水 ロング メンズ ヘリーハンセン キッズ パタゴニア 薄手 春夏 ショート丈 ll ゆったり 防寒 フード付き ライトジャケット ミリタリージャケット 春秋 春物 ミリタリー ビジネス カジュアル xxl 迷彩 カモ柄 ベビー 女の子 男の子 140 160 150 フードなし 韓国 メンズレディース アウトドア アーバンリサーチ 赤 アイボリー アウトドアブランド 青 インナー付き イーザッカ イエナ 裏地付き 裏起毛 裏メッシュ ウィメンズ"},
        "ジャンパー": {"ctname": "オークション > ファッション > メンズファッション > ジャケット、上着 > ジャンパー、ブルゾン > ジャンパー、ブルゾン一般 > Mサイズ",
                  "y_ct": "2084050108", "sex": "1", "male": "2084050108", "female": "2084057481",
                  "wowma_catid": "510404", "wowma_catname": "レディースファッション>オールインワン・サロペット>ジャンパースカート",
                  "qoo_catid": "300000041", "qoo_catname": "レディースファッション_アウター_ジャンパー・ブルゾン",
                  "s_keyword": "メンズ 春 薄手  春秋 大きいサイズ 冬 防寒 春物 メンズ春夏 夏 スカート レディース ホック 線 ワイヤー 学生服 ロング キッズ ロリータ デニム ミニ 黒 春夏 スポーツ 防水 ブランド カジュアル 打ち具 15mm 大 7060 足長 12mm 小 10mm セット オスメス メスメス ワニ口クリップ ヒューズ付き オスオス 基盤 ヒューズ コネクタ ストリッパー ブレッドボード 10cm 50cm 単線 1m"},
        "ブルゾン": {"ctname": "オークション > ファッション > メンズファッション > ジャケット、上着 > ジャンパー、ブルゾン > ジャンパー、ブルゾン一般 > Mサイズ",
                 "y_ct": "2084050108", "sex": "1", "male": "2084050108", "female": "2084057481",
                 "wowma_catid": "510324", "wowma_catname": "レディースファッション>アウター>ブルゾン", "qoo_catid": "300000041",
                 "qoo_catname": "レディースファッション_アウター_ジャンパー・ブルゾン",
                 "s_keyword": "メンズ 春 レディース 春秋 ジャケット 大きいサイズ 春夏 カジュアル ビジネス 春物 柄 4xl 夏 ゴルフ 冬 ブランド 薄手 白 オーバーサイズ 撥水 パープル ma-1 メンズ春物 キッズ 130 厚手 120 赤 アウトドア 青 秋冬 アーバンリサーチ アウター 赤ちゃん イベント インナー 裏起毛 裏地付き ウインドブレーカー ウィンドブレーカー ウィンド ブレーカー 襟 襟付き 女の子 男の子 オレンジ 大きい 110 韓国"},
        "手袋": {"ctname": "オークション > ファッション > ファッション小物 > 手袋 > 女性用 > その他", "y_ct": "2084214886", "sex": "1",
               "male": "2084214890", "female": "2084214886", "wowma_catid": "341018",
               "wowma_catname": "キッズベビー・マタニティ>子供用ファッション小物・雑貨>手袋", "qoo_catid": "300003092",
               "qoo_catname": "バッグ・雑貨_手袋_ニット手袋",
               "s_keyword": "使い捨て 作業 レディース ニトリル 防水 メンズ 白 黒 綿 ビニール 食品 s 食品衛生法適合 ポリエチレン l ss 作業用 薄手 10双セット 滑り止め sサイズ 革 防寒 静電気 夏用 暖かい スマホ対応 uvカット 指なし 夏 冬 m ll 1000枚 自転車 バイク スマホ キッズ スポーツ 薄い コスプレ 礼装 フォーマル レース ロング レザー 綿100 手荒れ 子供 日本製"},
        "キーケース": {"ctname": "オークション > ファッション > ファッション小物 > キーケース", "y_ct": "2084012476", "sex": "0", "male": "",
                  "female": "", "wowma_catid": "450406", "wowma_catname": "バッグ・財布・ファッション小物>ファッション小物>キーケース",
                  "qoo_catid": "320001111", "qoo_catname": "メンズバッグ・シューズ・小物_財布_キーケース",
                  "s_keyword": "メンズ レディース スマートキー対応 ランドセル ブランド bmw 人気 小銭入れ付き 革 可愛い スマートキー 安い 名入れ グレー 正規品 緑 ヌメ ピンク 財布 ダブル 小銭 オシャレ コンパクト 本革 車 スマート レザー カード ykk ファスナー 赤兎馬工房 かわいい 男の子 リール 女の子 子供 小学生 マジックテープ 男 アウトレット 大きめ ヴォクシー シリコン ハリアー アクア ルーミー アルファード カーボン セレナ ノート"},
        "ワンピース": {"ctname": "オークション > ファッション > レディースファッション > ワンピース > ミニスカート > Mサイズ", "y_ct": "2084224575", "sex": "0",
                  "male": "", "female": "", "wowma_catid": "510708", "wowma_catname": "レディースファッション>スーツ>ワンピーススーツ",
                  "qoo_catid": "300002248", "qoo_catname": "レディースファッション_スーツ_ワンピーススーツ",
                  "s_keyword": "102 102巻 コミック 予約 デジタル キンドル カラー 電子  レディース 全巻 フィギュア 春 カード きれいめ マガジン 大きいサイズ 夏 ロング 韓国 春夏 中古 全巻セット 激安 新品 まとめ買い 電子書籍 pop ルフィ ヤマト ナミ ゾロ フィギュアーツ シャンクス カジュアル かわいい 40代 カードゲーム romance dawn カードスリーブ スリーブ カードダス box スタートデッキ 膝丈 入学式 マキシ丈 大きいサイズミニ 花柄 マガジン14"},
        "ワンピ": {"ctname": "オークション > ファッション > レディースファッション > ワンピース > ミニスカート > Mサイズ", "y_ct": "2084224575", "sex": "0",
                "male": "", "female": "", "wowma_catid": "510708", "wowma_catname": "レディースファッション>スーツ>ワンピーススーツ",
                "qoo_catid": "300002250", "qoo_catname": "レディースファッション_ワンピース・ドレス_シャツワンピ",
                "s_keyword": "ース 102 102巻 コミック 予約 デジタル キンドル カラー レディース 全巻 フィギュア 春 カード きれいめ ースマガジン 大きいサイズ 夏 ロング 韓国 春夏 中古 全巻セット 激安 新品 まとめ買い 電子書籍 pop ルフィ ヤマト ナミ ゾロ フィギュアーツ シャンクス カジュアル かわいい 40代 カードゲーム romance dawn カードスリーブ スリーブ カードダス box スタートデッキ 膝丈 入学式 マキシ丈 大きいサイズミニ 花柄 ースマガジン14 ースマガジン全巻"},
        "サマードレス": {"ctname": "オークション > ファッション > レディースファッション > ワンピース > ミニスカート > Mサイズ", "y_ct": "2084224575", "sex": "0",
                   "male": "", "female": "", "wowma_catid": "511101", "wowma_catname": "レディースファッション>ワンピース>その他ワンピース",
                   "qoo_catid": "300000001", "qoo_catname": "レディースファッション_ワンピース・ドレス_ドレス",
                   "s_keyword": "ワンピース リゾート 大きいサイズ ロング ミニ ベビー 袖あり レース 部屋着 オフショル 青 結婚式 花柄 蒼 sp チノ 花ざかり ver ココア キッズ 子ども 白 の女たち 女性の ピンク 100"},
        "ネックレス": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ネックレス、ペンダント > その他", "y_ct": "2084005400", "sex": "0",
                  "male": "", "female": "", "wowma_catid": "3009", "wowma_catname": "アクセサリー・ジュエリー>ネックレス",
                  "qoo_catid": "300002342", "qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_ネックレス",
                  "s_keyword": "メンズ レディース 人気 チェーン コラントッテ 人気ブランド メンズ人気 シルバー ごろーず ゴールド メンズ人気ブランド シンプル 十字架 ブランド 安い 金属アレルギー対応 dior ステンレス 18金 ピンクゴールド プラチナ チェーンのみ 指輪 らくわ x100 メタックス ワイヤー 羽生結弦 55cm x50 チタン スマイル オープンハート ハート ダイヤモンド ピアス セット スワン ダンシング 金属アレルギー colantotte alt クレスト luce α tao matte スリム 収納 アジャスター"},
        "ペンダント": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ネックレス、ペンダント > その他", "y_ct": "2084005400", "sex": "0",
                  "male": "", "female": "", "wowma_catid": "3017", "wowma_catname": "アクセサリー・ジュエリー>ペンダント",
                  "qoo_catid": "300002368", "qoo_catname": "メンズバッグ・シューズ・小物_メンズ小物_ペンダント・チョーカー",
                  "s_keyword": "ライト ダクトレール ガラス 北欧 リモコン付き led 和風 アンティーク コンセント オーデリック  cmc 遺骨 トップ ダクトレール用 黒 3個セット ブラック ソケット 白 3灯 ガラスシェード e26 ガラス小型 バブル 青 北欧白 リモコン 6畳 木 おしゃれ 花 4灯 cmc総合研究所 電磁波 1000 電磁波バイオ c eタイプ チタン d e型 8畳 タキズミ 和室 12畳 寝室 完全防水 メンズ 刻印 犬"},
        "ブレスレット": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ブレスレット、バングル > バングル > その他", "y_ct": "2084019059",
                   "sex": "0", "male": "", "female": "", "wowma_catid": "3014", "wowma_catname": "アクセサリー・ジュエリー>ブレスレット",
                   "qoo_catid": "320001452", "qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_ブレスレット",
                   "s_keyword": "メンズ レディース 静電気除去 人気 コラントッテ ペア ゴム ブランド シルバー 革 レザー ゴールド 金 安い 18金 ピンクゴールド 天然石 日本製 最強 シリコン おしゃれ コランコラン 可愛い 人気ブランド アレルギー 安いk18 さくら 正規品 1600ゼウス ループ カーボン 数珠 プレミアムシルバー クレスト エクストリーム メタックス チタン 15 メンズチタン エルサ ペレッティ ミニ オープン ハート プラチナ アウトレット リンク ムーンストーン カップル つけっぱなし"},
        "マフラー": {"ctname": "オークション > ファッション > ファッション小物 > マフラー > 女性用 > マフラー一般", "y_ct": "2084006464", "sex": "1",
                 "male": "2084006472", "female": "2084006464", "wowma_catid": "450420",
                 "wowma_catname": "バッグ・財布・ファッション小物>ファッション小物>マフラー", "qoo_catid": "300000763",
                 "qoo_catname": "バッグ・雑貨_ストール・マフラー_マフラー",
                 "s_keyword": "カッター 2本出し 軽自動車 下向き ハイエース カーボン 大口径 ヤリスクロス タフト ストレート  タオル スーパーカブ レブル250 モンキー カブ ハンガー バンド スポーツ キャラクター 今治 かわいい 無地 額縁 額 ガスケット ヨシムラ fi c50 ステー ja44 ショート 50 キタコ モリワキ ディアブロ オーバーレーシング gem sp忠男 ガード ウイルズウィン z50j 静音 中古 カラー 静か インジェクション 純正 モナカ aa01 110"},
        "ストール": {"ctname": "オークション > ファッション > ファッション小物 > ストール > ストール一般", "y_ct": "2084006466", "sex": "1",
                 "male": "2084006472", "female": "2084006466", "wowma_catid": "450410",
                 "wowma_catname": "バッグ・財布・ファッション小物>ファッション小物>ストール・ショール", "qoo_catid": "300000764",
                 "qoo_catname": "バッグ・雑貨_ストール・マフラー_ストール",
                 "s_keyword": "レディース 春物 メンズ 大判 春 クリップ 結婚式 シルク ブランド 綿 薄手 コットン 可愛い 日本製 カシミヤ 春夏 今治 夏 リネン 厚手 黒 花柄 授乳ケープ ポンチョ ボタン uvカット 柄 春夏用 パール パーツ チェーン シンプル ゴールド レザー 金具 白 冬 グレー ベージュ シルバー 用 赤 麻 青 編み物 本 洗える 麻100 今治タオル インド綿"},
        "ギフトシール": {"ctname": "オークション > 事務、店舗用品 > 文房具 > その他", "y_ct": "2084042489", "sex": "0", "male": "", "female": "",
                   "wowma_catid": "540303", "wowma_catname": "日用品・文房具・手芸用品>タオル>ギフトセット", "qoo_catid": "300000488",
                   "qoo_catname": "日用品雑貨_生活雑貨_ギフト・イベントグッズ",
                   "s_keyword": "リボン ありがとう お世話になりました for you リボン付き ゴールド フォーユー 父の日 母の日 リボン型 小 ピンク ありがとうございます ロール おめでとう 金 印刷 犬 エレガント おしゃれ お礼 お元気で おせわになりました お祝い 四角 お誕生日おめでとう 感謝 かわいい 書ける くま ねこ さくら サンキュー 桜 シルバー よろしくお願いします 卒業おめでとう 卒業 誕生日 長方形 小さめ 手書き 透明 名前 ナチュラル 名入れ ラッピング 封印シール 猫"},
        "指輪": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > 指輪 > その他", "y_ct": "2084005435", "sex": "0", "male": "",
               "female": "", "wowma_catid": "3020", "wowma_catname": "アクセサリー・ジュエリー>指輪・リング", "qoo_catid": "320001121",
               "qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_指輪",
               "s_keyword": "メンズ レディース サイズ 計測 ケース ペアリング 物語 サイズ調整 の選んだ婚約者 9 おしゃれ フリーサイズ ゴールド シルバー ステンレス シルバー925 セット 黒 ブランド 人気 安い オシャレ ピンクゴールド 大きいサイズ プラチナ レディース18金 日本製 棒 正確 シリコン アメリカ us 日本規格 海外規格 携帯用 プロポーズ 持ち運び 2個用 ミニ 木製 キーホルダー 刻印 カップル 本 文庫 追補編 トールキン 旅の仲間 地図 全巻"},
        "スタイラスペン": {"ctname": "オークション > 事務、店舗用品 > 文房具 > その他", "y_ct": "2084042489", "sex": "0", "male": "",
                    "female": "", "wowma_catid": "460505", "wowma_catname": "パソコン・PC周辺機器>キーボード・マウス・入力機器>ゲームパッド",
                    "qoo_catid": "320002297", "qoo_catname": "スマートフォン・タブレットPC_タブレットPC用アクセサリー_タッチペン・スタイラス",
                    "s_keyword": "ipad jamjake kingone ペン android iphone 筆圧感知 socll ケース キングワン 第9世代 パームリジェクション 第5世代 ipad対応 mini4 air2対応 替え芯 カバー 2022 ペン先 交換 極細 高感度 超高感度 タッチペンipad ペン2020 軽量 傾き感知 ペン124 イラスト bluetooth タブレット 磁気吸着 iphone対応 充電式 iphone13 13 iphone12 windows 傾き検知 筆圧感知アンドロイド サイドボタン 第一世代 mini5 mini アンドロイド アンドロイド対応 アイフォン アクティブ アマゾンベーシック"},
        "Tシャツ": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > その他の袖丈", "y_ct": "2084054032", "sex": "1",
                 "male": "2084054037", "female": "2084054032", "wowma_catid": "510801",
                 "wowma_catname": "レディースファッション>トップス>Tシャツ", "qoo_catid": "300002252",
                 "qoo_catname": "レディースファッション_トップス_Tシャツ・カットソー",
                 "s_keyword": "tシャツ メンズ 半袖 おおきいサイズ 速乾 vネック おもしろ 白 厚手 無地 綿100 スポーツ レディース キッズ 長袖 ベビー 大きいサイズ ゆったり 七分袖 チャンピオン t1011 リバースウィーブ  青ラベル 3p 赤ラベル ジャパンフィット tシャツグレー ジュニア 160 ブランド 春 セット かわいい スポーツウェア 綿 キャラ サカゼン  バンド アニメ 赤 青 アメカジ インナー 犬 イラスト 印刷 インク インナーシャツ いぬ柄"},
        "Tシャツ": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > その他の袖丈", "y_ct": "2084054032", "sex": "1",
                 "male": "2084054037", "female": "2084054032", "wowma_catid": "510801",
                 "wowma_catname": "レディースファッション>トップス>Tシャツ", "qoo_catid": "300002252",
                 "qoo_catname": "レディースファッション_トップス_Tシャツ・カットソー",
                 "s_keyword": "tシャツ メンズ 半袖 おおきいサイズ 速乾 vネック おもしろ 白 厚手 無地 綿100 スポーツ レディース キッズ 長袖 ベビー 大きいサイズ ゆったり 七分袖 チャンピオン t1011 リバースウィーブ  青ラベル 3p 赤ラベル ジャパンフィット tシャツグレー ジュニア 160 ブランド 春 セット かわいい スポーツウェア 綿 キャラ サカゼン  バンド アニメ 赤 青 アメカジ インナー 犬 イラスト 印刷 インク インナーシャツ いぬ柄"},
        "tシャツ": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > その他の袖丈", "y_ct": "2084054032", "sex": "1",
                 "male": "2084054037", "female": "2084054032", "wowma_catid": "510801",
                 "wowma_catname": "レディースファッション>トップス>Tシャツ", "qoo_catid": "300002252",
                 "qoo_catname": "レディースファッション_トップス_Tシャツ・カットソー",
                 "s_keyword": "tシャツ メンズ 半袖 おおきいサイズ 速乾 vネック おもしろ 白 厚手 無地 綿100 スポーツ レディース キッズ 長袖 ベビー 大きいサイズ ゆったり 七分袖 チャンピオン t1011 リバースウィーブ  青ラベル 3p 赤ラベル ジャパンフィット tシャツグレー ジュニア 160 ブランド 春 セット かわいい スポーツウェア 綿 キャラ サカゼン  バンド アニメ 赤 青 アメカジ インナー 犬 イラスト 印刷 インク インナーシャツ いぬ柄"},
        "シャツ": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > その他の袖丈", "y_ct": "2084054032", "sex": "1",
                "male": "2084054037", "female": "2084054032", "wowma_catid": "510801",
                "wowma_catname": "レディースファッション>トップス>Tシャツ", "qoo_catid": "300002252",
                "qoo_catname": "レディースファッション_トップス_Tシャツ・カットソー",
                "s_keyword": "メンズ レディース 長袖 カジュアル ワンピース 春 ロング 春夏 ビジネス 半袖 大きいサイズ 下着 オフィス 白 形状記憶 ブランド ゆったり チェック ボタンダウン 春秋 ストライプ ノーアイロン 黒 春服 大きい 春物 柄 前あき 花柄 ワンアンブ gold ベージュ きれいめ 夏 ゴスロリ アイロン 赤 青 アイロン不要 麻 アウトドア アウター インナー 汗 イタリア インナーベルト 印刷 芋煮 犬柄 薄手"},
        "フォトプロップス": {"ctname": "オークション > 事務、店舗用品 > 文房具 > その他", "y_ct": "2084042489", "sex": "0", "male": "",
                     "female": "", "wowma_catid": "440506", "wowma_catname": "テレビ・オーディオ・カメラ>ビデオカメラ>周辺機器・アクセサリー",
                     "qoo_catid": "320002383", "qoo_catname": "PC周辺機器・消耗品_PC用アクセサリー_メンテナンス・クリーニング用品",
                     "s_keyword": "結婚式 誕生日 ウェディング 吹き出し 卒業 バースデー ベビー ハート 2歳 ベビーシャワー フレーム ありがとう かわいい おめでとう 大人 還暦 木 結婚 桜 す 卒園 送別会 手作り 春 花 飛行機 前撮り 無地 メッセージ 和風 ガーランド 動物 バルーン 棒 パーティー ピンク 本 2022"},
        "ピアス": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ピアス > その他", "y_ct": "2084005423", "sex": "0", "male": "",
                "female": "", "wowma_catid": "3012", "wowma_catname": "アクセサリー・ジュエリー>ピアス", "qoo_catid": "320001456",
                "qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_ピアス",
                "s_keyword": "メンズ レディース 18金 人気 金属アレルギー対応 キャッチ リング ケース 片耳 16g ブランド シンプル 黒 セット 両耳 ゴールド フープ ゆれる 大人 つけっぱなし ピンクゴールド パール フック 揺れる 樹脂 花 シリコン 落ちない ボール 14g キャッチャー プラチナ シルバー 18g 小さい 持ち運び 収納 携帯用 大容量 コンパクト プレゼント用 透明 ミニ ブルー チェーン 16ゲージ サージカルステンレス 軟骨 消毒 アレルギー対応"},
        "チューブトップ": {"ctname": "オークション > ファッション > レディースファッション > チューブトップ、ベアトップ", "y_ct": "2084243344", "sex": "0",
                    "male": "", "female": "", "wowma_catid": "510816",
                    "wowma_catname": "レディースファッション>トップス>ベアトップ・チューブトップ", "qoo_catid": "320001136",
                    "qoo_catname": "下着・レッグウェア_キャミソール・ペチコート_ベアトップ・チューブトップ",
                    "s_keyword": "ブラ カップ付き キッズ 大きいサイズ レディース 黒 レース 白 水着 ズレない セット 盛れる ホック付き カップ無し ジュニア ダンス ベージュ ストラップ付き 取り外し s 下着 ひも外せる 130 ストラップ ドレス 5l カップなし 黒ヘソだし キャミソール ピンク ワンピース 赤 穴あき 暖かい 網 青 厚手 編み上げ インナー 育乳 衣装 ウェディング 裏起毛 エナメル エステ 柄 オレンジ 落ちない おしゃれ お腹まで"},
        "スカーフ": {"ctname": "オークション > ファッション > ファッション小物 > スカーフ、ポケットチーフ > 女性用", "y_ct": "2084006442", "sex": "0",
                 "male": "", "female": "", "wowma_catid": "450409", "wowma_catname": "バッグ・財布・ファッション小物>ファッション小物>スカーフ",
                 "qoo_catid": "300000123", "qoo_catname": "バッグ・雑貨_スカーフ・ハンカチ_スカーフ",
                 "s_keyword": "レディース リング メンズ 大判 春 シルク ェイス 小さめ 夏用 春物 ブランド 正方形 留め シルバー クリップ クロス パール 小さいサイズ 春夏 白 赤 ドット 黒 日本製 薄手 綿 無地 90 ピンク おすすめ ストール ボタニカル リネン 70 ツイリー カレ90 新品 中古 人気 本 シルク100 バキ外伝 blu-ray tシャツ ポスター dvd フィギュア cd 小説 パーカー"},
        "オイルマッチ": {"ctname": "アンティーク、コレクション > 雑貨 > 喫煙グッズ > ライター > 一般 > オイルライター", "y_ct": "2084037605", "sex": "0",
                   "male": "", "female": "", "wowma_catid": "540803", "wowma_catname": "日用品・文房具・手芸用品>喫煙具>ライター",
                   "qoo_catid": "320000296", "qoo_catname": "カー用品_バイク用品_オイル・添加剤",
                   "s_keyword": "永久マッチ カラビナ ライター 付き灰皿 灰皿 フリント キャンプ ペンギン おしゃれ オイル キーホルダー 芯 アウトドア 面白い い おいる 交換 先 真鍮 手榴弾 スティック 弾 キーホルダー型の 本体 レトロ ジッポ 弾丸"},
        "ナイロンベルト": {"ctname": "ファッション > ファッション小物 > ベルト > 男性用 > その他", "y_ct": "2084214922", "sex": "0", "male": "",
                    "female": "", "wowma_catid": "450502", "wowma_catname": "バッグ・財布・ファッション小物>ベルト>その他ベルト",
                    "qoo_catid": "300002308", "qoo_catname": "メンズファッション_ビジネス・フォーマル_ベルト",
                    "s_keyword": "メンズ 作業用 20mm 30mm幅 時計 レディース 25mm 長いサイズ 18mm 日本製 大きいサイズ おおきいサイズ アウトドア 柄 細い ブランド ykk 極細 20mm幅 荷物 カーキ ワンタッチ 12 25mm幅 10m パーツ 幅40 腕時計 自衛隊 赤 穴あき 青 黄色 アタッチメント アジャスター 穴 メンズラドウェザー ウエスト デジタル 延長 オレンジ オートロック おしゃれ 金具 カラビナ カラー カモフラ カシス カシメ 加工"},
        "ひものれん": {"ctname": "オークション > 事務、店舗用品 > 文房具 > その他", "y_ct": "2084042489", "sex": "0", "male": "", "female": "",
                  "wowma_catid": "310802", "wowma_catname": "インテリア・寝具>クッション・ファブリック>室内用のれん", "qoo_catid": "320000512",
                  "qoo_catname": "家具・インテリア_カーテン・ソファカバー・クッション_のれん",
                  "s_keyword": "おしゃれ 透けない 紐のれん 北欧 200cm丈 150cm丈 日本製 キラキラ ヒモのれん グラデーション グレー 紐暖簾 180cm丈 高密度 ひも暖簾 太い 黒 麻 エスニック オレンジ カット カラフル 花粉 白 城 ストリングカーテン 丈100 つっぱり棒 二重 ニトリ 幅80 幅130 幅200 太め ホワイト 短い 緑  レース ロング びっくらたまご ドラえもん入浴剤 5個1セット ベージュ おんぶ紐 彼女が不在の3日間 グリーン やせたい 今村匡子 その生きづらさ かくれ繊細さん かもしれません 時田 ひさ子"},
        "リボン": {"ctname": "ファッション > レディースファッション > フォーマル > ウエディングドレス > その他", "y_ct": "2084064273", "sex": "0",
                "male": "", "female": "", "wowma_catid": "450512", "wowma_catname": "バッグ・財布・ファッション小物>ベルト>リボンベルト",
                "qoo_catid": "300000124", "qoo_catname": "バッグ・雑貨_ベルト_レディースベルト",
                "s_keyword": "髪飾り タイ バレッタ 手芸 ラッピング ブラウス ヘアゴム 赤 シール 子供 大きい 卒業式 白 黒 入学式 地雷 小さめ タイブラウス メンズ キッズ レディース 女の子 子ども 大きめ ネイビー 黄色 ネット付き パーツ フリル グログラン レース 本 6mm 3mm ワンタッチ オーガンジー 貼るだけ ゴールド 細い 長袖 大きいサイズ きれいめ ブラウスしろ ブラウスすー ピンク ヘアアクセ セット サテン 金 赤ちゃん"},
        "ジョーク グッズ": {"ctname": "オークション > おもちゃ、ゲーム > 手品、パーティグッズ > パーティグッズ > その他", "y_ct": "2084059858", "sex": "0",
                     "male": "", "female": "", "wowma_catid": "292001", "wowma_catname": "おもちゃ・趣味>ボードゲーム>その他ボードゲーム",
                     "qoo_catid": "300000702", "qoo_catname": "ホビー・コスプレ_パーティー・イベント用品_その他",
                     "s_keyword": "ジョークグッズ  女性  福袋 メンズ  おっぱい パンツ 匂い お金 お札 酒 ショーツ 指輪 ライター ブラジャー プレゼント バイブ"},
        "ウォールステッカー": {"ctname": "オークション > 住まい、インテリア > 工具、DIY用品 > 建築材料、住宅設備 > 内装 > 内装材料一般 > 壁材、壁紙 > 壁紙、クロス",
                      "y_ct": "2084304476", "sex": "0", "male": "", "female": "", "wowma_catid": "311904",
                      "wowma_catname": "インテリア・寝具>壁紙・装飾フィルム>ウォールステッカー", "qoo_catid": "300002927",
                      "qoo_catname": "家具・インテリア_インテリア・装飾_ウォールステッカー",
                      "s_keyword": "おしゃれ 植物 花 海 木 桜 トイレ 猫 北欧 モノトーン カフェ風英字 カフェ風 黒 オシャレ 小さい 人気 お洒落 大型 ウォールペーパー ウォールデコ 壁紙 はがせる 装飾 インテリア リビングルーム つた 大きい 花火 立体 花柄 黄色 花畑 青 花びら ブルー プリンセス 影 窓 身長 シルエット 音楽 スイッチ モノクロ 海の生き物 海の中 海をイメージ 海藻 海賊 海外 海防水"},
        "エプロン": {"ctname": "オークション > ファッション > ファッション小物 > エプロン", "y_ct": "2084018499", "sex": "0", "male": "",
                 "female": "", "wowma_catid": "341002", "wowma_catname": "キッズベビー・マタニティ>子供用ファッション小物・雑貨>エプロン",
                 "qoo_catid": "300003264", "qoo_catname": "日用品雑貨_生活雑貨_エプロン",
                 "s_keyword": "保育士 レディース メンズ おしゃれ 子供 キャラクター 黒 バッグ 大きいサイズ 無地 nishiki ニシキ  かぶるだけ 可愛い h型 お尻隠れる かわいい キャンプ 料理 デニム ボタン 人気 オシャレ レディース花柄 北欧 花柄 リネン かぶるたいぷ 男の子 女の子 食事 160 三角巾 セット 140 130 安い 絵本 新作 ジブリ 3l キャラクターなし ll 長袖 おしりが隠れる ロング x型 仕事用 小さめ"},
        "クシ": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > その他", "y_ct": "2084005387", "sex": "0",
               "male": "", "female": "", "wowma_catid": "301602", "wowma_catname": "アクセサリー・ジュエリー>ヘアアクセサリー>その他ヘアアクセサリー",
               "qoo_catid": "300000127", "qoo_catname": "バッグ・雑貨_ヘアアクセサリー_その他",
               "s_keyword": "タニ ジャケット kushitani グローブ シューズ ヒップバッグ レッグバッグ 夏 プロテクター バッグ  ャトリヤ hg ャトリア ガンプラ ジャケット春夏 メッシュ 冬 革 レディース 春 バイク グリーン hguc ャトリヤリペアード プラモデル 1/100 デカール ロボット魂 フィギュア シャツ パンツ gps 夏用 k_5333 ヨシムラ s k-5199 k-3586b 限定 アドーネ 25.5 防水 ラブクロム メンズ 折りたたみ タングルティーザー ドライヤー用 ドライヤー 木製 アイロン"},
        "コーム": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > その他", "y_ct": "2084005387", "sex": "0",
                "male": "", "female": "", "wowma_catid": "301605", "wowma_catname": "アクセサリー・ジュエリー>ヘアアクセサリー>コーム",
                "qoo_catid": "300000127", "qoo_catname": "バッグ・雑貨_ヘアアクセサリー_その他",
                "s_keyword": "メンズ 粗め 折りたたみ ブラシ レディース 犬 セット 眉毛 付き眉ハサミ バーバー 折り畳み ステンレス 高級 携帯 ケント 美容師 小さい かわいい トリートメント お風呂 細め キャラクター おしゃれ 韓国 可愛い 静電気 白 黒 まつ毛 眉 ヘアカラー 猫 プロ ネイル 人気 まとめ髪 携帯用 さらさら 細かい 小型犬 犬用 プロ用 ハチコウ 女の子 ハサミ  左利き 貝印 荒め あらめ"},
        "はさみ": {"ctname": "事務、店舗用品 > 店舗用品 > 理美容店用品", "y_ct": "2084263149", "sex": "0", "male": "", "female": "",
                "wowma_catid": "471217", "wowma_catname": "ビューティ・コスメ>メイク道具・ケアグッズ>散髪はさみ", "qoo_catid": "320000540",
                "qoo_catname": "文具_文房具_はさみ",
                "s_keyword": "ハサミ 小学生 切れ味抜群 コンパクト 髪 ハサミ男 看護師 ハサミポーセリン 左利き カバー付き  波佐見焼 こども 女の子 低学年 右手用 男の子 両利き用 高学年 右利き 日本製 細工用 チタン ミニ 文具 切れ味抜群工作 大きい 細かい 白 よく切れる 携帯 かわいい 可愛い コンパクト キャラクター マグカップ 茶碗 皿 急須 波佐見焼き 湯呑み カレー皿 どんぶり 子供 子ども 子供用 右手 子ども用 幼児 アンティーク アウトドア"},
        "ポーチ": {"ctname": "オークション > ファッション > レディースバッグ > ポーチ", "y_ct": "2084007482", "sex": "0", "male": "",
                "female": "", "wowma_catid": "450303", "wowma_catname": "バッグ・財布・ファッション小物>バッグ>ウエストポーチ",
                "qoo_catid": "300002863", "qoo_catname": "バッグ・雑貨_財布・ポーチ_ポーチ",
                "s_keyword": "レディース メンズ 小物入れ かわいい ブランド 可愛い 防水 キャラクター 人気 小さめ 大きめ プレゼント 肩掛け ショルダー 小さい 化粧品入れ 腰 革 透明 カラビナ付き 韓国 ナプキン入れ 雑貨 女の子 チャムス ベルト メッシュ ハードケース 腰掛け 安い おしゃれ 高校生 ピンク アウトドア 軽量 お風呂 ミニ 仕切り 大容量 男の子 黒 アニメ 赤 アイコス アフタヌーンティー アニマル 犬 イヤホン いちご イニシャル"},
        "収納袋": {"ctname": "オークション > ファッション > レディースバッグ > ポーチ", "y_ct": "2084007482", "sex": "0", "male": "",
                "female": "", "wowma_catid": "450322", "wowma_catname": "バッグ・財布・ファッション小物>バッグ>ポーチバッグ",
                "qoo_catid": "320001140", "qoo_catname": "バッグ・雑貨_バッグ_マザーズバッグ",
                "s_keyword": "アウトドア コミック 圧縮 衣類 特大 ふとん 巾着 毛布 不織布 長物 縦長 帆布 テーブル 丸 チェア 布団 敷き布団 収納ケース 円筒型 ダブル 大 50cm 小 巾着袋 小物入れ キャンプ 衣服 小型 透明 収納 薄型 うす型 薄い 縦 上 動く ウォールナット ウォール 上から 上のスペース 円柱 円形 エコバッグ 絵本 延長コード 円筒 縁台 エイリアン 園芸 おしゃれ"},
        "ライト": {"ctname": "住まい、インテリア > 家具、インテリア > 照明 > 卓上スタンド > デスクライト", "y_ct": "2084239865", "sex": "0", "male": "",
                "female": "", "wowma_catid": "40110507", "wowma_catname": "スポーツ・アウトドア>アウトドア>アウトドア用品>ヘッドライト",
                "qoo_catid": "320000765", "qoo_catname": "アウトドア_キャンプ用品_ライト・ランタン",
                "s_keyword": "ニングケーブル 2m 1m 短い usb-c usbc 3m iphone アンカー 純正 apple  ニング イヤホン スタンド セーバー タイプc anker mfi認証 急速充電 l字 黒 アップル 変換 イヤホンジャック 変換アダプタ 人気のiphone イヤホンランキング 充電 イヤホンマイク ストロボ 照明 卓上 撮影 ケース neewer キャンプ fosoto e26 10cm セット 20cm 30cm 15cm スターウォーズ fx おもちゃ オビワン ギャラクシーエッジ ルーク ブラックシリーズ"},
        "アイコス": {"ctname": "オークション > アンティーク、コレクション > 雑貨 > 喫煙グッズ > その他", "y_ct": "26144", "sex": "0", "male": "",
                 "female": "", "wowma_catid": "540801", "wowma_catname": "日用品・文房具・手芸用品>喫煙具>その他喫煙具",
                 "qoo_catid": "320002474", "qoo_catname": "電子タバコ・加熱式タバコ_電子タバコ・加熱式タバコ_アクセサリー",
                 "s_keyword": "互換機 イルマ ランキング 最強 人気 ブレード 日本製 互換機oixi ブレードなし イルマワン ケース カバー ワン イルマプライム 本体 イルマワンカバー アクセサリー イルマワン本体新品 正規品 イルマワンキット シリコンカバー 充電器 イルマワンケース スリーブ イルマ本体新品 イルマカバー ラップカバー リング カスタム イルマプライムケース 本革 3デュオ ホルダー 3デュオ本体 キャップ スティック 純正 ホルダー単品 ドアカバー  安い 本体キット 互換 2.4 本体のみ おしゃれ 革 キャラクター レザー かわいい ケースカバー"},
        "iQOS": {"ctname": "オークション > アンティーク、コレクション > 雑貨 > 喫煙グッズ > その他", "y_ct": "26144", "sex": "0", "male": "",
                 "female": "", "wowma_catid": "540801", "wowma_catname": "日用品・文房具・手芸用品>喫煙具>その他喫煙具",
                 "qoo_catid": "320002474", "qoo_catname": "電子タバコ・加熱式タバコ_電子タバコ・加熱式タバコ_アクセサリー",
                 "s_keyword": "iqosイルマワン カバー ケース アクセサリー シリコン 充電 車 けーす iqosイルマ本体 レッド ピンク iqos イルマ ワン 本体 プライム リング キット iqos3 duo ホルダーのみ キャップ ホルダー スティックのみ ドアカバー duoホルダー単品 充電器 iqosイルマケース キャラクター キラキラ ブランド レザー iluma one prime terea for メンソール タバコ case 互換機 日本製 人気 40本 typec 2022 ブレードレス pluscig 小型 multi マルチ"},
        "フィクシング": {"ctname": "オークション > ファッション > メンズファッション > その他", "y_ct": "2084207680", "sex": "0", "male": "",
                   "female": "", "wowma_catid": "470611", "wowma_catname": "ビューティ・コスメ>スキンケア>リップクリーム",
                   "qoo_catid": "320001714", "qoo_catname": "ポイントメイク_リップメイク_リップティント",
                   "s_keyword": "ティント ダスティベージュ ミッドナイトモーヴ  スモーキー イニスフリー vt cosmetics bt21 cosmetic リアルウェア  クッション"},
        "シール": {"ctname": "オークション > 住まい、インテリア > 工具、DIY用品 > 建築材料、住宅設備 > 内装 > 内装材料一般 > 壁材、壁紙 > 壁紙、クロス",
                "y_ct": "2084304476", "sex": "0", "male": "", "female": "", "wowma_catid": "341104",
                "wowma_catname": "キッズベビー・マタニティ>子供用日用品>名前シール・ネームラベル", "qoo_catid": "300003172",
                "qoo_catname": "おもちゃ・知育_子供用文房具_ステッカー・シール",
                "s_keyword": "剥がし ブック テープ ふすま紙 タイプ はがし エクステ ド かわいい 帳 スプレー 雷神 ヘラ 強力 車 剥がし液 3m プラスチック用 ガラス コラージュ 2歳 女の子 1歳 3歳 恐竜 トミカ 水道 耐油 エアー 8mm スリーボンド 耐熱 黒 ガソリン 洋風 ２枚入り 和風 2枚 モダン 無地 白 和風モダン ディゾルビット ロックタイト はがし液 人毛 人毛100 リムーバー ピンク ロング"},
        "ストッキング": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > ストッキング > Mサイズ", "y_ct": "2084053100",
                   "sex": "0", "male": "", "female": "", "wowma_catid": "320303",
                   "wowma_catname": "インナー・ルームウェア>タイツ・レギンス>ストッキング", "qoo_catid": "300000049",
                   "qoo_catname": "下着・レッグウェア_靴下・レッグウェア_ストッキング・タイツ",
                   "s_keyword": "膝下 着圧 黒 厚手 大きいサイズ 滑り止め ゆったり サブリナ ベージュ ベージュ膝下 加圧 ベージュ30デニール ベージュ安い ベージュ光沢 ベージュ大きい 膝上 3l 5l 4l 伝線しにくい ラメ 7l 20デニール 30デニール  野球 60デニール 80デニール 40デニール  セット 靴下 靴下屋 くるぶし サワーベージュ 消臭 マタニティ 2枚組 犬印 3枚組 伝染しにくい sm ll xl 強 肌 圧 シアーベージュ ひざ下 なめらか スキニーベージュ"},
        "レギンス": {"ctname": "オークション > ファッション > レディースファッション > レギンス、トレンカ", "y_ct": "2084007161", "sex": "0", "male": "",
                 "female": "", "wowma_catid": "320301", "wowma_catname": "インナー・ルームウェア>タイツ・レギンス>その他タイツ・レギンス",
                 "qoo_catid": "300000047", "qoo_catname": "レディースファッション_パンツ_レギンス",
                 "s_keyword": "マタニティ munny  レディース パンツ メンズ べるみす 着圧 キッズ スポーツ  7分丈 水着 ヨガ 大きいサイズ 5分丈 暖かい 夏 大きい 黒 デニム 綿 裏起毛 夏用 白 ランニング ラッシュガード ベルミス 女の子 男の子 100 120 150 90 スポーツ夏用 スポーツフィットネス ヒップアップ 柄 一枚ばき ll ハイウエスト 燃焼 穴あき 厚手 赤ちゃん アイボリー 赤 一分丈 一部丈 一体型 インナー"},
        "ドアオープナー": {"ctname": "オークション > 住まい、インテリア > その他", "y_ct": "24678", "sex": "0", "male": "", "female": "",
                    "wowma_catid": "551401", "wowma_catname": "本・コミック・雑誌>住まい・インテリア>その他住まい・インテリア",
                    "qoo_catid": "320002036", "qoo_catname": "生活家電_住宅設備家電_ドアロック",
                    "s_keyword": "非接触 日本製 銅 チタン リール付き 抗菌 s字型  シリコン シリコンモールド アシストフック 足 犬 おしゃれ かわいい カバー カバー付き カバー付 可愛い 軽い キーホルダー コロナ サンワ 真鍮 静電気 タッチパネル タッチペン チェーン 吊り革 つり革 鳥 猫 青い鳥の 非金属  リール アクリル ゴム 自動 プラスチック  マルチタッチツール"},
        "ナイフ": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > 調理器具 > 刃物 > 包丁 > 洋包丁", "y_ct": "2084063502", "sex": "0",
                "male": "", "female": "", "wowma_catid": "350806", "wowma_catname": "キッチン・食器・調理>ワイン・バー用品>ソムリエナイフ",
                "qoo_catid": "300003272", "qoo_catname": "キッチン用品_調理用品_包丁・ナイフ",
                "s_keyword": "アウトドア キャンプ レステープ フルタング 折りたたみ ケース フォーク シャープナー 大型 日本製 料理 バトニング オピネル サバイバル 薪割り 折り畳み 調理用 ダマスカス 3m スリーエム デザインライン 10m フィニッシュライン 50m フィニッシュ デザイン ワイヤー モーラ ステンレス  炭素鋼 ガーバー 小型 軽量 ケーパー カラビナ 革 ナイロン ベルト モール ケース革製 ミリタリー プラスチック ケース付き セット スプーン 置き 携帯 ステーキ スティック"},
        "パズル": {"ctname": "オークション > おもちゃ、ゲーム > パズル > その他", "y_ct": "27711", "sex": "0", "male": "", "female": "",
                "wowma_catid": "553505", "wowma_catname": "本・コミック・雑誌>趣味・ホビー>パズル・ゲーム", "qoo_catid": "300000456",
                "qoo_catname": "おもちゃ・知育_パズル_ジグソーパズル",
                "s_keyword": "1000ピース フレーム 50x75cm 26x38cm 51x73.5cm マット 38x53cm 100ピース 1000ピース用 300ピース ジブリ 風景 アニメ ラッセン ワンピース  木製 黒 ゴールド 白 ホワイト 赤  社 ピンク ビバリー グリーン ブラック 1000 大判 6畳 大理石 8畳 4.5畳 子供 60cm 厚め ブラウン uvカット 女の子 すみっこ マイクラ マリオ 51 73.5  エンスカイ 日本 猫 2歳"},
        "ブロック": {"ctname": "オークション > おもちゃ、ゲーム > パズル > その他", "y_ct": "27711", "sex": "0", "male": "", "female": "",
                 "wowma_catid": "403805", "wowma_catname": "スポーツ・アウトドア>ヨガ・ピラティス>ヨガブロック", "qoo_catid": "300003174",
                 "qoo_catname": "おもちゃ・知育_ベビー向けおもちゃ_積み木・ブロック",
                 "s_keyword": "ラボ ドール  人形 バケツ ワゴン 遊園地 3歳 ス トライゴン ほねほねザウルス ボードゲーム ストライゴン デュオ スタイル スライダー ストリングス big チェーン nftゲーム チェーンゲームの法制 チェーン技術概論 本 チェーンゲーム プログラミング チェーン実践入門 開発 牛タン わけあり 激安 タン元 国産 1kg 焼肉 タン中 仙台 コストコ 外国 おもちゃ 玩具 大きい 2歳 1歳 5歳 4歳 やわらかい メモ かわいい おしゃれ メモ帳 ケース"},
        "リュックサック": {"ctname": "オークション > ファッション > 男女兼用バッグ > リュックサック、デイパック", "y_ct": "2084233233", "sex": "0", "male": "",
                    "female": "", "wowma_catid": "34010411", "wowma_catname": "キッズベビー・マタニティ>キッズ>バッグ・ランドセル>リュックサック",
                    "qoo_catid": "320001065", "qoo_catname": "キッズ_バッグ・シューズ_リュックサック",
                    "s_keyword": "メンズ 大容量 おしゃれ 防水 小さめ ビジネス tumi 40l レディース 大人 通勤 軽量 通学 30l キッズ 女の子 20l recon ホットショット 防災  60l 高校生 女子 ザ 子供 キャンプ 30リットル 防水カバー タイムセール スモール ダブルトラブル コラボ レオパード 50l 60 90 小学生 男の子 入学祝い a4 キャラクター 25 33 15 ミッキー 黒 アウトドア 青 赤 雨カバー"},
        "マザーズバッグ": {"ctname": "オークション > ファッション > 男女兼用バッグ > リュックサック、デイパック", "y_ct": "2084233233", "sex": "0", "male": "",
                    "female": "", "wowma_catid": "29090513", "wowma_catname": "おもちゃ・趣味>サバイバルゲーム>装備・衣料>ポーチ・バッグ",
                    "qoo_catid": "320001140", "qoo_catname": "バッグ・雑貨_バッグ_マザーズバッグ",
                    "s_keyword": "トート リュック ショルダー 大容量 ジェラピケ qbag トートバッグ 軽量 レディース 2way おしゃれ 人気 防水 通勤 ブランド ベッド ベージュ ボーダー 斜めがけ ショルダーバッグ 白 ナイロン 小さめ 多機能 3way 撥水 ファスナー 内ポケット多数 キャラクター ファスナー付き 洗える アウトドア アンドット アーバンリサーチ アンコール アーノルド アーバン イブル インナーバッグ 犬 ウエストポーチ ウェット ウエストバッグ エンジェリーベ 大きめ 折り畳み オシャレ 男の子 おむつ替えシート かわいい"},
        "ヘアバンド": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ヘアバンド、カチューシャ", "y_ct": "2084019051",
                  "sex": "0", "male": "", "female": "", "wowma_catid": "301611",
                  "wowma_catname": "アクセサリー・ジュエリー>ヘアアクセサリー>ヘアバンド", "qoo_catid": "300000126",
                  "qoo_catname": "バッグ・雑貨_ヘアアクセサリー_カチューシャ・ヘアバンド",
                  "s_keyword": "メンズ キャラクター 洗顔 スポーツ 洗顔用 レディース かわいい おしゃれ 部屋用 大きめ サッカー  安い 子供 クレヨンしんちゃん  可愛い キャラ リボン キッズ 細い 黒 動物 今治 ハム  ブー  人気 豚 エイリアン 幅広 韓国 女の子 お洒落 オシャレ 赤ちゃん アニメ 汗止め 赤 あかちゃん アンブロ 汗 犬 家用 今治タオル 痛くない 犬耳 イヤホン 家"},
        "バンド": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ヘアバンド、カチューシャ", "y_ct": "2084019051",
                "sex": "0", "male": "", "female": "", "wowma_catid": "5826", "wowma_catname": "腕時計>腕時計用ベルト・バンド",
                "qoo_catid": "300000126", "qoo_catname": "バッグ・雑貨_ヘアアクセサリー_カチューシャ・ヘアバンド",
                "s_keyword": "エイド キズパワーパッド 防水 ウォーターブロック キャラクター ジャンボ 指先用 快適プラス 靴ずれブロック ジュニアサイズ ック フロントウォール ソロベースex チェア ソロティピー1 tc ソロドーム テント ソロベース テーブル タープ  ソー リ ソー替刃 18v ハイコーキ 卓上 ソーブレード cd フィギュア blu-ray スリーブ カバーコレクション bandolier リヤー コスプレ ドリーマーズベスト カーキ 予約 ベージュ 前幕 二股 グランドシート ソロベースex全幕 二又ポール チェアカバー ローチェア 2脚 セット 焚き火"},
        "カチューシャ": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ヘアバンド、カチューシャ", "y_ct": "2084019051",
                   "sex": "0", "male": "", "female": "", "wowma_catid": "301603",
                   "wowma_catname": "アクセサリー・ジュエリー>ヘアアクセサリー>カチューシャ", "qoo_catid": "300000126",
                   "qoo_catname": "バッグ・雑貨_ヘアアクセサリー_カチューシャ・ヘアバンド",
                   "s_keyword": "公式 スパンコール ミニー ミッキー ダッフィー ジェラトーニ オズワルド 海外 キーホルダー メンズ レディース キッズ 猫耳 人気の ランキング リボン 男 痛くない 大きい 部屋用 おしゃれ スポーツ 洗顔 大きめ 貝印 波 幅広 キラキラ 黒 サテン 細い 可愛い 入学式 フォーマル シンプル 水色 パール ネイビー 白 子供 メイド ピンク 赤 青 黄色 しっぽ 大人 男性用 男性 男女兼用"},
        "チョーカー": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > チョーカー > その他", "y_ct": "2084005394", "sex": "0",
                  "male": "", "female": "", "wowma_catid": "3008", "wowma_catname": "アクセサリー・ジュエリー>チョーカー",
                  "qoo_catid": "300002368", "qoo_catname": "メンズバッグ・シューズ・小物_メンズ小物_ペンダント・チョーカー",
                  "s_keyword": "レディース メンズ 地雷系 黒 首輪 レース ネックレス 赤 白 太め シンプル 地雷 シルバー 鈴 60cm レザー 革紐 ステンレス チェーン セット 十字架 地雷系安い リボン 子供 ベルト リード付き すず 大きい 500えんちょうど リード ハート ホワイト ピンク 襟 赤青 赤黒 青 アクセサリー アンティーク 足 アレルギー対応 犬 迷子札 犬用 イニシャル いちご しつけ 腕輪 ウェディング うさぎ"},
        "ボディバッグ": {"ctname": "オークション > ファッション > メンズバッグ > ボディバッグ", "y_ct": "2084008349", "sex": "0", "male": "",
                   "female": "", "wowma_catid": "450318", "wowma_catname": "バッグ・財布・ファッション小物>バッグ>ボディバッグ",
                   "qoo_catid": "300003081", "qoo_catname": "バッグ・雑貨_バッグ_ボディバッグ",
                   "s_keyword": "メンズ レディース 大容量 パタゴニア 防水 人気ブランド 小さめ 斜めがけ 革 本革 おしゃれ 人気 ブランド 軽量 大きめ 完全防水 a4 スポーツ 13インチ レザー ミリタリー オリオン スウィープ sweep メンズ ランニング オレンジ ウエストバッグ 撥水 1102 8l キッズ ヒップバッグ ウエストポーチ 1l 日本製 おしゃれ黒 防刃 nbtc-01 b5 ウエスト  アウトドア 赤 アウトドアブランド アンブロ アニメ イタリア インナー イタリアンレザー"},
        "財布": {"ctname": "オークション > ファッション > ファッション小物 > 財布 > 女性用 > その他", "y_ct": "2084292137", "sex": "1",
               "male": "2084292136", "female": "2084292137", "wowma_catid": "341115",
               "wowma_catname": "キッズベビー・マタニティ>子供用日用品>子供用財布・コインケース", "qoo_catid": "300000112",
               "qoo_catname": "バッグ・雑貨_財布・ポーチ_長財布",
               "s_keyword": "メンズ 二つ折り 長 レディース 2つ折り 小さい 人気ブランド ブランド 大容量 薄い ファスナー 本革 ぽーるすみす うす型 人気 がま口 人気ブランドグッチ かわいい 安い ノーブランド 革 小銭入れなし 可愛い 人気ブランド金運 人気ブランドコーチ 人気ブランドグリーン 人気ブランド国産 黒 アウトドア アニメ 赤 青 アブラサス アウトドアブランド 犬 印伝 イタリアンレザー イタリア 印伝屋 位置情報 薄型 うさぎ エムピウ ミッレフォッリエ エナメル エアタグ エッティンガー エヴァンゲリオン えるじファスナー エイ革"},
        "ショルダーバッグ": {"ctname": "オークション > ファッション > 男女兼用バッグ > ショルダーバッグ", "y_ct": "2084233231", "sex": "0", "male": "",
                     "female": "", "wowma_catid": "450307", "wowma_catname": "バッグ・財布・ファッション小物>バッグ>ショルダーバッグ",
                     "qoo_catid": "300000115", "qoo_catname": "バッグ・雑貨_バッグ_ショルダーバッグ",
                     "s_keyword": "レディース メンズ 斜めがけ メンズ斜めかけ  革 大容量 小さめ 軽量 ブランド メンズ小さめ a4 斜め掛け タンカー レザー a4サイズ スモーキー ヒート フォース 大きめ ナイロン かわいい 防水 大きい ミニ 7507 花柄 黒 7520 m l クラシック サッチェルs レオパード キッズ 公式 現行モデル バニラ ピンク ブルー オレンジ 革紐 アウトドア 赤 アウトドアブランド アニメ 犬 散歩 一眼レフ 医療"},
        "ウエストポーチ": {"ctname": "オークション > スポーツ、レジャー > スポーツ別 > ランニング、ジョギング > アクセサリー > ウエストポーチ", "y_ct": "2084285340",
                    "sex": "0", "male": "", "female": "", "wowma_catid": "450303",
                    "wowma_catname": "バッグ・財布・ファッション小物>バッグ>ウエストポーチ", "qoo_catid": "320001064",
                    "qoo_catname": "キッズ_バッグ・シューズ_ウエストポーチ",
                    "s_keyword": "仕事用 メンズ レディース ナースポーチ ランニング 美容師 防水 大容量 小さめ 多機能 小さめ縦 薄型 縦型 大きめ ナース 革 本革 ブランド おしゃれ かわいい 軽量 可愛い メッシュ ナノ ユニバース キャラクター エプロンポーチ 日本製 スマホ ペットボトル キッズ オシャレ バイク 釣り 仕事 迷彩 ミリタリー 大容量箱型 介護 ピンク タイムセール 4l 72 小さめ アウトドア アウトドアブランド 赤 青 犬の散歩用 犬 散歩"},
        "パーカー": {"ctname": "オークション > スポーツ、レジャー > スポーツウエア > 男性用 > パーカー", "y_ct": "2084303393", "sex": "1",
                 "male": "2084303393", "female": "2084050490", "wowma_catid": "500533",
                 "wowma_catname": "メンズファッション>ジャケット・アウター>マウンテンパーカー", "qoo_catid": "300003075",
                 "qoo_catname": "レディースファッション_トップス_パーカー",
                 "s_keyword": "メンズ  春 大きいサイズ ちゃんぴょん ジップアップ おしゃれ チャンピオン ブランド レディース ゆったり 韓国 キッズ マウンテン ザ ジャケット 薄手 s メンズ春物 白 夏 ボールペン 替え芯 名入れ ソネット ギフト ジョッター im 名入れ無料 アーバン 春夏 春物 春服 長袖 無地 リバースウィーブ ジップ usa 5l 4l 大きいサイズ春夏 6l かわいい ピンク ジュニア グレー 上下 赤 アニメ 青 厚手"},
        "孫の手": {"ctname": "オークション > 住まい、インテリア > その他", "y_ct": "24678", "sex": "0", "male": "", "female": "",
                "wowma_catid": "34051903", "wowma_catname": "キッズベビー・マタニティ>ベビー>衛生・ヘルスケア>その他衛生・ヘルスケア",
                "qoo_catid": "320001860", "qoo_catname": "ダイエット・矯正_矯正・マッサージ_姿勢矯正",
                "s_keyword": "日本製 人気 伸縮 おしゃれ おすすめ ブラシ 竹 スイッチ 猫 折りたたみ 人気セット 木製 塗り薬 ステンレス 丈夫 回らない 磁石 樹脂 伸縮自在 オシャレ kikkerland やわらか 竹製 玉 痛い 1m 3m 薬を塗る あかすり アジアン 赤 かわいい 小さい 背中かいて 折り畳み かくれんぼう ドラえもん 鬼 おもしろ おりたたみ 鬼の爪 折畳み かく恋棒 肩たたきボール付 肩たたき 可愛い 硬い 肩こり カーボン かくれんぼ"},
        "フット カバー": {"ctname": "オークション > ファッション > ファッション小物 > 靴下 > 女性用 > 一般 > 無地", "y_ct": "2084214893", "sex": "0",
                    "male": "", "female": "", "wowma_catid": "320604",
                    "wowma_catname": "インナー・ルームウェア>メンズ靴下>カバーソックス・フットカバー", "qoo_catid": "320001766",
                    "qoo_catname": "ボディ・ハンド・フットケア_フットケア_足用シート",
                    "s_keyword": "脱げ ない フットカバー 浅履き 厚手 雨 浅ばき 赤ちゃん 暖かい あったか メンズ アンクルストラップ 医療用 医療 薄手 レディース 裏起毛 薄い 柄 大きいサイズ 大きい おしゃれ オカモト 男の子 女の子 かわいい 可愛い かかと カラフル 韓国 キッズ キャラクター 極薄 雪 クッション 靴下 黒 車 靴下屋 靴擦れ クッション付き くるぶし 子供 ココピタ コットン 骨折 ベージュ 甲浅 5本指 こども 高齢者用"},
        "インソール": {"ctname": "オークション > ファッション > メンズシューズ > その他", "y_ct": "2084005486", "sex": "0", "male": "",
                  "female": "", "wowma_catid": "40520803", "wowma_catname": "スポーツ・アウトドア>野球>野球シューズ>インソール",
                  "qoo_catid": "300000759", "qoo_catname": "シューズ_シューズアクセサリー_シークレットインソール",
                  "s_keyword": "身長アップ メンズ 衝撃吸収 レディース なかじき 靴 疲れない 中敷き ソルボ 扁平足 革靴 1cm 10cm 28cm 3cm 5cm スニーカー 2cm つま先 消臭 かかと 身長 立ち仕事 衝撃分散吸収 スポーツ 薄型 パンプス モートン病 ハルタ 外反母趾 サイズ調整 安全靴 バスケ 疲れない27センチ用 25センチ 26 踵 ジュニア 29 キッズ 疲労対策 ウェッジヒールタイプ ランニングエア ウォーキング サッカー 子供 2s 矯正 アーチ アーチサポート"},
        "うきわ": {"ctname": "オークション > おもちゃ、ゲーム > 水遊び > 浮き輪、浮き具", "y_ct": "2084042423", "sex": "0", "male": "",
                "female": "", "wowma_catid": "401101", "wowma_catname": "スポーツ・アウトドア>アウトドア>その他アウトドア",
                "qoo_catid": "300000240", "qoo_catname": "アウトドア_キャンプ用品_その他",
                "s_keyword": "浮き輪 子供 60cm 男の子 腕 女の子 足入れ 紐付き 70cm 50cm 70 大人用 120cm 100cm フロート でかい かわいい ハート 透明 90cm ドーナツ  こども 幼児 赤ちゃん 大人 空気入れ 浮輪 こども用 子ども アーム 幼児用 お風呂 1歳 首 日除け 室内 ウキワ 腕輪 小学生 パウパトロール ハンドル 4歳 車 あひる 3歳 電動 手動 電池 電池式 空気入れ付き"},
        "フロート": {"ctname": "オークション > おもちゃ、ゲーム > 水遊び > 浮き輪、浮き具", "y_ct": "2084042423", "sex": "0", "male": "",
                 "female": "", "wowma_catid": "401101", "wowma_catname": "スポーツ・アウトドア>アウトドア>その他アウトドア",
                 "qoo_catid": "300000240", "qoo_catname": "アウトドア_キャンプ用品_その他",
                 "s_keyword": "リグ バルブ スイッチ 釣り ボート アウェイドリーム グラス 浮き輪 弁 アジング メバル アルカジック  リグフック 月下美人 ロッド ダイワ 中通し toto inax キャブレター バイク ミクニ 水槽 トイレ 3/4 100v ac100v リレー 12v 小型 スイッチ付きポンプ ビルジ 20a 発泡 玉 改造キット z1 改造 ロッドホルダー カバー ボートドーリー ストッパーピン デッキ ブライス 予約 ネオブライス レトロ クリームソーダ 大きいサイズ"},
        "シャワーカーテン": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > バス > その他", "y_ct": "2084024452", "sex": "0", "male": "",
                     "female": "", "wowma_catid": "471206", "wowma_catname": "ビューティ・コスメ>メイク道具・ケアグッズ>バスグッズ",
                     "qoo_catid": "300000500", "qoo_catname": "日用品雑貨_バス用品_その他",
                     "s_keyword": "防カビ ユニットバス 防水 透明 撥水 半透明 180 90 150 120 120x150 日本製 かわいい 海 星 120x150可愛い ブルー ユニットバス用 フック 120x180 星柄 ダークブラウン おしゃれ 厚手 フック式 s字 フック付き プラスチック クリップ 10個 細い ステンレス フックタイプ 花柄 北欧 お洒落 オシャレ 200cm丈 透けない 防寒 220cm 220 200  180x180 130x150 アニメ 赤 洗える アート アマゾンベーシック"},
        "ウィッグ": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ウイッグ > その他", "y_ct": "2084062532", "sex": "0",
                 "male": "", "female": "", "wowma_catid": "470902", "wowma_catname": "ビューティ・コスメ>ヘアケア・スタイリング>ウィッグ・かつら",
                 "qoo_catid": "300002181", "qoo_catname": "バッグ・雑貨_ウィッグ・つけ毛_フルウィッグ",
                 "s_keyword": "ロング ボブ ショート メンズ スタンド セミロング ネット 金髪 ブライトララ ストレート 巻き髪 黒 ピンク 姫カット 前髪なし カール 白 人毛 シルバー パーマ 自然 グレー ショートボブ レディース 男装 ブラック ウルフ マネキン 安い セット 発泡スチロール ハンガー 三脚 ドール コンパクト インナーカラー ウェーブ 肌色 水泳帽タイプ 医療用 コスプレ ストッキングタイプ 痛くない ストッキング ロングタイプ ミディアム ポニーテール フル グラデーション 黒髪 ウイッグ"},
        "パジャマ": {"ctname": "オークション > ファッション > メンズファッション > パジャマ", "y_ct": "2084006762", "sex": "1", "male": "2084006762",
                 "female": "2084053160", "wowma_catid": "320104", "wowma_catname": "インナー・ルームウェア>その他インナー・ルームウェア>ペアパジャマ",
                 "qoo_catid": "300002291", "qoo_catname": "メンズファッション_インナー・靴下_パジャマ・ルームウェア",
                 "s_keyword": "メンズ 春 綿100 春夏 冬 夏 上下 シルク ばくね  レディース 入院 ワンピース ナルエー かわいい 大きいサイズ 前開き 綿 猫 春秋 キッズ 女の子 男の子 クレヨンしんちゃん 150 半袖 長袖 130 日本製 ガーゼ ダブルガーゼ ペア 大人 子供 赤ちゃん 140 もこもこ こども  前あき 可愛い 夏用 和風 デリシャス 光る デリシャスパーティ 120 バンダイ 110 レディース 赤"},
        "折りたたみ バッグ": {"ctname": "オークション > ファッション > メンズバッグ > リュックサック、デイパック", "y_ct": "2084008303", "sex": "0",
                      "male": "", "female": "", "wowma_catid": "450313",
                      "wowma_catname": "バッグ・財布・ファッション小物>バッグ>バックパック・リュック", "qoo_catid": "300002169",
                      "qoo_catname": "バッグ・雑貨_バッグ_リュック・デイパック",
                      "s_keyword": "大容量 キャリーオン 旅行 ファスナー ブランド おしゃれ 黒 丈夫 防水 フォーマル アウトドア 買い物バッグ 折りたたみ 保冷 かいものかご バッグ りんこう袋 自転車 折りたたみ自転車 輪行バッグ 収納 バック ふくろ 専用ケース付き 14インチ 20インチ レジかごバッグ キャンプ 折りたたみバッグ 軽量 工具 小型 フォーマルさぶバッグ 石のさかい 高級 骨壷収納バッグ 軽撥水 手提げ 袋 骨壺 小さい ショルダー スーツケース スポーツ 保冷バッグ １６ ２０インチ対応 輪行袋 サイクリング ツーリング 持ち運び 便利"},
        "ネクタイピン": {"ctname": "オークション > ファッション > ファッション小物 > ネクタイ > ネクタイ一般", "y_ct": "2084036146", "sex": "0", "male": "",
                   "female": "", "wowma_catid": "450413", "wowma_catname": "バッグ・財布・ファッション小物>ファッション小物>ネクタイピン",
                   "qoo_catid": "300002307", "qoo_catname": "メンズファッション_ビジネス・フォーマル_ネクタイ",
                   "s_keyword": "おしゃれ メンズ おもしろ ブランド セット シンプル ク プレゼント メンズギフト メンズ魚 名入れ paul smith コレクション ブラック 黒 ツイスト 面白い 可愛い 動物 学校 犬 レディース かわいい 人気 人気箱入り チェーン 日本製 猫 カフスボタン カフス ギフト シルバー マット クメンズ クブランド クレージュ クセット クリップ クストライプ クロムハーツ クチェック ミラショーン アニメ アニメコラボ 赤 青 アーノルドパーマー アンティーク アメジスト"},
        "ネクタイ": {"ctname": "オークション > ファッション > ファッション小物 > ネクタイ > ネクタイ一般", "y_ct": "2084036146", "sex": "0", "male": "",
                 "female": "", "wowma_catid": "341009", "wowma_catname": "キッズベビー・マタニティ>子供用ファッション小物・雑貨>ネクタイ",
                 "qoo_catid": "300002307", "qoo_catname": "メンズファッション_ビジネス・フォーマル_ネクタイ",
                 "s_keyword": "ピン ハンガー おしゃれ メンズ ブランド ワンタッチ セット 結婚式 タイラバ おもしろ シンプル ピンク ランキング 電動 省スペース 回転 木製 10本 プレゼント メンズギフト メンズ魚 名入れ 人気 セール フェラガモ ブランドミチコ ジュニア 黒 レディース 卒業式 学生 白 贈り物 グリーン ドット シルバー レインボー 3本 シルク 洗える シルク100 無地 選べる チーフ パステル シルク100% ゴールド ブルー カーリー スタート"},
        "レインウェア": {"ctname": "オークション > スポーツ、レジャー > キャンプ、アウトドア用品 > 雨具、レインウエア > その他", "y_ct": "2084208701", "sex": "0",
                   "male": "", "female": "", "wowma_catid": "34051201",
                   "wowma_catname": "キッズベビー・マタニティ>ベビー>レインウェア>その他レインウェア", "qoo_catid": "320000984",
                   "qoo_catname": "自転車_サイクルウェア・ヘルメット_レインウェア",
                   "s_keyword": "メンズ ゴルフ レディース バイク 自転車 ダイワ 上下 釣り パンツ キッズ 150 登山 大きいサイズ 上下セット  スリクソン 上 タイトリスト ルコック ワークマンリュック いなれむ ズボン 透湿 リュック バイク用 リュック対応 コンパクト収納 コンパクト 防水 3l 通学 メンズ3l アウトドア 赤 アオキ 足 アジャスト バッグイン 犬 イナレム イージス 上のみ ウォーキング 薄手 動きやすい 海 ウィンターチェリー ウルトラライト エントラント エヴァ"},
        "おべんとケース": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > 弁当用品 > 弁当箱（男女兼用）", "y_ct": "2084261189", "sex": "0",
                    "male": "", "female": "", "wowma_catid": "350102", "wowma_catname": "キッチン・食器・調理>お弁当グッズ>お弁当箱",
                    "qoo_catid": "300003274", "qoo_catname": "キッチン用品_キッチン雑貨_お弁当箱",
                    "s_keyword": "東洋アルミ  深いぃ 深いい おべんとう箱 ケース付き ケース 女性 l"},
        "おべんとうケース": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > 弁当用品 > 弁当箱（男女兼用）", "y_ct": "2084261189", "sex": "0",
                     "male": "", "female": "", "wowma_catid": "350102", "wowma_catname": "キッチン・食器・調理>お弁当グッズ>お弁当箱",
                     "qoo_catid": "300003274", "qoo_catname": "キッチン用品_キッチン雑貨_お弁当箱", "s_keyword": "おべんとう箱 ケース付き ケース 女性"},
        "弁当箱": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > 弁当用品 > 弁当箱（男女兼用）", "y_ct": "2084261189", "sex": "0",
                "male": "", "female": "", "wowma_catid": "340809",
                "wowma_catname": "キッズベビー・マタニティ>子供用キッチン・お弁当グッズ>子供用お弁当箱", "qoo_catid": "300000448",
                "qoo_catname": "キッズ_雑貨・小物_子供用弁当箱・食器",
                "s_keyword": "男性 保温 女性 2段 わっぱ 子供 スリム 炊飯器 大容量 一段 女子 丼 タイガー どんぶり スケーター 1段 おしゃれ 小さめ 可愛い ステンレス 男子 女の子 600ml わっぱ風 レンジ対応 日本製 レンジ 食洗機対応 アルミ 男の子 450 食洗機 280 二段 漏れない thanko サンコー ２段 usb 1合 充電式 海外 洗いやすい 大人 赤 アウトドア アフタヌーンティー 入れる袋 箸付き 入れ物"},
        "装飾金具": {"ctname": "オークション > ホビー、カルチャー > ハンドクラフト、手工芸 > 裁縫、刺繍 > その他", "y_ct": "2084045844", "sex": "0",
                 "male": "", "female": "", "wowma_catid": "311902", "wowma_catname": "インテリア・寝具>壁紙・装飾フィルム>アートパネル・アートボード",
                 "qoo_catid": "300000475", "qoo_catname": "家具・インテリア_インテリア・装飾_その他",
                 "s_keyword": "コーナー ゴールド 輪 led電球 密閉形器具対応 e12口金 電球色相当 0.5w 装飾電球 t型タイプ ldt1lge12 e26口金 0.9w g型タイプ ldg1lgw"},
        "ギフト袋": {"ctname": "オークション > 事務、店舗用品 > その他", "y_ct": "22996", "sex": "0", "male": "", "female": "",
                 "wowma_catid": "54090201", "wowma_catname": "日用品・文房具・手芸用品>手芸・クラフト・生地>その他手芸用品>その他",
                 "qoo_catid": "320000539", "qoo_catname": "文具_文房具_ギフトラッピング用品",
                 "s_keyword": "小 ビニール 大きめ 特大 おしゃれ 手提げ 大 巾着 紙 100枚 透明 桜 水色 手提げビニール 中 ギフト 袋 青 ありがとう 犬 ギフトよう袋 ギフトよう紙袋 鉛筆 えんぴつ お酒 女の子 オーガンジー かわいい 可愛い 菓子 感謝 和 黄色 黒 亀のすけ 駄菓子詰め合わせ 選べる付 紙袋 小分け 子供 子ども コットン 小判抜き 酒 白 スクエア型 セット 正方形 誕生日 縦長"},
        "ラッピング袋": {"ctname": "オークション > 事務、店舗用品 > その他", "y_ct": "22996", "sex": "0", "male": "", "female": "",
                   "wowma_catid": "54090201", "wowma_catname": "日用品・文房具・手芸用品>手芸・クラフト・生地>その他手芸用品>その他",
                   "qoo_catid": "320000539", "qoo_catname": "文具_文房具_ギフトラッピング用品",
                   "s_keyword": "可愛い 透明 手提げ 小さい 誕生日 大量 お菓子 お祝い プレゼント用  特大 小さめ 大きめ 大 小 ビニール 大きい 紙袋 安い セット 大きめ大容量 かわいい バレンタイン opp プレゼント袋 ラッピング 袋 ありがとう 青 赤 麻 アニマル アクセサリー 明日 厚手 赤ちゃん 一枚 犬 犬柄 色々 インディゴ 色紙サイズ うさぎ ウルトラマン ウサギ 海 絵本 鉛筆 オシャレ 大き目 巾着"},
        "ラッピング 袋": {"ctname": "オークション > 事務、店舗用品 > その他", "y_ct": "22996", "sex": "0", "male": "", "female": "",
                    "wowma_catid": "54090201", "wowma_catname": "日用品・文房具・手芸用品>手芸・クラフト・生地>その他手芸用品>その他",
                    "qoo_catid": "320000539", "qoo_catname": "文具_文房具_ギフトラッピング用品",
                    "s_keyword": "小 透明 特大 大 おしゃれ 包装紙 プレゼント ギフト 中 小さめ 手提げ ビニール かわいい お菓子 小さい 無地 巾着 大きい まちあり テープ付き a4 マチあり 100センチ マチ付き 150センチ 誕生日 70センチ セリア 不織布 大きいサイズ 大量 安い 大人 オシャレ m おしゃれ大 ペン 500円位 セット sサイズ 10枚 ll 30 中身見えない 中サイズ 中身が見える 中身が見えない 紙袋 ありがとう 青"},
        "目出し帽": {"ctname": "オークション > 自動車、オートバイ > オートバイ > バイクウエア、装備 > フェイスマスク、ネックウォーマー", "y_ct": "2084246658",
                 "sex": "0", "male": "", "female": "", "wowma_catid": "29090504",
                 "wowma_catname": "おもちゃ・趣味>サバイバルゲーム>装備・衣料>フェイスマスク", "qoo_catid": "300002177",
                 "qoo_catname": "バッグ・雑貨_帽子_その他",
                 "s_keyword": "夏用 ニット 防寒 夏 uvカット 白 メンズ バラクラバ 迷彩 レディース 子ども 迷彩子ども用 ピンク 青 赤 アーミー アニマル タクティカル フェイスマスク ミリタリー フル 大きい かわいい フェイスカバー 自転車 ネックガード upf50+ 吸汗 速乾 バイク スポーツ 息苦しくない 薄手 うさぎ 兎 おしゃれ おもしろ 面白い カラフル カラー 可愛い 黄色 キッズ 口 口開き 黒 蛍光 コスプレ 子供 子供用"},
        "フェイスマスク": {"ctname": "オークション > 自動車、オートバイ > オートバイ > バイクウエア、装備 > フェイスマスク、ネックウォーマー", "y_ct": "2084246658",
                    "sex": "0", "male": "", "female": "", "wowma_catid": "29090504",
                    "wowma_catname": "おもちゃ・趣味>サバイバルゲーム>装備・衣料>フェイスマスク", "qoo_catid": "300002177",
                    "qoo_catname": "バッグ・雑貨_帽子_その他",
                    "s_keyword": "シート 夏用 バイク lululun スポーツ サバゲー パック ヘンポ 夏 個包装 シートのみ ドライ ルルルン 人気 韓国 クオリティ たまごシートマスク ギフト メンズ 冷感 釣り 大きいサイズ 息苦しくない レディース バイク用 防寒 耳かけ 耳カバー ブルー 10周年 青 7枚 桜 over45 黒 clear 京都 レスキュー 男性用 スポーツメーカー スポーツ用 冷 スポーツ ライラクス 骸骨 2枚 美白 面白い 大容量 sk2"},
        "ネックウォーマー": {"ctname": "オークション > 自動車、オートバイ > オートバイ > バイクウエア、装備 > フェイスマスク、ネックウォーマー", "y_ct": "2084246658",
                     "sex": "0", "male": "", "female": "", "wowma_catid": "450411",
                     "wowma_catname": "バッグ・財布・ファッション小物>ファッション小物>スヌード・ネックウォーマー", "qoo_catid": "300002177",
                     "qoo_catname": "バッグ・雑貨_帽子_その他",
                     "s_keyword": "メンズ レディース 夏用 スノーボード バイク キッズ buff 薄手 スポーツ 防寒 防風 大きいサイズ 夏 春 春夏 スノボ おしゃれ シルク 冷感 ボタン uv 赤 白 ブランド ロキシー ジュニア バイク用 コミネ タイチ バイクメンズ フルフェイス マジックテープ 女の子 スキー 男の子 フリース サッカー 野球 カモフラ uvカット メリノ メリノウール 多機能ヘッドウェア アウトドア 青 頭 雨 暖かい アニマル 犬"},
        "ハンドスピナー": {"ctname": "オークション > おもちゃ、ゲーム > その他", "y_ct": "26082", "sex": "0", "male": "", "female": "",
                    "wowma_catid": "401101", "wowma_catname": "スポーツ・アウトドア>アウトドア>その他アウトドア", "qoo_catid": "320000611",
                    "qoo_catname": "ホビー・コスプレ_コレクション_その他",
                    "s_keyword": "よく回る 民族 水道 光る こども用 吸盤 プッシュポップ かっこいい よく回る耐久力 日本製 よく回るかっこいい よく回る小さい よく回る安い よく回る民族 よく回る小さい安い 本物 民族水道 民族ヒカキン 民族アイスピン mixmart ispin 民族bruck 民族ｅｖｉｕｓ シルバー 水道本物 ゴールド 新型 安い こども用安い やすい 人気ランキング1位 赤ちゃん シリコン 腕 セット 星型 カッコイイ カッコいい アメリカン アイスピン ヒカキン 青 赤 アニメーション アークスター アルミ イラスト 浮く 動く ウロボロス"},
        "オフショル": {"ctname": "オークション > ファッション > レディースファッション > ニット、セーター > その他の袖丈", "y_ct": "2084054035", "sex": "0",
                  "male": "", "female": "", "wowma_catid": "510812", "wowma_catname": "レディースファッション>トップス>ノースリーブ",
                  "qoo_catid": "300000025", "qoo_catname": "レディースファッション_トップス_ニット",
                  "s_keyword": "ダー ワンピース 大きいサイズ ロング フレア 夏 マキシ 水着 長袖 ディープ vネック タイトミニ クラブドレス 白 トップス 春 キッズ 冬 半袖 レース レディース インナー ブラウス  ニット 5l tシャツ カップ付き ドレス パーカー ブラ ウエディングドレス 大きい 可愛い かわいい 韓国 カットソー 金 キャバ 黒 透け コスプレ 下着 シャツ シースルー ショート丈 スウェット セットアップ へそ出し タートルネック 谷間"},
        "セーター": {"ctname": "オークション > ファッション > レディースファッション > ニット、セーター > その他の袖丈", "y_ct": "2084054035", "sex": "1",
                 "male": "2084064188", "female": "2084054035", "wowma_catid": "510811",
                 "wowma_catname": "レディースファッション>トップス>ニット・セーター", "qoo_catid": "300000071",
                 "qoo_catname": "メンズファッション_トップス_ニット・セーター",
                 "s_keyword": "メンズ 春 ビジネス vネック ゴルフ  冬 大きいサイズ 薄手 タートルネック レディース 干しネット 干し ゆったり 学生 春物 春夏 柄 ボーダー ロング ピンク 黄色 日本製 2段 セキスイ sw-1 大 ぱっと２段 干しネット1段 人気 可愛い ウール 冬カシミヤ ハイネック 冬安い カシミヤ ニット 4l ベスト グリーン ハンガー 方 編み物 本 圧縮袋 青 赤 穴あき 補修 編み方 圧縮"},
        "フラットシューズ": {"ctname": "オークション > ファッション > レディースシューズ > その他", "y_ct": "2084005499", "sex": "0", "male": "",
                     "female": "", "wowma_catid": "51140501",
                     "wowma_catname": "レディースファッション>靴・シューズ>フラットシューズ>その他フラットシューズ", "qoo_catid": "320001571",
                     "qoo_catname": "シューズ_サンダル_コンフォート",
                     "s_keyword": "レディース 黒 歩きやすい キッズ 女の子 白 ストラップ 痛くない ビジュー リボン グレー 3e 人気 おしゃれ 幅広 やわらか フットスキ メンズ 赤 26 即日出荷 エナメル シルバー 厚底 雨 青 インソール 痛く無い ウォーキング 柄 大きいサイズ 折り畳み オフィス 折りたたみ オリエンタル 大人 革 韓国 カジュアル カメリア かわいい 可愛い キラキラ キャメル 本革 きらきら 靴下 クロックス クッション 結婚式"},
        "イヤホンケーブル": {"ctname": "オークション > 家電、AV、カメラ > オーディオ機器 > ヘッドフォン、イヤフォン > イヤフォン > その他", "y_ct": "2084219572",
                     "sex": "0", "male": "", "female": "", "wowma_catid": "44060201",
                     "wowma_catname": "テレビ・オーディオ・カメラ>ヘッドホン・イヤホン>イヤホン>その他イヤホン", "qoo_catid": "320002471",
                     "qoo_catname": "イヤホン・ヘッドホン_その他イヤホン・ヘッドホン_延長ケーブル",
                     "s_keyword": "延長 2pin mmcx クリップ オスオス まとめる 巻き取り マイク付き 変換 3m 延長アダプター 5m 短い 1m 3極 4極 0.78mm 4.4 2ピン 3.5 white seank kz 銀線 マイク 4.4mm 1.8m 3.5mm 秋月 い両端オス せんばいざー あいほん あいほんじゅうでん アイホンじゅう電 オスメス 音量調節 イヤホン ケーブル カバー 絡まない 金メッキ 金銀 切り替え 金 ケース 高音質 固定 高耐久 左右 収納"},
        "名刺入れ": {"ctname": "オークション > ファッション > ファッション小物 > 名刺入れ、カードケース > 男性用", "y_ct": "2084246781", "sex": "0",
                 "male": "", "female": "", "wowma_catid": "450421", "wowma_catname": "バッグ・財布・ファッション小物>ファッション小物>名刺入れ",
                 "qoo_catid": "300002375", "qoo_catname": "バッグ・雑貨_財布・ポーチ_名刺入れ・カードケース",
                 "s_keyword": "メンズ レディース ブランド 人気 革 本革 20代 人気ブランド 安い おしゃれ 黒 名入れ 高級 めいしいれレディース 名刺 入れ ケース 入社祝い 名前入れ グレー グリーン ネイビー レザー ピンク クロコ 正規品 ベージュ 薄型 男女兼用 薄い ブランドカードケース 女性 金属 ブランド男性 レディース アルミ アニメ 赤 アーノルドパーマー アルミケース 青 アフタヌーンティー 印伝 犬 イタリアンレザー 印伝屋 イタリア イニシャル イタリア製 うす型"},
        "髪留め": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ヘアピン", "y_ct": "2084005386", "sex": "0",
                "male": "", "female": "", "wowma_catid": "301612", "wowma_catname": "アクセサリー・ジュエリー>ヘアアクセサリー>ヘアピン",
                "qoo_catid": "300000125", "qoo_catname": "バッグ・雑貨_ヘアアクセサリー_ヘアピン",
                "s_keyword": "クリップ メンズ バレッタ ゴム 大きめ しっかり バナナクリップ リボン フォーマル ミニ 小さめ おしゃれ パール 黒 可愛い 洗顔 前髪 スポーツ 睡眠 カチューシャ シンプル アンティーク ピンク 御洒落 大人 子供 かわいい 細い 飾り しっかり透明 大きい 小さい 女の子 青 青緑 フック 水色 赤 あとがつかない 跡がつかない 赤ちゃん 網 アイロン 男の子 痛くない インコ 犬 痛まない うさぎ 海"},
        "ヘアピン": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ヘアピン", "y_ct": "2084005386", "sex": "0",
                 "male": "", "female": "", "wowma_catid": "301612", "wowma_catname": "アクセサリー・ジュエリー>ヘアアクセサリー>ヘアピン",
                 "qoo_catid": "300000125", "qoo_catname": "バッグ・雑貨_ヘアアクセサリー_ヘアピン",
                 "s_keyword": "おしゃれ 子供 メンズ ゴールド 黒 パール かわいい シルバー リボン 大人 大人可愛い 前髪 小さめ クリップ パッチン オシャレ シンプル 花 痛くない 大きめ 白 フォーマル 安全 目立たない スポーツ キャラ lサイズ マット ゴールド台座つき パーツ 強力 ぱっちん こども 小 卒業式 結婚式 セット 入学式 可愛い 韓国 子ども アメピン 御洒落 ラインストーン キラキラ ミニ ピンク 大きい 小さい 量産型"},
        "シートベルトヘルパー": {"ctname": "オークション > 自動車、オートバイ > セーフティ > チャイルドシート > その他", "y_ct": "2084242666", "sex": "0",
                       "male": "", "female": "", "wowma_catid": "3404", "wowma_catname": "キッズベビー・マタニティ>チャイルドシート",
                       "qoo_catid": "300000412", "qoo_catname": "ベビー・マタニティ_ベビーシート・チャイルドシート_チャイルドシート",
                       "s_keyword": "子供 アールエル らくらく"},
        "ジャケット": {"ctname": "オークション > ファッション > メンズファッション > ジャケット、上着 > ジャンパー、ブルゾン > ジャンパー、ブルゾン一般 > Lサイズ",
                  "y_ct": "2084050109", "sex": "1", "male": "2084050109", "female": "2084057476",
                  "wowma_catid": "500501", "wowma_catname": "メンズファッション>ジャケット・アウター>その他ジャケット・アウター",
                  "qoo_catid": "300002186", "qoo_catname": "レディースファッション_アウター_ダウンジャケット・コート",
                  "s_keyword": "メンズ 春 大きいサイズ ビジネス  春夏 カジュアル 大きめ 春秋 ゆったり レディース バイク 入学式 コミネ キッズ コンパクト np71830 140 フォーマル 白 大きい ノーカラー ベージュ 黒 夏 プロテクター入り 冬 メッシュ スーツ オフィス マウンテンパーカー 防水 グレー 3l ツイード 17号 フルメッシュ オールシーズン 春夏秋 jk112 赤 青 アウトドア 麻 インナー シャツ tシャツ ブラウス イタリア イラスト 衣装"},
        "ブラウス": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486", "sex": "0",
                 "male": "", "female": "", "wowma_catid": "510815", "wowma_catname": "レディースファッション>トップス>ブラウス",
                 "qoo_catid": "300000013", "qoo_catname": "レディースファッション_トップス_シャツ・ブラウス",
                 "s_keyword": "レディース 長袖 おしゃれ 春 オフィス フォーマル 大きいサイズ 白 スーツ リボン 襟付き 丈長 柄 きれいめ 春夏 綿素材 インナー vネック 七分袖 7分袖 セット ボウタイ ストライプ フリル レース レディースリボン ホワイト ノースリーブ レディース50代 半袖 大きいサイズ入学式 麻 大きいサイズベスト 卒業式 入学式 4l 光沢 シャツ 青 赤 アイロン不要 アイボリー アウター アクアガレージ 青山 厚手 イノ 衣装 インド キャミソール"},
        "チュニック": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486", "sex": "0",
                  "male": "", "female": "", "wowma_catid": "510810", "wowma_catname": "レディースファッション>トップス>チュニック",
                  "qoo_catid": "300002253", "qoo_catname": "レディースファッション_トップス_チュニック",
                  "s_keyword": "レディース 春 50代 40代 エプロン トップス ワンピース ブラウス 春夏 大きいサイズ 春50代 長袖 シニア 春物 ロング 袖バルーン シンプル 秋冬 50代日本製 60代 夏 おしゃれ 保育士 黒 型紙 エプロンll エプロン無地 デニム ワンピース春夏物 ワンピースストライプ ワンピース保育 ブラウス大きいサイズ 白 フレア ヘム シースル シフォン ゆったり 半袖 赤 青 アンサンブル 麻 アジアン インナー ウエスト 薄手 裏起毛 ウェア エスニック"},
        "水着": {"ctname": "オークション > スポーツ、レジャー > スポーツ別 > 水泳 > スイムウエア > 女性用 > Mサイズ > その他", "y_ct": "2084224142",
               "sex": "1", "male": "2084051836", "female": "2084224142", "wowma_catid": "340607",
               "wowma_catname": "キッズベビー・マタニティ>マタニティ・ママ>マタニティ水着", "qoo_catid": "300002298",
               "qoo_catname": "メンズファッション_その他メンズファッション_水着",
               "s_keyword": "レディース メンズ 体型カバー フィットネス ビキニ 男性 競泳 ワンピース 大きいサイズ セパレート ラッシュガード セット インナー おおきいサイズ 練習用 スピード 50代 可愛い 50代大きい 下 4点セット 水陸両用 アリーナ 半袖 スカート ハイウエスト スポーツ 上下セット フリル フレアトップ 3点セット 黒 かわいい 男性用 ジム 上着 上下 長袖 ぽっちゃり 40代 ママ タンキニ 子供 130 女の子 白 アンダーショーツ 穴あき 赤ちゃん インナーショーツ"},
        "レッグウォーマー": {"ctname": "オークション > スポーツ、レジャー > スポーツウエア > 女性用 > インナーウエア > タイツ", "y_ct": "2084246668", "sex": "0",
                     "male": "", "female": "", "wowma_catid": "320911", "wowma_catname": "インナー・ルームウェア>レディース靴下>レッグウォーマー",
                     "qoo_catid": "300000049", "qoo_catname": "下着・レッグウェア_靴下・レッグウェア_ストッキング・タイツ",
                     "s_keyword": "レディース メンズ イオンドクター ロング シルク ベビー 冷え対策 赤ちゃん 自転車 レディース夏用 薄手 コットン 夏 ゴルフ ゆったり 大きいサイズ スポーツ 夏用 黒 田中みなみ 41 バレエ 綿 かかと ダンス シルク100% 日本製 足首 ウール uv 男の子 女の子 オーガニック ホワイト 締め付けない 冷え対策ウール 綿100 オーガニックコットン 白 マビック 冬 赤 あかちゃん 厚手 アウトドア 春 犬用 犬 衣装 医療用"},
        "タイツ": {"ctname": "オークション > スポーツ、レジャー > スポーツウエア > 女性用 > インナーウエア > タイツ", "y_ct": "2084246668", "sex": "1",
                "male": "2084245567", "female": "2084246668", "wowma_catid": "320301",
                "wowma_catname": "インナー・ルームウェア>タイツ・レギンス>その他タイツ・レギンス", "qoo_catid": "300000049",
                "qoo_catname": "下着・レッグウェア_靴下・レッグウェア_ストッキング・タイツ", "s_keyword": ""},
        "レッグカバー": {"ctname": "オークション > スポーツ、レジャー > スポーツウエア > 女性用 > インナーウエア > タイツ", "y_ct": "2084246668", "sex": "0",
                   "male": "", "female": "", "wowma_catid": "320905",
                   "wowma_catname": "インナー・ルームウェア>レディース靴下>カバーソックス・フットカバー", "qoo_catid": "300000049",
                   "qoo_catname": "下着・レッグウェア_靴下・レッグウェア_ストッキング・タイツ",
                   "s_keyword": "メンズ 防水 ロードバイク 夏 雨 レディース パールイズミ 夏用 冷感 uv 海水 ランニング 自転車 ファスナー ロング 子供 迷彩 使い捨て 雨具 雨ゴルフ 418 バイク 赤ちゃん アウトドア 足 犬 裏起毛 おしゃれ 大きいサイズ おたふく 大きい カペルミュール 可愛い かわいい カブ 加圧 介護メンズ 介護 キッズ 着圧 ディゴラ 黒 車椅子 クール 日焼け防止 雨よけ コンプレッション こども 子供用 コスプレ"},
        "ブーツカフス": {"ctname": "オークション > スポーツ、レジャー > スポーツウエア > 女性用 > インナーウエア > タイツ", "y_ct": "2084246668", "sex": "0",
                   "male": "", "female": "", "wowma_catid": "450404",
                   "wowma_catname": "バッグ・財布・ファッション小物>ファッション小物>カフス・カフリンクス", "qoo_catid": "300002370",
                   "qoo_catname": "メンズバッグ・シューズ・小物_メンズ小物_カフス・タイピン", "s_keyword": "ファー"},
        "テーピングサポーター": {"ctname": "オークション > ビューティー、ヘルスケア > 健康用品、健康器具 > サポーター > その他", "y_ct": "2084216486", "sex": "0",
                       "male": "", "female": "", "wowma_catid": "471214",
                       "wowma_catname": "ビューティ・コスメ>メイク道具・ケアグッズ>ボディマッサージグッズ", "qoo_catid": "320001859",
                       "qoo_catname": "ダイエット・矯正_シェイプアップ・ダイエットグッズ_エクササイズグッズ",
                       "s_keyword": "足首 膝 ふくらはぎ 手首用 太もも 肘 足首用 指 fixfree プロフィッツ 肩 ふくらはぎ用 2枚組 足首かる mcdavid 中山式 外反母趾 内反小趾 左足用 22.5 25cm 1枚入 左右兼用 2枚入"},
        "ファランジリング": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > 指輪 > その他", "y_ct": "2084005435", "sex": "0",
                     "male": "", "female": "", "wowma_catid": "3004", "wowma_catname": "アクセサリー・ジュエリー>イヤリング",
                     "qoo_catid": "320001455", "qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_イヤリング",
                     "s_keyword": "レディース 黒 シルバー925 ステンレス 本 シルバー メンズ セット はじめての"},
        "レイヤーリング": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > 指輪 > その他", "y_ct": "2084005435", "sex": "0",
                    "male": "", "female": "", "wowma_catid": "3004", "wowma_catname": "アクセサリー・ジュエリー>イヤリング",
                    "qoo_catid": "320001455", "qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_イヤリング",
                    "s_keyword": "ファランジリング レディース 黒 シルバー925 ステンレス 本 シルバー メンズ セット"},
        "リング": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > 指輪 > その他", "y_ct": "2084005435", "sex": "0", "male": "",
                "female": "", "wowma_catid": "3004", "wowma_catname": "アクセサリー・ジュエリー>イヤリング", "qoo_catid": "320001455",
                "qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_イヤリング",
                "s_keyword": "フィット アドベンチャー ライト ノート ゲージ ファイル メンズ iphone12 ケース 付き ピアス マット ダウンロード版 セット レッグバンド コン アドベンチャー2 バンド ソフト スマホ 三脚 クリップ 18インチ led 卓上 neewer スタンド付き スイッチ b5 a5 a4 b6 a6 かわいい ノート用リムーバー キャラクター 方眼 日本製 正確 ゲージ棒 ゲージバンド 明光舎 usサイズ 平打ち 指輪 2穴 30穴 4穴 リヒトラブ シルバー"},
        "クリスマス　飾り": {"ctname": "オークション > ホビー、カルチャー > ハンドクラフト、手工芸 > 裁縫、刺繍 > 完成品 > その他", "y_ct": "2084240874", "sex": "0",
                     "male": "", "female": "", "wowma_catid": "54090501",
                     "wowma_catname": "日用品・文房具・手芸用品>手芸・クラフト・生地>クラフト>その他クラフト", "qoo_catid": "300000524",
                     "qoo_catname": "日用品雑貨_手芸・裁縫_その他",
                     "s_keyword": "クリスマス 飾り 置物 ライト ボール バルーン 屋外 飾り付け 木 壁 lua citron 風船 コンフェッティ パーティ 誕生日 バースデー お祝い 結婚式 二次会 ブラック クリスマス飾りつけ クリスマスつりー飾り クリスマスの飾り winomo 光ファイバー ファイバーツリー 三色 装飾led 雰囲気作りライト プレゼント パーティ飾りライト クリスマス飾り led"},
        "飾り": {"ctname": "オークション > ホビー、カルチャー > ハンドクラフト、手工芸 > 裁縫、刺繍 > 完成品 > その他", "y_ct": "2084240874", "sex": "0",
               "male": "", "female": "", "wowma_catid": "54090501",
               "wowma_catname": "日用品・文房具・手芸用品>手芸・クラフト・生地>クラフト>その他クラフト", "qoo_catid": "300000524",
               "qoo_catname": "日用品雑貨_手芸・裁縫_その他",
               "s_keyword": "誕生日 付け 男の子 女の子 大人 シンプル 1歳 おしゃれ マリオ 棚 ウォールシェルフ ガラス 木製 壁掛け スリム 賃貸 白 5歳 3歳 4歳 6歳 2歳 マイクラ 10歳 7歳 簡単 ガーランド プリンセス 8歳 クリアバルーン 名入れ タペストリー  ミッキー ドナルド  台 付けセット バルーン 桜 ペーパーファン 花 黒 アクリル 模型 ミニ 長方形 円形 丸 五月人形 30"},
        "クリスマス　ガーランド": {"ctname": "オークション > ホビー、カルチャー > ハンドクラフト、手工芸 > 裁縫、刺繍 > 完成品 > その他", "y_ct": "2084240874",
                        "sex": "0", "male": "", "female": "", "wowma_catid": "54090501",
                        "wowma_catname": "日用品・文房具・手芸用品>手芸・クラフト・生地>クラフト>その他クラフト", "qoo_catid": "300000524",
                        "qoo_catname": "日用品雑貨_手芸・裁縫_その他", "s_keyword": "クリスマス ガーランド ゴールド"},
        "ガーランド": {"ctname": "オークション > ホビー、カルチャー > ハンドクラフト、手工芸 > 裁縫、刺繍 > 完成品 > その他", "y_ct": "2084240874", "sex": "0",
                  "male": "", "female": "", "wowma_catid": "54090501",
                  "wowma_catname": "日用品・文房具・手芸用品>手芸・クラフト・生地>クラフト>その他クラフト", "qoo_catid": "300000524",
                  "qoo_catname": "日用品雑貨_手芸・裁縫_その他",
                  "s_keyword": "誕生日 バースデー 結婚式 ハッピーバースデー おしゃれ happy birthday キャンプ フラッグ インテリア 男の子 女の子 シルバー シンプル マリオ 男 ピンク マイクラ ナチュラル 1歳 ペーパーファン 写真 風船 和装 ウェルカム 木製 セット ゴールド 恐竜 花 布 オシャレ タッセル ブルー シック 麻 黒 ライト led トリコロール テント アンティーク 屋外 １０ｍ フィギュア 青 アルファベット 赤ちゃん アウトドア 赤"},
        "靴下": {"ctname": "オークション > ファッション > ファッション小物 > 靴下 > 女性用", "y_ct": "2084214901", "sex": "1",
               "male": "2084214908", "female": "2084214901", "wowma_catid": "320601",
               "wowma_catname": "インナー・ルームウェア>メンズ靴下>5本指ソックス", "qoo_catid": "300000048",
               "qoo_catname": "下着・レッグウェア_靴下・レッグウェア_靴下",
               "s_keyword": "メンズ ビジネス くるぶし レディース 白 黒 キッズ 屋 スポーツ 厚手 おしゃれ 27-29cm ブランド 消臭 夏 29cm 5本指 薄手 夏用 綿100 28cm 脱げない 大きいサイズ かわいい キャラクター セット 可愛い 中学生 男子 スクール 女子 女の子 ワンポイント 学生 男の子 フォーマル ショート ハイソックス 綿 10足 クルー丈 ソックス タイツ ストッキング レディース レギンス 屋さんの 赤 赤ちゃん 犬"},
        "ソックス": {"ctname": "オークション > ファッション > ファッション小物 > 靴下 > 女性用", "y_ct": "2084214901", "sex": "1",
                 "male": "2084214908", "female": "2084214901", "wowma_catid": "320601",
                 "wowma_catname": "インナー・ルームウェア>メンズ靴下>5本指ソックス", "qoo_catid": "320000633",
                 "qoo_catname": "ホビー・コスプレ_コスプレ・変装・仮装_ソックス",
                 "s_keyword": "メンズ 野球 レディース サッカー box408 バンド ラベル スポーツ 白 くるぶし ゴルフ テニス ランニング ビジネス 黒 5本指 ネイビー ジュニア 赤 青 紺 バレーボール おしゃれ 子供 キッズ 滑り止め 3足組 バスケ 足袋 ハイ 女の子 リボン 底パイル 消防 自転車 タビオ ノンアイロン カワグチ アイロン ピンク アイロン不要 グレー ブルー アクティバイタル 厚手 アンクル インザペイント インナー 磯 犬"},
        "ニーハイ": {"ctname": "オークション > ファッション > ファッション小物 > 靴下 > 女性用", "y_ct": "2084214901", "sex": "0", "male": "",
                 "female": "2084214901", "wowma_catid": "320908", "wowma_catname": "インナー・ルームウェア>レディース靴下>ニーハイソックス",
                 "qoo_catid": "300000750", "qoo_catname": "シューズ_ブーツ・ブーティー_ニーハイ",
                 "s_keyword": "ソックス ストッキング ブーツ 黒 レディース 女の子 小学生 網タイツ 白 キッズ ゴルフ 大きいサイズ ベージュ 光沢 ピンク 着圧 コスプレ ピンヒール 厚底 黒エナメル エナメル 綿 コットン ライン 黒180d グレー 40デニール レース 19 かわいい 18 卒業式 日本製 ガーター 薔薇 大きい lサイズ 大きめ セット 青 メンズ リボン 安い 滑り止め 網 透けない 厚手 子ども タイツ 赤"},
        "コイン": {"ctname": "オークション > アンティーク、コレクション > 貨幣 > 硬貨 > 世界 > ヨーロッパ", "y_ct": "26750", "sex": "0", "male": "",
                "female": "", "wowma_catid": "290806", "wowma_catname": "おもちゃ・趣味>コレクション>コイン・紙幣",
                "qoo_catid": "300002165", "qoo_catname": "バッグ・雑貨_財布・ポーチ_コインケース",
                "s_keyword": "ケース メンズ レディース キーホルダー 事務 小銭入れ 小さい 革 chums ブランド 本革 人気 おしゃれ ホルダー 車 財布 コレクション 紙 収集 薄型 100円玉 透明 カウンター 自動 カウンターケース 日本製 手動 エンゲルス 100円 カール  トレー ドライバー がま口 かわいい ボックス型 小さめ シリコン ラバー うさぎ クリア 可愛い 子供 木製 ゴールド レザー 抗菌 アンティーク トレード 木 黒"},
        "クッション": {"ctname": "オークション > 住まい、インテリア > 家具、インテリア > インテリア小物 > クッション > 一般 > その他", "y_ct": "2084063564",
                  "sex": "0", "male": "", "female": "", "wowma_catid": "310304",
                  "wowma_catname": "インテリア・寝具>イス・チェア>クッションチェア", "qoo_catid": "320000485",
                  "qoo_catname": "ベビー・マタニティ_ベビー用セーフティグッズ_コーナークッション",
                  "s_keyword": "よぎぼー ファンデーション フロア 椅子 ファンデ カバー tirtir お尻が痛くならない 腰痛 補充ビーズ ヨギボー 特大 ミニ 余儀ぼー 日本製安い 首 nars 崩れない 人気 パフ 韓国 ハリアス missha be カバー力高い フロアーシート 両面テープ カッター 壁紙屋本舗 フロア用両面テープ 大理石 フロアマット 接着剤 6畳 背もたれ ひも付き 姿勢矯正 かわいい 低反発 子供 丸 分厚い ティルティル ミシャ キルカバー 45 60 x 60cm おしゃれ"},
        "カットソー": {"ctname": "オークション > ファッション > レディースファッション > カットソー > 長袖 > Mサイズ", "y_ct": "2084050495", "sex": "0",
                  "male": "", "female": "", "wowma_catid": "500706", "wowma_catname": "メンズファッション>トップス>カットソー",
                  "qoo_catid": "300002252", "qoo_catname": "レディースファッション_トップス_Tシャツ・カットソー",
                  "s_keyword": "長袖 レディース きれいめ ゆったり 大きいサイズ ハイネック 白 ボーダー 花柄 vネック 日本製  春 7分袖 ボートネック オフィス メンズ 厚手 ワッフル 4枚セット 大きい 可愛い かわいい 半袖 ブルー 春夏 パステルカラー 春物 黄色 vis 7分袖青 青 グリーン アローズ 赤 アシメ アイボリー アーバンリサーチ インナー 衣装 スーツにあう みんなの かたやまゆうこ nissen シャツ ブラウス 無地 無地調 柄 襟付き 襟"},
        "パスポートケース": {"ctname": "オークション > ファッション > ファッション小物 > その他", "y_ct": "44164", "sex": "0", "male": "",
                     "female": "", "wowma_catid": "450418", "wowma_catname": "バッグ・財布・ファッション小物>ファッション小物>パスポートケース",
                     "qoo_catid": "320001139", "qoo_catname": "バッグ・雑貨_財布・ポーチ_パスケース",
                     "s_keyword": "首下げ スキミング防止 かわいい リフィル 透明 本革 革 黒 軽量 防水 クリア ポシェット 可愛い 6穴 リフィル付 カード 手帳 赤富士 アウトドア 薄型 ウエスト ねーえ おしゃれ オシャレ オレンジ オーロラ 家計管理 家族 皮 韓国 家計 海外旅行 キャラクター 貴重品入れ 航空券 トラベル セキュリティ 便利グッズ 首掛け クリアポケット付き クリアポケット コンパクト 小型 子供 腰 小銭 国際免許 財布 サンワ サコッシュ"},
        "パスポートカバー": {"ctname": "オークション > ファッション > ファッション小物 > その他", "y_ct": "44164", "sex": "0", "male": "",
                     "female": "", "wowma_catid": "450418", "wowma_catname": "バッグ・財布・ファッション小物>ファッション小物>パスポートケース",
                     "qoo_catid": "320001139", "qoo_catname": "バッグ・雑貨_財布・ポーチ_パスケース",
                     "s_keyword": "透明 キャラクター クリア スキミング防止 革 アメリカ 首下げ ストラップ messi baảcelona 赤 インドネシア ドラえもん おしゃれ クレヨンしんちゃん 子ども ほぼにち ディスに 猫 富士山 本革 マリオ getwing パスポートケース セキュリティポーチ 軽量コンパクト ７ポケット ブランド 防水 パンダ ピンク gowell rfid 2冊 sorasion 家計管理 ケース クリアファイル リフィル 6枚 付き 通帳ケース"},
        "カーディガン": {"ctname": "オークション > ファッション > レディースファッション > カーディガン > Mサイズ", "y_ct": "2084064209", "sex": "1",
                   "male": "2084007052", "female": "2084064209", "wowma_catid": "501103",
                   "wowma_catname": "メンズファッション>学生服>スクールニット・カーディガン", "qoo_catid": "300003071",
                   "qoo_catname": "レディースファッション_トップス_カーディガン",
                   "s_keyword": "レディース 春 メンズ 学生 女子 大きいサイズ wego 春夏 ゆったり ロング ショート丈 オフィス 黒 春物 ビジネス 薄手 冬 夏 グリーン ベージュ 柄 4l 厚手 グレー ピンク 白 男子 緑 ドロップショルダー ドロップ 春夏パーカー 丸首 紫 赤 青 アイボリー 洗える 医療用 医療 インナー インディゴ イタリア 市松模様 医療事務 ウィゴー ウール キッズ エスニック 襟付き 韓国"},
        "知育玩具": {"ctname": "オークション > おもちゃ、ゲーム > 知育玩具 > その他", "y_ct": "2084045581", "sex": "0", "male": "", "female": "",
                 "wowma_catid": "292001", "wowma_catname": "おもちゃ・趣味>ボードゲーム>その他ボードゲーム", "qoo_catid": "300000462",
                 "qoo_catname": "おもちゃ・知育_知育教材_その他",
                 "s_keyword": "1歳 0歳 3歳 小学生 2歳 犬 5歳 6歳 きのおもちゃ モンテッソーリ 木製 1歳半 つみき 女の子 楽器 赤ちゃん プーさん 指先 絵本 ボール ボール落とし おしゃれ 男の子 タブレット 日本製 音楽 人気 小学生高学年 低学年 パズル ドローン 500円 迷路 セール 2歳から 言葉カード わらべきみかの あいうえおカード にぎる お風呂 2歳児 おやつ 難しい ノーズワーク レベル フード ニーナ 留守番 カメラ クモン"},
        "ガウチョパンツ": {"ctname": "オークション > ファッション > レディースファッション > パンツ、スラックス > Mサイズ", "y_ct": "2084224590", "sex": "0",
                    "male": "", "female": "", "wowma_catid": "511004", "wowma_catname": "レディースファッション>パンツ>ガウチョ・スカーチョ",
                    "qoo_catid": "300002763", "qoo_catname": "レディースファッション_パンツ_その他",
                    "s_keyword": "レディース 春 大きいサイズ 春夏 夏 7分丈 七分丈 黒 フォーマル 冬  メンズ キッズ 女の子 デニム 白 v系 ネイビー 袴 ピンク 大きい ベージュ 春仕事 大きいサイズデニム デニム短め 赤 麻 足長 アス 青 インナー ウエストゴム 裏起毛 柄 エスニック おおきいサイズ おしゃれ オフィス 男の子 韓国 型紙 可愛い カーキ 切り替え 送料無料 透け感 華やか 花柄総レース ワイドパンツ スカーチョ スカンツ レースパンツ"},
        "ワイドパンツ": {"ctname": "オークション > ファッション > レディースファッション > パンツ、スラックス > Mサイズ", "y_ct": "2084224590", "sex": "0",
                   "male": "", "female": "", "wowma_catid": "511018", "wowma_catname": "レディースファッション>パンツ>ワイドパンツ",
                   "qoo_catid": "300002763", "qoo_catname": "レディースファッション_パンツ_その他",
                   "s_keyword": "レディース 春夏 春 大きいサイズ デニム 夏 フォーマル 白 冬 黒 メンズ 緑 チェック  スーツ 春夏大きいサイズ 通勤 低身長 オフィス 春夏レース 柄 ガウチョパンツ ゆったり 楽ちん ll-5l 8分丈 ブラック b062 セール 大きいサイズ夏 trtro ジーンズ デニムパンツ ジーパン ハイウエスト ゴム デニム白 卒業式 入学式 セットアップ 麻 赤 厚手 青 秋冬 アシンメトリー インナー ウエストゴム 裏起毛 運動 薄手"},
        "かんざし": {"ctname": "オークション > ファッション > 女性和服、着物 > かんざし", "y_ct": "2084048833", "sex": "0", "male": "",
                 "female": "", "wowma_catid": "51120401", "wowma_catname": "レディースファッション>和装・和服>和装小物>かんざし",
                 "qoo_catid": "300000125", "qoo_catname": "バッグ・雑貨_ヘアアクセサリー_ヘアピン",
                 "s_keyword": "和装 簪 一本 普段使い パール 一本挿し パーツ シンプル 留袖 結婚式 バチ 黒留袖 べっこう 卒業式 桜 バチ型 簪子 金属 蝶々 木製 一本差し コーム 普段使いシンプル シルバー 洋装 赤 洋服 べっ甲 長い セット とんぼ玉 皿付き ネジ式 アルミ 木 ハンドメイド パール１本 着物 夜会巻き 揺れる 青 アンティーク アニメ アジアン アクリル 飴 うさぎ 梅 漆 うどん"},
        "髪飾り": {"ctname": "オークション > ファッション > 女性和服、着物 > かんざし", "y_ct": "2084048833", "sex": "0", "male": "",
                "female": "", "wowma_catid": "34011335", "wowma_catname": "キッズベビー・マタニティ>キッズ>着物・浴衣・和小物（キッズ）>髪飾り",
                "qoo_catid": "300000125", "qoo_catname": "バッグ・雑貨_ヘアアクセサリー_ヘアピン",
                "s_keyword": "卒業式 パール リボン ドライフラワー 成人式 振袖 袴 人気の成人式 ランキング 小学生 ハーフアップ 赤 水引 バレッタ ピン 着物 パールコーム コーム ゴールド 和装 花 クリップ 子供 白 レース 黒 青 かすみ草 ピンク hanaspeak 霞草 人気 つまみ細工 オレンジ 紫 金 小さめ 袴用 ショートヘア 水引き 紐 緑 赤ちゃん あじさい 青系 アンティーク 色留袖 色打掛 イヤリング いちご"},
        "紐パン": {"ctname": "オークション > ファッション > レディースファッション > ナイトウエア、パジャマ", "y_ct": "2084053160", "sex": "0", "male": "",
                "female": "", "wowma_catid": "32070201", "wowma_catname": "インナー・ルームウェア>レディースインナー>ショーツ>Tバック・タンガ",
                "qoo_catid": "300000030", "qoo_catname": "下着・レッグウェア_ショーツ_ショーツ",
                "s_keyword": "ブラセット tバック ツ レディース 大きいサイズ メンズ 上下セット 下着 セット 可愛い 黒 c75 リリカルフラワー eカップ b80 穴あき サテン 綿 上下 かわいい セクシーでかいサイズ 穴 女装 竿 白 穴開き 赤 苺 男の娘 男 オープンクロッチ おおきいサイズ 極小 クロッチ 透け ほどける コスプレ 子供 股開き 高校生 コットン 光沢 シルク シースルー ショーツ 縞々 縞 スキャンティ ストレッチ 小さいサイズ"},
        "縞パン": {"ctname": "オークション > ファッション > レディースファッション > ナイトウエア、パジャマ", "y_ct": "2084053160", "sex": "0", "male": "",
                "female": "", "wowma_catid": "32070201", "wowma_catname": "インナー・ルームウェア>レディースインナー>ショーツ>Tバック・タンガ",
                "qoo_catid": "300000030", "qoo_catname": "下着・レッグウェア_ショーツ_ショーツ",
                "s_keyword": "セット ブラ レディース ローライズ 男の娘 水色 メンズ 大きいサイズ 女児 青 穴あき 小さい 大きい ロリパン フルバック  綿パン パンティー スキャンティー ショーツ 萌え ロリ おとこの娘 キッズ キューティーズ クロッチ コットン 子供 子供用 サテン 白黒 スポブラ つ 縞ブラ は正義 紐 フィギュア 本 緑 水着 綿 グリーン 上下 ビキニ ピンク ポリウレタン av dvd sサイズ 110 100"},
        "スカート": {"ctname": "オークション > ファッション > レディースファッション > スカート > ロングスカート > その他", "y_ct": "2084007175", "sex": "0",
                 "male": "", "female": "", "wowma_catid": "402311", "wowma_catname": "スポーツ・アウトドア>スポーツウェア>スポーツスカート",
                 "qoo_catid": "300002247", "qoo_catname": "レディースファッション_スーツ_スカートスーツ",
                 "s_keyword": "ハンガー レディース 春 ベルト 膝丈 ロング ギンガムチェック 省スペース 跡がつかない 連結 白 プラスチック 日本製 木製 ピンク 5本 きれいめ ゴルフ 大きいサイズ ミニ デニム 40代 きれいめゴム 春夏 可愛い マーメイド レース ベージュ チェック blk ライクパンツ ドット 学生 ゴム ベルト付き 細い 学生服 長い オリーブ 子ども ウエストゴム フレア タイト 黒 aライン プリーツ ライク セール ティアード キッズ"},
        "ニットキャップ": {"ctname": "オークション > ファッション > ファッション小物 > 帽子 > 女性用 > ワッチキャップ、ニットキャップ", "y_ct": "2084006693",
                    "sex": "0", "male": "", "female": "", "wowma_catid": "450711",
                    "wowma_catname": "バッグ・財布・ファッション小物>帽子>ニット帽", "qoo_catid": "300002173",
                    "qoo_catname": "バッグ・雑貨_帽子_ニット帽",
                    "s_keyword": "メンズ 夏 レディース 大きいサイズ コットン つば付き 夏用 薄手 赤 puma 春 大きい 白 ツバ ネイビー 耳あて チャンピオン 釣り 大きめ 浅め 青 アクリル 編み物 麻 アウトドア アウトドアブランド ニット帽春夏 ビーニー 医療用帽子 抗がん剤 サマーニット ガーゼ生地 綿 柔らかい 通気性 男女兼用 ウール エスニック オレンジ オールシーズン おしゃれ かわいい カーキ カシミア キッズ キャラクター スキー 黒 クリーム 子供"},
        "エコバッグ": {"ctname": "オークション > ファッション > 男女兼用バッグ > エコバッグ", "y_ct": "2084233235", "sex": "0", "male": "",
                  "female": "", "wowma_catid": "450304", "wowma_catname": "バッグ・財布・ファッション小物>バッグ>エコバッグ",
                  "qoo_catid": "300002171", "qoo_catname": "バッグ・雑貨_バッグ_エコバッグ",
                  "s_keyword": "大容量 折りたたみ おしゃれ コンパクト しゅぱっと 保冷 マリメッコ キャラクター 丈夫 軽量 ファスナー 防水 マチ付き 人気 メンズ ファスナー付き ブランド オシャレ デザイナーズ お洒落 極小 小さい カラビナ 肩掛け マチ m s l シュパット lサイズ リュック レジカゴ対応 折り畳み レジかごバッグ 正規品 馬 赤 ミニ 花柄 ロゴ ギフト 小さめ 大きめ 男の子 安い 美術館 9800円 洗える アウトドア アニメ"},
        "バルーンアート": {"ctname": "オークション > おもちゃ、ゲーム > 手品、パーティグッズ > パーティグッズ > その他", "y_ct": "2084059858", "sex": "0",
                    "male": "", "female": "", "wowma_catid": "290801", "wowma_catname": "おもちゃ・趣味>コレクション>その他コレクション",
                    "qoo_catid": "300000702", "qoo_catname": "ホビー・コスプレ_パーティー・イベント用品_その他",
                    "s_keyword": "風船 割れにくい ポンプ 空気入れ セット メタリック 本 誕生日 キャラクター クオラテックス ハート ピンク 黒 卒業式 ポンプ付き 電動 260 初心者 赤 アーチ アレンジメント 赤ちゃん 青 インテリア 犬 ウェディング エプロン お祝い 大きい 開店祝い 感謝 かわいい 記念日 黄色 キット 機械 結婚式 結婚祝い 国産 サッカー 白 シャンパン 周年 出産 シール スタンド 数字 卒業 卒園式 誕生日プレゼント"},
        "キャスケット": {"ctname": "オークション > ファッション > ファッション小物 > 帽子 > 女性用 > キャスケット", "y_ct": "2084243504", "sex": "0",
                   "male": "", "female": "", "wowma_catid": "34011102",
                   "wowma_catname": "キッズベビー・マタニティ>キッズ>帽子（キッズ）>キャスケット", "qoo_catid": "300002175",
                   "qoo_catname": "バッグ・雑貨_帽子_ハンチング・キャスケット",
                   "s_keyword": "レディース 春夏 メンズ 夏 大きいサイズ 帽子 ca4la 大きめ uv 春夏小さい 医療用 春夏大きいサイズ 春夏安い 赤 ニット つばなし 人気 夏用 春 ハンチング 白 夏大きいサイズ レザー 60cm メッシュ 大きいサイズ春夏 65cm ベージュ 62 防寒 折りたたみ 黒 青 麻 洗える アウトドア アナグラム 赤ちゃん あご紐 アクア 飲食店 医療用帽子 医療 イギリス イタリア イロドリ ウォバッシュ 腕時計 ウィッグ 薄手"},
        "帽子": {"ctname": "オークション > ファッション > ファッション小物 > 帽子 > 女性用 > その他", "y_ct": "2084006690", "sex": "1",
               "male": "2084006684", "female": "2084006690", "wowma_catid": "450701",
               "wowma_catname": "バッグ・財布・ファッション小物>帽子>その他帽子", "qoo_catid": "300002172", "qoo_catname": "バッグ・雑貨_帽子_キャップ",
               "s_keyword": "メンズ レディース 春夏 大きいサイズ 収納 掛け 夏用 春 かけ キャップ 夏 おしゃれ 深め メッシュ 65cm uv 春夏大きいサイズ つば広め キャスケット 春夏小さいサイズ 春夏日除け 医療 大きめ 日焼け防止 ハット バケットハット 麦わら 吊り下げ 収納ケース 収納ボックス 壁掛け 壁 ハンガー ドア スタンド フック 突っ張り棒 マグネット 傷つけない 夏用ハット 大きい 日本製 サファリハット 夏用ゴルフ メッシュミズノ かけるやつ 賃貸 子供 キッズ アウトドア"},
        "ショートパンツ": {"ctname": "オークション > ファッション > レディースファッション > ショートパンツ > Mサイズ", "y_ct": "2084224595", "sex": "0",
                    "male": "", "female": "", "wowma_catid": "511008", "wowma_catname": "レディースファッション>パンツ>ショートパンツ",
                    "qoo_catid": "300002760", "qoo_catname": "レディースファッション_パンツ_ショート・ハーフパンツ",
                    "s_keyword": "レディース メンズ レディース スポーツ デニム ルームウェア ランニング 大きいサイズ 水着 テニス 短め トレーニング 白 ポケット 綿 スパッツ 柄 キッズ 黒 ハイウエスト グレー ゴム ジュニア ガールズ グリーン ヒートギア ボーイズ 赤 穴あき アウトドア 麻 青 アニマル インナー 一体型 インナー付き インナーなし 衣装 運動 薄手 ウィゴー ウエストゴム エナメル エッチ えろ 女の子 おおきいサイズ 男の子 オープンクロッチ 140"},
        "ホットパンツ": {"ctname": "オークション > スポーツ、レジャー > スポーツ別 > バレーボール > ウエア > 女性用 > パンツ", "y_ct": "2084063029", "sex": "0",
                   "male": "", "female": "", "wowma_catid": "511001", "wowma_catname": "レディースファッション>パンツ>その他パンツ",
                   "qoo_catid": "300002760", "qoo_catname": "レディースファッション_パンツ_ショート・ハーフパンツ",
                   "s_keyword": "レディース 女装 デニム メンズ 大きいサイズ ローライズ 白 ヨガ 黒 おしゃれ ミニ ジッパー ダメージ キッズ ストレッチ 穴 穴開き 青 赤 衣装 インナー エナメル えろ 女の子 男 男の娘 オールインワン 大きい ダンス レザー 透け透け 子供 光沢 こども 股割れ サテン サスペンダー サロペット シルバー 小学生 レース スポーツ スカート スウェット 薄 セットアップ タイト 小さいサイズ 中出し チャック"},
        "ブローチ": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ネックレス、ペンダント > カラーストーン > その他", "y_ct": "2084042513",
                 "sex": "0", "male": "", "female": "", "wowma_catid": "301501",
                 "wowma_catname": "アクセサリー・ジュエリー>ブローチ・コサージュ>その他ブローチ・コサージュ", "qoo_catid": "320001458",
                 "qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_ブローチ",
                 "s_keyword": "卒業式 入学式 パール ピン 花 真珠 大きめ スーツ ママ 人気 子ども シンプル シルバー フォーマル ゴールド サークル リボン 桜 子供用 子供 25mm 30mm 15mm 20mm 日本製 回転式 台座 ハンドメイド パーツ クローバー ブラック バイオリン スワロフスキー動物 アナグラム 本物 アンティーク ピンク 花輪 布 花瓶 黄色 kawaii ミキモト 入園式 冠婚葬祭 冠 婚 葬祭 薔薇 あこや"},
        "トートバッグ": {"ctname": "オークション > ファッション > レディースバッグ > トートバッグ > その他", "y_ct": "2084050995", "sex": "1",
                   "male": "2084008301", "female": "2084050995", "wowma_catid": "450310",
                   "wowma_catname": "バッグ・財布・ファッション小物>バッグ>トートバッグ", "qoo_catid": "300000116",
                   "qoo_catname": "バッグ・雑貨_バッグ_トートバッグ",
                   "s_keyword": "レディース メンズ 大容量 キャンバス エルエルビーン マリメッコ a4 小さめ 人気 大学生 ブランド 通勤 ビジネス カジュアル ゴルフ 布 マザーズバック ファスナー付き ナイロン 防水 アウトドア キャラクター 肩掛け 無地 黒 ミニ スモール ラージ ミディアム ジップ ロングハンドル ショルダー l グローサリー 大きめ ファスナー デニム エクストララージ レザー ベージュ グリーン 赤 ピンク 70周年 縦型 ルートート furla 縦 軽量 横型"},
        "トート バッグ": {"ctname": "オークション > ファッション > レディースバッグ > トートバッグ > その他", "y_ct": "2084050995", "sex": "1",
                    "male": "2084008301", "female": "2084050995", "wowma_catid": "450310",
                    "wowma_catname": "バッグ・財布・ファッション小物>バッグ>トートバッグ", "qoo_catid": "300000116",
                    "qoo_catname": "バッグ・雑貨_バッグ_トートバッグ",
                    "s_keyword": "キャンバス 丈夫 大きい 男性 ポケット いっぱい 大 容量 容量ナイロン おすすめ 学校 メンズ インバッグ 大きめ ブランド レディース 人気 50 代 アフタヌーン 縦 型 大学生 布 洗える アマゾン アニメ トートバッグ 犬 イニシャル イラスト インナーバッグ 犬柄 イケア インナー いちご うちわ うちわ入る 薄手 うさぎ 内ポケット 宇宙 内ポケット付き 薄型 海 ウィゴー エルエルビーン エコバッグ 柄 エックスガール エナメル"},
        "手提げ": {"ctname": "オークション > ファッション > レディースバッグ > トートバッグ > その他", "y_ct": "2084050995", "sex": "1",
                "male": "2084008301", "female": "2084050995", "wowma_catid": "450310",
                "wowma_catname": "バッグ・財布・ファッション小物>バッグ>トートバッグ", "qoo_catid": "300000116",
                "qoo_catname": "バッグ・雑貨_バッグ_トートバッグ",
                "s_keyword": "袋 小学生 男の子 大きめ マチあり ナイロン a4サイズ セット 30 40  小さめ 金庫 lysmics a4 小型 a5 鍵付き sサイズ ミニ b5 耐火 女の子 すみっこ 防水 マチ キルティング 手土産 お菓子 袋付き ビニール ギフト 人気 紙 バッグ メンズ レディース  おしゃれ ニューヨーク 個包装 千円以内 京都 山口県 マチ付き 特大 かわいい プレゼント ビニールバッグ 白 厚手"},
        "バッグ": {"ctname": "オークション > ファッション > レディースバッグ > ハンドバッグ > 皮革製 > その他", "y_ct": "2084051017", "sex": "1",
                "male": "2084008300", "female": "2084051017", "wowma_catid": "340602",
                "wowma_catname": "キッズベビー・マタニティ>マタニティ・ママ>マザーバッグ", "qoo_catid": "300002371",
                "qoo_catname": "バッグ・雑貨_キャリーバッグ_バッグインバッグ",
                "s_keyword": "レディース イン メンズ ハンガー 収納 リュック チャーム 大容量 小さめ ショルダー トート 人気 a4 通勤 ブランド 軽量  縦 リヒトラブ 縦型 大きめ ななめ掛け ビジネス カジュアル テーブルフック クローゼット おしゃれ ハンガーホルダー クリッパ 10kg デスク カラビナ テーブル 吊り下げ 収納ボックス 収納袋 不織布 収納ケース フック 仕切り 山崎実業 タテ型 ワンズショップ リュック用 自立 bag in ナイロン チェーン 金具"},
        "ガラスフィルム": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール", "y_ct": "2084299106",
                    "sex": "0", "male": "", "female": "", "wowma_catid": "410518",
                    "wowma_catname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>液晶保護フィルム", "qoo_catid": "320002243",
                    "qoo_catname": "スマホケース・保護フィルム_保護フィルム_多機種対応保護フィルム",
                    "s_keyword": "iphone13  ブルーライトカット 覗き見防止 さらさら アンチグレア ブルーライト カメラ のぞき見防止 nimaso 全面 iphone12 指紋防止 iphone se3 日本製 白 ゴリラ 窓 iphone11 13 12 se ミラー おしゃれ 飛散防止 透明 目隠しシート 目隠し ダークブルー グラデーション ステンドグラス風 キャラクター 侍  覗き見 pro mini 13promax 13プロ 13ミニ 13インチ 12pro 12mini 12promax 12ミニ 12.9 12インチ se2 接着剤 sense6"},
        "クッキングシート": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > その他", "y_ct": "24462", "sex": "0", "male": "", "female": "",
                     "wowma_catid": "350609", "wowma_catname": "キッチン・食器・調理>キッチン用品・キッチン雑貨>クッキングシート",
                     "qoo_catid": "320000841", "qoo_catname": "キッチン用品_キッチン消耗品_クッキングシート",
                     "s_keyword": "業務用 繰り返し 無漂白 クックパー フライパン用 ラクック 33cm 茶色 柄 50m 33 100 40cm 三菱 パン 繰り返し使える シリコン 日本製 ケーキ 12cm 国産 グラシン ノンシリコン アルファミック 25cm mサイズ lサイズ m 20cm アルミシート 柄付き レシピ アルミ 旭化成 厚手 穴あき 洗える 油 アムウェイ アダチ 揚げ物 安全 色つき 板 器 薄い 英字 円形 エコ 英字新聞"},
        "クッキングマット": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > その他", "y_ct": "24462", "sex": "0", "male": "", "female": "",
                     "wowma_catid": "350609", "wowma_catname": "キッチン・食器・調理>キッチン用品・キッチン雑貨>クッキングシート",
                     "qoo_catid": "320000841", "qoo_catname": "キッチン用品_キッチン消耗品_クッキングシート",
                     "s_keyword": "シリコン 日本製 パン セット 大きいサイズ オーブン くっつかない 小さめ 40 60cm 厚 耐熱 70 50 厚手 板 大きい 目盛付き 繰り返し クッキー こねこね 下村企販 パンマット パンこね台 パン作り キャンバス地 18777  小さい 小 食洗機 スケーター そば 正方形 透明 富澤 まな板 大理石まな板 マカロン 目盛 木製 大 ピンク limnuo 25cm 60"},
        "ベルト": {"ctname": "オークション > ファッション > ファッション小物 > ベルト > 男性用 > 皮革、レザー > 黒", "y_ct": "2084214919", "sex": "1",
                "male": "2084214919", "female": "2084214915", "wowma_catid": "5826", "wowma_catname": "腕時計>腕時計用ベルト・バンド",
                "qoo_catid": "300000124", "qoo_catname": "バッグ・雑貨_ベルト_レディースベルト",
                "s_keyword": "メンズ 大きいサイズ カジュアル ビジネス 穴なし おおきいサイズ 本革 ブランド おしゃれ 革  レディース サンダー ポーチ 穴あけ 学生 男子 太め ゴム スーツ 細い 白 太 電動 替え 卓上 リョービ エアー アタッチメント 100mm 915mm 充電式 150 オートロック 無段階調整 安い 作業用 小型 スマホ レザー ミリタリー 防水 大きい 長い 日本製 ブラウン 幅広 穴あけポンチ 楕円 5mm 時計"},
        "ハンガー": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > ハンガー > 一般", "y_ct": "2084061605", "sex": "0", "male": "",
                 "female": "", "wowma_catid": "31140806", "wowma_catname": "インテリア・寝具>収納家具>ラック>ハンガーラック",
                 "qoo_catid": "320000832", "qoo_catname": "キッチン用品_キッチン雑貨_タオルハンガー",
                 "s_keyword": "スチームアイロン にかけたまま コードレス 日本製 アイリス 人気 にかけたまま日立 除菌 ラック スリム 幅30 幅50 幅40 白 幅60 キャスター おしゃれ 棚付き 頑丈 カバー付き 業務用 大容量 2段 ダブル 高さ180cm 突っ張り 押し入れ カバー 60cm 木製 オシャレ お洒落 キャスター付き 黒 収納 衣類 ワードローブ すべらない 滑らない 10本 30本 50本 100本 ズボン スカート ピンク バスタオル  マグネット ステンレス スタンド"},
        "キャミソール": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > キャミソール > Mサイズ", "y_ct": "2084053124",
                   "sex": "0", "male": "", "female": "", "wowma_catid": "510806",
                   "wowma_catname": "レディースファッション>トップス>キャミソール", "qoo_catid": "300000012",
                   "qoo_catname": "レディースファッション_トップス_キャミソール・タンクトップ",
                   "s_keyword": "レディース 下着 カップ付き ワンピース レース 授乳 セット ロング 白 大きいサイズ 綿100 人気 汗取り 140 130 120 夏 ジュニア 可愛い 中学生 ミニ インナー 黒 タイト サテン ストラップオープン 綿 ベルメゾン ll セットアップ セットスカイブルー 安い ロングワンピース コットン ロング丈 透けない かわいい 子供 カップ無し 白セット フリル 青 汗取りパッド付き 汗 アウター 厚手 アジャスター付き アジャスター 赤 いちご"},
        "タンクトップ": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > キャミソール > Mサイズ", "y_ct": "2084053124",
                   "sex": "0", "male": "", "female": "", "wowma_catid": "510809",
                   "wowma_catname": "レディースファッション>トップス>タンクトップ", "qoo_catid": "300000012",
                   "qoo_catname": "レディースファッション_トップス_キャミソール・タンクトップ",
                   "s_keyword": "メンズ トレーニング インナー 大きいサイズ  黒 筋トレ 白 レディース 綿100 セット  スポーツ カップ付き レース ゴールドジム プロクラブ 無地 大きい 厚手 トレーニングウェア ua ドライ 綿 5l 脇 わきあり 綿100ハイネック 綿100ロング丈 3枚 ヘビーウェイト m s 赤 汗取り アビレックス アンダーシャツ キッズ 男の子 ロング 犬 160 女の子 薄手 海 ウェア 後ろクロス 薄い ウルフ 運動 柄"},
        "バレッタ": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > バレッタ", "y_ct": "2084005385", "sex": "0",
                 "male": "", "female": "", "wowma_catid": "301608",
                 "wowma_catname": "アクセサリー・ジュエリー>ヘアアクセサリー>バレッタ・ヘアクリップ", "qoo_catid": "300003087",
                 "qoo_catname": "バッグ・雑貨_ヘアアクセサリー_ヘアクリップ",
                 "s_keyword": "パール 大きめ おしゃれ 大人 リボン しっかり 黒 髪留め シンプル ヘアアクセサリー 小さめ 結婚式 入学式 シルバー 卒園式 セット ゴールド しっかりとまる 材料 ベッコウ 翌日 白 子供 卒業式 ピンク ネイビー 喪服 ミニ ネット 大 キラキラ シフォン 可愛い アンティーク 御洒落 べっこう シンプルパール 細い 花 木製 ネット付き 赤 青 アレクサンドル ドゥパリ ドゥ パリ 網 アーバンリサーチ 犬"},
        "クラッチバッグ": {"ctname": "オークション > ファッション > レディースバッグ > クラッチバッグ、パーティバッグ", "y_ct": "2084008347", "sex": "1",
                    "male": "2084008304", "female": "2084008347", "wowma_catid": "450305",
                    "wowma_catname": "バッグ・財布・ファッション小物>バッグ>クラッチバッグ", "qoo_catid": "300002167",
                    "qoo_catname": "バッグ・雑貨_バッグ_クラッチバッグ",
                    "s_keyword": "メンズ 結婚式 ブランド 本革 小さめ a4 ショルダー  レディース たけおきくち 大きめ カジュアル フォーマル 黒 卒業式 シルバー ネイビー ゴールド 二つ折り 赤 アローズ アニアリ 青 アンティーク 厚い 明日 アンブレラ イタリア イタリアンレザー ウルティマ 薄型 エナメル エピ エコバッグ 大きい おしゃれ 折りたたみ オラオラ オシャレ オフィス 革 冠婚葬祭 紙 かわいい カステルバジャック カラフル 肩掛け キャンバス キャバ 着物 キャメル"},
        "アームウォーマー": {"ctname": "オークション > スポーツ、レジャー > 自転車、サイクリング > ウエア > ウォーマー、カバー", "y_ct": "2084229858", "sex": "0",
                     "male": "", "female": "", "wowma_catid": "450403",
                     "wowma_catname": "バッグ・財布・ファッション小物>ファッション小物>アームウォーマー", "qoo_catid": "300002388",
                     "qoo_catname": "バッグ・雑貨_手袋_アームウォーマー",
                     "s_keyword": "レディース メンズ ロードバイク シルク 白 ニット レース ランニング 綿 uvカット 冬 冷感 オシャレ 夏 スポーツ 保温 自転車 夏用 サイクリング 防寒 日本製 絹屋 シルク100% ニット付き 綿100 赤 赤ちゃん 温かい 厚手 網 あったかい あったか 衣装 裏起毛 薄手 エンジ エナメル おしゃれ 大きいサイズ オレンジ 親指 韓国 カステリ 可愛い かわいい カシミヤ カイロ 介護 カシミア カラー"},
        "アームカバー": {"ctname": "オークション > スポーツ、レジャー > 自転車、サイクリング > ウエア > ウォーマー、カバー", "y_ct": "2084229858", "sex": "0",
                   "male": "", "female": "", "wowma_catid": "450403",
                   "wowma_catname": "バッグ・財布・ファッション小物>ファッション小物>アームウォーマー", "qoo_catid": "320001137",
                   "qoo_catname": "バッグ・雑貨_小物_アームカバー",
                   "s_keyword": "メンズ レディース fps uvカット cwx ゲーミング 冷感 レース 夏用 白 スポーツ 夏 ゴルフ 指かけ おしゃれ ショート 家事 綿 指掛け かわいい 指あり 指先まで ブラック 大きいサイズ roi ひんやり uv ロング 日焼け止め 日焼け止め防止 指 ベージュ 手首 黒 アイボリー ロリータ 事務 赤 青 厚手 アウトドア 赤ちゃん 足 入れ墨 入墨 いれずみ 医療 いかつい イラスト 医療用"},
        "ヘア飾り": {"ctname": "オークション > アクセサリー、時計 > ハンドメイド > アクセサリー（女性用） > ヘアアクセサリー", "y_ct": "2084240619", "sex": "0",
                 "male": "", "female": "", "wowma_catid": "301602",
                 "wowma_catname": "アクセサリー・ジュエリー>ヘアアクセサリー>その他ヘアアクセサリー", "qoo_catid": "300000127",
                 "qoo_catname": "バッグ・雑貨_ヘアアクセサリー_その他",
                 "s_keyword": "卒業式 子供 パール リボン 和装 花 ドライフラワー 結婚式 着物 発表会 赤ちゃん 赤 大人 おしゃれ 和 かすみ草 金箔 キラキラ クリップ 七五三 成人式 卒園式 チュールのみ 入学式 玉ねぎヘア 髪飾り 女の子 人気の和装 ランキング 真珠の 袴 紐 ひも へ和装 水引 リーフ ぐるぐる お呼ばれ 和装かんざし ゴールド ベビー パーティー"},
        "ニット帽": {"ctname": "オークション > ファッション > ファッション小物 > 帽子 > 女性用 > ワッチキャップ、ニットキャップ", "y_ct": "2084006693", "sex": "1",
                 "male": "2084006686", "female": "2084006693", "wowma_catid": "450711",
                 "wowma_catname": "バッグ・財布・ファッション小物>帽子>ニット帽", "qoo_catid": "300002173", "qoo_catname": "バッグ・雑貨_帽子_ニット帽",
                 "s_keyword": "子メンズ 夏 メンズ 夏用 子レディース 春夏 supreme 大きめ 浅め 大きいサイズ つば 麻 ブランド つば付き コットン 春 スノーボード 冬 日本製 夏用メンズ レディース 大きい 医療 子供 スポーツ スノボ スキー 子レディース夏用 ポンポン 白 医療用 薄手 子メンズ大きいサイズ 黒 ネイビー 青 ビーニー キッズ 赤 赤ちゃん アウトドア アニメ 医療用帽子 イスラム インディアン 犬柄 インディゴ 薄い ウィゴー 薄め"},
        "カフスボタン": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > カフス > その他", "y_ct": "2084062587", "sex": "0", "male": "",
                   "female": "", "wowma_catid": "450404", "wowma_catname": "バッグ・財布・ファッション小物>ファッション小物>カフス・カフリンクス",
                   "qoo_catid": "300002370", "qoo_catname": "メンズバッグ・シューズ・小物_メンズ小物_カフス・タイピン",
                   "s_keyword": "メンズ ネクタイピン セット おしゃれ 結婚式 ブランド おもしろ フォーマル 白 白蝶貝 セットカルティエ バイク 真珠 ネタ 黒 オシャレ メンズタイピンセット セットブランド 青 赤 アニメ アンティーク アンブレラ アメジスト アニマル アルファベット アオキ 犬 イニシャル イカリ 祝い 石 イーグル 馬 ウクライナ ウェッジウッド ウィンブルドン 映画 エヴァンゲリオン エンブレム エヴァ えんぴつ エジプト 面白い 音楽 オニキス オレンジ 牡羊座 音符 かわいい"},
        "サングラス": {"ctname": "オークション > ファッション > ファッション小物 > サングラス", "y_ct": "2084224828", "sex": "0", "male": "",
                  "female": "", "wowma_catid": "341007", "wowma_catname": "キッズベビー・マタニティ>子供用ファッション小物・雑貨>サングラス",
                  "qoo_catid": "300000128", "qoo_catname": "バッグ・雑貨_眼鏡・サングラス_サングラス",
                  "s_keyword": "メンズ レディース 偏光 運転用 スポーツ ケース おしゃれ ゴルフ ポリス 大きめ 野球 フロッグスキン ランニング レーダーロック uvカット ブランド 透明 スワンズ クリップオン swans 調光 運転 釣り 偏光レンズ メガネの上 昼夜兼用 眼鏡の上 日本製 レディース昼夜 度付き 大きいサイズ 昼夜兼用クリア クリップ ブラウン ハード 車用 収納 カラビナ ミリタリー 007 登坂広臣 中古 ブルー グラディエント メガネの上から 青レンズ 青 赤 赤レンズ アウトドア"},
        "コースター": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > アクセサリー > コースター > その他", "y_ct": "2084230300", "sex": "0",
                  "male": "", "female": "", "wowma_catid": "350610", "wowma_catname": "キッチン・食器・調理>キッチン用品・キッチン雑貨>コースター",
                  "qoo_catid": "320000808", "qoo_catname": "キッチン用品_キッチン雑貨_コースター",
                  "s_keyword": "おしゃれ 珪藻土 木製 シリコン 布 紙 かわいい コルク 木 北欧 オシャレ 日本製 吸水 大理石 黒 白 ブラック 2枚 四角 猫 大きめ 丸 花 寄木細工 5枚セット セット シリコンモールド 可愛い グレー キャラクター レース 布製 無地 和風 洗える 厚手 100枚 桜 和紙 鶴 紙製 ピンク 水色 厚い プリント 5mm ファイル アニメ アンティーク 青"},
        "ダイヤモンド": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ネックレス、ペンダント > ダイヤモンド > プラチナチェーン", "y_ct": "2084209778",
                   "sex": "0", "male": "", "female": "", "wowma_catid": "3017", "wowma_catname": "アクセサリー・ジュエリー>ペンダント",
                   "qoo_catid": "320001121", "qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_指輪",
                   "s_keyword": "アート キット スクエア スクエアビーズ bts 花 キーホルダー マスク 小さめ 日本製 大きめ 子供用 こども用 不織布 黒 夢グループ通販マスク  砥石 型マスク 面直し 3000 1000 150 sk11 1200 3000番 両面 焼結 四角ビーズ プリンセス 美女と野獣 アラジン アリエル ステンドグラス ピンク グレー 19cm 小さめサイズ ベージュ ホワイト 30 初心者 全面貼り 大きいサイズ 猫 小さいサイズ 大型 a2 キャラクター スクエアビーズのみ アニメ"},
        "アイマスク": {"ctname": "オークション > ビューティー、ヘルスケア > リラクゼーショングッズ > アイピロー", "y_ct": "2084047754", "sex": "0", "male": "",
                  "female": "", "wowma_catid": "471101", "wowma_catname": "ビューティ・コスメ>ボディケア>その他ボディケア",
                  "qoo_catid": "320001867", "qoo_catname": "ダイエット・矯正_矯正・マッサージ_美顔器",
                  "s_keyword": "睡眠用 めぐりずむ ホット 充電式 蒸気 かわいい おもしろ あずき シルク 日本製 遮光 耳掛け メンズ キャラクター 無香料 ゆず メグリズム ラベンダー めぐリズム めぐりズム 5枚 ローズ カモミール レンジ コードレス クール 繰り返し 可愛い 使い捨て 温冷 マッサージ 人気 洗える 猫 bluetooth 蒸気で もこもこ 動物 ねこ かわいい子供用 くま 面白い 睡眠 セット おもしろ鬼滅 パーティー 小豆 あずきのちから 電子レンジ アズキ"},
        "フラワーシャワー": {"ctname": "オークション > 花、園芸 > アレンジメント > 生花 > その他", "y_ct": "2084206879", "sex": "0", "male": "",
                     "female": "", "wowma_catid": "350602",
                     "wowma_catname": "キッチン・食器・調理>キッチン用品・キッチン雑貨>その他キッチン用品・キッチン雑貨", "qoo_catid": "320001881",
                     "qoo_catname": "ガーデニング・DIY・工具_花_プリザーブドフラワー", "s_keyword": ""},
        "コスチューム": {"ctname": "オークション > コミック、アニメグッズ > コスプレ衣装 > コミック、アニメ、ゲームキャラクター > アクセサリー、小物", "y_ct": "2084311489",
                   "sex": "0", "male": "", "female": "", "wowma_catid": "3409",
                   "wowma_catname": "キッズベビー・マタニティ>子供用コスチューム", "qoo_catid": "300002272",
                   "qoo_catname": "レディースファッション_和服・コスチューム_コスチューム",
                   "s_keyword": "ダッフィー  嵐  公式 結婚式 パーカー ウッディ 20周年 ピンク レインコート おとこの娘 タマトイズ 3l sm 大きいサイズ セット 穴あき 大きめ チャイナ ミニスカ ハイレグ ホットパンツ 女性 奴隷 ボンテージ 過激拘束具 スパイダーマン 大人 子供 キッズ ベビー レディース 一体 ハイクオリティ ol 男性 おもしろ 面白い 仮装 かわいい 大人用 メンズ 男 人気の ベビーランキング ボンデージ エナメル アニメ アイドル風 赤ずきん"},
        "ひざかけ": {"ctname": "オークション > スポーツ、レジャー > キャンプ、アウトドア用品 > その他", "y_ct": "2084005102", "sex": "0", "male": "",
                 "female": "", "wowma_catid": "311601", "wowma_catname": "インテリア・寝具>寝具>その他寝具", "qoo_catid": "320000022",
                 "qoo_catname": "寝具・ベッド・マットレス_毛布・ブランケット・タオルケット_ブランケット",
                 "s_keyword": "ひざ掛け 電気毛布 ブランケット 夏用 電気 かわいい 厚手 キャラクター おしゃれ 大判 膝掛け 小さめ 膝掛け電気毛布 日本製 北欧 小さい  夏 可愛い アウトドア 綿 10枚セット オフィス ブラック すみっこぐらし ガーゼ 春夏 オシャレ 車 usb  充電式 電池式 洗える 暖かい アニメ 温かい あったかい 赤 犬 いちご 今治 今治タオル インディアン 犬柄 市松 犬用 薄い うさぎ 薄手 羽毛"},
        "シェイパー": {"ctname": "オークション > スポーツ、レジャー > スポーツ別 > エクササイズ用品 > その他", "y_ct": "25178", "sex": "0", "male": "",
                  "female": "", "wowma_catid": "403807", "wowma_catname": "スポーツ・アウトドア>ヨガ・ピラティス>ウェア",
                  "qoo_catid": "320001855", "qoo_catname": "ダイエット・矯正_シェイプアップ・ダイエットグッズ_二の腕シェイパー", "s_keyword": ""},
        "ヘアアレンジ": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ヘアピン", "y_ct": "2084005386", "sex": "0",
                   "male": "", "female": "", "wowma_catid": "301602",
                   "wowma_catname": "アクセサリー・ジュエリー>ヘアアクセサリー>その他ヘアアクセサリー", "qoo_catid": "320001790",
                   "qoo_catname": "ヘア_スタイリング_ヘアアレンジブラシ",
                   "s_keyword": "グッズ アイテム 本 紐 おもちゃ 練習 マネキン スティック リボン ゴム お団子 子ども 子供 くるくる まとめ髪 シニヨン おだんご 小学生 ロング ボブ 初心者 簡単 メンズ 紐リボン 卒業式 成人式 ゴールド 白 袴 和風 玩具 人毛 布 こども ワイヤー アップ アクセサリー 編み込み 赤ちゃん ストレート カール両用 温度調節可能 やけど防止 時短 恒温で髪を傷めない 切断保護 しない ウィッグ ウォーター エクステ"},
        "充電器": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > バッテリー、充電器 > USB式充電器", "y_ct": "2084239197", "sex": "0",
                "male": "", "female": "", "wowma_catid": "410903",
                "wowma_catname": "スマホ・タブレット・モバイル通信>バッテリー・充電器>スマホ・タブレット用充電器", "qoo_catid": "320002033",
                "qoo_catname": "生活家電_電池_充電器",
                "s_keyword": "type-c iphone モバイルバッテリー anker 急速充電 usb エネループ セット 人気のiphone ランキング ケーブル 100w 65w 2ポート ワイヤレス 持ち運び 純正 急速 apple watch アンカー 2m iphone12 大容量 軽量 小型 コンセント ケーブル内蔵 ソーラー pd 一体型 3m usb-c usbc 単3 単4 セット12本 単一 cc85 13 c ピンク l字 1.5 短い あいふぉん アイフォン あんかー アダプター アンドロイド"},
        "なべつかみ": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > 食器 > その他", "y_ct": "2084005666", "sex": "0", "male": "",
                  "female": "", "wowma_catid": "350618", "wowma_catname": "キッチン・食器・調理>キッチン用品・キッチン雑貨>ミトン・鍋つかみ",
                  "qoo_catid": "320000799", "qoo_catname": "キッチン用品_キッチン雑貨_鍋つかみ",
                  "s_keyword": "鍋つかみ シリコン やっとこ 耐熱 かわいい おしゃれ ミトン 北欧 三角 キャンプ  300度 鍋掴み マグネット ミニ 磁石 小さめ 日本製 動物 耐熱ミトン 250 ピンク 小さい 5本指 おしゃれ三角 ハワイ オシャレ ワニ ハート 可愛い マリメッコ アニマル アウトドア 赤 アルミ 洗える 厚手 犬 イケア いぬ いちご 薄手 うさぎ ウマ娘 馬 牛 ナベツカミ エバニュー オーブン 大きめ おもしろ"},
        "鍋つかみ": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > 食器 > その他", "y_ct": "2084005666", "sex": "0", "male": "",
                 "female": "", "wowma_catid": "350618", "wowma_catname": "キッチン・食器・調理>キッチン用品・キッチン雑貨>ミトン・鍋つかみ",
                 "qoo_catid": "320000799", "qoo_catname": "キッチン用品_キッチン雑貨_鍋つかみ",
                 "s_keyword": "シリコン やっとこ 耐熱 かわいい おしゃれ ミトン 北欧 三角 キャンプ マグネット ミニ 磁石 小さめ 日本製 動物 ステンレス ヤットコ  300度 耐熱ミトン 250 ピンク 小さい 5本指 可愛い オシャレ マリメッコ 布 皮 北欧風 ストウブ ミナペルホネン アニマル アウトドア 赤 アルミ 洗える 厚手 熱くない アルミコーティング アメリカ 犬 イケア いぬ いちご 薄手 うさぎ エバニュー オーブン 大きめ"},
        "レザーケース": {"ctname": "オークション > ファッション > ファッション小物 > 名刺入れ、カードケース > 男性用", "y_ct": "2084246781", "sex": "0",
                   "male": "", "female": "", "wowma_catid": "450405",
                   "wowma_catname": "バッグ・財布・ファッション小物>ファッション小物>カードケース", "qoo_catid": "300002375",
                   "qoo_catname": "バッグ・雑貨_財布・ポーチ_名刺入れ・カードケース",
                   "s_keyword": "iphone12  純正 magsafe 手帳型 magsafe対応 ブラック ブルー ベルロイ グレー クロコ iphone13 赤 ミッドナイト グリーン ピンク iphone se 13pro 小物入れ 12 小物 12pro 13 ショルダー 12mini 本革 アップル ネイビー ミッドナイトブルー apple レッド 13promax ベージュ えあーぽっつ プロ あいほん13esr イヤホン ウィステリア 第三世代 pro アイフォン13 ケース お財布付き カード収納 財布型 red galaxy s20 ultra 5g scg03"},
        "カードケース": {"ctname": "オークション > ファッション > ファッション小物 > 名刺入れ、カードケース > 男性用", "y_ct": "2084246781", "sex": "0",
                   "male": "", "female": "", "wowma_catid": "450405",
                   "wowma_catname": "バッグ・財布・ファッション小物>ファッション小物>カードケース", "qoo_catid": "300002375",
                   "qoo_catname": "バッグ・雑貨_財布・ポーチ_名刺入れ・カードケース",
                   "s_keyword": "メンズ 大容量 薄型 ブランド  革 本革 レディース 人気 かわいい じゃばら スリム スキミング防止 透明 二つ折り スリムビニール 日本製 人気ブランド スキミング 猫 カード入れ トレカ 120枚 magsafe iphone 磁気シールド 純正 スタンド 白 13 pro シールド ファイル クリア キャラクター マグネット ドラゴンボール 首掛け リール 縦型 両面 縦 2枚 横 グレー キーリング ベージュ キーケース シルバー ピンク ヌメ"},
        "パスケース": {"ctname": "オークション > ファッション > ファッション小物 > 名刺入れ、カードケース > 男性用", "y_ct": "2084246781", "sex": "0",
                  "male": "", "female": "", "wowma_catid": "450417", "wowma_catname": "バッグ・財布・ファッション小物>ファッション小物>パスケース",
                  "qoo_catid": "320001139", "qoo_catname": "バッグ・雑貨_財布・ポーチ_パスケース", "s_keyword": ""},
        "懐中時計": {"ctname": "オークション > アクセサリー、時計 > 懐中時計 > 機械式 > 手巻き", "y_ct": "2084062956", "sex": "0", "male": "",
                 "female": "", "wowma_catid": "5819", "wowma_catname": "腕時計>懐中時計", "qoo_catid": "300000103",
                 "qoo_catname": "腕時計・アクセサリー_ファッション腕時計_その他",
                 "s_keyword": "電波 アンティーク チェーン 日本製 デジタル 手巻き 電波時計 ソーラー 機械式 電波ソーラー ペンダント 防水 レトロ かっこいい 蓋付き 中古 6角形 アンティーク風 ゴールド tバー シルバー チェーン付き シルバー925 クリップ 黒 引き輪 鉄道 クォーツ 日本製受験 カラビナ 手巻き式 スケルトン 小さい レディース 自動巻き epos エポス 自動巻 オリエント スタンド アニメ アリス アナログ アウトドア アルバ アラーム 医療用 医療 十六夜咲夜 犬"},
        "ドッグタグ": {"ctname": "オークション > アクセサリー、時計 > 懐中時計 > 機械式 > 手巻き", "y_ct": "2084062956", "sex": "0", "male": "",
                  "female": "", "wowma_catid": "450321", "wowma_catname": "バッグ・財布・ファッション小物>バッグ>バッグ小物・アクセサリー",
                  "qoo_catid": "320001459", "qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_チャーム",
                  "s_keyword": "ネックレス 刻印 サイレンサー 刻印無料 無地 チェーン アルミ メンズ ペア ステンレス シルバー ゴールド ブランド 刻印機 刻印セット 犬 かっこいい シリコン クリア チェーンのみ キーホルダー アニメ アメリカ 青 アクセサリー アルマイト アンクレット プードル 医療 打ち込み ウルヴァリン 大きい 大きめ オリジナル オオカミ オーダーメイド カバー 革 機械 木 キット 金 黒 首輪 クロムハーツ ケース 小型 ことわざ サージカルステンレス 真鍮"},
        "ボディスーツ": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > 補正下着 > ボディスーツ > Cカップ", "y_ct": "2084053170",
                   "sex": "0", "male": "", "female": "", "wowma_catid": "32071103",
                   "wowma_catname": "インナー・ルームウェア>レディースインナー>補正下着>ボディスーツ", "qoo_catid": "300002907",
                   "qoo_catname": "下着・レッグウェア_補正下着_ボディスーツ", "s_keyword": ""},
        "シェイプUPインナー": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > 補正下着 > ボディスーツ > Cカップ", "y_ct": "2084053170",
                       "sex": "0", "male": "", "female": "", "wowma_catid": "32071101",
                       "wowma_catname": "インナー・ルームウェア>レディースインナー>補正下着>その他補正下着", "qoo_catid": "300000031",
                       "qoo_catname": "下着・レッグウェア_補正下着_補正下着・ガードル", "s_keyword": ""},
        "六角ドライバー": {"ctname": "オークション > 住まい、インテリア > 工具、DIY用品 > ハンドツール、大工道具 > スパナ、レンチ > 六角棒レンチ", "y_ct": "2084303401",
                    "sex": "0", "male": "", "female": "", "wowma_catid": "40110501",
                    "wowma_catname": "スポーツ・アウトドア>アウトドア>アウトドア用品>その他アウトドア用品", "qoo_catid": "320000927",
                    "qoo_catname": "ガーデニング・DIY・工具_道具・工具_手動工具", "s_keyword": ""},
        "電気ドリルシャフト": {"ctname": "オークション > 住まい、インテリア > 工具、DIY用品 > その他", "y_ct": "24674", "sex": "0", "male": "",
                      "female": "", "wowma_catid": "40110501", "wowma_catname": "アクセサリー・ジュエリー>アンクレット",
                      "qoo_catid": "320000929", "qoo_catname": "ガーデニング・DIY・工具_道具・工具_電動工具用部品・アクセサリー", "s_keyword": ""},
        "アンクレット": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > アンクレット > その他", "y_ct": "2084062566", "sex": "0",
                   "male": "", "female": "", "wowma_catid": "3003", "wowma_catname": "アクセサリー・ジュエリー>アンクレット",
                   "qoo_catid": "320001451", "qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_アンクレット",
                   "s_keyword": "メンズ レディース つけっぱなし ペア カップル 人気 磁気 ゴールド シルバー925 ブランド シルバー 青 健康 ピンクゴールド 18k 錆びない 開運 ステンレス 18金 つけっぱなし27cm 刻印 金 レザー ゴム 紐 金属アレルギー チタン 足首 50 スラッシュ 赤 アクセサリー 編み込み アメジスト アレルギー対応 アラビア アジャスター イニシャル 石 医療 糸 インド イルカ 海 ウエイト 延長 エスニック エメラルド おそろい 大きいサイズ"},
        "コードリール": {"ctname": "オークション > 住まい、インテリア > 工具、DIY用品 > 電動工具 > コードリール、延長コード > コードリール", "y_ct": "2084207800",
                   "sex": "0", "male": "", "female": "", "wowma_catid": "562309",
                   "wowma_catname": "楽器・音響機器>DTM・レコーディング・PA機器>ケーブル・コネクタ・配線", "qoo_catid": "320002331",
                   "qoo_catname": "パソコン_PCケーブル_その他PCケーブル",
                   "s_keyword": "屋外 20m 10m 30m ペンダントライト ハタヤ 照明 キーホルダー イヤホン 防水 50m 15m 漏電遮断器 屋外用 5m 防雨 温度センサー コンパクト 屋内 アース ミニ hayata usb 黒 ホワイト シルバー 真鍮 白 15a-10m js-101 15a ss-20 js おしゃれ 木製 照明用 カラビナ かわいい イヤホン用 巻き取り ダヤン アイロン アウトドア アース付き 雨 アダプター アクセサリー アンティーク インテリア 犬"},
        "メイクアップブラシ": {"ctname": "オークション > ビューティー、ヘルスケア > コスメ、スキンケア > メイク道具、化粧小物 > ブラシ、チップ、コーム > メイクブラシセット",
                      "y_ct": "2084228681", "sex": "0", "male": "", "female": "", "wowma_catid": "471002",
                      "wowma_catname": "ビューティ・コスメ>ベースメイク・メイクアップ>その他ベースメイク・メイクアップ", "qoo_catid": "320001725",
                      "qoo_catname": "メイク小物_メイク道具_メイクブラシ",
                      "s_keyword": "アーティス  オーバル7 エリート 白鳳堂 ファンデ セット クリーナー オーバル 3本 スライド アーティスト ウエダ セフィーヌ 柔らかいメイクブラシ 携帯便利 敏感肌適用 プレゼント 化粧 msq 化粧ブラシ 人気 メイクブラシ 粧ブラシ 可愛い 化粧筆 肌に優しい ファンデーシ energy store スポンジ付き フランフラン ベアミネラル diolan rownyeon スクリューブラシ 眉毛ブラシ 美眉メイク 天然毛 高級繊維毛 ウトワ 10 コンシーラー用 ar2060"},
        "バングル": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ブレスレット、バングル > バングル > その他", "y_ct": "2084019059",
                 "sex": "0", "male": "", "female": "", "wowma_catid": "3011", "wowma_catname": "アクセサリー・ジュエリー>バングル",
                 "qoo_catid": "300000107", "qoo_catname": "メンズバッグ・シューズ・小物_メンズ小物_ブレスレット・バングル",
                 "s_keyword": "メンズ レディース 太め ハワイアンジュエリー ペア ダニエルウェリントン シルバー ウォッチ シルバー925 ゴールド チタン 黒 レザー ブランド ステンレス ピンクゴールド 人気 天然石 細め ブラック 皮 金 刻印 ハワイアン 2000円 時計 ブレスレット レディース太め レディースステンレス レディース14金 sサイズ カトラリー 防水 かわいい ユニセックス シリコン デジタル jaxis 青 足 アクリル アジアン 赤 アンティーク アレルギー対応 アクセサリーパーツ アンクレット アメリカン 石 インディアン"},
        "エクステンション": {"ctname": "オークション > 住まい、インテリア > 工具、DIY用品 > ハンドツール、大工道具 > 工具セット", "y_ct": "2084303396", "sex": "0",
                     "male": "", "female": "", "wowma_catid": "311002",
                     "wowma_catname": "インテリア・寝具>テーブル>エクステンションテーブル（伸張式）", "qoo_catid": "300003089",
                     "qoo_catname": "バッグ・雑貨_ウィッグ・つけ毛_エクステンション・つけ毛",
                     "s_keyword": "バー 9.5 12.7 6.35 コーケン 自転車 ktc ラチェット 首振り 1/4 コイカツ サンシャイン セット トネ 250 300mm アストロプロダクツ 9.5mm 600mm インパクト koken 12.7mm ロング 300 600  シフトノブ デスク アウターバレル 12 1.25 10 m8 m10 1.75 1.5 ショート 11 m12 バウヒュッテ 140 電動ドライバー 200 150 75 32 1/2 オフセット 短小 1インチ 0.5"},
        "ヘッドキャップ": {"ctname": "オークション > ファッション > ファッション小物 > 帽子 > 女性用 > その他", "y_ct": "2084006690", "sex": "1",
                    "male": "2084006684", "female": "2084006690", "wowma_catid": "404003",
                    "wowma_catname": "スポーツ・アウトドア>ラグビー>ヘッドキャップ", "qoo_catid": "300000127",
                    "qoo_catname": "バッグ・雑貨_ヘアアクセサリー_その他",
                    "s_keyword": "ラグビー 子供 ロードバイク カンタベリー 自転車 インパクト タオル 紐 xs ジュニア キッズ ゴールド 夏 汗 アルミ 医療 エアフロー 衛生 お風呂 おたふく カーボン カバー付き 紙 九桜 黒 ヘルメット 日除け 子ども 子供用 サーフィン 白 シルク 仕事 食品 スパカズ ステム スズキ チタン 使い捨て 時計 夏用 ネット 風呂 マウント 浅め 子ども用 汗取り ロリータ ガーミン ゴム"},
        "Joy-Con": {"ctname": "オークション > おもちゃ、ゲーム > ゲーム > テレビゲーム > ニンテンドースイッチ > ニンテンドースイッチアクセサリー", "y_ct": "2084315796",
                    "sex": "0", "male": "", "female": "", "wowma_catid": "3705", "wowma_catname": "ゲーム機・ゲームソフト>PCゲーム",
                    "qoo_catid": "320001922", "qoo_catname": "テレビゲーム_Nintendo Switch_周辺機器",
                    "s_keyword": "joy-con 修理キット 充電 l グリップ r スティック 純正 修理 カバー 白 日本製 第四世代 ボタン sl sr lボタン lrボタン 38pcs 充電グリップ 充電スタンド 充電器 ライセンス ホリ スタンド / ゼルダの伝説 スカイウォードソード エディション グレー ネオングリーン あつまれ どうぶつの森 ネオンレッド/ ネオンブルー ネオンレッド ボクシング ゼルダ グリップ充電 フィットボクシング ケース v字 レッド ネオンピンク レール rボタン ロック レッグバンド スティックカバー 第4世代 2個"},
        "スマホケース": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0",
                   "male": "", "female": "", "wowma_catid": "410509",
                   "wowma_catname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>スマホケース", "qoo_catid": "320002232",
                   "qoo_catname": "スマホケース・保護フィルム_その他スマホケース_多機種対応ケース",
                   "s_keyword": "iphone12 iphone13 iphone se iphone11 iphone8 xr iphonese2 galaxys10 iphone7 mini 手帳型 韓国 透明 max かわいい topologie pro  se2 se3  リング付き iphone11プロ 手帳 クリア iphone8プラス おしゃれ 耐衝撃 シリコン ハード キャラクター 可愛い iphone7プラス カード収納 背面 あんどろいど 全機種対応 アンドロイド アニメ あくおす sense6 sense3 sense4 アローズ あいふぇいす あろーずwe 犬 イラスト インコ"},
        "iPhoneケース": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0",
                      "male": "", "female": "", "wowma_catid": "410509",
                      "wowma_catname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>スマホケース", "qoo_catid": "320002219",
                      "qoo_catname": "スマホケース・保護フィルム_iPhoneケース_その他 iPhone ケース",
                      "s_keyword": "13 se 12 11 トムとジェリー 11pro xr 13pro xs 13mini 13promax 韓国 13手帳型 キャラクター max クリア se2 手帳型 se3 カード収納 可愛い iface かわいい 12プロ mini 12ミニ 12promax 透明 肩掛け カップル 12mini 11proマックス シリコン ブランド リング付き ショルダー キラキラ ストラップ xsマックス 8 アルミ アイフェス アルミバンパー アクスタ あんぱんまん アイフェイス透明 アイフェス13 アニメキャラクター あつ森 アップルロゴ"},
        "iphoneケース": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0",
                      "male": "", "female": "", "wowma_catid": "410509",
                      "wowma_catname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>スマホケース", "qoo_catid": "320002219",
                      "qoo_catname": "スマホケース・保護フィルム_iPhoneケース_その他 iPhone ケース",
                      "s_keyword": "13 se 12 11 トムとジェリー 11pro xr 13pro xs 13mini 13promax 韓国 13手帳型 キャラクター max クリア se2 手帳型 se3 カード収納 可愛い iface かわいい 12プロ mini 12ミニ 12promax 透明 肩掛け カップル 12mini 11proマックス シリコン ブランド リング付き ショルダー キラキラ ストラップ xsマックス 8 アルミ アイフェス アルミバンパー アクスタ あんぱんまん アイフェイス透明 アイフェス13 アニメキャラクター あつ森 アップルロゴ"},
        "スマホカバー": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0",
                   "male": "", "female": "", "wowma_catid": "410509",
                   "wowma_catname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>スマホケース", "qoo_catid": "320002283",
                   "qoo_catname": "スマートフォン・タブレットPC_スマートフォン用アクセサリー_その他スマートフォン用アクセサリー",
                   "s_keyword": "iphone12 iphone se iphone13 iphone8 xr 11 aquos sense6 galaxy s21 5g 手帳型 mini iphone12ミニ max 韓国  リング付き se2 かわいい se3 キャラクター 第3世代 iphone13ミニ おしゃれ iphone13プロ pro iphone8プラス 可愛い オシャレ クリア xrポケモン リング あいふぇいす 本革 アニメ 11pro 11プロ ストラップ 11プロマックス iitrust 猫 クーピー 花柄 耐衝撃 全面 純正 全機種対応 アンドロイド"},
        "ボクサーパンツ": {"ctname": "オークション > ファッション > メンズファッション > インナーウエア > ボクサーブリーフ > Mサイズ", "y_ct": "2084053072",
                    "sex": "0", "male": "", "female": "", "wowma_catid": "320409",
                    "wowma_catname": "インナー・ルームウェア>メンズインナー>ボクサーパンツ", "qoo_catid": "300000066",
                    "qoo_catname": "メンズファッション_インナー・靴下_ボクサーパンツ",
                    "s_keyword": "メンズ  前開き  下着 ロング 大きいサイズ ボディわいるど セット ローライズ レディース bvd 3枚 コットン メンズブリーフ メッシュ 赤 グレー  綿 かわいい 綿100 シームレス ブランド おしゃれ 黒 前閉じ エアーズ 3d s 吸水速乾 速乾 4枚セット 6枚セット前閉じ ボクサーブリーフ おおきいサイズ sサイズ ロング丈 3l 日本製 アウトドア アニメ アンブロ 陰茎分離型 いんのう分離 いちご 犬 犬柄 陰茎 一枚 イラスト"},
        "パーティグッズ": {"ctname": "オークション > おもちゃ、ゲーム > 手品、パーティグッズ > パーティグッズ > その他", "y_ct": "2084059858", "sex": "0",
                    "male": "", "female": "", "wowma_catid": "29061102",
                    "wowma_catname": "おもちゃ・趣味>アート・美術品・骨董品>骨董品・アンティーク>インテリア雑貨", "qoo_catid": "300000702",
                    "qoo_catname": "ホビー・コスプレ_パーティー・イベント用品_その他",
                    "s_keyword": "誕生日 メガネ 帽子 蝶ネクタイ コスチューム たすき キラキラ 仮面 led かぶりもの 還暦祝い お面 王冠 大人 宇宙人 カツラ かつら おさるのジョージ 扇子 人気 めがね ヘビ 赤 被り物 電気 frozen"},
        "キーチェーン": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > キーチェーン、ウォレットチェーン > キーチェーン", "y_ct": "2084062588",
                   "sex": "0", "male": "", "female": "", "wowma_catid": "3023", "wowma_catname": "アクセサリー・ジュエリー>キーチェーン",
                   "qoo_catid": "320001114", "qoo_catname": "メンズバッグ・シューズ・小物_財布_その他",
                   "s_keyword": "伸びる カラビナ 丈夫 メンズ 自転車 子供 レディース 革 ランドセル かわいい ワイヤー キャラクター リール 頑丈 カラビナベンツ 小さい ブランド おしゃれ 人気 ロング ダイヤル ホルダー ぬいぐるみ コーデュロイ テラコッタ アニメ アウトドア アンティーク アクリル アメリカン 赤 インコ 犬 イルカ ウォレットチェーン ウマ娘 ウォッチ オシャレ 女の子 狼 オレンジ 面白い 大きい 可愛い カードケース 金具 韓国 鍵 キーホルダー キッズ"},
        "キーホルダー": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > キーチェーン、ウォレットチェーン > キーチェーン", "y_ct": "2084062588",
                   "sex": "0", "male": "", "female": "", "wowma_catid": "450407",
                   "wowma_catname": "バッグ・財布・ファッション小物>ファッション小物>キーホルダー・キーリング", "qoo_catid": "300002385",
                   "qoo_catname": "バッグ・雑貨_小物_キーホルダー",
                   "s_keyword": "メンズ カラビナ ぬいぐるみ レディース 人気 gps パーツ  リング おしゃれ ブランド 革 カッコイイ チタン 車 リール かわいい ロック付き 真鍮 ディッキーズ ピンク 韓国 ニキ  猫 キャラクター 安い キラキラ 皮 人気ブランド 名入れ 子供 追跡 認知症 見守り 鍵 スマホ 防犯 高齢 アンドロイド レジン ゴールド シルバー ハート ナスカン 丸カン チェーン 星 アンティークゴールド うさぎ"},
        "ストラップ": {"ctname": "オークション > 自動車、オートバイ > 自動車関連グッズ > アパレル > その他", "y_ct": "2084062588", "sex": "0", "male": "",
                  "female": "", "wowma_catid": "320703", "wowma_catname": "インナー・ルームウェア>レディースインナー>ストラップ",
                  "qoo_catid": "300003050", "qoo_catname": "シューズ_サンダル_ストラップ",
                  "s_keyword": "首掛け スマホ カメラ iphone ホルダー リング 携帯 レスブラ スマホリング キャラクター 子供 おしゃれ 社員証 キッズ携帯 革 首かけ スマホケース かわいい ネック 手首 クリップ 取り外し レザー 金具 ロープ ネジ ホール 肩掛け ケース ショルダー 付きケース 挟む パッチ ホルダー外付けホール  シリコン カラビナ 切れない 式 パーツ 本革 つける 大人 首から 大きいサイズ ずれない 盛れる レスブラジャー ピーチジョン ずれない大きいサイズ"},
        "スウェットパンツ": {"ctname": "オークション > ファッション > メンズファッション > パンツ、スラックス > Mサイズ", "y_ct": "2084224619", "sex": "1",
                     "male": "2084224619", "female": "2084224590", "wowma_catid": "500807",
                     "wowma_catname": "メンズファッション>パンツ・ボトムス>スウェットパンツ", "qoo_catid": "300000064",
                     "qoo_catname": "メンズファッション_パンツ_その他",
                     "s_keyword": "メンズ 大きいサイズ ゆったり  綿100 夏 チャンピオン  レディース ロサンゼルスアパレル グレー 裏起毛 綿 白 ジョガーパンツ ジョガー キッズ ズボン トレーニング 120 迷彩 青タグ 裾ボタン リバースウィーブ ベーシック ベビー バスケットボール ck-sb220 黒 l ネイビー xs セメント ワイド 2xl ジュニア 冬 レイニングチャンプ 5075 厚手 青 赤 アウトドア 薄手 裏パイル 裏毛 運動 柄 エゴザル エックスガール エミネム"},
        "ハーフパンツ": {"ctname": "オークション > ファッション > メンズファッション > パンツ、スラックス > Mサイズ", "y_ct": "2084224619", "sex": "1",
                   "male": "2084224619", "female": "2084224595", "wowma_catid": "511016",
                   "wowma_catname": "レディースファッション>パンツ>ハーフパンツ", "qoo_catid": "300002760",
                   "qoo_catname": "レディースファッション_パンツ_ショート・ハーフパンツ",
                   "s_keyword": "メンズ スポーツ トレーニング  大きいサイズ ゴルフ 7分 スウェット レディース キッズ yonex 水着 テニス 速乾 膝丈 7分丈 ホワイト 迷彩 デサント 3枚 無地 ジュニア バドミントン 15048 150 140 ss 女の子 男の子  100 130 ピンク 白 赤 8l 和柄 七分丈 ロゴ ストレッチ ゴム アウトドア 麻 アンブロ 青 インナー付き インナー いかつい インパル インクブルー インディゴブルー"},
        "バッテリーチェッカー": {"ctname": "オークション > 自動車、オートバイ > 工具 > その他", "y_ct": "2084042062", "sex": "0", "male": "",
                       "female": "", "wowma_catid": "33641404", "wowma_catname": "カー用品・バイク用品>カー用品>トラック用品>その他トラック用品",
                       "qoo_catid": "320000307", "qoo_catname": "カー用品_カー用品_メンテナンス用品",
                       "s_keyword": "車 乾電池 シガーソケット 車用 12v バイク リポ cca シガー 日本製 車スマホ bal オーム 人気 日本 usb 電動ガン エーモン エアガン 大橋 音 オーム電機 オート 紙 キジマ コイン電池 国産 サバゲー  スマホ ソケット 東芝 ニッケル水素 日本語 電池 車の リポの フィルム ミニ四駆 メルテック モバイルバッテリー ラジコン リチウムイオン リチウムイオン電池 リチウム対応 リチウム スマイルキッズ adc-10 しがーソケット 充電池"},
        "バッテリーテスター": {"ctname": "オークション > 自動車、オートバイ > 工具 > その他", "y_ct": "2084042062", "sex": "0", "male": "",
                      "female": "", "wowma_catid": "33641404", "wowma_catname": "カー用品・バイク用品>カー用品>トラック用品>その他トラック用品",
                      "qoo_catid": "320000307", "qoo_catname": "カー用品_カー用品_メンテナンス用品",
                      "s_keyword": "cca 車 12v バイク 日本製 乾電池 バッテリーチェッカー 日本語 24v konnwei 車用 プリンター リチウム アイドリングストップ カイセ プリンター付き クランプ 古河 コード シガーソケット セルスター ソーラー て 内部抵抗 yks 電池残量測定器 ブラック bt-168 車の 比重計 メルテック ヤザワ ユアサ リチウムイオン デジタル 電池 autool bal ds5 ds4 ds7 kaise lvyuan ml-100 usb yazawa 150w 200v 20a midtronics ミドトロニクス pbt-300"},
        "電池残量測定器": {"ctname": "オークション > 自動車、オートバイ > 工具 > その他", "y_ct": "2084042062", "sex": "0", "male": "",
                    "female": "", "wowma_catid": "33641404", "wowma_catname": "カー用品・バイク用品>カー用品>トラック用品>その他トラック用品",
                    "qoo_catid": "320000307", "qoo_catname": "カー用品_カー用品_メンテナンス用品",
                    "s_keyword": "乾 液晶 測定器 単1 5形 9ｖ形乾電池 1.5ｖボタン電池 乾電池 残量 チェッカー テスター yks バッテリーテスター ブラック bt-168 デジタルバッテリー 電池チェッカー 電池の残量チェック"},
        "USBケーブル": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > バッテリー、充電器 > USB式充電器", "y_ct": "2084239197",
                    "sex": "0", "male": "", "female": "", "wowma_catid": "461408",
                    "wowma_catname": "パソコン・PC周辺機器>記録メディア>USBメモリ", "qoo_catid": "320002328",
                    "qoo_catname": "パソコン_PCケーブル_USBケーブル",
                    "s_keyword": "usbケーブル タイプc iphone マイクロb 延長 3in1 オスオス 3m ps4 abタイプ 2m 短い l字 急速充電 アンカー 50cm 30cm 1m 純正 5m anker 0.3m 3.0 10m 0.5m 充電 1.5m 巻き取り データ転送 50ｃｍ 充電用 2本 type-c タイプb オス タイプa 3メートル メス 通信 コントローラー オーディオ プリンター 0.3 アイフォン アンドロイド あいふぉん用 アンドロイドスマホ アイホン用 アップル純正 アイフォン用 磁石"},
        "HDMIケーブル": {"ctname": "オークション > 家電、AV、カメラ > 映像機器 > 映像用ケーブル > HDMIケーブル", "y_ct": "2084239134", "sex": "0",
                     "male": "", "female": "", "wowma_catid": "562309",
                     "wowma_catname": "楽器・音響機器>DTM・レコーディング・PA機器>ケーブル・コネクタ・配線", "qoo_catid": "320002324",
                     "qoo_catname": "パソコン_PCケーブル_HDMIケーブル",
                     "s_keyword": "hdmiケーブル 5m 3m 2m 10m 1m iphone テレビ 2.1 0.5m 4k スリム 柔らかい 2.0 8k 白 タイプc ホワイト やわらか l型 光ファイバー  mini l字 純正 netflix アップル 切り替え amazon観れる 遅延 2022 2.1規格 2本 ハイスピード 120hz 60hz 4kプレミアム 20m アイフォン 変換 あいふぉん アンカー アダプター アンドロイド アップル純正 アマゾンベーシック イーサネット対応 一眼レフ イコライザー付き イーサネット ps4 arc hdr hdmi"},
        "充電ケーブル": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > バッテリー、充電器 > USB式充電器", "y_ct": "2084239197",
                   "sex": "0", "male": "", "female": "", "wowma_catid": "410903",
                   "wowma_catname": "スマホ・タブレット・モバイル通信>バッテリー・充電器>スマホ・タブレット用充電器", "qoo_catid": "320002270",
                   "qoo_catname": "スマートフォン・タブレットPC_バッテリー・充電器_充電ケーブル・充電器", "s_keyword": ""},
        "壁飾り": {"ctname": "オークション > ホビー、カルチャー > ハンドクラフト、手工芸 > 裁縫、刺繍 > 完成品 > その他", "y_ct": "2084240874", "sex": "0",
                "male": "", "female": "", "wowma_catid": "311904", "wowma_catname": "インテリア・寝具>壁紙・装飾フィルム>ウォールステッカー",
                "qoo_catid": "300000475", "qoo_catname": "家具・インテリア_インテリア・装飾_その他",
                "s_keyword": "インテリア お洒落 アイアン 北欧 植物 花 シール 壁掛け パネル かわいい アンティーク 鳥 ライト おしゃれ 咲羅多 トロピカル 北欧風 太陽 北欧壁紙 花束 シール御洒落 シールおしゃれ パネルマリメッコ パネル犬 和風 アニメ 青 アートパネル アート ウォールデコ 絵 折り紙 オブジェ オシャレ オレンジ お花 絵画 韓国 和 可愛い 紙 キラキラ 木 キャラクター 黄色 金属 キット くま 果物 飾り棚 木製"},
        "リース": {"ctname": "オークション > ホビー、カルチャー > ハンドクラフト、手工芸 > 裁縫、刺繍 > 完成品 > その他", "y_ct": "2084240874", "sex": "0",
                "male": "", "female": "", "wowma_catid": "311908", "wowma_catname": "インテリア・寝具>壁紙・装飾フィルム>その他壁紙・装飾フィルム",
                "qoo_catid": "300000475", "qoo_catname": "家具・インテリア_インテリア・装飾_その他",
                "s_keyword": "土台 玄関 ワイヤー リング 春 ノー コンバーター フィギュア ミモザ 20cm 30cm 50cm 10cm 40cm 25cm 15cm ハート 月 春夏 通年 玄関ドア用 おしゃれ 大きめ 夏 桜 緑 ワイヤー茶色 26 細い 23 ブラウン グリーン ゴールド 24 辛口 甘口 ドイツ ワイン アルザス クラシック グラス アウスレーゼ 白 ドライフラワー 贈り物 青 プリザーブド 造花 本 アイアン"},
        "オーナメント": {"ctname": "オークション > ホビー、カルチャー > ハンドクラフト、手工芸 > 裁縫、刺繍 > 完成品 > その他", "y_ct": "2084240874", "sex": "0",
                   "male": "", "female": "", "wowma_catid": "311908",
                   "wowma_catname": "インテリア・寝具>壁紙・装飾フィルム>その他壁紙・装飾フィルム", "qoo_catid": "320000881",
                   "qoo_catname": "ガーデニング・DIY・工具_住宅設備・ライト_ガーデンオーナメント・置物",
                   "s_keyword": "水槽 ガーデン アクアリウム ここねこ ボール スタンド ニブ 星 庭 小さい ジブリ かわいい 和風 きのこ 岩 石 隠れ家 動物 おしゃれ アンティーク ハンギング 猫 小鳥 アニマル 犬 アイアン スポンジボブ オブジェ 大型 diy ココネコ 透明 グリーン クリア 6cm 3センチ ドイツ スタンドホルダー ブラウゼ 鳥 春 北欧 赤 アメリカ インテリア いちご 家 イニシャル うさぎ 馬"},
        "デニムバック": {"ctname": "オークション > ファッション > 男女兼用バッグ > リュックサック、デイパック", "y_ct": "2084233233", "sex": "0", "male": "",
                   "female": "", "wowma_catid": "450302", "wowma_catname": "バッグ・財布・ファッション小物>バッグ>その他バッグ",
                   "qoo_catid": "300000117", "qoo_catname": "バッグ・雑貨_バッグ_その他",
                   "s_keyword": "ショルダー人気 メンズ レディース トートバッグ おしゃれ 小物メンズ a4 サボイ diesel lee"},
        "ショルダーバック": {"ctname": "オークション > ファッション > 男女兼用バッグ > リュックサック、デイパック", "y_ct": "2084233233", "sex": "0",
                     "male": "", "female": "", "wowma_catid": "450307", "wowma_catname": "バッグ・財布・ファッション小物>バッグ>ショルダーバッグ",
                     "qoo_catid": "300000115", "qoo_catname": "バッグ・雑貨_バッグ_ショルダーバッグ",
                     "s_keyword": "れディース 人気 小さめ カジュアル 男性 革 斜めがけ a4サイズ 大容量 おすすめ 皮 レディース 斜めがけ小さめ 斜めがけ軽量 斜めがけブランド 斜めがけミニ 斜めがけ革 斜めがけ人気 pu 布 れレディース れレディース人気 れレディース斜めがけ れレディース小さめ れレディース安い れレディース大容量 れレディース大きめ ブランド れレディース50歳 レディース人気 可愛い メンズ とりばーち 女性 ななめがけ 女性用 a4 アウトドアブランド 赤 アニメ アイパッド 洗える 男性 アルファ アイボリー 犬 運動 ウエットティッシュ 薄い 薄型 薄手"},
        "スリッパ": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > スリッパ", "y_ct": "2084047779", "sex": "0", "male": "",
                 "female": "", "wowma_catid": "31141303", "wowma_catname": "インテリア・寝具>収納家具>玄関収納>スリッパラック",
                 "qoo_catid": "320001468", "qoo_catname": "メンズバッグ・シューズ・小物_メンズシューズ_スリッパ",
                 "s_keyword": "室内 メンズ レディース ラック おしゃれ 学校行事 来客用 洗える 夏用 大きいサイズ 安い セット 夏 かわいい 28cm おりたたみ 防臭 携帯 30cm 冬 ヒール 可愛い パンジー かかとあり キャラクター 壁掛け スリム 山崎実業 マグネット 木製 引っ掛け式 ホワイト 2足 トイレ オシャレ 北欧 お洒落 折りたたみ 25 小さめ s 折り畳み 大きい 前とじ ランキング 4足セット 5足セット 2足セット 高級 学校"},
        "部屋履き": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > スリッパ", "y_ct": "2084047779", "sex": "0", "male": "",
                 "female": "", "wowma_catid": "31141303", "wowma_catname": "インテリア・寝具>収納家具>玄関収納>スリッパラック",
                 "qoo_catid": "300000484", "qoo_catname": "日用品雑貨_生活雑貨_スリッパ・ルームシューズ",
                 "s_keyword": "スリッパ サンダル メンズ レディース シューズ 靴下 夏 靴 草履 暖かい ゴム shperoww ルームシューズ 室内履き 部屋 あったか もこもこ 秋冬 防寒 滑り止め かわいい 夏春 静音で軽量 麻 可愛い 来客用 部屋用 ギフト 洗えるスリッパ スニーカー 私の パンジー pansy 履きやすい部屋ばき ブーツ"},
        "ルームシューズ": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > スリッパ", "y_ct": "2084047779", "sex": "0", "male": "",
                    "female": "", "wowma_catid": "34011513", "wowma_catname": "キッズベビー・マタニティ>キッズ>靴（キッズ）>上履き",
                    "qoo_catid": "300000484", "qoo_catname": "日用品雑貨_生活雑貨_スリッパ・ルームシューズ",
                    "s_keyword": "レディース メンズ 夏 洗える おしゃれ かわいい カモレグ かかと付き もこもこ かかとあり 春夏 夏用 携帯 かかと 春  蒸れない 大きいサイズ 28cm 踵付き スリッポン 滑り止め パイル オシャレ 北欧 冬 レザー 可愛い 500円以内 動物 ゴム キャラクター モコモコ アニマル 大きめ キッズ ルームブーツ 厚底 暖かい 麻 あったか 赤ちゃん あたたかい 犬 い草 インソール 今治 インド綿 今治タオル いぐさ"},
        "コスプレ服": {"ctname": "オークション > コミック、アニメグッズ > コスプレ衣装 > 学生服", "y_ct": "2084311904", "sex": "0", "male": "",
                  "female": "", "wowma_catid": "290801", "wowma_catname": "おもちゃ・趣味>コレクション>その他コレクション",
                  "qoo_catid": "300000701", "qoo_catname": "ホビー・コスプレ_パーティー・イベント用品_コスプレ・変装・仮装",
                  "s_keyword": "アニメ メンズ 135cmサイズ コスプレ 女性キャラ 男 ウィッグ付き 衣装 アニメキャラ レム 女性 アイドル 悪魔 アニマル アズールレーン 犬 インナー 肌色 イースター キャラ イリヤ レディース 医者 ウィッグ ウマ娘 うさぎ ウイッグ うま娘 ウィッグネット ウエディングドレス ウェディング ウエイトレス エッチ えろ エヴァ エプロン えろかわいい えっち 人気 穴あき エヴァンゲリオン エルフ 大きいサイズ おおきいサイズ おもしろ 花魁 面白い おとこの娘 かわいい 可愛い"},
        "コスプレ衣装": {"ctname": "オークション > コミック、アニメグッズ > コスプレ衣装 > 学生服", "y_ct": "2084311904", "sex": "0", "male": "",
                   "female": "", "wowma_catid": "290801", "wowma_catname": "おもちゃ・趣味>コレクション>その他コレクション",
                   "qoo_catid": "300000701", "qoo_catname": "ホビー・コスプレ_パーティー・イベント用品_コスプレ・変装・仮装",
                   "s_keyword": "サキュバス  lサイズ エナメル 女性 大きいサイズ アニメ 和風 スカート 女装 メンズ アニメキャラ アニメ男子 アニメフェスティバル 祝日贈り物 東京卍會 ウエディングドレス 中野二乃 大きめ あんスタ alkaloid 月永レオ 白鳥藍良 斎宮 ウマ娘 男性 ウィッグ付き 緋弾のアリア 神崎 h アリア エネ 男性用 通販 本 アズールレーン アルバーン アイドル アークナイツ グラベル アイドル風 シラユキ イブラヒム 和服 ウルトラマン ウェディングピーチ 薄桜鬼 歌衣メイカ ウイッグ ラブライブ 南 ことりur 覚醒後 アイドル衣装編 lovelive"},
        "プリンセス服": {"ctname": "オークション > コミック、アニメグッズ > コスプレ衣装 > 学生服", "y_ct": "2084311904", "sex": "0", "male": "",
                   "female": "", "wowma_catid": "290802", "wowma_catname": "おもちゃ・趣味>コレクション>アニメグッズ",
                   "qoo_catid": "300000701", "qoo_catname": "ホビー・コスプレ_パーティー・イベント用品_コスプレ・変装・仮装",
                   "s_keyword": "子供 110 100 プリンセス 服 キッズ 120 大人 長袖 90 アクセサリー 秋田書店 アップリケ アクアビーズ あいうえお アルミ 弁当箱 アクセサリーセット アリエル アルバム 衣装 色鉛筆 12色 椅子 イス 移動ポケット 上履き 上履き入れ うわばき 腕時計 ウォールステッカー 浮き輪 上靴入れ 17 16.5 絵本 エプロン えんぴつ 鉛筆 エコバッグ 2b 鉛筆削り 3歳 おもちゃ お弁当箱 お菓子 お弁当 おしぼり お皿 お化粧セット"},
        "扇子": {"ctname": "オークション > ファッション > ファッション小物 > 扇子", "y_ct": "2084045073", "sex": "0", "male": "", "female": "",
               "wowma_catid": "450422", "wowma_catname": "バッグ・財布・ファッション小物>ファッション小物>扇子", "qoo_catid": "320001128",
               "qoo_catname": "レディースファッション_和服・コスチューム_和装小物",
               "s_keyword": "メンズ レディース 無地 白 立て 桜 金 赤 紫 高級 日本製 丈夫 おしゃれ 名入れ 大きい 虎 かわいい ブランド 布 可愛い 竹 人気 黒 結婚式 大 手作り 白檀 白無地 白竹堂 安い 白無垢 白竹 レース 半月 壁掛け 桜柄 紅葉 シルク 金属 金魚 金色 金銀 金具 小さい 日の丸 金物留め具 バレエ 赤ちゃん 紫陽花 アニメ"},
        "ミニドレス": {"ctname": "オークション > ファッション > レディースファッション > フォーマル > カラードレス > その他", "y_ct": "2084064292", "sex": "0",
                  "male": "", "female": "", "wowma_catid": "510905", "wowma_catname": "レディースファッション>ドレス>キャバドレス・ミニドレス",
                  "qoo_catid": "300000001", "qoo_catname": "レディースファッション_ワンピース・ドレス_ドレス",
                  "s_keyword": "キャバ 白 黒 フレア 大きいサイズ ピンク きれいめ 上品 水色 キャバ嬢 ふわふわ 花嫁 赤 青 白い 襟付き オフショル 大人 可愛い かわいい 韓国 黄色 キッズ キラキラ 透け透け コスプレ 子ども サテン 透け タイト と 長袖 夏 人気の 白ランキング キャバランキング 女の子 花柄 半袖 フリル ホワイト 緑 ミニワンピース 紫 ミニ チャイナドレス セクシーチャイナ服 梅花柄 光沢あり 短袖"},
        "ウェディングベール": {"ctname": "オークション > ファッション > レディースファッション > フォーマル > カラードレス > その他", "y_ct": "2084064292",
                      "sex": "0", "male": "", "female": "", "wowma_catid": "510911",
                      "wowma_catname": "レディースファッション>ドレス>パーティドレス", "qoo_catid": "300002195",
                      "qoo_catname": "レディースファッション_ワンピース・ドレス_その他",
                      "s_keyword": "ロング ショート ミディアム ミドル オフホワイト 3m コーム付き 2層 ラメ 5m アイボリー 安い キラキラ ケース コスプレ 刺繍 シンプル ティアラ 人気の 花 フラワー メタル メロウ パイピング パール 1m 250 200 4m"},
        "腕時計": {"ctname": "オークション > アクセサリー、時計 > メンズ腕時計 > アナログ（クォーツ式） > その他", "y_ct": "2084053684", "sex": "1",
                "male": "2084053684", "female": "2084223414", "wowma_catid": "5801", "wowma_catname": "腕時計>その他腕時計",
                "qoo_catid": "300002357", "qoo_catname": "腕時計・アクセサリー_ファッション腕時計_メンズ腕時計",
                "s_keyword": "メンズ レディース 電波ソーラー ベルト デジタル スタンド 防水 安い 電波 人気 ソーラー チタン アナログ 革ベルト 20mm 22mm 18mm ピン 外し 方 ベルト調整 革 16mm 19mm 文字大きい 1本 2本 木製 自動巻 おしゃれ 白 壁掛け 4本 gショック キッズ スタンダード カシオエディフィス エディフィス アウトドア ケース アニメ 赤 アンティーク 青 アップルウォッチ イヤホン 医療用 インビクタ イタリア 入れ物"},
        "変換プラグ": {"ctname": "オークション > 家電、AV、カメラ > 電子部品 > コネクタ", "y_ct": "2084282461", "sex": "0", "male": "",
                  "female": "", "wowma_catid": "562309", "wowma_catname": "楽器・音響機器>DTM・レコーディング・PA機器>ケーブル・コネクタ・配線",
                  "qoo_catid": "320002045", "qoo_catname": "生活家電_その他生活家電_変圧器・変換プラグ",
                  "s_keyword": "acアダプター 海外 コンセント cタイプ ヘッドホン 人気の海外 ランキング bf iphone 日本用 usb type-c 5.5 2.5 l型 19v 延長 4.0 dell 7.4 4.5 海外から日本 c 日本 b3 海外旅行 海外用 n極 アメリカ 3p 2p イギリス cタイプからaタイプ ライトニング セット aメス 3.5 マイク 6.35 4極 bfタイプ kashimura イヤホン o2タイプ seタイプ オーストラリア 3ピンから2ピン oタイプ アメリカから日本 アダプター"},
        "中継プラグ": {"ctname": "オークション > 家電、AV、カメラ > 電子部品 > コネクタ", "y_ct": "2084282461", "sex": "0", "male": "",
                  "female": "", "wowma_catid": "562309", "wowma_catname": "楽器・音響機器>DTM・レコーディング・PA機器>ケーブル・コネクタ・配線",
                  "qoo_catid": "320002045", "qoo_catname": "生活家電_その他生活家電_変圧器・変換プラグ",
                  "s_keyword": "テレビ 延長コネクター 3ピン rcaとrca メス アンテナの接続方法 av端子 acアダプター 4.8 1.7 変換アダプタ dxアンテナ dcプラグ 中継 hdmi 3aカンパニー s端子 オーディオ メス-メス vad-jsvst 2分岐 rj45 プラグ rca オスオス メスメス アンテナ wuernine 5個セット f型接栓 3.5mm フジパーツ ピン端子-ピン端子 ac-333"},
        "ホログラム": {"ctname": "オークション > 自動車、オートバイ > メンテナンス > 塗料", "y_ct": "2084049690", "sex": "0", "male": "",
                  "female": "", "wowma_catid": "336402", "wowma_catname": "カー用品・バイク用品>カー用品>バッテリー・メンテナンス用品",
                  "qoo_catid": "320000298", "qoo_catname": "カー用品_バイク用品_メンテナンス用品",
                  "s_keyword": "シート シール テープ アート スリーブ ネイル 透明 熱転写 ハート 赤 青 黒 緑 ピンク 釣り ルアー インクジェット 印刷 a4 シールシート シールオーロラ 粘着あり オーロラ 水色 金 テープシール 粘着 粘着有り 紫 アートシール プリンセス すみっ 子供 水族館 キラキラユニコーン l版 チェキ ミニ色紙 インナー ポストカード トレカ テープ付 丸 ネイルポリッシュ 六角 セット フィルム ステッカー カッティングシート 折り紙"},
        "イヤーフック": {"ctname": "オークション > 家電、AV、カメラ > オーディオ機器 > ヘッドフォン、イヤフォン > イヤフォン > その他", "y_ct": "2084219572",
                   "sex": "0", "male": "", "female": "", "wowma_catid": "44060201",
                   "wowma_catname": "テレビ・オーディオ・カメラ>ヘッドホン・イヤホン>イヤホン>その他イヤホン", "qoo_catid": "320002462",
                   "qoo_catname": "イヤホン・ヘッドホン_イヤホン_イヤホン",
                   "s_keyword": "イヤホン アクセサリー airpods pro ワイヤレスイヤホン マスク bluetooth パーツ マスク用 耳掛け 有線 final 11ミリ シリコン イヤホン用 メンズ 韓国 アクセサリー蝶 花 apple 第二世代 第三世代 用 イヤホンカバー 充電 後付け 付き ハンドメイド ワイヤレス ヘッドセット アンカー アップル イヤリング イヤーピース インナーイヤー イヤフォン さとう式 さうんどぴーつ air3 エアーポッズ エアーポッズプロ おしゃれ カナル型 金具 片耳 可愛い カナル 会議 付きイヤホン 黒"},
        "ガラスフイルム": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール", "y_ct": "2084299106",
                    "sex": "0", "male": "", "female": "", "wowma_catid": "410518",
                    "wowma_catname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>液晶保護フィルム", "qoo_catid": "320002243",
                    "qoo_catname": "スマホケース・保護フィルム_保護フィルム_多機種対応保護フィルム",
                    "s_keyword": "iphone13  ブルーライトカット 覗き見防止 さらさら アンチグレア ブルーライト カメラ のぞき見防止 nimaso 全面 iphone12 指紋防止 iphone se3 日本製 白 ゴリラ 窓 iphone11 13 12 se ミラー おしゃれ 飛散防止 透明 目隠しシート 目隠し ダークブルー グラデーション ステンドグラス風 キャラクター 侍  覗き見 pro mini 13promax 13プロ 13ミニ 13インチ 12pro 12mini 12promax 12ミニ 12.9 12インチ se2 接着剤 sense6"},
        "ガラスフィルム": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール", "y_ct": "2084299106",
                    "sex": "0", "male": "", "female": "", "wowma_catid": "410518",
                    "wowma_catname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>液晶保護フィルム", "qoo_catid": "320002243",
                    "qoo_catname": "スマホケース・保護フィルム_保護フィルム_多機種対応保護フィルム",
                    "s_keyword": "iphone13  ブルーライトカット 覗き見防止 さらさら アンチグレア ブルーライト カメラ のぞき見防止 nimaso 全面 iphone12 指紋防止 iphone se3 日本製 白 ゴリラ 窓 iphone11 13 12 se ミラー おしゃれ 飛散防止 透明 目隠しシート 目隠し ダークブルー グラデーション ステンドグラス風 キャラクター 侍  覗き見 pro mini 13promax 13プロ 13ミニ 13インチ 12pro 12mini 12promax 12ミニ 12.9 12インチ se2 接着剤 sense6"},
        "強化ガラス": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール", "y_ct": "2084299106", "sex": "0",
                  "male": "", "female": "", "wowma_catid": "311905", "wowma_catname": "インテリア・寝具>壁紙・装飾フィルム>ガラスフィルム",
                  "qoo_catid": "320002243", "qoo_catname": "スマホケース・保護フィルム_保護フィルム_多機種対応保護フィルム",
                  "s_keyword": "iphone13 フィルム ipad mini セット コップ iphone12 板ガラス グラス ブルーライトカット カメラ のぞき見防止 日本製 指紋防止 全面 子供 デュラレックス 130ml 赤ちゃん pro ブルーライト max iphone13ミニ iphone13プロ 全面保護 ゴリラ ケース 大きいサイズ 子ども 500ml 500 iphone se 皿 ピアス iphone8 食器 アイフォンse アイフォン アイフォン12 アンチグレア アイフォン13 うすはり 液晶保護フィルム 液体 円 円形 12mm 3d耐衝撃ガラス xs"},
        "保護フィルム": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール", "y_ct": "2084299106",
                   "sex": "0", "male": "", "female": "", "wowma_catid": "410518",
                   "wowma_catname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>液晶保護フィルム", "qoo_catid": "320002243",
                   "qoo_catname": "スマホケース・保護フィルム_保護フィルム_多機種対応保護フィルム",
                   "s_keyword": "macbook air m1  アンチグレア ブルーライトカット 覗き見 光沢 ブルーライト キーボード ガラス nimaso ipadだい9世代 エクスペリア5iii アイフォン13 iphone13 iphone se iphone12 フリーサイズ 紙 ペーパーライク 指紋 滑りやすい pet カメラ 覗き見防止 日本製 全面 マット さらさら プロ 強化ガラス 指紋防止 見えない pro mini iphone13ミニ max スマホふぃるむ se2 スマホ se3 第3世代 iphone12ミニ 2枚 タブレット 特大 9h 7インチ ノングレア"},
        "トートバック": {"ctname": "オークション > ファッション > 男女兼用バッグ > トートバッグ", "y_ct": "2084233232", "sex": "0", "male": "",
                   "female": "", "wowma_catid": "450310", "wowma_catname": "バッグ・財布・ファッション小物>バッグ>トートバッグ",
                   "qoo_catid": "300000116", "qoo_catname": "バッグ・雑貨_バッグ_トートバッグ",
                   "s_keyword": "大きめ レディース メンズ キャンプ キャンバス 帆布 かわいい 黒 自立 ファスナー付き 小さい 小さいブランド チャック付き ピンク 小さいかわいい ナイロン ビニール ランチ 人気 ブランド ブランド大きめ ブランドanero オシャレ 布 ファスナー キャンバス生地 小さめ a4 猫 スラッシャー 多機能 大容量レディース 大学生 肩掛け 安い 大容量 学生 可愛い ノースフェース アニエスべー 厚手 アウトドアブランド アニメキャラクター 赤 アンダーマー アヒル 麻 犬 散歩 薄い ウクライナ"},
        "ハンドグリップ": {"ctname": "オークション > スポーツ、レジャー > スポーツ別 > エクササイズ用品 > ギア > その他", "y_ct": "2084006837", "sex": "0",
                    "male": "", "female": "", "wowma_catid": "401101", "wowma_catname": "スポーツ・アウトドア>アウトドア>その他アウトドア",
                    "qoo_catid": "300000206", "qoo_catname": "スポーツ_スポーツシューズ・雑貨_スポーツ用品",
                    "s_keyword": "50kg 60kg 100kg 70kg 40kg 80kg 調整可能 スマホ 30kg 70kgゴリラ オレンジ 三脚 カウンター カメラ アイアン 握力 アルミ 青 アクションカメラ アルインコ グリッパー 握力トレーニング 赤 移動ポケット 痛く無い エアガン おもちゃ 親指 可変式 カウンター付き 軽い カバー カメラ用 軽め 可変 カウント キャプテンスタッグ 吸盤 金属 キッズ クラッシュ 車 黒 血圧 懸垂 血圧低下 こども用 子供 こども 小型"},
        "眼鏡 ケース": {"ctname": "オークション > ビューティー、ヘルスケア > めがね、コンタクト > めがね > その他", "y_ct": "2084063613", "sex": "0",
                   "male": "", "female": "", "wowma_catid": "450604", "wowma_catname": "バッグ・財布・ファッション小物>メガネ>メガネケース",
                   "qoo_catid": "300002384", "qoo_catname": "バッグ・雑貨_眼鏡・サングラス_眼鏡ケース",
                   "s_keyword": "ハンドグリップ 50kg 60kg 100kg 70kg 40kg 80kg 調整可能 スマホ 30kg 70kgゴリラ オレンジ 三脚 カウンター カメラ アイアン 握力 アルミ 青 アクションカメラ アルインコ グリッパー 握力トレーニング 赤 移動ポケット 痛く無い エアガン おもちゃ 親指 可変式 カウンター付き 軽い カバー カメラ用 軽め 可変 カウント キャプテンスタッグ 吸盤 金属 キッズ クラッシュ 車 黒 血圧 懸垂 血圧低下 こども用 子供 こども 小型"},
        "グリッパー": {"ctname": "オークション > スポーツ、レジャー > スポーツ別 > エクササイズ用品 > ギア > その他", "y_ct": "2084006837", "sex": "0",
                  "male": "", "female": "", "wowma_catid": "401101", "wowma_catname": "スポーツ・アウトドア>アウトドア>その他アウトドア",
                  "qoo_catid": "300000206", "qoo_catname": "スポーツ_スポーツシューズ・雑貨_スポーツ用品",
                  "s_keyword": "coc  0.5 2 1.5 トレーナー ガイド 38 赤 34 ネイビー 37 レッド ホワイト 25 青 白 握力 体育館シューズ 体育館シューズ24 靴 23.5 ブルー ズグローブ m えんぴつ 2b 鉛筆 b グリーン 26.5 シューズ カーペット キャンプ 上履き アウトドア 運動靴 キャプテン あさひ シートカバー スタンド 10個 調整 釣り テーブルソー milicamp クッカークリップ メスティン クッカー用 鍋つかみ クッカーハンドル"},
        "眼鏡ケース": {"ctname": "オークション > ビューティー、ヘルスケア > めがね、コンタクト > めがね > その他", "y_ct": "2084063613", "sex": "0",
                  "male": "", "female": "", "wowma_catid": "450604", "wowma_catname": "バッグ・財布・ファッション小物>メガネ>メガネケース",
                  "qoo_catid": "300002384", "qoo_catname": "バッグ・雑貨_眼鏡・サングラス_眼鏡ケース",
                  "s_keyword": "おしゃれ ハード スリム 大きめ 可愛い コンパクト 革 御洒落 レディース キャラクター かわいい 花柄 男性 お洒落 ブランド オシャレ おしゃれマリメッコ 軽量 白 黒 本革 猫 スリム和柄 安い 携帯 革製 名入れ アニメ アルミ 赤 アウトドア アウトドアブランド 安価 アリエル 青 アリス アンティーク 犬 イーブイ 印伝 イニシャル いちご 薄型 ウレタン うさまる ウッド うさぎ ソフト エヴァンゲリオン 映画"},
        "サニタリーショーツ": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > ショーツ > サニタリー", "y_ct": "2084211791",
                      "sex": "0", "male": "", "female": "", "wowma_catid": "32070203",
                      "wowma_catname": "インナー・ルームウェア>レディースインナー>ショーツ>サニタリー", "qoo_catid": "300002905",
                      "qoo_catname": "下着・レッグウェア_ショーツ_サニタリーショーツ",
                      "s_keyword": "ジュニア 羽根付き対応 レディース 大きいサイズ ロリエ ソフィ 夜用 セット 150 ポケット 160 ポケット付き  140 はねつき対応 ナイト かわいい ボクサー 綿 xl 女の子 深め 羽根 夜 綿100 黒 3l 深履き 5l 4l 昼用 ハイウエスト l m ガードル 横もれ コットン カジュアル デオプラス ロリエll 超熟睡密着フィット ナチュラル ソフィll ナイトフィット 深ばき 羽根つき対応 ll 黄色 ワコールジュニア 2s"},
        "生理用ショーツ": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > ショーツ > サニタリー", "y_ct": "2084211791",
                    "sex": "0", "male": "", "female": "", "wowma_catid": "32070203",
                    "wowma_catname": "インナー・ルームウェア>レディースインナー>ショーツ>サニタリー", "qoo_catid": "300002905",
                    "qoo_catname": "下着・レッグウェア_ショーツ_サニタリーショーツ",
                    "s_keyword": "ジュニア ロリエ ナプキン不要 羽根つき対応 大きいサイズ ソフィ 小学生 夜用 吸水 ポケット付き 150  ジュニアスポーツ ポケット 160 140 m l 夜 綿 大きいサイズ3l 深ばき 4l xl 深め キャラクター ナプキン 一枚 ウイング ウィスパー 羽がしまえる おしゃれ オーガニック 女の子 多い日 大きい 可愛い かわいい 紙 カイロ 吸水型 吸収型 キティ きれい 吸収 キッズ 黒 一分だけ 子供 コットン"},
        "ナプキン": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > ショーツ > サニタリー", "y_ct": "2084211791", "sex": "0",
                 "male": "", "female": "", "wowma_catid": "320709", "wowma_catname": "インナー・ルームウェア>レディースインナー>布ナプキン",
                 "qoo_catid": "300002905", "qoo_catname": "下着・レッグウェア_ショーツ_サニタリーショーツ",
                 "s_keyword": "生理用品  パンツ型 夜用 羽つき 羽なし 昼用 オーガニック はだおもい ソフィ エリス 羽根つき 420 400 ロリエ スリム 360 センターイン 昼 定期便 25 大きいサイズ xl 大きめ s まとめ買い ll ショーツタイプ 大きい sサイズ l m オーガニックコットン 26 29センチ おりもの 夜 シンプル 27 羽根なし 23 軽い日 朝までブロック 朝まで アクティブ 安心ショーツ 青 赤 麻 悪露 入れる ポーチ"},
        "コンソールケーブル": {"ctname": "オークション > コンピュータ > パーツ > ケーブル、コネクタ > その他", "y_ct": "2084039542", "sex": "0", "male": "",
                      "female": "", "wowma_catid": "46080402",
                      "wowma_catname": "パソコン・PC周辺機器>パソコン本体>デスクトップパソコン>ディスプレイセット", "qoo_catid": "320002331",
                      "qoo_catname": "パソコン_PCケーブル_その他PCケーブル",
                      "s_keyword": "usb rj45 cisco 変換 type-c rj-45 db-9 シリアルケーブル 互換ケーブル rj45-db9 buffalo usb-c cisco純正 延長 巻き取り タイプc 爪 バッファロー aruba db9 elecom fortigate ftdi iphone  シリアル チップ nec panasonic rs232c yamaha usb, 1.8m 3m"},
        "ロールオーバーケーブル": {"ctname": "オークション > コンピュータ > パーツ > ケーブル、コネクタ > その他", "y_ct": "2084039542", "sex": "0",
                        "male": "", "female": "", "wowma_catid": "46080402",
                        "wowma_catname": "パソコン・PC周辺機器>パソコン本体>デスクトップパソコン>ディスプレイセット", "qoo_catid": "320002331",
                        "qoo_catname": "パソコン_PCケーブル_その他PCケーブル", "s_keyword": "usb-c cisco コンソール"},
        "3D ゴーグル": {"ctname": "オークション > 家電、AV、カメラ > 映像機器 > その他", "y_ct": "2084051816", "sex": "0", "male": "",
                    "female": "", "wowma_catid": "610102", "wowma_catname": "音楽・映像>映像DVD・Blu-ray>その他映像DVD・Blu-ray",
                    "qoo_catid": "320002420", "qoo_catname": "テレビ・オーディオ_テレビ用アクセサリー_3Dメガネ",
                    "s_keyword": "3d ゴーグル ディスプレイ vrゴーグル ヘッドホン付き med-vrg3  焦点距離調節機能 vrヘッドセット 3dゴーグル本体 3dゴーグル クエスト2 スマホ 不要 メガネ vrゴーグル用 保護マスク アイマスク 100枚入り vr-ms100 ホワイト ゲーム bestface hdmi echoamz iphone pc用 t-pro urgod vr samonic 2d pico g2 4k ヘッド"},
        "3Dゴーグル": {"ctname": "オークション > 家電、AV、カメラ > 映像機器 > その他", "y_ct": "2084051816", "sex": "0", "male": "",
                   "female": "", "wowma_catid": "610102", "wowma_catname": "音楽・映像>映像DVD・Blu-ray>その他映像DVD・Blu-ray",
                   "qoo_catid": "320002420", "qoo_catname": "テレビ・オーディオ_テレビ用アクセサリー_3Dメガネ",
                   "s_keyword": "3dゴーグル スマホ iphone pc用 不要 クエスト2 ゲーム メガネ  3d vrゴーグル 焦点距離調節機能 ヘッドホン付き med-vrg3 vrヘッドセット 3dゴーグル本体 vrゴーグル用 保護マスク アイマスク 100枚入り vr-ms100 ホワイト bestface hdmi echoamz t-pro urgod vr ゴーグル samonic 2d ディスプレイ pico g2 4k ヘッド"},
        "VRメガネ": {"ctname": "オークション > 家電、AV、カメラ > 映像機器 > その他", "y_ct": "2084051816", "sex": "0", "male": "",
                  "female": "", "wowma_catid": "610102", "wowma_catname": "音楽・映像>映像DVD・Blu-ray>その他映像DVD・Blu-ray",
                  "qoo_catid": "320002282", "qoo_catname": "スマートフォン・タブレットPC_スマートフォン用アクセサリー_VRゴーグル",
                  "s_keyword": "vrメガネ iphone vrメガネ型 スマホ用 タブレット pc用 vrメガネカバー メガネをしながらvr hqing hp vr メガネ oculus quest 2 vrゴーグル メガネ対応 3d"},
        "バーチャルリアリティメガネ": {"ctname": "オークション > 家電、AV、カメラ > 映像機器 > その他", "y_ct": "2084051816", "sex": "0", "male": "",
                          "female": "", "wowma_catid": "610102",
                          "wowma_catname": "音楽・映像>映像DVD・Blu-ray>その他映像DVD・Blu-ray", "qoo_catid": "320002282",
                          "qoo_catname": "スマートフォン・タブレットPC_スマートフォン用アクセサリー_VRゴーグル",
                          "s_keyword": "vrメガネ iphone vrメガネ型 スマホ用 タブレット pc用 vrメガネカバー メガネをしながらvr hqing hp vr メガネ oculus quest 2 vrゴーグル メガネ対応 3d"},
        "トランプ": {"ctname": "オークション > おもちゃ、ゲーム > ゲーム > カードゲーム > トランプ", "y_ct": "40534", "sex": "0", "male": "",
                 "female": "", "wowma_catid": "291201", "wowma_catname": "おもちゃ・趣味>トレーディングカード>その他トレーディングカード",
                 "qoo_catid": "320000661", "qoo_catname": "ホビー・コスプレ_手品・マジック_カード・トランプ",
                 "s_keyword": "プラスチック 信者 潜入一年 バイスクル キャラクター ケース 任天堂 ポーカー カード おしゃれ 子供 恐竜 透明 bicycle ポーカーサイズ 黒 エリートエディション ダブルバック ライダーバック 青 ブリッジサイズ セット ジブリ プラスチックソフィア リラックマ すみっこ きめつ マリオ ケースのみ かっこいい ケース付き 木 潜入1年 信者潜入 ナップ 622 ポーカー用 プロテクター 4色 ポーカーチップ ポーカースターズ カードケース 無地 カード入れ 白紙 高級 マジック かわいい アニメ アクセサリー"},
        "カードゲーム": {"ctname": "オークション > おもちゃ、ゲーム > ゲーム > カードゲーム > トランプ", "y_ct": "40534", "sex": "0", "male": "",
                   "female": "", "wowma_catid": "550601", "wowma_catname": "本・コミック・雑誌>ゲーム攻略・ゲームブック>TRPG・カードゲーム",
                   "qoo_catid": "300003162", "qoo_catname": "おもちゃ・知育_カード・ボードゲーム_カードゲーム",
                   "s_keyword": "ワンピース 予約 プレイマット レシピ 人気 ケース 子供 スリーブ romance dawn スタートデッキ バンダイ 麦わらの box  ホロライブ デュエマ アニメ ウルトラプロ デジモン スイーツ クリスマス ハワイ セット 和食 エブリイ 北海道 ワールド 定番 家族 大人 2人 二人 小学生 子ども 大量収納 120枚 レザー コンパクト 紙 大量pocket ケース鑑賞 知育 子供向け one piece アルゴ アタッシュケース あいうえお アクリル"},
        "アンダーウェア": {"ctname": "オークション > スポーツ、レジャー > スポーツウエア > 男性用 > インナーウエア > シャツ", "y_ct": "2084246663", "sex": "0",
                    "male": "", "female": "", "wowma_catid": "320712", "wowma_catname": "インナー・ルームウェア>レディースインナー>アンダーウェア",
                    "qoo_catid": "300002873", "qoo_catname": "スポーツ_スポーツウェア_メンズスポーツインナー",
                    "s_keyword": "メンズ レディース 夏 ゴルフ キッズ パールイズミ スポーツ 下 パンツ 半袖 ハイネック 夏用 速乾 uv 長袖 指穴 stb アームサポーター stb-ac01 バドミントン ウェア yonex アンダーギア st 42009 大きい np df モック タイト l/s トップ dd1987-010 サッカー 野球 ノースリーブ キッズスキー 120 110 赤 青 汗 アウトドア 暖かい 医療 上 ウール 裏起毛 うんち えんじ色"},
        "コンプレッションウェア": {"ctname": "オークション > スポーツ、レジャー > スポーツウエア > 男性用 > インナーウエア > シャツ", "y_ct": "2084246663",
                        "sex": "0", "male": "", "female": "", "wowma_catid": "500903",
                        "wowma_catname": "メンズファッション>作業服>作業用インナー・コンプレッションウェア", "qoo_catid": "300002873",
                        "qoo_catname": "スポーツ_スポーツウェア_メンズスポーツインナー",
                        "s_keyword": "メンズ 半袖 夏用 上下セット ノースリーブ 夏 vネック タイツ ハイネック 長袖  レディース セット キッズ 冷感 レディース夏用 bobora 3枚 v 上下セットナイキ 上下セット紺色 トレーニングウェア 5点セット セットアップ アスリオ 赤 アニメ アンブロ アベンジャーズ アーム インナー ウィメンズ 裏起毛 エクシオ 柄 大きいサイズ おたふく オールシーズン おしゃれ 女の子 オレンジ おたふく手袋 カモフラージュ カップ付き 加圧 カモフラ クール 蛍光 子供 腰 作業着"},
        "カジュアル ベルト": {"ctname": "スポーツ・アウトドア>アウトドア>アウトドアウェア>ベルト", "y_ct": "2084246663", "sex": "0", "male": "",
                      "female": "", "wowma_catid": "40110208", "wowma_catname": "スポーツ・アウトドア>アウトドア>アウトドアウェア>ベルト",
                      "qoo_catid": "300002178", "qoo_catname": "メンズバッグ・シューズ・小物_メンズ小物_メンズカジュアルベルト",
                      "s_keyword": "メンズ おおきいサイズ  細め ベルト カジュアル 穴あり 大きいサイズ 安い おしゃれ かっこいい むだんかい調整ベルト 大きい カジュアルベルト 黒 長さ調整 小さいサイズ 白 長い エムアールユー 父の日 ギフト ビジネス 本革 レザー 紳士 バックル サイ 編み込み freese メッシュ ビジネス&カジュアル 伸縮 サイズ調整フリー レディース ロング beel ベール 牛革 オートロック式ベルト 穴無し 革 ブラック 祝いギフトbox付 ナチュラル 細ベルト レザーベルト ステッチ 0110937 アメカジ ブランド"},
        "ネックレス": {"ctname": "アクセサリー・ジュエリー>ネックレス", "y_ct": "2084246663", "sex": "0", "male": "", "female": "",
                  "wowma_catid": "3009", "wowma_catname": "アクセサリー・ジュエリー>ネックレス", "qoo_catid": "300002342",
                  "qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_ネックレス",
                  "s_keyword": "メンズ レディース 人気 チェーン コラントッテ 人気ブランド メンズ人気 シルバー ごろーず ゴールド メンズ人気ブランド シンプル 十字架 ブランド 安い 金属アレルギー対応 dior ステンレス 18金 ピンクゴールド プラチナ チェーンのみ 指輪 らくわ x100 メタックス ワイヤー 羽生結弦 55cm x50 チタン スマイル オープンハート ハート ダイヤモンド ピアス セット スワン ダンシング 金属アレルギー colantotte alt クレスト luce α tao matte スリム 収納 アジャスター"},
        "ブルーライトカットフィルム": {"ctname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>液晶保護フィルム", "y_ct": "2084246663", "sex": "0", "male": "",
                          "female": "", "wowma_catid": "410518", "wowma_catname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>液晶保護フィルム",
                          "qoo_catid": "320002243", "qoo_catname": "スマホケース・保護フィルム_保護フィルム_多機種対応保護フィルム",
                          "s_keyword": "ipad  第9世代 衝撃 第7世代 第6世代 第5世代 10.2 9.7インチ 第8世代 iphone13 macbook air パソコン 携帯 15.6 24インチ 21.5 99% 90% m1 19インチ 15.6インチ iphone8 iphone se2 モニター 13 ブルーライトカット フィルム アイフォン8 アイフォン13 アイパッド アンドロイド アイフォン11 アイフォン10 アイフォン12 アイホン11 アンチグレア アイフォン7 いphone11 あいふぉん13 ピタ貼り for 有機elモデル カット出来る 切れる ぎゃらくしーs21 サーフェス pro 12.9 取り外し"},
        "カメラレンズ": {"ctname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>カメラレンズ", "y_ct": "2084246663", "sex": "0", "male": "",
                   "female": "", "wowma_catid": "410505", "wowma_catname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>カメラレンズ",
                   "qoo_catid": "320002277", "qoo_catname": "スマートフォン・タブレットPC_スマートフォン用アクセサリー_スマートフォン用カメラレンズ",
                   "s_keyword": "iphone13 保護 キャラクター キラキラ  保護ケース グリーン アルミ spigen iphone12 カバー ブルー ゴールド 白 かわいい ブラック mini 保護フィルム nimaso 赤 ケース パープル 日本製 シルバー 保護max  クリーナー キャップ クリーナー液 ハクバ クリーナーセット クリーナークロス ペーパー スプレー 液体 ハード モール nikon iphone 13promax 13 ipad 12pro iphone13プロ max 12 13pro ストラップ キャップホルダー 52mm 富士フイルム"},
        "ラッピング袋": {"ctname": "日用品・文房具・手芸用品>文房具・事務用品・画材>ラッピング用品>袋", "y_ct": "2084246663", "sex": "0", "male": "",
                   "female": "", "wowma_catid": "54112208", "wowma_catname": "日用品・文房具・手芸用品>文房具・事務用品・画材>ラッピング用品>袋",
                   "qoo_catid": "320000539", "qoo_catname": "文具_文房具_ギフトラッピング用品",
                   "s_keyword": "可愛い 透明 手提げ 小さい 誕生日 大量 お菓子 お祝い プレゼント用  特大 小さめ 大きめ 大 小 ビニール 大きい 紙袋 安い セット 大きめ大容量 かわいい バレンタイン opp プレゼント袋 ラッピング 袋 ありがとう 青 赤 麻 アニマル アクセサリー 明日 厚手 赤ちゃん 一枚 犬 犬柄 色々 インディゴ 色紙サイズ うさぎ ウルトラマン ウサギ 海 絵本 鉛筆 オシャレ 大き目 巾着"},
        "バンカーリング": {"ctname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>スマホリング", "y_ct": "2084246663", "sex": "0", "male": "",
                    "female": "", "wowma_catid": "410511", "wowma_catname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>スマホリング",
                    "qoo_catid": "320002283", "qoo_catname": "スマートフォン・タブレットPC_スマートフォン用アクセサリー_その他スマートフォン用アクセサリー",
                    "s_keyword": "マグネット 薄型 magsafe キャラクター 透明  ワイヤレス充電対応 iphone アンカー 強力 マグネット車載器対応 マグネット対応 マグネット付き 車 x 2mm アイフォン13ミニ ゴールド 磁石 1mm グリーン magsafe対応 取り外し anker アニメ 貼り直し ハート 蝶 おすすめ 黒 ブラック 星 かわいい ワイヤレス ストラップ  ケース 赤  青 あいふぇいす アイリング アウトレット アイアンマン アベンジャーズ 犬 イーブイ 痛くない 一体化 iphone12"},
        "ラウンドネック": {"ctname": "スポーツ・アウトドア>アウトドア>アウトドアウェア>その他アウトドアウェア", "y_ct": "2084246663", "sex": "0", "male": "",
                    "female": "", "wowma_catid": "40110201", "wowma_catname": "スポーツ・アウトドア>アウトドア>アウトドアウェア>その他アウトドアウェア",
                    "qoo_catid": "300000237", "qoo_catname": "アウトドア_登山用品_アウトドアウェア",
                    "s_keyword": "レディース メンズ パーカー tシャツ パーカーメンズ プルオーバー シャツレディース ダウン ジャケット シャツ インナー セットアップ カーディガン トップス ワンピース 無地 切り替え カジュアルワンピース カジュアル ブラウス カットソー 買わなきゃ損 長袖 アルファベット 春秋 メンズパーカー コート 下着 スリット チュニックレディース チュニック 五分袖 薄手 水玉 トレーナー ニットセーター ニット リボン ロング フォーマル ベスト /jyuryu 吸汗速乾 uvカット ストレッチ 見逃せない 配色 s-3xl パーカー/フーディー"},
        "iphone ケース": {"ctname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>スマホケース", "y_ct": "2084246663", "sex": "0", "male": "",
                       "female": "", "wowma_catid": "410509", "wowma_catname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>スマホケース",
                       "qoo_catid": "320002219", "qoo_catname": "スマホケース・保護フィルム_iPhoneケース_その他 iPhone ケース",
                       "s_keyword": "ショルダー se 12 13 11 13pro mini 11pro xs クリア おしゃれ 韓国 くすみ 韓国12pro 12mini 8 se2 第2世代 se3 第一世代 手帳型 第3世代 セーラームーン キャラクター かわいい ハート オシャレ 花 チェーン キラキラ にこちゃん ゼロハリバートン  13promax 手帳 13手帳型 可愛い 人気 13mini 吸盤式 ブランド x xr x13 13pro 13 プリンセス 12pro 透明 ヴィランズ 12promax"},
        "トレーニンググローブ": {"ctname": "ダイエット・健康>ダイエット>ダイエット・フィットネス器具>シェイプアップグッズ", "y_ct": "2084246663", "sex": "0",
                       "male": "", "female": "", "wowma_catid": "42030605",
                       "wowma_catname": "ダイエット・健康>ダイエット>ダイエット・フィットネス器具>シェイプアップグッズ", "qoo_catid": "320001859",
                       "qoo_catname": "ダイエット・矯正_シェイプアップ・ダイエットグッズ_エクササイズグッズ",
                       "s_keyword": "レディース メンズ 野球 soomloom tra-033 ゴールドジム フルフィンガー ハーフ 人気  筋トレ 革 メンズグロ レッド ウィメンズ スラッガー ハービンジャー 厚手 赤 洗える アイロテック かわいい 可愛い tmt ウェイトトレーニング サイクリンググローブ 薄手 ウェイト ウエイト オープン オールアウト 女 おしゃれ 重り オレンジ カモフラ キッズ用ss 黄色 キャッチャー キッズ クッション 黒 懸垂 けんすい 硬式 子供 コブラ シーク 滑り止め スポーツ"},
        "ミニ財布": {"ctname": "バッグ・財布・ファッション小物>財布>その他財布", "y_ct": "2084246663", "sex": "0", "male": "", "female": "",
                 "wowma_catid": "450802", "wowma_catname": "バッグ・財布・ファッション小物>財布>その他財布", "qoo_catid": "300002166",
                 "qoo_catname": "バッグ・雑貨_財布・ポーチ_その他",
                 "s_keyword": "レディース メンズ 人気 三つ折り財布 ブランド レアリーク お札が折れない ラシエム がま口 二つ折り 薄型 本革 三つ折り 安い カード多め 3つ折り 人気ブランド 薄い 韓国 人気猫柄 2つ折り チャーリーブラウン アルディ キャスキッドソン グリーン セリーヌ ゴールド アウトレット クロエ ブランド風 お札が折れない日本製 お札が折れない薄い キー かわいい バレンシアガ アウトドア 赤 アブラサス アニメ 青 アイボリー イラスト イタリアンレザー 印伝 犬 イタリア いちご うさぎ box小銭 宇宙"},
        "ロングTシャツ": {"ctname": "レディースファッション>トップス>ロングTシャツ", "y_ct": "2084246663", "sex": "0", "male": "", "female": "",
                    "wowma_catid": "510820", "wowma_catname": "レディースファッション>トップス>ロングTシャツ", "qoo_catid": "300002252",
                    "qoo_catname": "レディースファッション_トップス_Tシャツ・カットソー",
                    "s_keyword": "ロングtシャツ メンズ 大きいサイズ ブランド スポーツ 厚手 速乾 vネック セット チャンピオン レディース 長袖 半袖 ワンピース 白 ゆったり 韓国 パタゴニア キッズ 2xl 5l 作業服 登山 ポリエステル 女の子 130 120 150 110 140 男の子 吸汗速乾 丸首 cm4hq202 長袖tシャツ 綿100% 定番 ワンポイントロゴ刺繍 c3-p401 バスケ ロングtシャツusa バスケットボール 赤 スポーツブランド アニメ アウトドア 赤ちゃん インナー 犬 薄手 海"},
        "イヤホン ストラップ": {"ctname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>イヤホンジャック・ピアス", "y_ct": "2084246663", "sex": "0",
                       "male": "", "female": "", "wowma_catid": "410504",
                       "wowma_catname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>イヤホンジャック・ピアス", "qoo_catid": "320002280",
                       "qoo_catname": "スマートフォン・タブレットPC_スマートフォン用アクセサリー_イヤホンジャック",
                       "s_keyword": "落下防止 イヤフォン ホルダー メンズ レディース 紛失防止 バンドホルダー wf-1000xm4 アンカー ピアス ストラップ イヤホンじゃっく ぶるーとぅーす bluetooth イヤホン ワイヤレス"},
        "AirPods": {"ctname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>その他スマホアクセサリー", "y_ct": "2084246663", "sex": "0", "male": "",
                    "female": "", "wowma_catid": "410501", "wowma_catname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>その他スマホアクセサリー",
                    "qoo_catid": "320002283", "qoo_catname": "スマートフォン・タブレットPC_スマートフォン用アクセサリー_その他スマートフォン用アクセサリー",
                    "s_keyword": "airpods pro 第3世代 ケース proケース max イヤーピース 3 充電ケース おしゃれ  かわいい apple イヤーチップ キャラクター シリコン カバー 第2世代 韓国 ブランド 可愛い クリア proケース透明 スタンド イヤーパッド 充電スタンド case ケーブル アウトレット 純正 ss あいrぽds azla ウレタン 滑り止め 低反発 m 透明  3世代 アクセサリー  落下防止 アップルウォッチ 充電器 アップル 充電器スタンド ケース アニメ アダプタ 赤"},
        # N/A
        "ニップレス": {"ctname": "インナー・ルームウェア>レディースインナー>ブラ>ブラトップ", "y_ct": "2084246663", "sex": "0", "male": "",
                  "female": "", "wowma_catid": "32070611", "wowma_catname": "インナー・ルームウェア>レディースインナー>ブラ>ブラトップ",
                  "qoo_catid": "300002904", "qoo_catname": "下着・レッグウェア_ブラジャー_シリコンブラ",
                  "s_keyword": "レディース メンズ 男性用 女性 女性用 シリコン 繰り返し シール かぶれない 使い捨て 水泳 ガーゼ インナー シャツ スポーツ 20組 40枚 薄型 乳首隠し 服 福 大きめ 日本製 肌に優しい 大 男女兼用 男 ケース 可愛い と は 防水 ハート シール可愛い シールド menon 120枚 洗える 赤 厚め アクセサリー 汗 上げる 青 医療用 陰部 色 医療 運動 うさぎ"},
        "パールビーズ": {"ctname": "日用品・文房具・手芸用品>手芸・クラフト・生地>ビーズ>パール", "y_ct": "2084246663", "sex": "0", "male": "",
                   "female": "", "wowma_catid": "54091213", "wowma_catname": "日用品・文房具・手芸用品>手芸・クラフト・生地>ビーズ>パール",
                   "qoo_catid": "300000524", "qoo_catname": "日用品雑貨_手芸・裁縫_その他",
                   "s_keyword": "穴なし 6mm 穴あり 3mm 4mm 10mm 2mm 穴有り 8mm 大量 ブラシスタンド 12mm 6ミリ 紫 穴あり3 穴大きめ 穴無し 赤 大きい 大粒 大穴 片穴 カラー 極小 金 黒 ショーツ 手芸 白 シルバー しずく チュールコサージュ チェーン 釣り トーホー ナツメ ネックレス ハート 半円 半球 変形 本 ミックス つや消し銀 紗や工房 両穴 かんざし グリーン グレー ゴールド"},
        "マルチフック": {"ctname": "キッズベビー・マタニティ>ベビー>ベビーカー・おでかけ>ベビーカー用フック", "y_ct": "2084246663", "sex": "0", "male": "",
                   "female": "", "wowma_catid": "34050606", "wowma_catname": "キッズベビー・マタニティ>ベビー>ベビーカー・おでかけ>ベビーカー用フック",
                   "qoo_catid": "320000830", "qoo_catname": "キッチン用品_キッチン雑貨_フック",
                   "s_keyword": "キーパー vik 工具 車 手ぶくろ 自転車 バイク ベビーカー 富士工業 トラスコ カラビナ 腹ペコあおむし 壁 キッチン タオル タフト ひつじのショーン active winner ベビーカーフック 360度回転 荷物フック es m6 umbra スティックス"},
        "名刺ケース": {"ctname": "バッグ・財布・ファッション小物>ファッション小物>名刺入れ", "y_ct": "2084246663", "sex": "0", "male": "", "female": "",
                  "wowma_catid": "450421", "wowma_catname": "バッグ・財布・ファッション小物>ファッション小物>名刺入れ", "qoo_catid": "320001113",
                  "qoo_catname": "メンズバッグ・シューズ・小物_財布_名刺入れ・カードケース",
                  "s_keyword": "メンズ レディース プラスチック 大容量 アルミ ステンレス 100枚 革 木製 ブランド 印伝 名入れ 木 オシャレ かわいい 可愛い ねこ 人気 安い 牛革 薄型 100個 200枚 プラスチック製 透明 50枚 ミク 黒 1個 紙箱 アニメ 赤 アクリル アイマス アルバム インデックス イタリアンレザー 犬 スリム 背面ポケット ウルトラマン 海上自衛隊 エヴァンゲリオン おしゃれ おもしろ 音楽 面白い 大きめ 折れない 紙"},
        "ストッキング": {"ctname": "インナー・ルームウェア>タイツ・レギンス>ストッキング", "y_ct": "2084246663", "sex": "0", "male": "", "female": "",
                   "wowma_catid": "320303", "wowma_catname": "インナー・ルームウェア>タイツ・レギンス>ストッキング", "qoo_catid": "300000049",
                   "qoo_catname": "下着・レッグウェア_靴下・レッグウェア_ストッキング・タイツ",
                   "s_keyword": "膝下 着圧 黒 厚手 大きいサイズ 滑り止め ゆったり サブリナ ベージュ ベージュ膝下 加圧 ベージュ30デニール ベージュ安い ベージュ光沢 ベージュ大きい 膝上 3l 5l 4l 伝線しにくい ラメ 7l 20デニール 30デニール  野球 60デニール 80デニール 40デニール  セット 靴下 靴下屋 くるぶし サワーベージュ 消臭 マタニティ 2枚組 犬印 3枚組 伝染しにくい sm ll xl 強 肌 圧 シアーベージュ ひざ下 なめらか スキニーベージュ"},
        "EMS": {"ctname": "ダイエット・健康>ダイエット>ダイエット・フィットネス器具>EMS", "y_ct": "2084246663", "sex": "0", "male": "",
                "female": "", "wowma_catid": "42030601", "wowma_catname": "ダイエット・健康>ダイエット>ダイエット・フィットネス器具>EMS",
                "qoo_catid": "300000222", "qoo_catname": "スポーツ_フィットネス・ヨガ_フィットネス器具",
                "s_keyword": "ems 腹筋ベルト 美顔器 ジェルシート不要 足 顔 パッド 肩こり ジェル em生活 ジェル不要 日本製 人気 女性 2022 シックスパッド 太もも リフトアップ 目元 ほうれい線 ハンズフリー age-r 防水 ローラー 温熱 腕 3899 腹筋マシン 洗濯 120 足用 足裏マッサージ 足裏マット 筋トレ ヒップ むくみ 足やせ 足裏 フットマット たるみ ベルト 顔痩せ スティック ルルド 丸型 オムロン パッドなし フィンガルリンク 肩 丸 パッド不要"},
        "チュチュ スカート": {"ctname": "キッズベビー・マタニティ>ジュニア>子供服（ボトムス）>フレアスカート", "y_ct": "2084246663", "sex": "0", "male": "",
                      "female": "", "wowma_catid": "34021010", "wowma_catname": "キッズベビー・マタニティ>ジュニア>子供服（ボトムス）>フレアスカート",
                      "qoo_catid": "320001579", "qoo_catname": "ベビー・マタニティ_ベビー服_スカート",
                      "s_keyword": "ベビー キッズ 大人 子供 チュチュスカート インナー 黒 白 ミニ レインボー ロング グレー ダンス ドット ブラック ボリューム パニエ ピンク 120 100 130"},
        "ロングスカート": {"ctname": "レディースファッション>スカート>その他スカート", "y_ct": "2084246663", "sex": "0", "male": "", "female": "",
                    "wowma_catid": "510601", "wowma_catname": "レディースファッション>スカート>その他スカート", "qoo_catid": "300002764",
                    "qoo_catname": "レディースファッション_スカート_ロングスカート",
                    "s_keyword": "レディース 春夏 春 大きいサイズ 黒 白 タイト ワンピース 冬 花柄 夏 チェック フリル 裏地付き aライン 春夏秋 ウエストゴム スウェット フォーマル デニム 演奏会 レース プリーツ ゴム フレア 可愛い スリット 大きい マーメイド パール 綿 フ 白デニム 白黒 タイト上下 タイトレディース ジャージ ティアード 赤 青 アシンメトリー 麻 青チェック 秋冬 アジアン アウトドア 衣装 イレギュラー インナー付き 裏地"},
        "ショルダーバック": {"ctname": "キッズベビー・マタニティ>キッズ>バッグ・ランドセル>ショルダーバッグ", "y_ct": "2084246663", "sex": "0", "male": "",
                     "female": "", "wowma_catid": "34010404", "wowma_catname": "キッズベビー・マタニティ>キッズ>バッグ・ランドセル>ショルダーバッグ",
                     "qoo_catid": "320001471", "qoo_catname": "メンズバッグ・シューズ・小物_メンズバッグ_ショルダーバッグ",
                     "s_keyword": "れディース 人気 小さめ カジュアル 男性 革 斜めがけ a4サイズ 大容量 おすすめ 皮 レディース 斜めがけ小さめ 斜めがけ軽量 斜めがけブランド 斜めがけミニ 斜めがけ革 斜めがけ人気 pu 布 れレディース れレディース人気 れレディース斜めがけ れレディース小さめ れレディース安い れレディース大容量 れレディース大きめ ブランド れレディース50歳 レディース人気 可愛い メンズ とりばーち 女性 ななめがけ 女性用 a4 アウトドアブランド 赤 アニメ アイパッド 洗える 男性 アルファ アイボリー 犬 運動 ウエットティッシュ 薄い 薄型 薄手"},
        "リブレギンス": {"ctname": "レディースファッション>パンツ>スパッツ・レギンス", "y_ct": "2084246663", "sex": "0", "male": "", "female": "",
                   "wowma_catid": "511011", "wowma_catname": "レディースファッション>パンツ>スパッツ・レギンス", "qoo_catid": "320001852",
                   "qoo_catname": "ダイエット・矯正_シェイプアップ・ダイエットグッズ_着圧レギンス・スパッツ",
                   "s_keyword": "レディース  キッズ スリット 着圧 80 ベビー 120 パンツ 白 くすみ 130 70 赤ちゃん 厚手 大きいサイズ ミルクティー マタニティ もっちりコットン ホワイト メロウ 綿 グレー パープル devirock s 100 110 160 10分丈 4l 7分丈 8分丈 90"},
        "カバーケース": {"ctname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>スマホケース", "y_ct": "2084246663", "sex": "0", "male": "",
                   "female": "", "wowma_catid": "410509", "wowma_catname": "スマホ・タブレット・モバイル通信>スマホアクセサリー>スマホケース",
                   "qoo_catid": "320002232", "qoo_catname": "スマホケース・保護フィルム_その他スマホケース_多機種対応ケース",
                   "s_keyword": "surface laptop 4  13.5 15インチ 純正 水色 かわいい キャラクター あつ森 go3 ホワイト マニア エクスペディア galaxy se iphone13 pro s22 b5 イルマワン あいぱっとだい8世代 あいぱっとえあー4 えあーぽっつ プロ ふぁーうえい mini iphone 13がんじょう ipad air お絵描き iphone12 おしゃれ パソコン かわいい15インチ キーボード付き 第9世代 山崎産業 ラバーカップ 洋式 al付き トイレ つまり取り al 付き 139880 iphonese3 滑りにくい ぐーぐるぴくせる6"},
        "メッシュバッグ": {"ctname": "スポーツ・アウトドア>マリンスポーツ>ダイビング・シュノーケリング>メッシュバッグ", "y_ct": "2084246663", "sex": "0", "male": "",
                    "female": "", "wowma_catid": "40370612",
                    "wowma_catname": "スポーツ・アウトドア>マリンスポーツ>ダイビング・シュノーケリング>メッシュバッグ", "qoo_catid": "300000117",
                    "qoo_catname": "バッグ・雑貨_バッグ_その他",
                    "s_keyword": "砂場 水泳 アリーナ ダイビング 大容量 温泉 レディース トート 小 おもちゃ l 白 dean 小さめ 小型 小さい 巾着 アウトドア 洗える インポーチ付き イスカ 海 バッグ 洗濯ネット ジムバッグ 軽量 チャック ホワイト ランドリーネット 鞄 袋 手さげ袋 お風呂 大きい おしゃれ 大型 お砂場 大きめ 女の子 折りたたみ 肩掛け かわいい 革 可愛い カラビナ カラフル 競泳 キャンプ キッズ 黒"},
        "バックパック": {"ctname": "バッグ・財布・ファッション小物>バッグ>バックパック・リュック", "y_ct": "2084246663", "sex": "0", "male": "",
                   "female": "", "wowma_catid": "450313", "wowma_catname": "バッグ・財布・ファッション小物>バッグ>バックパック・リュック",
                   "qoo_catid": "300002169", "qoo_catname": "バッグ・雑貨_バッグ_リュック・デイパック",
                   "s_keyword": "大容量 防水 40l メンズ ミリタリー レディース 30l 野球 通学 60l 80l キャンプ バイク 防水カバー 軽量 ビジネス 登山 旅行 30 キッズ ヒューズ ホットショット 10l おしゃれ レザー 大容量90リッター 小さめ ミリタリー100 20l 50l ネイビー ブランド 釣り アウトドア アクセサリー 赤 青 椅子付き インケース インナーバッグ 椅子 犬 イギリス 一眼 イタリア イス 薄型 ウエストベルト ウルトラライト 後付け"},
        "シフォンシャツ": {"ctname": "レディースファッション>トップス>シャツ", "y_ct": "2084246663", "sex": "0", "male": "", "female": "",
                    "wowma_catid": "510807", "wowma_catname": "レディースファッション>トップス>シャツ", "qoo_catid": "300000418",
                    "qoo_catname": "キッズ_女の子ファッション_Tシャツ・ブラウス",
                    "s_keyword": "レディース ブラウス 長袖 大きいサイズ 春 黒 メンズ キッズ 白 レース 刺繍 子供用ブラウス ホワイト レッド 春秋着 秋物 シャツ 子供服 無地 女の子 リンクコーデ 長袖シャツ カジュアル"},
        "オフショルダー": {"ctname": "レディースファッション>トップス>その他トップス", "y_ct": "2084246663", "sex": "0", "male": "", "female": "",
                    "wowma_catid": "510802", "wowma_catname": "レディースファッション>トップス>その他トップス", "qoo_catid": "300000013",
                    "qoo_catname": "レディースファッション_トップス_シャツ・ブラウス",
                    "s_keyword": "ワンピース 大きいサイズ ロング 夏 フレア ワンピースミニ マキシ 春 水着 長袖 トップス キッズ 冬 白 メンズ 半袖  レディース インナー ブラウス ニット 5l tシャツ カップ付き 赤 秋 アシンメトリー アウター えろ 襟付き 女の子 おおきいサイズ 大きい オールインワン カットソー 韓国 重ね着 カーディガン かわいい 肩出し 型紙 黄色 キャミ キャバドレス 黒 子供 コスプレ サテン シャツ 下着 シースルー"},
        "レインカバー": {"ctname": "キッズベビー・マタニティ>ベビー>ベビーカー・おでかけ>レインカバー", "y_ct": "2084246663", "sex": "0", "male": "",
                   "female": "", "wowma_catid": "34050612", "wowma_catname": "キッズベビー・マタニティ>ベビー>ベビーカー・おでかけ>レインカバー",
                   "qoo_catid": "300000081", "qoo_catname": "メンズバッグ・シューズ・小物_メンズシューズ_その他",
                   "s_keyword": "ベビーカー  コンビ アップリカ ピジョン b型 両対面 サイベックス グレコ 人気 自転車 後ろ リュック ランドセル ビッケ 靴 前 チャイルドシート バッグ ogk ヤマハ ラボクル 後ろかご bikke 30l 25l 反射 20l 50l 40l 45l 特大 女の子 男 防水 透明 ユニコーン すみっこ 星座 赤 アリサナ フロント 前乗せ 後付け 純正 ブリヂストン リア キッズ バイク 子ども 子供"},
        "セットアップ": {"ctname": "キッズベビー・マタニティ>キッズ>子供服（オールインワン）>セットアップ", "y_ct": "2084246663", "sex": "0", "male": "",
                   "female": "", "wowma_catid": "34010703", "wowma_catname": "キッズベビー・マタニティ>キッズ>子供服（オールインワン）>セットアップ",
                   "qoo_catid": "320001096", "qoo_catname": "メンズファッション_その他メンズファッション_セットアップ",
                   "s_keyword": "メンズ 大きいサイズ 夏 春 おしゃれ カジュアル  スーツ 上下 レディース フォーマル 韓国 スウェット スカート パンツ etc 車載機 込み 入園式 ママ レディース 2.0 軽自動車 バイク 新セキュリティ シガーソケット アンテナ一体型 24v 一体型 きれいめ 春夏 10代 30代 白 安い ベージュ 千鳥格子 b系 大きいサイズ夏 ジャケット 夏用 七分 半袖 夏服 夏 夏物 麻 花柄 無地 パンツスーツ フォーマルスカート"},
        "リボンベルト": {"ctname": "バッグ・財布・ファッション小物>ベルト>リボンベルト", "y_ct": "2084246663", "sex": "0", "male": "", "female": "",
                   "wowma_catid": "450512", "wowma_catname": "バッグ・財布・ファッション小物>ベルト>リボンベルト", "qoo_catid": "300000124",
                   "qoo_catname": "バッグ・雑貨_ベルト_レディースベルト",
                   "s_keyword": "レディース メンズ 大きいサイズ サテン 子供 黒 白 時計 スニーカー ox 革 ドレス 赤 靴 ワンピース ゴールド converse スリッポン as ribbonbelt オールスター スウェーデン製 nato ナトータイプ 20mmグラフィック 31304040 31304041"},
        "ブローチ": {"ctname": "アクセサリー・ジュエリー>ブローチ・コサージュ>その他ブローチ・コサージュ", "y_ct": "2084246663", "sex": "0", "male": "",
                 "female": "", "wowma_catid": "301501", "wowma_catname": "アクセサリー・ジュエリー>ブローチ・コサージュ>その他ブローチ・コサージュ",
                 "qoo_catid": "320001458", "qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_ブローチ",
                 "s_keyword": "卒業式 入学式 パール ピン 花 真珠 大きめ スーツ ママ 人気 子ども シンプル シルバー フォーマル ゴールド サークル リボン 桜 子供用 子供 25mm 30mm 15mm 20mm 日本製 回転式 台座 ハンドメイド パーツ クローバー ブラック バイオリン スワロフスキー動物 アナグラム 本物 アンティーク ピンク 花輪 布 花瓶 黄色 kawaii ミキモト 入園式 冠婚葬祭 冠 婚 葬祭 薔薇 あこや"},
        "ボディピアス": {"ctname": "アクセサリー・ジュエリー>ボディピアス", "y_ct": "2084246663", "sex": "0", "male": "", "female": "",
                   "wowma_catid": "3019", "wowma_catname": "アクセサリー・ジュエリー>ボディピアス", "qoo_catid": "320001456",
                   "qoo_catname": "腕時計・アクセサリー_アクセサリー・ジュエリー_ピアス",
                   "s_keyword": "16g 14g 18g 専門店jewel's セット リング 00g キャッチ 12g ラブレット ゴールド 黒 サージカルステンレス 8mm 軟骨 ストレートバーベル つけっぱなし へそ ブラック パール スパイラル セグメント ニードル ステンレス 6g リングボール 20g リングセット シリコン アクリル クリア プラグ シングルフレア フレア ハート 00ゲージ ボール キャッチのみ オーリング キャッチなし 4g キャッチャー バーベル サーキュラー 10mm 透明 トンネル 12ゲージ 凛 アレルギー対応"},
        "ツインコーム": {"ctname": "アクセサリー・ジュエリー>ヘアアクセサリー>コーム", "y_ct": "2084246663", "sex": "0", "male": "", "female": "",
                   "wowma_catid": "301605", "wowma_catname": "アクセサリー・ジュエリー>ヘアアクセサリー>コーム", "qoo_catid": "300000127",
                   "qoo_catname": "バッグ・雑貨_ヘアアクセサリー_その他", "s_keyword": "髪留め ダブルコーム ビーズ ミニ"},
        "メイクブラシ": {"ctname": "ビューティ・コスメ>メイク道具・ケアグッズ>その他メイク道具・ケアグッズ", "y_ct": "2084246663", "sex": "0", "male": "",
                   "female": "", "wowma_catid": "471202", "wowma_catname": "ビューティ・コスメ>メイク道具・ケアグッズ>その他メイク道具・ケアグッズ",
                   "qoo_catid": "320001725", "qoo_catname": "メイク小物_メイク道具_メイクブラシ",
                   "s_keyword": "セット 人気 ケース クリーナー スタンド マリリン  収納 熊野筆 かわいい  くまのふで  安い ケース付き 日本製 可愛い ケースつき ピンク 人気熊野 天然毛 蓋付き 持ち運び 小さい コンパクト 自立 腰巻 パール プロ 電動 スプレー 速乾 クリーナーマット  スポンジ mac シリコン ドライ 大理石 アクリル 乾燥 大容量 蓋 単品 フェイスブラシ 11本 マミ様 ふた付き ポーチ 収納ボックス"},
        "ダーツ": {"ctname": "おもちゃ・ホビー > その他 > マグネット ダーツ リバーシブル セット 磁気 の 矢 4本", "y_ct": "2084246663", "sex": "0",
                "male": "", "female": "", "wowma_catid": "291101", "wowma_catname": "おもちゃ・趣味>ダーツ>その他ダーツ",
                "qoo_catid": "320000668", "qoo_catname": "ホビー・コスプレ_ダーツ・ビリヤード・遊技機_ダーツ",
                "s_keyword": "ボード ケース ライブホーム フライト バレル スタンド シャフト ライブ チップ ハード ソフト スマホ連動 ブラケット 電子ボード 初心者 初中級者向け 自動採点 音声機能 ゲーム 競技 練習 静音モード 多人ゲーム インテリア おしゃれ カメオ 2セット収納 トリニダード アルミ コンパクト 可愛い ピンク 革 led ライト セグメント セット ledライト ネジ 白 一体型 エルスタイル フライトケース シェイプ フィット スリム ロケット l-style ティアドロップ タングステン"},
        "トレーニングベル": {"ctname": "インテリア/生活雑貨 > 青×黒 ペット 犬 猫 トレーニングベル 呼び鈴 コールベル おもちゃ", "y_ct": "2084246663", "sex": "0",
                     "male": "", "female": "", "wowma_catid": "491108", "wowma_catname": "ペット・ペットグッズ>犬用品・ドッグフード>しつけ用品",
                     "qoo_catid": "300002816", "qoo_catname": "ペット_犬用品_しつけ用品",
                     "s_keyword": "レディース ゴールドジム 筋トレ 腰 ナイロン レザー レバーアクション ハービンジャー シーク 犬 ペット 足 赤 トレーニング ウェア メンズ 上下 ウエイト 腕 ウェイト ウォーターバッグ ウエア上下 円盤 エナジー サコッシュ ユニセックス 1.5l 栄養学 エルボースリーブ エアロバイク 変動 エルボー 栄養 円柱 重り おもり 足首 おむつ オムツ お箸 オーバーサイズ tシャツ 革 加重 カスタム 器具"},
        "夜行テープ": {"ctname": "インテリア/生活雑貨 > インテリア > その他", "y_ct": "2084246663", "sex": "0", "male": "", "female": "",
                  "wowma_catid": "40110507", "wowma_catname": "スポーツ・アウトドア>アウトドア>アウトドア用品>ヘッドライト",
                  "qoo_catid": "320000765", "qoo_catname": "アウトドア_キャンプ用品_ライト・ランタン", "s_keyword": "ピンク"},
        "虫よけ": {"ctname": "DIY・工具 ", "y_ct": "2084246663", "sex": "0", "male": "", "female": "",
                "wowma_catid": "34051924", "wowma_catname": "キッズベビー・マタニティ>ベビー>衛生・ヘルスケア>虫よけ用品", "qoo_catid": "300000487",
                "qoo_catname": "日用品雑貨_生活雑貨_虫よけ剤・スプレー",
                "s_keyword": "バリア スプレー 吊り下げ ネット 366日 玄関 置き型 バリアスプレー プレミアム 網戸 バリアブラック ブラック 虫こないアース ワンプッシュ 大容量 リッチ 室内 ベランダ 屋外 蚊 かわいい アロマ ペット 帽子 園芸 ネットパーカー 農業 ネット付き帽子 プランター 1年 3xパワー ベランダ用 無香料 365日用 虫除け プレート 1年用 バリアプレミアム アミ戸にピタッ 300日用 2個 網戸用 アミ戸 玄関とベランダ あみ戸"},
        "工具": {"ctname": "DIY・工具 ", "y_ct": "2084246663", "sex": "0", "male": "", "female": "", "wowma_catid": "292808",
               "wowma_catname": "おもちゃ・趣味>模型・プラモデル>工具", "qoo_catid": "320000870",
               "qoo_catname": "ガーデニング・DIY・工具_DIY工具_手動工具",
               "s_keyword": "セット ktc レザークラフト プラモデル ktcツールセット 家庭用 電気工事士 2種 アストロプロダクツ バイク 日本製  バッグ 入れ ニックス 差し 箱 ツールボックス 大型 小型 大容量 ショルダー リュック 腰 sk11 小さい 激安 2022 9.5 キャビネット 91点 12.7 12.7sq 67点 腰袋 ツールバッグ ポーチ ボックス ロール ケース 革 チェーン 黒 赤 ナイロン 3段 2段 コーデュラ 初心者 クラフト社 seiwa"},
        "両面テープ": {"ctname": "DIY・工具 ", "y_ct": "2084246663", "sex": "0", "male": "", "female": "",
                  "wowma_catid": "540928", "wowma_catname": "日用品・文房具・手芸用品>手芸・クラフト・生地>接着テープ・接着芯",
                  "qoo_catid": "320001525", "qoo_catname": "文具_文房具_セロハンテープ",
                  "s_keyword": "強力 3m 超強力 はがせる マジックテープ 付き クッションフロア 車 外装 屋外 厚手 薄い 外壁用 フック 壁紙 車外装用 丸型 内装 壁紙用 布 エーモン 車外 剥がせる 透明 壁 白 布用 丸 3cm オス 賃貸 50mm 東リ 30mm 40mm ニトムズ 10mm 5mm幅 8ミリ 外装5ミリ 15 厚さ3mm 厚め 厚み5mm あとが残らない 厚さ2mm 厚 厚い アクリル 医療用"},
        "お菓子入れ": {"ctname": "おもちゃ・ホビー > その他", "y_ct": "2084246663", "sex": "0", "male": "", "female": "",
                  "wowma_catid": "351816", "wowma_catname": "キッチン・食器・調理>製菓用品・器具>和菓子用器具", "qoo_catid": "300000539",
                  "qoo_catname": "食品_スイーツ・お菓子_その他",
                  "s_keyword": "容器 卓上 カゴ る箱 蓋付き おしゃれ かご 赤ちゃん 袋 容器プラスチック 持ち運び オシャレ る容器可愛い 卓上北欧風 木 大容量 お洒落 バスケット 缶 ガラス 袋 アンティーク 入れ物が可愛いお菓子 お菓子 入れ物 可愛い 犬 うさぎ 缶ペンケース 筆箱 小物入れ グッズ 企業 レトロ 駄菓子 復刻版 a 名入れ おめでとう お供え 御菓子 のし付き法事 お皿 折りたたみ 大きい 缶のみ カゴ 鞄 かわいい"},
        "鳥グッズ": {"ctname": "ペット用品", "y_ct": "2084246663", "sex": "0", "male": "", "female": "", "wowma_catid": "491301",
                 "wowma_catname": "ペット・ペットグッズ>小動物・鳥用品>フード・おやつ・ドリンク・サプリメント", "qoo_catid": "320000701",
                 "qoo_catname": "ペット_鳥用品_その他",
                 "s_keyword": "雑貨 プレゼント 文房具 あだるとグッズ 立鳥 鳥 グッズ 可愛い かわいい 囀る鳥は羽ばたかない うらみちお兄さん 小鳥さん 千鳥 お笑い 文鳥 おもちゃ 鍵 鳥好き ふろしき文鳥 焼き 鳥避けグッズ 害鳥よけグッズ 鳥よけグッズ シマエナガ クリップ 小鳥 ことりクリップ しろ文鳥 癒しグッズ c すずめ 鳩よけ ツバメ 対策 猫よけ とげマット 害獣除け ベランダ 軒下用 とげシート 14枚セット クリア トート 火の鳥 近鉄 手塚治虫 止まり木 インコ ケージ スタンド とまり木 鳥かご 遊び場 食器 付き"},
        "猫のおもちゃ": {"ctname": "ペット用品", "y_ct": "2084246663", "sex": "0", "male": "", "female": "",
                   "wowma_catid": "491201", "wowma_catname": "ペット・ペットグッズ>猫用品・キャットフード>キャットフード・おやつ・ドリンク・サプリメント",
                   "qoo_catid": "300002817", "qoo_catname": "ペット_猫用品_おもちゃ",
                   "s_keyword": "電動 ボール ねずみ 魚 人気 電動じゃらし エビ もぐらたたき 回転 ネズミ 動く エビフライ ぬいぐるみ 釣り竿 あきもと 猫ちゃんのかつお削り 芋虫 イカ いちご いもむし うさぎの毛 えび お寿司 おやつ 海老 カサカサ カシャカシャブンブン かわいい かに 巨大 吸盤 動く魚のおもちゃ 猫 けたぐり けりぐるみ ケリケリ 子供 昆虫 さんま さかな サメ 自然素材 鈴入り 鈴 寿司 セット たいやき タイムセール 蝶々 替え"},
        "ブランケット": {"ctname": "ブランケット", "y_ct": "2084246663", "sex": "0", "male": "", "female": "",
                   "wowma_catid": "40110910", "wowma_catname": "スポーツ・アウトドア>アウトドア>テント>レジャーシート・ブランケット",
                   "qoo_catid": "320000022", "qoo_catname": "寝具・ベッド・マットレス_毛布・ブランケット・タオルケット_ブランケット",
                   "s_keyword": "夏用 大判 キャンプ ペンドルトン おしゃれ 膝掛け クリップ 北欧 アウトドア 小さめ シングル 赤ちゃん 子供 今治 ダブル ベビー キャラクター 夏 御洒落 ふわふわ 難燃 コンパクト キャンプ用 ネイティブ キャンプ春秋 メキシカン マット ウール タオル スパイダーロック ハーディング ローブ オシャレ お洒落 ひざ掛け 可愛い ダウン 電気 ベビーカー ミッキー 抱っこ紐 木製 パーツ くま 冬 洗える グリーン 羊毛 防寒 防水"},
        "リード": {"ctname": "リード", "y_ct": "2084246663", "sex": "0", "male": "", "female": "", "wowma_catid": "491601",
                "wowma_catname": "ペット・ペットグッズ>首輪・胴輪・リード>リード", "qoo_catid": "320001536", "qoo_catname": "ペット_犬用品_リード",
                "s_keyword": "犬 伸縮 10m ロング 小型犬 大型犬 8m 中型犬 ショルダー ハンズフリー  工業 lead ディフューザー ヘルメット 線 ケース クラリネット スティック キッチンペーパー クッキングペーパー シールド ジェットヘルメット フルフェイス ハーフヘルメット バイクヘルメット システムヘルメット bc-10 アイボリー/ネイビー フリーサイズ 57-60cm未満 スペアシールド xl 容器 詰め替え  木と果 大容量 ラベンダー ホワイトムスク ボトル ジェット ハーフ flx レディース シールドbc10 スモーク 大きいサイズ アース棒 線付"},
        "ボトルオープナー": {"ctname": "ボトルオープナー", "y_ct": "2084246663", "sex": "0", "male": "", "female": "",
                     "wowma_catid": "350602", "wowma_catname": "キッチン・食器・調理>キッチン用品・キッチン雑貨>その他キッチン用品・キッチン雑貨",
                     "qoo_catid": "300000504", "qoo_catname": "キッチン用品_キッチン雑貨_その他",
                     "s_keyword": "キーホルダー 壁掛け ペットボトル 壁 カラビナ リング ブロムス チタン ペットボトルパンチ 結婚式 シリコン アンティーク 缶 鍵 キー 強力 ステンレス ペッと 指輪 ワイン バタフライナイフ パーツ tc4 edc ミニレンチ チタン合金 マルチツール the friendly エクストララージ "},
        "クイックキー": {"ctname": "クイックキー", "y_ct": "2084246663", "sex": "0", "male": "", "female": "",
                   "wowma_catid": "350602", "wowma_catname": "キッチン・食器・調理>キッチン用品・キッチン雑貨>その他キッチン用品・キッチン雑貨",
                   "qoo_catid": "300000504", "qoo_catname": "キッチン用品_キッチン雑貨_その他",
                   "s_keyword": "キーホルダー 壁掛け ペットボトル 壁 カラビナ リング ブロムス チタン ペットボトルパンチ 結婚式 シリコン アンティーク 缶 鍵 キー 強力 ステンレス ペッと 指輪 ワイン バタフライナイフ パーツ tc4 edc ミニレンチ チタン合金 マルチツール the friendly エクストララージ "},
        "コンビネゾン": {"ctname": "コンビネゾン", "y_ct": "2084246663", "sex": "0", "male": "", "female": "",
                   "wowma_catid": "511101", "wowma_catname": "レディースファッション>ワンピース>その他ワンピース", "qoo_catid": "300002195",
                   "qoo_catname": "レディースファッション_ワンピース・ドレス_その他", "s_keyword": "レディース オールインワン すみっこ 黒 着ぐるみ 半袖"},
        "妊婦帯": {"ctname": "妊婦帯", "y_ct": "2084246663", "sex": "0", "male": "", "female": "", "wowma_catid": "34060311",
                "wowma_catname": "キッズベビー・マタニティ>マタニティ・ママ>マタニティインナー>妊婦帯・腹帯", "qoo_catid": "300000386",
                "qoo_catname": "ベビー・マタニティ_マタニティ_その他",
                "s_keyword": "パンツ パンツタイプ 犬印本舗 セット ピジョン 大きいサイズ び 夏用 ll パンツxl 犬印 夏 オールインワン ベルト 通気性 4l 3l 安産祈願 アカチャンホンポ 一体型 戌の日 妊婦 うつ伏せ クッション 運動 ウエスト アジャスター ウエディングドレス 運転 ウエハース ウェディングドレス ウエスト調整 上着 エンゼル カルシウム カフェラテ カフェインレス 肩凝り 肩こり 風邪薬 感染 鞄 サプリ カリウム 着圧ソックス キャミソール キーホルダー 着圧 着圧ソックス寝るよう 救急"},
    }

"""
    _MY_CT_CODES_KEYWORD = {
        "プリンセスドレス": {"ctname": "オークション > ファッション > レディースファッション > フォーマル > ウエディングドレス > プリンセスタイプ", "y_ct": "2084064269", "sex": "0", "male": "", "female": ""},
        "便利手帳": {"ctname": "オークション > 本、雑誌 > 住まい、暮らし、育児 > インテリア、家づくり", "y_ct": "2084008946", "sex": "0", "male": "", "female": ""},
        "リップブラシ": {"ctname": "オークション > ビューティー、ヘルスケア > コスメ、スキンケア > メイク道具、化粧小物 > ブラシ、チップ、コーム > その他", "y_ct": "2084228684", "sex": "0", "male": "", "female": ""},
        "鍋敷き": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > 収納、キッチン雑貨 > その他", "y_ct": "2084018482", "sex": "0", "male": "", "female": ""},
        "VGAケーブル": {"ctname": "オークション > コンピュータ > 周辺機器 > その他", "y_ct": "2084048551", "sex": "0", "male": "", "female": ""},
        "ブリーフ": {"ctname": "オークション > ファッション > メンズファッション > インナーウエア > ビキニ、ブリーフ > Mサイズ", "y_ct": "2084053066", "sex": "0", "male": "", "female": ""},
        "シャープペンシル": {"ctname": "オークション > 事務、店舗用品 > 文房具 > 筆記用具 > シャープペンシル", "y_ct": "2084040729", "sex": "0", "male": "", "female": ""},
        "VGA延長アダプタ": {"ctname": "オークション > 家電、AV、カメラ > その他", "y_ct": "23972", "sex": "0", "male": "", "female": ""},
        "HDMI変換アダプター": {"ctname": "オークション > 家電、AV、カメラ > 映像機器 > 映像用ケーブル > HDMIケーブル", "y_ct": "2084239134", "sex": "0", "male": "", "female": ""},
        "ハロウィン コスプレ 男性": {"ctname": "オークション > コミック、アニメグッズ > コスプレ衣装 > 男性用", "y_ct": "2084241340", "sex": "0", "male": "", "female": ""},
        "メモリカードホルダー": {"ctname": "オークション > コンピュータ > 周辺機器 > その他", "y_ct": "2084048551", "sex": "0", "male": "", "female": ""},
        "枕カバー": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > 寝具 > シーツ、カバー > 枕カバー", "y_ct": "2084245297", "sex": "0", "male": "", "female": ""},
        "ガーランド": {"ctname": "オークション > 住まい、インテリア > 季節、年中行事 > クリスマス > クリスマスツリー > 飾り、オーナメント", "y_ct": "2084283929", "sex": "0", "male": "", "female": ""},
        "ラグマット": {"ctname": "オークション > 住まい、インテリア > 家具、インテリア > カーペット、ラグ、マット > ラグ > ラグ一般", "y_ct": "2084304266", "sex": "0", "male": "", "female": ""},
        "シリコンふた": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > 収納、キッチン雑貨 > その他", "y_ct": "2084018482", "sex": "0", "male": "", "female": ""},
        "まつげブラシ": {"ctname": "オークション > ビューティー、ヘルスケア > コスメ、スキンケア > メイク道具、化粧小物 > ブラシ、チップ、コーム > メイクブラシセット", "y_ct": "2084228681", "sex": "0", "male": "", "female": ""},
        "テーブルクロス": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > テーブルリネン > テーブルクロス", "y_ct": "2084046784", "sex": "0", "male": "", "female": ""},
        "アルミバンパー": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0", "male": "", "female": ""},
        "ドアストッパー": {"ctname": "オークション > 住まい、インテリア > 工具、DIY用品 > 建築材料、住宅設備 > 内装 > 建具 > ドア、扉 > その他", "y_ct": "2084304484", "sex": "0", "male": "", "female": ""},
        "ケースオープナー": {"ctname": "オークション > アクセサリー、時計 > 時計用工具 > セット", "y_ct": "2084062479", "sex": "0", "male": "", "female": ""},
        "サポーター": {"ctname": "オークション > ビューティー、ヘルスケア > 健康用品、健康器具 > サポーター > その他", "y_ct": "2084216486", "sex": "0", "male": "", "female": ""},
        "Pro用ケース": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0", "male": "", "female": ""},
        "カーラー": {"ctname": "オークション > ビューティー、ヘルスケア > コスメ、スキンケア > メイク道具、化粧小物 > ビューラー", "y_ct": "2084007463", "sex": "0", "male": "", "female": ""},
        "アイプチ": {"ctname": "オークション > ビューティー、ヘルスケア > コスメ、スキンケア > メイク道具、化粧小物 > ビューラー", "y_ct": "2084007463", "sex": "0", "male": "", "female": ""},
        "バランスボール": {"ctname": "オークション > スポーツ、レジャー > スポーツ別 > ヨガ、ピラティス > ヨガボール", "y_ct": "2084286287", "sex": "0", "male": "", "female": ""},
        "歯ブラシ": {"ctname": "オークション > ビューティー、ヘルスケア > オーラルケア > 歯ブラシ > 一般", "y_ct": "2084063362", "sex": "0", "male": "", "female": ""},
        "靴紐": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > 靴用品 > その他", "y_ct": "2084238538", "sex": "0", "male": "", "female": ""},
        "シューレース": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > 靴用品 > その他", "y_ct": "2084238538", "sex": "0", "male": "", "female": ""},
        "ドリンクホルダー": {"ctname": "オークション > 自動車、オートバイ > アクセサリー > 車内収納、ホルダー > コンソールボックス", "y_ct": "2084213751", "sex": "0", "male": "", "female": ""},
        "保護ケース": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0", "male": "", "female": ""},
        "D端子ケーブル": {"ctname": "オークション > 家電、AV、カメラ > 映像機器 > 映像用ケーブル > D端子ケーブル", "y_ct": "2084239135", "sex": "0", "male": "", "female": ""},
        "ペンケース": {"ctname": "オークション > 事務、店舗用品 > 文房具 > ペンケース", "y_ct": "2084048848", "sex": "0", "male": "", "female": ""},
        "健康ボード": {"ctname": "オークション > ビューティー、ヘルスケア > 健康用品、健康器具 > その他", "y_ct": "2084042545", "sex": "0", "male": "", "female": ""},
        "犬の服": {"ctname": "オークション > 住まい、インテリア > ペット用品 > 犬 > 服 > 小型犬用 > その他", "y_ct": "2084057211", "sex": "0", "male": "", "female": ""},
        "ドッグウエア": {"ctname": "オークション > 住まい、インテリア > ペット用品 > 犬 > 服 > 小型犬用 > その他", "y_ct": "2084057211", "sex": "0", "male": "", "female": ""},
        "アイフォンケース": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0", "male": "", "female": ""},
        "ハーネス": {"ctname": "オークション > 住まい、インテリア > ペット用品 > 犬 > 首輪、リード > リード", "y_ct": "2084062614", "sex": "0", "male": "", "female": ""},
        "ブックマーク": {"ctname": "オークション > 事務、店舗用品 > 文房具 > その他", "y_ct": "2084042489", "sex": "0", "male": "", "female": ""},
        "しおり": {"ctname": "オークション > 事務、店舗用品 > 文房具 > その他", "y_ct": "2084042489", "sex": "0", "male": "", "female": ""},
        "肩サポーター": {"ctname": "オークション > ビューティー、ヘルスケア > 健康用品、健康器具 > サポーター > その他", "y_ct": "2084216486", "sex": "0", "male": "", "female": ""},
        "荒野行動コントローラー": {"ctname": "オークション > コンピュータ > 周辺機器 > 入力装置 > ジョイスティック", "y_ct": "2084039610", "sex": "0", "male": "", "female": ""},
        "タイヤ エア バルブ キャップ": {"ctname": "オークション > 自動車、オートバイ > 工具 > タイヤチェンジャー", "y_ct": "2084261043", "sex": "0", "male": "", "female": ""},
        "インナーパンツ": {"ctname": "オークション > ファッション > レディースファッション > レギンス、トレンカ", "y_ct": "2084007161", "sex": "0", "male": "", "female": ""},
        "Vネック ニット": {"ctname": "オークション > ファッション > レディースファッション > ニット、セーター > 長袖 > Mサイズ", "y_ct": "2084064247", "sex": "0", "male": "", "female": ""},
        "タブレット用 折りたたみ式 スタンド": {"ctname": "オークション > コンピュータ > 周辺機器 > その他", "y_ct": "2084048551", "sex": "0", "male": "", "female": ""},
        "折り畳み式スタンド": {"ctname": "オークション > コンピュータ > 周辺機器 > その他", "y_ct": "2084048551", "sex": "0", "male": "", "female": ""},
        "スノボ膝プロテクター": {"ctname": "オークション > スポーツ、レジャー > スポーツ別 > スノーボード > ウエア、装備（男性用） > プロテクター", "y_ct": "2084284390", "sex": "0", "male": "", "female": ""},
        "エアーギター": {"ctname": "オークション > ホビー、カルチャー > 楽器、器材 > ギター > エレキギター > 本体 > その他", "y_ct": "2084019026", "sex": "0", "male": "", "female": ""},
        "リアキャップ": {"ctname": "オークション > 家電、AV、カメラ > カメラ、光学機器 > レンズ > 一眼カメラ用（マニュアルフォーカス） > その他", "y_ct": "2084261700", "sex": "0", "male": "", "female": ""},
        "シューズカバー": {"ctname": "オークション > スポーツ、レジャー > 自転車、サイクリング > ウエア > ウォーマー、カバー", "y_ct": "2084229858", "sex": "0", "male": "", "female": ""},
        "ドッグウェア": {"ctname": "オークション > 住まい、インテリア > ペット用品 > 犬 > 服 > 小型犬用 > その他", "y_ct": "2084057211", "sex": "0", "male": "", "female": ""},
        "反射ステッカー": {"ctname": "オークション > 自動車、オートバイ > アクセサリー > ステッカー、デカール > トラック、ダンプ用", "y_ct": "2084291447", "sex": "0", "male": "", "female": ""},
        "エア枕": {"ctname": "オークション > スポーツ、レジャー > キャンプ、アウトドア用品 > 寝袋、寝具 > その他", "y_ct": "2084263235", "sex": "0", "male": "", "female": ""},
        "空気まくら": {"ctname": "オークション > スポーツ、レジャー > キャンプ、アウトドア用品 > 寝袋、寝具 > その他", "y_ct": "2084263235", "sex": "0", "male": "", "female": ""},
        "USB充電ポート": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > バッテリー、充電器 > USB式充電器", "y_ct": "2084239197", "sex": "0", "male": "", "female": ""},
        "キーカバー": {"ctname": "オークション > 自動車、オートバイ > アクセサリー > キーホルダー > その他", "y_ct": "2084210631", "sex": "0", "male": "", "female": ""},
        "ランチョンマット": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > テーブルリネン > ランチョンマット", "y_ct": "2084046785", "sex": "0", "male": "", "female": ""},
        "ボールペン": {"ctname": "オークション > 事務、店舗用品 > 文房具 > 筆記用具 > ボールペン > ボールペン一般", "y_ct": "2084064350", "sex": "0", "male": "", "female": ""},
        "巾着": {"ctname": "オークション > ファッション > 女性和服、着物 > きんちゃく、バッグ > 巾着", "y_ct": "2084308407", "sex": "0", "male": "", "female": ""},
        "フィッシングルアー": {"ctname": "オークション > スポーツ、レジャー > フィッシング > ルアー用品 > その他", "y_ct": "2084303062", "sex": "0", "male": "", "female": ""},
        "フィシングルアー": {"ctname": "オークション > スポーツ、レジャー > フィッシング > ルアー用品 > その他", "y_ct": "2084303062", "sex": "0", "male": "", "female": ""},
        "ラッピング ボックス": {"ctname": "オークション > 事務、店舗用品 > ラッピング、包装 > ギフトボックス", "y_ct": "2084221001", "sex": "0", "male": "", "female": ""},
        "保護ガラス": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール", "y_ct": "2084299106", "sex": "0", "male": "", "female": ""},
        "ヨガ スポーツ ウェア": {"ctname": "オークション > スポーツ、レジャー > スポーツ別 > エクササイズ用品 > ウエア > 女性用 > スパッツ", "y_ct": "2084006880", "sex": "0", "male": "", "female": ""},
        "レッグパンツ": {"ctname": "オークション > ファッション > レディースファッション > パンツ、スラックス > Mサイズ", "y_ct": "2084224590", "sex": "1", "male": "2084224620", "female": "2084224590"},
        "レインコート": {"ctname": "オークション > スポーツ、レジャー > キャンプ、アウトドア用品 > 雨具、レインウエア > その他", "y_ct": "2084208701", "sex": "0", "male": "", "female": ""},
        "カバーケース": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0", "male": "", "female": ""},
        "iPhone X ケース": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0", "male": "", "female": ""},
        "iPhoneカバー": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0", "male": "", "female": ""},
        "iphoenケース": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0", "male": "", "female": ""},
        "携帯電話用防水ケース": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0", "male": "", "female": ""},
        "TPU ケース": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0", "male": "", "female": ""},
        "Lightningケーブル": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > バッテリー、充電器 > USB式充電器", "y_ct": "2084239197", "sex": "0", "male": "", "female": ""},
        "iPhoneケーブル": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > バッテリー、充電器 > USB式充電器", "y_ct": "2084239197", "sex": "0", "male": "", "female": ""},
        "メタル プレート": {"ctname": "オークション > アンティーク、コレクション > 広告、ノベルティグッズ > 看板", "y_ct": "27784", "sex": "0", "male": "", "female": ""},
        "スマホホルダー": {"ctname": "オークション > 自動車、オートバイ > アクセサリー > 携帯電話・スマートフォン用品 > ホルダー", "y_ct": "2084286659", "sex": "0", "male": "", "female": ""},
        "スマホスタンド": {"ctname": "オークション > 自動車、オートバイ > アクセサリー > 携帯電話・スマートフォン用品 > ホルダー", "y_ct": "2084286659", "sex": "0", "male": "", "female": ""},
        "外反母趾": {"ctname": "オークション > ビューティー、ヘルスケア > その他", "y_ct": "2084005300", "sex": "0", "male": "", "female": ""},
        "レインブーツカバー": {"ctname": "オークション > 自動車、オートバイ > オートバイ > バイクウエア、装備 > 雨具 > ブーツ・シューズカバー", "y_ct": "2084235749", "sex": "0", "male": "", "female": ""},
        "レインフィットカバー": {"ctname": "オークション > 自動車、オートバイ > オートバイ > バイクウエア、装備 > 雨具 > ブーツ・シューズカバー", "y_ct": "2084235749", "sex": "0", "male": "", "female": ""},
        "レインブーツ": {"ctname": "オークション > スポーツ、レジャー > キャンプ、アウトドア用品 > 雨具、レインウエア > その他", "y_ct": "2084208701", "sex": "0", "male": "", "female": ""},
        "IQOS": {"ctname": "オークション > アンティーク、コレクション > 雑貨 > 喫煙グッズ > その他", "y_ct": "26144", "sex": "0", "male": "", "female": ""},
        "手帳型ケース": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > レザーケース", "y_ct": "2084306950", "sex": "0", "male": "", "female": ""},
        "TPUケース": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他", "y_ct": "2084306951", "sex": "0", "male": "", "female": ""},
        "ソフトケース": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他", "y_ct": "2084306951", "sex": "0", "male": "", "female": ""},
        "スリム ケース": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他", "y_ct": "2084306951", "sex": "0", "male": "", "female": ""},
        "スマホ ケース": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他", "y_ct": "2084306951", "sex": "0", "male": "", "female": ""},
        "スマートフォン カバー": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > ケース > その他", "y_ct": "2084306951", "sex": "0", "male": "", "female": ""},
        "耳栓": {"ctname": "オークション > ビューティー、ヘルスケア > リラクゼーショングッズ > その他", "y_ct": "2084042540", "sex": "0", "male": "", "female": ""},
        "glo": {"ctname": "オークション > アンティーク、コレクション > 雑貨 > 喫煙グッズ > その他", "y_ct": "26144", "sex": "0", "male": "", "female": ""},
        "風船": {"ctname": "オークション > おもちゃ、ゲーム > 手品、パーティグッズ > パーティグッズ > その他", "y_ct": "2084059858", "sex": "0", "male": "", "female": ""},
        "つけまつげ": {"ctname": "オークション > ビューティー、ヘルスケア > コスメ、スキンケア > マスカラ、まつげ用品 > その他 > まつげエクステ、つけまつげ", "y_ct": "2084263000", "sex": "0", "male": "", "female": ""},
        "スポーツブラ": {"ctname": "オークション > スポーツ、レジャー > スポーツウエア > 女性用 > インナーウエア > スポーツブラ", "y_ct": "2084246688", "sex": "0", "male": "", "female": ""},
        "サポートインナー": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > 補正下着 > その他", "y_ct": "2084053156", "sex": "0", "male": "", "female": ""},
        "ストレッチインナー": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > 補正下着 > その他", "y_ct": "2084053156", "sex": "0", "male": "", "female": ""},
        "二の腕やせサポーター": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > 補正下着 > その他", "y_ct": "2084053156", "sex": "0", "male": "", "female": ""},
        "補正下着": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > 補正下着 > その他", "y_ct": "2084053156", "sex": "0", "male": "", "female": ""},
        "姿勢改善インナー": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > 補正下着 > その他", "y_ct": "2084053156", "sex": "0", "male": "", "female": ""},
        "ウエストウォーマー": {"ctname": "オークション > ビューティー、ヘルスケア > 健康用品、健康器具 > サポーター > 腰用", "y_ct": "2084216485", "sex": "0", "male": "", "female": ""},
        "腹巻き": {"ctname": "オークション > ビューティー、ヘルスケア > 健康用品、健康器具 > サポーター > 腰用", "y_ct": "2084216485", "sex": "0", "male": "", "female": ""},
        "コルセット": {"ctname": "オークション > ビューティー、ヘルスケア > 健康用品、健康器具 > サポーター > 腰用", "y_ct": "2084216485", "sex": "0", "male": "", "female": ""},
        "耳かき": {"ctname": "オークション > ビューティー、ヘルスケア > 救急、衛生用品 > 耳掃除用品", "y_ct": "2084227183", "sex": "0", "male": "", "female": ""},
        "トレーニング チューブ": {"ctname": "オークション > スポーツ、レジャー > スポーツ別 > エクササイズ用品 > ギア > エキスパンダー、チューブ", "y_ct": "2084006835", "sex": "0", "male": "", "female": ""},
        "いびきストッパー": {"ctname": "オークション > ビューティー、ヘルスケア > 健康用品、健康器具 > その他", "y_ct": "2084042545", "sex": "0", "male": "", "female": ""},
        "手首サポーター": {"ctname": "オークション > ビューティー、ヘルスケア > 健康用品、健康器具 > サポーター > 手首用", "y_ct": "2084216482", "sex": "0", "male": "", "female": ""},
        "手首 サポーター": {"ctname": "オークション > ビューティー、ヘルスケア > 健康用品、健康器具 > サポーター > 手首用", "y_ct": "2084216482", "sex": "0", "male": "", "female": ""},
        "手首　サポーター": {"ctname": "オークション > ビューティー、ヘルスケア > 健康用品、健康器具 > サポーター > 手首用", "y_ct": "2084216482", "sex": "0", "male": "", "female": ""},
        "スマホとタブレットのスタンド": {"ctname": "オークション > コンピュータ > 周辺機器 > その他", "y_ct": "2084048551", "sex": "0", "male": "", "female": ""},
        "ヨガパンツ": {"ctname": "オークション > スポーツ、レジャー > スポーツウエア > 女性用 > ボトムス > ロング > その他", "y_ct": "2084057034", "sex": "0", "male": "", "female": ""},
        "ストレッチパンツ": {"ctname": "オークション > スポーツ、レジャー > スポーツウエア > 女性用 > ボトムス > ロング > その他", "y_ct": "2084057034", "sex": "0", "male": "", "female": ""},
        "ズボン": {"ctname": "オークション > ファッション > レディースファッション > パンツ、スラックス > Mサイズ", "y_ct": "2084224590", "sex": "1", "male": "2084224619", "female": "2084224590"},
        "バルーン": {"ctname": "オークション > おもちゃ、ゲーム > 手品、パーティグッズ > パーティグッズ > その他", "y_ct": "2084059858", "sex": "0", "male": "", "female": ""},
        "メイクブラシ": {"ctname": "オークション > ビューティー、ヘルスケア > コスメ、スキンケア > メイク道具、化粧小物 > ブラシ、チップ、コーム > メイクブラシセット", "y_ct": "2084228681", "sex": "0", "male": "", "female": ""},
        "化粧道具": {"ctname": "オークション > ビューティー、ヘルスケア > コスメ、スキンケア > メイク道具、化粧小物 > その他", "y_ct": "2084007465", "sex": "0", "male": "", "female": ""},
        "コンシーラー": {"ctname": "オークション > ビューティー、ヘルスケア > コスメ、スキンケア > コンシーラー", "y_ct": "2084005315", "sex": "0", "male": "", "female": ""},
        "ベスト": {"ctname": "オークション > ファッション > メンズファッション > ベスト > Mサイズ", "y_ct": "2084064193", "sex": "0", "male": "2084064193", "female": ""},
        "トレーナー": {"ctname": "オークション > ファッション > メンズファッション > トレーナー > Mサイズ", "y_ct": "2084057461", "sex": "1", "male": "2084057461", "female": "2084064261"},
        "サルエルパンツ": {"ctname": "オークション > ファッション > メンズファッション > サルエルパンツ", "y_ct": "2084246078", "sex": "1", "male": "2084246078", "female": "2084246107"},
        "ジョガーパンツ": {"ctname": "オークション > ファッション > メンズファッション > パンツ、スラックス > Lサイズ", "y_ct": "2084224620", "sex": "1", "male": "2084224620", "female": "2084224590"},
        "スエットパンツ": {"ctname": "オークション > ファッション > メンズファッション > パンツ、スラックス > Lサイズ", "y_ct": "2084224620", "sex": "1", "male": "2084224620", "female": "2084224590"},
        "マウンテンパーカー": {"ctname": "オークション > ファッション > メンズファッション > ジャケット、上着 > ジャンパー、ブルゾン > ジャンパー、ブルゾン一般 > Mサイズ","y_ct": "2084050108", "sex": "1", "male": "2084050108", "female": "2084057472"},
        "ジャンパー": {"ctname": "オークション > ファッション > メンズファッション > ジャケット、上着 > ジャンパー、ブルゾン > ジャンパー、ブルゾン一般 > Mサイズ","y_ct": "2084050108", "sex": "1", "male": "2084050108", "female": "2084057481"},
        "ブルゾン": {"ctname": "オークション > ファッション > メンズファッション > ジャケット、上着 > ジャンパー、ブルゾン > ジャンパー、ブルゾン一般 > Mサイズ","y_ct": "2084050108", "sex": "1", "male": "2084050108", "female": "2084057481"},
        "手袋": {"ctname": "オークション > ファッション > ファッション小物 > 手袋 > 女性用 > その他", "y_ct": "2084214886", "sex": "1", "male": "2084214890","female": "2084214886"},
        "キーケース": {"ctname": "オークション > ファッション > ファッション小物 > キーケース", "y_ct": "2084012476", "sex": "0", "male": "","female": ""},
        "ワンピース": {"ctname": "オークション > ファッション > レディースファッション > ワンピース > ミニスカート > Mサイズ", "y_ct": "2084224575", "sex": "0","male": "", "female": ""},
        "ワンピ": {"ctname": "オークション > ファッション > レディースファッション > ワンピース > ミニスカート > Mサイズ", "y_ct": "2084224575", "sex": "0","male": "", "female": ""},
        "サマードレス": {"ctname": "オークション > ファッション > レディースファッション > ワンピース > ミニスカート > Mサイズ", "y_ct": "2084224575", "sex": "0","male": "", "female": ""},
        "ネックレス": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ネックレス、ペンダント > その他", "y_ct": "2084005400", "sex": "0","male": "", "female": ""},
        "ペンダント": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ネックレス、ペンダント > その他", "y_ct": "2084005400", "sex": "0","male": "", "female": ""},
        "ブレスレット": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ブレスレット、バングル > バングル > その他", "y_ct": "2084019059","sex": "0", "male": "", "female": ""},
        "マフラー": {"ctname": "オークション > ファッション > ファッション小物 > マフラー > 女性用 > マフラー一般", "y_ct": "2084006464", "sex": "1","male": "2084006472", "female": "2084006464"},
        "ストール": {"ctname": "オークション > ファッション > ファッション小物 > ストール > ストール一般", "y_ct": "2084006466", "sex": "1", "male": "2084006472","female": "2084006466"},
        "ギフトシール": {"ctname": "オークション > 事務、店舗用品 > 文房具 > その他", "y_ct": "2084042489", "sex": "0", "male": "","female": ""},
        "指輪": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > 指輪 > その他", "y_ct": "2084005435", "sex": "0", "male": "","female": ""},
        "スタイラスペン": {"ctname": "オークション > 事務、店舗用品 > 文房具 > その他", "y_ct": "2084042489", "sex": "0", "male": "","female": ""},
        "Tシャツ": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > その他の袖丈", "y_ct": "2084054032", "sex": "1","male": "2084054037", "female": "2084054032"},
        "tシャツ": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > その他の袖丈", "y_ct": "2084054032", "sex": "1","male": "2084054037", "female": "2084054032"},
        "シャツ": {"ctname": "オークション > ファッション > レディースファッション > Tシャツ > その他の袖丈", "y_ct": "2084054032", "sex": "1","male": "2084054037", "female": "2084054032"},
        "フォトプロップス": {"ctname": "オークション > 事務、店舗用品 > 文房具 > その他", "y_ct": "2084042489", "sex": "0", "male": "","female": ""},
        "ピアス": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ピアス > その他", "y_ct": "2084005423", "sex": "0", "male": "","female": ""},
        "チューブトップ": {"ctname": "オークション > ファッション > レディースファッション > チューブトップ、ベアトップ", "y_ct": "2084243344", "sex": "0","male": "", "female": ""},
        "スカーフ": {"ctname": "オークション > ファッション > ファッション小物 > スカーフ、ポケットチーフ > 女性用", "y_ct": "2084006442", "sex": "0","male": "", "female": ""},
        "オイルマッチ": {"ctname": "アンティーク、コレクション > 雑貨 > 喫煙グッズ > ライター > 一般 > オイルライター", "y_ct": "2084037605", "sex": "0","male": "", "female": ""},
        "ナイロンベルト": {"ctname": "ファッション > ファッション小物 > ベルト > 男性用 > その他", "y_ct": "2084214922", "sex": "0", "male": "","female": ""},
        "ひものれん": {"ctname": "オークション > 事務、店舗用品 > 文房具 > その他", "y_ct": "2084042489", "sex": "0", "male": "", "female": ""},
        "リボン": {"ctname": "ファッション > レディースファッション > フォーマル > ウエディングドレス > その他", "y_ct": "2084064273", "sex": "0","male": "", "female": ""},
        "ジョーク グッズ": {"ctname": "オークション > おもちゃ、ゲーム > 手品、パーティグッズ > パーティグッズ > その他", "y_ct": "2084059858", "sex": "0","male": "", "female": ""},
        "ウォールステッカー": {"ctname": "オークション > 住まい、インテリア > 工具、DIY用品 > 建築材料、住宅設備 > 内装 > 内装材料一般 > 壁材、壁紙 > 壁紙、クロス","y_ct": "2084304476", "sex": "0", "male": "", "female": ""},
        "エプロン": {"ctname": "オークション > ファッション > ファッション小物 > エプロン", "y_ct": "2084018499", "sex": "0", "male": "","female": ""},
        "クシ": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > その他", "y_ct": "2084005387", "sex": "0","male": "", "female": ""},
        "コーム": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > その他", "y_ct": "2084005387", "sex": "0","male": "", "female": ""},
        "はさみ": {"ctname": "事務、店舗用品 > 店舗用品 > 理美容店用品", "y_ct": "2084263149", "sex": "0", "male": "", "female": ""},
        "ポーチ": {"ctname": "オークション > ファッション > レディースバッグ > ポーチ", "y_ct": "2084007482", "sex": "0", "male": "","female": ""},
        "収納袋": {"ctname": "オークション > ファッション > レディースバッグ > ポーチ", "y_ct": "2084007482", "sex": "0", "male": "","female": ""},
        "ライト": {"ctname": "住まい、インテリア > 家具、インテリア > 照明 > 卓上スタンド > デスクライト", "y_ct": "2084239865", "sex": "0", "male": "","female": ""},
        "アイコス": {"ctname": "オークション > アンティーク、コレクション > 雑貨 > 喫煙グッズ > その他", "y_ct": "26144", "sex": "0", "male": "","female": ""},
        "iQOS": {"ctname": "オークション > アンティーク、コレクション > 雑貨 > 喫煙グッズ > その他", "y_ct": "26144", "sex": "0", "male": "","female": ""},
        "フィクシング": {"ctname": "オークション > ファッション > メンズファッション > その他", "y_ct": "2084207680", "sex": "0", "male": "","female": ""},
        "シール": {"ctname": "オークション > 住まい、インテリア > 工具、DIY用品 > 建築材料、住宅設備 > 内装 > 内装材料一般 > 壁材、壁紙 > 壁紙、クロス","y_ct": "2084304476", "sex": "0", "male": "", "female": ""},
        "ストッキング": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > ストッキング > Mサイズ", "y_ct": "2084053100","sex": "0", "male": "", "female": ""},
        "レギンス": {"ctname": "オークション > ファッション > レディースファッション > レギンス、トレンカ", "y_ct": "2084007161", "sex": "0", "male": "","female": ""},
        "ドアオープナー": {"ctname": "オークション > 住まい、インテリア > その他", "y_ct": "24678", "sex": "0", "male": "", "female": ""},
        "ナイフ": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > 調理器具 > 刃物 > 包丁 > 洋包丁", "y_ct": "2084063502", "sex": "0","male": "", "female": ""},
        "パズル": {"ctname": "オークション > おもちゃ、ゲーム > パズル > その他", "y_ct": "27711", "sex": "0", "male": "", "female": ""},
        "ブロック": {"ctname": "オークション > おもちゃ、ゲーム > パズル > その他", "y_ct": "27711", "sex": "0", "male": "", "female": ""},
        "リュックサック": {"ctname": "オークション > ファッション > 男女兼用バッグ > リュックサック、デイパック", "y_ct": "2084233233", "sex": "0", "male": "","female": ""},
        "マザーズバッグ": {"ctname": "オークション > ファッション > 男女兼用バッグ > リュックサック、デイパック", "y_ct": "2084233233", "sex": "0", "male": "","female": ""},
        "ヘアバンド": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ヘアバンド、カチューシャ", "y_ct": "2084019051","sex": "0", "male": "", "female": ""},
        "バンド": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ヘアバンド、カチューシャ", "y_ct": "2084019051","sex": "0", "male": "", "female": ""},
        "カチューシャ": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ヘアバンド、カチューシャ", "y_ct": "2084019051","sex": "0", "male": "", "female": ""},
        "チョーカー": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > チョーカー > その他", "y_ct": "2084005394", "sex": "0","male": "", "female": ""},
        "ボディバッグ": {"ctname": "オークション > ファッション > メンズバッグ > ボディバッグ", "y_ct": "2084008349", "sex": "0", "male": "","female": ""},
        "財布": {"ctname": "オークション > ファッション > ファッション小物 > 財布 > 女性用 > その他", "y_ct": "2084292137", "sex": "1", "male": "2084292136","female": "2084292137"},
        "ショルダーバッグ": {"ctname": "オークション > ファッション > 男女兼用バッグ > ショルダーバッグ", "y_ct": "2084233231", "sex": "0", "male": "","female": ""},
        "ウエストポーチ": {"ctname": "オークション > スポーツ、レジャー > スポーツ別 > ランニング、ジョギング > アクセサリー > ウエストポーチ", "y_ct": "2084285340","sex": "0", "male": "", "female": ""},
        "パーカー": {"ctname": "オークション > スポーツ、レジャー > スポーツウエア > 男性用 > パーカー", "y_ct": "2084303393", "sex": "1", "male": "2084303393","female": "2084050490"},
        "孫の手": {"ctname": "オークション > 住まい、インテリア > その他", "y_ct": "24678", "sex": "0", "male": "", "female": ""},
        "フット カバー": {"ctname": "オークション > ファッション > ファッション小物 > 靴下 > 女性用 > 一般 > 無地", "y_ct": "2084214893", "sex": "0","male": "", "female": ""},
        "インソール": {"ctname": "オークション > ファッション > メンズシューズ > その他", "y_ct": "2084005486", "sex": "0", "male": "","female": ""},
        "うきわ": {"ctname": "オークション > おもちゃ、ゲーム > 水遊び > 浮き輪、浮き具", "y_ct": "2084042423", "sex": "0", "male": "","female": ""},
        "フロート": {"ctname": "オークション > おもちゃ、ゲーム > 水遊び > 浮き輪、浮き具", "y_ct": "2084042423", "sex": "0", "male": "","female": ""},
        "シャワーカーテン": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > バス > その他", "y_ct": "2084024452", "sex": "0", "male": "","female": ""},
        "ウィッグ": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ウイッグ > その他", "y_ct": "2084062532", "sex": "0","male": "", "female": ""},
        "パジャマ": {"ctname": "オークション > ファッション > メンズファッション > パジャマ", "y_ct": "2084006762", "sex": "1", "male": "2084006762","female": "2084053160"},
        "折りたたみ バッグ": {"ctname": "オークション > ファッション > メンズバッグ > リュックサック、デイパック", "y_ct": "2084008303", "sex": "0","male": "", "female": ""},
        "ネクタイピン": {"ctname": "オークション > ファッション > ファッション小物 > ネクタイ > ネクタイ一般", "y_ct": "2084036146", "sex": "0", "male": "","female": ""},
        "ネクタイ": {"ctname": "オークション > ファッション > ファッション小物 > ネクタイ > ネクタイ一般", "y_ct": "2084036146", "sex": "0", "male": "","female": ""},
        "レインウェア": {"ctname": "オークション > スポーツ、レジャー > キャンプ、アウトドア用品 > 雨具、レインウエア > その他", "y_ct": "2084208701", "sex": "0", "male": "","female": ""},
        "おべんとケース": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > 弁当用品 > 弁当箱（男女兼用）", "y_ct": "2084261189", "sex": "0","male": "", "female": ""},
        "おべんとうケース": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > 弁当用品 > 弁当箱（男女兼用）", "y_ct": "2084261189", "sex": "0","male": "", "female": ""},
        "弁当箱": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > 弁当用品 > 弁当箱（男女兼用）", "y_ct": "2084261189", "sex": "0","male": "", "female": ""},
        "装飾金具": {"ctname": "オークション > ホビー、カルチャー > ハンドクラフト、手工芸 > 裁縫、刺繍 > その他", "y_ct": "2084045844", "sex": "0","male": "", "female": ""},
        "ギフト袋": {"ctname": "オークション > 事務、店舗用品 > その他", "y_ct": "22996", "sex": "0", "male": "", "female": ""},
        "ラッピング袋": {"ctname": "オークション > 事務、店舗用品 > その他", "y_ct": "22996", "sex": "0", "male": "", "female": ""},
        "ラッピング 袋": {"ctname": "オークション > 事務、店舗用品 > その他", "y_ct": "22996", "sex": "0", "male": "", "female": ""},
        "目出し帽": {"ctname": "オークション > 自動車、オートバイ > オートバイ > バイクウエア、装備 > フェイスマスク、ネックウォーマー", "y_ct": "2084246658","sex": "0", "male": "", "female": ""},
        "フェイスマスク": {"ctname": "オークション > 自動車、オートバイ > オートバイ > バイクウエア、装備 > フェイスマスク、ネックウォーマー", "y_ct": "2084246658","sex": "0", "male": "", "female": ""},
        "ネックウォーマー": {"ctname": "オークション > 自動車、オートバイ > オートバイ > バイクウエア、装備 > フェイスマスク、ネックウォーマー", "y_ct": "2084246658","sex": "0", "male": "", "female": ""},
        "ハンドスピナー": {"ctname": "オークション > おもちゃ、ゲーム > その他", "y_ct": "26082", "sex": "0", "male": "", "female": ""},
        "オフショル": {"ctname": "オークション > ファッション > レディースファッション > ニット、セーター > その他の袖丈", "y_ct": "2084054035", "sex": "0","male": "", "female": ""},
        "セーター": {"ctname": "オークション > ファッション > レディースファッション > ニット、セーター > その他の袖丈", "y_ct": "2084054035", "sex": "1","male": "2084064188", "female": "2084054035"},
        "フラットシューズ": {"ctname": "オークション > ファッション > レディースシューズ > その他", "y_ct": "2084005499", "sex": "0", "male": "","female": ""},
        "イヤホンケーブル": {"ctname": "オークション > 家電、AV、カメラ > オーディオ機器 > ヘッドフォン、イヤフォン > イヤフォン > その他", "y_ct": "2084219572","sex": "0", "male": "", "female": ""},
        "名刺入れ": {"ctname": "オークション > ファッション > ファッション小物 > 名刺入れ、カードケース > 男性用", "y_ct": "2084246781", "sex": "0","male": "", "female": ""},
        "髪留め": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ヘアピン", "y_ct": "2084005386", "sex": "0","male": "", "female": ""},
        "ヘアピン": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ヘアピン", "y_ct": "2084005386", "sex": "0","male": "", "female": ""},
        "シートベルトヘルパー": {"ctname": "オークション > 自動車、オートバイ > セーフティ > チャイルドシート > その他", "y_ct": "2084242666", "sex": "0","male": "", "female": ""},
        "ジャケット": {"ctname": "オークション > ファッション > メンズファッション > ジャケット、上着 > ジャンパー、ブルゾン > ジャンパー、ブルゾン一般 > Lサイズ","y_ct": "2084050109", "sex": "1", "male": "2084050109", "female": "2084057476"},
        "ブラウス": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486", "sex": "0","male": "", "female": ""},
        "チュニック": {"ctname": "オークション > ファッション > レディースファッション > シャツ、ブラウス > 長袖 > Mサイズ", "y_ct": "2084057486", "sex": "0","male": "", "female": ""},
        "水着": {"ctname": "オークション > スポーツ、レジャー > スポーツ別 > 水泳 > スイムウエア > 女性用 > Mサイズ > その他", "y_ct": "2084224142","sex": "1", "male": "2084051836", "female": "2084224142"},
        "レッグウォーマー": {"ctname": "オークション > スポーツ、レジャー > スポーツウエア > 女性用 > インナーウエア > タイツ", "y_ct": "2084246668", "sex": "0","male": "", "female": ""},
        "タイツ": {"ctname": "オークション > スポーツ、レジャー > スポーツウエア > 女性用 > インナーウエア > タイツ", "y_ct": "2084246668", "sex": "1","male": "2084245567", "female": "2084246668"},
        "レッグカバー": {"ctname": "オークション > スポーツ、レジャー > スポーツウエア > 女性用 > インナーウエア > タイツ", "y_ct": "2084246668", "sex": "0","male": "", "female": ""},
        "ブーツカフス": {"ctname": "オークション > スポーツ、レジャー > スポーツウエア > 女性用 > インナーウエア > タイツ", "y_ct": "2084246668", "sex": "0","male": "", "female": ""},
        "テーピングサポーター": {"ctname": "オークション > ビューティー、ヘルスケア > 健康用品、健康器具 > サポーター > その他", "y_ct": "2084216486", "sex": "0","male": "", "female": ""},
        "ファランジリング": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > 指輪 > その他", "y_ct": "2084005435", "sex": "0","male": "", "female": ""},
        "レイヤーリング": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > 指輪 > その他", "y_ct": "2084005435", "sex": "0","male": "", "female": ""},
        "リング": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > 指輪 > その他", "y_ct": "2084005435", "sex": "0", "male": "","female": ""},
        "クリスマス　飾り": {"ctname": "オークション > ホビー、カルチャー > ハンドクラフト、手工芸 > 裁縫、刺繍 > 完成品 > その他", "y_ct": "2084240874", "sex": "0","male": "", "female": ""},
        "クリスマス 飾り": {"ctname": "オークション > ホビー、カルチャー > ハンドクラフト、手工芸 > 裁縫、刺繍 > 完成品 > その他", "y_ct": "2084240874", "sex": "0","male": "", "female": ""},
        "クリスマス　ガーランド": {"ctname": "オークション > ホビー、カルチャー > ハンドクラフト、手工芸 > 裁縫、刺繍 > 完成品 > その他", "y_ct": "2084240874","sex": "0", "male": "", "female": ""},
        "クリスマス ガーランド": {"ctname": "オークション > ホビー、カルチャー > ハンドクラフト、手工芸 > 裁縫、刺繍 > 完成品 > その他", "y_ct": "2084240874","sex": "0", "male": "", "female": ""},
        "靴下": {"ctname": "オークション > ファッション > ファッション小物 > 靴下 > 女性用", "y_ct": "2084214901", "sex": "1", "male": "2084214908","female": "2084214901"},
        "ソックス": {"ctname": "オークション > ファッション > ファッション小物 > 靴下 > 女性用", "y_ct": "2084214901", "sex": "1", "male": "2084214908","female": "2084214901"},
        "ニーハイ": {"ctname": "オークション > ファッション > ファッション小物 > 靴下 > 女性用", "y_ct": "2084214901", "sex": "0", "male": "","female": "2084214901"},
        "コイン": {"ctname": "オークション > アンティーク、コレクション > 貨幣 > 硬貨 > 世界 > ヨーロッパ", "y_ct": "26750", "sex": "0", "male": "","female": ""},
        "クッション": {"ctname": "オークション > 住まい、インテリア > 家具、インテリア > インテリア小物 > クッション > 一般 > その他", "y_ct": "2084063564","sex": "0", "male": "", "female": ""},
        "カットソー": {"ctname": "オークション > ファッション > レディースファッション > カットソー > 長袖 > Mサイズ", "y_ct": "2084050495", "sex": "0","male": "", "female": ""},
        "パスポートケース": {"ctname": "オークション > ファッション > ファッション小物 > その他", "y_ct": "44164", "sex": "0", "male": "","female": ""},
        "パスポートカバー": {"ctname": "オークション > ファッション > ファッション小物 > その他", "y_ct": "44164", "sex": "0", "male": "","female": ""},
        "カーディガン": {"ctname": "オークション > ファッション > レディースファッション > カーディガン > Mサイズ", "y_ct": "2084064209", "sex": "1","male": "2084007052", "female": "2084064209"},
        "知育玩具": {"ctname": "オークション > おもちゃ、ゲーム > 知育玩具 > その他", "y_ct": "2084045581", "sex": "0", "male": "","female": ""},
        "ガウチョパンツ": {"ctname": "オークション > ファッション > レディースファッション > パンツ、スラックス > Mサイズ", "y_ct": "2084224590", "sex": "0","male": "", "female": ""},
        "ワイドパンツ": {"ctname": "オークション > ファッション > レディースファッション > パンツ、スラックス > Mサイズ", "y_ct": "2084224590", "sex": "0","male": "", "female": ""},
        "かんざし": {"ctname": "オークション > ファッション > 女性和服、着物 > かんざし", "y_ct": "2084048833", "sex": "0", "male": "","female": ""},
        "髪飾り": {"ctname": "オークション > ファッション > 女性和服、着物 > かんざし", "y_ct": "2084048833", "sex": "0", "male": "","female": ""},
        "紐パン": {"ctname": "オークション > ファッション > レディースファッション > ナイトウエア、パジャマ", "y_ct": "2084053160", "sex": "0", "male": "","female": ""},
        "縞パン": {"ctname": "オークション > ファッション > レディースファッション > ナイトウエア、パジャマ", "y_ct": "2084053160", "sex": "0", "male": "","female": ""},
        "スカート": {"ctname": "オークション > ファッション > レディースファッション > スカート > ロングスカート > その他", "y_ct": "2084007175", "sex": "0","male": "", "female": ""},
        "ニットキャップ": {"ctname": "オークション > ファッション > ファッション小物 > 帽子 > 女性用 > ワッチキャップ、ニットキャップ", "y_ct": "2084006693","sex": "0", "male": "", "female": ""},
        "エコバッグ": {"ctname": "オークション > ファッション > 男女兼用バッグ > エコバッグ", "y_ct": "2084233235", "sex": "0", "male": "","female": ""},
        "バルーンアート": {"ctname": "オークション > おもちゃ、ゲーム > 手品、パーティグッズ > パーティグッズ > その他", "y_ct": "2084059858", "sex": "0","male": "", "female": ""},
        "キャスケット": {"ctname": "オークション > ファッション > ファッション小物 > 帽子 > 女性用 > キャスケット", "y_ct": "2084243504", "sex": "0","male": "", "female": ""},
        "帽子": {"ctname": "オークション > ファッション > ファッション小物 > 帽子 > 女性用 > その他", "y_ct": "2084006690", "sex": "1", "male": "2084006684","female": "2084006690"},
        "ショートパンツ": {"ctname": "オークション > ファッション > レディースファッション > ショートパンツ > Mサイズ", "y_ct": "2084224595", "sex": "0","male": "", "female": ""},
        "ホットパンツ": {"ctname": "オークション > スポーツ、レジャー > スポーツ別 > バレーボール > ウエア > 女性用 > パンツ", "y_ct": "2084063029", "sex": "0","male": "", "female": ""},
        "ブローチ": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ネックレス、ペンダント > カラーストーン > その他", "y_ct": "2084042513","sex": "0", "male": "", "female": ""},
        "トートバッグ": {"ctname": "オークション > ファッション > レディースバッグ > トートバッグ > その他", "y_ct": "2084050995", "sex": "1", "male": "2084008301","female": "2084050995"},
        "トート バッグ": {"ctname": "オークション > ファッション > レディースバッグ > トートバッグ > その他", "y_ct": "2084050995", "sex": "1", "male": "2084008301","female": "2084050995"},
        "手提げ": {"ctname": "オークション > ファッション > レディースバッグ > トートバッグ > その他", "y_ct": "2084050995", "sex": "1", "male": "2084008301","female": "2084050995"},
        "バッグ": {"ctname": "オークション > ファッション > レディースバッグ > ハンドバッグ > 皮革製 > その他", "y_ct": "2084051017", "sex": "1","male": "2084008300", "female": "2084051017"},
        "ガラスフィルム": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール", "y_ct": "2084299106","sex": "0", "male": "", "female": ""},
        "クッキングシート": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > その他", "y_ct": "24462", "sex": "0", "male": "","female": ""},
        "クッキングマット": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > その他", "y_ct": "24462", "sex": "0", "male": "","female": ""},
        "ベルト": {"ctname": "オークション > ファッション > ファッション小物 > ベルト > 男性用 > 皮革、レザー > 黒", "y_ct": "2084214919", "sex": "1","male": "2084214919", "female": "2084214915"},
        "ハンガー": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > ハンガー > 一般", "y_ct": "2084061605", "sex": "0", "male": "","female": ""},
        "キャミソール": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > キャミソール > Mサイズ", "y_ct": "2084053124","sex": "0", "male": "", "female": ""},
        "タンクトップ": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > キャミソール > Mサイズ", "y_ct": "2084053124","sex": "0", "male": "", "female": ""},
        "バレッタ": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > バレッタ", "y_ct": "2084005385", "sex": "0","male": "", "female": ""},
        "クラッチバッグ": {"ctname": "オークション > ファッション > レディースバッグ > クラッチバッグ、パーティバッグ", "y_ct": "2084008347", "sex": "1","male": "2084008304", "female": "2084008347"},
        "アームウォーマー": {"ctname": "オークション > スポーツ、レジャー > 自転車、サイクリング > ウエア > ウォーマー、カバー", "y_ct": "2084229858", "sex": "0","male": "", "female": ""},
        "アームカバー": {"ctname": "オークション > スポーツ、レジャー > 自転車、サイクリング > ウエア > ウォーマー、カバー", "y_ct": "2084229858", "sex": "0","male": "", "female": ""},
        "ヘア飾り": {"ctname": "オークション > アクセサリー、時計 > ハンドメイド > アクセサリー（女性用） > ヘアアクセサリー", "y_ct": "2084240619", "sex": "0","male": "", "female": ""},
        "ニット帽": {"ctname": "オークション > ファッション > ファッション小物 > 帽子 > 女性用 > ワッチキャップ、ニットキャップ", "y_ct": "2084006693", "sex": "1","male": "2084006686", "female": "2084006693"},
        "カフスボタン": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > カフス > その他", "y_ct": "2084062587", "sex": "0", "male": "","female": ""},
        "サングラス": {"ctname": "オークション > ファッション > ファッション小物 > サングラス ", "y_ct": "2084224828", "sex": "0", "male": "","female": ""},
        "コースター": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > アクセサリー > コースター > その他", "y_ct": "2084230300", "sex": "0","male": "", "female": ""},
        "ダイヤモンド": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ネックレス、ペンダント > ダイヤモンド > プラチナチェーン", "y_ct": "2084209778","sex": "0", "male": "", "female": ""},
        "アイマスク": {"ctname": "オークション > ビューティー、ヘルスケア > リラクゼーショングッズ > アイピロー", "y_ct": "2084047754", "sex": "0", "male": "","female": ""},
        "フラワーシャワー": {"ctname": "オークション > 花、園芸 > アレンジメント > 生花 > その他", "y_ct": "2084206879", "sex": "0", "male": "","female": ""},
        "コスチューム": {"ctname": "オークション > コミック、アニメグッズ > コスプレ衣装 > コミック、アニメ、ゲームキャラクター > アクセサリー、小物", "y_ct": "2084311489","sex": "0", "male": "", "female": ""},
        "ひざかけ": {"ctname": "オークション > スポーツ、レジャー > キャンプ、アウトドア用品 > その他", "y_ct": "2084005102", "sex": "0", "male": "","female": ""},
        "シェイパー": {"ctname": "オークション > スポーツ、レジャー > スポーツ別 > エクササイズ用品 > その他", "y_ct": "25178", "sex": "0", "male": "","female": ""},
        "ヘアアレンジ": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ヘアアクセサリー > ヘアピン", "y_ct": "2084005386", "sex": "0","male": "", "female": ""},
        "充電器": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > バッテリー、充電器 > USB式充電器", "y_ct": "2084239197", "sex": "0","male": "", "female": ""},
        "なべつかみ": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > 食器 > その他", "y_ct": "2084005666", "sex": "0", "male": "","female": ""},
        "鍋つかみ": {"ctname": "オークション > 住まい、インテリア > キッチン、食器 > 食器 > その他", "y_ct": "2084005666", "sex": "0", "male": "","female": ""},
        "レザーケース": {"ctname": "オークション > ファッション > ファッション小物 > 名刺入れ、カードケース > 男性用", "y_ct": "2084246781", "sex": "0","male": "", "female": ""},
        "カードケース": {"ctname": "オークション > ファッション > ファッション小物 > 名刺入れ、カードケース > 男性用", "y_ct": "2084246781", "sex": "0","male": "", "female": ""},
        "パスケース": {"ctname": "オークション > ファッション > ファッション小物 > 名刺入れ、カードケース > 男性用", "y_ct": "2084246781", "sex": "0","male": "", "female": ""},
        "懐中時計": {"ctname": "オークション > アクセサリー、時計 > 懐中時計 > 機械式 > 手巻き", "y_ct": "2084062956", "sex": "0", "male": "","female": ""},
        "ドッグタグ": {"ctname": "オークション > アクセサリー、時計 > 懐中時計 > 機械式 > 手巻き", "y_ct": "2084062956", "sex": "0", "male": "","female": ""},
        "ボディスーツ": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > 補正下着 > ボディスーツ > Cカップ", "y_ct": "2084053170","sex": "0", "male": "", "female": ""},
        "シェイプUPインナー": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > 補正下着 > ボディスーツ > Cカップ", "y_ct": "2084053170","sex": "0", "male": "", "female": ""},
        "六角ドライバー": {"ctname": "オークション > 住まい、インテリア > 工具、DIY用品 > ハンドツール、大工道具 > スパナ、レンチ > 六角棒レンチ", "y_ct": "2084303401","sex": "0", "male": "", "female": ""},
        "電気ドリルシャフト": {"ctname": "オークション > 住まい、インテリア > 工具、DIY用品 > その他", "y_ct": "24674", "sex": "0", "male": "","female": ""},
        "アンクレット": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > アンクレット > その他", "y_ct": "2084062566", "sex": "0","male": "", "female": ""},
        "コードリール": {"ctname": "オークション > 住まい、インテリア > 工具、DIY用品 > 電動工具 > コードリール、延長コード > コードリール", "y_ct": "2084207800","sex": "0", "male": "", "female": ""},
        "メイクアップブラシ": {"ctname": "オークション > ビューティー、ヘルスケア > コスメ、スキンケア > メイク道具、化粧小物 > ブラシ、チップ、コーム > メイクブラシセット","y_ct": "2084228681", "sex": "0", "male": "", "female": ""},
        "バングル": {"ctname": "オークション > アクセサリー、時計 > レディースアクセサリー > ブレスレット、バングル > バングル > その他", "y_ct": "2084019059","sex": "0", "male": "", "female": ""},
        "エクステンション": {"ctname": "オークション > 住まい、インテリア > 工具、DIY用品 > ハンドツール、大工道具 > 工具セット", "y_ct": "2084303396", "sex": "0","male": "", "female": ""},
        "ヘッドキャップ": {"ctname": "オークション > ファッション > ファッション小物 > 帽子 > 女性用 > その他", "y_ct": "2084006690", "sex": "1","male": "2084006684", "female": "2084006690"},
        "Joy-Con": {"ctname": "オークション > おもちゃ、ゲーム > ゲーム > テレビゲーム > ニンテンドースイッチ > ニンテンドースイッチアクセサリー", "y_ct": "2084315796","sex": "0", "male": "", "female": ""},
        "スマホケース": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0","male": "", "female": ""},
        "iPhoneケース": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0","male": "", "female": ""},
        "iphoneケース": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0","male": "", "female": ""},
        "スマホカバー": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > その他", "y_ct": "2084005062", "sex": "0","male": "", "female": ""},
        "ボクサーパンツ": {"ctname": "オークション > ファッション > メンズファッション > インナーウエア > ボクサーブリーフ > Mサイズ", "y_ct": "2084053072","sex": "0", "male": "", "female": ""},
        "パーティグッズ": {"ctname": "オークション > おもちゃ、ゲーム > 手品、パーティグッズ > パーティグッズ > その他", "y_ct": "2084059858", "sex": "0","male": "", "female": ""},
        "キーチェーン": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > キーチェーン、ウォレットチェーン > キーチェーン", "y_ct": "2084062588","sex": "0", "male": "", "female": ""},
        "キーホルダー": {"ctname": "オークション > アクセサリー、時計 > メンズアクセサリー > キーチェーン、ウォレットチェーン > キーチェーン", "y_ct": "2084062588","sex": "0", "male": "", "female": ""},
        "ストラップ": {"ctname": "オークション > 自動車、オートバイ > 自動車関連グッズ > アパレル > その他", "y_ct": "2084062588", "sex": "0", "male": "","female": ""},
        "スウェットパンツ": {"ctname": "オークション > ファッション > メンズファッション > パンツ、スラックス > Mサイズ", "y_ct": "2084224619", "sex": "1","male": "2084224619", "female": "2084224590"},
        "ハーフパンツ": {"ctname": "オークション > ファッション > メンズファッション > パンツ、スラックス > Mサイズ", "y_ct": "2084224619", "sex": "1","male": "2084224619", "female": "2084224595"},
        "バッテリーチェッカー": {"ctname": "オークション > 自動車、オートバイ > 工具 > その他", "y_ct": "2084042062", "sex": "0", "male": "","female": ""},
        "バッテリーテスター": {"ctname": "オークション > 自動車、オートバイ > 工具 > その他", "y_ct": "2084042062", "sex": "0", "male": "","female": ""},
        "電池残量測定器": {"ctname": "オークション > 自動車、オートバイ > 工具 > その他", "y_ct": "2084042062", "sex": "0", "male": "","female": ""},
        "USBケーブル": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > バッテリー、充電器 > USB式充電器", "y_ct": "2084239197","sex": "0", "male": "", "female": ""},
        "HDMIケーブル": {"ctname": "オークション > 家電、AV、カメラ > 映像機器 > 映像用ケーブル > HDMIケーブル", "y_ct": "2084239134", "sex": "0","male": "", "female": ""},
        "充電ケーブル": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > バッテリー、充電器 > USB式充電器", "y_ct": "2084239197","sex": "0", "male": "", "female": ""},
        "壁飾り": {"ctname": "オークション > ホビー、カルチャー > ハンドクラフト、手工芸 > 裁縫、刺繍 > 完成品 > その他", "y_ct": "2084240874", "sex": "0","male": "", "female": ""},
        "リース": {"ctname": "オークション > ホビー、カルチャー > ハンドクラフト、手工芸 > 裁縫、刺繍 > 完成品 > その他", "y_ct": "2084240874", "sex": "0","male": "", "female": ""},
        "オーナメント": {"ctname": "オークション > ホビー、カルチャー > ハンドクラフト、手工芸 > 裁縫、刺繍 > 完成品 > その他", "y_ct": "2084240874", "sex": "0","male": "", "female": ""},
        "デニムバック": {"ctname": "オークション > ファッション > 男女兼用バッグ > リュックサック、デイパック", "y_ct": "2084233233", "sex": "0", "male": "","female": ""},
        "ショルダーバック": {"ctname": "オークション > ファッション > 男女兼用バッグ > リュックサック、デイパック", "y_ct": "2084233233", "sex": "0","male": "", "female": ""},
        "スリッパ": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > スリッパ", "y_ct": "2084047779", "sex": "0", "male": "","female": ""},
        "部屋履き": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > スリッパ", "y_ct": "2084047779", "sex": "0", "male": "","female": ""},
        "ルームシューズ": {"ctname": "オークション > 住まい、インテリア > 家庭用品 > スリッパ", "y_ct": "2084047779", "sex": "0", "male": "","female": ""},
        "コスプレ服": {"ctname": "オークション > コミック、アニメグッズ > コスプレ衣装 > 学生服", "y_ct": "2084311904", "sex": "0", "male": "","female": ""},
        "コスプレ衣装": {"ctname": "オークション > コミック、アニメグッズ > コスプレ衣装 > 学生服", "y_ct": "2084311904", "sex": "0", "male": "","female": ""},
        "プリンセス服": {"ctname": "オークション > コミック、アニメグッズ > コスプレ衣装 > 学生服", "y_ct": "2084311904", "sex": "0", "male": "","female": ""},
        "扇子": {"ctname": "オークション > ファッション > ファッション小物 > 扇子", "y_ct": "2084045073","sex": "0", "male": "", "female": ""},
        "ミニドレス": {"ctname": "オークション > ファッション > レディースファッション > フォーマル > カラードレス > その他", "y_ct": "2084064292", "sex": "0","male": "", "female": ""},
        "ウェディングベール": {"ctname": "オークション > ファッション > レディースファッション > フォーマル > カラードレス > その他", "y_ct": "2084064292","sex": "0", "male": "", "female": ""},
        "腕時計": {"ctname": "オークション > アクセサリー、時計 > メンズ腕時計 > アナログ（クォーツ式） > その他", "y_ct": "2084053684", "sex": "1","male": "2084053684", "female": "2084223414"},
        "変換プラグ": {"ctname": "オークション > 家電、AV、カメラ > 電子部品 > コネクタ", "y_ct": "2084282461", "sex": "0", "male": "","female": ""},
        "中継プラグ": {"ctname": "オークション > 家電、AV、カメラ > 電子部品 > コネクタ", "y_ct": "2084282461", "sex": "0", "male": "","female": ""},
        "ホログラム": {"ctname": "オークション > 自動車、オートバイ > メンテナンス > 塗料", "y_ct": "2084049690", "sex": "0", "male": "","female": ""},
        "イヤーフック": {"ctname": "オークション > 家電、AV、カメラ > オーディオ機器 > ヘッドフォン、イヤフォン > イヤフォン > その他", "y_ct": "2084219572","sex": "0", "male": "", "female": ""},
        "ガラスフイルム": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール", "y_ct": "2084299106","sex": "0", "male": "", "female": ""},
        "強化ガラス": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール", "y_ct": "2084299106", "sex": "0","male": "", "female": ""},
        "保護フィルム": {"ctname": "オークション > 家電、AV、カメラ > 携帯電話、スマートフォン > アクセサリー > 保護フィルム、シール", "y_ct": "2084299106","sex": "0", "male": "", "female": ""},
        "トートバック": {"ctname": "オークション > ファッション > 男女兼用バッグ > トートバッグ", "y_ct": "2084233232", "sex": "0", "male": "","female": ""},
        "ハンドグリップ": {"ctname": "オークション > スポーツ、レジャー > スポーツ別 > エクササイズ用品 > ギア > その他", "y_ct": "2084006837", "sex": "0","male": "", "female": ""},
        "眼鏡 ケース": {"ctname": "オークション > ビューティー、ヘルスケア > めがね、コンタクト > めがね > その他", "y_ct": "2084063613", "sex": "0","male": "", "female": ""},
        "グリッパー": {"ctname": "オークション > スポーツ、レジャー > スポーツ別 > エクササイズ用品 > ギア > その他", "y_ct": "2084006837", "sex": "0","male": "", "female": ""},
        "眼鏡ケース": {"ctname": "オークション > ビューティー、ヘルスケア > めがね、コンタクト > めがね > その他", "y_ct": "2084063613", "sex": "0","male": "", "female": ""},
        "サニタリーショーツ": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > ショーツ > サニタリー", "y_ct": "2084211791","sex": "0", "male": "", "female": ""},
        "生理用ショーツ": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > ショーツ > サニタリー", "y_ct": "2084211791","sex": "0", "male": "", "female": ""},
        "ナプキン": {"ctname": "オークション > ファッション > レディースファッション > インナーウエア > ショーツ > サニタリー", "y_ct": "2084211791", "sex": "0","male": "", "female": ""},
        "コンソールケーブル": {"ctname": "オークション > コンピュータ > パーツ > ケーブル、コネクタ > その他", "y_ct": "2084039542", "sex": "0", "male": "","female": ""},
        "ロールオーバーケーブル": {"ctname": "オークション > コンピュータ > パーツ > ケーブル、コネクタ > その他", "y_ct": "2084039542", "sex": "0","male": "", "female": ""},
        "3D ゴーグル": {"ctname": "オークション > 家電、AV、カメラ > 映像機器 > その他", "y_ct": "2084051816", "sex": "0", "male": "","female": ""},
        "3Dゴーグル": {"ctname": "オークション > 家電、AV、カメラ > 映像機器 > その他", "y_ct": "2084051816", "sex": "0", "male": "","female": ""},
        "VRメガネ": {"ctname": "オークション > 家電、AV、カメラ > 映像機器 > その他", "y_ct": "2084051816", "sex": "0", "male": "","female": ""},
        "バーチャルリアリティメガネ": {"ctname": "オークション > 家電、AV、カメラ > 映像機器 > その他", "y_ct": "2084051816", "sex": "0", "male": "","female": ""},
        "トランプ": {"ctname": "オークション > おもちゃ、ゲーム > ゲーム > カードゲーム > トランプ", "y_ct": "40534", "sex": "0", "male": "","female": ""},
        "カードゲーム": {"ctname": "オークション > おもちゃ、ゲーム > ゲーム > カードゲーム > トランプ", "y_ct": "40534", "sex": "0", "male": "","female": ""},
        "アンダーウェア": {"ctname": "オークション > スポーツ、レジャー > スポーツウエア > 男性用 > インナーウエア > シャツ", "y_ct": "2084246663", "sex": "0","male": "", "female": ""},
        "コンプレッションウェア": {"ctname": "オークション > スポーツ、レジャー > スポーツウエア > 男性用 > インナーウエア > シャツ", "y_ct": "2084246663","sex": "0", "male": "", "female": ""},
    
"""

class BuyersBrandInfo(object):
    def __init__(self, logger):
        self.logger = logger
        help = 'get from ya buyers brand list.'
        self.logger.info('buyers_brand_info in. init')
        self.upd_csv = []

    # 指定された文字列中からブランドコードをチェックしてマッチしたら消し込む。
    # 取り扱いできないブランド（送料などが対応不可）であればNGのフラグを第２パラメータで返却する
    # 商品コードと配送コードが取得できたら返却する。
    # return:
    #  0: 不要文字を消し込んだ商品名
    #  1: ngフラグ
    #  2: バイヤーズの商品コード
    #  3: バイヤーズの配送コード
    def chk_goods_title(self, chk_str):

        try:
            ng_flg = 0
            ret_goods_cd = ''
            ret_delivery_cd = ''
            """
            商品名の削除の前に、商品コードとブランドコードを分析する
            """
            retobj = re.findall('^([a-z\d]+) ([a-z\d]+) ', chk_str)
            if len(retobj) == 1:
                retstr = retobj[0][0] + retobj[0][1]

                # 商品コードと配送コードに分離
                retobj_2 = re.findall('^([a-z]+[\d]+)([a-z]+[\d]+)', retstr)
                if len(retobj_2) == 1:
                    ret_goods_cd = retobj_2[0][0]
                    ret_delivery_cd = retobj_2[0][1]
                else:
                    # エラー
                    pass
            else:
                # エラー
                pass

            # 取り扱いNGのブランドはチェックフラグをたてる
            for ng_item in __class__._MY_GR_CODES_NG:
                if chk_str.find(ng_item) > -1:
                    ng_flg = 1

            # 先頭の小文字4文字を消し込む
            # ngでないものだけ削除、NGなものは確認用に残しておく
            if ng_flg == 0:
                """
                # ブランドコード 英字 4桁始まり　固定
                chk_str = re.sub('^[a-z]{4} ', "", chk_str)

                # 雑貨などの特定商品　数字3桁始まり固定
                chk_str = re.sub('^[0-9]{3} ', "", chk_str)

                # 続いて、数字3桁+小文字＋数字4桁固定
                chk_str = re.sub('^[0-9]{3}[a-z\d]{4} ', "", chk_str)
                """
                chk_str = re.sub('^[a-z\d]+ [a-z\d]+ ', "", chk_str)

            # 変換する文字。shift-jis変換でコケた文字はここに登録
            for exchange_words in __class__._MY_EXCHANGE_WORDS:
                chk_str = re.sub(exchange_words[0], exchange_words[1], chk_str)

            # NGな文章も消しておく
            for ng_words in __class__._MY_DEL_WORDS:
                chk_str = re.sub(ng_words, "", chk_str)

            # サブカテゴリにマッチしたら正解
            return chk_str, ng_flg, ret_goods_cd, ret_delivery_cd

        except Exception as e:
            self.logger.debug(traceback.format_exc())
            return False

    """
    配送関連情報を、バイヤーズ配送コードから割り出す
    ret1: deli_method　2(送料無料) か3（個別送料）
    ret2: wowmaの配送コード
    ret3: qoo10の配送コード
    
    ### Qoo10 yukiyuki-shop 送料コード設定 ##########
    549678　:　送料無料、追跡あり
    555768　:　送料無料、追跡なし　定形外
    555767　:　送料無料、佐川で沖縄離島は1500円　（sg）
    555770　:　ゆうパック、yp06 60サイズ
    555771　:　ゆうパック、yp08 80サイズ
    555772　:　ゆうパック、yp10 100サイズ
    555773　:　ゆうパック、yp12 120サイズ
    555774　:　ゆうパック、yp14 140サイズ
    555776　:　ゆうパック、yp16 160サイズ

    ### Wowma  送料コード設定 ##########
    100003　:　送料無料、追跡あり
    100003　:　送料無料、追跡なし　定形外
    100005　:　送料無料、佐川で沖縄離島は1500円　（sg）
    100060　:　ゆうパック、yp06 60サイズ
    100080　:　ゆうパック、yp08 80サイズ
    100100　:　ゆうパック、yp10 100サイズ
    100120　:　ゆうパック、yp12 120サイズ
    100140　:　ゆうパック、yp14 140サイズ
    100160　:　ゆうパック、yp16 160サイズ

    """
    def get_delivery_info(self, delivery_cd):

        try:
            ret_deli_method = 2
            ret_wow_deli_id = 100003 # 送料無料 追跡あり
            ret_qoo_deli_id = 549678 # 送料無料 追跡あり

            # 配送コードにマッチする文字列から割り出す
            m = re.search(r'upk|nkps|ltpp|zgyx', delivery_cd) # ゆうパック　送料無料
            if m:
                pass # 初期設定のまま

            m = re.search(r'tkgi|tk50|kn05|ygtx|fmaz', delivery_cd) # 定形外　送料無料
            if m:
                ret_qoo_deli_id = 555768
                ret_wow_deli_id = 100003 # 送料無料 追跡あり

            m = re.search(r'sg', delivery_cd) # 沖縄県または離島の場合は別途1500円
            if m:
                ret_qoo_deli_id = 555767
                ret_wow_deli_id = 100005
                ret_deli_method = 3

            m = re.search(r'yp06', delivery_cd) # yp06
            if m:
                ret_qoo_deli_id = 555770
                ret_wow_deli_id = 100060
                ret_deli_method = 3
            m = re.search(r'yp08', delivery_cd) # yp08
            if m:
                ret_qoo_deli_id = 555771
                ret_wow_deli_id = 100080
                ret_deli_method = 3
            m = re.search(r'yp10', delivery_cd) # yp10
            if m:
                ret_qoo_deli_id = 555772
                ret_wow_deli_id = 100100
                ret_deli_method = 3
            m = re.search(r'yp12', delivery_cd) # yp12
            if m:
                ret_qoo_deli_id = 555773
                ret_wow_deli_id = 100120
                ret_deli_method = 3
            m = re.search(r'yp14', delivery_cd) # yp14
            if m:
                ret_qoo_deli_id = 555774
                ret_wow_deli_id = 100140
                ret_deli_method = 3
            m = re.search(r'yp16', delivery_cd) # yp16
            if m:
                ret_qoo_deli_id = 555776
                ret_wow_deli_id = 100160
                ret_deli_method = 3

            return ret_deli_method, ret_wow_deli_id, ret_qoo_deli_id

        except Exception as e:
            self.logger.debug(traceback.format_exc())
            return False

    # 指定された文字列を末尾を指定の長さでカット。かつ、中途半端な単語を切った場合は
    # 末尾から直前の空白まで削除していく。商品タイトルや検索キーワード用
    @staticmethod
    def cut_str(chk_str, max_len):
        try:
            tmp_str = chk_str[:max_len]
            if len(tmp_str) == max_len:
                # 最大文字数と同じならチェック（切り出したはず）
                i = 0
                while True:
                    i += 1
                    m = re.match(r'.+[ 　]$', tmp_str)
                    if m:
                        # もし空白マッチしたら、trimして終了
                        tmp_str = tmp_str.rstrip()
                        break
                    else:
                        max_len = len(tmp_str) - 1
                        # もし通常文字なら、一文字消して続行
                        tmp_str = tmp_str[:max_len]
                    if i == max_len:
                        break
            else:
                # この場合はそのままにする
                pass
 
            return tmp_str

        except Exception as e:
            print(traceback.format_exc())
            return False

    def chk_goods_detail(self, chk_str):

        try:
            ng_flg = 0
            worn_key = ""

            # まず取り扱いOKのブランドコードを消し込み
            for item in __class__._MY_GR_CODES_DEL:
                chk_str = re.sub(item, "", chk_str)

            # 取り扱いNGのブランドはチェックフラグもたてる
            for ng_item in __class__._MY_GR_CODES_NG:
                if chk_str.find(ng_item) > -1:
                    ng_flg = 5 # 5にしてdeleteにしよう
                    #chk_str = re.sub(ng_item, "", chk_str)


            # 先頭文字を消し込む
            # ブランドコード 英字 4桁始まり　固定
            chk_str = re.sub('^[a-z]{4} ', "", chk_str)

            # 雑貨などの特定商品　数字3桁始まり固定
            chk_str = re.sub('^[0-9]{3} ', "", chk_str)

            # 続いて、数字3桁+小文字＋数字4桁固定
            chk_str = re.sub('^[0-9]{3}[a-z\d]{4} ', "", chk_str)

            # httpsや、特殊な文字列が入っていたら、それ以降は面倒なので消してしまう
            chk_str = re.sub(r'https:(.+?)', "", chk_str)
            chk_str = re.sub(r'/buyerz.shop(.+?)', "", chk_str)
            chk_str = re.sub(r'【商品バリエーション】(.+?)', "", chk_str)
            chk_str = re.sub(r'【関連商品】(.+?)', "", chk_str)
            chk_str = re.sub(r'関連商品(.+?)', "", chk_str)
            chk_str = re.sub(r'/www.dropbox.com(.+?)', "", chk_str)
            chk_str = re.sub(r'shop/shopbrand.html(.+?)', "", chk_str)

            # NGな文章も消しておく
            for ng_words in __class__._MY_DEL_WORDS:
                chk_str = re.sub(ng_words, "", chk_str)

            # 変換する文字。shift-jis変換でコケた文字はここに登録
            for exchange_words in __class__._MY_EXCHANGE_WORDS:
                chk_str = re.sub(exchange_words[0], exchange_words[1], chk_str)

            # タグも消しておく
            chk_str = re.sub(r'<a>https:(.+?)</a>', "", chk_str)
            chk_str = re.sub(r'<a(.+?)>https:(.+?)</a>', "", chk_str)
            chk_str = re.sub(r'<a(.+?)>', "", chk_str)
            chk_str = re.sub('</a>', "", chk_str)
            chk_str = re.sub(r'<span(.+?)>', "", chk_str)
            chk_str = re.sub('</span>', "", chk_str)
            chk_str = re.sub(r'https:(.+?)\n', "", chk_str)
            chk_str = re.sub(r'<img(.+?)>', "", chk_str)
            chk_str = re.sub(r'<br style(.+?)>', "", chk_str)

            # 確認すべきキーワードに引っかかったらチェックしておく。
            # 商品説明の冒頭に、キーワードを付記しておく
            for ng_words in __class__._MY_CHK_WORDS:
                if chk_str.find(ng_words) > -1:

                    chk_flg = 1
                    # 確認スべきキーワードであってもOKの文章の一部であればスルーする
                    for ok_words in __class__._MY_CHK_OK_WORDS:
                        if chk_str.find(ok_words) > -1 and ok_words.find(ng_words) > -1 :
                            chk_flg = 0

                    if chk_flg == 1:
                        ng_flg = 6
                        chk_str = '[' + ng_words + ']' + chk_str
                        worn_key = '[' + ng_words + ']' + worn_key

            # サブカテゴリにマッチしたら正解
            return chk_str, ng_flg, worn_key

        except Exception as e:
            self.logger.debug(traceback.format_exc())
            return False



    # 扱いOKだが、商品名・商品説明から削除しておくブランドコード
    _MY_GR_CODES_DEL = [
        "zvpa",
        "hbab",
        "spab",
        "zyta",
        "ddab",
        "zgyx",
        "xmab",
    ]

    # 扱いNGだが、商品名・商品説明から削除しておくブランドコード
    """
    ■バイヤーズの配送ルール、配送記号について
    https://buyerz.jp/wholesale/%e7%b7%8a%e6%80%a5%e3%81%ae%e9%85%8d%e9%80%81%e3%81%a8%e3%80%81%e9%80%9a%e5%b8%b8%e3%83%bb%e7%b7%8a%e6%80%a5%e9%85%8d%e9%80%81%e3%81%ae%e5%88%b0%e7%9d%80%e3%81%be%e3%81%a7%e3%81%ae%e6%97%a5%e6%95%b0/
    
    https://buyerz.shop/new/2018-07-19-185208.html?_ga=2.115492162.556954132.1634903115-1893302815.1632927011
    
    配送業者は商品タイトルに記載されている記号から確認可能です。下記のように「英字2文字、数字3文字、英字4文字」という型番が全商品についています。配送業者は「最後の英字4文字」で判断します。
    
    fhab 001upk1
    fhab 002upk2
    fhab 003upk3
    fhab 004tkgi
    fhab 005nkps
    
    「upk1、upk2、upk3、tkgi、nkps、ltpp」と6種類あります。
    
    upk1、upk2、upk3=　日本郵便のゆうパケット（追跡番号あり、商品保証なし）
    nkps=　ヤマト運輸のネコポス便（追跡番号あり、商品保証なし、即日配達）
    tkgi=　日本郵便の定形外郵便（追跡番号なし、商品保証なし）
    「ltpp」は郵便局のレターパックプラス。
    
    商品名、アルファベット4桁数字3桁or4桁の後に「sg」と記載のあるものは
    送料が商品代金に基本的に含まれておりますが、沖縄県または離島の場合は別途1500円かかります。
    
    商品名、アルファベット4桁数字3桁or4桁の後に「yp」と記載のあるものは送料が商品代金に含まれておりません。
     例）aaab 000yp06　ゆうパックでの発送となります。 
    銀行振込にてご購入される方は送料込みの合計価格をご入金頂き、 
    ポイントにてご購入される方はポイント利用の画面にて、必ず「すべてのポイントを利用する」をご選択ください。
    
    yp06 (60サイズ)
    yp08
    yp10
    yp12
    yp14
    yp16
    
    北海道3日、沖縄6日、近畿1日、その他2日
    
    amzn＝Amazonから配送
    
    zaqa 1020tk50　「tk50」は「定型外郵便500g以内」での全国一律料金発送です。
    zaqa 1031kn05 「kn05」は「定型郵便規格内」での全国一律料金発送です。
    とかもある
    
    """
    _MY_GR_CODES_NG = [
        "zzz", # ロット商品らしい
        #"yp", # 送料がかかる
        "cpct", # 送料がかかる
        "cheers", # 仕入れができない
        "amzn", # Amazonから配送
        "opsn", # バイヤーズのオプション
        "アクセサリーギフトオプション", # アクセサリーギフトオプション
        "ロット商品",
        "個人利用向け商品",
        "包装オプション",
        "ガスアダプター",
        "ボンテージ",
        "セクシーランジェリー",
        "ykpa",  # 模造品をよく出すブランド
        "ynja",  # 模造品をよく出すブランド
    ]

    # Shift-jis変換が効かない文字などを変換する。
    _MY_EXCHANGE_WORDS = [
        ['㎝','cm'],
        ['㎏','kg'],
        ['㎎','mg'],
        ['゙','”'],
        ['゚|\u02da','°'],
        ['♫','♪'],
        ['♬','♪'],
        ['Ⅿ','M'],
        ['Ⅽ','C'],
        ['Ⅼ','L'],
        ['✕','Ｘ'],
        ['－','-'],
        ['✅','■'],
        ['‼','！'],
        ['※|\u2733','※'],
        [',','、'],
        ['\n', '<br/>'],
        ['～|\u223c', '~'],
        ['•|◎', '●'],
        ['\u2014|–', '-'],
        ['：', ':'],
        ['バストアップ', '育乳'],
        ['\u2460|\u2780|\u2160', '１'],
        ['\u2461|\u2781|\u2161', '２'],
        ['\u2462|\u2782|\u2162', '３'],
        ['\u2463|\u2783|\u2163', '４'],
        ['\u2464|\u2784|\u2164', '５'],
        ['\u2465|\u2785|\u2165', '６'],
        ['\u2466|\u2786|\u2166', '７'],
        ['\u2467|\u2787|\u2167', '８'],
        ['\u2468|\u2788|\u2168', '９'],
        ['\u2469|\u2789|\u2169', '１０'],
        ['\u24b6', 'A.'],
        ['\u24b7', 'B.'],
        ['\u24b8', 'C.'],
        ['\u24b9', 'D.'],
        ['\u24ba', 'E.'],
        ['\ufe0f', ':'],
        ['\u2762', '！'],
        ['\u2764', '・'],
        ['\u2b1b|\u26ab|\U0001f9f6|\u2600|\U0001f9e3|\U0001f381|\U0001f4a1|\u25fc|\u263a', '■'],
        ['\u2660|\u2661|\u2662', '■'],
        ['\uf06c|\'', ''],
        ['\u339c', 'mm'],
        ['\u2728|\u2729', '★'],
        ['|♡|♠|♢|✔|♥|♣|♧|♦|♨|♩|╰|︶|╯|\u202a|\u7e6b|\ufe0e|\u525d|\u5e26|\u02ca|\u1d55|\u02cb|\u6d01|\u26a0', ''],
        ['\uf0b7|\u26aa|\u52bf|\u2b50',''],
    ]

    # 扱いOKだが、商品名・商品説明から削除しておくブランドコード
    _MY_DEL_WORDS = [
        '※ご入金いただいたご注文に関しましては、1～2日以内に発送いたします。',
        'ご入金いただいたご注文に関しましては、1~2日以内に大阪からゆうパケットで発送いたします。',
        '★発送について',
        '※追跡番号あり。ゆうパケット【送料無料】【税込み】',
        '以下メルカリ説明用 販売先用に編集してください。',
        '数多くの商品の中からからご覧頂きありがとうございます！',
        '　　　　　コメント無しの即購入OKです！',
        '◇◆◇◆◇◆◇◆◇◆◇◆◇◆◇◆◇◆◇◆◇◆◇◆◇',
        '送料は全国無料で発送致します。',
        '発送までに2日～3日お時間を頂く場合がございますが、ご了承ください。',
        '購入希望の方は、赤色の「購入」または「購入手続きへ」のボタンからご購入お願いします。</div>',
        '【送料無料】',
        '（送料無料）',
        '☆彡　送料無料',
        '★送料無料',
        '※この商品は送料無料です。',
        '送料無料',
        '【型番 ygtx は《自社発送》となります】',
        '・注文確定日（入金日）の翌営業日までに発送致します。（日曜除く）',
        '※土曜日に入金の場合、月曜日発送となる場合が御座います。',
        '予め2~3日程度の発送設定をお薦め致します。',
        '型番zgyx商品はすべて自社発送です。',
        'ご入金いただいたご注文に関しましては、1～2日以内に大阪からゆうパケットで発送いたします。',
        'ご注意：タイトルの一番前に書いてる　色とサイズは　このページの商品です、ご確認していただいてから、ご購入お願いいたします。',
        '・保証付きはプロフをご確認願います。',
        '・基本的にはご入金確認後の翌日の発送となります。',
        '・ご住所入力漏れによる返送は着払いにて再送させていただきます。',
        'お値引きは対応したしかねますのご了承願います。',
        '◆無在庫販売者様へのお願い◆',
        'この商品の在庫は切らさないように、毎日在庫チェックしています',
        '大変安定して利益を得やすい商品となります。',
        '★なるべくお安く提供する為に、簡易包装・普通郵便での配送を予定しておりますのであらかじめご了承願います。',
        '★販売者プロフィール★',
        '※商品の不良については到着後3日以内にご連絡お願い致します。',
        'それ以降の対応については致しかねます。',
        'メルカリで複数アカウント運用させていただいております。',
        'メルカリ無在庫販売には自信があります。',
        '無在庫やっていて不安のある ・商品詳細のコメント対応 ・メルカリ販売用テンプレート を徹底対応させていただきます。',
        'myabが扱う商品はメルカリで稼げる商品となります。',
        'myabが販売させていただいてる商品は最低でも75円利益でる商品となります。',
        'メルカリの相場が下がってきた場合、当店の価格調整も行っております。',
        '気軽にお問合せください。',
        '以下メルカリ説明用 販売先用に編集してください。',
        '★仕入れ,卸問屋,ドロップシッピング★',
        '☆彡　意外と知られてないバカ売れ商品',
        '☆彡　amazonランキング[ベビー＆マタニティ]50位以内、メルカリ・ラクマなど1,500～2,000円位で多数販売実績有り♪',
        '☆彡　一部カラーリング・ロゴ等が変更になってます。スマホ撮影実物写真でご確認願います。',
        '追跡番号はメールにてご連絡いたします。',
        '土、日、祝日、年末年始にも休まずに通常発送いたします。',
        '（お願い：住所間違いなど再送料金かかります。盗難、未投函などの補償なし。日時指定、代引き不可、ご了承ください。）',
        '定形外郵便※追跡番号なし（送料無料）群馬県より発送',
        '【発送方法】',
        '「kn05」は「定型郵便規格内」での全国一律料金発送です。',
        '送料は販売価格に含まれていますが、発送時に「追跡番号がつけられない発送方法」となりますのでご了承ください。',
        '再入荷についてお問い合わせをする',
        '※こちらの価格には消費税が含まれています。',
        '1,480',
        'SOLD OUT',
        '外部サイトに貼る',
        '通報する',
        '◆◆◆',
        '大きなサイズの商品画像はこちらのDropboxからDLできます。',
        '【送料・税込880円】で',
        '⇒⇒⇒ 送料・税込 880円！',
        'お値引きは対応したしかねますのご了承願います。</div>',
        'お気軽のご質問ください。',
        '気になることなどは、ご購入前に',
        '「tk50」は「定型外郵便500g以内」での全国一律料金発送です。',
        '送料は販売価格に含まれていますが、発送時に「追跡番号がつけられない発送方法」となりますのでご了承ください。',
        '定形外郵便※追跡番号なし（送料無料）',
        '▼▼▼▼▼▼商品説明文は以下▼▼▼▼▼▼',
        '<a href=\"\"https://buyerz.shop/shop/shopbrand.html?search=ygt/\"\" target=\"\"_blank\"\"><img src=\"\"https://img21.shop-pro.jp/PA01428/325/etc/sample1.png?cmsp_timestamp=20191218035250\"\"></a>',
        '<form action=\"\"https://www.amazon.co.jp/gp/product/handle-buy-box/ref=dp_start-bbf_1_glance\"\" id=\"\"twister\"\" method=\"\"post\"\">',
        '■メール便で送料無料■',
        '配送料は無料でお送り致します。',
        '配送方法はメール便になります。',
        '<a href=\"\"https://www.amazon.co.jp/dp/B07HGC6QPT?th=1\"\">Amazonに在庫あります</a></div>',
        '在庫切れの場合は↓確認ください。ここより安いかも！？',
        '<form action=\"\"https://www.amazon.co.jp/gp/product/handle-buy-box/ref=dp_start-bbf_1_glance\"\" id=\"\"twister\"\" method=\"\"post\"\">',
        '昨年のアマゾンベストセラー商品です。',
        '郵便局定形内郵便でお届けします。',
        '☆彡　Ya〇〇〇ショッピング送料込み1,985円で販売実績有り（粗利益：１,286円　粗利率：64.7%）',
        '楽天の通販などでは販売していないような種類を作成しました。',
        '商品は自店（三重県）からクリックポストで発送します。★送料無料★',
        '☆彡　在庫切れリスク回避 バイヤーズ在庫管理システムで安心（説明文下段参照）',
        '☆彡　大口注文でさらに驚愕値引き',
        '☆彡　保管場所不要',
        '☆彡　発送の自動化（倉庫から任意の配送先に当日若しくは翌日発送開始）',
        '☆彡　スマホ撮影　実物写真有り',
        '【定形外郵便発送】',
        '発送：定形外郵便 追跡番号はありません。',
        '発送地：東京都',
        '※当日発送不可、前日までのご入金で翌日発送、日曜発送はございません。バイヤーズ倉庫発送の商品と異なりますので、ご了承下さい。',
        '※バイヤーズの各種オプションは併用出来ませんのでご注意ください。',
        '【メール便OK】',
        '定形外郵便※追跡番号なし群馬県より発送',
        '【メール便発送 】',
        '(↓リンク)',
        '定形外郵便※追跡番号なし群馬県より発送',
        '配送方法 クリックポスト',
        '定形外郵便※追跡番号なし',
        '＜出品者様へ＞',
        '※こちらの商品は在庫が30個を下回った時点で',
        '再発注しております。在庫切れの場合でも、最長10日以内に復活いたしますので、',
        '安心して販売促進をお願いできたらと思います。',
        '他にも売れる商品をご用意しております！！商品検索で「zbb」<wbr>と検索をお願い致します。',
        '★発送について',
        '※商品説明にタイトル以外のカラー画像も使用しています※',
        '<br>\r\n<br>\r\n<br>',
        '以上改善したところですが、改善した事によって、単価は少しだけ高くなりますが、その価値は絶対ありますので、是非売ってみてください。',
        'この商品に関して、たくさんお客様からの声を聞いて、今まで売っていただいた商品の欠点が把握し',
        'これからもっと長く安定に続けて売っていただきたいので、',
        '思い切って、商品を改善させていただきました。',
        '何メーカーと商談し、改善したいところを伝えて、サンプルもたくさん参考しました。',
        'その結果はやっと、価値がある商品が見つかりました。',
        '基本年中無休です。',
        '\r\n\r\n\r\n',
        '※クリックポストでの自社発送です。1-2日以内に発送します。送料込み、追跡番号あり、埼玉県より出荷。',
        'こちらの商品は自社契約倉庫発送です。',
        'ご入金いただいたご注文に関しましては、2~4日（土日祝除く）以内に大阪から佐川急便で発送いたします',
        '（沖縄県及び一部離島地域ゆうパックになります）追跡可能',
        '配送先の電話番号必要になります。',
        '※商品出荷手配後の変更・キャンセルは承っておりません、ご注文内容をよくご確認のうえ、お買い求め頂ますようお願いいたします。',
        '定形外orヤマト',
        '※自社契約倉庫から発送ので、複数注文可能です。',
        'こちらの商品は自社契約倉庫から発送です。',
        '※商品出荷手配後の変更・キャンセルは承っておりません、ご注文内容をよくご確認のうえ、お買い求め頂ますようお願いいたします。',
        'ご入金いただいたご注文に関しましては、2~4営業日以内に大阪から佐川急便かゆうパックで発送いたします。（土日祝除く）',
        '※配送先の電話番号必要になります。',
        '※ご購入後お客様ご都合となるご返品は承ることはできませんので十分に確認の上ご注文くださいませ。',
        '検索ワード',
        '「tk1k」は「定型外郵便1㎏以内」での発送となり送料は販売価格に含まれています。',
        '商品発送時に「追跡番号がつけられない発送方法」となりますのでご了承ください。',
        '【ノーブランド 品】',
        '以下文は販売時、売りやすいように御自分の言葉で編集をしてくださいませ！',
        'あまりにも高価なブランド品だとあれですが',
        '頑張ればなんとかなるでしょう、自己責任でお願い致します',
        '失敗経験も大事な資産になりますし！',
        '■xmab 商品一覧',
        '■xmab 商品一覧()',
        '型番商品はすべて自社発送です。',
        '（素人採寸誤差多少があり）',
        '素人採寸',
        '★※生産ロットによってチュール1枚と3枚縫製、2枚と2枚縫製した場合があります！',
        'こちらの商品は自社発送です。',
        'ご入金いただいたご注文に関しましては、5日以内に大阪から佐川急便で発送いたします。',
        '（土日祝除く）配送先の電話番号必要になります。',
        'Amazonに在庫あります',
        '※1~2日以内に大阪からゆうパケットで発送いたします、追跡可能です。タイムリー追跡してください。',
        '※（ポストサイズ、入れ物いっぱいなど投函できない場合があります、早めに郵便局へ連絡して、再配達の依頼をしてください！',
        '※土日祭日の発送はお休みです、簡易包装となります',
        '型番商品はすべて自社発送です。<br/>',
        'ご入金いただいたご注文に関しましては、1～2日以内に大阪からゆうパケットで発送いたします。（追跡あり）',
        '■メール便で■',
        '★仕入れ,卸問屋,ドロップシッピング★',
        '発送について',
        'クリックポスト（追跡番号あり）での出荷です。',
        '※追跡番号あり、保証なし。群馬県より発送',
        'ゆうパケット（upk1,upk2,upk3）またはクリックポスト',
        '※簡易包装で発送になります。',
        '土日の発送はお休みです',
        '通常発送はゆうパケットです',
        '<img src=\"',
        '※追跡番号あり。【税込み】',
        '土日の発送はお休みをいただいております',
        'ご入金後2～3日以内に発送いたします、土日の発送はお休みです。',
        '追跡番号はメールにてご連絡いたします',
        'ご入金いただいたご注文に関しましては、1～2日以内に大阪から佐川急便、ゆうパック、ゆうパケットで発送いたします。',
        '・お客様へ提供する商品品質の観点より自社にてチェックしてからの発送　をしております。',
        '土日の発送はお休みです。</div>',
        '商品の再送、又は返金にてスグに対応させて頂きます。',
        '※評価後は対応出来ませんのでご注意下さい。',
        '配送方法：レターパックプラス',
        '　　　　　クリックポスト',
        '発送はメール便です 土日の発送はお休みです',
        '土日の発送はお休みです。',
        '※お送りする品はチェックした物を簡易包装にて発送させていただきます。',
        'チェックはしておりますが、購入後不具合が出ましたら交換対応させて頂きます',
        'ご連絡後返送いただき、届いた後に代替品をお送りします。',
        '発送はメール便です、土日の発送はお休みです',
        '包装は本体のみの簡易包装です、土日の発送はお休みです',
        '【安心の国内メーカー仕入れ！】',
        '定形外郵便にて発送 簡易包装です',
        'サイズが合わないのでは？と不安なあなたに！！当店ではお客様に安心してお買い求めいただくために「30日間返金保証」を付与していますので安心してお買い求めいただけます。',
        '■ 商品一覧()',
        '＊某サイトで3000円以上するので、',
        '&nbsp;',
        '☆彡　amazonランキング[ベビー＆マタニティ]50位以内、メルカリ・ラクマなど1,500～2,000円位で多数販売実績有り♪',
        '発送前の個別写真のご要望には対応できませんのでご了承ください。',
        '関東発送ゆうぱけっと便',
        '当社商品一覧はこちら！',
        'https://buyerz.shop/*',
        '↓',
        '【商品バリエーション】',
        '■バリエーション',
        '※ご入金いただいたご注文に関しましては、1~2日以内に大阪からゆうパケットで発送いたします。',
        '立体裁断により、陰茎と睾丸を別々に収納する【陰茎分離型】なのでベタつかず通気性バツグン',
        '局部をキープし',
        '袋部分が脚の付け根に付く感じの、',
        '陰嚢分離 のパンツは、様々ございますが、',
        '陰嚢分離',
        '',
        '<br/><br/><br/>',
        '※形状説明のため他カラー画像も含まれております※',
        '※形状説明のため他種類画像も含まれております※',
        '当社商品一覧は【ykha】でバイヤーズ上で検索！',
        '需要の高く売れている幅広いジャンルの商品を扱っております！',
        '■■■■■■■■■■■■■■■■',
        '【型番 ygtx は《自社発送》となります】',
        'こちらの商品は倉庫発送ではなく、自社発送商品になります。',
        '発送:普通郵便 送料込み',
        '発送地:群馬県',
        '※当日発送不可、前日までのご入金で翌日発送、日曜発送はございません。倉庫発送の商品と異なりますので、ご了承下さい。',
        '【型番 ygtx は《自社発送》となります】',
        '・注文確定日（入金日）の翌営業日までに発送致します。（日曜除く）',
        '※土曜日に入金の場合、月曜日発送となる場合が御座います。',
        '予め2~3日程度の発送設定をお薦め致します。',
        '【発送方法】<br/>定形外郵便※追跡番号なし群馬県より発送',
        '商品説明文は以下',
        '▼▼▼▼▼▼',
        '■ynza 商品一覧',
        '在庫切れの場合は確認ください。ここより安いかも',
        '佐川急便での発送です。必ず電話番号を入力してください。',
        '※発送は佐川急便となります、送料は商品代金に含まれております。',
        '※こちらの商品に関しまして、万が一不良等がございましたら、',
        '商品ページ内の[商品についてのお問合せ]よりご連絡をお願いいたします。',
        '如何なる場合でも商品返品後の返金、商品返品後の良品の発送となりますので、ご了承下さい。',
        '発送は佐川急便となります、送料は商品代金に含まれておりますが沖縄・離島は別途送料1500円が掛かります。',
        '※商品ページにsgと記載がございます商品は佐川急便での発送となります',
        '&lt;br/&gt;&lt;br/&gt;',
        '&lt;br/&gt;',
        '免責事項についてはプロフをご確認ください。',
        'ynza 商品一覧&lt;br/&gt;search=ynza&lt;br/&gt;&lt;br/&gt;',
        '[普通郵便]こちらの発送は普通郵便です。&lt;br/&gt;&lt;br/&gt;',
        '[普通郵便]こちらの発送は普通郵便です。<br/><br/>',
        '■ynza 商品一覧<br/>search=ynza<br/><br/>',
        '●立体構造により、陰茎と睾丸を別々に収納する【陰茎分離型】なのでベタつかず清潔で快適さを保ちます。',
        '立体裁断により、陰茎と睾丸を別々に収納する【陰茎分離型】なのでベタつかず、清潔で快適さを保ちます。<br/>',
        '3Dフォルム＋伸縮性素材により、睾丸をメッシュ生地で包み込み',
        '立体裁断により、陰茎と睾丸を別々に収納する【陰茎分離型】なのでベタつかず、清潔で快適さを保ちます。',
        'search=',
        '()',
    ]

    # =================== 不要文字を含むが定型文としてOKが取れてるのでスルーするキーワード =========================
    # _MY_CHK_WORDSがヒットしても、下記に該当する文章であれば問題なしなので、6に仕分けしない。
    _MY_CHK_OK_WORDS = [
        "☆発送前にチェックしていますが",
        "・安心！追跡番号付きです（保証はついておりません）",
        "・中身のわからないような梱包（簡易梱包）にて発送します。",
        "発送は安心の追跡番号付にて発送させていただきます！",
        "・こちらの商品は、お手頃価格のプライス価格で販売していますので、化粧箱は付いていませんが、商品に傷付かないよう簡易包装で発送とさせていただきます。",
        "発送重量",
        "コンパクトに発送するため、商品は二つ折りになっております。",
        "☆商品は簡易包装にて発送いたしております。ご理解の程、よろしくお願いいたします。",
        "検品してから発送してますが，",
        "●たたんだ状態で発送するため、折ジワがあります。",
        "緩衝材で保護の上、ボール紙保護ケースに入れて発送します。",
        "☆商品は簡易包装にて発送いたしております。",
        "発送前にとれていないか検品後発送しておりますが",
        "※発送の都合上、畳じわがあります。",
        "発送や保管状態により、",
        "発送は簡易包装となります。",
        "発送する場合は２タイプがランダム発送になりますので、ご了承ください。",
        "とても楽天的",
        "プロフェッショナル",
        "発送前に検品しておりますが万が一、不良などございました場合はすぐにご連絡下さい。",
        "発送上の状態によって商品がシワになる場合がございます",
        "３色セット",
        "コルセット",
        "アクセサリーセット",
        "個 セット",
        "フォーマルセット",
        "セットアップ",
        "2枚セット",
        "枚　セット",
        "点セット",
        "点 セット",
        "セット内容",
        "2セット",
        "3セット",
        "5組セット",
        "ピンセット",
        "本 セット",
        "リング セット",
        "ベルトのセットです",
        "セットの方法",
        "リング セット",
        "セット：",
        "上下セット",
        "セット内容：",
        "個セット",
        "セット クリスマス",
        "仮装 セット",
        "枚 セット",
        "2個1セット",
        "個 セット",
        "2個で1セット",
        "本セット",
        "本組セット",
        "コーデのセット",
        "ヨガウェアセット",
        "枚セット",
        "アソートセット",
        "足セット",
        "２個で1セット",
        "靴下セット",
        "色セット",
        "色 セット",
        "ヘッドセット",
        "ポーチもセット",
        "1セット",
        "セットです",
        "ケアセット",
        "組みセット",
        "4セット",
        "にセットすれば",
        "オープナーセット",
        "お得なセット",
        "種セット",
        "種 セット",
        "リードセット",
        "セットされている",
        "（帽子）セット",
        "コスプレセット",
        "２枚組１セット",
        "左右セット",
        "２つセット",
        "以上がセットされております。",
        "3種類セット",
        "セットジュエリー",
        "セット商品",
        "ランダムでの発送となります",
        "※こちらの商品は、簡易包装での発送になります",
        "２個１セット",
        "海外仕入れの製品のため",
        "【セット】",
        "セットしていただく",
        "木製セットは",
        "両手首用セット",
        "朝のセット",
        "すぐにセット",
        "サッとセットできます",
        "あの人にセット",
        "直接セットします",
        "本商品は送料を抑えた簡易包装",
        "ミニポーチがセット",
    ]

    # =================== 不要文字としてチェックすべきキーワード =========================
    # 不要文字を削除しても以下がヒットしたら、登録せずに内容を確認が必須。
    # コンタクトレンズなどは出品できない。
    _MY_CHK_WORDS = [
        "発送",
        "追跡番号",
        "送料",
        "無料",
        "Amazon",
        "メルカリ",
        "ラクマ",
        "プロフ",
        "お値引き",
        "無在庫",
        "メール便",
        "定形外",
        "アマゾン",
        "在庫切れ",
        "全国一律",
        "仕入れ",
        "楽天",
        "クリックポスト",
        "バイヤーズ",
        "【個人利用向け商品】",
        "コンタクトレンズ",
        "出品者",
        "年中無休",
        "佐川急便",
        "ゆうパック",
        "メール便",
        "ゆうパケット",
        "ロット販売",
        "同梱送料",
        "大口オプション",
        "普通郵便",
        "ネコポス",
        "ロット商品",
        "包装オプション",
        "セット",
        "小口ロット",
        "大口ロット",
        "円以上",
        "過激",
        "セクシー",
        "超特価",
        "銃",
        "ライフル",
        "スコープ",
        "すけべ",
        "すけすけ",
        "スケベ",
        "タクティカル",
        "陰茎",
        "睾丸",
        "陰嚢",
    ]
