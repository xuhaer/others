import pytesseract
from PIL import Image


def foo(path_name, lang='chi_sim+eng'):
    return pytesseract.image_to_string(Image.open(path_name), lang=lang)
