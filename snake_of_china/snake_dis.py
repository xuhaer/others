from pyecharts.render import make_snapshot
from pyecharts.charts import Map
from pyecharts.commons.utils import JsCodefrom pyecharts import options as opts
from pyecharts import options as opts
from snapshot_selenium import snapshot

provs = {'北京': 13, '天津': 10, '重庆': 29, '上海': 12, '河北': 12, '山西': 17, '辽宁': 17, '吉林': 11, '黑龙江': 10, '江苏': 29, '浙江': 60, '安徽': 48, '福建': 85, '江西': 58, '山东': 14, '河南': 26, '湖北': 32, '湖南': 66, '广东': 76, '海南': 66, '四川': 66, '贵州': 74, '云南': 96, '陕西': 33, '甘肃': 36, '青海': 4, '台湾': 58, '内蒙古': 9, '广西': 99, '西藏': 39, '宁夏': 7, '新疆': 10, '香港': 29, '澳门': 15}


def map_visualmap() -> Map:
    c = (
        Map()
        .add("", [[k, v] for k, v in provs.items()], "china", is_map_symbol_show=False,
        label_opts=opts.LabelOpts(
            formatter=JsCode("function(params){return params.value;}"),
            font_size=15,
        ))
        .set_global_opts(
            title_opts=opts.TitleOpts(title="中国各省蛇种数量分布图——许某"),
            visualmap_opts=opts.VisualMapOpts(max_=100, is_piecewise=True),
        )
    )
    return c

make_snapshot(snapshot, map_visualmap().render(), "各省蛇种数量.png")
