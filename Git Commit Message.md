# Git Commit Message 编写指南

## 提交信息的结构

Commit message 一般都包括三个部分：Header，Body 和 Footer。

```
<type>(<scope>): <subject>
// 空一行
<body>
// 空一行
<footer>
```

其中，Header 是必需的，Body 和 Footer 大多数情况可以省略。

#### 1. Header

**Type：类型**

`type`用于说明 commit 的类别, 具体来说，`Type` 分为：

- **feat:** 增加新功能(feature)；
- **fix:** 修复错误(bug)；
- **docs:** 修改文档(documentation)；
- **style:** 修改样式(不影响代码运行的变动)；
- **refactor:** 代码重构(即不是新增功能，也不是修改bug的代码变动)；
- **test:** 增加测试模块，不涉及生产环境的代码；
- **chore:** 更新核心模块，包配置文件，不涉及生产环境的代码；

如果`type`为`feat`和`fix`，则该 commit 将肯定出现在 Change log (**可以直接从commit生成Change log**)之中。其他情况（`docs`、`chore`、`style`、`refactor`、`test`）由你决定，要不要放入 Change log，建议是不要。



**Scope**

`scope`用于说明 commit 影响的范围，比如数据层、控制层、视图层等等，视项目不同而不同。



**Subject：标题**

`subject`是 commit 目的的简短描述，不超过50个字符。

具体要求如下: 

* 以动词开头，使用祈使句来描述，比如`change`，而不是`changed`或`changes`
* 第一个字母小写
* 结尾不加句号（`.`）

#### 2. Body：正文

并不是所有的 Commit 都需要正文，必要的时候对本次 Commit 做一些背景说明，阐释具体的原因和内容，但是不解释具体的过程。

注意：

* 正文的文字不能超过72个字符
* 同样使用祈使句来描述

#### 3. Footer：结尾

Footer 部分只用于两种情况。

**（1）不兼容变动**

如果当前代码与上一个版本不兼容，则 Footer 部分以`BREAKING CHANGE`开头，后面是对变动的描述、以及变动理由和迁移方法。

```markdown
BREAKING CHANGE: isolate scope bindings definition has changed.

    To migrate the code follow the example below:

    Before:

    scope: {
      myAttr: 'attribute',
    }

    After:

    scope: {
      myAttr: '@',
    }

    The removed `inject` wasn't generaly useful for directives so there should be no code using it.
```

**（2）关闭 Issue**

如果当前 commit 针对某个issue，那么可以在 Footer 部分关闭这个 issue 。

```markdown
Closes #1, #2, #3
```



**补充:**

还有一种特殊情况，如果当前 commit 用于撤销以前的 commit，则必须以`revert:`开头，后面跟着被撤销 Commit 的 Header。

```
revert: feat(pencil): add 'graphiteWidth' option

This reverts commit 667ecc1654a317a13331b17617d973392f415f02.
```

Body部分的格式是固定的，必须写成`This reverts commit <hash>.`，其中的`hash`是被撤销 commit 的 SHA 标识符。

如果当前 commit 与被撤销的 commit，在同一个发布（release）里面，那么它们都不会出现在 Change log 里面。如果两者在不同的发布，那么当前 commit，会出现在 Change log 的`Reverts`小标题下面。

**Example：举例**

```
docs: add FAQ in readme file
```