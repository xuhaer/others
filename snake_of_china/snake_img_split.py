import re
import glob
import time

import tempfile

import numpy as np
import cv2
from pdf2image import convert_from_path


def pdf_2_image(path='/Users/har/Desktop/test_data.pdf'):
    with tempfile.TemporaryDirectory() as temp_path:
        images = convert_from_path(path, dpi=96, thread_count=2, output_folder=temp_path)
    for index, image in enumerate(images, start=1):
        image.save(f'./datasets/pdf_imgs_上册/第{index}页.png')


class CV2Process:
    """将单页的 pdf 图片进行处理，并从中提取出蛇类的图片"""

    def __init__(self, path='./datasets/test_pdf_imgs/*.png', min_acontourAre=50000):
        self.min_acontourAre = min_acontourAre
        self.im_paths = glob.glob(path)
        self.croped_images = {}

    def gen_crop_images(self):
        """将原始 pdf 页初处理并以{page: img}的形式存储"""
        for im_path in self.im_paths:
            img = cv2.imread(im_path)
            page = int(re.findall(r'第(\d+)页', im_path)[0])
            if page % 2:
                # 有右上侧栏:
                # 上、下、左、右
                croped_img = img[155: -1, 8:-145] # 下册
                # 上册: croped_img = img[155: -1, 8:-250]
            else:
                # 有左侧栏
                croped_img = img[1:-1, 330:-6] # 下册
                # 上册: croped_img = img[260:-230, 220:-6]
            self.croped_images[page] = croped_img

    def find_contours(self, croped_image, page):
        """给定crop_image, 返回该页所有包含蛇类的contours"""
        # 转为灰度图
        gray = cv2.cvtColor(croped_image, cv2.COLOR_BGR2GRAY)

        # 留下具有高水平梯度和低垂直梯度的图像区域
        gradX = cv2.Sobel(gray, ddepth=cv2.CV_64F, dx=1, dy=0, ksize=-1)
        gradY = cv2.Sobel(gray, ddepth=cv2.CV_64F, dx=0, dy=1, ksize=-1)
        gradient = cv2.subtract(gradX, gradY)
        gradient = cv2.convertScaleAbs(gradient)

        # 去除图像上的噪声
        blurred = cv2.blur(gradient, (15, 15))
        # 梯度图像中不大于90的任何像素都设置为0(黑色), 否则，像素设置为255(白色)
        _, thresh = cv2.threshold(blurred, 90, 255, cv2.THRESH_BINARY)

        contours_, contours_property = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        snake_contours = list(filter(lambda ct: cv2.contourArea(ct) > self.min_acontourAre, contours_))
        return snake_contours

    def save_contours(self):
        self.gen_crop_images()
        for page, croped_image in self.croped_images.items():
            for index, snake_ct in enumerate(self.find_contours(croped_image, page), start=1):
                rect = cv2.minAreaRect(snake_ct)
                box = np.int0(cv2.boxPoints(rect))
                Xs = [i[0] for i in box]
                Ys = [i[1] for i in box]
                x1, x2 = min(Xs), max(Xs)
                y1, y2 = min(Ys), max(Ys)
                height, width = y2 - y1, x2 - x1
                snake_img = croped_image[y1:y1 + height, x1:x1 + width]
                cv2.imwrite(f'./datasets/snake_imgs/{page}页第{index}张图.jpeg', snake_img)

if __name__ == '__main__':
    start = time.time()
    c = CV2Process(path='./datasets/test_pdf_imgs/*.png')
    c.save_contours()
    total_time = time.time() - start
    with open('total_time.txt', 'w') as f:
        f.write(str(total_time))
