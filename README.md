# others
一些不方便归类的其它代码片段、笔记、脚本等。


## Tesseract

[官方文档：](https://github.com/tesseract-ocr/tesseract/wiki/TrainingTesseract-4.00)

想进行`### Fine Tuning for Impact`，尝试了2天，遇到这些问题：

* [Fix mktemp in tesstrain_utils.sh](https://github.com/tesseract-ocr/tesseract/pull/2051/commits/dbfc89f9af2b58f8a102cef81edbc2d4c2f37f0f)
* [Fix unbound variable $FONTS](https://github.com/tesseract-ocr/tesseract/pull/2056)

都解决后，在`# Create the training data`步骤后却无任何输出， 进行不到`=== Phase II===`步骤，却无错误提示，也暂未找到究竟哪儿出错了。

暂时放弃 Fine Tuning 的想法。
