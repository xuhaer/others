# others
一些不方便归类的其它代码片段、笔记、脚本等。


## Tesseract基于图片训练

### 1. 在 jTessBoxEditor 首先选择`Trainer`以生成`.box`文件:

```bash
# tesseract 安装目录:
Tesseract Executables: /usr/local/bin/tesseract
# 训练图片所在的路径:
Training Data: 
# 所要训练的语言名称，可以自己取名:
Language: chi_sim_my
# 生成box文件依赖的语言:
Bootstrap Languange: chi_sim+eng
# 单选框选择 Make Box File Only
```

### 2. 在 jTessBoxEditor选择`Box Editor`编辑修正.box 文件

### 3. 在 jTessBoxEditor再次选择`Trainer`完成训练

```bash
在完成box文件的编辑之后就可以使用box文件进行训练了
这一次单选框选择选择Train with Existing Box

训练过程中具体使用了哪些命令，都可以在控制台中查看。训练完成之后会在Training Data目录下生成有一个tessdata文件夹，文件夹文件夹中有个chi_my.tessdata文件就是我们的训练结果。我们需要将这个文件copy到*/share/tessdata就可以使用了。
```
