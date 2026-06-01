---
aliases: [Dataview查询手册]
tags: [工具, Dataview]
---

# Dataview 常用查询手册

> 安装Obsidian插件：**Dataview**（必装）、**Templater**（推荐）

---

## 1. 按阶段查询所有政策文件

```dataview
TABLE 发布日期, 效力层级, 发布机构
FROM ""
WHERE 演进阶段 = "阶段三：规制重构期"
SORT 发布日期 ASC
```

将引号内改为以下任一值：
- `阶段一：萌芽起步期`
- `阶段二：加速构建期`
- `阶段三：规制重构期`
- `阶段四：高质量发展期`

---

## 2. 按专题分类查询

```dataview
TABLE 文件名称, 发布日期, 效力层级
FROM ""
WHERE 专题分类 = "数据安全"
SORT 发布日期 ASC
```

---

## 3. 查询全国人大立法（最高效力层级）

```dataview
TABLE 文件名称, 发布日期, 施行日期
FROM ""
WHERE 效力层级 = "全国人大常委会立法"
SORT 发布日期 ASC
```

---

## 4. 查询尚未精读的重要文件（⭐⭐⭐⭐以上）

```dataview
TABLE 文件名称, 重要程度, 演进阶段
FROM ""
WHERE 阅读状态 != "精读完成" AND 重要程度 >= "⭐⭐⭐⭐"
SORT 重要程度 DESC
```

---

## 5. 查询典型案例

```dataview
TABLE 案例名称, 涉及主体, 监管机构, 处理结果
FROM "05-典型案例"
SORT 发生时间 DESC
```

---

## 6. 数据跨境相关文件全检索

```dataview
TABLE 文件名称, 发布日期, 效力层级
FROM ""
WHERE contains(tags, "数据跨境") OR 专题分类 = "数据跨境"
SORT 发布日期 ASC
```

---

## 7. 查询某文件的所有配套文件（反向链接）

在任意笔记中使用以下代码，查看哪些文件引用了当前文件：

```dataview
LIST
FROM [[]]
```

---

## 8. 统计各阶段文件数量

```dataview
TABLE length(rows) AS "文件数量"
FROM ""
WHERE 演进阶段 != null
GROUP BY 演进阶段
```

---

## 9. 教学资料快速检索

```dataview
TABLE 课程名称, 适用章节, 所需课时
FROM "07-教学资料"
SORT file.mtime DESC
```

---

## 10. 待办：有未完成研究任务的文件

```dataview
TASK
FROM ""
WHERE !completed
GROUP BY file.link
```
