import glob
import time

import tempfile

from PIL import Image
import numpy as np
import pytesseract
import cv2
import pdf2image
from pdf2image import convert_from_path


def pdf_2_image(path='/Users/har/Desktop/test_data.pdf'):
    with tempfile.TemporaryDirectory() as temp_path:
        images = convert_from_path(path, dpi=96, thread_count=2, output_folder=temp_path)
    for index, image in enumerate(images, start=1):
        image.save(f'./datasets/pdf_imgs/第{index}页.png')


class CV2Process:
    """将单页的 pdf 图片进行处理，并从中提取出蛇类的图片"""

    def __init__(self, img_folder='./datasets/pdf_imgs/*.png', min_acontourAre=50000):
        self.min_acontourAre = min_acontourAre
        self.pdf_imgs = glob.glob(img_folder)

    def find_contours(self, img):
        """给定一页 pdf(图片), 返回该页所有包含蛇类的contours"""
        # 转为灰度图
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 留下具有高水平梯度和低垂直梯度的图像区域
        gradX = cv2.Sobel(gray, ddepth=cv2.CV_64F, dx=1, dy=0, ksize=-1)
        gradY = cv2.Sobel(gray, ddepth=cv2.CV_64F, dx=0, dy=1, ksize=-1)
        gradient = cv2.subtract(gradX, gradY)
        gradient = cv2.convertScaleAbs(gradient)

        # 去除图像上的噪声
        blurred = cv2.blur(gradient, (9, 9))
        # 梯度图像中不大于90的任何像素都设置为0(黑色), 否则，像素设置为255(白色)
        _, thresh = cv2.threshold(blurred, 90, 255, cv2.THRESH_BINARY)

        contours_, contours_property = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        snake_contours = list(filter(lambda ct: cv2.contourArea(ct) > self.min_acontourAre, contours_))
        return snake_contours

    def save_contours(self):
        for pdf_img in self.pdf_imgs:
            img = cv2.imread(pdf_img)
            for index, snake_ct in enumerate(self.find_contours(img)):
                rect = cv2.minAreaRect(snake_ct)
                box = np.int0(cv2.boxPoints(rect))
                Xs = [i[0] for i in box]
                Ys = [i[1] for i in box]
                x1, x2 = min(Xs), max(Xs)
                y1, y2 = min(Ys), max(Ys)
                height, width = y2 - y1, x2 - x1
                cropImg = img[y1:y1 + height, x1:x1 + width]
                cv2.imwrite(f'./datasets/snake_imgs/test{index}.png', cropImg)

if __name__ == '__main__':
    start = time.time()
    pdf_2_image()
    total_time = time.time() - start
    with open('total_time.txt', 'w') as f:
        f.write(str(total_time))
